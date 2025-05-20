import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from app.telegram_handlers.conversation_defs import (
    COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, ASK_DURATION,
    USER_DATA_PROPOSAL_TYPE, PROPOSAL_TYPE_CALLBACK,
    VOTE_CALLBACK_PREFIX, PROPOSAL_FILTER_CALLBACK_PREFIX,
    PROPOSAL_FILTER_OPEN, PROPOSAL_FILTER_CLOSED
)
from app.persistence.models.proposal_model import ProposalType, ProposalStatus
from app.core.submission_service import SubmissionService
from app.core.proposal_service import ProposalService
from app.persistence.database import AsyncSessionLocal
from app.core.user_service import UserService
from app.utils import telegram_utils

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
    if not callback_data or not callback_data.startswith(VOTE_CALLBACK_PREFIX):
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
            await session.commit() # Commit user interaction separately

            submission_service = SubmissionService(session)
            success_for_alert, response_message_text = await submission_service.record_vote(
                proposal_id=proposal_id,
                submitter_telegram_id=user_telegram_id,
                option_index=option_index
            )
            # record_vote now handles its own commit for the submission, so no session.commit() here for that.

    except ValueError as ve:
        logger.error(f"Error parsing vote callback data '{callback_data}': {ve}", exc_info=True)
        response_message_text = "Error: Could not process your vote due to invalid data format."
    except Exception as e:
        logger.error(f"Error processing vote callback for data '{callback_data}': {e}", exc_info=True)
        response_message_text = "An unexpected error occurred while processing your vote. Please try again."
    
    await query.answer(text=response_message_text, show_alert=True)

