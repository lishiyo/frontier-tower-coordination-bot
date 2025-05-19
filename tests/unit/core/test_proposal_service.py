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