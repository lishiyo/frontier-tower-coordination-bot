import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from app.telegram_handlers.conversation_defs import (
    COLLECT_TITLE, COLLECT_DESCRIPTION, COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, ASK_DURATION, ASK_CONTEXT,
    USER_DATA_PROPOSAL_TITLE, USER_DATA_PROPOSAL_DESCRIPTION, USER_DATA_PROPOSAL_TYPE,
    USER_DATA_PROPOSAL_OPTIONS, USER_DATA_DEADLINE_DATE, USER_DATA_TARGET_CHANNEL_ID,
    USER_DATA_CONTEXT_DOCUMENT_ID, PROPOSAL_TYPE_CALLBACK
)
from app.persistence.models.proposal_model import ProposalType
from app.services.llm_service import LLMService
from app.core.context_service import ContextService
from app.core.proposal_service import ProposalService
from app.persistence.database import AsyncSessionLocal
from app.utils import telegram_utils
from app.config import ConfigService
from app.persistence.repositories.document_repository import DocumentRepository
from app.persistence.repositories.user_repository import UserRepository
from app.services.vector_db_service import VectorDBService

logger = logging.getLogger(__name__)

# --- Proposal Conversation State Handlers ---

async def handle_collect_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collects the proposal title."""
    title = update.message.text.strip()
    if not title:
        await update.message.reply_text("Title cannot be empty. Please provide a title for your proposal.")
        return COLLECT_TITLE

    context.user_data[USER_DATA_PROPOSAL_TITLE] = title
    logger.info(f"User {update.effective_user.id} provided title: '{title}'")
    await update.message.reply_text(
        f"Great! The title is: '{title}'.\nNow, please provide a brief description for your proposal."
    )
    return COLLECT_DESCRIPTION

async def handle_collect_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collects the proposal description."""
    description = update.message.text.strip()
    if not description:
        await update.message.reply_text("Description cannot be empty. Please provide a description.")
        return COLLECT_DESCRIPTION

    context.user_data[USER_DATA_PROPOSAL_DESCRIPTION] = description
    logger.info(f"User {update.effective_user.id} provided description: '{description[:50]}...'")
    
    keyboard = [
        [InlineKeyboardButton("Multiple Choice (Users vote on options)", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.MULTIPLE_CHOICE.value}")],
        [InlineKeyboardButton("Free Form (Users submit ideas/text)", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.FREE_FORM.value}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Title: '{context.user_data[USER_DATA_PROPOSAL_TITLE]}'\n"
        f"Description: '{description}'\n\n"
        "Next, what type of proposal is this?",
        reply_markup=reply_markup
    )
    return COLLECT_PROPOSAL_TYPE

async def handle_collect_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Collects options for a multiple choice proposal."""
    options_str = update.message.text.strip()
    if not options_str:
        await update.message.reply_text("Options cannot be empty. Please provide at least two options separated by commas.")
        return COLLECT_OPTIONS

    options = [opt.strip() for opt in options_str.split(",") if opt.strip()]
    if len(options) < 2:
        await update.message.reply_text("Multiple choice proposals must have at least two options. Please list them separated by commas.")
        return COLLECT_OPTIONS

    context.user_data[USER_DATA_PROPOSAL_OPTIONS] = options
    logger.info(f"User {update.effective_user.id} provided options: {options}")

    # ASK_CHANNEL logic would go here if enabled
    # For now, skipping to ASK_DURATION
    await update.message.reply_text(
        f"Options recorded: { ', '.join(options) }.\nHow long should this proposal be open for voting, or until when would you like to set the deadline? (e.g., '7 days', 'until May 21st at 5 PM')"
    )
    return ASK_DURATION

async def handle_ask_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles user's natural language input for proposal duration."""
    user_input = update.message.text
    logger.info(f"User {update.effective_user.id} provided duration string: '{user_input}'")

    # LLMService does not require a session for parsing duration
    llm_service = LLMService() # Removed session argument

    # AsyncSessionLocal should be used if other database operations are needed here,
    # but for now, only LLMService is used which handles its own API key.
    # async with AsyncSessionLocal() as session: # Keep this structure if db ops are added later

    deadline_date = await llm_service.parse_natural_language_duration(user_input)

    if deadline_date:
        context.user_data[USER_DATA_DEADLINE_DATE] = deadline_date
        logger.info(f"Parsed deadline for user {update.effective_user.id}: {deadline_date}")
        # Use the new display formatter
        display_deadline_str = telegram_utils.format_datetime_for_display(deadline_date)
        await update.message.reply_text(
            f"Got it! Deadline set for: {display_deadline_str}. "
            "Now, do you have any initial context or background information to add for this proposal? "
            "You can paste text, provide a URL, or just type 'no' for now.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASK_CONTEXT
    else:
        await update.message.reply_text(
            "I couldn't understand that duration. Please try again, for example: 'in 7 days', 'next Monday at 5pm', 'for 3 weeks'."
        )
        return ASK_DURATION

async def handle_ask_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Implementation for ASK_CONTEXT (Task 3.4 continued)
    # This will use ContextService.process_and_store_document
    user_input_context = update.message.text.strip()
    user = update.effective_user
    logger.info(f"User {user.id} provided context string: '{user_input_context[:100]}...'")

    if user_input_context.lower() not in ["no", "none", "skip"]:
        async with AsyncSessionLocal() as session:
            # Instantiate required services for ContextService
            llm_service = LLMService()
            vector_db_service = VectorDBService() # Uses default path
            
            context_service = ContextService(
                db_session=session, 
                llm_service=llm_service, 
                vector_db_service=vector_db_service
            )
            try:
                # Determine source_type (text or url)
                # Basic check, can be improved
                source_type = "user_url" if user_input_context.startswith(("http://", "https://")) else "user_text"
                
                # Construct the title with tappable username if available
                if user.username:
                    user_display_name = f"@{user.username}"
                elif user.first_name:
                    user_display_name = user.first_name
                else:
                    user_display_name = str(user.id)
                
                title = f"proposal context by {user_display_name}"
                
                # process_and_store_document expects proposal_id to be optional for general docs
                # For proposal creation, we don't have proposal_id yet.
                # We store the doc, get doc_id, then link it *after* proposal is created.
                document = await context_service.process_and_store_document(
                    content_source=user_input_context,
                    source_type=source_type,
                    title=title,
                    # proposal_id will be linked later
                )
                if document: # Check if document ID was returned (it's an int)
                    context.user_data[USER_DATA_CONTEXT_DOCUMENT_ID] = document # Store the int ID directly
                    logger.info(f"User {user.id} context processed and stored. Document ID: {document}")
                    await update.message.reply_text(f"Context added (Document ID: {document}).")
                else:
                    logger.warning(f"User {user.id} provided context, but document processing returned None or no ID.")
                    await update.message.reply_text("I tried to process your context, but something went wrong. We'll proceed without it for now.")
            except Exception as e:
                logger.error(f"Error processing context for user {user.id}: {e}", exc_info=True)
                await update.message.reply_text("Sorry, there was an error processing your context. We'll proceed without it for now.")
    else:
        logger.info(f"User {user.id} opted out of providing initial context.")
        await update.message.reply_text("No initial context will be added.")

    # All data collected, proceed to create proposal
    try:
        async with AsyncSessionLocal() as session:
            proposal_service = ProposalService(session, bot_app=context.application)
            user_repo = UserRepository(session) # For fetching full user object for channel message

            # Retrieve all data from context.user_data
            title = context.user_data[USER_DATA_PROPOSAL_TITLE]
            description = context.user_data[USER_DATA_PROPOSAL_DESCRIPTION]
            proposal_type_str = context.user_data[USER_DATA_PROPOSAL_TYPE]
            proposal_type_enum = ProposalType(proposal_type_str) # Convert string back to enum
            options = context.user_data.get(USER_DATA_PROPOSAL_OPTIONS)
            deadline_date = context.user_data[USER_DATA_DEADLINE_DATE]
            target_channel_id = context.user_data.get(USER_DATA_TARGET_CHANNEL_ID) or ConfigService.get_target_channel_id()
            
            if not target_channel_id:
                 logger.error(f"User {user.id}: Target channel ID is not set in context or config. Cannot create proposal.")
                 await update.message.reply_text("Error: Target channel for proposals is not configured. Please contact admin.", reply_markup=ReplyKeyboardRemove())
                 context.user_data.clear()
                 return ConversationHandler.END

            logger.info(f"User {user.id}: Creating proposal. Title='{title}', Type='{proposal_type_enum.value}', TargetChannel='{target_channel_id}'")

            db_user = await user_repo.get_user_by_telegram_id(user.id)
            if not db_user:
                # This should not happen if propose_command_entry registered the user
                logger.error(f"User {user.id} not found in DB during final proposal creation step.")
                await update.message.reply_text("Error: Could not find your user record. Please try /start again.", reply_markup=ReplyKeyboardRemove())
                context.user_data.clear()
                return ConversationHandler.END

            new_proposal = await proposal_service.create_proposal(
                proposer_telegram_id=user.id,
                proposer_username=user.username,
                proposer_first_name=user.first_name,
                title=title,
                description=description,
                proposal_type=proposal_type_enum,
                options=options,
                deadline_date=deadline_date,
                target_channel_id=target_channel_id
            )

            if not new_proposal or not new_proposal.id:
                logger.error(f"User {user.id}: Proposal creation failed or returned invalid proposal object in final step.")
                await update.message.reply_text("Sorry, there was an issue creating the proposal record. Please try again.", reply_markup=ReplyKeyboardRemove())
                context.user_data.clear()
                return ConversationHandler.END

            logger.info(f"User {user.id}: Proposal {new_proposal.id} created successfully in DB.")

            # Link context document if it was created
            context_document_id = context.user_data.get(USER_DATA_CONTEXT_DOCUMENT_ID)
            if context_document_id:
                doc_repo = DocumentRepository(session)
                # Link the document to the proposal in the SQL database
                linked_doc = await doc_repo.link_document_to_proposal(context_document_id, new_proposal.id)
                if linked_doc:
                    await session.commit() # Commit the document link update
                    logger.info(f"User {user.id}: Linked document {context_document_id} to proposal {new_proposal.id} in SQL.")

                    # Now, update the metadata in ChromaDB
                    # Instantiate services needed for ContextService within this session scope
                    llm_service_for_linking = LLMService()
                    vector_db_service_for_linking = VectorDBService()
                    context_service_for_linking = ContextService(
                        db_session=session, # Use the current session
                        llm_service=llm_service_for_linking,
                        vector_db_service=vector_db_service_for_linking
                    )
                    await context_service_for_linking.link_document_to_proposal_in_vector_store(
                        document_sql_id=context_document_id,
                        proposal_id=new_proposal.id
                    )
                else:
                    logger.error(f"User {user.id}: Failed to link document {context_document_id} to proposal {new_proposal.id}. Update returned None.")
                    # Decide if we should rollback or just log

            # Send confirmation DM
            # Ensure all parts of the message that might contain special MarkdownV2 characters are escaped.
            title_escaped = telegram_utils.escape_markdown_v2(new_proposal.title)
            # Ensure channel_id is string before escaping, as it might be an int from config
            channel_id_escaped = telegram_utils.escape_markdown_v2(str(new_proposal.target_channel_id))
            
            confirmation_dm_parts = [
                f"Proposal ID `{new_proposal.id}` created successfully\\!\n",
                f"Title: {title_escaped}\n",
                f"It will be posted to the channel '{channel_id_escaped}' shortly\\.\n\n",
                f"You can add more context later using: `/add_doc {new_proposal.id} <URL or paste text>`\n",
                f"To edit \\(only if no votes\\): `/edit_proposal {new_proposal.id}`\n",
                f"To cancel: `/cancel_proposal {new_proposal.id}`" # Clarified cancel command
            ]
            confirmation_dm = "".join(confirmation_dm_parts)

            await update.message.reply_text(confirmation_dm, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=ReplyKeyboardRemove())

            # Post to channel
            channel_message_text = telegram_utils.format_proposal_message(new_proposal, db_user) # Use db_user
            channel_reply_markup = None

            if new_proposal.proposal_type == ProposalType.FREE_FORM.value:
                # Use existing helper for free form button, now passing bot_username
                bot_username = context.bot.username
                channel_reply_markup = telegram_utils.get_free_form_submit_button(new_proposal.id, bot_username)
            elif new_proposal.proposal_type == ProposalType.MULTIPLE_CHOICE.value:
                if new_proposal.options:
                    # Use the new helper for multiple choice options keyboard
                    channel_reply_markup = telegram_utils.create_proposal_options_keyboard(new_proposal.id, new_proposal.options)
                else:
                    logger.warning(f"User {user.id}: Multiple choice proposal {new_proposal.id} has no options. Cannot create voting keyboard.")
            else:
                logger.warning(f"User {user.id}: Unknown proposal type {new_proposal.proposal_type} for proposal {new_proposal.id}")
            
            logger.info(f"User {user.id}: Final channel_reply_markup: {channel_reply_markup is not None}")

            sent_channel_message = await context.bot.send_message(
                chat_id=new_proposal.target_channel_id,
                text=channel_message_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=channel_reply_markup
            )

            # Update proposal with channel_message_id
            await proposal_service.proposal_repository.update_proposal_message_id(new_proposal.id, sent_channel_message.message_id)
            await session.commit() # Commit message_id update
            logger.info(f"User {user.id}: Proposal {new_proposal.id} posted to channel {new_proposal.target_channel_id}, message ID {sent_channel_message.message_id} updated.")

    except Exception as e:
        logger.error(f"Critical error in final proposal creation step for user {user.id}: {e}", exc_info=True)
        await update.message.reply_text("A critical error occurred while finalizing your proposal. Please try again later or contact an admin.", reply_markup=ReplyKeyboardRemove())
    finally:
        context.user_data.clear()
        return ConversationHandler.END