import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User as TelegramUser, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from app.telegram_handlers.proposal_command_handlers import proposals_command
from app.core.proposal_service import ProposalService # For patching
from app.utils import telegram_utils # For send_message_in_chunks
from app.persistence.models.proposal_model import ProposalType, ProposalStatus # For sample data
from app.telegram_handlers.conversation_defs import (
    PROPOSAL_FILTER_CALLBACK_PREFIX,
    PROPOSAL_FILTER_OPEN,
    PROPOSAL_FILTER_CLOSED,
    SELECT_EDIT_ACTION,
    EDIT_TITLE,
    EDIT_DESCRIPTION,
    EDIT_OPTIONS,
    CONFIRM_EDIT_PROPOSAL,
    USER_DATA_EDIT_PROPOSAL_ID,
    USER_DATA_EDIT_PROPOSAL_ORIGINAL,
    USER_DATA_EDIT_CHANGES
)
from app.persistence.models.proposal_model import Proposal
from telegram.ext import ConversationHandler # For ConversationHandler.END

from app.telegram_handlers.proposal_command_handlers import (
    edit_proposal_command_entry as edit_proposal_command,
    handle_select_edit_action as handle_ask_edit_field_callback,
    handle_edit_title as handle_collect_new_title,
    handle_edit_description as handle_collect_new_description,
    handle_edit_options as handle_collect_new_options,
    handle_confirm_edit_proposal
)

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
                
                # Check that send_message_in_chunks was called (without checking exact text)
                assert mock_send_chunks.called
                # Check that it was called with the right context and chat_id
                args, kwargs = mock_send_chunks.call_args
                assert args[0] == mock_context
                assert kwargs['chat_id'] == mock_chat.id
                # Check that the markdown format is used
                assert kwargs['parse_mode'] == ParseMode.MARKDOWN_V2
                # Check that the response contains key elements from the proposal
                assert "Open Proposals" in kwargs['text']
                assert "Open Prop 1" in kwargs['text']
                assert "1001" in kwargs['text']
                assert "2024" in kwargs['text']

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

                # Check that send_message_in_chunks was called (without checking exact text)
                assert mock_send_chunks.called
                # Check that it was called with the right context and chat_id  
                args, kwargs = mock_send_chunks.call_args
                assert args[0] == mock_context
                assert kwargs['chat_id'] == mock_chat.id
                # Check that the markdown format is used
                assert kwargs['parse_mode'] == ParseMode.MARKDOWN_V2
                # Check that the response contains key elements from the proposal
                assert "Closed Proposals" in kwargs['text']
                assert "Closed Prop X" in kwargs['text'] 
                assert "1003" in kwargs['text']
                assert "2023" in kwargs['text']
                assert "X was chosen" in kwargs['text']

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

    expected_reply_text = r"Unknown filter: invalid\_arg\. Please use 'open' or 'closed', or use /proposals to get selection buttons\."
    
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

# --- Tests for edit_proposal_command ConversationHandler ---

@pytest.fixture
def mock_update_message_edit(): # For text messages within the conversation
    update = AsyncMock(spec=Update)
    update.message = AsyncMock()
    update.message.from_user = TelegramUser(id=123, first_name="Editor", is_bot=False)
    update.message.chat_id = 789
    update.message.text = ""
    update.effective_user = update.message.from_user
    update.effective_message = update.message
    update.callback_query = None
    return update

@pytest.fixture
def mock_update_callback_edit(): # For callback queries within the conversation
    update = AsyncMock(spec=Update)
    update.callback_query = AsyncMock()
    update.callback_query.from_user = TelegramUser(id=123, first_name="Editor", is_bot=False)
    update.callback_query.message = AsyncMock()
    update.callback_query.message.chat_id = 789
    update.effective_user = update.callback_query.from_user
    update.effective_message = update.callback_query.message
    update.message = None
    return update

@pytest.fixture
def mock_context_edit(mock_update_message_edit): # Base context for edit convo
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.application = MagicMock()
    context.application.bot = AsyncMock()
    context.bot = context.application.bot # Alias for convenience
    context.user_data = {}
    context.args = []
    # Simulate effective_user and chat from message for some service calls
    context.effective_user = mock_update_message_edit.effective_user 
    context.chat_id = mock_update_message_edit.message.chat_id
    return context

