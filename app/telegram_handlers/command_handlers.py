import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatType
from datetime import datetime, timedelta
from typing import Optional, List

from app.core.user_service import UserService
from app.persistence.database import AsyncSessionLocal
from app.core.proposal_service import ProposalService
from app.persistence.models.proposal_model import ProposalType
from app.config import ConfigService
from app.utils import telegram_utils
from app.persistence.repositories.proposal_repository import ProposalRepository
from app.persistence.repositories.user_repository import UserRepository

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
        "  /my_submissions (or /my_votes) - View your voting/submission history (DM only).\n"
        "  /proposals open - List open proposals (DM only).\n"
        "  /proposals closed - List closed proposals (DM only).\n"
        "  /view_submissions &lt;proposal_id&gt; - View all anonymized submissions for a closed free-form proposal (DM only).\n"
        "  /edit_proposal &lt;proposal_id&gt; - Edit your proposal (if no votes yet, DM only).\n"
        "  /cancel_proposal &lt;proposal_id&gt; - Cancel your active proposal (DM only).\n"
        "  /add_proposal_context &lt;proposal_id&gt; &lt;URL or paste text&gt; - Add context to your proposal (DM only).\n\n"
        "<b>Information:</b>\n"
        "  /ask &lt;question&gt; - Ask a general question.\n"
        "  /ask &lt;proposal_id&gt; &lt;question&gt; - Ask a question specific to a proposal.\n\n"
        "<b>Admin (Future - for now, `/add_doc` might be restricted):</b>\n"
        "  /add_doc &lt;URL or paste text&gt; - Add a general context document (DM only).\n\n"
        "Remember to interact with me via Direct Message (DM) for most commands, especially when creating proposals or submitting responses."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    if update.effective_user:
        logger.info(f"User {update.effective_user.id} requested help.")
    else:
        logger.info("Received /help command from a user with no effective_user object.")

async def propose_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /propose command to create a new proposal."""
    logger.debug(f"User {update.effective_user.id if update.effective_user else 'Unknown'}: /propose command received. Raw args: {context.args}")

    if not update.effective_user:
        await update.message.reply_text("Sorry, I can't identify you to create a proposal.")
        logger.warning("propose_command called without effective_user.")
        return

    if update.message.chat.type != ChatType.PRIVATE:
        await update.message.reply_text("Please use the /propose command in a private chat with me (DM).")
        return

    args_str = " ".join(context.args) if context.args else ""
    parts = [p.strip() for p in args_str.split(";")]

    if len(parts) < 2:
        await update.message.reply_text(
            "Usage: /propose <Title>; <Description>; [Option1,Option2,... OR \"FREEFORM\"]\n"
            "Example: /propose Snack Policy; New snacks for the office; FREEFORM\n"
            "Example: /propose Movie Night; Pick a movie; Action, Comedy, Drama"
        )
        return

    title = parts[0]
    description = parts[1]
    options_str = parts[2] if len(parts) > 2 else ""

    proposal_type: ProposalType
    options: Optional[List[str]] = None

    if not options_str or options_str.upper() == "FREEFORM":
        proposal_type = ProposalType.FREE_FORM
    else:
        proposal_type = ProposalType.MULTIPLE_CHOICE
        options = [opt.strip() for opt in options_str.split(",") if opt.strip()]
        if len(options) < 2:
            await update.message.reply_text("Multiple choice proposals must have at least 2 options.")
            return

    # For Task 2.4, use a fixed duration (e.g., 7 days)
    deadline_date = datetime.utcnow() + timedelta(days=7)
    # In future, this will be parsed from user input using LLMService

    user = update.effective_user

    async with AsyncSessionLocal() as session:
        try:
            logger.debug(f"User {user.id}: Entered propose_command try block.")
            proposal_service = ProposalService(session)
            
            logger.debug(f"User {user.id}: Calling proposal_service.create_proposal with title='{title}', type='{proposal_type.value}'")
            new_proposal = await proposal_service.create_proposal(
                proposer_telegram_id=user.id,
                proposer_username=user.username,
                proposer_first_name=user.first_name,
                title=title,
                description=description,
                proposal_type=proposal_type,
                options=options,
                deadline_date=deadline_date,
            )
            logger.debug(f"User {user.id}: Proposal_service.create_proposal returned proposal ID {new_proposal.id if new_proposal else 'None'}.")

            if not new_proposal or not new_proposal.id:
                logger.error(f"User {user.id}: Proposal creation failed or returned invalid proposal object.")
                await update.message.reply_text("Sorry, there was an issue creating the proposal record. Please try again.")
                return

            confirmation_dm = f"Understood\\. Your proposal ID is `{new_proposal.id}`\\. It will be posted to the channel shortly\\.\nIf you think of more context to add later, you can always DM me: `/add_proposal_context {new_proposal.id} <URL or paste text>`"
            logger.debug(f"User {user.id}: Prepared confirmation DM: \"{confirmation_dm[:50]}...\"")
            await update.message.reply_text(confirmation_dm, parse_mode=ParseMode.MARKDOWN_V2)
            logger.debug(f"User {user.id}: Successfully sent confirmation DM for proposal {new_proposal.id}.")

            # Post to channel
            target_channel_id = ConfigService.get_target_channel_id()
            logger.debug(f"User {user.id}: Target channel ID: {target_channel_id}")
            if not target_channel_id:
                logger.error("TARGET_CHANNEL_ID is not configured. Cannot post proposal to channel.")
                await update.message.reply_text("Error: Bot is not configured to post to a channel. Please contact admin.")
                return
            
            user_repo = UserRepository(session)
            proposer_db_user = await user_repo.get_user_by_telegram_id(user.id)
            if not proposer_db_user:
                 logger.error(f"User {user.id}: Failed to fetch proposer {user.id} from DB for channel message.")
                 proposer_db_user = user 
            logger.debug(f"User {user.id}: Fetched proposer_db_user: {proposer_db_user.first_name if proposer_db_user else 'None'}")

            channel_message_text = telegram_utils.format_proposal_message(new_proposal, proposer_db_user)
            logger.debug(f"User {user.id}: Formatted channel message text: \"{channel_message_text[:50]}...\"")
            
            reply_markup = None
            if new_proposal.proposal_type == ProposalType.FREE_FORM.value:
                reply_markup = telegram_utils.get_free_form_submit_button(new_proposal.id)
            
            logger.debug(f"User {user.id}: Attempting to send message to channel {target_channel_id}.")
            sent_channel_message = await context.bot.send_message(
                chat_id=target_channel_id,
                text=channel_message_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup
            )
            logger.debug(f"User {user.id}: Successfully sent message to channel. Message ID: {sent_channel_message.message_id}.")

            proposal_repo = ProposalRepository(session)
            logger.debug(f"User {user.id}: Updating proposal {new_proposal.id} with channel message ID {sent_channel_message.message_id}.")
            await proposal_repo.update_proposal_message_id(new_proposal.id, sent_channel_message.message_id)
            await session.commit()
            logger.info(f"Proposal {new_proposal.id} created by user {user.id}, posted to channel {target_channel_id}, message ID updated and committed.")

        except ValueError as e:
            logger.error(f"ValueError during proposal creation for user {user.id}: {e}", exc_info=True)
            await update.message.reply_text(f"Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during proposal creation for user {user.id}: {e}", exc_info=True)
            await update.message.reply_text("Sorry, something went wrong while creating your proposal. Please try again later.") 