import logging
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models.proposal_model import Proposal, ProposalType, ProposalStatus
from app.persistence.repositories.proposal_repository import ProposalRepository
from app.persistence.repositories.submission_repository import SubmissionRepository
from app.core.user_service import UserService # To ensure voter exists

logger = logging.getLogger(__name__)

class SubmissionService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.proposal_repository = ProposalRepository(db_session)
        self.submission_repository = SubmissionRepository(db_session)
        self.user_service = UserService(db_session)

    async def record_vote(
        self,
        proposal_id: int,
        submitter_telegram_id: int, # submitter's telegram_id
        option_index: int
    ) -> Tuple[bool, str]: # Returns (success_status, message_to_user)
        """
        Records a vote for a multiple-choice proposal.
        Validates the proposal and option, then adds/updates the submission.
        """
        try:
            # 1. Fetch the proposal
            proposal = await self.proposal_repository.get_proposal_by_id(proposal_id)
            if not proposal:
                logger.warning(f"Attempt to vote on non-existent proposal ID: {proposal_id}")
                return False, "Error: Proposal not found."

            # 2. Validate proposal status and type
            if proposal.status != ProposalStatus.OPEN.value:
                logger.warning(f"Attempt to vote on proposal {proposal_id} which is not open (status: {proposal.status}).")
                return False, f"Sorry, voting for proposal '{proposal.title}' is closed."
            
            if proposal.proposal_type != ProposalType.MULTIPLE_CHOICE.value:
                logger.warning(f"Attempt to vote on proposal {proposal_id} which is not multiple-choice (type: {proposal.proposal_type}).")
                return False, "Error: This proposal does not support multiple-choice voting."

            # 3. Validate option_index
            if not proposal.options or not (0 <= option_index < len(proposal.options)):
                logger.error(f"Invalid option index {option_index} for proposal {proposal_id} with {len(proposal.options) if proposal.options else 0} options.")
                return False, "Error: Invalid option selected."
            
            selected_option_string = proposal.options[option_index]

            # 4. Ensure voter (submitter) exists - UserService handles get_or_create logic
            # We assume user details (username, first_name) are not strictly needed here for submission,
            # but if they were, the callback_query.from_user object would be passed here.
            # For now, just ensuring the user is in our DB is enough via their ID.
            voter = await self.user_service.register_user_interaction(
                telegram_id=submitter_telegram_id,
                username=None,  # We don't have these details here
                first_name=None  # We don't have these details here
            )
            if not voter: # Should ideally be registered from some prior interaction like /start
                # If we want to auto-register on vote, we'd need more user details.
                # For now, we assume they must have interacted before if they are voting.
                logger.warning(f"User {submitter_telegram_id} attempted to vote but is not registered. This should ideally not happen.")
                # This case is tricky: if user not in DB, FK constraint on submissions.submitter_id will fail.
                # Best practice: ensure users are registered upon any interaction that could lead to DB writes.
                # For now, we will rely on UserService.get_user_by_telegram_id and fail if not found, 
                # assuming /start or other commands register them.
                # If a truly new user (no /start) somehow gets a vote button, this needs robust handling.
                # One approach: If UserService.register_user_interaction was called with (id, None, None)
                # during the callback handler setup or here if it can be done without breaking flow.
                # Simplest for now: user must exist. This implies that their first_name/username 
                # were captured during an earlier interaction.
                return False, "Error: Voter registration not found. Please /start the bot first."

            # 5. Add or update the submission
            submission = await self.submission_repository.add_or_update_submission(
                proposal_id=proposal_id,
                submitter_id=submitter_telegram_id,
                response_content=selected_option_string
            )

            if submission:
                logger.info(f"Successfully recorded vote for user {submitter_telegram_id} on proposal {proposal_id}, option: '{selected_option_string}'")
                return True, f"Your vote for '{selected_option_string}' has been recorded!"
            else:
                logger.error(f"Failed to record vote for user {submitter_telegram_id} on proposal {proposal_id} in repository.")
                return False, "An error occurred while saving your vote. Please try again."

        except Exception as e:
            logger.error(f"Unexpected error in record_vote for proposal {proposal_id}, user {submitter_telegram_id}: {e}", exc_info=True)
            return False, "An unexpected error occurred. Please try again later."

    async def record_free_form_submission(
        self,
        proposal_id: int,
        submitter_telegram_id: int, # submitter's telegram_id
        text_submission: str
    ) -> Tuple[bool, str]: # Returns (success_status, message_to_user)
        """
        Records a free-form submission for a proposal.
        Validates the proposal, then adds/updates the submission.
        """
        try:
            # 1. Fetch the proposal
            proposal = await self.proposal_repository.get_proposal_by_id(proposal_id)
            if not proposal:
                logger.warning(f"Attempt to submit to non-existent proposal ID: {proposal_id}")
                return False, "Error: Proposal not found."

            # 2. Validate proposal status and type
            if proposal.status != ProposalStatus.OPEN.value:
                logger.warning(f"Attempt to submit to proposal {proposal_id} which is not open (status: {proposal.status}).")
                return False, f"Sorry, submissions for proposal '{proposal.title}' are closed."
            
            if proposal.proposal_type != ProposalType.FREE_FORM.value:
                logger.warning(f"Attempt to submit to proposal {proposal_id} which is not free_form (type: {proposal.proposal_type}).")
                return False, "Error: This proposal does not accept free-form submissions."

            # 3. Ensure submitter exists
            # Assuming user details (username, first_name) are not strictly needed here for submission.
            # The command handler for /submit should pass the user's telegram_id.
            submitter = await self.user_service.register_user_interaction(
                telegram_id=submitter_telegram_id,
                username=None,  # We don't have these details here from just the ID and text
                first_name=None  # We don't have these details here
            )
            if not submitter:
                logger.warning(f"User {submitter_telegram_id} attempted to submit but is not registered. This should ideally not happen.")
                return False, "Error: Submitter registration not found. Please /start the bot first."

            # 4. Add or update the submission
            submission = await self.submission_repository.add_or_update_submission(
                proposal_id=proposal_id,
                submitter_id=submitter_telegram_id,
                response_content=text_submission
            )

            if submission:
                logger.info(f"Successfully recorded free-form submission for user {submitter_telegram_id} on proposal {proposal_id}.")
                return True, "Your submission has been recorded!"
            else:
                logger.error(f"Failed to record free-form submission for user {submitter_telegram_id} on proposal {proposal_id} in repository.")
                return False, "An error occurred while saving your submission. Please try again."

        except Exception as e:
            logger.error(f"Unexpected error in record_free_form_submission for proposal {proposal_id}, user {submitter_telegram_id}: {e}", exc_info=True)
            return False, "An unexpected error occurred. Please try again later." 