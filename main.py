import logging
import asyncio # Keep for type hinting if necessary, but not for running the main loop
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler
import telegram.ext.filters as filters # Changed import

from app.config import ConfigService
# from app.persistence.database import DatabaseManager # Will be implemented in a future task

# Import command handlers from their new locations
from app.telegram_handlers.command_handlers import (
    start_command, help_command, unknown_command, ask_command
)
from app.telegram_handlers.user_command_handlers import my_votes_command, my_proposals_command
from app.telegram_handlers.document_command_handlers import (
    view_document_content_command, view_docs_command
    # edit_doc_command, delete_doc_command, view_global_docs_command, edit_global_doc_command, delete_global_doc_command, add_global_doc_command, add_doc_command, edit_proposal_command # Commented out
)
from app.telegram_handlers.proposal_command_handlers import (
    proposal_conv_handler, 
    proposals_command,
    edit_proposal_conv_handler # Added for /edit_proposal
)
from app.telegram_handlers.submission_command_handlers import (
    submit_command, handle_prefilled_submit #, my_votes_command, view_results_command, ask_command # Commented out
)
from app.telegram_handlers.callback_handlers import (
    handle_vote_callback, 
    handle_collect_proposal_type_callback, # Corrected name
    handle_proposal_filter_callback, # Added new handler
    handle_my_proposals_for_edit_prompt # Added for /edit_proposal prompt button
    # handle_channel_selection_callback # Commented out - definition missing in callback_handlers.py
)
from app.telegram_handlers.admin_command_handlers import get_add_global_doc_conversation_handler # view_global_docs_command, edit_global_doc_command, delete_global_doc_command
from app.telegram_handlers.error_handler import error_handler

# Import scheduler functions
from app.services.scheduling_service import start_scheduler_async, stop_scheduler

# For PROPOSAL_TYPE_CALLBACK and CHANNEL_SELECT_CALLBACK patterns
from app.telegram_handlers.conversation_defs import PROPOSAL_TYPE_CALLBACK, PROPOSAL_FILTER_CALLBACK_PREFIX

# message_handlers, callback_handlers, and conversation_defs are now used within proposal_command_handlers.py
# and no longer need to be directly imported into main.py

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def post_init_actions(application: Application):
    """Actions to run after the application is initialized but before polling starts."""
    await start_scheduler_async(application)
    logger.info("Post-initialization actions (like starting scheduler) completed.")

def main() -> None:
    """Start the bot.""" 
    config_service = ConfigService()

    # Initialize DatabaseManager if you plan to use it directly here or pass to services
    # For now, ensuring it can be initialized if needed by other parts of your app
    # db_manager = DatabaseManager(config_service.get_database_url())
    # await db_manager.init_db() # Or a similar method to set up connections/tables

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config_service.get_bot_token()).build()

    # Assign the async post_init_actions function
    application.post_init = post_init_actions

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
    application.add_handler(CommandHandler("submit", submit_command, block=False)) # Task 4.3, added block=False
    application.add_handler(CommandHandler("my_votes", my_votes_command)) # Task 7.1
    application.add_handler(CommandHandler("my_proposals", my_proposals_command)) # Task 7.2
    application.add_handler(CommandHandler("my_submissions", my_votes_command)) # Alias for my_votes (Task 7.1)
    # application.add_handler(CommandHandler("view_results", view_results_command)) # Task 7.6
    application.add_handler(CommandHandler("ask", ask_command)) # Task 6.1
    # application.add_handler(CommandHandler("cancel_proposal", cancel_proposal_command)) # Task 7.4
    # application.add_handler(CommandHandler("add_doc", add_doc_command)) # Task 7.5

    # Register ConversationHandlers
    application.add_handler(proposal_conv_handler)
    application.add_handler(edit_proposal_conv_handler) # Added for /edit_proposal
    application.add_handler(get_add_global_doc_conversation_handler()) # Added

    # Register MessageHandler for prefilled submits (must be before generic message handlers if any)
    # This specifically handles the "@botname submit <id> <text>" pattern in private chats
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & filters.ChatType.PRIVATE, handle_prefilled_submit))

    # Register CallbackQueryHandlers
    application.add_handler(CallbackQueryHandler(handle_collect_proposal_type_callback, pattern=f"^{PROPOSAL_TYPE_CALLBACK}")) # Corrected name
    application.add_handler(CallbackQueryHandler(handle_vote_callback, pattern=r"^vote_.*$")) # Task 4.2
    application.add_handler(CallbackQueryHandler(handle_proposal_filter_callback, pattern=f"^{PROPOSAL_FILTER_CALLBACK_PREFIX}")) # New handler
    application.add_handler(CallbackQueryHandler(handle_my_proposals_for_edit_prompt, pattern=r"^my_proposals_for_edit_prompt$")) # Added

    # Proposal viewing commands
    application.add_handler(CommandHandler("proposals", proposals_command))

    application.add_error_handler(error_handler) # Added error handler

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
        stop_scheduler() # Stop the scheduler
    except ValueError as e: # Catch config errors from ConfigService
        logger.error(f"Configuration error: {e}")
        stop_scheduler() # Stop the scheduler
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True) 
        stop_scheduler() # Stop the scheduler
    finally:
        # Ensure scheduler is stopped if it was running and an error occurred before the specific except blocks
        # This is a bit redundant if stop_scheduler() is in all excepts, but good for belt-and-suspenders
        # However, direct call to stop_scheduler() in excepts is cleaner.
        pass # stop_scheduler() already called in specific handlers 