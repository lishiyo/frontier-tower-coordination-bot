import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode, ChatType
from typing import Optional

from app.core.user_service import UserService
from app.persistence.database import AsyncSessionLocal, get_session
from app.core.proposal_service import ProposalService
from app.core.context_service import ContextService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.config import ConfigService
from app.utils.telegram_utils import escape_markdown_v2

logger = logging.getLogger(__name__)

# Initialize services for handlers that don't have their own session management
# This might need refinement based on how sessions are handled per request/handler
# For now, assuming a simplified approach or that services handle sessions internally if needed for single calls
config_service = ConfigService()
# Note: Consider dependency injection or a context-based service provider for more complex scenarios

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued, handles deep links."""
    if not update.effective_user or not update.message:
        logger.warning("start_command received update without effective_user or message.")
        # Send a generic message if possible, though context might be limited
        if update.message:
            await update.message.reply_text("Hello! Welcome to CoordinationBot. Type /help to see available commands.")
        return

    user = update.effective_user
    payload = None
    if context.args and len(context.args) > 0:
        payload = context.args[0]
        logger.info(f"User {user.id} started bot with payload: {payload}")

    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        await user_service.register_user_interaction(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

    if payload and payload.startswith("submit_"):
        try:
            proposal_id_str = payload.split("submit_")[-1]
            proposal_id = int(proposal_id_str)
            
            message_text = f"You\'re about to submit an idea for Proposal ID `{proposal_id}`\\.\nClick the button below to prefill the command, then add your idea\\!"
            
            # This button WILL work because we are now in a DM with the bot.
            query_to_prefill = f"submit {proposal_id} "
            keyboard = [[InlineKeyboardButton("📝 Prefill Submission Command", switch_inline_query_current_chat=query_to_prefill)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
            logger.info(f"User {user.id} deep-linked to submit for proposal {proposal_id}. Sent prefill button.")
            return # End here after handling deep link
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing submit payload '{payload}' for user {user.id}: {e}")
            # Fall through to generic welcome if payload is malformed

    # Generic welcome message if no valid payload
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
    logger.info(f"User {user.id} ({user.username}) started the bot (or payload not handled) and was registered/updated.")

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

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /ask command, providing answers based on RAG."""
    if not update.message or not update.effective_user:
        logger.warning("ask_command received update without message or effective_user.")
        return

    if not context.args:
        await update.message.reply_text(
            "Please provide a question. Usage: /ask <your question>"
        )
        return

    # Instantiate services directly
    llm_service = LLMService()
    vector_db_service = VectorDBService()

    question_text = " ".join(context.args)
    logger.info(f"/ask command called with question: '{question_text}' by user {update.effective_user.id}")

    if not question_text.strip():
        await update.message.reply_text("Your question seems to be empty. Please provide a question.")
        return

    await update.message.reply_chat_action(action='typing')

    # Determine if the first argument is a proposal ID for specific document RAG
    proposal_id_filter: Optional[int] = None
    question_text_for_service = question_text

    if context.args and len(context.args) > 1: # Need at least two args for <id> <question>
        try:
            potential_proposal_id = int(context.args[0])
            # Check if it's a plausible ID (e.g., > 0, though DB would ultimately validate)
            # For now, any int is considered a potential ID to filter by.
            proposal_id_filter = potential_proposal_id
            question_text_for_service = " ".join(context.args[1:])
            logger.info(f"Detected proposal ID {proposal_id_filter} for specific document RAG. Question: '{question_text_for_service}'")
        except ValueError:
            # First arg is not an int, so it's part of a general question for intelligent ask
            logger.info("First argument not a proposal ID, proceeding with intelligent ask for the full query.")
            pass # proposal_id_filter remains None, question_text_for_service is already full query

    try:
        async with AsyncSessionLocal() as session:
            context_service = ContextService(
                db_session=session,
                llm_service=llm_service,
                vector_db_service=vector_db_service
            )
            
            answer: str
            if proposal_id_filter is not None:
                # Case 1: /ask <proposal_id> <question> - RAG on specific proposal's documents
                logger.info(f"Calling get_answer_for_question for prop ID {proposal_id_filter} and question '{question_text_for_service}'")
                answer = await context_service.get_answer_for_question(
                    question_text=question_text_for_service,
                    proposal_id_filter=proposal_id_filter
                )
            else:
                # Case 2: /ask <general_question_about_proposals_or_docs> - Intelligent ask
                logger.info(f"Calling handle_intelligent_ask for query '{question_text_for_service}'")
                answer = await context_service.handle_intelligent_ask(
                    query_text=question_text_for_service, 
                    user_telegram_id=update.effective_user.id
                )
            
            # MarkdownV2 escaping should be done carefully, especially if LLM already formats some markdown.
            # For now, let's assume the answer from handle_intelligent_ask is plain text or simple markdown that needs escaping.
            escaped_answer = escape_markdown_v2(answer)
        # Ensure the message object exists before replying
        if update.message:
            await update.message.reply_text(escaped_answer, parse_mode='MarkdownV2')
    except Exception as e:
        logger.error(f"Error in ask_command: {e}", exc_info=True)
        if update.message: # Ensure message object exists for error reply
            await update.message.reply_text("Sorry, I couldn't process your request at the moment.")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles unknown commands."""
    await update.message.reply_text("Sorry, I didn't understand that command. Type /help to see available commands.")