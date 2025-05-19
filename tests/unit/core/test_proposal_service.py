import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import List, Dict, Any # Added Dict, Any

from app.core.proposal_service import ProposalService
from app.persistence.models.proposal_model import Proposal, ProposalStatus, ProposalType
from app.utils import telegram_utils # For formatting dates

@pytest.mark.asyncio
async def test_list_proposals_by_proposer_found():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    user_telegram_id = 12345

    # Mock Proposals from repository
    repo_proposal1 = Proposal(
        id=1, proposer_telegram_id=user_telegram_id, title="My Prop 1", 
        description="Desc 1", proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        options=["A", "B"], target_channel_id="-1001", channel_message_id=50,
        creation_date=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        deadline_date=datetime(2023, 1, 8, 10, 0, 0, tzinfo=timezone.utc),
        status=ProposalStatus.OPEN.value, outcome=None, raw_results=None
    )
    repo_proposal2 = Proposal(
        id=2, proposer_telegram_id=user_telegram_id, title="My Prop 2", 
        description="Desc 2", proposal_type=ProposalType.FREE_FORM.value,
        options=None, target_channel_id="-1002", channel_message_id=51,
        creation_date=datetime(2023, 1, 2, 11, 0, 0, tzinfo=timezone.utc),
        deadline_date=datetime(2023, 1, 9, 11, 0, 0, tzinfo=timezone.utc),
        status=ProposalStatus.CLOSED.value, outcome="Summary", raw_results={}
    )
    mock_repo_proposals = [repo_proposal1, repo_proposal2]

    service = ProposalService(mock_session)

    # Patch the repository method
    with patch.object(service.proposal_repository, 'get_proposals_by_proposer_id', return_value=mock_repo_proposals) as mock_get_from_repo:
        # Act
        formatted_proposals = await service.list_proposals_by_proposer(user_telegram_id)

        # Assert
        mock_get_from_repo.assert_called_once_with(user_telegram_id)
        assert len(formatted_proposals) == 2

        # Check formatting of the first proposal
        prop1_formatted = formatted_proposals[0]
        assert prop1_formatted["id"] == 1
        assert prop1_formatted["title"] == "My Prop 1"
        assert prop1_formatted["status"] == ProposalStatus.OPEN.value
        assert prop1_formatted["proposal_type"] == ProposalType.MULTIPLE_CHOICE.value
        assert prop1_formatted["target_channel_id"] == "-1001"
        # Assuming telegram_utils.format_datetime_for_display works as expected
        # Its own tests should verify its specific output format.
        # Here we just check if it was called and returned a string.
        assert isinstance(prop1_formatted["deadline_date"], str)
        assert isinstance(prop1_formatted["creation_date"], str)
        assert prop1_formatted["outcome"] is None

        # Check formatting of the second proposal
        prop2_formatted = formatted_proposals[1]
        assert prop2_formatted["id"] == 2
        assert prop2_formatted["title"] == "My Prop 2"
        assert prop2_formatted["status"] == ProposalStatus.CLOSED.value
        assert prop2_formatted["outcome"] == "Summary"

@pytest.mark.asyncio
async def test_list_proposals_by_proposer_not_found():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    user_telegram_id = 12345
    service = ProposalService(mock_session)

    with patch.object(service.proposal_repository, 'get_proposals_by_proposer_id', return_value=[]) as mock_get_from_repo:
        # Act
        formatted_proposals = await service.list_proposals_by_proposer(user_telegram_id)

        # Assert
        mock_get_from_repo.assert_called_once_with(user_telegram_id)
        assert len(formatted_proposals) == 0 

# Tests for edit_proposal_details

@pytest.fixture
def mock_proposal_service(mock_session_arg): # Renamed fixture argument
    service = ProposalService(db_session=mock_session_arg)
    service.proposal_repository = AsyncMock()
    service.submission_repository = AsyncMock()
    service.llm_service = AsyncMock()  # Add this for re-indexing
    return service

