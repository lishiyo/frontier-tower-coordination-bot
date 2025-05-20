import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from telegram.constants import ParseMode

from app.persistence.database import AsyncSessionLocal
from app.core.proposal_service import ProposalService
from app.core.context_service import ContextService
from app.config import ConfigService
from app.utils.telegram_utils import escape_markdown_v2
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Tuple, Any
# Add any other necessary imports from the original command_handlers.py, like services or models if directly used.

logger = logging.getLogger(__name__)

# Helper Function for fetching document content
async def _get_and_format_document_for_display(document_id: int, session: AsyncSession) -> Tuple[Optional[str], bool]:
    """
    Fetches document content and indicates if found.
    Returns a tuple: (raw_content_string_or_none, found_boolean).
    """
    # ContextService needs to be initialized.
    # Since get_document_content doesn't use LLM or VectorDB services, we can pass None.
    context_service = ContextService(
        db_session=session,
        llm_service=None, 
        vector_db_service=None
    )
    
    raw_content = await context_service.get_document_content(document_id)
    
    if raw_content:
        return raw_content, True
    return None, False

# New Helper Function for displaying document content
async def _display_document_content(doc_id: int, message_destination: Any, log_prefix: str = "", user_id: Optional[int] = None) -> bool:
    """
    Shared helper to fetch and display document content to a given message destination.
    
    Args:
        doc_id: The document ID to display
        message_destination: An object with reply_text method (like update.message or query.message)
        log_prefix: Optional prefix for log messages
        user_id: Optional user ID for logging purposes
        
    Returns:
        bool: True if document was found and displayed, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            raw_content, found = await _get_and_format_document_for_display(doc_id, session)

        if found and raw_content:
            display_content = escape_markdown_v2(raw_content)
            max_length = 4096
            
            message_header = f"Content for Document ID {doc_id}:\n\n"
            
            if len(display_content) <= (max_length - len(message_header)):
                await message_destination.reply_text(f"{message_header}{display_content}", parse_mode=ParseMode.MARKDOWN_V2)
            else:
                await message_destination.reply_text(f"Displaying content for Document ID {doc_id} \\(truncated due to length\\):", parse_mode=ParseMode.MARKDOWN_V2)
                for i in range(0, len(display_content), max_length):
                    chunk = display_content[i:i + max_length]
                    await message_destination.reply_text(chunk, parse_mode=ParseMode.MARKDOWN_V2)
            if user_id:
                logger.info(f"{log_prefix} User {user_id} viewed content of document {doc_id}.")
            return True
        else:
            await message_destination.reply_text(f"Could not retrieve content for Document ID {doc_id}\\. It might not exist or have no content\\.")
            if user_id:
                logger.warning(f"{log_prefix} User {user_id} failed to view content for document {doc_id}.")
            return False
    except Exception as e:
        logger.error(f"{log_prefix} Error processing doc_id {doc_id}: {e}", exc_info=True)
        await message_destination.reply_text("Sorry, I couldn't retrieve the document at the moment.")
        return False

async def view_document_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the raw content of a specific document using the helper function."""
    if not update.effective_user or not update.message:
        logger.warning("view_document_content_command called without effective_user or message.")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /view_doc <document_id>")
        return

    try:
        document_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid Document ID. It must be a number.")
        return

    # Use shared helper function
    await _display_document_content(
        doc_id=document_id,
        message_destination=update.message,
        log_prefix="view_document_content_command:",
        user_id=update.effective_user.id
    )

