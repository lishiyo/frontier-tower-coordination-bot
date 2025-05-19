import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from telegram import Update, User, Message, Chat
from telegram.ext import ConversationHandler, ContextTypes, Application

from app.telegram_handlers.admin_command_handlers import (
    add_global_doc_command,
    handle_add_global_doc_content,
    handle_add_global_doc_title,
    cancel_add_global_doc,
    # get_add_global_doc_conversation_handler, # We test functions directly
    ADD_GLOBAL_DOC_CONTENT,
    ADD_GLOBAL_DOC_TITLE,
)
from app.config import ConfigService
from app.core.context_service import ContextService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.persistence.database import AsyncSessionLocal

ADMIN_ID = 12345
NON_ADMIN_ID = 67890

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
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

@pytest.mark.asyncio
@patch('app.telegram_handlers.admin_command_handlers.ConfigService')
async def test_add_global_doc_command_admin_starts_conversation_no_args(mock_config_service, mock_update, mock_context):
    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_instance.get_admin_ids.return_value = [ADMIN_ID]
    mock_config_service.return_value = mock_config_instance
    mock_update.effective_user.id = ADMIN_ID
    mock_context.args = []

    result = await add_global_doc_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "Let's add a new global document. "
        "Please send the document content (paste text directly or provide a URL)."
    )
    assert result == ADD_GLOBAL_DOC_CONTENT
    mock_config_instance.get_admin_ids.assert_called_once()

@pytest.mark.asyncio
@patch('app.telegram_handlers.admin_command_handlers.ConfigService')
async def test_add_global_doc_command_admin_starts_conversation_with_args(mock_config_service, mock_update, mock_context):
    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_instance.get_admin_ids.return_value = [ADMIN_ID]
    mock_config_service.return_value = mock_config_instance
    mock_update.effective_user.id = ADMIN_ID
    doc_content = "This is the document content."
    mock_context.args = doc_content.split()

    result = await add_global_doc_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "Great! Now, please provide a title for this document."
    )
    assert mock_context.user_data['add_global_doc_content_or_url'] == doc_content
    assert result == ADD_GLOBAL_DOC_TITLE
    mock_config_instance.get_admin_ids.assert_called_once()

@pytest.mark.asyncio
@patch('app.telegram_handlers.admin_command_handlers.ConfigService')
async def test_add_global_doc_command_non_admin_access_denied(mock_config_service, mock_update, mock_context):
    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_instance.get_admin_ids.return_value = [ADMIN_ID]
    mock_config_service.return_value = mock_config_instance
    mock_update.effective_user.id = NON_ADMIN_ID

    result = await add_global_doc_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "Access Denied: This command is for administrators only."
    )
    assert result == ConversationHandler.END
    mock_config_instance.get_admin_ids.assert_called_once()

@pytest.mark.asyncio
async def test_handle_add_global_doc_content_success(mock_update, mock_context):
    doc_content = "This is the document content."
    mock_update.message.text = doc_content

    result = await handle_add_global_doc_content(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "Great! Now, please provide a title for this document."
    )
    assert mock_context.user_data['add_global_doc_content_or_url'] == doc_content
    assert result == ADD_GLOBAL_DOC_TITLE

@pytest.mark.asyncio
async def test_handle_add_global_doc_content_empty(mock_update, mock_context):
    mock_update.message.text = ""

    result = await handle_add_global_doc_content(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "Content cannot be empty. Please send the content or URL again, or /cancel."
    )
    assert 'add_global_doc_content_or_url' not in mock_context.user_data
    assert result == ADD_GLOBAL_DOC_CONTENT

