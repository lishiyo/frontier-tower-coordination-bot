import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler
from typing import List # Minimal imports from typing
import telegram.ext.filters as filters # For PTB V20+
from telegram.constants import ParseMode

from app.core.user_service import UserService
from app.persistence.database import AsyncSessionLocal
from app.persistence.models.proposal_model import ProposalType, ProposalStatus
from app.config import ConfigService
from app.telegram_handlers.conversation_defs import (
    COLLECT_TITLE, COLLECT_DESCRIPTION, COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, ASK_DURATION, 
    USER_DATA_PROPOSAL_PARTS, USER_DATA_PROPOSAL_TITLE, USER_DATA_PROPOSAL_DESCRIPTION,
    USER_DATA_PROPOSAL_TYPE, USER_DATA_PROPOSAL_OPTIONS, USER_DATA_DEADLINE_DATE,
    USER_DATA_TARGET_CHANNEL_ID, USER_DATA_CURRENT_CONTEXT, ASK_CONTEXT, PROPOSAL_TYPE_CALLBACK,
    PROPOSAL_FILTER_OPEN, PROPOSAL_FILTER_CLOSED,
    SELECT_EDIT_ACTION, EDIT_TITLE, EDIT_DESCRIPTION, EDIT_OPTIONS, CONFIRM_EDIT_PROPOSAL,
    USER_DATA_EDIT_PROPOSAL_ID, USER_DATA_EDIT_PROPOSAL_ORIGINAL, USER_DATA_EDIT_CHANGES
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
from app.core.proposal_service import ProposalService
from app.utils import telegram_utils

logger = logging.getLogger(__name__)

# Define states for the /proposals conversation if needed for the base command
ASK_PROPOSAL_STATUS_FILTER = 1

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

async def proposals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /proposals [open|closed] command, or prompts with buttons if no args."""
    if not update.effective_user or not update.message:
        logger.warning("proposals_command called without effective_user or message.")
        if update.message:
            await update.message.reply_text("Could not get your user details for this command.")
        return

    args = context.args
    chat_id = update.message.chat_id

    if not args:
        keyboard = [
            [InlineKeyboardButton("Open Proposals", callback_data=PROPOSAL_FILTER_OPEN)],
            [InlineKeyboardButton("Closed Proposals", callback_data=PROPOSAL_FILTER_CLOSED)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Which proposals would you like to see?", reply_markup=reply_markup
        )
        return

    filter_status_str = args[0].lower()
    status_to_fetch = None
    display_title = ""

    if filter_status_str == "open":
        status_to_fetch = ProposalStatus.OPEN
        display_title = "Open Proposals"
    elif filter_status_str == "closed":
        status_to_fetch = ProposalStatus.CLOSED
        display_title = "Closed Proposals"
    else:
        escaped_arg = telegram_utils.escape_markdown_v2(args[0])
        await update.message.reply_text(
            f"Unknown filter: {escaped_arg}\. Please use 'open' or 'closed', or use /proposals to get selection buttons\."
        )
        return

    async with AsyncSessionLocal() as session:
        proposal_service = ProposalService(session)
        if status_to_fetch is None: 
            logger.error(f"proposals_command: status_to_fetch is None for filter '{filter_status_str}'")
            await update.message.reply_text("An unexpected error occurred filtering proposals.")
            return
        
        proposals_data = await proposal_service.list_proposals_by_status(status_to_fetch.value)

    full_message = f"*{telegram_utils.escape_markdown_v2(display_title)}:*\n\n"
    if not proposals_data:
        full_message += "No proposals found\."
    else:
        message_parts = []
        for prop_data in proposals_data:
            title_escaped = telegram_utils.escape_markdown_v2(prop_data['title'])
            channel_id_str = str(prop_data['target_channel_id'])
            channel_message_id = prop_data.get('channel_message_id')
            
            channel_display = f"Channel ID: `{telegram_utils.escape_markdown_v2(channel_id_str)}`"
            if channel_message_id:
                link = telegram_utils.create_telegram_message_link(channel_id_str, channel_message_id)
                if link:
                    escaped_link_text = telegram_utils.escape_markdown_v2(f"Channel: {channel_id_str}")
                    # Link itself should not be Markdown escaped
                    channel_display = f"[{escaped_link_text}]({link})"
                else: # Fallback if link couldn't be formed, but message_id exists
                    channel_display = f"Channel ID: `{telegram_utils.escape_markdown_v2(channel_id_str)}` (msg: {channel_message_id})"

            part = f"\\- *ID:* `{prop_data['id']}` *Title:* {title_escaped}\n"
            part += f"  {channel_display}\n"
    
            if status_to_fetch == ProposalStatus.OPEN:
                deadline_escaped = telegram_utils.escape_markdown_v2(str(prop_data.get('deadline_date', 'N/A')))
                part += f"  *Voting ends:* {deadline_escaped}\n"
            elif status_to_fetch == ProposalStatus.CLOSED:
                outcome_display = prop_data.get('outcome', 'Not Processed')
                outcome_escaped = telegram_utils.escape_markdown_v2(outcome_display)
                closed_date_display = prop_data.get('closed_date', 'N/A')
                closed_date_escaped = telegram_utils.escape_markdown_v2(closed_date_display)
                part += f"  *Closed on:* {closed_date_escaped}\n"
                part += f"  *Outcome:* {outcome_escaped}\n"
            message_parts.append(part)
        full_message += "\n".join(message_parts)

    if not full_message.strip():
        logger.warning(f"Formatted message for {display_title} is empty. Defaulting text.")
        full_message = "No proposals found or an error occurred generating the list\."

    await telegram_utils.send_message_in_chunks(context, chat_id=chat_id, text=full_message, parse_mode=ParseMode.MARKDOWN_V2)

# TODO: Add other proposal-related commands here if any (e.g., /edit_proposal, /cancel_proposal)

# TODO: Move other proposal-related command handlers here:
# - Handler for /proposals open/closed
# - Handler for /edit_proposal
# - Handler for /cancel_proposal (if different from generic cancel_conversation)

# --- Edit Proposal Conversation --- #

async def edit_proposal_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"User {update.effective_user.id} initiated /edit_proposal command.")
    if not update.effective_user or not update.message:
        if update.message: await update.message.reply_text("Cannot identify user.")
        return ConversationHandler.END

    context.user_data[USER_DATA_EDIT_PROPOSAL_ID] = None
    context.user_data[USER_DATA_EDIT_PROPOSAL_ORIGINAL] = None
    context.user_data[USER_DATA_EDIT_CHANGES] = {}

    if not context.args:
        keyboard = [
            [InlineKeyboardButton("Show My Proposals", callback_data="my_proposals_for_edit_prompt")] # Use a unique callback
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Which proposal would you like to edit? Use `/my_proposals` to see your proposals, then use `/edit_proposal <proposal_id>`.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END # End conversation if no ID is provided initially

    try:
        proposal_id_to_edit = int(context.args[0])
        context.user_data[USER_DATA_EDIT_PROPOSAL_ID] = proposal_id_to_edit
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Invalid proposal ID. Please provide a numeric ID. Use `/my_proposals` to find the correct ID."
        )
        return ConversationHandler.END

    async with AsyncSessionLocal() as session:
        proposal_service = ProposalService(session, bot_app=context.application) # Pass bot_app
        proposal, error = await proposal_service.get_proposal_for_editing(proposal_id_to_edit, update.effective_user.id)

        if error:
            await update.message.reply_text(error)
            return ConversationHandler.END
        
        if proposal:
            context.user_data[USER_DATA_EDIT_PROPOSAL_ORIGINAL] = {
                "title": proposal.title,
                "description": proposal.description,
                "options": proposal.options,
                "proposal_type": proposal.proposal_type
            }
            
            actions = ["Title", "Description"]
            if proposal.proposal_type == ProposalType.MULTIPLE_CHOICE.value:
                actions.append("Options")
            
            keyboard = [[InlineKeyboardButton(action, callback_data=f"edit_action_{action.lower()}")] for action in actions]
            keyboard.append([InlineKeyboardButton("Finish Editing (Show Summary)", callback_data="edit_action_finish")])
            keyboard.append([InlineKeyboardButton("Cancel Edit", callback_data="edit_action_cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"Editing Proposal ID: {proposal_id_to_edit} \\- {telegram_utils.escape_markdown_v2(proposal.title)}\nWhat would you like to change?",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return SELECT_EDIT_ACTION
        else:
            # Should be caught by error above, but as a fallback
            await update.message.reply_text("Could not load proposal for editing.")
            return ConversationHandler.END

async def handle_select_edit_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data
    context.user_data['_current_edit_action'] = action # Store which part we are editing sequentially for "All"

    if action == "edit_action_title" or action == "edit_action_all":
        await query.edit_message_text(text="Please send the new title for the proposal.")
        return EDIT_TITLE
    elif action == "edit_action_description":
        await query.edit_message_text(text="Please send the new description for the proposal.")
        return EDIT_DESCRIPTION
    elif action == "edit_action_options":
        original_proposal_type = context.user_data.get(USER_DATA_EDIT_PROPOSAL_ORIGINAL, {}).get("proposal_type")
        if original_proposal_type == ProposalType.MULTIPLE_CHOICE.value:
            await query.edit_message_text(text="Please send the new options, separated by commas.")
            return EDIT_OPTIONS
        else:
            await query.edit_message_text(text="This proposal is free-form and does not have editable options.")
            # Go back to selection or end if they only chose options wrongly
            # For simplicity, returning to selection for now
            # TODO: Re-prompt with SELECT_EDIT_ACTION keyboard.
            # This requires storing and resending the original message with keyboard.
            # For now, just ending this path if invalid.
            current_proposal_id = context.user_data.get(USER_DATA_EDIT_PROPOSAL_ID)
            await query.message.reply_text(f"Returning to edit options for proposal {current_proposal_id}.") 
            # Need to re-send the SELECT_EDIT_ACTION prompt here. This part is tricky with edit_message_text.
            # Let's just allow them to cancel or send another command.
            return ConversationHandler.END # Simplified for now

    elif action == "edit_action_finish":
        # This will now call prompt_confirm_edit_proposal, which handles the no-changes case.
        return await prompt_confirm_edit_proposal(update, context)
    # Removed the specific edit_prop_finish_no_change as prompt_confirm_edit_proposal handles no changes.
    # The finish button should always lead to the confirmation/summary step.

    # elif action == "edit_action_cancel": # This is handled by fallbacks
    #     await query.edit_message_text(text="Proposal editing cancelled.")
    #     return ConversationHandler.END
    
    logger.warning(f"handle_select_edit_action: Unknown action '{action}'. This might be okay if it's 'edit_action_cancel' handled by fallback.")
    # Don't send error message for cancel, as it might be a fallback race condition or normal flow.
    # await query.edit_message_text(text="Sorry, an unexpected error occurred or unknown action.")
    # Let fallbacks handle cancel. If it's truly unknown and not cancel, it will end via this path.
    return ConversationHandler.END

async def handle_edit_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_title = update.message.text.strip()
    if not new_title:
        await update.message.reply_text("Title cannot be empty. Please send a valid title, or /cancel_edit.")
        return EDIT_TITLE
    
    context.user_data[USER_DATA_EDIT_CHANGES]['title'] = new_title
    await update.message.reply_text(f"New title set to: '{new_title}'")

    current_edit_action = context.user_data.get('_current_edit_action')
    if current_edit_action == "edit_action_all":
        await update.message.reply_text("Now, please send the new description for the proposal.")
        return EDIT_DESCRIPTION
    else:
        # Ask to confirm or select another field
        # For simplicity, directly go to confirm after any single edit for now
        return await prompt_confirm_edit_proposal(update, context)

async def handle_edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_description = update.message.text.strip()
    if not new_description:
        await update.message.reply_text("Description cannot be empty. Please send a valid description, or /cancel_edit.")
        return EDIT_DESCRIPTION

    context.user_data[USER_DATA_EDIT_CHANGES]['description'] = new_description
    await update.message.reply_text(f"New description set.") # Don't echo back potentially long desc

    current_edit_action = context.user_data.get('_current_edit_action')
    original_proposal_type = context.user_data.get(USER_DATA_EDIT_PROPOSAL_ORIGINAL, {}).get("proposal_type")

    if current_edit_action == "edit_action_all":
        if original_proposal_type == ProposalType.MULTIPLE_CHOICE.value:
            await update.message.reply_text("Now, please send the new options, separated by commas.")
            return EDIT_OPTIONS
        else: # Freeform, skip options
            return await prompt_confirm_edit_proposal(update, context)
    else:
        return await prompt_confirm_edit_proposal(update, context)

async def handle_edit_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_options_str = update.message.text.strip()
    if not new_options_str:
        await update.message.reply_text("Options cannot be empty for a multiple-choice proposal. Please provide options or /cancel_edit.")
        return EDIT_OPTIONS
    
    new_options_list = [opt.strip() for opt in new_options_str.split(',') if opt.strip()]
    if not new_options_list:
        await update.message.reply_text("No valid options provided. Please list options separated by commas, or /cancel_edit.")
        return EDIT_OPTIONS

    context.user_data[USER_DATA_EDIT_CHANGES]['options'] = new_options_list
    await update.message.reply_text(f"New options set to: {', '.join(new_options_list)}")
    
    # Whether coming from "edit_action_all" or "edit_action_opts", options are last for MC
    return await prompt_confirm_edit_proposal(update, context)

async def prompt_confirm_edit_proposal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    changes = context.user_data.get(USER_DATA_EDIT_CHANGES, {})
    original = context.user_data.get(USER_DATA_EDIT_PROPOSAL_ORIGINAL, {})
    proposal_id = context.user_data.get(USER_DATA_EDIT_PROPOSAL_ID)

    query = update.callback_query
    action = query.data if query else None

    # If this function is called via a callback button (e.g., "Finish Editing")
    # and no changes were made, notify the user and end.
    if query and action == "edit_action_finish" and not changes:
        await query.answer() # Answer callback query first
        await query.edit_message_text("No changes were made. Finishing edit process.")
        return ConversationHandler.END
    # If somehow called without changes (e.g., directly after a single edit that was then cleared, though less likely now)
    # or if called by a message update (not callback) and no changes exist.
    elif not changes:
        reply_method = None
        if update.message:
            reply_method = update.message.reply_text
        elif query and query.message: # Fallback if called by callback but not 'edit_action_finish'
            reply_method = query.message.reply_text
        
        if reply_method:
            await reply_method("No changes were made. Finishing edit process.")
        else:
            logger.warning("prompt_confirm_edit_proposal: No changes and no clear way to reply.")
        return ConversationHandler.END

    summary_parts = [f"Summary of changes for proposal ID {proposal_id}:"]
    if 'title' in changes:
        summary_parts.append(f"  Title: '{telegram_utils.escape_markdown_v2(original.get('title'))}' \-\> '{telegram_utils.escape_markdown_v2(changes['title'])}'")
    if 'description' in changes:
        summary_parts.append(f"  Description: Changed \(new version will be applied\)")
    if 'options' in changes:
        original_opts_str = ", ".join(original.get('options', []))
        new_opts_str = ", ".join(changes['options'])
        summary_parts.append(f"  Options: '{telegram_utils.escape_markdown_v2(original_opts_str)}' \-\> '{telegram_utils.escape_markdown_v2(new_opts_str)}'")
    
    summary_text = "\n".join(summary_parts)
    summary_text += "\n\nDo you want to apply these changes?"

    keyboard = [
        [InlineKeyboardButton("Yes, Apply Changes", callback_data="confirm_edit_yes")],
        [InlineKeyboardButton("No, Discard Changes", callback_data="confirm_edit_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Ensure message is sent from update.message if available, or context.bot if from callback
    if update.message:
        await update.message.reply_text(summary_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    elif update.callback_query and update.callback_query.message: # If called after a callback query message edit
        # We might need to send a new message here, as edit_message_text was used before.
        await context.bot.send_message(chat_id=update.effective_chat.id, text=summary_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        logger.error("prompt_confirm_edit_proposal: Cannot find a message to reply to or a chat to send to.")
        return ConversationHandler.END
        
    return CONFIRM_EDIT_PROPOSAL

async def handle_confirm_edit_proposal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    decision = query.data

    proposal_id = context.user_data.get(USER_DATA_EDIT_PROPOSAL_ID)
    changes = context.user_data.get(USER_DATA_EDIT_CHANGES, {})

    if decision == "confirm_edit_yes":
        if not changes or not proposal_id:
            await query.edit_message_text("No changes to apply or proposal ID missing. Edit cancelled.")
            return ConversationHandler.END

        async with AsyncSessionLocal() as session:
            proposal_service = ProposalService(session, bot_app=context.application)
            updated_proposal, error_msg = await proposal_service.edit_proposal_details(
                proposal_id=proposal_id,
                proposer_telegram_id=update.effective_user.id,
                new_title=changes.get('title'),
                new_description=changes.get('description'),
                new_options=changes.get('options')
            )
            if error_msg:
                await query.edit_message_text(f"Error applying changes: {error_msg}")
                return ConversationHandler.END
            
            if updated_proposal:
                await session.commit() # Commit changes here as service layer doesn't
                
                base_text_segment = " has been successfully updated."
                proposal_identifier_text = f"Proposal ID {updated_proposal.id}"
                
                # Default message if no link can be formed
                confirmation_message = f"{proposal_identifier_text}{base_text_segment}" # Plain text by default
                current_parse_mode = None

                if updated_proposal.target_channel_id and updated_proposal.channel_message_id:
                    message_url = telegram_utils.create_telegram_message_link(
                        updated_proposal.target_channel_id,
                        updated_proposal.channel_message_id
                    )
                        
                    if message_url:
                        escaped_link_text = telegram_utils.escape_markdown_v2(proposal_identifier_text)
                        escaped_base_text = telegram_utils.escape_markdown_v2(base_text_segment)
                        # The URL itself (message_url) should NOT be escaped for MarkdownV2 link syntax
                        confirmation_message = f"[{escaped_link_text}]({message_url}){escaped_base_text}"
                        current_parse_mode = ParseMode.MARKDOWN_V2
                
                await query.edit_message_text(confirmation_message, parse_mode=current_parse_mode)
                
                # Update message in channel
                if updated_proposal.target_channel_id and updated_proposal.channel_message_id:
                    try:
                        # We need the proposer User object to format the message correctly
                        proposer_user = await proposal_service.user_service.get_user_by_telegram_id(updated_proposal.proposer_telegram_id)
                        if not proposer_user:
                             logger.error(f"Could not find proposer user {updated_proposal.proposer_telegram_id} for updating channel message of proposal {updated_proposal.id}")
                        else:
                            new_channel_message_text = telegram_utils.format_proposal_message(updated_proposal, proposer_user)
                            reply_markup_channel = None
                            if updated_proposal.proposal_type == ProposalType.MULTIPLE_CHOICE.value and updated_proposal.options:
                                reply_markup_channel = telegram_utils.create_proposal_options_keyboard(updated_proposal.id, updated_proposal.options)
                            elif updated_proposal.proposal_type == ProposalType.FREE_FORM.value and context.bot.username:
                                reply_markup_channel = telegram_utils.get_free_form_submit_button(updated_proposal.id, context.bot.username)

                            await context.bot.edit_message_text(
                                chat_id=updated_proposal.target_channel_id,
                                message_id=updated_proposal.channel_message_id,
                                text=new_channel_message_text,
                                reply_markup=reply_markup_channel,
                                parse_mode=ParseMode.MARKDOWN_V2
                            )
                            logger.info(f"Updated message for proposal {updated_proposal.id} in channel {updated_proposal.target_channel_id}.")
                    except Exception as e:
                        logger.error(f"Failed to update message in channel for proposal {updated_proposal.id}: {e}", exc_info=True)
                        # If query.message is not available (e.g. message too old to edit for bot), send new message
                        try:
                            await query.message.reply_text("Proposal details updated, but failed to update the message in the channel. Please check manually.")
                        except AttributeError: # If query.message is None
                             await context.bot.send_message(chat_id=update.effective_chat.id, text="Proposal details updated, but failed to update the message in the channel. Please check manually.")
            else:
                # This case is theoretically covered by error_msg from edit_proposal_details
                await query.edit_message_text("Failed to update proposal for an unknown reason.")
        
    elif decision == "confirm_edit_no":
        await query.edit_message_text("Changes discarded. Proposal not modified.")
    else:
        logger.warning(f"handle_confirm_edit_proposal: Unknown decision '{decision}'.")
        await query.edit_message_text("Invalid confirmation. Edit cancelled.")

    # Clean up user_data
    for key in [USER_DATA_EDIT_PROPOSAL_ID, USER_DATA_EDIT_PROPOSAL_ORIGINAL, USER_DATA_EDIT_CHANGES, '_current_edit_action']:
        if key in context.user_data: del context.user_data[key]
    return ConversationHandler.END

async def cancel_edit_proposal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the proposal editing conversation."""
    logger.info(f"User {update.effective_user.id} cancelled proposal editing.")
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text="Proposal editing cancelled.")
    elif update.message:
        await update.message.reply_text("Proposal editing cancelled.")
    
    # Clear user_data related to this conversation
    for key in [USER_DATA_EDIT_PROPOSAL_ID, USER_DATA_EDIT_PROPOSAL_ORIGINAL, USER_DATA_EDIT_CHANGES]:
        if key in context.user_data:
            del context.user_data[key]
            
    return ConversationHandler.END

