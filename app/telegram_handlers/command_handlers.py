import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode, ChatType
from datetime import datetime, timedelta
from typing import Optional, List, Pattern

from app.core.user_service import UserService
from app.persistence.database import AsyncSessionLocal
from app.core.proposal_service import ProposalService
from app.persistence.models.proposal_model import ProposalType
from app.config import ConfigService
from app.utils import telegram_utils
from app.persistence.repositories.proposal_repository import ProposalRepository
from app.persistence.repositories.user_repository import UserRepository
# New imports for conversation
from app.telegram_handlers.conversation_defs import (
    COLLECT_TITLE, COLLECT_DESCRIPTION, COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, ASK_DURATION, ASK_CONTEXT,
    USER_DATA_PROPOSAL_PARTS, USER_DATA_PROPOSAL_TITLE, USER_DATA_PROPOSAL_DESCRIPTION,
    USER_DATA_PROPOSAL_TYPE, USER_DATA_PROPOSAL_OPTIONS, USER_DATA_DEADLINE_DATE,
    USER_DATA_TARGET_CHANNEL_ID, USER_DATA_CURRENT_CONTEXT
)
from app.services.llm_service import LLMService # For parsing parts if needed
from app.core.context_service import ContextService # For context handling

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

async def propose_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Starts the proposal creation conversation.
    Parses initial arguments from /propose command if any.
    """
    logger.info(f"User {update.effective_user.id if update.effective_user else 'Unknown'} initiated /propose command.")
    if not update.effective_user:
        await update.message.reply_text("Sorry, I can't identify you to create a proposal.")
        logger.warning("propose_command_entry called without effective_user.")
        return ConversationHandler.END

    # Ensure user is registered/updated
    async with AsyncSessionLocal() as session:
        user_service = UserService(session)
        await user_service.register_user_interaction(
            telegram_id=update.effective_user.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )
        await session.commit() # Ensure user is saved before conversation starts

    # Initialize user_data for the conversation
    context.user_data[USER_DATA_CURRENT_CONTEXT] = {}
    context.user_data[USER_DATA_PROPOSAL_TITLE] = None
    context.user_data[USER_DATA_PROPOSAL_DESCRIPTION] = None
    context.user_data[USER_DATA_PROPOSAL_TYPE] = None
    context.user_data[USER_DATA_PROPOSAL_OPTIONS] = None
    context.user_data[USER_DATA_TARGET_CHANNEL_ID] = ConfigService.get_target_channel_id() # Default for now
    context.user_data[USER_DATA_DEADLINE_DATE] = None


    args_str = " ".join(context.args) if context.args else ""
    
    # Simple parsing for initial parts based on ";"
    # More sophisticated parsing (e.g., LLM-based for unstructured input) could be added here
    parsed_parts = [p.strip() for p in args_str.split(";") if p.strip()]
    context.user_data[USER_DATA_PROPOSAL_PARTS] = parsed_parts

    if parsed_parts:
        context.user_data[USER_DATA_PROPOSAL_TITLE] = parsed_parts[0]
        if len(parsed_parts) > 1:
            context.user_data[USER_DATA_PROPOSAL_DESCRIPTION] = parsed_parts[1]
        if len(parsed_parts) > 2:
            # Attempt to determine type and options from the third part
            # This is a simplification. Real logic for options/type will be in COLLECT_PROPOSAL_TYPE/COLLECT_OPTIONS
            options_or_type_str = parsed_parts[2]
            if options_or_type_str.upper() == "FREEFORM":
                context.user_data[USER_DATA_PROPOSAL_TYPE] = ProposalType.FREE_FORM.value
            else:
                # Assume multiple choice if not "FREEFORM" and options are given
                options = [opt.strip() for opt in options_or_type_str.split(",") if opt.strip()]
                if options:
                    context.user_data[USER_DATA_PROPOSAL_TYPE] = ProposalType.MULTIPLE_CHOICE.value
                    context.user_data[USER_DATA_PROPOSAL_OPTIONS] = options
    
    # Determine the first state based on missing information
    if not context.user_data.get(USER_DATA_PROPOSAL_TITLE):
        await update.message.reply_text("Okay, let's create a new proposal! What would you like to name it?")
        return COLLECT_TITLE
    elif not context.user_data.get(USER_DATA_PROPOSAL_DESCRIPTION):
        await update.message.reply_text(f"Got it. The title is: '{context.user_data[USER_DATA_PROPOSAL_TITLE]}'.\nNow, can you provide a brief description for it?")
        return COLLECT_DESCRIPTION
    elif not context.user_data.get(USER_DATA_PROPOSAL_TYPE):
        await update.message.reply_text(
            f"Title: '{context.user_data[USER_DATA_PROPOSAL_TITLE]}'\n"
            f"Description: '{context.user_data[USER_DATA_PROPOSAL_DESCRIPTION]}'\n\n"
            "Is this a 'multiple_choice' proposal (you'll list options) or a 'free_form' idea collection?"
        )
        # We'll use an inline keyboard for this in the actual handler for COLLECT_PROPOSAL_TYPE
        return COLLECT_PROPOSAL_TYPE # This state will handle presenting options
    elif context.user_data[USER_DATA_PROPOSAL_TYPE] == ProposalType.MULTIPLE_CHOICE.value and not context.user_data.get(USER_DATA_PROPOSAL_OPTIONS):
        await update.message.reply_text("Please list the options for your multiple choice proposal, separated by commas.")
        return COLLECT_OPTIONS
    # Add ASK_CHANNEL logic here if multi-channel is enabled and needed
    else: # All core details (title, desc, type, options if MC) seem to be gathered or inferred
        await update.message.reply_text("How long should this proposal be open for voting/submissions, or until when would you like to set the deadline? (e.g., '7 days', 'until May 21st at 5 PM')")
        return ASK_DURATION

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info(f"User {user.first_name} ({user.id}) canceled the conversation.")
    await update.message.reply_text(
        "Okay, I've cancelled the current operation. You can start over if you like.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END

# Placeholder for old propose_command, will be removed or fully replaced by the ConversationHandler
# async def propose_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Handles the /propose command to create a new proposal."""
#     logger.debug(f"User {update.effective_user.id if update.effective_user else 'Unknown'}: /propose command received. Raw args: {context.args}")