@pytest.fixture
def mock_session_arg(): # Fixture to provide mock_session
    return AsyncMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_edit_proposal_details_success(mock_proposal_service, mock_session_arg): # Use renamed fixture
    proposal_id = 1
    proposer_telegram_id = 123
    new_title = "New Title"
    new_description = "New Description"
    new_options = ["Opt1", "Opt2"]

    mock_proposal = Proposal(
        id=proposal_id, proposer_telegram_id=proposer_telegram_id, title="Old Title", 
        description="Old Desc", proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        options=["OldOpt1"], status=ProposalStatus.OPEN.value, channel_message_id=789
    )

    mock_proposal_service.proposal_repository.get_proposal_by_id.return_value = mock_proposal
    mock_proposal_service.submission_repository.count_submissions_for_proposal.return_value = 0
    
    # Mock the updated proposal return value
    updated_mock_proposal = Proposal(
        id=proposal_id, proposer_telegram_id=proposer_telegram_id, title=new_title, 
        description=new_description, proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        options=new_options, status=ProposalStatus.OPEN.value, channel_message_id=789
    )
    mock_proposal_service.proposal_repository.update_proposal_details.return_value = updated_mock_proposal
    
    # Mock the embedding generation for re-indexing
    mock_proposal_service.llm_service.generate_embedding.return_value = [0.1, 0.2]

    updated_proposal_obj, message = await mock_proposal_service.edit_proposal_details(
        proposal_id, proposer_telegram_id, new_title, new_description, new_options
    )

    assert updated_proposal_obj is not None # Check that a Proposal object was returned
    assert message is None # On success, message is None
    mock_proposal_service.proposal_repository.get_proposal_by_id.assert_called_once_with(proposal_id)
    mock_proposal_service.submission_repository.count_submissions_for_proposal.assert_called_once_with(proposal_id)
    # The arguments to update_proposal_details in the service are now based on what was new, vs what was original.
    # The test should ensure the call reflects the new values passed to edit_proposal_details.
    mock_proposal_service.proposal_repository.update_proposal_details.assert_called_once_with(
        proposal_id=proposal_id, title=new_title, description=new_description, options=new_options
    )

@pytest.mark.asyncio
async def test_edit_proposal_details_success_no_channel_message(mock_proposal_service, mock_session_arg):
    proposal_id = 1
    proposer_telegram_id = 123
    new_title = "New Title"
    mock_proposal = Proposal(
        id=proposal_id, proposer_telegram_id=proposer_telegram_id, title="Old Title",
        description="Old Desc", proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        options=["OldOpt1"], status=ProposalStatus.OPEN.value, channel_message_id=None # No channel message ID
    )
    mock_proposal_service.proposal_repository.get_proposal_by_id.return_value = mock_proposal
    mock_proposal_service.submission_repository.count_submissions_for_proposal.return_value = 0
    
    # Updated mock proposal
    updated_mock_proposal = Proposal(
        id=proposal_id, proposer_telegram_id=proposer_telegram_id, title=new_title,
        description="Old Desc", proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        options=["OldOpt1"], status=ProposalStatus.OPEN.value, channel_message_id=None
    )
    mock_proposal_service.proposal_repository.update_proposal_details.return_value = updated_mock_proposal
    
    # Mock the embedding generation for re-indexing
    mock_proposal_service.llm_service.generate_embedding.return_value = [0.1, 0.2]

    updated_proposal_obj, message = await mock_proposal_service.edit_proposal_details(
        proposal_id, proposer_telegram_id, new_title, None, None # Only updating title
    )
    assert updated_proposal_obj is not None
    assert message is None

