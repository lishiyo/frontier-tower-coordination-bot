import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from app.telegram_handlers.conversation_defs import (
    COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, ASK_DURATION,
    USER_DATA_PROPOSAL_TYPE, PROPOSAL_TYPE_CALLBACK
)
from app.persistence.models.proposal_model import ProposalType
from app.core.submission_service import SubmissionService
from app.persistence.database import AsyncSessionLocal
from app.core.user_service import UserService

# Placeholder for imports that will be needed soon:
# from app.core.services import AppServiceFactory # Or direct service instantiation

logger = logging.getLogger(__name__)

async def handle_collect_proposal_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles user's choice of proposal type from inline keyboard or direct message text."""
    query = update.callback_query
    user_response_value = None
    user_friendly_response = ""

    if query:
        await query.answer() # Acknowledge callback query
        data = query.data
        user_response_value = data.replace(PROPOSAL_TYPE_CALLBACK, "")
        
        if user_response_value == ProposalType.MULTIPLE_CHOICE.value:
            user_friendly_response = "Multiple Choice"
        elif user_response_value == ProposalType.FREE_FORM.value:
            user_friendly_response = "Free Form"
        else:
            logger.warning(f"Invalid callback data for proposal type: {data}")
            await query.edit_message_text(text="Invalid selection. Please try again.")
            # Re-prompt with keyboard
            keyboard = [
                [InlineKeyboardButton("Multiple Choice", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.MULTIPLE_CHOICE.value}")],
                [InlineKeyboardButton("Free Form", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.FREE_FORM.value}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("What type of proposal is this?", reply_markup=reply_markup)
            return COLLECT_PROPOSAL_TYPE

        await query.edit_message_text(text=f"Proposal Type: {user_friendly_response}")
    
    elif update.message and update.message.text: # Handling text input for proposal type
        text_input = update.message.text.strip().lower()
        if "multiple" in text_input or "choice" in text_input:
            user_response_value = ProposalType.MULTIPLE_CHOICE.value
            user_friendly_response = "Multiple Choice"
        elif "free" in text_input or "form" in text_input:
            user_response_value = ProposalType.FREE_FORM.value
            user_friendly_response = "Free Form"
        else:
            await update.message.reply_text("I didn't understand that proposal type. Please choose from the options, or type 'multiple choice' or 'free form'.")
            keyboard = [
                [InlineKeyboardButton("Multiple Choice", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.MULTIPLE_CHOICE.value}")],
                [InlineKeyboardButton("Free Form", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.FREE_FORM.value}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("What type of proposal is this?", reply_markup=reply_markup)
            return COLLECT_PROPOSAL_TYPE
        
        await update.message.reply_text(f"Proposal Type set to: {user_friendly_response}")

    else: # Should not happen if handlers are set up correctly
        logger.error("handle_collect_proposal_type_callback called without query or message text.")
        if update.effective_message:
             await update.effective_message.reply_text("Something went wrong. Please try selecting the proposal type again.")
        return COLLECT_PROPOSAL_TYPE

    context.user_data[USER_DATA_PROPOSAL_TYPE] = user_response_value
    logger.info(f"User {update.effective_user.id} selected proposal type: {user_response_value}")

    if user_response_value == ProposalType.MULTIPLE_CHOICE.value:
        next_message = "This will be a multiple choice proposal. Please provide the options, separated by commas (e.g., Option A, Option B, Option C)."
        next_state = COLLECT_OPTIONS
    else:  # FREE_FORM
        next_message = "This will be a free form proposal.\nHow long should this proposal be open for submissions, or until when would you like to set the deadline? (e.g., '7 days', 'until May 21st at 5 PM')"
        next_state = ASK_DURATION
    
    # Send the next prompt from the effective message (either query.message or update.message)
    if query: # If from callback, use query.message to send the next prompt to the same chat
        await query.message.reply_text(next_message)
    elif update.message: # If from text message, use update.message
        await update.message.reply_text(next_message)

    return next_state 

async def handle_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles callback queries for voting on multiple-choice proposals.
    Callback data format: vote_[proposal_id]_[option_index]
    Ensures query.answer() is called only once.
    """
    query = update.callback_query
    response_message_text = "An unexpected error occurred."
    success_for_alert = False # Determines if the final alert is for success or error

    callback_data = query.data
    if not callback_data or not callback_data.startswith("vote_"):
        logger.warning(f"handle_vote_callback received invalid data: {callback_data}")
        response_message_text = "Error: Invalid vote data received."
        await query.answer(text=response_message_text, show_alert=True)
        return

    try:
        parts = callback_data.split('_')
        if len(parts) != 3:
            raise ValueError("Callback data format is incorrect (expected 3 parts).")
        
        action_prefix, proposal_id_str, option_index_str = parts
        proposal_id = int(proposal_id_str)
        option_index = int(option_index_str)
        user_telegram_id = query.from_user.id
        user_first_name = query.from_user.first_name
        user_username = query.from_user.username

        logger.info(f"Vote received: User {user_telegram_id} selected option {option_index} for proposal {proposal_id}.")

        async with AsyncSessionLocal() as session:
            user_service = UserService(session)
            await user_service.register_user_interaction(
                telegram_id=user_telegram_id,
                username=user_username,
                first_name=user_first_name
            )
            await session.commit()

            submission_service = SubmissionService(session)
            success_for_alert, response_message_text = await submission_service.record_vote(
                proposal_id=proposal_id,
                submitter_telegram_id=user_telegram_id,
                option_index=option_index
            )

    except ValueError as ve:
        logger.error(f"Error parsing vote callback data '{callback_data}': {ve}", exc_info=True)
        response_message_text = "Error: Could not process your vote due to invalid data format."
    except Exception as e:
        logger.error(f"Error processing vote callback for data '{callback_data}': {e}", exc_info=True)
        response_message_text = "An unexpected error occurred while processing your vote. Please try again."
    
    # Single call to query.answer() at the end
    # For success, submission_service.record_vote already provides a good message.
    # For errors caught here, response_message_text is set accordingly.
    await query.answer(text=response_message_text, show_alert=True) 