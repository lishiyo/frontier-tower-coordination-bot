import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User as TelegramUser, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.telegram_handlers.proposal_command_handlers import my_proposals_command, proposals_command
from app.core.proposal_service import ProposalService # For patching
from app.core.user_service import UserService # For patching
from app.utils import telegram_utils # For send_message_in_chunks
from app.persistence.models.proposal_model import ProposalType, ProposalStatus # For sample data
from app.telegram_handlers.conversation_defs import (
    PROPOSAL_FILTER_CALLBACK_PREFIX,
    PROPOSAL_FILTER_OPEN,
    PROPOSAL_FILTER_CLOSED
)

@pytest.mark.asyncio
async def test_my_proposals_command_user_has_proposals():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    
    mock_effective_user = TelegramUser(id=123, first_name="TestProposer", is_bot=False, username="testproposer")
    mock_chat = Chat(id=123, type='private')
    mock_update.effective_user = mock_effective_user
    mock_update.effective_chat = mock_chat
    mock_update.message = MagicMock()
    mock_update.message.chat_id = mock_chat.id
    mock_update.message.reply_text = AsyncMock()

    # Mock data from ProposalService.list_proposals_by_proposer
    formatted_proposals_data = [
        {
            "id": 1, "title": "Prop Alpha", "status": ProposalStatus.OPEN,
            "deadline_date": "2023-12-01 PST", "creation_date": "2023-11-01 PST",
            "outcome": None, "target_channel_id": "-1001",
            "proposal_type": ProposalType.MULTIPLE_CHOICE,
            "channel_message_id": "111"
        },
        {
            "id": 2, "title": "Prop Beta", "status": ProposalStatus.CLOSED,
            "deadline_date": "2023-11-15 PST", "creation_date": "2023-10-15 PST",
            "outcome": "Beta idea selected", "target_channel_id": "-100200",
            "proposal_type": ProposalType.FREE_FORM,
            "channel_message_id": "222"
        },
        {
            "id": 3, "title": "Prop Gamma (No Msg ID)", "status": ProposalStatus.OPEN,
            "deadline_date": "2023-12-15 PST", "creation_date": "2023-11-15 PST",
            "outcome": None, "target_channel_id": "-1003",
            "proposal_type": ProposalType.MULTIPLE_CHOICE,
            "channel_message_id": None
        }
    ]

    expected_final_message = (
        '*Your Proposals:*\n\n'
        '\- *Title:* Prop Alpha \(ID: `1`\)\n'
        '  Status: open\n'
        '  Type: multiple\_choice\n'
        '  [Channel: \-1001](https://t.me/c/1/111)\n'
        '  Created: 2023\-11\-01 PST\n'
        '  Deadline: 2023\-12\-01 PST\n'
        '  Outcome: N/A\n\n'
        '\- *Title:* Prop Beta \(ID: `2`\)\n'
        '  Status: closed\n'
        '  Type: free\_form\n'
        '  [Channel: \-100200](https://t.me/c/200/222)\n'
        '  Created: 2023\-10\-15 PST\n'
        '  Deadline: 2023\-11\-15 PST\n'
        '  Outcome: Beta idea selected\n\n'
        '\- *Title:* Prop Gamma \(No Msg ID\) \(ID: `3`\)\n'
        '  Status: open\n'
        '  Type: multiple\_choice\n'
        '  Channel ID: `\-1003`\n'
        '  Created: 2023\-11\-15 PST\n'
        '  Deadline: 2023\-12\-15 PST\n'
        '  Outcome: N/A\n'
    )

    mock_session_instance = AsyncMock()
    mock_async_session_local_callable = MagicMock()
    mock_async_session_local_callable.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_async_session_local_callable.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal', mock_async_session_local_callable):
        with patch('app.telegram_handlers.proposal_command_handlers.UserService') as MockUserService:
            with patch('app.telegram_handlers.proposal_command_handlers.ProposalService') as MockProposalService:
                with patch('app.telegram_handlers.proposal_command_handlers.telegram_utils.send_message_in_chunks', new_callable=AsyncMock) as mock_send_chunks:
                    mock_user_service_instance = MockUserService.return_value
                    mock_user_service_instance.register_user_interaction = AsyncMock()
                    mock_proposal_service_instance = MockProposalService.return_value
                    mock_proposal_service_instance.list_proposals_by_proposer = AsyncMock(return_value=formatted_proposals_data)

                    await my_proposals_command(mock_update, mock_context)

                    MockUserService.assert_called_once_with(mock_session_instance)
                    MockProposalService.assert_called_once_with(mock_session_instance)
                    mock_user_service_instance.register_user_interaction.assert_called_once_with(
                        telegram_id=123, username="testproposer", first_name="TestProposer"
                    )
                    mock_proposal_service_instance.list_proposals_by_proposer.assert_called_once_with(123)
                    mock_send_chunks.assert_called_once_with(
                        mock_context,
                        chat_id=mock_chat.id,
                        text=expected_final_message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )

