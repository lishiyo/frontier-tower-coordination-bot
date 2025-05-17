import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode, ChatType
from datetime import datetime, timedelta
from typing import Optional, List, Pattern

from app.core.user_service import UserService
from app.persistence.database import AsyncSessionLocal
from app.core.proposal_service import ProposalService

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    if update.effective_user:
        user = update.effective_user

        async with AsyncSessionLocal() as session:
            user_service = UserService(session)
            await user_service.register_user_interaction(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )

        welcome_message = (
            f"Hello {user.first_name}! Welcome to CoordinationBot.\n\n"
            f"I can help you create proposals, vote on them, and get information about policies.\n\n"
            f"Here are some things you can do:\n"
            f"  - Use /propose to create a new policy proposal or idea generation.\n"
            f"  - Use /ask to get information about existing policies or proposals.\n"
            f"  - Use /help to see all available commands.\n\n"
            f"Type /help to get started."
        )
        await update.message.reply_text(welcome_message)
        logger.info(f"User {user.id} ({user.username}) started the bot and was registered/updated.")
    else:
        await update.message.reply_text("Hello! Welcome to CoordinationBot. Type /help to see available commands.")
        logger.info("Received /start command from a user with no effective_user object.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the /help command is issued."""
    help_text = (
        "Here's how I can assist you:\n\n"
        "<b>General Commands:</b>\n"
        "  /start - Welcome message and basic intro.\n"
        "  /help - Shows this help message.\n"
        "  /privacy - Displays the bot's privacy policy.\n\n"
        "<b>Proposals &amp; Voting:</b>\n"
        "  /propose &lt;Title&gt;; &lt;Description&gt;; [Options OR \"FREEFORM\"] - Start creating a new proposal (DM only).\n"
        "    Example (Multiple Choice): <code>/propose Event Types; What kind of events?; Hackathons, Talks, Socials</code>\n"
        "    Example (Free Form): <code>/propose AI Project Ideas; Suggest cool AI projects!</code>\n"
        "  /submit &lt;proposal_id&gt; &lt;Your idea/response&gt; - Submit your free-form response to an idea proposal (DM only).\n"
        "  /my_votes - View your voting/free-form submission history (DM only).\n"
        "  /proposals open - List open proposals (DM only).\n"
        "  /proposals closed - List closed proposals (DM only).\n"
        "  /view_results &lt;proposal_id&gt; - View all results (anonymized submissions or breakdown of votes) for a closed proposal (DM only).\n"
        "  /edit_proposal &lt;proposal_id&gt; - Edit your proposal (if no votes yet, DM only).\n"
        "  /cancel_proposal &lt;proposal_id&gt; - Cancel your active proposal (DM only).\n"
        "  /add_doc &lt;proposal_id&gt; &lt;URL or paste text&gt; - Add context to your proposal (DM only).\n\n"
        "<b>Information:</b>\n"
        "  /ask &lt;question&gt; - Ask a general question.\n"
        "  /ask &lt;proposal_id&gt; &lt;question&gt; - Ask a question specific to a proposal.\n\n"
        "<b>Admin (Future - for now, `/add_doc` might be restricted):</b>\n"
        "  /add_global_doc &lt;URL or paste text&gt; - Add a general context document (DM only).\n\n"
        "Remember to interact with me via Direct Message (DM) for most commands, especially when creating proposals or submitting responses."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    if update.effective_user:
        logger.info(f"User {update.effective_user.id} requested help.")
    else:
        logger.info("Received /help command from a user with no effective_user object.")

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    if update.message and update.message.from_user:
        user = update.message.from_user
        logger.info(f"User {user.first_name} ({user.id}) canceled the conversation.")
    else:
        logger.info("Conversation canceled.")
    
    if update.callback_query: # If cancellation came from a callback (e.g. inline button)
        await update.callback_query.answer("Operation cancelled.")
        if update.callback_query.message: # Try to edit the message to remove keyboard or show cancelled state
            try:
                await update.callback_query.edit_message_reply_markup(reply_markup=None)
            except Exception as e:
                logger.debug(f"Could not edit message reply markup on cancel: {e}")
    
    if update.message: # If cancellation came from a command/message
        await update.message.reply_text(
            "Okay, I've cancelled the current operation. You can start over if you like.",
            reply_markup=ReplyKeyboardRemove(),
        )
    context.user_data.clear()
    return ConversationHandler.END