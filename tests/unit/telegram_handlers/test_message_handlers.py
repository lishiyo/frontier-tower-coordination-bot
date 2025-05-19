import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User, Message, Chat, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from app.telegram_handlers.message_handlers import (
    handle_collect_title,
    handle_collect_description,
    handle_collect_options,
    handle_ask_duration,
    handle_ask_context,
)
from app.telegram_handlers.conversation_defs import (
    COLLECT_TITLE, COLLECT_DESCRIPTION, COLLECT_PROPOSAL_TYPE, 
    COLLECT_OPTIONS, ASK_DURATION, ASK_CONTEXT,
    USER_DATA_PROPOSAL_TITLE, USER_DATA_PROPOSAL_DESCRIPTION, 
    USER_DATA_PROPOSAL_TYPE, USER_DATA_PROPOSAL_OPTIONS, 
    USER_DATA_DEADLINE_DATE, USER_DATA_TARGET_CHANNEL_ID,
    USER_DATA_CONTEXT_DOCUMENT_ID, PROPOSAL_TYPE_CALLBACK
)
from app.persistence.models.proposal_model import ProposalType

# Common mock objects
@pytest.fixture
def mock_update_message():
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "Test"
    update.message = MagicMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 67890
    update.message.reply_text = AsyncMock()
    update.message.reply_markdown_v2 = AsyncMock()
    return update

@pytest.fixture
def mock_context_user_data():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.bot = AsyncMock()
    context.bot.username = "TestBot"
    context.application = MagicMock() # For ProposalService bot_app
    return context


@pytest.mark.asyncio
async def test_handle_collect_title_success(mock_update_message, mock_context_user_data):
    """Test collecting title successfully."""
    mock_update_message.message.text = "My Awesome Proposal"

    next_state = await handle_collect_title(mock_update_message, mock_context_user_data)

    assert mock_context_user_data.user_data[USER_DATA_PROPOSAL_TITLE] == "My Awesome Proposal"
    mock_update_message.message.reply_text.assert_called_once_with(
        "Great! The title is: 'My Awesome Proposal'.\nNow, please provide a brief description for your proposal."
    )
    assert next_state == COLLECT_DESCRIPTION

@pytest.mark.asyncio
async def test_handle_collect_title_empty(mock_update_message, mock_context_user_data):
    """Test collecting title when it is empty."""
    mock_update_message.message.text = "  " # Empty or whitespace

    next_state = await handle_collect_title(mock_update_message, mock_context_user_data)

    assert USER_DATA_PROPOSAL_TITLE not in mock_context_user_data.user_data
    mock_update_message.message.reply_text.assert_called_once_with(
        "Title cannot be empty. Please provide a title for your proposal."
    )
    assert next_state == COLLECT_TITLE

@pytest.mark.asyncio
async def test_handle_collect_description_success(mock_update_message, mock_context_user_data):
    """Test collecting description successfully."""
    mock_context_user_data.user_data[USER_DATA_PROPOSAL_TITLE] = "Existing Title"
    mock_update_message.message.text = "This is a great description."

    next_state = await handle_collect_description(mock_update_message, mock_context_user_data)

    assert mock_context_user_data.user_data[USER_DATA_PROPOSAL_DESCRIPTION] == "This is a great description."
    
    # Check that reply_text was called with an InlineKeyboardMarkup
    call_args = mock_update_message.message.reply_text.call_args
    assert call_args is not None
    assert "Next, what type of proposal is this?" in call_args[0][0]
    assert isinstance(call_args[1]['reply_markup'], InlineKeyboardMarkup)
    keyboard = call_args[1]['reply_markup'].inline_keyboard
    assert len(keyboard) == 2
    assert keyboard[0][0].text == "Multiple Choice (Users vote on options)"
    assert keyboard[0][0].callback_data == f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.MULTIPLE_CHOICE.value}"
    assert keyboard[1][0].text == "Free Form (Users submit ideas/text)"
    assert keyboard[1][0].callback_data == f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.FREE_FORM.value}"
    assert next_state == COLLECT_PROPOSAL_TYPE