#     if not update.effective_user:
#         await update.message.reply_text("Sorry, I can't identify you to create a proposal.")
#         logger.warning("propose_command called without effective_user.")
#         return

#     if update.message.chat.type != ChatType.PRIVATE:
#         await update.message.reply_text("Please use the /propose command in a private chat with me (DM).")
#         return

#     args_str = " ".join(context.args) if context.args else ""
#     parts = [p.strip() for p in args_str.split(";")]

#     if len(parts) < 2:
#         await update.message.reply_text(
#             "Usage: /propose <Title>; <Description>; [Option1,Option2,... OR \"FREEFORM\"]\n"
#             "Example: /propose Snack Policy; New snacks for the office; FREEFORM\n"
#             "Example: /propose Movie Night; Pick a movie; Action, Comedy, Drama"
#         )
#         return

#     title = parts[0]
#     description = parts[1]
#     options_str = parts[2] if len(parts) > 2 else ""

#     proposal_type: ProposalType
#     options: Optional[List[str]] = None

#     if not options_str or options_str.upper() == "FREEFORM":
#         proposal_type = ProposalType.FREE_FORM
#     else:
#         proposal_type = ProposalType.MULTIPLE_CHOICE
#         options = [opt.strip() for opt in options_str.split(",") if opt.strip()]
#         if len(options) < 2:
#             await update.message.reply_text("Multiple choice proposals must have at least 2 options.")
#             return

#     # For Task 2.4, use a fixed duration (e.g., 7 days)
#     deadline_date = datetime.utcnow() + timedelta(days=7)
#     # In future, this will be parsed from user input using LLMService

#     user = update.effective_user