async def handle_proposal_filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callback query for filtering proposals (open/closed)."""
    query = update.callback_query

    if not query: # Guard clause for no callback query
        logger.error("handle_proposal_filter_callback called without callback_query.")
        return

    await query.answer() # Acknowledge callback

    if not query.data:
        logger.warning("Callback query received without data.")
        if query.message:
            try:
                await query.edit_message_text(text="Error: No action specified.")
            except Exception as e:
                logger.error(f"Error editing message (no data): {e}")
        return

    if not query.data.startswith(PROPOSAL_FILTER_CALLBACK_PREFIX):
        logger.warning(f"Invalid callback data for proposal filter: {query.data}")
        if query.message:
            try:
                await query.edit_message_text(text="Invalid selection. Please try again.")
            except Exception as e:
                logger.error(f"Error editing message (invalid prefix): {e}")
        return

    filter_type = query.data
    status_to_fetch = None
    display_title = ""

    if filter_type == PROPOSAL_FILTER_OPEN:
        status_to_fetch = ProposalStatus.OPEN
        display_title = "Open Proposals"
    elif filter_type == PROPOSAL_FILTER_CLOSED:
        status_to_fetch = ProposalStatus.CLOSED
        display_title = "Closed Proposals"
    else:
        logger.warning(f"Unknown proposal filter action: {filter_type}")
        if query.message:
            try:
                await query.edit_message_text(text="Invalid filter selected. Please try again.")
            except Exception as e:
                logger.error(f"Error editing message (unknown action): {e}")    
        return

    try:
        async with AsyncSessionLocal() as session:
            proposal_service = ProposalService(session)
            proposals_data = await proposal_service.list_proposals_by_status(status_to_fetch.value)
            
            full_message = f"*{telegram_utils.escape_markdown_v2(display_title)}:*\n\n"
            if not proposals_data:
                full_message += "No proposals found\\."
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
                            channel_display = f"[{escaped_link_text}]({link})" # Corrected: use link variable
                        else: # Fallback if link couldn't be formed, but message_id exists
                            channel_display = f"Channel ID: `{telegram_utils.escape_markdown_v2(channel_id_str)}` (msg: {channel_message_id})"

                    part = f"\\- *ID:* `{prop_data['id']}` *Title:* {title_escaped}\n"
                    part += f"  {channel_display}\n"
            
                    if status_to_fetch == ProposalStatus.OPEN:
                        deadline_escaped = telegram_utils.escape_markdown_v2(str(prop_data.get('deadline_date', 'N/A')))
                        part += f"  *Voting ends:* {deadline_escaped}\n"
                    elif status_to_fetch == ProposalStatus.CLOSED:
                        outcome_escaped = telegram_utils.escape_markdown_v2(str(prop_data.get('outcome', 'Not Processed')))
                        closed_date_escaped = telegram_utils.escape_markdown_v2(str(prop_data.get('closed_date', 'N/A')))
                        part += f"  *Closed on:* {closed_date_escaped}\n"
                        part += f"  *Outcome:* {outcome_escaped}\n"
                    message_parts.append(part)
                full_message += "\n".join(message_parts)
            
            if query.message:
                if not full_message.strip(): # Ensure message is not empty after formatting
                    logger.warning(f"Formatted message for {filter_type} is empty. Defaulting text.")
                    full_message = "No proposals found or an error occurred generating the list."
                
                await query.edit_message_text(
                    text=full_message,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            else:
                logger.warning("Callback query message does not exist, cannot edit.")

    except Exception as e:
        logger.error(f"Error processing proposal filter callback ({filter_type}): {e}", exc_info=True)
        if query.message:
            try:
                await query.edit_message_text(text="Sorry, an error occurred while fetching proposals.")
            except Exception as edit_e:
                logger.error(f"Error editing message on exception: {edit_e}")

    logger.info(f"User {query.from_user.id} viewed {filter_type} proposals via callback.")

async def handle_my_proposals_for_edit_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'My Proposals' button from the /edit_proposal prompt by displaying the user's proposals."""
    query = update.callback_query
    await query.answer()

    if not query.from_user or not query.message or not query.message.chat:
        logger.warning("handle_my_proposals_for_edit_prompt missing user/message/chat details.")
        try:
            await query.edit_message_text(text="Sorry, I couldn't retrieve the necessary details to show your proposals.")
        except Exception as e:
            logger.error(f"Error editing message in handle_my_proposals_for_edit_prompt (details missing): {e}")
        return

    user_id = query.from_user.id
    chat_id = query.message.chat.id

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        # Ensure user is registered/updated. This typically happens in command entry, but good practice here too.
        await user_service.register_user_interaction(
            telegram_id=user_id, 
            username=query.from_user.username, 
            first_name=query.from_user.first_name
        )
        # No explicit commit needed here if register_user_interaction handles its transaction
        # or if the main purpose is read-only for proposals.
        # However, my_proposals_command does commit after user registration, so let's be consistent.
        await session.commit()

        proposal_service = ProposalService(session)
        proposals_list_data = await proposal_service.list_proposals_by_proposer(user_id)

    message_text_parts = []
    if not proposals_list_data:
        message_text_parts.append("You haven't created any proposals yet\.")
    else:
        message_text_parts.append("*Your Proposals:*\n")
        for prop_data in proposals_list_data:
            title_escaped = telegram_utils.escape_markdown_v2(prop_data['title'])
            status_str = prop_data['status'].value if hasattr(prop_data['status'], 'value') else str(prop_data['status'])
            status_escaped = telegram_utils.escape_markdown_v2(status_str)
            
            proposal_type_str = prop_data['proposal_type'].value if hasattr(prop_data['proposal_type'], 'value') else str(prop_data['proposal_type'])
            type_escaped = telegram_utils.escape_markdown_v2(proposal_type_str)
            
            created_escaped = telegram_utils.escape_markdown_v2(str(prop_data['creation_date']))
            deadline_escaped = telegram_utils.escape_markdown_v2(str(prop_data['deadline_date']))
            outcome_display = prop_data.get('outcome') if prop_data.get('outcome') is not None else "N/A"
            outcome_escaped = telegram_utils.escape_markdown_v2(outcome_display)

            channel_id_str = str(prop_data['target_channel_id'])
            channel_message_id = prop_data.get('channel_message_id')
            
            channel_display = f"Channel ID: `{telegram_utils.escape_markdown_v2(channel_id_str)}`"
            if channel_message_id and channel_id_str.startswith("-100"):
                try:
                    numeric_channel_id = channel_id_str[4:]
                    link = f"https://t.me/c/{numeric_channel_id}/{channel_message_id}" 
                    escaped_link_text = telegram_utils.escape_markdown_v2(f"Channel: {channel_id_str}")
                    channel_display = f"[{escaped_link_text}]({link})"
                except Exception as e:
                    logger.error(f"Error creating channel link for my_proposals callback {channel_id_str}, {channel_message_id}: {e}")
                    channel_display = f"Channel ID: `{telegram_utils.escape_markdown_v2(channel_id_str)}` (msg: {channel_message_id})"
            elif channel_message_id:
                 channel_display = f"Chat ID: `{telegram_utils.escape_markdown_v2(channel_id_str)}` (msg: {channel_message_id})"
            
            part = (
                f"\\- *Title:* {title_escaped} \\(ID: `{prop_data['id']}`\\)\n"
                f"  Status: {status_escaped}\n"
                f"  Type: {type_escaped}\n"
                f"  {channel_display}\n"
                f"  Created: {created_escaped}\n"
                f"  Deadline: {deadline_escaped}\n"
                f"  Outcome: {outcome_escaped}\n"
            )
            message_text_parts.append(part)
    
    final_message_text = "\n".join(message_text_parts)

    try:
        # Send the list of proposals as a new message
        await context.bot.send_message(
            chat_id=chat_id,
            text=final_message_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        # Then edit the original message (that had the button)
        edited_text = "Your proposals are listed below\\. Please use the relevant command \\(e\\.g\\., `/edit_proposal <ID>` or `/cancel_proposal <ID>`\\) with the appropriate ID\\."
        await query.edit_message_text(
            text=edited_text,
            parse_mode=ParseMode.MARKDOWN_V2
            # No reply_markup needed here, as we're removing the button implicitly by not providing it.
        )
    except Exception as e:
        logger.error(f"Error sending/editing message in handle_my_proposals_for_edit_prompt: {e}", exc_info=True)
        # If sending new message failed, at least try to edit the original to give some feedback
        try:
            await query.edit_message_text(text="Could not display your proposals due to an error\. Please try `/my_proposals` directly\.")
        except Exception as e2:
            logger.error(f"Nested error editing message in handle_my_proposals_for_edit_prompt: {e2}") 

async def handle_ask_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles callbacks for 'Search for Proposals' and 'Search for Documents' buttons.
    Provides guidance on how to use the /ask command properly.
    """
    query = update.callback_query
    await query.answer()
    
    if not query.message:
        logger.warning("handle_ask_search_callback called without message.")
        return
    
    callback_data = query.data
    
    # Determine the search type based on callback data
    if callback_data == "ask_proposal_search":
        instructions = (
            "To find a proposal ID, type:\n\n"
            "/ask which proposal was about [topic]\n\n"
            "Examples:\n"
            " /ask which proposal was about budget changes\n"
            " /ask which proposals were created this month\n"
            " /ask which open proposals mention AI floor\n\n"
            "After finding the proposal, use:\n"
            " /edit_proposal [ID]\n"
            " /cancel_proposal [ID]"
        )
        # Add a keyboard to make it easier to start typing the command
        keyboard = [[InlineKeyboardButton("Close", callback_data="close_instructions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    elif callback_data == "ask_doc_search":
        instructions = (
            "To find a document ID, type:\n\n"
            "/ask which doc mentioned [topic]\n\n"
            "Examples:\n"
            " /ask which doc mentioned event planning\n"
            " /ask which document has information about guest polisy\n\n"
            "After finding the document, use:\n"
            " /view_doc [ID]"
        )
        # Add a keyboard to make it easier to start typing the command
        keyboard = [[InlineKeyboardButton("Close", callback_data="close_instructions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        logger.warning(f"Unknown ask search callback: {callback_data}")
        instructions = "Please use the /ask command followed by your search query."
        reply_markup = None
    
    try:
        await query.edit_message_text(
            text=instructions,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message in handle_ask_search_callback: {e}", exc_info=True)
        try:
            # If editing fails, try sending a new message
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=instructions,
                reply_markup=reply_markup
            )
        except Exception as e2:
            logger.error(f"Failed to send new message in handle_ask_search_callback: {e2}")

async def handle_close_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'Close' button for search instructions."""
    query = update.callback_query
    await query.answer()
    
    if query.message:
        try:
            await query.message.delete()
        except Exception as e:
            logger.error(f"Error deleting message in handle_close_instructions: {e}", exc_info=True)
            try:
                await query.edit_message_text("Instructions closed.")
            except Exception as e2:
                logger.error(f"Error editing message in handle_close_instructions: {e2}") 