edit_proposal_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("edit_proposal", edit_proposal_command_entry)],
    states={
        SELECT_EDIT_ACTION: [
            CallbackQueryHandler(handle_select_edit_action, pattern="^edit_action_")
        ],
        EDIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_title)],
        EDIT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_description)],
        EDIT_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_options)],
        CONFIRM_EDIT_PROPOSAL: [
            CallbackQueryHandler(handle_confirm_edit_proposal, pattern="^confirm_edit_(yes|no)$")
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_edit_proposal, pattern="^edit_action_cancel$"),
        CommandHandler("cancel", cancel_edit_proposal) # Generic cancel command
    ],
    name="edit_proposal_conversation",
    # persistent=False # Consider persistence if needed
)

async def cancel_proposal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /cancel_proposal command.
    Allows a proposer to cancel their own open proposal.
    """
    if not update.effective_user or not update.message:
        logger.warning("cancel_proposal_command called without effective_user or message.")
        if update.message:
            await update.message.reply_text("Could not get your user details for this command.")
        return

    user_id = update.effective_user.id
    # chat_id = update.message.chat_id # Not strictly needed if all replies are DMs

    if not context.args:
        # No proposal_id provided
        keyboard = [
            [InlineKeyboardButton("Show My Proposals", callback_data="my_proposals_for_edit_prompt")]
            # Using a unique callback to potentially handle this prompt if needed, or just for clarity.
            # Alternatively, could be same as edit: "my_proposals_for_edit_prompt"
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Which proposal would you like to cancel? \n"
            "Use `/my_proposals` to see your proposals, then use `/cancel_proposal <proposal_id>`\\.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        proposal_id_to_cancel = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Invalid Proposal ID format. Please use `/cancel_proposal <ID>` where ID is a number."
        )
        return

    async with AsyncSessionLocal() as session:
        # Ensure bot_app is passed to ProposalService if it's used for sending messages (it is for editing channel message)
        proposal_service = ProposalService(db_session=session, bot_app=context.application)
        success, message = await proposal_service.cancel_proposal_by_proposer(
            proposal_id=proposal_id_to_cancel,
            user_telegram_id=user_id
        )
        # Commit is handled within cancel_proposal_by_proposer if successful

    await update.message.reply_text(message)

# TODO: Move other proposal-related command handlers here:
# - Handler for /proposals open/closed
# - Handler for /edit_proposal (already here as a conversation)
# - Handler for /cancel_proposal (NOW ADDED!) 