#     async with AsyncSessionLocal() as session:
#         try:
#             logger.debug(f"User {user.id}: Entered propose_command try block.")
#             proposal_service = ProposalService(session)
            
#             # Get the target_channel_id from ConfigService
#             # This is for the single-channel mode as per Task 2.4 and 2.5 scope
#             target_channel_id_for_proposal = ConfigService.get_target_channel_id()
#             if not target_channel_id_for_proposal:
#                 logger.error(f"User {user.id}: TARGET_CHANNEL_ID is not configured. Cannot create proposal.")
#                 await update.message.reply_text("Error: Bot is not configured with a target channel for proposals. Please contact admin.")
#                 return

#             logger.debug(f"User {user.id}: Calling proposal_service.create_proposal with title='{title}', type='{proposal_type.value}', target_channel_id='{target_channel_id_for_proposal}'")
#             new_proposal = await proposal_service.create_proposal(
#                 proposer_telegram_id=user.id,
#                 proposer_username=user.username,
#                 proposer_first_name=user.first_name,
#                 title=title,
#                 description=description,
#                 proposal_type=proposal_type,
#                 options=options,
#                 deadline_date=deadline_date,
#                 target_channel_id=target_channel_id_for_proposal,
#             )
#             logger.debug(f"User {user.id}: Proposal_service.create_proposal returned proposal ID {new_proposal.id if new_proposal else 'None'}.")

#             if not new_proposal or not new_proposal.id:
#                 logger.error(f"User {user.id}: Proposal creation failed or returned invalid proposal object.")
#                 await update.message.reply_text("Sorry, there was an issue creating the proposal record. Please try again.")
#                 return

#             confirmation_dm = f"Understood\\. Your proposal ID is `{new_proposal.id}`\\. It will be posted to the channel shortly\\.\nIf you think of more context to add later, you can always DM me: `/add_proposal_context {new_proposal.id} <URL or paste text>`"
#             logger.debug(f"User {user.id}: Prepared confirmation DM: \"{confirmation_dm[:50]}...\"")
#             await update.message.reply_text(confirmation_dm, parse_mode=ParseMode.MARKDOWN_V2)
#             logger.debug(f"User {user.id}: Successfully sent confirmation DM for proposal {new_proposal.id}.")

#             # Post to channel
#             # target_channel_id is now sourced from new_proposal.target_channel_id
#             logger.debug(f"User {user.id}: Target channel ID from proposal: {new_proposal.target_channel_id}")
#             if not new_proposal.target_channel_id: # Should not happen if creation was successful
#                 logger.error("Proposal object has no target_channel_id after creation. Cannot post proposal to channel.")
#                 await update.message.reply_text("Error: Proposal created without a channel. Please contact admin.")
#                 return
            
#             user_repo = UserRepository(session)
#             proposer_db_user = await user_repo.get_user_by_telegram_id(user.id)
#             if not proposer_db_user:
#                  logger.error(f"User {user.id}: Failed to fetch proposer {user.id} from DB for channel message.")
#                  proposer_db_user = user 
#             logger.debug(f"User {user.id}: Fetched proposer_db_user: {proposer_db_user.first_name if proposer_db_user else 'None'}")

#             channel_message_text = telegram_utils.format_proposal_message(new_proposal, proposer_db_user)
#             logger.debug(f"User {user.id}: Formatted channel message text: \"{channel_message_text[:50]}...\"")
            
#             # Initialize reply_markup for the channel message
#             channel_reply_markup = None

#             if new_proposal.proposal_type == ProposalType.FREE_FORM: # Check against Enum member
#                 # Use the inline button for free-form as per Task 2.4 update
#                 keyboard = [[InlineKeyboardButton("💬 Submit Your Idea", switch_inline_query_current_chat=f"/submit {new_proposal.id} ")]]
#                 channel_reply_markup = InlineKeyboardMarkup(keyboard)
#             elif new_proposal.proposal_type == ProposalType.MULTIPLE_CHOICE: # Check against Enum member
#                 # For multiple_choice, buttons will be added in Task 4.2.
#                 # For now, no reply_markup is needed for multiple choice either.
#                 # For task 2.4 it was specified not to add buttons yet for MC
#                 pass
            