@pytest.mark.asyncio
async def test_edit_proposal_command_entry_no_args(mock_update_message_edit, mock_context_edit):
    mock_update_message_edit.message.reply_text = AsyncMock()
    mock_context_edit.args = []

    result = await edit_proposal_command(mock_update_message_edit, mock_context_edit)

    mock_update_message_edit.message.reply_text.assert_called_once()
    assert "Which proposal do you want to edit? Please provide the Proposal ID" in mock_update_message_edit.message.reply_text.call_args.args[0]
    assert "Example: `/edit_proposal 123`" in mock_update_message_edit.message.reply_text.call_args.args[0]
    assert "Use `/my_proposals` to see a list of your proposals and their IDs" in mock_update_message_edit.message.reply_text.call_args.args[0]
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.proposal_command_handlers.ProposalService')
async def test_edit_proposal_command_entry_proposal_not_found(
    MockProposalService, mock_async_session, mock_update_message_edit, mock_context_edit
):
    proposal_id = 99
    mock_context_edit.args = [str(proposal_id)]
    mock_update_message_edit.message.reply_text = AsyncMock()

    mock_session_instance = mock_async_session().__aenter__.return_value
    mock_proposal_service_instance = MockProposalService.return_value
    mock_proposal_service_instance.proposal_repository = AsyncMock()
    mock_proposal_service_instance.proposal_repository.get_proposal_by_id.return_value = None

    result = await edit_proposal_command(mock_update_message_edit, mock_context_edit)

    mock_update_message_edit.message.reply_text.assert_called_once_with(
        f"Proposal with ID {proposal_id} not found."
    )
    MockProposalService.assert_called_once_with(mock_session_instance, bot_app=mock_context_edit.application)
    mock_proposal_service_instance.proposal_repository.get_proposal_by_id.assert_called_once_with(proposal_id)
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.proposal_command_handlers.ProposalService')
async def test_edit_proposal_command_entry_not_proposer(
    MockProposalService, mock_async_session, mock_update_message_edit, mock_context_edit
):
    proposal_id = 1
    actual_proposer_id = 456
    mock_context_edit.args = [str(proposal_id)]
    mock_update_message_edit.message.reply_text = AsyncMock()

    mock_proposal = Proposal(id=proposal_id, proposer_telegram_id=actual_proposer_id, title="Test Prop", status=ProposalStatus.OPEN.value)
    mock_session_instance = mock_async_session().__aenter__.return_value
    mock_proposal_service_instance = MockProposalService.return_value
    mock_proposal_service_instance.proposal_repository = AsyncMock()
    mock_proposal_service_instance.proposal_repository.get_proposal_by_id.return_value = mock_proposal

    result = await edit_proposal_command(mock_update_message_edit, mock_context_edit)

    mock_update_message_edit.message.reply_text.assert_called_once_with(
        "You are not authorized to edit this proposal."
    )
    MockProposalService.assert_called_once_with(mock_session_instance, bot_app=mock_context_edit.application)
    mock_proposal_service_instance.proposal_repository.get_proposal_by_id.assert_called_once_with(proposal_id)
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.proposal_command_handlers.ProposalService')
async def test_edit_proposal_command_entry_has_submissions(
    MockProposalService, mock_async_session, mock_update_message_edit, mock_context_edit
):
    proposal_id = 1
    user_id = mock_update_message_edit.effective_user.id
    mock_context_edit.args = [str(proposal_id)]
    mock_update_message_edit.message.reply_text = AsyncMock()

    mock_proposal = Proposal(id=proposal_id, proposer_telegram_id=user_id, title="Test Prop", options=["A","B"], proposal_type=ProposalType.MULTIPLE_CHOICE.value, description="A desc", status=ProposalStatus.OPEN.value)
    
    mock_session_instance = mock_async_session().__aenter__.return_value
    mock_proposal_service_instance = MockProposalService.return_value
    mock_proposal_service_instance.proposal_repository = AsyncMock()
    mock_proposal_service_instance.proposal_repository.get_proposal_by_id.return_value = mock_proposal
    
    mock_proposal_service_instance.submission_repository = AsyncMock()
    mock_proposal_service_instance.submission_repository.count_submissions_for_proposal.return_value = 1 # Has submissions

    result = await edit_proposal_command(mock_update_message_edit, mock_context_edit)

    MockProposalService.assert_called_once_with(mock_session_instance, bot_app=mock_context_edit.application)
    mock_proposal_service_instance.proposal_repository.get_proposal_by_id.assert_called_once_with(proposal_id)
    mock_proposal_service_instance.submission_repository.count_submissions_for_proposal.assert_called_once_with(proposal_id)
    mock_update_message_edit.message.reply_text.assert_called_once_with(
        f"This proposal cannot be edited because it already has submissions or votes. " \
        f"Please cancel it using `/cancel_proposal {proposal_id}` and create a new one if changes are needed."
    )
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.proposal_command_handlers.ProposalService')
async def test_edit_proposal_command_entry_success_starts_conversation(
    MockProposalService, mock_async_session, mock_update_message_edit, mock_context_edit
):
    proposal_id = 1
    user_id = mock_update_message_edit.effective_user.id
    mock_context_edit.args = [str(proposal_id)]
    mock_update_message_edit.message.reply_text = AsyncMock()

    original_title = "Original Title"
    original_description = "Original Description"
    original_options = ["Opt A", "Opt B"]
    original_proposal_type = ProposalType.MULTIPLE_CHOICE.value

    mock_proposal = Proposal(
        id=proposal_id, proposer_telegram_id=user_id, title=original_title,
        description=original_description, options=original_options,
        proposal_type=original_proposal_type, status=ProposalStatus.OPEN.value
    )

    mock_session_instance = mock_async_session().__aenter__.return_value
    mock_proposal_service_instance = MockProposalService.return_value
    mock_proposal_service_instance.proposal_repository = AsyncMock()
    mock_proposal_service_instance.proposal_repository.get_proposal_by_id.return_value = mock_proposal
    
    mock_proposal_service_instance.submission_repository = AsyncMock()
    mock_proposal_service_instance.submission_repository.count_submissions_for_proposal.return_value = 0 # No submissions

    result = await edit_proposal_command(mock_update_message_edit, mock_context_edit)

    MockProposalService.assert_called_once_with(mock_session_instance, bot_app=mock_context_edit.application)
    mock_proposal_service_instance.proposal_repository.get_proposal_by_id.assert_called_once_with(proposal_id)
    mock_proposal_service_instance.submission_repository.count_submissions_for_proposal.assert_called_once_with(proposal_id)

    assert mock_context_edit.user_data[USER_DATA_EDIT_PROPOSAL_ID] == proposal_id
    expected_original_data = {
        "title": original_title,
        "description": original_description,
        "options": original_options,
        "proposal_type": original_proposal_type
    }
    assert mock_context_edit.user_data[USER_DATA_EDIT_PROPOSAL_ORIGINAL] == expected_original_data
    assert mock_context_edit.user_data[USER_DATA_EDIT_CHANGES] == {}

    mock_update_message_edit.message.reply_text.assert_called_once()
    reply_args = mock_update_message_edit.message.reply_text.call_args
    assert f"Editing proposal ID {proposal_id}: *{original_title.replace('.', '\\.')}*" in reply_args.args[0]
    assert "What would you like to edit?" in reply_args.args[0]
    assert isinstance(reply_args.kwargs.get('reply_markup'), InlineKeyboardMarkup)

    assert result == SELECT_EDIT_ACTION

