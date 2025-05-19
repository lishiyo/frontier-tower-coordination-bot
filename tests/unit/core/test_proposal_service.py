import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import List, Dict, Any # Added Dict, Any
from telegram.constants import ParseMode # Import ParseMode

from app.core.proposal_service import ProposalService
from app.persistence.models.proposal_model import Proposal, ProposalStatus, ProposalType
from app.utils import telegram_utils # For formatting dates
from app.persistence.models.user_model import User
from app.utils.telegram_utils import escape_markdown_v2 # Import for direct use
# Assuming you have a way to get Application for bot_app context, or mock it appropriately
# from telegram.ext import Application

# Add fixtures for the new tests
@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def mock_proposal_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_submission_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def mock_user_service():
    service = AsyncMock()
    return service

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
    service.vector_db_service = AsyncMock()  # Add this for vector DB testing
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

# Add new test functions for proposal indexing with properly defined fixtures

@pytest.mark.asyncio
@patch('app.core.proposal_service.LLMService')
@patch('app.core.proposal_service.VectorDBService')
async def test_create_proposal_indexes_proposal(
    mock_vector_db_service, 
    mock_llm_service, 
    mock_session, 
    mock_proposal_repo, 
    mock_submission_repo, 
    mock_user_service
):
    """Test that create_proposal calls the embedding and indexing functions"""
    # Setup
    mock_bot_app = MagicMock()
    mock_proposal_id = 123
    mock_title = "Test Proposal Title"
    mock_description = "Test Proposal Description"
    mock_deadline = datetime.now(timezone.utc)
    
    # Mock the proposal repository to return a new proposal
    mock_new_proposal = Proposal(
        id=mock_proposal_id,
        title=mock_title,
        description=mock_description,
        proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        status=ProposalStatus.OPEN.value,
        deadline_date=mock_deadline,
        creation_date=datetime.now(timezone.utc),
        target_channel_id="-1001234567890"
    )
    mock_proposal_repo.add_proposal.return_value = mock_new_proposal
    
    # Mock the user service
    mock_user = MagicMock()
    mock_user.telegram_id = 456
    mock_user_service.register_user_interaction.return_value = mock_user
    
    # Mock LLMService for embedding generation
    mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Simplified embedding vector
    mock_llm_service_instance = mock_llm_service.return_value
    mock_llm_service_instance.generate_embedding = AsyncMock(return_value=mock_embedding)
    
    # Mock VectorDBService for storing embeddings
    mock_vector_db_instance = mock_vector_db_service.return_value
    mock_vector_db_instance.add_proposal_embedding.return_value = f"proposal_{mock_proposal_id}"
    
    # Create service
    service = ProposalService(mock_session, mock_bot_app)
    service.proposal_repository = mock_proposal_repo
    service.user_service = mock_user_service
    service.submission_repository = mock_submission_repo
    service.llm_service = mock_llm_service_instance
    service.vector_db_service = mock_vector_db_instance
    
    # Call the method
    result = await service.create_proposal(
        proposer_telegram_id=456,
        proposer_username="testuser",
        proposer_first_name="Test",
        title=mock_title,
        description=mock_description,
        proposal_type=ProposalType.MULTIPLE_CHOICE,
        options=["Option 1", "Option 2"],
        deadline_date=mock_deadline,
        target_channel_id="-1001234567890"
    )
    
    # Assertions
    assert result == mock_new_proposal
    
    # Verify embedding was generated
    mock_llm_service_instance.generate_embedding.assert_called_once()
    call_args = mock_llm_service_instance.generate_embedding.call_args[0]
    assert call_args[0] == f"{mock_title} {mock_description}"
    
    # Verify embedding was stored
    mock_vector_db_instance.add_proposal_embedding.assert_called_once()
    call_args = mock_vector_db_instance.add_proposal_embedding.call_args[1]
    assert call_args["proposal_id"] == mock_proposal_id
    assert call_args["text_content"] == f"{mock_title} {mock_description}"
    assert call_args["embedding"] == mock_embedding
    assert call_args["metadata"]["proposal_id"] == mock_proposal_id
    assert call_args["metadata"]["status"] == ProposalStatus.OPEN.value
    assert call_args["metadata"]["proposal_type"] == ProposalType.MULTIPLE_CHOICE.value
    assert call_args["metadata"]["target_channel_id"] == "-1001234567890"