#             logger.debug(f"User {user.id}: Attempting to send message to channel {new_proposal.target_channel_id}.")
#             sent_channel_message = await context.bot.send_message(
#                 chat_id=new_proposal.target_channel_id, # Use target_channel_id from the proposal object
#                 text=channel_message_text,
#                 parse_mode=ParseMode.MARKDOWN_V2,
#                 reply_markup=channel_reply_markup 
#             )
#             logger.debug(f"User {user.id}: Successfully sent message to channel. Message ID: {sent_channel_message.message_id}.")

#             proposal_repo = ProposalRepository(session)
#             logger.debug(f"User {user.id}: Updating proposal {new_proposal.id} with channel message ID {sent_channel_message.message_id}.")
#             await proposal_repo.update_proposal_message_id(new_proposal.id, sent_channel_message.message_id)
#             await session.commit() # Commit after all operations related to proposal creation are successful
#             logger.info(f"Proposal {new_proposal.id} created by user {user.id}, posted to channel {new_proposal.target_channel_id}, message ID updated and committed.")

#         except ValueError as e:
#             logger.error(f"ValueError during proposal creation for user {user.id}: {e}", exc_info=True)
#             await update.message.reply_text(f"Error: {e}")
#         except Exception as e:
#             logger.error(f"Unexpected error during proposal creation for user {user.id}: {e}", exc_info=True)
#             await update.message.reply_text("Sorry, something went wrong while creating your proposal. Please try again later.") 