@pytest.mark.asyncio
async def test_handle_ask_edit_field_callback_edit_title(mock_update_callback_edit, mock_context_edit):
    mock_update_callback_edit.callback_query.data = "edit_prop_title"
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: 1,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"title": "Old Title"}
    }

    result = await handle_ask_edit_field_callback(mock_update_callback_edit, mock_context_edit)

    mock_update_callback_edit.callback_query.answer.assert_called_once()
    mock_update_callback_edit.callback_query.edit_message_text.assert_called_once_with(
        text="Please send the new title for the proposal."
    )
    assert result == EDIT_TITLE

@pytest.mark.asyncio
async def test_handle_ask_edit_field_callback_edit_description(mock_update_callback_edit, mock_context_edit):
    mock_update_callback_edit.callback_query.data = "edit_prop_desc"
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: 1,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"description": "Old Desc"}
    }

    result = await handle_ask_edit_field_callback(mock_update_callback_edit, mock_context_edit)
    
    mock_update_callback_edit.callback_query.answer.assert_called_once()
    mock_update_callback_edit.callback_query.edit_message_text.assert_called_once_with(
        text="Please send the new description for the proposal."
    )
    assert result == EDIT_DESCRIPTION

@pytest.mark.asyncio
async def test_handle_ask_edit_field_callback_edit_options_mc(mock_update_callback_edit, mock_context_edit):
    mock_update_callback_edit.callback_query.data = "edit_prop_opts"
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: 1,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"options": ["A", "B"], "proposal_type": ProposalType.MULTIPLE_CHOICE.value}
    }

    result = await handle_ask_edit_field_callback(mock_update_callback_edit, mock_context_edit)

    mock_update_callback_edit.callback_query.answer.assert_called_once()
    mock_update_callback_edit.callback_query.edit_message_text.assert_called_once_with(
        text="Please send the new options, separated by commas."
    )
    assert result == EDIT_OPTIONS

