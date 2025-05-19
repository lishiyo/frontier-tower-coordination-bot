"""Unit tests for command handlers."""
import pytest
from unittest.mock import AsyncMock, patch
from telegram import Update, User, Message, Chat
from app.telegram_handlers.command_handlers import start_command, help_command


@pytest.fixture
def mock_update():
    """Create a mock Update object with a user and message."""
    mock_user = AsyncMock(spec=User)
    mock_user.id = 12345
    mock_user.first_name = "Test"
    mock_user.username = "test_user"
    
    mock_message = AsyncMock(spec=Message)
    mock_message.reply_text = AsyncMock()
    
    mock_chat = AsyncMock(spec=Chat)
    mock_chat.id = 12345
    
    mock_message.chat = mock_chat
    
    mock_update = AsyncMock(spec=Update)
    mock_update.effective_user = mock_user
    mock_update.message = mock_message
    
    return mock_update


@pytest.fixture
def mock_context():
    """Create a mock context object."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_start_command_with_user(mock_update, mock_context):
    """Test the start command when a user is present."""
    # Call the start command
    await start_command(mock_update, mock_context)
    
    # Check that reply_text was called once
    mock_update.message.reply_text.assert_called_once()
    
    # Verify the welcome message format contains the user's name and key components
    called_args = mock_update.message.reply_text.call_args[0][0]
    assert f"Hello {mock_update.effective_user.first_name}" in called_args
    assert "I can help you create proposals" in called_args
    assert "/help" in called_args


@pytest.mark.asyncio
async def test_start_command_without_user(mock_update, mock_context):
    """Test the start command when no user is present."""
    # Remove the user from the update
    mock_update.effective_user = None
    
    # Call the start command
    await start_command(mock_update, mock_context)
    
    # Check that reply_text was called once
    mock_update.message.reply_text.assert_called_once()
    
    # Verify the welcome message format for no user
    called_args = mock_update.message.reply_text.call_args[0][0]
    assert "Hello! Welcome to CoordinationBot" in called_args
    assert "/help" in called_args


@pytest.mark.asyncio
async def test_help_command_with_user(mock_update, mock_context):
    """Test the help command when a user is present."""
    # Call the help command
    await help_command(mock_update, mock_context)
    
    # Check that reply_text was called once
    mock_update.message.reply_text.assert_called_once()
    
    # Verify the help message contains key sections and commands
    called_args = mock_update.message.reply_text.call_args[0][0]
    assert "Here's how I can assist you:" in called_args
    assert "General Commands:" in called_args
    assert "/start" in called_args
    assert "/help" in called_args
    assert "/privacy" in called_args
    assert "Proposals &amp; Voting:" in called_args
    assert "/propose" in called_args
    assert "Information:" in called_args
    assert "/ask" in called_args
    # Not checking Admin section for now as it might change


@pytest.mark.asyncio
async def test_help_command_without_user(mock_update, mock_context):
    """Test the help command when no user is present."""
    # Remove the user from the update
    mock_update.effective_user = None
    
    # Call the help command
    await help_command(mock_update, mock_context)
    
    # Check that reply_text was called once
    mock_update.message.reply_text.assert_called_once()
    
    # The help message content should be the same regardless of whether a user is present
    called_args = mock_update.message.reply_text.call_args[0][0]
    assert "Here's how I can assist you:" in called_args 