async def view_docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /view_docs command with various arguments."""
    if not update.effective_user or not update.message:
        logger.warning("view_docs_command called without effective_user or message.")
        return

    args = context.args
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        cfg_service = ConfigService()
        proposal_service = ProposalService(db_session=session)
        # Ensure LLMService and VectorDBService are correctly initialized if ContextService needs them
        # For list_documents_for_proposal, they are likely not needed.
        llm_service_instance = None # Or initialize properly if needed elsewhere
        vector_db_service_instance = None # Or initialize properly if needed elsewhere
        context_service = ContextService(db_session=session, llm_service=llm_service_instance, vector_db_service=vector_db_service_instance)

        if not args: # /view_docs (no arguments)
            logger.info(f"User {user_id} requested /view_docs (no args).")
            target_channel_id = cfg_service.get_target_channel_id()
            if target_channel_id:
                # Attempt to get channel name if possible (future enhancement)
                await update.message.reply_text(f"Proposals are currently managed in channel: {target_channel_id}. Use `/view_docs <channel_id>` to list all proposals for the channel.")
            else:
                await update.message.reply_text("The bot is not currently configured with a default target proposal channel.")
            return

        first_arg = args[0]
        
        try:
            # Attempt to parse as an integer first
            potential_id = int(first_arg)

            if potential_id > 0: # Proposal IDs are positive integers
                logger.info(f"User {user_id} requested /view_docs with potential proposal_id: {potential_id}")
                # Check if it's a valid proposal and list its documents
                documents = await context_service.list_documents_for_proposal(potential_id)
                if documents:
                    doc_lines = [f"Documents for Proposal ID {potential_id}:"]
                    for doc in documents:
                        doc_lines.append(f"  - ID: {doc.id}, Title: {doc.title or 'N/A'}")
                        
                    # add a line about using `/view_doc <document_id>` to see the doc in detail
                    doc_lines.append(f"\nUse `/view_doc <document_id>` to see the doc in detail.")
                    await update.message.reply_text("\n".join(doc_lines))
                    return
                else:
                    # It's a positive integer, but either not a proposal or a proposal with no documents.
                    # Check if the proposal itself exists to give a more specific message.
                    proposal_exists = await proposal_service.proposal_repository.get_proposal_by_id(potential_id)
                    if proposal_exists:
                        await update.message.reply_text(f"No documents found for Proposal ID {potential_id}.")
                        return
                    else:
                        # Positive int, but not a proposal ID. It might be an invalid ID or a numeric channel string.
                        # Fall through to treat as channel_id string.
                        logger.info(f"Positive integer {potential_id} is not a known proposal ID. Will attempt to treat '{first_arg}' as a channel identifier.")
                        pass # Fall through to channel_id string logic
            else:
                # It's a non-positive integer (e.g., a typical Telegram channel ID like -100...). Treat as channel_id.
                logger.info(f"Argument '{first_arg}' (parsed as {potential_id}) is non-positive. Treating as channel identifier.")
                pass # Fall through to channel_id string logic
        
        except ValueError:
            # Not an integer, so must be a string channel_id (or invalid argument).
            logger.info(f"Argument '{first_arg}' is not an integer. Treating as channel identifier.")
            pass # Fall through to channel_id string logic

        # If we reached here, it's either a string, a non-positive int, or a positive int not recognized as a proposal_id.
        # Treat first_arg as a channel_id string for listing proposals.
        channel_id_arg_str = str(first_arg)
        logger.info(f"User {user_id} attempting to list proposals for channel/identifier: {channel_id_arg_str}")
        
        proposals_list = await proposal_service.list_proposals_by_channel(channel_id_arg_str) # Renamed variable to avoid conflict
        if proposals_list:
            proposal_lines = [f"Proposals for channel/identifier '{channel_id_arg_str}':"]
            for prop in proposals_list:
                status_display = prop.status.value if hasattr(prop.status, 'value') else str(prop.status)
                proposal_lines.append(f"  - ID: {prop.id}, Title: {prop.title}, Status: {status_display}")
            
            # Add a line about using `view_docs <proposal_id>` to view the documents for a proposal
            proposal_lines.append(f"\nUse `/view_docs <proposal_id>` to view the documents for a proposal.")
            
            await update.message.reply_text("\n".join(proposal_lines))
        else:
            await update.message.reply_text(f"No proposals found for channel/identifier '{channel_id_arg_str}', or it's not a recognized proposal ID or channel. Use `/view_docs` to list all channel ids.")

async def view_doc_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the callback query from 'View Source' buttons by using the shared helper function."""
    query = update.callback_query
    await query.answer() # Acknowledge the callback

    callback_data = query.data
    logger.info(f"view_doc_button_callback received callback_data: {callback_data}")

    if not callback_data or not callback_data.startswith("/view_doc "):
        logger.warning(f"Invalid callback_data received: {callback_data}")
        if query.message: 
            await query.message.reply_text("Sorry, there was an error processing this action.")
        return

    try:
        doc_id_str = callback_data.split("/view_doc ")[1]
        doc_id = int(doc_id_str)
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing doc_id from callback_data '{callback_data}': {e}")
        if query.message:
            await query.message.reply_text("Sorry, there was an error processing this action (invalid document ID format).")
        return

    # Use shared helper function if message exists
    if query.message:
        await _display_document_content(
            doc_id=doc_id,
            message_destination=query.message,
            log_prefix="view_doc_button_callback:"
        )

# TODO: Move other document-related commands here:
# - add_doc_command
# - edit_doc_command
# - delete_doc_command
# - ask_command (parts of it, or if it becomes too document-centric) 