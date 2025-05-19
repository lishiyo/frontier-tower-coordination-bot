import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.submission_service import SubmissionService
from app.persistence.models.submission_model import Submission
from app.persistence.models.proposal_model import Proposal, ProposalType, ProposalStatus # Import Proposal related models
from app.persistence.models.user_model import User # Import User model for proposer
from app.utils.telegram_utils import format_datetime_for_display # For formatting dates

@pytest.mark.asyncio
async def test_get_user_submission_history_found():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    submitter_id = 123

    # Mock User for proposer
    mock_proposer = User(id=1, telegram_id=789, username="proposer_user", first_name="Proposer")

    # Mock Submissions
    mock_submission1 = Submission(
        id=1, proposal_id=101, submitter_id=submitter_id, 
        response_content="Vote A", timestamp=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    )
    mock_submission2 = Submission(
        id=2, proposal_id=102, submitter_id=submitter_id, 
        response_content="My idea", timestamp=datetime(2023, 1, 2, 11, 0, 0, tzinfo=timezone.utc)
    )
    mock_submissions = [mock_submission1, mock_submission2]

    # Mock Proposals
    mock_proposal1 = Proposal(
        id=101, proposer_telegram_id=789, title="Prop One", 
        description="Desc 1", proposal_type=ProposalType.MULTIPLE_CHOICE.value,
        options=["Vote A", "Vote B"], target_channel_id="-1001", channel_message_id=50,
        creation_date=datetime(2023, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
        deadline_date=datetime(2023, 1, 8, 9, 0, 0, tzinfo=timezone.utc),
        status=ProposalStatus.OPEN.value, outcome=None, raw_results=None,
        proposer=mock_proposer
    )
    mock_proposal2 = Proposal(
        id=102, proposer_telegram_id=789, title="Prop Two", 
        description="Desc 2", proposal_type=ProposalType.FREE_FORM.value,
        options=None, target_channel_id="-1002", channel_message_id=51,
        creation_date=datetime(2023, 1, 2, 9, 0, 0, tzinfo=timezone.utc),
        deadline_date=datetime(2023, 1, 9, 9, 0, 0, tzinfo=timezone.utc),
        status=ProposalStatus.CLOSED.value, outcome="Summary of ideas", raw_results={},
        proposer=mock_proposer
    )
    mock_proposals_dict = {101: mock_proposal1, 102: mock_proposal2}

    service = SubmissionService(mock_session)

    # Patch repository methods used by the service
    with patch.object(service.submission_repository, 'get_submissions_by_user', return_value=mock_submissions) as mock_get_subs:
        with patch.object(service.proposal_repository, 'get_proposals_by_ids', side_effect=lambda ids: [mock_proposals_dict[pid] for pid in ids if pid in mock_proposals_dict]) as mock_get_props:

            # Act
            history = await service.get_user_submission_history(submitter_id)

            # Assert
            mock_get_subs.assert_called_once_with(submitter_id)
            mock_get_props.assert_called_once_with([101, 102]) # Check it's called with unique proposal_ids

            assert len(history) == 2
            
            # Item 1
            assert history[0]["proposal_title"] == "Prop One"
            assert history[0]["user_response"] == "Vote A"
            assert history[0]["proposal_status"] == ProposalStatus.OPEN.value
            assert history[0]["proposal_outcome"] == "N/A"  # Or None, depending on what's set
            assert history[0]["submission_timestamp"] == format_datetime_for_display(mock_submission1.timestamp)

            # Item 2
            assert history[1]["proposal_title"] == "Prop Two"
            assert history[1]["user_response"] == "My idea"
            assert history[1]["proposal_status"] == ProposalStatus.CLOSED.value
            assert history[1]["proposal_outcome"] == "Summary of ideas"
            assert history[1]["submission_timestamp"] == format_datetime_for_display(mock_submission2.timestamp)

@pytest.mark.asyncio
async def test_get_user_submission_history_no_submissions():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    submitter_id = 123

    service = SubmissionService(mock_session)

    with patch.object(service.submission_repository, 'get_submissions_by_user', return_value=[]) as mock_get_subs:
        with patch.object(service.proposal_repository, 'get_proposals_by_ids') as mock_get_props:

            # Act
            history = await service.get_user_submission_history(submitter_id)

            # Assert
            mock_get_subs.assert_called_once_with(submitter_id)
            mock_get_props.assert_not_called() # Should not be called if no submissions
            assert len(history) == 0 