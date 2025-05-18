import logging
import asyncio # Keep for type hinting if necessary, but not for running the main loop
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler
import telegram.ext.filters as filters # Changed import

from app.config import ConfigService
# from app.persistence.database import DatabaseManager # Will be implemented in a future task

# Import command handlers from their new locations
from app.telegram_handlers.command_handlers import (
    start_command, help_command # privacy_command # Commented out
)
from app.telegram_handlers.document_command_handlers import (
    view_document_content_command, view_docs_command
    # edit_doc_command, delete_doc_command, view_global_docs_command, edit_global_doc_command, delete_global_doc_command, add_global_doc_command, add_doc_command, edit_proposal_command # Commented out
)
from app.telegram_handlers.proposal_command_handlers import (
    proposal_conv_handler, # get_proposal_creation_conv_handler, cancel_proposal_command, proposals_command # Commented out, proposal_conv_handler is covered by get_proposal_creation_conv_handler
)
from app.telegram_handlers.submission_command_handlers import (
    submit_command #, my_votes_command, view_results_command, ask_command # Commented out
)
from app.telegram_handlers.callback_handlers import (
    handle_vote_callback, 
    handle_collect_proposal_type_callback, # Corrected name
    # handle_channel_selection_callback # Commented out - definition missing in callback_handlers.py
)

# For PROPOSAL_TYPE_CALLBACK and CHANNEL_SELECT_CALLBACK patterns
from app.telegram_handlers.conversation_defs import PROPOSAL_TYPE_CALLBACK, CHANNEL_SELECT_CALLBACK

# message_handlers, callback_handlers, and conversation_defs are now used within proposal_command_handlers.py
# and no longer need to be directly imported into main.py

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot.""" 
    config_service = ConfigService()

    # Initialize DatabaseManager if you plan to use it directly here or pass to services
    # For now, ensuring it can be initialized if needed by other parts of your app
    # db_manager = DatabaseManager(config_service.get_database_url())
    # await db_manager.init_db() # Or a similar method to set up connections/tables

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config_service.get_bot_token()).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    # application.add_handler(CommandHandler("privacy", privacy_command)) # Task 7.7
    # application.add_handler(CommandHandler("add_global_doc", add_global_doc_command)) # Task 6.2
    application.add_handler(CommandHandler("view_doc", view_document_content_command)) # Task 3.5
    application.add_handler(CommandHandler("view_docs", view_docs_command)) # Task 3.5, 8.2
    # application.add_handler(CommandHandler("edit_doc", edit_doc_command)) # Task 7.8
    # application.add_handler(CommandHandler("delete_doc", delete_doc_command)) # Task 7.8
    # application.add_handler(CommandHandler("view_global_docs", view_global_docs_command)) # Task 7.9
    # application.add_handler(CommandHandler("edit_global_doc", edit_global_doc_command)) # Task 7.9
    # application.add_handler(CommandHandler("delete_global_doc", delete_global_doc_command)) # Task 7.9
    application.add_handler(CommandHandler("submit", submit_command)) # Task 4.3
    # application.add_handler(CommandHandler("my_votes", my_votes_command)) # Task 7.1
    # application.add_handler(CommandHandler("my_submissions", my_votes_command)) # Alias for my_votes (Task 7.1)
    # application.add_handler(CommandHandler("view_results", view_results_command)) # Task 7.6
    # application.add_handler(CommandHandler("ask", ask_command)) # Task 6.1
    # application.add_handler(CommandHandler("proposals", proposals_command)) # Task 7.2
    # application.add_handler(CommandHandler("cancel_proposal", cancel_proposal_command)) # Task 7.4
    # application.add_handler(CommandHandler("add_doc", add_doc_command)) # Task 7.5
    # application.add_handler(CommandHandler("edit_proposal", edit_proposal_command)) # Task 7.3

    # Register ConversationHandlers
    application.add_handler(proposal_conv_handler)

    # Register CallbackQueryHandlers
    application.add_handler(CallbackQueryHandler(handle_collect_proposal_type_callback, pattern=f"^{PROPOSAL_TYPE_CALLBACK}")) # Corrected name
    # application.add_handler(CallbackQueryHandler(handle_channel_selection_callback, pattern=f"^{CHANNEL_SELECT_CALLBACK}")) # Commented out - definition missing
    application.add_handler(CallbackQueryHandler(handle_vote_callback, pattern=r"^vote_.*$")) # Task 4.2

    logger.info("Bot command and callback handlers registered.")

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot polling...")
    application.run_polling()
    logger.info("Bot polling stopped.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt).")
    except ValueError as e: # Catch config errors from ConfigService
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True) 