@pytest.mark.asyncio
async def test_handle_collect_description_empty(mock_update_message, mock_context_user_data):
    """Test collecting description when it is empty."""
    mock_context_user_data.user_data[USER_DATA_PROPOSAL_TITLE] = "Existing Title"
    mock_update_message.message.text = "  "

    next_state = await handle_collect_description(mock_update_message, mock_context_user_data)

    assert USER_DATA_PROPOSAL_DESCRIPTION not in mock_context_user_data.user_data
    mock_update_message.message.reply_text.assert_called_once_with(
        "Description cannot be empty. Please provide a description."
    )
    assert next_state == COLLECT_DESCRIPTION

@pytest.mark.asyncio
async def test_handle_collect_options_success(mock_update_message, mock_context_user_data):
    """Test collecting options successfully."""
    mock_update_message.message.text = "Option 1, Option 2, Option 3"

    next_state = await handle_collect_options(mock_update_message, mock_context_user_data)

    assert mock_context_user_data.user_data[USER_DATA_PROPOSAL_OPTIONS] == ["Option 1", "Option 2", "Option 3"]
    mock_update_message.message.reply_text.assert_called_once_with(
        "Options recorded: Option 1, Option 2, Option 3.\nHow long should this proposal be open for voting, or until when would you like to set the deadline? (e.g., '7 days', 'until May 21st at 5 PM')"
    )
    assert next_state == ASK_DURATION

@pytest.mark.asyncio
async def test_handle_collect_options_empty(mock_update_message, mock_context_user_data):
    """Test collecting options when input is empty."""
    mock_update_message.message.text = "  "
    next_state = await handle_collect_options(mock_update_message, mock_context_user_data)
    assert USER_DATA_PROPOSAL_OPTIONS not in mock_context_user_data.user_data
    mock_update_message.message.reply_text.assert_called_once_with(
        "Options cannot be empty. Please provide at least two options separated by commas."
    )
    assert next_state == COLLECT_OPTIONS

@pytest.mark.asyncio
async def test_handle_collect_options_insufficient(mock_update_message, mock_context_user_data):
    """Test collecting options when less than two are provided."""
    mock_update_message.message.text = "OnlyOne"
    next_state = await handle_collect_options(mock_update_message, mock_context_user_data)
    assert USER_DATA_PROPOSAL_OPTIONS not in mock_context_user_data.user_data
    mock_update_message.message.reply_text.assert_called_once_with(
        "Multiple choice proposals must have at least two options. Please list them separated by commas."
    )
    assert next_state == COLLECT_OPTIONS


# We need to mock LLMService for handle_ask_duration
@patch("app.telegram_handlers.message_handlers.LLMService")
@pytest.mark.asyncio
async def test_handle_ask_duration_success(mock_llm_service_class, mock_update_message, mock_context_user_data):
    """Test asking for duration successfully."""
    mock_update_message.message.text = "in 7 days"
    
    # Mock the LLMService instance and its method
    mock_llm_instance = AsyncMock()
    mock_llm_instance.parse_natural_language_duration.return_value = "2023-12-31T23:59:59Z" # Example ISO date
    mock_llm_service_class.return_value = mock_llm_instance

    # Patch telegram_utils.format_datetime_for_display
    with patch("app.telegram_handlers.message_handlers.telegram_utils.format_datetime_for_display") as mock_format_datetime:
        mock_format_datetime.return_value = "December 31, 2023, 11:59 PM UTC" # Example display string

        next_state = await handle_ask_duration(mock_update_message, mock_context_user_data)

        mock_llm_instance.parse_natural_language_duration.assert_called_once_with("in 7 days")
        assert mock_context_user_data.user_data[USER_DATA_DEADLINE_DATE] == "2023-12-31T23:59:59Z"
        mock_format_datetime.assert_called_once_with("2023-12-31T23:59:59Z")
        mock_update_message.message.reply_text.assert_called_once_with(
            "Got it! Deadline set for: December 31, 2023, 11:59 PM UTC. "
            "Now, do you have any initial context or background information to add for this proposal? "
            "You can paste text, provide a URL, or just type 'no' for now.",
            reply_markup=mock_update_message.message.reply_text.call_args[1]['reply_markup'] # Preserve ReplyKeyboardRemove
        )
        assert next_state == ASK_CONTEXT