@pytest.mark.asyncio
@patch('app.core.proposal_service.LLMService')
@patch('app.core.proposal_service.VectorDBService')
async def test_create_proposal_handles_embedding_error(
    mock_vector_db_service, 
    mock_llm_service, 
    mock_session, 
    mock_proposal_repo, 
    mock_submission_repo, 
    mock_user_service
):
    """Test that create_proposal gracefully handles embedding errors"""
    # Setup
    mock_bot_app = MagicMock()
    mock_new_proposal = Proposal(
        id=123,
        title="Test Title",
        description="Test Description",
        proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        status=ProposalStatus.OPEN.value
    )
    mock_proposal_repo.add_proposal.return_value = mock_new_proposal
    
    mock_user = MagicMock()
    mock_user.telegram_id = 456
    mock_user_service.register_user_interaction.return_value = mock_user
    
    # Mock LLMService to return None (error case)
    mock_llm_service_instance = mock_llm_service.return_value
    mock_llm_service_instance.generate_embedding = AsyncMock(return_value=None)
    
    # Mock VectorDBService
    mock_vector_db_instance = mock_vector_db_service.return_value
    
    # Create service
    service = ProposalService(mock_session, mock_bot_app)
    service.proposal_repository = mock_proposal_repo
    service.user_service = mock_user_service
    service.submission_repository = mock_submission_repo
    service.llm_service = mock_llm_service_instance
    service.vector_db_service = mock_vector_db_instance
    
    # Call the method
    result = await service.create_proposal(
        proposer_telegram_id=456,
        proposer_username="testuser",
        proposer_first_name="Test",
        title="Test Title",
        description="Test Description",
        proposal_type=ProposalType.MULTIPLE_CHOICE,
        options=["Option 1", "Option 2"],
        deadline_date=datetime.now(timezone.utc),
        target_channel_id="-1001234567890"
    )
    
    # Assertions
    assert result == mock_new_proposal
    
    # Verify embedding was attempted but storage was not called
    mock_llm_service_instance.generate_embedding.assert_called_once()
    mock_vector_db_instance.add_proposal_embedding.assert_not_called()

@pytest.mark.asyncio
@patch('app.core.proposal_service.LLMService')
@patch('app.core.proposal_service.VectorDBService')
async def test_edit_proposal_details_reindexes_on_content_change(
    mock_vector_db_service, 
    mock_llm_service, 
    mock_session, 
    mock_proposal_repo, 
    mock_submission_repo, 
    mock_user_service
):
    """Test that edit_proposal_details reindexes proposal when title/description changes"""
    # Setup
    mock_bot_app = MagicMock()
    proposer_id = 456
    proposal_id = 123
    old_title = "Old Title"
    old_description = "Old Description"
    new_title = "New Title"
    
    # Create the existing proposal
    mock_proposal = Proposal(
        id=proposal_id,
        proposer_telegram_id=proposer_id,
        title=old_title,
        description=old_description,
        proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        status=ProposalStatus.OPEN.value,
        target_channel_id="-1001234567890"
    )
    mock_proposal_repo.get_proposal_by_id.return_value = mock_proposal
    
    # Create the updated proposal
    mock_updated_proposal = Proposal(
        id=proposal_id,
        proposer_telegram_id=proposer_id,
        title=new_title,  # Changed title
        description=old_description,
        proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        status=ProposalStatus.OPEN.value,
        target_channel_id="-1001234567890"
    )
    mock_proposal_repo.update_proposal_details.return_value = mock_updated_proposal
    
    # No submissions
    mock_submission_repo.count_submissions_for_proposal.return_value = 0
    
    # Mock LLMService for embedding generation
    mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Simplified embedding vector
    mock_llm_service_instance = mock_llm_service.return_value
    mock_llm_service_instance.generate_embedding = AsyncMock(return_value=mock_embedding)
    
    # Mock VectorDBService for storing embeddings
    mock_vector_db_instance = mock_vector_db_service.return_value
    mock_vector_db_instance.add_proposal_embedding.return_value = f"proposal_{proposal_id}"
    
    # Create service
    service = ProposalService(mock_session, mock_bot_app)
    service.proposal_repository = mock_proposal_repo
    service.user_service = mock_user_service
    service.submission_repository = mock_submission_repo
    service.llm_service = mock_llm_service_instance
    service.vector_db_service = mock_vector_db_instance
    
    # Call the method
    result, error = await service.edit_proposal_details(
        proposal_id=proposal_id,
        proposer_telegram_id=proposer_id,
        new_title=new_title,  # Only changing title
        new_description=None,
        new_options=None
    )
    
    # Assertions
    assert result == mock_updated_proposal
    assert error is None
    
    # Verify embedding was generated with new content
    mock_llm_service_instance.generate_embedding.assert_called_once()
    call_args = mock_llm_service_instance.generate_embedding.call_args[0]
    assert call_args[0] == f"{new_title} {old_description}"
    
    # Verify embedding was stored
    mock_vector_db_instance.add_proposal_embedding.assert_called_once()
    call_args = mock_vector_db_instance.add_proposal_embedding.call_args[1]
    assert call_args["proposal_id"] == proposal_id
    assert call_args["text_content"] == f"{new_title} {old_description}"
    assert call_args["embedding"] == mock_embedding

