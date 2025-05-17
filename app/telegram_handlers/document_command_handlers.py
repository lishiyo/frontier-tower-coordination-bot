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
        context_service = ContextService(db_session=session, llm_service=None, vector_db_service=None)

        if not args: # /view_docs (no arguments)
            logger.info(f"User {user_id} requested /view_docs (no args).")
            target_channel_id = cfg_service.get_target_channel_id()
            if target_channel_id:
                await update.message.reply_text(f"Proposals are currently managed in channel: {target_channel_id}")
            else:
                await update.message.reply_text("The bot is not currently configured with a target proposal channel.")
            return

        first_arg = args[0]
        try:
            proposal_id_arg = int(first_arg)
            logger.info(f"User {user_id} requested /view_docs for proposal_id: {proposal_id_arg}")

            # Check if this proposal_id actually exists to differentiate from a numeric channel_id
            # This is a bit heuristic. A more robust way might be needed if channel IDs can also be purely numeric
            # and overlap with proposal IDs. For now, assume proposal IDs are primary.
            # To be safer, we could first try to fetch as proposal. If not found, then try as channel if it's a string.
            # For now, this logic assumes if it's an int, it *could* be a proposal_id.
            
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
                pass # Fall through to channel_id logic
        except ValueError:
            pass # Fall through to channel_id logic
        
        channel_id_arg = str(first_arg)
        logger.info(f"User {user_id} requested /view_docs for channel_id: {channel_id_arg}")
        proposals = await proposal_service.list_proposals_by_channel(channel_id_arg)
        if proposals:
            proposal_lines = [f"Proposals in Channel {channel_id_arg}:"]
            for prop in proposals:
                proposal_lines.append(f"  - ID: {prop.id}, Title: {prop.title}, Status: {prop.status}")
            await update.message.reply_text("\n".join(proposal_lines))
        else:
            await update.message.reply_text(f"No proposals found in Channel {channel_id_arg}, or channel not found/authorized.")

# TODO: Move other document-related commands here:
# - add_proposal_context_command
# - add_doc_command
# - ask_command 