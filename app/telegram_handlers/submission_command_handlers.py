import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from app.core.submission_service import SubmissionService
from app.persistence.database import AsyncSessionLocal

# TODO: Implement submission-related command handlers here:
# - submit_command (/submit)
# - my_votes_command (/my_submissions or /my_votes)
# - view_results_command (/view_results)

logger = logging.getLogger(__name__)

async def submit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /submit command for free-form proposals.
    Expected format: /submit <proposal_id> <text_submission>
    """
    if not update.message or not update.message.text or not update.effective_user:
        logger.warning("submit_command received an empty message or no user.")
        return

    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "Usage: /submit <proposal_id> <your text submission>\n"
            "Example: /submit 123 This is my great idea for the community event!"
        )
        return

    try:
        proposal_id_str = args[0]
        proposal_id = int(proposal_id_str)
    except ValueError:
        await update.message.reply_text(
            f"Invalid proposal ID: '{proposal_id_str}'. Please provide a numeric ID."
        )
        return

    text_submission = " ".join(args[1:])
    submitter_telegram_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        submission_service = SubmissionService(session)
        success, message = await submission_service.record_free_form_submission(
            proposal_id=proposal_id,
            submitter_telegram_id=submitter_telegram_id,
            text_submission=text_submission
        )
        
        await update.message.reply_text(message)

    logger.info(f"User {submitter_telegram_id} used /submit for proposal {proposal_id}. Success: {success}. Message: {message}")


# Add other submission-related command handlers below 