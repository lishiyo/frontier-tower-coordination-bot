import logging
from telegram.ext import ApplicationBuilder, Application

from app.config import ConfigService

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def register_handlers(app: Application) -> None:
    """
    Register all command, message and callback handlers with the application.
    
    This function will be expanded as we implement more handlers.
    """
    # TODO: Add handlers as they are implemented
    # Example:
    # from app.telegram_handlers.command_handlers import start_command, help_command
    # app.add_handler(CommandHandler("start", start_command))
    # app.add_handler(CommandHandler("help", help_command))
    
    logger.info("Handlers registered successfully.")

def main() -> None:
    """Main function to initialize and start the bot."""
    logger.info("Starting CoordinationBot...")
    
    # Initialize configuration service
    config_service = ConfigService()
    
    # Get bot token from config
    bot_token = config_service.get_bot_token()
    
    # Create the Application instance
    app = ApplicationBuilder().token(bot_token).build()
    
    # Register handlers
    register_handlers(app)
    
    # Start the bot (polling mode for development)
    logger.info("Bot started. Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main() 