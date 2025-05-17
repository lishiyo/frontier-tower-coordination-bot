import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.persistence.database import AsyncSessionLocal
from app.core.proposal_service import ProposalService
from app.core.context_service import ContextService
from app.config import ConfigService
# Add any other necessary imports from the original command_handlers.py, like services or models if directly used.

logger = logging.getLogger(__name__)

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
        max_length = 4000 # Telegram message length limit
        if len(raw_content) <= max_length:
            await update.message.reply_text(f"Content for Document ID {document_id}:\n\n{raw_content}")
        else:
            await update.message.reply_text(f"Content for Document ID {document_id} (part 1):\n\n")
            for i in range(0, len(raw_content), max_length):
                chunk = raw_content[i:i + max_length]
                await update.message.reply_text(chunk)
                if i + max_length < len(raw_content):
                    await update.message.reply_text(f"Content for Document ID {document_id} (part {i // max_length + 2}):\n\n")
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
        cfg_service = ConfigService()
        proposal_service = ProposalService(db_session=session)
        # Ensure LLMService and VectorDBService are correctly initialized if ContextService needs them
        # For list_documents_for_proposal, they are likely not needed.
        llm_service_instance = None # Or initialize properly if needed elsewhere
        vector_db_service_instance = None # Or initialize properly if needed elsewhere
        context_service = ContextService(db_session=session, llm_service=llm_service_instance, vector_db_service=vector_db_service_instance)

        if not args: # /view_docs (no arguments)
            logger.info(f"User {user_id} requested /view_docs (no args).")
            target_channel_id = cfg_service.get_target_channel_id()
            if target_channel_id:
                # Attempt to get channel name if possible (future enhancement)
                await update.message.reply_text(f"Proposals are currently managed in channel: {target_channel_id}")
            else:
                await update.message.reply_text("The bot is not currently configured with a default target proposal channel.")
            return

        first_arg = args[0]
        
        try:
            # Attempt to parse as an integer first
            potential_id = int(first_arg)

            if potential_id > 0: # Proposal IDs are positive integers
                logger.info(f"User {user_id} requested /view_docs with potential proposal_id: {potential_id}")
                # Check if it's a valid proposal and list its documents
                documents = await context_service.list_documents_for_proposal(potential_id)
                if documents:
                    doc_lines = [f"Documents for Proposal ID {potential_id}:"]
                    for doc in documents:
                        doc_lines.append(f"  - ID: {doc.id}, Title: {doc.title or 'N/A'}")
                    await update.message.reply_text("\n".join(doc_lines))
                    return
                else:
                    # It's a positive integer, but either not a proposal or a proposal with no documents.
                    # Check if the proposal itself exists to give a more specific message.
                    proposal_exists = await proposal_service.proposal_repository.get_proposal_by_id(potential_id)
                    if proposal_exists:
                        await update.message.reply_text(f"No documents found for Proposal ID {potential_id}.")
                    else:
                        # Positive int, but not a proposal ID. It might be an invalid ID or a numeric channel string.
                        # Fall through to treat as channel_id string.
                        logger.info(f"Positive integer {potential_id} is not a known proposal ID. Will attempt to treat '{first_arg}' as a channel identifier.")
                        pass # Fall through to channel_id string logic
            else:
                # It's a non-positive integer (e.g., a typical Telegram channel ID like -100...). Treat as channel_id.
                logger.info(f"Argument '{first_arg}' (parsed as {potential_id}) is non-positive. Treating as channel identifier.")
                pass # Fall through to channel_id string logic
        
        except ValueError:
            # Not an integer, so must be a string channel_id (or invalid argument).
            logger.info(f"Argument '{first_arg}' is not an integer. Treating as channel identifier.")
            pass # Fall through to channel_id string logic

        # If we reached here, it's either a string, a non-positive int, or a positive int not recognized as a proposal_id.
        # Treat first_arg as a channel_id string for listing proposals.
        channel_id_arg_str = str(first_arg)
        logger.info(f"User {user_id} attempting to list proposals for channel/identifier: {channel_id_arg_str}")
        
        proposals_list = await proposal_service.list_proposals_by_channel(channel_id_arg_str) # Renamed variable to avoid conflict
        if proposals_list:
            proposal_lines = [f"Proposals for channel/identifier '{channel_id_arg_str}':"]
            for prop in proposals_list:
                status_display = prop.status.value if hasattr(prop.status, 'value') else str(prop.status)
                proposal_lines.append(f"  - ID: {prop.id}, Title: {prop.title}, Status: {status_display}")
            await update.message.reply_text("\n".join(proposal_lines))
        else:
            await update.message.reply_text(f"No proposals found for channel/identifier '{channel_id_arg_str}', or it's not a recognized proposal ID or channel.")

# TODO: Move other document-related commands here:
# - add_doc_command
# - ask_command 