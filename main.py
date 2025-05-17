import logging
import asyncio # Keep for type hinting if necessary, but not for running the main loop
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler
import telegram.ext.filters as filters # Changed import

from app.config import ConfigService
# from app.persistence.database import DatabaseManager # Will be implemented in a future task

# Import command handlers from their new locations
from app.telegram_handlers.command_handlers import (
    start_command, help_command # cancel_conversation is used in proposal_conv_handler, not directly in main
)
from app.telegram_handlers.document_command_handlers import (
    view_document_content_command, view_docs_command
)
from app.telegram_handlers.proposal_command_handlers import (
    proposal_conv_handler # propose_command_entry is used within this handler
)

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
    
    # Proposal Conversation Handler registration (now imported)
    application.add_handler(proposal_conv_handler) 

    # Document related commands
    application.add_handler(CommandHandler("view_doc", view_document_content_command))
    application.add_handler(CommandHandler("view_docs", view_docs_command))

    # TODO: Register other command handlers from their new files as they are created/moved
    # e.g., submission_command_handlers, other proposal_command_handlers

    logger.info("Bot application created and command handlers registered.")

    # Run the bot until the user presses Ctrl-C
    # run_polling() is a blocking call that starts the event loop.
    logger.info("Starting bot polling...")
    application.run_polling()
    # No explicit shutdown needed here for run_polling, it handles Ctrl+C gracefully.
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