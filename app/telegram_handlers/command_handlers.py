import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    if update.effective_user:
        user = update.effective_user
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
        logger.info(f"User {user.id} ({user.username}) started the bot.")
    else:
        await update.message.reply_text("Hello! Welcome to CoordinationBot. Type /help to see available commands.")
        logger.info("Received /start command from a user with no effective_user object.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the /help command is issued."""
    help_text = (
        "Here's how I can assist you:\n\n"
        "**General Commands:**\n"
        "  /start - Welcome message and basic intro.\n"
        "  /help - Shows this help message.\n"
        "  /privacy - Displays the bot's privacy policy.\n\n"
        "**Proposals & Voting:**\n"
        "  /propose <Title>; <Description>; [Options OR \"FREEFORM\"] - Start creating a new proposal (DM only).\n"
        "    Example (Multiple Choice): `/propose Event Types; What kind of events?; Hackathons, Talks, Socials`\n"
        "    Example (Free Form): `/propose AI Project Ideas; Suggest cool AI projects!`\n"
        "  /submit <proposal_id> <Your idea/response> - Submit your free-form response to an idea proposal (DM only).\n"
        "  /my_submissions (or /my_votes) - View your voting/submission history (DM only).\n"
        "  /proposals open - List open proposals (DM only).\n"
        "  /proposals closed - List closed proposals (DM only).\n"
        "  /view_submissions <proposal_id> - View all anonymized submissions for a closed free-form proposal (DM only).\n"
        "  /edit_proposal <proposal_id> - Edit your proposal (if no votes yet, DM only).\n"
        "  /cancel_proposal <proposal_id> - Cancel your active proposal (DM only).\n"
        "  /add_proposal_context <proposal_id> <URL or paste text> - Add context to your proposal (DM only).\n\n"
        "**Information:**\n"
        "  /ask <question> - Ask a general question.\n"
        "  /ask <proposal_id> <question> - Ask a question specific to a proposal.\n\n"
        "**Admin (Future - for now, `/add_doc` might be restricted):**\n"
        "  /add_doc <URL or paste text> - Add a general context document (DM only).\n\n"
        "Remember to interact with me via Direct Message (DM) for most commands, especially when creating proposals or submitting responses."
    )
    await update.message.reply_text(help_text)
    if update.effective_user:
        logger.info(f"User {update.effective_user.id} requested help.")
    else:
        logger.info("Received /help command from a user with no effective_user object.") 