import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from app.telegram_handlers.conversation_defs import (
    COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, ASK_DURATION,
    USER_DATA_PROPOSAL_TYPE, PROPOSAL_TYPE_CALLBACK
)
from app.persistence.models.proposal_model import ProposalType

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