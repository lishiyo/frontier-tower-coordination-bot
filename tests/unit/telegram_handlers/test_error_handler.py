import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import logging
import html
import json

from telegram import Update
from telegram.ext import ContextTypes

from app.telegram_handlers.error_handler import error_handler

@pytest.mark.asyncio
async def test_error_handler_logs_and_replies(caplog):
    """Test that the error_handler logs the exception and attempts to reply to the user."""
    caplog.set_level(logging.ERROR)

    mock_update = MagicMock(spec=Update)
    mock_update.effective_message = AsyncMock()
    update_dict = {"id": 123, "message": {"text": "test"}}
    mock_update.to_dict.return_value = update_dict

    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_context.error = ValueError("Test exception")
    mock_context.chat_data = {"key": "chat_value"}
    mock_context.user_data = {"key": "user_value"}

    await error_handler(mock_update, mock_context)

    # Check if the error was logged
    assert "Test exception" in caplog.text
    assert "Exception while handling an update:" in caplog.text
    expected_update_log = f"<pre>update = {html.escape(json.dumps(update_dict, indent=2, ensure_ascii=False))}</pre>"
    assert expected_update_log in caplog.text
    assert f"<pre>context.chat_data = {html.escape(str(mock_context.chat_data))}</pre>" in caplog.text
    assert f"<pre>context.user_data = {html.escape(str(mock_context.user_data))}</pre>" in caplog.text

    # Check if reply_text was called
    mock_update.effective_message.reply_text.assert_called_once_with(
        "Sorry, something went wrong. The developers have been notified. Please try again later."
    )

@pytest.mark.asyncio
async def test_error_handler_callback_query(caplog):
    """Test error_handler with a callback_query update."""
    caplog.set_level(logging.ERROR)

    mock_update = MagicMock(spec=Update)
    mock_update.effective_message = None # No direct message
    mock_update.callback_query = AsyncMock()
    mock_update.callback_query.answer = AsyncMock()
    update_dict_callback = {"id": 456, "callback_query": {"data": "test_callback"}}
    mock_update.to_dict.return_value = update_dict_callback

    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_context.error = TypeError("Another Test exception")
    mock_context.chat_data = {}
    mock_context.user_data = {}
    mock_context.bot = AsyncMock() # Mock bot for sending follow-up message if needed

    await error_handler(mock_update, mock_context)

    assert "Another Test exception" in caplog.text
    expected_update_log_callback = f"<pre>update = {html.escape(json.dumps(update_dict_callback, indent=2, ensure_ascii=False))}</pre>"
    assert expected_update_log_callback in caplog.text

    mock_update.callback_query.answer.assert_called_once_with(
        "Sorry, something went wrong. The developers have been notified. Please try again later.",
        show_alert=True
    )
    # In this setup, we don't expect a follow-up message by default
    mock_context.bot.send_message.assert_not_called()

@pytest.mark.asyncio
async def test_error_handler_no_update_object(caplog):
    """Test error_handler when update is not an Update instance."""
    caplog.set_level(logging.ERROR)

    # Simulate an update object that is not an instance of Update
    mock_non_update_object = "This is not an Update object"
    
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_context.error = ConnectionError("Network issue")
    mock_context.chat_data = {}
    mock_context.user_data = {}

    await error_handler(mock_non_update_object, mock_context)

    assert "Network issue" in caplog.text
    assert "Exception while handling an update:" in caplog.text
    # Verify that str(update) was used for logging
    # When update is not an Update instance, update_str becomes str(update),
    # and then json.dumps is called on that string, which adds quotes.
    expected_update_log_non_obj = f"<pre>update = {html.escape(json.dumps(str(mock_non_update_object), indent=2, ensure_ascii=False))}</pre>"
    assert expected_update_log_non_obj in caplog.text
    # No reply should be attempted if it's not an Update object with effective_message or callback_query
    assert "Error sending error message to user" not in caplog.text # No attempt to send message 