@pytest.mark.asyncio
@patch('app.core.proposal_service.LLMService')
@patch('app.core.proposal_service.VectorDBService')
async def test_edit_proposal_details_no_reindex_without_content_change(
    mock_vector_db_service, 
    mock_llm_service, 
    mock_session, 
    mock_proposal_repo, 
    mock_submission_repo, 
    mock_user_service
):
    """Test that edit_proposal_details doesn't reindex if only options change (not title/description)"""
    # Setup
    mock_bot_app = MagicMock()
    proposer_id = 456
    proposal_id = 123
    title = "Test Title"
    description = "Test Description"
    old_options = ["Option A", "Option B"]
    new_options = ["Option C", "Option D"]  # Only changing options
    
    # Create the existing proposal
    mock_proposal = Proposal(
        id=proposal_id,
        proposer_telegram_id=proposer_id,
        title=title,
        description=description,
        options=old_options,
        proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        status=ProposalStatus.OPEN.value
    )
    mock_proposal_repo.get_proposal_by_id.return_value = mock_proposal
    
    # Create the updated proposal
    mock_updated_proposal = Proposal(
        id=proposal_id,
        proposer_telegram_id=proposer_id,
        title=title,
        description=description,
        options=new_options,
        proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        status=ProposalStatus.OPEN.value
    )
    mock_proposal_repo.update_proposal_details.return_value = mock_updated_proposal
    
    # No submissions
    mock_submission_repo.count_submissions_for_proposal.return_value = 0
    
    # Mock services
    mock_llm_service_instance = mock_llm_service.return_value
    mock_vector_db_instance = mock_vector_db_service.return_value
    
    # Create service
    service = ProposalService(mock_session, mock_bot_app)
    service.proposal_repository = mock_proposal_repo
    service.user_service = mock_user_service
    service.submission_repository = mock_submission_repo
    service.llm_service = mock_llm_service_instance
    service.vector_db_service = mock_vector_db_instance
    
    # Call the method
    result, error = await service.edit_proposal_details(
        proposal_id=proposal_id,
        proposer_telegram_id=proposer_id,
        new_title=None,
        new_description=None,
        new_options=new_options  # Only changing options
    )
    
    # Assertions
    assert result == mock_updated_proposal
    assert error is None
    
    # Verify no embedding was generated or stored
    mock_llm_service_instance.generate_embedding.assert_not_called()
    mock_vector_db_instance.add_proposal_embedding.assert_not_called()

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session

@pytest.fixture
def mock_bot_app():
    bot_app = MagicMock()
    bot_app.bot = AsyncMock()
    bot_app.bot.edit_message_text = AsyncMock()
    return bot_app

@pytest.fixture
def mock_proposal_repository(mock_db_session):
    repo = AsyncMock()
    repo.get_proposal_by_id = AsyncMock()
    repo.update_proposal_status = AsyncMock()
    # Add other methods if your service uses them and they need mocking for these tests
    return repo

