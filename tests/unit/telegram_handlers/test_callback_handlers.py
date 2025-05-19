import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from telegram import Update, User, Message, Chat, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler, Application

from app.telegram_handlers.callback_handlers import (
    handle_collect_proposal_type_callback,
    handle_vote_callback
)
from app.telegram_handlers.conversation_defs import (
    COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, ASK_DURATION,
    USER_DATA_PROPOSAL_TYPE, PROPOSAL_TYPE_CALLBACK
)
from app.persistence.models.proposal_model import ProposalType
from app.core.submission_service import SubmissionService
from app.core.user_service import UserService
from app.persistence.database import AsyncSessionLocal

@pytest.fixture
def mock_update_callback():
    update = MagicMock(spec=Update)
    update.callback_query = AsyncMock(spec=CallbackQuery)
    update.callback_query.from_user = MagicMock(spec=User)
    update.callback_query.from_user.id = 123
    update.callback_query.from_user.first_name = "Test"
    update.callback_query.from_user.username = "testuser"
    update.callback_query.message = AsyncMock(spec=Message)
    update.callback_query.message.chat_id = 456
    update.effective_user = update.callback_query.from_user # For logger
    update.effective_message = update.callback_query.message # For logger
    update.message = None # Explicitly set to None for callback-based updates
    return update

@pytest.fixture
def mock_update_message():
    update = MagicMock(spec=Update)
    update.message = AsyncMock(spec=Message)
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 123
    update.message.chat_id = 456
    update.message.chat = MagicMock(spec=Chat) # ensure chat attribute exists
    update.message.chat.id = 456 # ensure chat.id exists
    update.effective_user = update.message.from_user
    update.effective_message = update.message
    update.callback_query = None # Explicitly set to None for message-based updates
    return update

@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.application = MagicMock(spec=Application) # Ensure application is on context
    context.bot = AsyncMock()
    context.user_data = {}
    return context

# Tests for handle_collect_proposal_type_callback

@pytest.mark.asyncio
async def test_handle_collect_proposal_type_callback_multiple_choice(mock_update_callback, mock_context):
    mock_update_callback.callback_query.data = f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.MULTIPLE_CHOICE.value}"

    next_state = await handle_collect_proposal_type_callback(mock_update_callback, mock_context)

    mock_update_callback.callback_query.answer.assert_called_once()
    mock_update_callback.callback_query.edit_message_text.assert_called_once_with(text="Proposal Type: Multiple Choice")
    mock_update_callback.callback_query.message.reply_text.assert_called_once_with(
        "This will be a multiple choice proposal. Please provide the options, separated by commas (e.g., Option A, Option B, Option C)."
    )
    assert mock_context.user_data[USER_DATA_PROPOSAL_TYPE] == ProposalType.MULTIPLE_CHOICE.value
    assert next_state == COLLECT_OPTIONS

@pytest.mark.asyncio
async def test_handle_collect_proposal_type_callback_free_form(mock_update_callback, mock_context):
    mock_update_callback.callback_query.data = f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.FREE_FORM.value}"

    next_state = await handle_collect_proposal_type_callback(mock_update_callback, mock_context)

    mock_update_callback.callback_query.answer.assert_called_once()
    mock_update_callback.callback_query.edit_message_text.assert_called_once_with(text="Proposal Type: Free Form")
    mock_update_callback.callback_query.message.reply_text.assert_called_once_with(
        "This will be a free form proposal.\nHow long should this proposal be open for submissions, or until when would you like to set the deadline? (e.g., '7 days', 'until May 21st at 5 PM')"
    )
    assert mock_context.user_data[USER_DATA_PROPOSAL_TYPE] == ProposalType.FREE_FORM.value
    assert next_state == ASK_DURATION