@pytest.mark.asyncio
async def test_my_proposals_command_no_proposals():
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_effective_user = TelegramUser(id=123, first_name="TestProposer", is_bot=False, username="testproposer")
    mock_chat = Chat(id=123, type='private')
    mock_update.effective_user = mock_effective_user
    mock_update.effective_chat = mock_chat
    mock_update.message = MagicMock()
    mock_update.message.chat_id = mock_chat.id
    mock_update.message.reply_text = AsyncMock()

    expected_message = "You haven't created any proposals yet."
    mock_session_instance = AsyncMock()
    mock_async_session_local_callable = MagicMock()
    mock_async_session_local_callable.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_async_session_local_callable.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal', mock_async_session_local_callable):
        with patch('app.telegram_handlers.proposal_command_handlers.UserService') as MockUserService:
            with patch('app.telegram_handlers.proposal_command_handlers.ProposalService') as MockProposalService:
                with patch('app.telegram_handlers.proposal_command_handlers.telegram_utils.send_message_in_chunks', new_callable=AsyncMock) as mock_send_chunks:
                    mock_user_service_instance = MockUserService.return_value
                    mock_user_service_instance.register_user_interaction = AsyncMock()
                    mock_proposal_service_instance = MockProposalService.return_value
                    mock_proposal_service_instance.list_proposals_by_proposer = AsyncMock(return_value=[])

                    await my_proposals_command(mock_update, mock_context)

                    mock_send_chunks.assert_called_once_with(
                        mock_context,
                        chat_id=mock_chat.id,
                        text=expected_message,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )

@pytest.mark.asyncio
async def test_my_proposals_command_no_effective_user():
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_update.effective_user = None
    mock_update.message = MagicMock()
    mock_update.message.reply_text = AsyncMock()

    await my_proposals_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with("Could not retrieve your user details.")

@pytest.mark.asyncio
async def test_proposals_command_no_args_shows_buttons():
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_effective_user = TelegramUser(id=789, first_name="Test User", is_bot=False)
    mock_update.effective_user = mock_effective_user
    mock_update.message = MagicMock()
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = []

    await proposals_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert call_args is not None
    assert call_args.args[0] == "Which proposals would you like to see?"
    
    reply_markup = call_args.kwargs.get('reply_markup')
    assert isinstance(reply_markup, InlineKeyboardMarkup)
    assert len(reply_markup.inline_keyboard) == 2
    assert len(reply_markup.inline_keyboard[0]) == 1
    assert len(reply_markup.inline_keyboard[1]) == 1

    button_open = reply_markup.inline_keyboard[0][0]
    assert button_open.text == "Open Proposals"
    assert button_open.callback_data == PROPOSAL_FILTER_OPEN

    button_closed = reply_markup.inline_keyboard[1][0]
    assert button_closed.text == "Closed Proposals"
    assert button_closed.callback_data == PROPOSAL_FILTER_CLOSED