@pytest.fixture
def proposal_service(mock_db_session, mock_bot_app, mock_proposal_repository):
    # Patch the ProposalRepository instance within the service,
    # or ensure the service is instantiated with the mock.
    # For simplicity, let's assume ProposalService takes repository as an arg or sets it.
    # If ProposalService instantiates its own repository, patching might be needed at module level.
    # For now, let's assume it can be injected or set.
    
    # Re-mocking ProposalRepository inside the fixture to ensure it's used by the service
    # This approach assumes ProposalService might instantiate its own repo if not passed.
    # A cleaner way is if ProposalService accepts the repo in __init__.
    # Based on current service structure, it instantiates repo internally.
    # So we need to patch where it's instantiated or pass it.
    # The service takes session and bot_app. It instantiates repository internally.
    # So, we'll patch 'app.core.proposal_service.ProposalRepository'
    
    with patch('app.core.proposal_service.ProposalRepository', return_value=mock_proposal_repository):
        service = ProposalService(db_session=mock_db_session, bot_app=mock_bot_app)
        # service.proposal_repository = mock_proposal_repository # If it were settable
        return service

@pytest.fixture
def sample_user():
    return User(id=1, telegram_id=12345, username="testuser", first_name="Test")

@pytest.fixture
def sample_proposal(sample_user):
    return Proposal(
        id=1,
        proposer_telegram_id=sample_user.telegram_id,
        title="Test Proposal",
        description="A test proposal.",
        proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        options=["Opt1", "Opt2"],
        target_channel_id="-100123",
        channel_message_id=555,
        creation_date=datetime.now(timezone.utc),
        deadline_date=datetime.now(timezone.utc), # Make sure it's realistic for 'open'
        status=ProposalStatus.OPEN.value,
        proposer=sample_user # Eager loaded proposer
    )

@pytest.mark.asyncio
async def test_cancel_proposal_success(proposal_service, mock_proposal_repository, mock_db_session, mock_bot_app, sample_proposal, sample_user):
    mock_proposal_repository.get_proposal_by_id.return_value = sample_proposal
    
    cancelled_proposal_mock = MagicMock(spec=Proposal)
    cancelled_proposal_mock.id = sample_proposal.id
    cancelled_proposal_mock.title = sample_proposal.title
    cancelled_proposal_mock.description = sample_proposal.description
    cancelled_proposal_mock.status = ProposalStatus.CANCELLED.value
    cancelled_proposal_mock.target_channel_id = sample_proposal.target_channel_id
    cancelled_proposal_mock.channel_message_id = sample_proposal.channel_message_id
    
    mock_proposal_repository.update_proposal_status.return_value = cancelled_proposal_mock
    
    with patch('app.core.proposal_service.telegram_utils.format_proposal_message', return_value="Formatted cancelled message text") as mock_format_message:
        success, message = await proposal_service.cancel_proposal_by_proposer(
            proposal_id=sample_proposal.id,
            user_telegram_id=sample_user.telegram_id
        )

    assert success is True
    assert message == f"Proposal ID {sample_proposal.id} has been successfully cancelled."
    mock_proposal_repository.get_proposal_by_id.assert_called_once_with(sample_proposal.id)
    mock_proposal_repository.update_proposal_status.assert_called_once_with(sample_proposal.id, ProposalStatus.CANCELLED)
    mock_db_session.commit.assert_called_once()
    
    mock_format_message.assert_called_once_with(
        proposal=cancelled_proposal_mock,
        proposer=sample_proposal.proposer
    )
    
    # Construct expected prefix using the same logic as the service
    expected_channel_text_prefix = escape_markdown_v2("--- CANCELLED ---\n\n")
    expected_final_text = expected_channel_text_prefix + "Formatted cancelled message text"
    
    mock_bot_app.bot.edit_message_text.assert_called_once_with(
        chat_id=sample_proposal.target_channel_id,
        message_id=sample_proposal.channel_message_id,
        text=expected_final_text,
        reply_markup=None,
        parse_mode=ParseMode.MARKDOWN_V2
    )