@pytest.mark.asyncio
async def test_handle_collect_proposal_type_callback_invalid_data(mock_update_callback, mock_context):
    mock_update_callback.callback_query.data = f"{PROPOSAL_TYPE_CALLBACK}invalid_type"

    next_state = await handle_collect_proposal_type_callback(mock_update_callback, mock_context)

    mock_update_callback.callback_query.answer.assert_called_once()
    mock_update_callback.callback_query.edit_message_text.assert_called_once_with(text="Invalid selection. Please try again.")
    
    expected_keyboard = [
        [InlineKeyboardButton("Multiple Choice", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.MULTIPLE_CHOICE.value}")],
        [InlineKeyboardButton("Free Form", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.FREE_FORM.value}")]
    ]
    expected_reply_markup = InlineKeyboardMarkup(expected_keyboard)
    mock_update_callback.callback_query.message.reply_text.assert_called_once_with(
        "What type of proposal is this?", reply_markup=expected_reply_markup
    )
    assert USER_DATA_PROPOSAL_TYPE not in mock_context.user_data
    assert next_state == COLLECT_PROPOSAL_TYPE

@pytest.mark.asyncio
async def test_handle_collect_proposal_type_text_multiple_choice(mock_update_message, mock_context):
    mock_update_message.message.text = "multiple choice please"

    next_state = await handle_collect_proposal_type_callback(mock_update_message, mock_context)

    mock_update_message.message.reply_text.assert_any_call("Proposal Type set to: Multiple Choice")
    mock_update_message.message.reply_text.assert_any_call(
        "This will be a multiple choice proposal. Please provide the options, separated by commas (e.g., Option A, Option B, Option C)."
    )
    assert mock_context.user_data[USER_DATA_PROPOSAL_TYPE] == ProposalType.MULTIPLE_CHOICE.value
    assert next_state == COLLECT_OPTIONS

@pytest.mark.asyncio
async def test_handle_collect_proposal_type_text_free_form(mock_update_message, mock_context):
    mock_update_message.message.text = "let's do a free form"

    next_state = await handle_collect_proposal_type_callback(mock_update_message, mock_context)

    mock_update_message.message.reply_text.assert_any_call("Proposal Type set to: Free Form")
    mock_update_message.message.reply_text.assert_any_call(
        "This will be a free form proposal.\nHow long should this proposal be open for submissions, or until when would you like to set the deadline? (e.g., '7 days', 'until May 21st at 5 PM')"
    )
    assert mock_context.user_data[USER_DATA_PROPOSAL_TYPE] == ProposalType.FREE_FORM.value
    assert next_state == ASK_DURATION

@pytest.mark.asyncio
async def test_handle_collect_proposal_type_text_invalid(mock_update_message, mock_context):
    mock_update_message.message.text = "i dunno, something else"

    next_state = await handle_collect_proposal_type_callback(mock_update_message, mock_context)

    mock_update_message.message.reply_text.assert_any_call("I didn't understand that proposal type. Please choose from the options, or type 'multiple choice' or 'free form'.")
    expected_keyboard = [
        [InlineKeyboardButton("Multiple Choice", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.MULTIPLE_CHOICE.value}")],
        [InlineKeyboardButton("Free Form", callback_data=f"{PROPOSAL_TYPE_CALLBACK}{ProposalType.FREE_FORM.value}")]
    ]
    expected_reply_markup = InlineKeyboardMarkup(expected_keyboard)
    # Check that the re-prompt with keyboard was called
    # We need to find this specific call among potentially multiple calls to reply_text
    found_keyboard_prompt = False
    for call_args_item in mock_update_message.message.reply_text.call_args_list:
        if call_args_item[0][0] == "What type of proposal is this?" and call_args_item[1].get('reply_markup') == expected_reply_markup:
            found_keyboard_prompt = True
            break
    assert found_keyboard_prompt, "Reply with keyboard options not found"

    assert USER_DATA_PROPOSAL_TYPE not in mock_context.user_data
    assert next_state == COLLECT_PROPOSAL_TYPE

# Tests for handle_vote_callback

@pytest.mark.asyncio
@patch('app.telegram_handlers.callback_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.callback_handlers.UserService')
@patch('app.telegram_handlers.callback_handlers.SubmissionService')
async def test_handle_vote_callback_success(
    mock_submission_service_class, mock_user_service_class, mock_async_session, mock_update_callback, mock_context
):
    proposal_id = 1
    option_index = 0
    mock_update_callback.callback_query.data = f"vote_{proposal_id}_{option_index}"

    # Mock AsyncSessionLocal context manager behavior
    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    # Mock UserService
    mock_user_service_instance = AsyncMock(spec=UserService)
    mock_user_service_class.return_value = mock_user_service_instance

    # Mock SubmissionService
    mock_submission_service_instance = AsyncMock(spec=SubmissionService)
    mock_submission_service_instance.record_vote.return_value = (True, "Vote recorded successfully.")
    mock_submission_service_class.return_value = mock_submission_service_instance

    await handle_vote_callback(mock_update_callback, mock_context)

    mock_user_service_instance.register_user_interaction.assert_called_once_with(
        telegram_id=mock_update_callback.callback_query.from_user.id,
        username=mock_update_callback.callback_query.from_user.username,
        first_name=mock_update_callback.callback_query.from_user.first_name
    )
    mock_session.commit.assert_called_once() 
    mock_submission_service_instance.record_vote.assert_called_once_with(
        proposal_id=proposal_id,
        submitter_telegram_id=mock_update_callback.callback_query.from_user.id,
        option_index=option_index
    )
    mock_update_callback.callback_query.answer.assert_called_once_with(text="Vote recorded successfully.", show_alert=True)

@pytest.mark.asyncio
async def test_handle_vote_callback_invalid_data_prefix(mock_update_callback, mock_context):
    mock_update_callback.callback_query.data = "invalid_prefix_1_0"

    await handle_vote_callback(mock_update_callback, mock_context)

    mock_update_callback.callback_query.answer.assert_called_once_with(
        text="Error: Invalid vote data received.", show_alert=True
    )

@pytest.mark.asyncio
async def test_handle_vote_callback_invalid_data_parts(mock_update_callback, mock_context):
    mock_update_callback.callback_query.data = "vote_1" # Not enough parts

    await handle_vote_callback(mock_update_callback, mock_context)

    # This will enter the try block but fail at parts destructuring
    mock_update_callback.callback_query.answer.assert_called_once_with(
        text="Error: Could not process your vote due to invalid data format.", show_alert=True
    )

@pytest.mark.asyncio
async def test_handle_vote_callback_value_error_parsing(mock_update_callback, mock_context):
    mock_update_callback.callback_query.data = "vote_notanint_0"

    await handle_vote_callback(mock_update_callback, mock_context)

    mock_update_callback.callback_query.answer.assert_called_once_with(
        text="Error: Could not process your vote due to invalid data format.", show_alert=True
    )

@pytest.mark.asyncio
@patch('app.telegram_handlers.callback_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.callback_handlers.UserService')
@patch('app.telegram_handlers.callback_handlers.SubmissionService')
async def test_handle_vote_callback_submission_service_returns_error(
    mock_submission_service_class, mock_user_service_class, mock_async_session, mock_update_callback, mock_context
):
    proposal_id = 2
    option_index = 1
    mock_update_callback.callback_query.data = f"vote_{proposal_id}_{option_index}"

    # Mock AsyncSessionLocal context manager behavior
    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager

    mock_user_service_instance = AsyncMock(spec=UserService)
    mock_user_service_class.return_value = mock_user_service_instance

    mock_submission_service_instance = AsyncMock(spec=SubmissionService)
    mock_submission_service_instance.record_vote.return_value = (False, "Proposal is closed.")
    mock_submission_service_class.return_value = mock_submission_service_instance

    await handle_vote_callback(mock_update_callback, mock_context)

    mock_update_callback.callback_query.answer.assert_called_once_with(text="Proposal is closed.", show_alert=True)

@pytest.mark.asyncio
@patch('app.telegram_handlers.callback_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.callback_handlers.UserService', side_effect=Exception("User service boom!"))
async def test_handle_vote_callback_user_service_exception(
    mock_user_service_class, mock_async_session, mock_update_callback, mock_context
):
    proposal_id = 3
    option_index = 0
    mock_update_callback.callback_query.data = f"vote_{proposal_id}_{option_index}"

    # Mock AsyncSessionLocal context manager behavior
    mock_session_context_manager = AsyncMock()
    mock_session = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    mock_session_context_manager.__aexit__.return_value = None
    mock_async_session.return_value = mock_session_context_manager
    
    # UserService is patched to raise an exception, no instance needed here

    await handle_vote_callback(mock_update_callback, mock_context)

    mock_update_callback.callback_query.answer.assert_called_once_with(
        text="An unexpected error occurred while processing your vote. Please try again.", show_alert=True
    )

# Remove placeholder
# def test_placeholder():
#     assert True 