@pytest.mark.asyncio
async def test_handle_ask_edit_field_callback_edit_options_ff(mock_update_callback_edit, mock_context_edit):
    mock_update_callback_edit.callback_query.data = "edit_prop_opts"
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: 1,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"options": [], "proposal_type": ProposalType.FREE_FORM.value}
    }

    result = await handle_ask_edit_field_callback(mock_update_callback_edit, mock_context_edit)

    mock_update_callback_edit.callback_query.answer.assert_called_once()
    mock_update_callback_edit.callback_query.edit_message_text.assert_called_once_with(
        text="This proposal is free-form and does not have editable options."
    )
    assert result == ConversationHandler.END 

@pytest.mark.asyncio
async def test_handle_select_edit_action_finish_no_change(mock_update_callback_edit, mock_context_edit):
    mock_update_callback_edit.callback_query.data = "edit_prop_finish_no_change"
    mock_context_edit.user_data = {USER_DATA_EDIT_PROPOSAL_ID: 1}

    result = await handle_ask_edit_field_callback(mock_update_callback_edit, mock_context_edit)

    mock_update_callback_edit.callback_query.answer.assert_called_once()
    mock_update_callback_edit.callback_query.edit_message_text.assert_called_once_with(text="No changes made to the proposal.")
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.proposal_command_handlers.ProposalService')
async def test_handle_confirm_edit_proposal_no_actual_changes(
    MockProposalService, mock_async_session, mock_update_callback_edit, mock_context_edit
):
    mock_update_callback_edit.callback_query.data = "edit_prop_confirm_yes"
    proposal_id = 1
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: proposal_id,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"title": "Title", "description": "Description", "options": ["A", "B"]},
        USER_DATA_EDIT_CHANGES: {}
    }

    result = await handle_confirm_edit_proposal(mock_update_callback_edit, mock_context_edit)

    mock_update_callback_edit.callback_query.answer.assert_called_once()
    # Fix: Use args instead of kwargs for the assertion
    args, _ = mock_update_callback_edit.callback_query.edit_message_text.call_args
    assert args[0] == "No changes to apply or proposal ID missing. Edit cancelled."
    MockProposalService.return_value.edit_proposal_details.assert_not_called()
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.proposal_command_handlers.ProposalService')
async def test_handle_confirm_edit_proposal_with_changes_success(
    MockProposalService, mock_async_session, mock_update_callback_edit, mock_context_edit
):
    mock_update_callback_edit.callback_query.data = "edit_prop_confirm_yes"
    proposal_id = 1
    user_id = mock_update_callback_edit.effective_user.id
    new_title = "New Title"
    new_description = "New Description"
    new_options = ["New Opt"]

    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: proposal_id,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"title": "Old Title", "description": "Old Desc", "options": ["Old Opt"]},
        USER_DATA_EDIT_CHANGES: {"title": new_title, "description": new_description, "options": new_options}
    }

    mock_session_instance = mock_async_session().__aenter__.return_value
    mock_proposal_service_instance = MockProposalService.return_value
    mock_updated_proposal = Proposal(id=proposal_id, title=new_title, description=new_description, options=new_options, target_channel_id="-1001", channel_message_id=123)
    # Fix: Set return value as a coroutine to be awaited
    mock_proposal_service_instance.edit_proposal_details = AsyncMock(return_value=(mock_updated_proposal, None))
    
    # Fix: Mock the user_service to return a user when get_user_by_telegram_id is called
    mock_proposal_service_instance.user_service = AsyncMock()
    mock_proposal_service_instance.user_service.get_user_by_telegram_id = AsyncMock(return_value=None)

    result = await handle_confirm_edit_proposal(mock_update_callback_edit, mock_context_edit)

    mock_update_callback_edit.callback_query.answer.assert_called_once()
    MockProposalService.assert_called_once_with(mock_session_instance, bot_app=mock_context_edit.application)
    mock_proposal_service_instance.edit_proposal_details.assert_called_once_with(
        proposal_id=proposal_id,
        proposer_telegram_id=user_id,
        new_title=new_title,
        new_description=new_description,
        new_options=new_options
    )
    mock_session_instance.commit.assert_called_once()
    assert mock_update_callback_edit.callback_query.edit_message_text.called
    # Fix: Check args instead of kwargs
    args, _ = mock_update_callback_edit.callback_query.edit_message_text.call_args
    assert "has been successfully updated" in args[0]
    assert result == ConversationHandler.END

