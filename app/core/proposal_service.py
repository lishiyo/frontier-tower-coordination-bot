from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models.proposal_model import Proposal, ProposalType, ProposalStatus
from app.persistence.repositories.proposal_repository import ProposalRepository
from app.persistence.repositories.submission_repository import SubmissionRepository
from app.services.llm_service import LLMService
from app.utils import telegram_utils
from app.config import ConfigService
from telegram.ext import Application

from collections import Counter

from app.core.user_service import UserService

import logging
logger = logging.getLogger(__name__)

class ProposalService:
    def __init__(self, db_session: AsyncSession, bot_app: Optional[Application] = None):
        self.db_session = db_session
        self.proposal_repository = ProposalRepository(db_session)
        self.user_service = UserService(db_session)
        self.submission_repository = SubmissionRepository(db_session)
        self.llm_service = LLMService()
        self.bot_app = bot_app


    async def create_proposal(
        self,
        proposer_telegram_id: int,
        proposer_username: Optional[str],
        proposer_first_name: Optional[str],
        title: str,
        description: str,
        proposal_type: ProposalType,
        options: Optional[List[str]],
        deadline_date: datetime,
        target_channel_id: str,
    ) -> Proposal:
        """
        Creates a new proposal but does NOT commit the session.
        The calling handler/service is responsible for the commit.
        Ensures the proposer exists via UserService and then adds the proposal.
        """
        # Ensure proposer exists. UserService's register_user_interaction
        # handles the get_or_create logic. The underlying UserRepository
        # methods are designed not to commit, allowing service layer to control transactions.
        proposer = await self.user_service.register_user_interaction(
            telegram_id=proposer_telegram_id,
            username=proposer_username,
            first_name=proposer_first_name,
        )

        # Add the proposal using ProposalRepository
        # Note: ProposalRepository.add_proposal currently has its own commit.
        # This might be revisited for unified transaction management.
        new_proposal = await self.proposal_repository.add_proposal(
            proposer_telegram_id=proposer.telegram_id,
            title=title,
            description=description,
            proposal_type=proposal_type,
            options=options,
            deadline_date=deadline_date,
            target_channel_id=target_channel_id,
            # channel_message_id and status use defaults or are set later.
        )
        
        # No commit here. The caller (e.g., conversation handler) will commit.
        # await self.db_session.commit() # REMOVED

        return new_proposal 

    async def list_proposals_by_channel(self, channel_id: str) -> List[Proposal]:
        """Lists proposals for a given channel_id."""
        # Ensure channel_id is a string, as it's stored that way and might come as int from Telegram
        return await self.proposal_repository.get_proposals_by_channel_id(str(channel_id))

    async def list_proposals_by_proposer(self, user_telegram_id: int) -> List[Dict[str, Any]]:
        """Lists proposals created by a specific user, formatted for display."""
        proposals = await self.proposal_repository.get_proposals_by_proposer_id(user_telegram_id)
        formatted_proposals = []
        for proposal in proposals:
            formatted_proposals.append({
                "id": proposal.id,
                "title": proposal.title,
                "status": proposal.status,
                "deadline_date": telegram_utils.format_datetime_for_display(proposal.deadline_date),
                "creation_date": telegram_utils.format_datetime_for_display(proposal.creation_date),
                "outcome": proposal.outcome,
                "target_channel_id": proposal.target_channel_id,
                "proposal_type": proposal.proposal_type,
                "channel_message_id": proposal.channel_message_id
            })
        return formatted_proposals

    async def list_proposals_by_status(self, status: str) -> list[dict]:
        """Lists proposals by their status (e.g., 'open', 'closed')."""
        proposals = await self.proposal_repository.get_proposals_by_status(status)
        formatted_proposals = []
        for proposal in proposals:
            proposal_info = {
                "id": proposal.id,
                "title": proposal.title,
                "status": proposal.status.value if hasattr(proposal.status, 'value') else str(proposal.status),
                "target_channel_id": proposal.target_channel_id,
                "channel_message_id": proposal.channel_message_id
            }
            if proposal.status == ProposalStatus.OPEN.value:
                proposal_info["deadline_date"] = telegram_utils.format_datetime_for_display(proposal.deadline_date)
            elif proposal.status == ProposalStatus.CLOSED.value:
                proposal_info["outcome"] = proposal.outcome or "Results not yet processed or N/A"
                proposal_info["closed_date"] = telegram_utils.format_datetime_for_display(proposal.deadline_date) # Or a separate closed_at field if added
            
            formatted_proposals.append(proposal_info)
        return formatted_proposals

    async def process_expired_proposals(self) -> List[Proposal]:
        """
        Processes proposals that have passed their deadline.
        - Fetches expired open proposals.
        - Calculates results for multiple-choice or summarizes free-form.
        - Updates proposal status, outcome, and raw_results.
        - Posts results to the target channel.
        Returns a list of processed proposals.
        """
        logger.info("Processing expired proposals...")
        expired_proposals = await self.proposal_repository.find_expired_open_proposals()
        processed_proposals = []

        if not expired_proposals:
            logger.info("No expired open proposals found.")
            return processed_proposals

        for proposal in expired_proposals:
            logger.info(f"Processing expired proposal ID: {proposal.id} - '{proposal.title}'")
            submissions = await self.submission_repository.get_submissions_for_proposal(proposal.id)
            
            outcome_text = "Results are now available."
            raw_results_data = {}

            if proposal.proposal_type == ProposalType.MULTIPLE_CHOICE.value:
                if submissions:
                    vote_counts = Counter(sub.response_content for sub in submissions if sub.response_content in proposal.options)
                    raw_results_data = dict(vote_counts)
                    
                    if vote_counts:
                        # Determine winner(s)
                        max_votes = 0
                        winners = []
                        for option, count in vote_counts.items():
                            if count > max_votes:
                                max_votes = count
                                winners = [option]
                            elif count == max_votes:
                                winners.append(option)
                        
                        if len(winners) == 1:
                            outcome_text = f"Voting ended. Winner: {winners[0]} ({max_votes} vote{'s' if max_votes > 1 else ''})."
                        elif len(winners) > 1:
                            outcome_text = f"Voting ended. Tie between: {', '.join(winners)} (each with {max_votes} vote{'s' if max_votes > 1 else ''})."
                        else: # Should not happen if vote_counts is not empty
                            outcome_text = "Voting ended. No votes were cast for valid options."
                    else:
                        outcome_text = "Voting ended. No votes were cast."
                else:
                    outcome_text = "Voting ended. No submissions received."
                logger.info(f"Proposal {proposal.id} (MC) outcome: {outcome_text}, Raw: {raw_results_data}")

            elif proposal.proposal_type == ProposalType.FREE_FORM.value:
                submission_texts = [sub.response_content for sub in submissions]
                raw_results_data = {"submissions": submission_texts} # Store all submissions
                
                if submission_texts:
                    num_submissions = len(submission_texts)
                    s_char = 's' if num_submissions != 1 else ''
                    try:
                        summary = await self.llm_service.cluster_and_summarize_texts(submission_texts)
                        if summary: # Check if summary is not None or empty
                            # Ensure newlines from LLM (which might be literal \n or \\n) are actual \n characters
                            # The LLM is prompted to provide newlines for formatting.
                            # If the LLM itself sends '\n' (literal backslash + n), it might become '\\n' after f-string or escaping.
                            # We want actual newline characters in the string before MarkdownV2 escaping.
                            processed_summary = summary.replace("\\n", "\n").replace("\n", "\n") 
                            # The f-string itself should use a literal newline where desired for the initial part.
                            outcome_text = f"{num_submissions} submission{s_char} recorded. Summary of themes:\n{processed_summary}"
                            logger.info(f"Proposal {proposal.id} (FF) - Generated LLM summary for {num_submissions} submissions. Processed summary for outcome: {repr(outcome_text)}")
                        else: # LLM service returned None or empty, or an error message string from the service itself
                            outcome_text = f"{num_submissions} submission{s_char} recorded. Could not generate a summary of submissions. Full list available via /view_results."
                            logger.warning(f"Proposal {proposal.id} (FF) - LLM summary was None or empty for {num_submissions} submissions. Fallback message used.")
                    except Exception as e:
                        logger.error(f"Error during LLM clustering for proposal {proposal.id} ({num_submissions} submissions): {e}", exc_info=True)
                        outcome_text = f"{num_submissions} submission{s_char} recorded. Error processing submissions for summary. Full list available via /view_results."
                else:
                    outcome_text = "No submissions received." # Changed from "Idea collection ended. No submissions received." for conciseness
                logger.info(f"Proposal {proposal.id} (FF) outcome: {outcome_text}")
            
            # Update proposal in DB
            updated_proposal = await self.proposal_repository.update_proposal_status(
                proposal_id=proposal.id,
                status=ProposalStatus.CLOSED,
                outcome=outcome_text,
                raw_results=raw_results_data
            )

            if updated_proposal:
                processed_proposals.append(updated_proposal)
                # Post results to channel
                if self.bot_app and self.bot_app.bot and updated_proposal.target_channel_id and updated_proposal.channel_message_id:
                    try:
                        # We need user object for proposer name, which is not directly available here.
                        # For now, we might need a simpler results message or modify format_proposal_results_message
                        # Alternatively, fetch proposer from updated_proposal.proposer_telegram_id if needed by formatter
                        
                        # Let's create a simpler results message directly for now
                        results_message_text = f"🏁 *Results for: {telegram_utils.escape_markdown_v2(updated_proposal.title)}* 🏁\n\n"
                        results_message_text += f"{telegram_utils.escape_markdown_v2(outcome_text)}\n\n"
                        
                        if updated_proposal.proposal_type == ProposalType.MULTIPLE_CHOICE.value and raw_results_data:
                            results_message_text += "Vote breakdown:\n"
                            total_votes = sum(raw_results_data.values())
                            for option, count in sorted(raw_results_data.items(), key=lambda item: item[1], reverse=True):
                                percentage = (count / total_votes * 100) if total_votes > 0 else 0
                                # Escape the percentage part separately
                                percentage_str = f"({percentage:.1f}%)"
                                escaped_percentage_str = telegram_utils.escape_markdown_v2(percentage_str)
                                results_message_text += f"\\- {telegram_utils.escape_markdown_v2(option)}: {count} vote{'s' if count != 1 else ''} {escaped_percentage_str}\n"
                        
                        # Escape the final instructional line part that's not in a code block
                        bot_username_mention = f"@{self.bot_app.bot.username}" if self.bot_app and self.bot_app.bot and self.bot_app.bot.username else "the bot"
                        instructional_part = f" (DM {bot_username_mention})"
                        escaped_instructional_part = telegram_utils.escape_markdown_v2(instructional_part)
                        results_message_text += f"\nView full details or all submissions with: `/view_results {updated_proposal.id}`{escaped_instructional_part}"

                        logger.info(f"Attempting to send results message for proposal {updated_proposal.id}. Final text (repr): {repr(results_message_text)}")
                        await self.bot_app.bot.send_message(
                            chat_id=updated_proposal.target_channel_id,
                            text=results_message_text,
                            reply_to_message_id=updated_proposal.channel_message_id, # Reply to original proposal message
                            parse_mode='MarkdownV2'
                        )
                        logger.info(f"Posted results for proposal {updated_proposal.id} to channel {updated_proposal.target_channel_id}")
                    except Exception as e:
                        logger.error(f"Error posting results for proposal {updated_proposal.id} to channel: {e}", exc_info=True)
            else:
                logger.error(f"Failed to update status for proposal ID: {proposal.id}")
        
        logger.info(f"Finished processing {len(processed_proposals)} expired proposals.")
        return processed_proposals 