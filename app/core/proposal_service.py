from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models.proposal_model import Proposal, ProposalType, ProposalStatus
from app.persistence.repositories.proposal_repository import ProposalRepository
from app.persistence.repositories.submission_repository import SubmissionRepository
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.utils import telegram_utils
from app.config import ConfigService
from telegram.ext import Application

from collections import Counter

from app.core.user_service import UserService
from app.persistence.models.user_model import User
from app.utils.telegram_utils import escape_markdown_v2
from telegram.constants import ParseMode

import logging
logger = logging.getLogger(__name__)

class ProposalService:
    def __init__(self, db_session: AsyncSession, bot_app: Optional[Application] = None):
        self.db_session = db_session
        self.proposal_repository = ProposalRepository(db_session)
        self.user_service = UserService(db_session)
        self.submission_repository = SubmissionRepository(db_session)
        self.llm_service = LLMService()
        self.vector_db_service = VectorDBService()
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
        
        # Index the proposal for semantic search
        try:
            # Concatenate title and description for indexing
            proposal_text_to_index = new_proposal.title + " " + new_proposal.description
            
            # For multiple-choice proposals, include the options in the indexed text
            if new_proposal.proposal_type == ProposalType.MULTIPLE_CHOICE.value and new_proposal.options:
                options_text = " Options: " + ", ".join(new_proposal.options)
                proposal_text_to_index += options_text
            
            # Generate embedding using LLMService
            embedding = await self.llm_service.generate_embedding(proposal_text_to_index)
            
            if embedding:
                # Prepare metadata for the embedding
                metadata = {
                    "proposal_id": new_proposal.id,
                    "status": new_proposal.status,
                    "deadline_date_iso": new_proposal.deadline_date.isoformat() if new_proposal.deadline_date else None,
                    "creation_date_iso": new_proposal.creation_date.isoformat() if new_proposal.creation_date else None,
                    "proposal_type": new_proposal.proposal_type,
                    "target_channel_id": new_proposal.target_channel_id
                }
                
                # Store the embedding
                chroma_id = await self.vector_db_service.add_proposal_embedding(
                    proposal_id=new_proposal.id,
                    text_content=proposal_text_to_index,
                    embedding=embedding,
                    metadata=metadata
                )
                
                if chroma_id:
                    logger.info(f"Successfully indexed proposal ID {new_proposal.id} for semantic search with ChromaDB ID {chroma_id}")
                else:
                    logger.error(f"Failed to index proposal ID {new_proposal.id} in ChromaDB")
            else:
                logger.error(f"Failed to generate embedding for proposal ID {new_proposal.id}")
        except Exception as e:
            # We don't want to fail the proposal creation if indexing fails
            logger.error(f"Error during indexing of new proposal ID {new_proposal.id}: {e}", exc_info=True)

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

    async def get_proposal_for_editing(self, proposal_id: int, user_telegram_id: int) -> tuple[Optional[Proposal], Optional[str]]:
        """
        Retrieves a proposal for editing, performing necessary checks.
        Checks: Proposal existence, user authorization, proposal status (must be OPEN),
                and if there are any submissions.
        Returns: (Proposal, None) if all checks pass, otherwise (None, error_message).
        """
        proposal = await self.proposal_repository.get_proposal_by_id(proposal_id)

        if not proposal:
            return None, "Proposal not found."

        if proposal.proposer_telegram_id != user_telegram_id:
            return None, "You are not authorized to edit this proposal."

        if proposal.status != ProposalStatus.OPEN.value:
            return None, f"This proposal is not open for editing (current status: {proposal.status})."

        submission_count = await self.submission_repository.count_submissions_for_proposal(proposal_id)
        if submission_count > 0:
            return None, (
                f"This proposal cannot be edited because it already has submissions or votes. "
                f"Please cancel it using `/cancel_proposal {proposal_id}` and create a new one if changes are needed."
            )

        return proposal, None

    async def edit_proposal_details(
        self,
        proposal_id: int,
        proposer_telegram_id: int,
        new_title: Optional[str] = None,
        new_description: Optional[str] = None,
        new_options: Optional[List[str]] = None,
    ) -> tuple[Optional[Proposal], Optional[str]]:
        """
        Edits the details of an existing proposal if the user is the proposer
        and no submissions have been made.
        Returns a tuple (updated_proposal, error_message).
        One of them will be None.
        """
        proposal = await self.proposal_repository.get_proposal_by_id(proposal_id)

        if not proposal:
            return None, "Proposal not found."

        if proposal.proposer_telegram_id != proposer_telegram_id:
            return None, "You are not authorized to edit this proposal."

        if proposal.status != ProposalStatus.OPEN.value:
            return None, f"This proposal is not open for editing (current status: {proposal.status})."

        submission_count = await self.submission_repository.count_submissions_for_proposal(proposal_id)
        if submission_count > 0:
            return None, "This proposal cannot be edited because it already has submissions. Please cancel it and create a new one if changes are needed."

        # At least one field must be provided for editing
        if new_title is None and new_description is None and new_options is None:
            return None, "No changes provided. Please specify what you want to edit (title, description, or options)."

        updated_proposal = await self.proposal_repository.update_proposal_details(
            proposal_id=proposal_id,
            title=new_title if new_title is not None else proposal.title,
            description=new_description if new_description is not None else proposal.description,
            options=new_options if new_options is not None else proposal.options,
            # Ensure proposal_type is not accidentally changed if options are None but type was MC
            # This method assumes options are only provided if they are being changed.
            # If new_options are provided and it's an empty list for an MC proposal, it should likely remain MC with no options or be an error.
            # For simplicity, we'll assume type doesn't change here. It's complex if options make it freeform.
        )

        if not updated_proposal:
            # This case should ideally not happen if the proposal existed and update logic is correct
            return None, "Failed to update proposal in the database."
            
        # Caller (ConversationHandler) will be responsible for committing the session
        # and for updating the message in the channel.
        
        # Re-index proposal for semantic search if title or description changed
        if new_title or new_description or new_options:
            try:
                proposal_text_to_index = updated_proposal.title + " " + updated_proposal.description
                
                # For multiple-choice proposals, include the options in the indexed text
                if updated_proposal.proposal_type == ProposalType.MULTIPLE_CHOICE.value and updated_proposal.options:
                    options_text = " Options: " + ", ".join(updated_proposal.options)
                    proposal_text_to_index += options_text
                
                embedding = await self.llm_service.generate_embedding(proposal_text_to_index)
                
                if embedding:
                    # Prepare metadata for the embedding
                    metadata = {
                        "proposal_id": updated_proposal.id,
                        "status": updated_proposal.status,
                        "deadline_date_iso": updated_proposal.deadline_date.isoformat() if updated_proposal.deadline_date else None,
                        "creation_date_iso": updated_proposal.creation_date.isoformat() if updated_proposal.creation_date else None,
                        "proposal_type": updated_proposal.proposal_type,
                        "target_channel_id": updated_proposal.target_channel_id
                    }
                    
                    # Update the embedding in ChromaDB
                    chroma_id = await self.vector_db_service.add_proposal_embedding(
                        proposal_id=updated_proposal.id,
                        text_content=proposal_text_to_index,
                        embedding=embedding,
                        metadata=metadata
                    )
                    
                    if chroma_id:
                        logger.info(f"Successfully re-indexed proposal ID {updated_proposal.id} for semantic search with ChromaDB ID {chroma_id}")
                    else:
                        logger.error(f"Failed to re-index proposal ID {updated_proposal.id} in ChromaDB")
                else:
                    logger.error(f"Failed to generate embedding for updated proposal ID {updated_proposal.id}")
            except Exception as e:
                logger.error(f"Error during re-indexing proposal {updated_proposal.id} after edit: {e}", exc_info=True)

        return updated_proposal, None

    async def cancel_proposal_by_proposer(self, proposal_id: int, user_telegram_id: int) -> tuple[bool, str]:
        """
        Cancels a proposal if the user is the proposer and the proposal is open.
        Updates the proposal status and edits the channel message.
        Returns a tuple (success_status, message_to_user).
        """
        proposal = await self.proposal_repository.get_proposal_by_id(proposal_id)

        if not proposal:
            return False, "Proposal not found."

        if proposal.proposer_telegram_id != user_telegram_id:
            return False, "You are not authorized to cancel this proposal."

        if proposal.status != ProposalStatus.OPEN.value:
            return False, f"This proposal cannot be cancelled. Its current status is: {proposal.status}"

        updated_proposal = await self.proposal_repository.update_proposal_status(
            proposal_id, ProposalStatus.CANCELLED
        )

        if not updated_proposal:
            return False, "Failed to update proposal status to cancelled."

        # Commit the session after successful status update and before trying to send messages
        await self.db_session.commit()
        logger.info(f"Proposal {proposal_id} cancelled by user {user_telegram_id}. Status updated and committed.")

        # Edit the original message in the channel to indicate cancellation
        if self.bot_app and updated_proposal.target_channel_id and updated_proposal.channel_message_id:
            try:
                if not proposal.proposer: # Should not happen due to eager loading
                    logger.error(f"Proposer not loaded for proposal {proposal_id} during cancellation message update.")
                    # Avoid raising an error that might rollback the successful cancellation,
                    # just log and proceed with user message. Channel message edit will fail gracefully.
                else:
                    # To ensure the formatted message reflects the "cancelled" status,
                    # we should pass the `updated_proposal` object, as its status field is current.
                    # The `proposer` information comes from the original `proposal` object which had it eager-loaded.
                    channel_message_text = telegram_utils.format_proposal_message(
                        proposal=updated_proposal, # This has the updated 'cancelled' status
                        proposer=proposal.proposer # This is the eagerly loaded User object
                    )
                    
                    # Add a clear "CANCELLED" prefix or suffix to the message
                    cancelled_prefix = escape_markdown_v2("--- CANCELLED ---\n\n")
                    final_channel_text = cancelled_prefix + channel_message_text

                    await self.bot_app.bot.edit_message_text(
                        chat_id=updated_proposal.target_channel_id,
                        message_id=updated_proposal.channel_message_id,
                        text=final_channel_text,
                        reply_markup=None, # Remove voting buttons
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    logger.info(f"Edited channel message for cancelled proposal ID {proposal_id}.")
            except Exception as e:
                logger.error(f"Failed to edit channel message for cancelled proposal ID {proposal_id}: {e}", exc_info=True)
                # Don't return error to user here, proposal is already cancelled. This is a secondary effect.

        return True, f"Proposal ID {proposal_id} has been successfully cancelled."

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