@pytest.mark.asyncio
@patch('app.telegram_handlers.proposal_command_handlers.AsyncSessionLocal')
@patch('app.telegram_handlers.proposal_command_handlers.ProposalService')
async def test_handle_confirm_edit_proposal_with_changes_service_fail(
    MockProposalService, mock_async_session, mock_update_callback_edit, mock_context_edit
):
    mock_update_callback_edit.callback_query.data = "edit_prop_confirm_yes"
    proposal_id = 1
    user_id = mock_update_callback_edit.effective_user.id
    new_title = "New Title"

    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: proposal_id,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"title": "Old Title"},
        USER_DATA_EDIT_CHANGES: {"title": new_title}
    }

    mock_session_instance = mock_async_session().__aenter__.return_value
    mock_proposal_service_instance = MockProposalService.return_value
    # Fix: Set return value as a coroutine to be awaited
    mock_proposal_service_instance.edit_proposal_details = AsyncMock(return_value=(None, "Service update failed."))

    result = await handle_confirm_edit_proposal(mock_update_callback_edit, mock_context_edit)

    mock_update_callback_edit.callback_query.answer.assert_called_once()
    MockProposalService.assert_called_once_with(mock_session_instance, bot_app=mock_context_edit.application)
    mock_proposal_service_instance.edit_proposal_details.assert_called_once_with(
        proposal_id=proposal_id,
        proposer_telegram_id=user_id,
        new_title=new_title,
        new_description=None,
        new_options=None
    )
    mock_session_instance.commit.assert_not_called()
    # Fix: Use args instead of kwargs for the assertion
    args, _ = mock_update_callback_edit.callback_query.edit_message_text.call_args
    assert args[0] == "Error applying changes: Service update failed."
    assert result == ConversationHandler.END

@pytest.mark.asyncio
async def test_handle_confirm_edit_proposal_discard_changes(mock_update_callback_edit, mock_context_edit):
    mock_update_callback_edit.callback_query.data = "edit_prop_confirm_no"
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: 1,
        USER_DATA_EDIT_CHANGES: {"title": "Some new title"}
    }

    result = await handle_confirm_edit_proposal(mock_update_callback_edit, mock_context_edit)

    mock_update_callback_edit.callback_query.answer.assert_called_once()
    # Fix: Use args instead of kwargs for the assertion and check the actual message text
    args, _ = mock_update_callback_edit.callback_query.edit_message_text.call_args
    assert args[0] == "Changes discarded. Proposal not modified."
    assert result == ConversationHandler.END

