import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User as TelegramUser, Chat
from telegram.ext import ContextTypes

from app.telegram_handlers.proposal_command_handlers import my_proposals_command
from app.core.proposal_service import ProposalService # For patching
from app.core.user_service import UserService # For patching
from app.utils import telegram_utils # For send_message_in_chunks
from app.persistence.models.proposal_model import ProposalType, ProposalStatus # For sample data

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
    mock_update.message.reply_text = AsyncMock()

    # Mock data from ProposalService.list_proposals_by_proposer
    formatted_proposals_data = [
        {
            "id": 1, "title": "Prop Alpha", "status": "Open", 
            "deadline_date": "2023-12-01 PST", "creation_date": "2023-11-01 PST",
            "outcome": None, "target_channel_id": "-1001", "proposal_type": ProposalType.MULTIPLE_CHOICE.value
        },
        {
            "id": 2, "title": "Prop Beta", "status": "Closed", 
            "deadline_date": "2023-11-15 PST", "creation_date": "2023-10-15 PST",
            "outcome": "Beta idea selected", "target_channel_id": "-1002", "proposal_type": ProposalType.FREE_FORM.value
        }
    ]

    expected_message_parts = [
        "*Your Proposals:*\n",
        (
            "\\- *Title:* Prop Alpha \\(ID: `1`\\)\n"
            "  Status: Open\n"
            "  Type: multiple\\_choice\n"
            "  Channel: `\\-1001`\n"
            "  Created: 2023\\-11\\-01 PST\n"
            "  Deadline: 2023\\-12\\-01 PST\n"
            "  Outcome: N/A\n"
        ),
        (
            "\\- *Title:* Prop Beta \\(ID: `2`\\)\n"
            "  Status: Closed\n"
            "  Type: free\\_form\n"
            "  Channel: `\\-1002`\n"
            "  Created: 2023\\-10\\-15 PST\n"
            "  Deadline: 2023\\-11\\-15 PST\n"
            "  Outcome: Beta idea selected\n"
        )
    ]
    expected_final_message = "\n".join(expected_message_parts)

    # Mock for the session instance yielded by AsyncSessionLocal
    mock_session_instance = AsyncMock()

    # Mock for AsyncSessionLocal callable itself
    mock_async_session_local_callable = MagicMock() # Not AsyncMock
    # Its return_value is the async context manager
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

                    # Act
                    await my_proposals_command(mock_update, mock_context)

                    # Assert
                    MockUserService.assert_called_once_with(mock_session_instance)
                    MockProposalService.assert_called_once_with(mock_session_instance)
                    mock_user_service_instance.register_user_interaction.assert_called_once_with(
                        telegram_id=123, username="testproposer", first_name="TestProposer"
                    )
                    mock_proposal_service_instance.list_proposals_by_proposer.assert_called_once_with(123)
                    
                    mock_send_chunks.assert_called_once()
                    called_args_tuple = mock_send_chunks.call_args
                    assert called_args_tuple is not None, "send_message_in_chunks was not called"
                    
                    # call_args can be a Call object or a tuple (args, kwargs)
                    # For AsyncMock, it's often ((pos_args_tuple), {kw_args_dict})
                    # or just a Call object directly. Let's be flexible.
                    if isinstance(called_args_tuple, tuple): # (args, kwargs) format
                        pos_args, kw_args = called_args_tuple
                    else: # Call object format (e.g. call.args, call.kwargs)
                        pos_args = called_args_tuple.args
                        kw_args = called_args_tuple.kwargs

                    assert len(pos_args) == 1, f"Expected 1 positional argument, got {len(pos_args)}"
                    assert pos_args[0] is mock_context # Context is the first positional arg
                    assert kw_args.get('chat_id') == 123
                    assert kw_args.get('text') == expected_final_message
                    assert kw_args.get('parse_mode') == 'MarkdownV2'

@pytest.mark.asyncio
async def test_my_proposals_command_no_proposals():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_effective_user = TelegramUser(id=123, first_name="TestProposer", is_bot=False, username="testproposer")
    mock_chat = Chat(id=123, type='private')
    mock_update.effective_user = mock_effective_user
    mock_update.effective_chat = mock_chat
    mock_update.message = MagicMock()
    mock_update.message.reply_text = AsyncMock()

    expected_message = "You haven't created any proposals yet."

    # Mock for the session instance yielded by AsyncSessionLocal
    mock_session_instance = AsyncMock()

    # Mock for AsyncSessionLocal callable itself
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
                    mock_proposal_service_instance.list_proposals_by_proposer = AsyncMock(return_value=[]) # No proposals

                    # Act
                    await my_proposals_command(mock_update, mock_context)

                    # Assert
                    MockUserService.assert_called_once_with(mock_session_instance)
                    MockProposalService.assert_called_once_with(mock_session_instance)
                    mock_send_chunks.assert_called_once() # Check it was called
                    called_args_tuple = mock_send_chunks.call_args
                    assert called_args_tuple is not None, "send_message_in_chunks was not called"
                    
                    # call_args can be a Call object or a tuple (args, kwargs)
                    # For AsyncMock, it's often ((pos_args_tuple), {kw_args_dict})
                    # or just a Call object directly. Let's be flexible.
                    if isinstance(called_args_tuple, tuple): # (args, kwargs) format
                        pos_args, kw_args = called_args_tuple
                    else: # Call object format (e.g. call.args, call.kwargs)
                        pos_args = called_args_tuple.args
                        kw_args = called_args_tuple.kwargs

                    assert len(pos_args) == 1, f"Expected 1 positional argument, got {len(pos_args)}"
                    assert pos_args[0] is mock_context # Context is the first positional arg
                    assert kw_args.get('chat_id') == 123
                    assert kw_args.get('text') == expected_message
                    assert kw_args.get('parse_mode') == 'MarkdownV2'

@pytest.mark.asyncio
async def test_my_proposals_command_no_effective_user():
    # Arrange
    mock_update = AsyncMock(spec=Update)
    mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    mock_update.effective_user = None
    mock_update.message = MagicMock() # Important: message might still exist
    mock_update.message.reply_text = AsyncMock()

    # Act
    await my_proposals_command(mock_update, mock_context)

    # Assert
    mock_update.message.reply_text.assert_called_once_with("I can't identify you to fetch your proposals.") 