@pytest.mark.asyncio
@patch('app.telegram_handlers.admin_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.admin_command_handlers.ContextService')
@patch('app.telegram_handlers.admin_command_handlers.LLMService')
@patch('app.telegram_handlers.admin_command_handlers.VectorDBService')
@patch('app.telegram_handlers.admin_command_handlers.ConfigService')
async def test_handle_add_global_doc_title_success_text_content(
    mock_config_service, mock_vector_db_service, mock_llm_service, mock_context_service_class, mock_async_session, mock_update, mock_context
):
    title = "Test Title"
    doc_content = "This is test content."
    mock_update.message.text = title
    mock_context.user_data['add_global_doc_content_or_url'] = doc_content

    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_instance.get_openai_api_key.return_value = "fake_api_key"
    mock_config_service.return_value = mock_config_instance

    mock_llm_instance = MagicMock(spec=LLMService)
    mock_llm_service.return_value = mock_llm_instance
    mock_vector_db_instance = MagicMock(spec=VectorDBService)
    mock_vector_db_service.return_value = mock_vector_db_instance
    
    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_cs_instance.process_and_store_document.return_value = 1
    mock_context_service_class.return_value = mock_cs_instance
    
    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    result = await handle_add_global_doc_title(mock_update, mock_context)

    mock_context_service_class.assert_called_once_with(
        db_session=mock_session, 
        llm_service=mock_llm_instance, 
        vector_db_service=mock_vector_db_instance
    )
    mock_cs_instance.process_and_store_document.assert_called_once_with(
        content_source=doc_content,
        source_type="admin_global_text",
        title=title,
        proposal_id=None
    )
    mock_update.message.reply_text.assert_called_once_with(
        f"Global document '{title}' (ID: 1) added successfully."
    )
    assert 'add_global_doc_content_or_url' not in mock_context.user_data
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.admin_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.admin_command_handlers.ContextService')
@patch('app.telegram_handlers.admin_command_handlers.LLMService')
@patch('app.telegram_handlers.admin_command_handlers.VectorDBService')
@patch('app.telegram_handlers.admin_command_handlers.ConfigService')
async def test_handle_add_global_doc_title_success_url_content(
    mock_config_service, mock_vector_db_service, mock_llm_service, mock_context_service_class, mock_async_session, mock_update, mock_context
):
    title = "Test URL Title"
    doc_url = "http://example.com/doc"
    mock_update.message.text = title
    mock_context.user_data['add_global_doc_content_or_url'] = doc_url

    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_instance.get_openai_api_key.return_value = "fake_api_key"
    mock_config_service.return_value = mock_config_instance

    mock_llm_instance = MagicMock(spec=LLMService)
    mock_llm_service.return_value = mock_llm_instance
    mock_vector_db_instance = MagicMock(spec=VectorDBService)
    mock_vector_db_service.return_value = mock_vector_db_instance

    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_cs_instance.process_and_store_document.return_value = 2
    mock_context_service_class.return_value = mock_cs_instance

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    result = await handle_add_global_doc_title(mock_update, mock_context)

    mock_cs_instance.process_and_store_document.assert_called_once_with(
        content_source=doc_url,
        source_type="admin_global_url",
        title=title,
        proposal_id=None
    )
    mock_update.message.reply_text.assert_called_once_with(
        f"Global document '{title}' (ID: 2) added successfully."
    )
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_handle_add_global_doc_title_empty_title(mock_update, mock_context):
    mock_update.message.text = ""
    mock_context.user_data['add_global_doc_content_or_url'] = "some content"

    result = await handle_add_global_doc_title(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "Title cannot be empty. Please provide a title, or /cancel."
    )
    assert result == ADD_GLOBAL_DOC_TITLE

