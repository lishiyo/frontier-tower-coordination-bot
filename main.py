import logging
import asyncio # Keep for type hinting if necessary, but not for running the main loop
from telegram.ext import Application, CommandHandler

from app.config import ConfigService
# from app.persistence.database import DatabaseManager # Will be implemented in a future task
# Import your new command handlers
from app.telegram_handlers.command_handlers import start_command, help_command, propose_command

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
    application.add_handler(CommandHandler("propose", propose_command))

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