async def view_document_content_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the raw content of a specific document."""
    if not update.effective_user or not update.message:
        logger.warning("view_document_content_command called without effective_user or message.")
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /view_doc <document_id>")
        return

    try:
        document_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid Document ID. It must be a number.")
        return

    async with AsyncSessionLocal() as session:
        # Assuming LLMService and VectorDBService are not directly needed for this command's core logic
        # but ContextService might require them for its full initialization.
        # If ContextService can be initialized with only db_session for this specific path, adjust accordingly.
        # For now, passing None for services not strictly used by get_document_content.
        # This is a simplification and might need a more robust DI or service locator pattern.
        
        # A better approach would be to have a way to get services from context or a factory
        # For now, let's assume ContextService can be partially initialized or these are available
        # This part might need adjustment based on how services are typically instantiated and passed around.
        # Simplification: Directly instantiating services here - NOT ideal for production.
        # config_service = ConfigService() # This should be available globally or passed in.
        # llm_service = LLMService(api_key=config_service.get_openai_api_key())
        # vector_db_service = VectorDBService(host="localhost", port=8000) # Example, needs proper config
        
        # The services below are not used by get_document_content directly.
        # If ContextService.__init__ requires them, they'd need to be instantiated.
        # For now, let's assume they are not strictly needed for this specific method or ContextService handles their optionality.
        context_service = ContextService(
            db_session=session, 
            llm_service=None, # Not used by get_document_content
            vector_db_service=None # Not used by get_document_content
        )
        
        raw_content = await context_service.get_document_content(document_id)

    if raw_content:
        # Telegram has a message length limit (4096 characters).
        # We need to split long content into multiple messages.
        max_length = 4000 # Leave some room
        if len(raw_content) <= max_length:
            await update.message.reply_text(f"Content for Document ID {document_id}:\\n\\n{raw_content}")
        else:
            await update.message.reply_text(f"Content for Document ID {document_id} (part 1):\\n\\n")
            for i in range(0, len(raw_content), max_length):
                chunk = raw_content[i:i + max_length]
                await update.message.reply_text(chunk)
                if i + max_length < len(raw_content):
                    await update.message.reply_text(f"Content for Document ID {document_id} (part {i // max_length + 2}):\\n\\n")
        logger.info(f"User {update.effective_user.id} viewed content of document {document_id}.")
    else:
        await update.message.reply_text(f"Could not retrieve content for Document ID {document_id}. It might not exist or have no content.")
        logger.warning(f"User {update.effective_user.id} failed to view content for document {document_id}.") 

async def view_docs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /view_docs command with various arguments."""
    if not update.effective_user or not update.message:
        logger.warning("view_docs_command called without effective_user or message.")
        return

    args = context.args
    user_id = update.effective_user.id

    async with AsyncSessionLocal() as session:
        # Simplified service instantiation for now. See note in view_document_content_command.
        # These services might need to be fetched from a central place or DI container in a full app.
        cfg_service = ConfigService()
        
        # For llm_service and vector_db_service, they are not directly used by the 
        # list_documents_for_proposal path in ContextService, or by ProposalService for listing.
        # If their __init__ methods become strict, this needs reconsideration.
        llm_service = None # LLMService(api_key=cfg_service.get_openai_api_key())
        vector_db_service = None # VectorDBService(host=...)
        
        proposal_service = ProposalService(db_session=session)
        context_service = ContextService(db_session=session, llm_service=llm_service, vector_db_service=vector_db_service)

        if not args: # /view_docs (no arguments)
            logger.info(f"User {user_id} requested /view_docs (no args).")
            target_channel_id = cfg_service.get_target_channel_id()
            if target_channel_id:
                # In single-channel mode, we just show the configured target channel.
                # For multi-channel, this will list all authorized channels (Phase 8).
                await update.message.reply_text(f"Proposals are currently managed in channel: {target_channel_id}")
            else:
                await update.message.reply_text("The bot is not currently configured with a target proposal channel.")
            return

        # At this point, args exist. Try to parse as int for proposal_id or use as channel_id string.
        first_arg = args[0]
        try:
            # Attempt to interpret as proposal_id first
            proposal_id_arg = int(first_arg)
            logger.info(f"User {user_id} requested /view_docs for proposal_id: {proposal_id_arg}")
            
            # Check if this proposal_id actually exists to differentiate from a numeric channel_id
            # This is a bit heuristic. A more robust way might be needed if channel IDs can also be purely numeric
            # and overlap with proposal IDs. For now, assume proposal IDs are primary.
            # To be safer, we could first try to fetch as proposal. If not found, then try as channel if it's a string.
            # For now, this logic assumes if it's an int, it *could* be a proposal_id.
            
            # Let's refine: Check if it is a valid proposal. If not, it might be a channel ID or invalid.
            temp_proposal = await proposal_service.proposal_repository.get_proposal_by_id(proposal_id_arg)

            if temp_proposal:
                documents = await context_service.list_documents_for_proposal(proposal_id_arg)
                if documents:
                    doc_lines = [f"Documents for Proposal ID {proposal_id_arg}:"]
                    for doc in documents:
                        doc_lines.append(f"  - ID: {doc.id}, Title: {doc.title or 'N/A'}")
                    await update.message.reply_text("\n".join(doc_lines))
                else:
                    await update.message.reply_text(f"No documents found for Proposal ID {proposal_id_arg}.")
                return
            else:
                # If it was a number but not a valid proposal_id, treat it as a channel_id
                # This path will also be hit if the first_arg was non-numeric initially
                pass # Fall through to channel_id logic

        except ValueError:
            # first_arg is not an integer, so treat it as a channel_id string
            pass # Fall through to channel_id logic
        
        # If we're here, first_arg is to be treated as a channel_id
        channel_id_arg = str(first_arg) # Ensure it's a string
        logger.info(f"User {user_id} requested /view_docs for channel_id: {channel_id_arg}")
        proposals = await proposal_service.list_proposals_by_channel(channel_id_arg)
        if proposals:
            proposal_lines = [f"Proposals in Channel {channel_id_arg}:"]
            for prop in proposals:
                proposal_lines.append(f"  - ID: {prop.id}, Title: {prop.title}, Status: {prop.status}")
            await update.message.reply_text("\n".join(proposal_lines))
        else:
            await update.message.reply_text(f"No proposals found in Channel {channel_id_arg}, or channel not found/authorized.") 