@pytest.mark.asyncio
async def test_handle_add_global_doc_title_missing_content_in_user_data(mock_update, mock_context):
    mock_update.message.text = "Some Title"
    # 'add_global_doc_content_or_url' is deliberately not set in mock_context.user_data

    result = await handle_add_global_doc_title(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "An error occurred. Please try starting over with /add_global_doc."
    )
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.admin_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.admin_command_handlers.ContextService')
@patch('app.telegram_handlers.admin_command_handlers.LLMService')
@patch('app.telegram_handlers.admin_command_handlers.VectorDBService')
@patch('app.telegram_handlers.admin_command_handlers.ConfigService')
async def test_handle_add_global_doc_title_context_service_failure(
    mock_config_service, mock_vector_db_service, mock_llm_service, mock_context_service_class, mock_async_session, mock_update, mock_context
):
    title = "Test Fail Title"
    doc_content = "content that will fail"
    mock_update.message.text = title
    mock_context.user_data['add_global_doc_content_or_url'] = doc_content

    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_instance.get_openai_api_key.return_value = "fake_api_key"
    mock_config_service.return_value = mock_config_instance

    mock_llm_instance = MagicMock(spec=LLMService)
    mock_llm_service.return_value = mock_llm_instance
    mock_vector_db_instance = MagicMock(spec=VectorDBService)
    mock_vector_db_service.return_value = mock_vector_db_instance

    mock_cs_instance = AsyncMock(spec=ContextService)
    mock_cs_instance.process_and_store_document.side_effect = Exception("DB commit failed") 
    mock_context_service_class.return_value = mock_cs_instance

    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    result = await handle_add_global_doc_title(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "An error occurred while adding the document. Please try again later."
    )
    assert 'add_global_doc_content_or_url' not in mock_context.user_data
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.admin_command_handlers.ConfigService')
@patch('app.telegram_handlers.admin_command_handlers.LLMService', side_effect=AttributeError("Mocked AttributeError"))
async def test_handle_add_global_doc_title_service_init_attribute_error(
    mock_llm_service, mock_config_service, mock_update, mock_context
):
    title = "Error Title"
    doc_content = "Some content"
    mock_update.message.text = title
    mock_context.user_data['add_global_doc_content_or_url'] = doc_content

    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_service.return_value = mock_config_instance
    # LLMService is already patched to raise AttributeError

    result = await handle_add_global_doc_title(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "A configuration error occurred with a core service (API key missing?). Please contact an admin."
    )
    assert 'add_global_doc_content_or_url' in mock_context.user_data
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.admin_command_handlers.ConfigService')
@patch('app.telegram_handlers.admin_command_handlers.LLMService', side_effect=Exception("Mocked Generic Exception"))
async def test_handle_add_global_doc_title_service_init_generic_exception(
    mock_llm_service, mock_config_service, mock_update, mock_context
):
    title = "Generic Error Title"
    doc_content = "Some content"
    mock_update.message.text = title
    mock_context.user_data['add_global_doc_content_or_url'] = doc_content

    mock_config_instance = MagicMock(spec=ConfigService)
    mock_config_service.return_value = mock_config_instance
    # LLMService is already patched to raise Exception

    result = await handle_add_global_doc_title(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "A configuration error occurred with a core service. Please contact an admin."
    )
    assert 'add_global_doc_content_or_url' in mock_context.user_data
    assert result == ConversationHandler.END


@pytest.mark.asyncio
async def test_cancel_add_global_doc(mock_update, mock_context):
    mock_context.user_data['add_global_doc_content_or_url'] = "some content to be cleared"

    result = await cancel_add_global_doc(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "Global document addition cancelled."
    )
    assert 'add_global_doc_content_or_url' not in mock_context.user_data
    assert result == ConversationHandler.END

# Test for get_add_global_doc_conversation_handler can be added if needed,
# but it's usually more about testing the individual handlers that make up the conversation.
# For example, to check if it returns a ConversationHandler instance with correct states and fallbacks.

# from app.telegram_handlers.admin_command_handlers import get_add_global_doc_conversation_handler
# from telegram.ext import CommandHandler as TelegramCommandHandler # Renamed to avoid conflict
# from telegram.ext import MessageHandler as TelegramMessageHandler # Renamed
# from telegram.ext import filters as telegram_filters # Renamed

# def test_get_add_global_doc_conversation_handler_structure():
#     handler = get_add_global_doc_conversation_handler()
#     assert isinstance(handler, ConversationHandler)
#     assert len(handler.entry_points) == 1
#     assert isinstance(handler.entry_points[0], TelegramCommandHandler)
#     assert handler.entry_points[0].command == ['add_global_doc']
    
#     assert ADD_GLOBAL_DOC_CONTENT in handler.states
#     assert ADD_GLOBAL_DOC_TITLE in handler.states
#     assert len(handler.states[ADD_GLOBAL_DOC_CONTENT]) == 1
#     assert isinstance(handler.states[ADD_GLOBAL_DOC_CONTENT][0], TelegramMessageHandler)
    
#     assert len(handler.fallbacks) == 1
#     assert isinstance(handler.fallbacks[0], TelegramCommandHandler)
#     assert handler.fallbacks[0].command == ['cancel']

# Removed placeholder
# def test_placeholder():
#     assert True 