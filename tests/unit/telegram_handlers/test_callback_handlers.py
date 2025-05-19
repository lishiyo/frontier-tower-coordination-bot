import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from telegram import Update, User, Message, Chat, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler, Application
from telegram.constants import ParseMode

from app.telegram_handlers.callback_handlers import (
    handle_collect_proposal_type_callback,
    handle_vote_callback,
    handle_proposal_filter_callback
)
from app.telegram_handlers.conversation_defs import (
    COLLECT_PROPOSAL_TYPE, COLLECT_OPTIONS, ASK_DURATION,
    USER_DATA_PROPOSAL_TYPE, PROPOSAL_TYPE_CALLBACK,
    PROPOSAL_FILTER_OPEN,
    PROPOSAL_FILTER_CLOSED,
    PROPOSAL_FILTER_CALLBACK_PREFIX
)
from app.persistence.models.proposal_model import ProposalType, ProposalStatus
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

# Tests for handle_proposal_filter_callback

@pytest.mark.asyncio
async def test_handle_proposal_filter_callback_open():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    mock_callback_query = AsyncMock(spec=CallbackQuery)
    mock_callback_query.data = PROPOSAL_FILTER_OPEN
    mock_callback_query.answer = AsyncMock()
    mock_callback_query.edit_message_text = AsyncMock()
    mock_callback_query.from_user = MagicMock(id=12345) # For logger
    
    mock_update.callback_query = mock_callback_query
    
    mock_session_instance = AsyncMock()
    mock_async_session_local_callable = MagicMock()
    mock_async_session_local_callable.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_async_session_local_callable.return_value.__aexit__ = AsyncMock(return_value=None)

    # Mock data returned by ProposalService.list_proposals_by_status
    proposals_data_open = [
        {
            "id": 1, "title": "Open Prop 1", "status": "OPEN", 
            "target_channel_id": "-1001", "channel_message_id": "11",
            "deadline_date": "2024-01-01 PST"
        },
        {
            "id": 2, "title": "Open Prop 2", "status": "OPEN", 
            "target_channel_id": "-1002", "channel_message_id": "22",
            "deadline_date": "2024-02-01 PST"
        }
    ]
    # Expected formatted message (simplified for brevity, adapt to your exact formatting)
    expected_formatted_list = (
        '*Open Proposals:*\n\n'
        '\- *ID:* `1` *Title:* Open Prop 1\n'
        '  [Channel: \-1001](https://t.me/c/1/11)\n'
        '  *Voting ends:* 2024\-01\-01 PST\n\n'
        '\- *ID:* `2` *Title:* Open Prop 2\n'
        '  [Channel: \-1002](https://t.me/c/2/22)\n'
        '  *Voting ends:* 2024\-02\-01 PST\n'
    )


    with patch('app.telegram_handlers.callback_handlers.AsyncSessionLocal', mock_async_session_local_callable):
        with patch('app.telegram_handlers.callback_handlers.ProposalService') as MockProposalService:
            mock_proposal_service_instance = MockProposalService.return_value
            mock_proposal_service_instance.list_proposals_by_status = AsyncMock(return_value=proposals_data_open)

            # Act
            await handle_proposal_filter_callback(mock_update, mock_context)

            # Assert
            MockProposalService.assert_called_once_with(mock_session_instance)
            mock_proposal_service_instance.list_proposals_by_status.assert_called_once_with(ProposalStatus.OPEN.value)
            mock_callback_query.edit_message_text.assert_called_once_with(
                text=expected_formatted_list,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            mock_callback_query.answer.assert_called_once()

@pytest.mark.asyncio
async def test_handle_proposal_filter_callback_closed():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    mock_callback_query = AsyncMock(spec=CallbackQuery)
    mock_callback_query.data = PROPOSAL_FILTER_CLOSED
    mock_callback_query.answer = AsyncMock()
    mock_callback_query.edit_message_text = AsyncMock()
    mock_callback_query.from_user = MagicMock(id=12345) # For logger
    
    mock_update.callback_query = mock_callback_query
    
    mock_session_instance = AsyncMock()
    mock_async_session_local_callable = MagicMock()
    mock_async_session_local_callable.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_async_session_local_callable.return_value.__aexit__ = AsyncMock(return_value=None)

    proposals_data_closed = [
        {
            "id": 3, "title": "Closed Prop 1", "status": "CLOSED", 
            "target_channel_id": "-1003", "channel_message_id": "33",
            "closed_date": "2023-12-01 PST", "outcome": "Result A"
        }
    ]
    expected_formatted_list = (
        '*Closed Proposals:*\n\n'
        '\- *ID:* `3` *Title:* Closed Prop 1\n'
        '  [Channel: \-1003](https://t.me/c/3/33)\n'
        '  *Closed on:* 2023\-12\-01 PST\n'
        '  *Outcome:* Result A\n'
    )

    with patch('app.telegram_handlers.callback_handlers.AsyncSessionLocal', mock_async_session_local_callable):
        with patch('app.telegram_handlers.callback_handlers.ProposalService') as MockProposalService:
            mock_proposal_service_instance = MockProposalService.return_value
            mock_proposal_service_instance.list_proposals_by_status = AsyncMock(return_value=proposals_data_closed)

            # Act
            await handle_proposal_filter_callback(mock_update, mock_context)

            # Assert
            MockProposalService.assert_called_once_with(mock_session_instance)
            mock_proposal_service_instance.list_proposals_by_status.assert_called_once_with(ProposalStatus.CLOSED.value)
            mock_callback_query.edit_message_text.assert_called_once_with(
                text=expected_formatted_list,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            mock_callback_query.answer.assert_called_once()

@pytest.mark.asyncio
async def test_handle_proposal_filter_callback_open_no_proposals():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_callback_query = AsyncMock(spec=CallbackQuery)
    mock_callback_query.data = PROPOSAL_FILTER_OPEN
    mock_callback_query.answer = AsyncMock()
    mock_callback_query.edit_message_text = AsyncMock()
    mock_callback_query.from_user = MagicMock(id=12345)
    mock_update.callback_query = mock_callback_query
    
    mock_session_instance = AsyncMock()
    mock_async_session_local_callable = MagicMock()
    mock_async_session_local_callable.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_async_session_local_callable.return_value.__aexit__ = AsyncMock(return_value=None)

    # Corrected expected text to match the handler change
    expected_text_no_proposals = '*Open Proposals:*\n\nNo proposals found\\.'

    with patch('app.telegram_handlers.callback_handlers.AsyncSessionLocal', mock_async_session_local_callable):
        with patch('app.telegram_handlers.callback_handlers.ProposalService') as MockProposalService:
            mock_proposal_service_instance = MockProposalService.return_value
            mock_proposal_service_instance.list_proposals_by_status = AsyncMock(return_value=[]) # Empty list

            # Act
            await handle_proposal_filter_callback(mock_update, mock_context)

            # Assert
            mock_proposal_service_instance.list_proposals_by_status.assert_called_once_with(ProposalStatus.OPEN.value)
            mock_callback_query.edit_message_text.assert_called_once_with(
                text=expected_text_no_proposals,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            mock_callback_query.answer.assert_called_once()

@pytest.mark.asyncio
async def test_handle_proposal_filter_callback_unknown_data():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    mock_callback_query = AsyncMock(spec=CallbackQuery)
    mock_callback_query.data = "some_unknown_filter_action" # Not OPEN or CLOSED
    mock_callback_query.answer = AsyncMock()
    mock_callback_query.edit_message_text = AsyncMock()
    
    mock_update.callback_query = mock_callback_query
    
    mock_session_instance = AsyncMock()
    mock_async_session_local_callable = MagicMock()
    mock_async_session_local_callable.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_async_session_local_callable.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch('app.telegram_handlers.callback_handlers.AsyncSessionLocal', mock_async_session_local_callable):
        with patch('app.telegram_handlers.callback_handlers.ProposalService') as MockProposalService:
            with patch('app.telegram_handlers.callback_handlers.logger.warning') as mock_logger_warning:
                mock_proposal_service_instance = MockProposalService.return_value
                mock_proposal_service_instance.list_proposals_by_status = AsyncMock()

                # Act
                await handle_proposal_filter_callback(mock_update, mock_context)

                # Assert
                MockProposalService.assert_not_called()
                mock_proposal_service_instance.list_proposals_by_status.assert_not_called()
                
                mock_callback_query.edit_message_text.assert_called_once_with(text="Invalid selection. Please try again.")
                
                mock_logger_warning.assert_called_once_with(f"Invalid callback data for proposal filter: {mock_callback_query.data}")
                
                mock_callback_query.answer.assert_called_once_with()

@pytest.mark.asyncio
async def test_handle_proposal_filter_callback_no_query():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_update.callback_query = None # No callback query

    with patch('app.telegram_handlers.callback_handlers.logger.error') as mock_logger_error:
        # Act
        await handle_proposal_filter_callback(mock_update, mock_context)

        # Assert
        mock_logger_error.assert_called_once_with("handle_proposal_filter_callback called without callback_query.")
        # Ensure no other actions like edit_message_text or answer are attempted
        # (implicitly tested as mocks for those aren't set up on update/context directly here)

# Remove placeholder
# def test_placeholder():
#     assert True 