@pytest.mark.asyncio
async def test_edit_proposal_details_proposal_not_found(mock_proposal_service, mock_session_arg):
    mock_proposal_service.proposal_repository.get_proposal_by_id.return_value = None

    updated_proposal_obj, message = await mock_proposal_service.edit_proposal_details(999, 123, "T", "D", [])

    assert updated_proposal_obj is None
    assert message == "Proposal not found."
    mock_proposal_service.submission_repository.count_submissions_for_proposal.assert_not_called()

@pytest.mark.asyncio
async def test_edit_proposal_details_not_proposer(mock_proposal_service, mock_session_arg):
    mock_proposal_from_repo = Proposal(id=1, proposer_telegram_id=456, status=ProposalStatus.OPEN.value) # Different proposer_id
    mock_proposal_service.proposal_repository.get_proposal_by_id.return_value = mock_proposal_from_repo

    updated_proposal_obj, message = await mock_proposal_service.edit_proposal_details(1, 123, "T", "D", []) # User 123 attempts edit

    assert updated_proposal_obj is None
    assert message == "You are not authorized to edit this proposal."

@pytest.mark.asyncio
async def test_edit_proposal_details_not_open(mock_proposal_service, mock_session_arg):
    mock_proposal_from_repo = Proposal(id=1, proposer_telegram_id=123, status=ProposalStatus.CLOSED.value) # Not OPEN
    mock_proposal_service.proposal_repository.get_proposal_by_id.return_value = mock_proposal_from_repo

    updated_proposal_obj, message = await mock_proposal_service.edit_proposal_details(1, 123, "T", "D", [])

    assert updated_proposal_obj is None
    assert message == f"This proposal is not open for editing (current status: {ProposalStatus.CLOSED.value})."

@pytest.mark.asyncio
async def test_edit_proposal_details_has_submissions(mock_proposal_service, mock_session_arg):
    mock_proposal_from_repo = Proposal(id=1, proposer_telegram_id=123, status=ProposalStatus.OPEN.value)
    mock_proposal_service.proposal_repository.get_proposal_by_id.return_value = mock_proposal_from_repo
    mock_proposal_service.submission_repository.count_submissions_for_proposal.return_value = 1 # Has submissions

    updated_proposal_obj, message = await mock_proposal_service.edit_proposal_details(1, 123, "T", "D", [])

    assert updated_proposal_obj is None
    assert message == "This proposal cannot be edited because it already has submissions. Please cancel it and create a new one if changes are needed."
    mock_proposal_service.proposal_repository.update_proposal_details.assert_not_called()

@pytest.mark.asyncio
async def test_edit_proposal_details_update_fails_in_repo(mock_proposal_service, mock_session_arg):
    mock_proposal_from_repo = Proposal(id=1, proposer_telegram_id=123, status=ProposalStatus.OPEN.value)
    mock_proposal_service.proposal_repository.get_proposal_by_id.return_value = mock_proposal_from_repo
    mock_proposal_service.submission_repository.count_submissions_for_proposal.return_value = 0
    mock_proposal_service.proposal_repository.update_proposal_details.return_value = None # Simulate DB update failure

    updated_proposal_obj, message = await mock_proposal_service.edit_proposal_details(1, 123, "T", "D", [])

    assert updated_proposal_obj is None
    assert message == "Failed to update proposal in the database."

@pytest.mark.asyncio
async def test_edit_proposal_details_no_changes_provided(mock_proposal_service, mock_session_arg):
    mock_proposal_from_repo = Proposal(id=1, proposer_telegram_id=123, status=ProposalStatus.OPEN.value)
    mock_proposal_service.proposal_repository.get_proposal_by_id.return_value = mock_proposal_from_repo
    mock_proposal_service.submission_repository.count_submissions_for_proposal.return_value = 0

    updated_proposal_obj, message = await mock_proposal_service.edit_proposal_details(1, 123, None, None, None)

    assert updated_proposal_obj is None
    assert message == "No changes provided. Please specify what you want to edit (title, description, or options)."
    mock_proposal_service.proposal_repository.update_proposal_details.assert_not_called() 