@patch("app.telegram_handlers.message_handlers.LLMService")
@pytest.mark.asyncio
async def test_handle_ask_duration_failure(mock_llm_service_class, mock_update_message, mock_context_user_data):
    """Test asking for duration when LLM fails to parse."""
    mock_update_message.message.text = "gibberish duration"
    
    mock_llm_instance = AsyncMock()
    mock_llm_instance.parse_natural_language_duration.return_value = None
    mock_llm_service_class.return_value = mock_llm_instance

    next_state = await handle_ask_duration(mock_update_message, mock_context_user_data)

    mock_llm_instance.parse_natural_language_duration.assert_called_once_with("gibberish duration")
    assert USER_DATA_DEADLINE_DATE not in mock_context_user_data.user_data
    mock_update_message.message.reply_text.assert_called_once_with(
        "I couldn't understand that duration. Please try again, for example: 'in 7 days', 'next Monday at 5pm', 'for 3 weeks'."
    )
    assert next_state == ASK_DURATION

# For handle_ask_context, we need to mock AsyncSessionLocal, ContextService, ProposalService, UserRepository, ConfigService, DocumentRepository
# This will be more involved.

# Start with a test for "no" context
@patch("app.telegram_handlers.message_handlers.AsyncSessionLocal")
@patch("app.telegram_handlers.message_handlers.ProposalService")
@patch("app.telegram_handlers.message_handlers.UserRepository")
@patch("app.telegram_handlers.message_handlers.ConfigService")
@patch("app.telegram_handlers.message_handlers.telegram_utils") # For format_proposal_message and escape_markdown_v2
@patch("app.telegram_handlers.message_handlers.DocumentRepository") # Not strictly used for "no" case, but good to have for consistency
@pytest.mark.asyncio
async def test_handle_ask_context_no_context_success(
    mock_doc_repo_class, mock_telegram_utils, mock_config_service_class, 
    mock_user_repo_class, mock_proposal_service_class, mock_async_session_local,
    mock_update_message, mock_context_user_data
):
    """Test handle_ask_context when user provides 'no' context and proposal creation is successful."""
    mock_update_message.message.text = "no"

    # Populate user_data as if previous steps completed
    mock_context_user_data.user_data = {
        USER_DATA_PROPOSAL_TITLE: "Test Title",
        USER_DATA_PROPOSAL_DESCRIPTION: "Test Description",
        USER_DATA_PROPOSAL_TYPE: ProposalType.FREE_FORM.value,
        USER_DATA_DEADLINE_DATE: "2023-12-31T23:59:59Z",
        # USER_DATA_TARGET_CHANNEL_ID will be fetched from ConfigService mock
    }

    # Mock AsyncSessionLocal context manager
    mock_session = AsyncMock()
    mock_async_session_local.return_value.__aenter__.return_value = mock_session
    mock_async_session_local.return_value.__aexit__.return_value = None

    # Mock ConfigService
    mock_config_instance = MagicMock()
    mock_config_instance.get_target_channel_id.return_value = "-100123456789"
    mock_config_service_class.return_value = mock_config_instance
    # Also mock the static get_target_channel_id if used directly
    mock_config_service_class.get_target_channel_id.return_value = "-100123456789"

    # Mock UserRepository
    mock_user_repo_instance = AsyncMock()
    mock_db_user = MagicMock()
    mock_db_user.id = 1 # DB user ID, not Telegram ID
    mock_db_user.telegram_id = mock_update_message.effective_user.id
    mock_db_user.username = mock_update_message.effective_user.username
    mock_db_user.first_name = mock_update_message.effective_user.first_name
    mock_user_repo_instance.get_user_by_telegram_id.return_value = mock_db_user
    mock_user_repo_class.return_value = mock_user_repo_instance

    # Mock ProposalService
    mock_proposal_service_instance = AsyncMock()
    mock_new_proposal = MagicMock()
    mock_new_proposal.id = 101
    mock_new_proposal.title = "Test Title"
    mock_new_proposal.target_channel_id = "-100123456789"
    mock_new_proposal.proposal_type = ProposalType.FREE_FORM.value # Ensure it matches
    mock_new_proposal.options = None # For FREE_FORM
    mock_proposal_service_instance.create_proposal.return_value = mock_new_proposal
    mock_proposal_service_instance.proposal_repository = AsyncMock() # For update_proposal_message_id
    mock_proposal_service_class.return_value = mock_proposal_service_instance

    # Mock telegram_utils
    mock_telegram_utils.escape_markdown_v2.side_effect = lambda x: x # Simple pass-through for testing
    mock_telegram_utils.format_proposal_message.return_value = "Formatted Proposal Message for Channel"
    mock_telegram_utils.get_free_form_submit_button.return_value = InlineKeyboardMarkup([[InlineKeyboardButton("Submit Idea", url="http://dummy.url")]])

    # Mock bot send_message for channel post
    mock_sent_channel_message = AsyncMock()
    mock_sent_channel_message.message_id = 9876
    mock_context_user_data.bot.send_message.return_value = mock_sent_channel_message

    next_state = await handle_ask_context(mock_update_message, mock_context_user_data)

    mock_update_message.message.reply_text.assert_any_call("No initial context will be added.")
    # Check proposal creation call
    mock_proposal_service_instance.create_proposal.assert_called_once_with(
        proposer_telegram_id=mock_update_message.effective_user.id,
        proposer_username=mock_update_message.effective_user.username,
        proposer_first_name=mock_update_message.effective_user.first_name,
        title="Test Title",
        description="Test Description",
        proposal_type=ProposalType.FREE_FORM, # Ensure it's the enum
        options=None,
        deadline_date="2023-12-31T23:59:59Z",
        target_channel_id="-100123456789"
    )
    
    # Check DM confirmation (using reply_markdown_v2 due to ParseMode.MARKDOWN_V2)
    # We check if it was called, specific content can be tricky with escapes
    dm_called = False
    for call in mock_update_message.message.reply_text.call_args_list:
        if f"Proposal ID `{mock_new_proposal.id}` created successfully" in call[0][0]:
            dm_called = True
            assert call[1]['parse_mode'] == 'MarkdownV2'
            break
    assert dm_called, "Confirmation DM not sent or content mismatch"

    # Check channel message
    mock_context_user_data.bot.send_message.assert_called_once_with(
        chat_id="-100123456789",
        text="Formatted Proposal Message for Channel",
        parse_mode='MarkdownV2',
        reply_markup=mock_telegram_utils.get_free_form_submit_button.return_value
    )

    # Check message_id update
    mock_proposal_service_instance.proposal_repository.update_proposal_message_id.assert_called_once_with(
        mock_new_proposal.id, mock_sent_channel_message.message_id
    )
    
    # Check session commit was called (implicitly via ProposalService or DocumentRepository if context was added)
    # For 'no context' it would be after proposal creation and message_id update
    assert mock_session.commit.call_count >= 1 # At least once for proposal and message_id

    assert USER_DATA_CONTEXT_DOCUMENT_ID not in mock_context_user_data.user_data
    assert not mock_context_user_data.user_data # user_data should be cleared
    assert next_state == ConversationHandler.END

# TODO: Add more tests for handle_ask_context:
# - With text context (successful processing)
# - With URL context (successful processing)
# - Context processing failure
# - Proposal creation failure (various points: no target_channel_id, user not found, create_proposal returns None)
# - Multiple choice proposal type in final step 