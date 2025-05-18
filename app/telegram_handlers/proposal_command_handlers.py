import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler
from typing import List # Minimal imports from typing
import telegram.ext.filters as filters # For PTB V20+

from app.core.user_service import UserService
from app.persistence.database import AsyncSessionLocal
from app.persistence.models.proposal_model import ProposalType
from app.config import ConfigService
from app.telegram_handlers.conversation_defs import (
    COLLECT_TITLE, COLLECT_DESCRIPTION, COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, ASK_DURATION, 
    USER_DATA_PROPOSAL_PARTS, USER_DATA_PROPOSAL_TITLE, USER_DATA_PROPOSAL_DESCRIPTION,
    USER_DATA_PROPOSAL_TYPE, USER_DATA_PROPOSAL_OPTIONS, USER_DATA_DEADLINE_DATE,
    USER_DATA_TARGET_CHANNEL_ID, USER_DATA_CURRENT_CONTEXT, ASK_CONTEXT, PROPOSAL_TYPE_CALLBACK
)
from app.telegram_handlers.message_handlers import (
    handle_collect_title,
    handle_collect_description,
    handle_collect_options, 
    handle_ask_duration,
    handle_ask_context
)
from app.telegram_handlers.callback_handlers import handle_collect_proposal_type_callback
from app.telegram_handlers.command_handlers import cancel_conversation # Assuming cancel_conversation remains in core command_handlers

logger = logging.getLogger(__name__)

async def propose_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Starts the proposal creation conversation.
    Parses initial arguments from /propose command if any.
    """
    logger.info(f"User {update.effective_user.id if update.effective_user else 'Unknown'} initiated /propose command.")
    if not update.effective_user or not update.message: # Added check for update.message
        logger.warning("propose_command_entry called without effective_user or message.")
        # Try to send reply if possible, otherwise just end
        if update.message: 
            await update.message.reply_text("Sorry, I can't identify you to create a proposal.")
        return ConversationHandler.END

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        await user_service.register_user_interaction(
            telegram_id=update.effective_user.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
        await session.commit() 

    context.user_data[USER_DATA_CURRENT_CONTEXT] = {}
    context.user_data[USER_DATA_PROPOSAL_TITLE] = None
    context.user_data[USER_DATA_PROPOSAL_DESCRIPTION] = None
    context.user_data[USER_DATA_PROPOSAL_TYPE] = None
    context.user_data[USER_DATA_PROPOSAL_OPTIONS] = None
    context.user_data[USER_DATA_TARGET_CHANNEL_ID] = ConfigService.get_target_channel_id() 
    context.user_data[USER_DATA_DEADLINE_DATE] = None

    args_str = " ".join(context.args) if context.args else ""

    # Simple parsing for initial parts based on ";"
    # More sophisticated parsing (e.g., LLM-based for unstructured input) could be added here
    parsed_parts = [p.strip() for p in args_str.split(";") if p.strip()]
    context.user_data[USER_DATA_PROPOSAL_PARTS] = parsed_parts

    if parsed_parts:
        context.user_data[USER_DATA_PROPOSAL_TITLE] = parsed_parts[0]
        if len(parsed_parts) > 1:
            context.user_data[USER_DATA_PROPOSAL_DESCRIPTION] = parsed_parts[1]
        if len(parsed_parts) > 2:
            # Attempt to determine type and options from the third part
            # This is a simplification. Real logic for options/type will be in COLLECT_PROPOSAL_TYPE/COLLECT_OPTIONS
            options_or_type_str = parsed_parts[2]
            if options_or_type_str.upper() == "FREEFORM":
                context.user_data[USER_DATA_PROPOSAL_TYPE] = ProposalType.FREE_FORM.value
            else:
                # Assume multiple choice if not "FREEFORM" and options are given
                options = [opt.strip() for opt in options_or_type_str.split(",") if opt.strip()]
                if options:
                    context.user_data[USER_DATA_PROPOSAL_TYPE] = ProposalType.MULTIPLE_CHOICE.value
                    context.user_data[USER_DATA_PROPOSAL_OPTIONS] = options
    
    message_to_send = ""
    next_state = -1 # Default to an invalid state or ConversationHandler.END

    # Determine the first state based on missing information
    if not context.user_data.get(USER_DATA_PROPOSAL_TITLE):
        message_to_send = "Okay, let's create a new proposal! What would you like to name it?"
        next_state = COLLECT_TITLE
    elif not context.user_data.get(USER_DATA_PROPOSAL_DESCRIPTION):
        message_to_send = f"Got it. The title is: '{context.user_data[USER_DATA_PROPOSAL_TITLE]}'.\nNow, can you provide a brief description for it?"
        next_state = COLLECT_DESCRIPTION
    elif not context.user_data.get(USER_DATA_PROPOSAL_TYPE):
        message_to_send = (
            f"Title: '{context.user_data[USER_DATA_PROPOSAL_TITLE]}'\n"
            f"Description: '{context.user_data[USER_DATA_PROPOSAL_DESCRIPTION]}'\n\n"
            "Is this a 'multiple_choice' proposal (you'll list options) or a 'free_form' idea collection?"
        )
        next_state = COLLECT_PROPOSAL_TYPE
    elif context.user_data[USER_DATA_PROPOSAL_TYPE] == ProposalType.MULTIPLE_CHOICE.value and not context.user_data.get(USER_DATA_PROPOSAL_OPTIONS):
        message_to_send = "Please list the options for your multiple choice proposal, separated by commas."
        next_state = COLLECT_OPTIONS
    else: 
        message_to_send = "How long should this proposal be open for voting/submissions, or until when would you like to set the deadline? (e.g., '7 days', 'until May 21st at 5 PM')"
        next_state = ASK_DURATION
    
    if update.message: # Ensure there is a message to reply to
        await update.message.reply_text(message_to_send)
    else: # Should not happen if effective_user and message were present at start
        logger.error("propose_command_entry: No message to reply to when sending prompt.")
        return ConversationHandler.END
        
    return next_state

# Proposal Conversation Handler Definition
proposal_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("propose", propose_command_entry)],
    states={
        COLLECT_TITLE: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_collect_title)],
        COLLECT_DESCRIPTION: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_collect_description)],
        COLLECT_PROPOSAL_TYPE: [
            CallbackQueryHandler(handle_collect_proposal_type_callback, pattern=f"^{PROPOSAL_TYPE_CALLBACK}"),
            MessageHandler(filters.TEXT & (~filters.COMMAND), handle_collect_proposal_type_callback) 
        ],
        COLLECT_OPTIONS: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_collect_options)],
        ASK_DURATION: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_ask_duration)],
        ASK_CONTEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_ask_context)],
    },
    fallbacks=[CommandHandler("cancel", cancel_conversation)],
    # Using default per_message=False to make sure command entry points work properly
    # name="proposal_creation_conversation", # Optional: for debugging or specific handler management
    # persistent=False, # Set to True if you want to use persistence across restarts
)

# TODO: Move other proposal-related command handlers here:
# - Handler for /proposals open/closed
# - Handler for /edit_proposal
# - Handler for /cancel_proposal (if different from generic cancel_conversation) 