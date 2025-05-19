import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User as TelegramUser, Chat
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.telegram_handlers.user_command_handlers import my_votes_command
from app.core.submission_service import SubmissionService # For type hinting and patching
from app.core.user_service import UserService # For patching register_user_interaction
from app.utils import telegram_utils # For send_message_in_chunks

@pytest.mark.asyncio
async def test_my_votes_command_user_has_votes():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    mock_effective_user = TelegramUser(id=123, first_name="TestUser", is_bot=False)
    mock_chat = Chat(id=123, type='private')
    mock_update.effective_user = mock_effective_user
    mock_update.effective_chat = mock_chat # Make sure effective_chat is present
    mock_update.message = MagicMock()
    mock_update.message.reply_text = AsyncMock()

    mock_context.bot = AsyncMock()
    mock_context.bot.send_message = AsyncMock()

    formatted_history = [
        {"proposal_id": 1, "proposal_title": "Prop Alpha", "user_response": "Voted Yes", "proposal_status": "Open", "proposal_outcome": "N/A", "submission_timestamp": "2023-01-01 PST"},
        {"proposal_id": 2, "proposal_title": "Prop Beta", "user_response": "My Idea X", "proposal_status": "Closed", "proposal_outcome": "Finalized", "submission_timestamp": "2023-01-02 PST"}
    ]
    expected_message = (
        "*Your Votes & Submissions:*\n\n"
        "\\- Proposal: *Prop Alpha*\n"
        "  Your Vote/Submission: `Voted Yes`\n"
        "  Status/Outcome: `Open`\n"
        "  Submitted: `2023-01-01 PST`\n\n"
        "\\- Proposal: *Prop Beta*\n"
        "  Your Vote/Submission: `My Idea X`\n"
        "  Status/Outcome: `Closed - Finalized`\n"
        "  Submitted: `2023-01-02 PST`"
    )

    # Mock for the session instance that __aenter__ will return
    mock_session_instance = AsyncMock()

    with patch('app.telegram_handlers.user_command_handlers.get_session', new_callable=MagicMock) as mock_get_session_function:
        # Configure the mock for the get_session() call
        # get_session() should return an async context manager
        mock_async_context_manager = AsyncMock() # This is the object returned by get_session()
        mock_async_context_manager.__aenter__.return_value = mock_session_instance # __aenter__ returns the session
        mock_async_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_get_session_function.return_value = mock_async_context_manager

        with patch('app.telegram_handlers.user_command_handlers.UserService') as MockUserService:
            with patch('app.telegram_handlers.user_command_handlers.SubmissionService') as MockSubmissionService:
                mock_user_service_instance = MockUserService.return_value
                mock_user_service_instance.register_user_interaction = AsyncMock()

                mock_submission_service_instance = MockSubmissionService.return_value
                mock_submission_service_instance.get_user_submission_history = AsyncMock(return_value=formatted_history)

                await my_votes_command(mock_update, mock_context)

                mock_get_session_function.assert_called_once() # Ensure get_session() was called
                MockUserService.assert_called_once_with(mock_session_instance)
                MockSubmissionService.assert_called_once_with(mock_session_instance)
                mock_user_service_instance.register_user_interaction.assert_called_once()
                mock_submission_service_instance.get_user_submission_history.assert_called_once_with(submitter_id=123)
                mock_update.message.reply_text.assert_called()
                args, kwargs = mock_update.message.reply_text.call_args
                assert kwargs.get('parse_mode') == ParseMode.MARKDOWN_V2
                assert "Prop Alpha" in args[0]
                assert "Prop Beta" in args[0]

@pytest.mark.asyncio
async def test_my_votes_command_no_votes():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_effective_user = TelegramUser(id=123, first_name="TestUser", is_bot=False, username="test_user")
    mock_chat = Chat(id=123, type='private')
    mock_update.effective_user = mock_effective_user
    mock_update.effective_chat = mock_chat
    mock_update.message = MagicMock()
    mock_update.message.reply_text = AsyncMock()

    expected_message = "You haven't made any submissions or cast any votes yet."

    mock_session_instance = AsyncMock()

    with patch('app.telegram_handlers.user_command_handlers.get_session', new_callable=MagicMock) as mock_get_session_function:
        mock_async_context_manager = AsyncMock()
        mock_async_context_manager.__aenter__.return_value = mock_session_instance
        mock_async_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_get_session_function.return_value = mock_async_context_manager

        with patch('app.telegram_handlers.user_command_handlers.UserService') as MockUserService:
            with patch('app.telegram_handlers.user_command_handlers.SubmissionService') as MockSubmissionService:
                mock_user_service_instance = MockUserService.return_value
                mock_user_service_instance.register_user_interaction = AsyncMock()

                mock_submission_service_instance = MockSubmissionService.return_value
                mock_submission_service_instance.get_user_submission_history = AsyncMock(return_value=[]) # No history

                await my_votes_command(mock_update, mock_context)
                
                mock_get_session_function.assert_called_once()
                MockUserService.assert_called_once_with(mock_session_instance)
                MockSubmissionService.assert_called_once_with(mock_session_instance)
                mock_update.message.reply_text.assert_called_once_with(expected_message)

@pytest.mark.asyncio
async def test_my_votes_command_no_effective_user():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_update.effective_user = None # No user
    mock_update.message = MagicMock()
    mock_update.message.reply_text = AsyncMock() # Setup reply_text on the message mock

    # Act
    await my_votes_command(mock_update, mock_context)

    # Assert
    mock_update.message.reply_text.assert_called_once_with(
        "Could not identify user." # Updated to match actual message
    ) 