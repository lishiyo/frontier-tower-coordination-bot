import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes, Application

from app.telegram_handlers.document_command_handlers import (
    view_document_content_command,
    view_docs_command
)
from app.core.context_service import ContextService
from app.core.proposal_service import ProposalService # For view_docs
from app.config import ConfigService # For view_docs
from app.persistence.models.proposal_model import Proposal, ProposalStatus # For view_docs test data
from app.persistence.models.document_model import Document # For view_docs test data
from app.persistence.database import AsyncSessionLocal # For patching


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.message = AsyncMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 123
    return update

@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.application = MagicMock(spec=Application)
    context.bot = AsyncMock()
    context.args = []
    context.user_data = {}
    return context

# Tests for view_docs_command

@pytest.mark.asyncio
@patch('app.telegram_handlers.document_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.document_command_handlers.ConfigService')
@patch('app.telegram_handlers.document_command_handlers.ProposalService') # Not used directly but part of imports
@patch('app.telegram_handlers.document_command_handlers.ContextService') # Not used directly but part of imports
async def test_view_docs_command_no_args_no_config_channel(
    mock_cs_class, mock_ps_class, mock_config_service_class, mock_async_session, mock_update, mock_context
):
    mock_context.args = []
    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_instance.get_target_channel_id.return_value = None
    mock_config_service_class.return_value = mock_config_instance

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    await view_docs_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with(
        "The bot is not currently configured with a default target proposal channel."
    )

@pytest.mark.asyncio
@patch('app.telegram_handlers.document_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.document_command_handlers.ConfigService')
@patch('app.telegram_handlers.document_command_handlers.ProposalService') 
@patch('app.telegram_handlers.document_command_handlers.ContextService') 
async def test_view_docs_command_no_args_with_config_channel(
    mock_cs_class, mock_ps_class, mock_config_service_class, mock_async_session, mock_update, mock_context
):
    target_channel = "-100123456789"
    mock_context.args = []
    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_instance.get_target_channel_id.return_value = target_channel
    mock_config_service_class.return_value = mock_config_instance

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    await view_docs_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with(
        f"Proposals are currently managed in channel: {target_channel}. Use `/view_docs <channel_id>` to list all proposals for the channel."
    )

@pytest.mark.asyncio
@patch('app.telegram_handlers.document_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.document_command_handlers.ConfigService')
@patch('app.telegram_handlers.document_command_handlers.ProposalService')
@patch('app.telegram_handlers.document_command_handlers.ContextService')
async def test_view_docs_command_with_proposal_id_found_docs(
    mock_context_service_class, mock_proposal_service_class, mock_config_service_class, mock_async_session, mock_update, mock_context
):
    proposal_id = 101
    mock_context.args = [str(proposal_id)]

    mock_doc1 = MagicMock(spec=Document)
    mock_doc1.id=1
    mock_doc1.title="Doc 1 Title"
    mock_doc1.proposal_id=proposal_id
    
    mock_doc2 = MagicMock(spec=Document)
    mock_doc2.id=2
    mock_doc2.title="Doc 2 Title"
    mock_doc2.proposal_id=proposal_id
    
    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_cs_instance.list_documents_for_proposal.return_value = [mock_doc1, mock_doc2]
    mock_context_service_class.return_value = mock_cs_instance

    mock_ps_instance = AsyncMock(spec=ProposalService)
    mock_ps_instance.proposal_repository = AsyncMock()
    mock_ps_instance.proposal_repository.get_proposal_by_id.return_value = Proposal(id=proposal_id, title="Some Prop") 
    mock_proposal_service_class.return_value = mock_ps_instance

    await view_docs_command(mock_update, mock_context)

    mock_cs_instance.list_documents_for_proposal.assert_called_once_with(proposal_id)
    expected_message = (
        f"Documents for Proposal ID {proposal_id}:\n"
        f"  - ID: {mock_doc1.id}, Title: {mock_doc1.title}\n"
        f"  - ID: {mock_doc2.id}, Title: {mock_doc2.title}\n"
        f"\nUse `/view_doc <document_id>` to see the doc in detail."
    )
    mock_update.message.reply_text.assert_called_once_with(expected_message)

@pytest.mark.asyncio
@patch('app.telegram_handlers.document_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.document_command_handlers.ConfigService')
@patch('app.telegram_handlers.document_command_handlers.ProposalService')
@patch('app.telegram_handlers.document_command_handlers.ContextService')
async def test_view_docs_command_with_proposal_id_no_docs(
    mock_context_service_class, mock_proposal_service_class, mock_config_service_class, mock_async_session, mock_update, mock_context
):
    proposal_id = 102
    mock_context.args = [str(proposal_id)]

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_cs_instance.list_documents_for_proposal.return_value = [] 
    mock_context_service_class.return_value = mock_cs_instance

    mock_ps_instance = AsyncMock(spec=ProposalService)
    mock_ps_instance.proposal_repository = AsyncMock() 
    mock_ps_instance.proposal_repository.get_proposal_by_id.return_value = MagicMock(spec=Proposal, id=proposal_id)
    mock_proposal_service_class.return_value = mock_ps_instance

    await view_docs_command(mock_update, mock_context)

    mock_cs_instance.list_documents_for_proposal.assert_called_once_with(proposal_id)
    mock_ps_instance.proposal_repository.get_proposal_by_id.assert_called_once_with(proposal_id)
    mock_update.message.reply_text.assert_called_once_with(f"No documents found for Proposal ID {proposal_id}.")

