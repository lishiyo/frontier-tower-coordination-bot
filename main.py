import logging
import asyncio # Keep for type hinting if necessary, but not for running the main loop
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler
import telegram.ext.filters as filters # Changed import

from app.config import ConfigService
# from app.persistence.database import DatabaseManager # Will be implemented in a future task
# Import your new command handlers
from app.telegram_handlers.command_handlers import (
    start_command, help_command, propose_command_entry, cancel_conversation,
    view_document_content_command, view_docs_command # Added new handlers
)
from app.telegram_handlers.message_handlers import (
    handle_collect_title,
    handle_collect_description,
    handle_collect_options, # Renamed from handle_collect_options_type
    handle_ask_duration,
    handle_ask_context
)
from app.telegram_handlers.callback_handlers import handle_collect_proposal_type_callback # Specific handler for proposal type callback

from app.telegram_handlers.conversation_defs import (
    COLLECT_TITLE, COLLECT_DESCRIPTION, COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, 
    ASK_DURATION, ASK_CONTEXT, PROPOSAL_TYPE_CALLBACK
)

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

    # Proposal Conversation Handler
    proposal_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("propose", propose_command_entry)],
        states={
            COLLECT_TITLE: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_collect_title)],
            COLLECT_DESCRIPTION: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_collect_description)],
            COLLECT_PROPOSAL_TYPE: [
                CallbackQueryHandler(handle_collect_proposal_type_callback, pattern=f"^{PROPOSAL_TYPE_CALLBACK}"),
                # Allow text input for proposal type as well, as per message_handler logic
                MessageHandler(filters.TEXT & (~filters.COMMAND), handle_collect_proposal_type_callback) 
            ],
            COLLECT_OPTIONS: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_collect_options)],
            ASK_DURATION: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_ask_duration)],
            ASK_CONTEXT: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_ask_context)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        # per_message=True, # Consider if needed for specific scenarios
        # name="proposal_creation_conversation", # Optional: for debugging or specific handler management
        # persistent=False, # Set to True if you want to use persistence across restarts
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    # application.add_handler(CommandHandler("propose", propose_command)) # Old direct command
    application.add_handler(proposal_conv_handler) # New conversation handler
    application.add_handler(CommandHandler("view_doc", view_document_content_command))
    application.add_handler(CommandHandler("view_docs", view_docs_command))

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