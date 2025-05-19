import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import re

from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

from app.telegram_handlers.submission_command_handlers import submit_command, handle_prefilled_submit

# Common mock objects
@pytest.fixture
def mock_update_submission():
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    update.message.text = ""
    return update

@pytest.fixture
def mock_context_submission():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.args = []
    context.bot = MagicMock()
    context.bot.username = "TestBotName"
    return context

@patch("app.telegram_handlers.submission_command_handlers.AsyncSessionLocal")
@patch("app.telegram_handlers.submission_command_handlers.SubmissionService")
@pytest.mark.asyncio
async def test_submit_command_success(
    mock_submission_service_class, mock_async_session_local, 
    mock_update_submission, mock_context_submission
):
    """Test /submit command successfully records a submission."""
    mock_context_submission.args = ["1", "This", "is", "my", "submission"]
    
    mock_session = AsyncMock()
    mock_async_session_local.return_value.__aenter__.return_value = mock_session
    mock_async_session_local.return_value.__aexit__.return_value = None

    mock_submission_service_instance = AsyncMock()
    mock_submission_service_instance.record_free_form_submission.return_value = (True, "Submission recorded!")
    mock_submission_service_class.return_value = mock_submission_service_instance

    await submit_command(mock_update_submission, mock_context_submission)

    mock_submission_service_instance.record_free_form_submission.assert_called_once_with(
        proposal_id=1,
        submitter_telegram_id=12345,
        text_submission="This is my submission"
    )
    mock_update_submission.message.reply_text.assert_called_once_with("Submission recorded!")

@pytest.mark.asyncio
async def test_submit_command_no_args(mock_update_submission, mock_context_submission):
    """Test /submit command with no arguments."""
    mock_context_submission.args = []
    await submit_command(mock_update_submission, mock_context_submission)
    mock_update_submission.message.reply_text.assert_called_once_with(
        "Usage: /submit <proposal_id> <your text submission>\n"
        "Example: /submit 123 This is my great idea for the community event!"
    )

@pytest.mark.asyncio
async def test_submit_command_one_arg(mock_update_submission, mock_context_submission):
    """Test /submit command with only proposal_id argument."""
    mock_context_submission.args = ["1"]
    await submit_command(mock_update_submission, mock_context_submission)
    mock_update_submission.message.reply_text.assert_called_once_with(
        "Usage: /submit <proposal_id> <your text submission>\n"
        "Example: /submit 123 This is my great idea for the community event!"
    )

@pytest.mark.asyncio
async def test_submit_command_invalid_proposal_id(mock_update_submission, mock_context_submission):
    """Test /submit command with an invalid (non-numeric) proposal_id."""
    mock_context_submission.args = ["abc", "My", "submission"]
    await submit_command(mock_update_submission, mock_context_submission)
    mock_update_submission.message.reply_text.assert_called_once_with(
        "Invalid proposal ID: 'abc'. Please provide a numeric ID."
    )

@patch("app.telegram_handlers.submission_command_handlers.AsyncSessionLocal")
@patch("app.telegram_handlers.submission_command_handlers.SubmissionService")
@pytest.mark.asyncio
async def test_submit_command_service_failure(
    mock_submission_service_class, mock_async_session_local, 
    mock_update_submission, mock_context_submission
):
    """Test /submit command when SubmissionService fails."""
    mock_context_submission.args = ["2", "Another", "submission"]
    
    mock_session = AsyncMock()
    mock_async_session_local.return_value.__aenter__.return_value = mock_session
    mock_async_session_local.return_value.__aexit__.return_value = None

    mock_submission_service_instance = AsyncMock()
    mock_submission_service_instance.record_free_form_submission.return_value = (False, "Failed to record.")
    mock_submission_service_class.return_value = mock_submission_service_instance

    await submit_command(mock_update_submission, mock_context_submission)

    mock_submission_service_instance.record_free_form_submission.assert_called_once_with(
        proposal_id=2,
        submitter_telegram_id=12345,
        text_submission="Another submission"
    )
    mock_update_submission.message.reply_text.assert_called_once_with("Failed to record.")


# Tests for handle_prefilled_submit

@patch("app.telegram_handlers.submission_command_handlers.submit_command", new_callable=AsyncMock) # Patch the original submit_command
@pytest.mark.asyncio
async def test_handle_prefilled_submit_success(mock_original_submit_command, mock_update_submission, mock_context_submission):
    """Test handle_prefilled_submit successfully parses and calls submit_command."""
    mock_update_submission.message.text = "@TestBotName submit 123 This is a prefilled submission."
    
    await handle_prefilled_submit(mock_update_submission, mock_context_submission)

    # Check that the original submit_command was called with the correct update and context
    # The context.args should be modified by handle_prefilled_submit
    mock_original_submit_command.assert_called_once()
    called_update, called_context = mock_original_submit_command.call_args[0]
    assert called_update is mock_update_submission
    assert called_context is mock_context_submission
    assert called_context.args == ["123", "This", "is", "a", "prefilled", "submission."]

@patch("app.telegram_handlers.submission_command_handlers.submit_command", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_handle_prefilled_submit_different_bot_name(mock_original_submit_command, mock_update_submission, mock_context_submission):
    """Test handle_prefilled_submit ignores messages for different bot names."""
    mock_update_submission.message.text = "@OtherBot submit 123 This is a prefilled submission."
    
    await handle_prefilled_submit(mock_update_submission, mock_context_submission)
    mock_original_submit_command.assert_not_called()

@patch("app.telegram_handlers.submission_command_handlers.submit_command", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_handle_prefilled_submit_no_match(mock_original_submit_command, mock_update_submission, mock_context_submission):
    """Test handle_prefilled_submit ignores messages that don't match the pattern."""
    mock_update_submission.message.text = "This is a regular message, not a prefilled submit."
    
    await handle_prefilled_submit(mock_update_submission, mock_context_submission)
    mock_original_submit_command.assert_not_called()

@patch("app.telegram_handlers.submission_command_handlers.submit_command", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_handle_prefilled_submit_no_text(mock_original_submit_command, mock_update_submission, mock_context_submission):
    """Test handle_prefilled_submit with empty submission text after proposal ID."""
    mock_update_submission.message.text = "@TestBotName submit 456 "
    
    await handle_prefilled_submit(mock_update_submission, mock_context_submission)
    
    mock_original_submit_command.assert_called_once()
    _, called_context = mock_original_submit_command.call_args[0]
    assert called_context.args == ["456"] # The submit_command itself will handle if text is missing

@patch("app.telegram_handlers.submission_command_handlers.submit_command", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_handle_prefilled_submit_case_insensitivity_and_spacing(mock_original_submit_command, mock_update_submission, mock_context_submission):
    """Test handle_prefilled_submit with varied casing and spacing."""
    mock_update_submission.message.text = "  @tEsTbOtNaMe    SuBmIt   789   My awesome idea  is great!   "
    
    await handle_prefilled_submit(mock_update_submission, mock_context_submission)
    
    mock_original_submit_command.assert_called_once()
    _, called_context = mock_original_submit_command.call_args[0]
    assert called_context.args == ["789", "My", "awesome", "idea", "is", "great!"]

@patch("app.telegram_handlers.submission_command_handlers.submit_command", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_handle_prefilled_submit_no_message_text(mock_original_submit_command, mock_update_submission, mock_context_submission):
    """Test handle_prefilled_submit when update.message.text is None."""
    mock_update_submission.message.text = None
    
    await handle_prefilled_submit(mock_update_submission, mock_context_submission)
    mock_original_submit_command.assert_not_called() 