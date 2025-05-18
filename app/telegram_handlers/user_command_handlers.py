import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.core.user_service import UserService
from app.core.submission_service import SubmissionService
from app.persistence.database import get_session
from app.utils.telegram_utils import escape_markdown_v2

logger = logging.getLogger(__name__)

async def my_votes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the user a history of their votes/submissions."""
    if not update.effective_user:
        # This check might be redundant if an error handler catches update.effective_user being None earlier
        if update.message: # Check if message exists before replying
            await update.message.reply_text("Could not identify user.")
        else: # Log if no message associated, though typically commands come via messages
            logger.warning("/my_votes command received without an effective user and no message.")
        return

    user_id = update.effective_user.id
    username = update.effective_user.username or "N/A"
    first_name = update.effective_user.first_name or "N/A"
    
    logger.info(f"/my_votes command initiated by user {user_id} ({username})")

    async with get_session() as db_session:
        try:
            user_service = UserService(db_session)
            await user_service.register_user_interaction(
                telegram_id=user_id,
                username=username,
                first_name=first_name
            )

            submission_service = SubmissionService(db_session)
            history = await submission_service.get_user_submission_history(submitter_id=user_id)

            if not history:
                await update.message.reply_text("You haven't made any submissions or cast any votes yet.")
                return

            response_messages = []
            current_message = "Here\'s your submission history:\n\n"
            
            for item in history:
                proposal_title = escape_markdown_v2(str(item.get('proposal_title', 'N/A')))
                proposal_id_str = escape_markdown_v2(str(item.get('proposal_id', 'N/A')))
                user_response = escape_markdown_v2(str(item.get('user_response', 'N/A')))
                proposal_status = escape_markdown_v2(str(item.get('proposal_status', 'N/A')))
                proposal_outcome = escape_markdown_v2(str(item.get('proposal_outcome', 'N/A')))
                submission_timestamp = escape_markdown_v2(str(item.get('submission_timestamp', 'N/A')))

                submission_text = (
                    f"📝 *Proposal:* {proposal_title} \\(ID: {proposal_id_str}\\)\n"
                    f"   Your Response: {user_response}\n"
                    f"   Status: {proposal_status}\n"
                    f"   Outcome: {proposal_outcome}\n"
                    f"   Submitted: {submission_timestamp}\n"
                    f"\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\\-\n" # Doubled backslashes for hyphens
                )
                
                if len(current_message) + len(submission_text) > 4096:
                    response_messages.append(current_message)
                    current_message = "Continuing your submission history:\n\n" # Header for subsequent messages
                current_message += submission_text
            
            response_messages.append(current_message) # Add the last message part

            for i, message_part in enumerate(response_messages):
                if i == 0 and len(response_messages) > 1:
                     # Already handled by initial message or continuation header
                    pass # First part might already have the main header
                elif i > 0:
                    # Subsequent messages already have "Continuing..." header
                    pass 
                await update.message.reply_text(message_part, parse_mode=ParseMode.MARKDOWN_V2)

        except Exception as e:
            logger.error(f"Error processing /my_votes for user {user_id}: {e}", exc_info=True)
            if update.message:
                await update.message.reply_text("Sorry, something went wrong while fetching your history. Please try again later.")
