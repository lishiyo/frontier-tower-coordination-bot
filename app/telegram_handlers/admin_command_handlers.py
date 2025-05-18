import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

# Direct imports for services needed
from app.config import ConfigService
from app.core.context_service import ContextService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.persistence.database import AsyncSessionLocal

from app.telegram_handlers.conversation_defs import ADD_GLOBAL_DOC_CONTENT, ADD_GLOBAL_DOC_TITLE

# if TYPE_CHECKING: # No longer strictly needed here if not using context.application.services
#     from app.services.main_services import MainServices

logger = logging.getLogger(__name__)

async def add_global_doc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation to add a new global document.
    Handles content provided directly with the command or prompts for it.
    """
    user_id = update.effective_user.id
    
    config_service = ConfigService() # Instantiate directly
    admin_ids = config_service.get_admin_ids()

    if user_id not in admin_ids:
        await update.message.reply_text("Access Denied: This command is for administrators only.")
        return ConversationHandler.END

    if context.args:
        doc_content_or_url = " ".join(context.args)
        context.user_data['add_global_doc_content_or_url'] = doc_content_or_url
        logger.info(f"User {user_id} initiated /add_global_doc with content: '{doc_content_or_url[:50]}...'")
        await update.message.reply_text(
            "Great! Now, please provide a title for this document."
        )
        return ADD_GLOBAL_DOC_TITLE # Go directly to asking for title
    else:
        logger.info(f"User {user_id} initiated /add_global_doc without initial content.")
        await update.message.reply_text(
            "Let's add a new global document. "
            "Please send the document content (paste text directly or provide a URL)."
        )
        return ADD_GLOBAL_DOC_CONTENT # Ask for content

async def handle_add_global_doc_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles receiving the content (text or URL) for the global document."""
    doc_content_or_url = update.message.text
    if not doc_content_or_url:
        await update.message.reply_text("Content cannot be empty. Please send the content or URL again, or /cancel.")
        return ADD_GLOBAL_DOC_CONTENT

    context.user_data['add_global_doc_content_or_url'] = doc_content_or_url
    await update.message.reply_text("Great! Now, please provide a title for this document.")
    return ADD_GLOBAL_DOC_TITLE

async def handle_add_global_doc_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles receiving the title for the global document and processes it."""
    title = update.message.text
    if not title:
        await update.message.reply_text("Title cannot be empty. Please provide a title, or /cancel.")
        return ADD_GLOBAL_DOC_TITLE

    doc_content_or_url = context.user_data.get('add_global_doc_content_or_url')

    if not doc_content_or_url:
        logger.error("doc_content_or_url not found in user_data for add_global_doc.")
        await update.message.reply_text("An error occurred. Please try starting over with /add_global_doc.")
        return ConversationHandler.END

    config_service = ConfigService() # Instantiate directly
    try:
        llm_service = LLMService()
        vector_db_service = VectorDBService()
    except AttributeError as e: # Catch if config_service.get_openai_api_key() doesn't exist
        logger.error(f"Configuration error for LLM/VectorDB service: {e}", exc_info=True)
        await update.message.reply_text("A configuration error occurred with a core service (API key missing?). Please contact an admin.")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Failed to initialize LLM or VectorDB service in admin_command_handler: {e}", exc_info=True)
        await update.message.reply_text("A configuration error occurred with a core service. Please contact an admin.")
        return ConversationHandler.END

    source_type_suffix = "_text"
    if doc_content_or_url.startswith("http://") or doc_content_or_url.startswith("https://"):
        source_type_suffix = "_url"
    
    final_source_type = f"admin_global{source_type_suffix}"

    document_id_stored = None
    try:
        async with AsyncSessionLocal() as session:
            context_service = ContextService(
                db_session=session, 
                llm_service=llm_service, 
                vector_db_service=vector_db_service
            )
            document_id_stored = await context_service.process_and_store_document(
                content_source=doc_content_or_url, 
                source_type=final_source_type, # Use the more specific source type 
                title=title,
                proposal_id=None 
            )
        if document_id_stored is not None:
            await update.message.reply_text(f"Global document '{title}' (ID: {document_id_stored}) added successfully.")
        else:
            await update.message.reply_text("Failed to add the global document. Please check the logs or try again.")
    except Exception as e:
        logger.error(f"Error processing and storing global document: {e}", exc_info=True)
        await update.message.reply_text("An error occurred while adding the document. Please try again later.")
    finally:
        if 'add_global_doc_content_or_url' in context.user_data:
            del context.user_data['add_global_doc_content_or_url']
        
    return ConversationHandler.END

async def cancel_add_global_doc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the global document addition conversation."""
    if 'add_global_doc_content_or_url' in context.user_data:
        del context.user_data['add_global_doc_content_or_url']
    await update.message.reply_text("Global document addition cancelled.")
    return ConversationHandler.END

def get_add_global_doc_conversation_handler() -> ConversationHandler:
    """Creates and returns the ConversationHandler for adding global documents."""
    return ConversationHandler(
        entry_points=[CommandHandler("add_global_doc", add_global_doc_command)],
        states={
            ADD_GLOBAL_DOC_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_global_doc_content)
            ],
            ADD_GLOBAL_DOC_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_global_doc_title)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_add_global_doc)],
    )

# TODO: Implement admin-onlycommand handlers here:
# - add_global_doc
# - view_global_docs
# - edit_global_doc
# - delete_global_doc 