@pytest.mark.asyncio
@patch('app.telegram_handlers.document_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.document_command_handlers.ConfigService')
@patch('app.telegram_handlers.document_command_handlers.ProposalService')
@patch('app.telegram_handlers.document_command_handlers.ContextService')
async def test_view_docs_command_with_non_int_arg_as_channel_id(
    mock_context_service_class, mock_proposal_service_class, mock_config_service_class, mock_async_session, mock_update, mock_context
):
    channel_id_arg = "my_channel_name" 
    mock_context.args = [channel_id_arg]

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_context_service_class.return_value = mock_cs_instance

    mock_ps_instance = AsyncMock(spec=ProposalService)
    mock_prop1 = MagicMock(spec=Proposal)
    mock_prop1.id=1
    mock_prop1.title="Prop 1"
    mock_prop1.status=ProposalStatus.OPEN
    
    mock_prop2 = MagicMock(spec=Proposal)
    mock_prop2.id=2
    mock_prop2.title="Prop 2"
    mock_prop2.status=ProposalStatus.CLOSED

    mock_ps_instance.list_proposals_by_channel.return_value = [mock_prop1, mock_prop2]
    mock_proposal_service_class.return_value = mock_ps_instance

    await view_docs_command(mock_update, mock_context)

    mock_cs_instance.list_documents_for_proposal.assert_not_called() 
    mock_ps_instance.list_proposals_by_channel.assert_called_once_with(channel_id_arg)
    
    expected_message = (
        f"Proposals for channel/identifier '{channel_id_arg}':\n"
        f"  - ID: {mock_prop1.id}, Title: {mock_prop1.title}, Status: {mock_prop1.status.value}\n"
        f"  - ID: {mock_prop2.id}, Title: {mock_prop2.title}, Status: {mock_prop2.status.value}\n"
        f"\nUse `/view_docs <proposal_id>` to view the documents for a proposal."
    )
    mock_update.message.reply_text.assert_called_once_with(expected_message)

@pytest.mark.asyncio
@patch('app.telegram_handlers.document_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.document_command_handlers.ConfigService')
@patch('app.telegram_handlers.document_command_handlers.ProposalService')
@patch('app.telegram_handlers.document_command_handlers.ContextService')
async def test_view_docs_command_with_channel_id_no_proposals_found(
    mock_context_service_class, mock_proposal_service_class, mock_config_service_class, mock_async_session, mock_update, mock_context
):
    channel_id_arg = "-100987654321"
    mock_context.args = [channel_id_arg]

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_context_service_class.return_value = mock_cs_instance

    mock_ps_instance = AsyncMock(spec=ProposalService)
    mock_ps_instance.proposal_repository = AsyncMock() 
    mock_ps_instance.proposal_repository.get_proposal_by_id.return_value = None 
    mock_ps_instance.list_proposals_by_channel.return_value = [] 
    mock_proposal_service_class.return_value = mock_ps_instance

    await view_docs_command(mock_update, mock_context)

    mock_cs_instance.list_documents_for_proposal.assert_not_called()
    mock_ps_instance.proposal_repository.get_proposal_by_id.assert_not_called()
    
    mock_ps_instance.list_proposals_by_channel.assert_called_once_with(channel_id_arg)
    mock_update.message.reply_text.assert_called_once_with(
        f"No proposals found for channel/identifier '{channel_id_arg}', or it's not a recognized proposal ID or channel. Use `/view_docs` to list all channel ids."
    )


# Tests for view_document_content_command

@pytest.mark.asyncio
@patch('app.telegram_handlers.document_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.document_command_handlers.ContextService')
async def test_view_document_content_command_success(mock_context_service_class, mock_async_session, mock_update, mock_context):
    doc_id = 1
    content = "This is the document content."
    mock_context.args = [str(doc_id)]

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_cs_instance.get_document_content.return_value = content
    mock_context_service_class.return_value = mock_cs_instance

    await view_document_content_command(mock_update, mock_context)

    mock_context_service_class.assert_called_once_with(db_session=mock_session, llm_service=None, vector_db_service=None)
    mock_cs_instance.get_document_content.assert_called_once_with(doc_id)
    mock_update.message.reply_text.assert_called_once_with(f"Content for Document ID {doc_id}:\n\n{content}")

@pytest.mark.asyncio
@patch('app.telegram_handlers.document_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.document_command_handlers.ContextService')
async def test_view_document_content_command_long_content(mock_context_service_class, mock_async_session, mock_update, mock_context):
    doc_id = 2
    long_content_part = "A" * 3000
    content = long_content_part + "B" * 1500 
    mock_context.args = [str(doc_id)]

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_cs_instance.get_document_content.return_value = content
    mock_context_service_class.return_value = mock_cs_instance

    await view_document_content_command(mock_update, mock_context)

    expected_calls = [
        call(f"Content for Document ID {doc_id} (part 1):\n\n"),
        call(content[:4000]),
        call(f"Content for Document ID {doc_id} (part 2):\n\n"),
        call(content[4000:])
    ]
    mock_update.message.reply_text.assert_has_calls(expected_calls)
    assert mock_update.message.reply_text.call_count == 4

@pytest.mark.asyncio
async def test_view_document_content_command_no_args(mock_update, mock_context):
    mock_context.args = []
    await view_document_content_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with("Usage: /view_doc <document_id>")

@pytest.mark.asyncio
async def test_view_document_content_command_invalid_id(mock_update, mock_context):
    mock_context.args = ["abc"]
    await view_document_content_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with("Invalid Document ID. It must be a number.")

@pytest.mark.asyncio
@patch('app.telegram_handlers.document_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.document_command_handlers.ContextService')
async def test_view_document_content_command_not_found(mock_context_service_class, mock_async_session, mock_update, mock_context):
    doc_id = 99
    mock_context.args = [str(doc_id)]

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_cs_instance.get_document_content.return_value = None 
    mock_context_service_class.return_value = mock_cs_instance

    await view_document_content_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with(f"Could not retrieve content for Document ID {doc_id}. It might not exist or have no content.")