@pytest.mark.asyncio
async def test_proposals_command_with_open_arg():
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_effective_user = TelegramUser(id=789, first_name="Test User", is_bot=False)
    mock_chat = Chat(id=456, type='private')
    mock_update.effective_user = mock_effective_user
    mock_update.message = MagicMock()
    mock_update.message.chat_id = mock_chat.id
    mock_context.args = ["open"]

    proposals_data_open = [
        {"id": 1, "title": "Open Prop 1", "target_channel_id": "-1001", "channel_message_id": "11", "deadline_date": "2024-01-01 PST"},
    ]
    expected_formatted_list = (
        '*Open Proposals:*\n\n'
        '\- *ID:* `1` *Title:* Open Prop 1\n'
        '  [Channel: \-1001](https://t.me/c/1/11)\n'
        '  *Voting ends:* 2024\-01\-01 PST\n'
    )
    
    mock_session_instance = AsyncMock()
    mock_async_session_local_callable = MagicMock()
    mock_async_session_local_callable.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_async_session_local_callable.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal', mock_async_session_local_callable):
        with patch('app.telegram_handlers.proposal_command_handlers.ProposalService') as MockProposalService:
            with patch('app.telegram_handlers.proposal_command_handlers.telegram_utils.send_message_in_chunks', new_callable=AsyncMock) as mock_send_chunks:
                mock_proposal_service_instance = MockProposalService.return_value
                mock_proposal_service_instance.list_proposals_by_status = AsyncMock(return_value=proposals_data_open)

                await proposals_command(mock_update, mock_context)

                mock_send_chunks.assert_called_once_with(
                    mock_context,
                    chat_id=mock_chat.id,
                    text=expected_formatted_list,
                    parse_mode=ParseMode.MARKDOWN_V2
                )

@pytest.mark.asyncio
async def test_proposals_command_with_closed_arg():
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_effective_user = TelegramUser(id=789, first_name="Test User", is_bot=False)
    mock_chat = Chat(id=456, type='private')
    mock_update.effective_user = mock_effective_user
    mock_update.message = MagicMock()
    mock_update.message.chat_id = mock_chat.id
    mock_context.args = ["closed"]

    proposals_data_closed = [
        {"id": 3, "title": "Closed Prop X", "target_channel_id": "-1003", "channel_message_id": "33", "closed_date": "2023-12-01 PST", "outcome": "X was chosen"}
    ]
    expected_formatted_list = (
        '*Closed Proposals:*\n\n'
        '\- *ID:* `3` *Title:* Closed Prop X\n'
        '  [Channel: \-1003](https://t.me/c/3/33)\n'
        '  *Closed on:* 2023\-12\-01 PST\n'
        '  *Outcome:* X was chosen\n'
    )
        
    mock_session_instance = AsyncMock()
    mock_async_session_local_callable = MagicMock()
    mock_async_session_local_callable.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
    mock_async_session_local_callable.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal', mock_async_session_local_callable):
        with patch('app.telegram_handlers.proposal_command_handlers.ProposalService') as MockProposalService:
            with patch('app.telegram_handlers.proposal_command_handlers.telegram_utils.send_message_in_chunks', new_callable=AsyncMock) as mock_send_chunks:
                mock_proposal_service_instance = MockProposalService.return_value
                mock_proposal_service_instance.list_proposals_by_status = AsyncMock(return_value=proposals_data_closed)

                await proposals_command(mock_update, mock_context)

                mock_send_chunks.assert_called_once_with(
                    mock_context,
                    chat_id=mock_chat.id,
                    text=expected_formatted_list,
                    parse_mode=ParseMode.MARKDOWN_V2
                )

@pytest.mark.asyncio
async def test_proposals_command_with_invalid_arg():
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_effective_user = TelegramUser(id=789, first_name="Test User", is_bot=False)
    mock_chat = Chat(id=456, type='private')
    mock_update.effective_user = mock_effective_user
    mock_update.message = MagicMock()
    mock_update.message.reply_text = AsyncMock()
    mock_context.args = ["invalid_arg"]

    expected_reply_text = "Unknown filter: invalid\_arg\. Please use 'open' or 'closed', or use /proposals to get selection buttons\."
    
    await proposals_command(mock_update, mock_context)
    mock_update.message.reply_text.assert_called_once_with(expected_reply_text)

@pytest.mark.asyncio
async def test_proposals_command_no_message():
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_update.effective_user = TelegramUser(id=789, first_name="Test User", is_bot=False)
    mock_update.message = None

    with patch('app.telegram_handlers.proposal_command_handlers.logger.warning') as mock_logger_warning:
        await proposals_command(mock_update, mock_context)
        mock_logger_warning.assert_called_once_with("proposals_command called without effective_user or message.")