@pytest.mark.asyncio
async def test_cancel_proposal_not_found(proposal_service, mock_proposal_repository, sample_user):
    mock_proposal_repository.get_proposal_by_id.return_value = None

    success, message = await proposal_service.cancel_proposal_by_proposer(
        proposal_id=999, # Non-existent
        user_telegram_id=sample_user.telegram_id
    )

    assert success is False
    assert message == "Proposal not found."
    mock_proposal_repository.get_proposal_by_id.assert_called_once_with(999)
    mock_proposal_repository.update_proposal_status.assert_not_called()
    
@pytest.mark.asyncio
async def test_cancel_proposal_not_proposer(proposal_service, mock_proposal_repository, sample_proposal, sample_user):
    mock_proposal_repository.get_proposal_by_id.return_value = sample_proposal
    
    wrong_user_id = 67890

    success, message = await proposal_service.cancel_proposal_by_proposer(
        proposal_id=sample_proposal.id,
        user_telegram_id=wrong_user_id 
    )

    assert success is False
    assert message == "You are not authorized to cancel this proposal."
    mock_proposal_repository.get_proposal_by_id.assert_called_once_with(sample_proposal.id)
    mock_proposal_repository.update_proposal_status.assert_not_called()

@pytest.mark.asyncio
async def test_cancel_proposal_not_open(proposal_service, mock_proposal_repository, sample_proposal, sample_user):
    sample_proposal.status = ProposalStatus.CLOSED.value # Set to not open
    mock_proposal_repository.get_proposal_by_id.return_value = sample_proposal

    success, message = await proposal_service.cancel_proposal_by_proposer(
        proposal_id=sample_proposal.id,
        user_telegram_id=sample_user.telegram_id
    )

    assert success is False
    assert message == f"This proposal cannot be cancelled. Its current status is: {ProposalStatus.CLOSED.value}"
    mock_proposal_repository.get_proposal_by_id.assert_called_once_with(sample_proposal.id)
    mock_proposal_repository.update_proposal_status.assert_not_called()
    sample_proposal.status = ProposalStatus.OPEN.value # Reset for other tests if fixture is session-scoped

@pytest.mark.asyncio
async def test_cancel_proposal_update_repo_fails(proposal_service, mock_proposal_repository, mock_db_session, sample_proposal, sample_user):
    mock_proposal_repository.get_proposal_by_id.return_value = sample_proposal
    mock_proposal_repository.update_proposal_status.return_value = None # Simulate failure

    success, message = await proposal_service.cancel_proposal_by_proposer(
        proposal_id=sample_proposal.id,
        user_telegram_id=sample_user.telegram_id
    )

    assert success is False
    assert message == "Failed to update proposal status to cancelled."
    mock_proposal_repository.get_proposal_by_id.assert_called_once_with(sample_proposal.id)
    mock_proposal_repository.update_proposal_status.assert_called_once_with(sample_proposal.id, ProposalStatus.CANCELLED)
    mock_db_session.commit.assert_not_called() # Should not commit if update failed

@pytest.mark.asyncio
async def test_cancel_proposal_channel_message_edit_fails(proposal_service, mock_proposal_repository, mock_db_session, mock_bot_app, sample_proposal, sample_user):
    mock_proposal_repository.get_proposal_by_id.return_value = sample_proposal
    
    cancelled_proposal_mock = MagicMock(spec=Proposal) # As in success test
    cancelled_proposal_mock.status = ProposalStatus.CANCELLED.value
    cancelled_proposal_mock.target_channel_id = sample_proposal.target_channel_id
    cancelled_proposal_mock.channel_message_id = sample_proposal.channel_message_id
    # ... other fields if needed by format_proposal_message
    mock_proposal_repository.update_proposal_status.return_value = cancelled_proposal_mock
    
    mock_bot_app.bot.edit_message_text.side_effect = Exception("Telegram API error")

    with patch('app.core.proposal_service.telegram_utils.format_proposal_message', return_value="Formatted message"):
        success, message = await proposal_service.cancel_proposal_by_proposer(
            proposal_id=sample_proposal.id,
            user_telegram_id=sample_user.telegram_id
        )

    assert success is True # Primary action (cancellation) succeeded
    assert message == f"Proposal ID {sample_proposal.id} has been successfully cancelled."
    mock_db_session.commit.assert_called_once() # Commit should still happen
    mock_bot_app.bot.edit_message_text.assert_called_once() # Attempted to edit 