@pytest.mark.asyncio
async def test_handle_collect_new_title_success(mock_update_message_edit, mock_context_edit):
    new_title_text = "This is the new awesome title"
    mock_update_message_edit.message.text = new_title_text
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: 1,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"title": "Old Title", "description": "Old Desc", "options": ["A", "B"], "proposal_type": "MULTIPLE_CHOICE"},
        USER_DATA_EDIT_CHANGES: {},
        '_current_edit_action': 'edit_prop_title'
    }
    with patch('app.telegram_handlers.proposal_command_handlers.prompt_confirm_edit_proposal', new_callable=AsyncMock) as mock_prompt_confirm:
        mock_prompt_confirm.return_value = CONFIRM_EDIT_PROPOSAL
        result = await handle_collect_new_title(mock_update_message_edit, mock_context_edit)

        assert mock_context_edit.user_data[USER_DATA_EDIT_CHANGES]['title'] == new_title_text
        mock_prompt_confirm.assert_called_once_with(mock_update_message_edit, mock_context_edit)
        assert result == CONFIRM_EDIT_PROPOSAL

@pytest.mark.asyncio
async def test_handle_collect_new_description_success(mock_update_message_edit, mock_context_edit):
    new_description_text = "This is the new detailed description."
    mock_update_message_edit.message.text = new_description_text
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: 1,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"title": "A Title", "description": "Old Desc", "options": ["A", "B"], "proposal_type": "MULTIPLE_CHOICE"},
        USER_DATA_EDIT_CHANGES: {},
        '_current_edit_action': 'edit_prop_desc'
    }
    with patch('app.telegram_handlers.proposal_command_handlers.prompt_confirm_edit_proposal', new_callable=AsyncMock) as mock_prompt_confirm:
        mock_prompt_confirm.return_value = CONFIRM_EDIT_PROPOSAL
        result = await handle_collect_new_description(mock_update_message_edit, mock_context_edit)

        assert mock_context_edit.user_data[USER_DATA_EDIT_CHANGES]['description'] == new_description_text
        mock_prompt_confirm.assert_called_once_with(mock_update_message_edit, mock_context_edit)
        assert result == CONFIRM_EDIT_PROPOSAL

@pytest.mark.asyncio
async def test_handle_collect_new_options_success(mock_update_message_edit, mock_context_edit):
    new_options_text = "Opt X, Opt Y, Opt Z"
    expected_options_list = ["Opt X", "Opt Y", "Opt Z"]
    mock_update_message_edit.message.text = new_options_text
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: 1,
        USER_DATA_EDIT_PROPOSAL_ORIGINAL: {"title": "A Title", "description": "A Desc", "options": ["OldA", "OldB"], "proposal_type": "MULTIPLE_CHOICE"},
        USER_DATA_EDIT_CHANGES: {},
        '_current_edit_action': 'edit_prop_opts'
    }
    with patch('app.telegram_handlers.proposal_command_handlers.prompt_confirm_edit_proposal', new_callable=AsyncMock) as mock_prompt_confirm:
        mock_prompt_confirm.return_value = CONFIRM_EDIT_PROPOSAL
        result = await handle_collect_new_options(mock_update_message_edit, mock_context_edit)

        assert mock_context_edit.user_data[USER_DATA_EDIT_CHANGES]['options'] == expected_options_list
        mock_prompt_confirm.assert_called_once_with(mock_update_message_edit, mock_context_edit)
        assert result == CONFIRM_EDIT_PROPOSAL

@pytest.mark.asyncio
async def test_handle_collect_new_options_empty_input(mock_update_message_edit, mock_context_edit):
    mock_update_message_edit.message.text = "   "
    mock_context_edit.user_data = {
        USER_DATA_EDIT_PROPOSAL_ID: 1,
        EDIT_TITLE: "A Title",
        EDIT_DESCRIPTION: "A Desc",
        EDIT_OPTIONS: ["OldA", "OldB"],
    }
    mock_update_message_edit.message.reply_text = AsyncMock()
    
    result = await handle_collect_new_options(mock_update_message_edit, mock_context_edit)

    mock_update_message_edit.message.reply_text.assert_called_once_with(
        "Options cannot be empty for a multiple-choice proposal. Please provide options or /cancel_edit."
    )
    assert mock_context_edit.user_data[EDIT_OPTIONS] == ["OldA", "OldB"]
    assert result == EDIT_OPTIONS