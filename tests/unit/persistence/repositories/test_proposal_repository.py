import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional # Import Optional
from datetime import datetime, timezone # Import timezone

from app.persistence.models.proposal_model import Proposal, ProposalStatus, ProposalType
from app.persistence.repositories.proposal_repository import ProposalRepository

@pytest.mark.asyncio
async def test_get_proposals_by_ids_found():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    proposal_ids = [1, 2]
    
    # Sample proposal data matching Proposal model structure
    proposal1_data = {
        "id": 1, "proposer_telegram_id": 123, "title": "Prop 1", 
        "description": "Desc 1", "proposal_type": ProposalType.MULTIPLE_CHOICE.value,
        "options": ["A", "B"], "target_channel_id": "-1001", "channel_message_id": 50,
        "creation_date": datetime.now(timezone.utc), # Add timezone.utc
        "deadline_date": datetime.now(timezone.utc), # Add timezone.utc
        "status": ProposalStatus.OPEN.value, "outcome": None, "raw_results": None
    }
    proposal2_data = {
        "id": 2, "proposer_telegram_id": 456, "title": "Prop 2", 
        "description": "Desc 2", "proposal_type": ProposalType.FREE_FORM.value,
        "options": None, "target_channel_id": "-1002", "channel_message_id": 51,
        "creation_date": datetime.now(timezone.utc), # Add timezone.utc
        "deadline_date": datetime.now(timezone.utc), # Add timezone.utc
        "status": ProposalStatus.CLOSED.value, "outcome": "Summary", "raw_results": {}
    }
    
    mock_proposal1 = Proposal(**proposal1_data)
    mock_proposal2 = Proposal(**proposal2_data)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_proposal1, mock_proposal2]
    mock_session.execute.return_value = mock_result
    
    repo = ProposalRepository(mock_session)

    # Act
    proposals = await repo.get_proposals_by_ids(proposal_ids)

    # Assert
    assert len(proposals) == 2
    assert proposals[0].id == 1
    assert proposals[1].id == 2
    
    assert mock_session.execute.call_args is not None
    called_stmt = mock_session.execute.call_args[0][0]
    # A bit more robust to check for the IN clause part of the query
    compiled_query_str = str(called_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "proposals.id IN (1, 2)" in compiled_query_str # Check for the IN clause specifically

@pytest.mark.asyncio
async def test_get_proposals_by_ids_not_found():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    proposal_ids = [3, 4]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    repo = ProposalRepository(mock_session)

    # Act
    proposals = await repo.get_proposals_by_ids(proposal_ids)

    # Assert
    assert len(proposals) == 0
    mock_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_proposals_by_ids_empty_list():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    proposal_ids = []
    repo = ProposalRepository(mock_session)

    # Act
    proposals = await repo.get_proposals_by_ids(proposal_ids)

    # Assert
    assert len(proposals) == 0
    mock_session.execute.assert_not_called() # Should not query DB if list is empty 

@pytest.mark.asyncio
async def test_get_proposals_by_proposer_id_found():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    proposer_telegram_id = 12345
    
    proposal1_data = {
        "id": 1, "proposer_telegram_id": proposer_telegram_id, "title": "My Prop 1", 
        "description": "Desc 1", "proposal_type": ProposalType.MULTIPLE_CHOICE.value,
        "options": ["A", "B"], "target_channel_id": "-1001", "channel_message_id": 50,
        "creation_date": datetime.now(timezone.utc),
        "deadline_date": datetime.now(timezone.utc),
        "status": ProposalStatus.OPEN.value
    }
    proposal2_data = {
        "id": 2, "proposer_telegram_id": proposer_telegram_id, "title": "My Prop 2", 
        "description": "Desc 2", "proposal_type": ProposalType.FREE_FORM.value,
        "options": None, "target_channel_id": "-1002", "channel_message_id": 51,
        "creation_date": datetime.now(timezone.utc),
        "deadline_date": datetime.now(timezone.utc),
        "status": ProposalStatus.CLOSED.value
    }
    mock_proposal1 = Proposal(**proposal1_data)
    mock_proposal2 = Proposal(**proposal2_data)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_proposal1, mock_proposal2]
    mock_session.execute.return_value = mock_result
    
    repo = ProposalRepository(mock_session)

    # Act
    proposals = await repo.get_proposals_by_proposer_id(proposer_telegram_id)

    # Assert
    assert len(proposals) == 2
    assert proposals[0].id == 1
    assert proposals[1].id == 2
    assert proposals[0].proposer_telegram_id == proposer_telegram_id
    assert proposals[1].proposer_telegram_id == proposer_telegram_id
    
    assert mock_session.execute.call_args is not None
    called_stmt = mock_session.execute.call_args[0][0]
    compiled_query_str = str(called_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert f"WHERE proposals.proposer_telegram_id = {proposer_telegram_id}" in compiled_query_str
    assert "ORDER BY proposals.creation_date DESC" in compiled_query_str

@pytest.mark.asyncio
async def test_get_proposals_by_proposer_id_not_found():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    proposer_telegram_id = 12345
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    repo = ProposalRepository(mock_session)

    # Act
    proposals = await repo.get_proposals_by_proposer_id(proposer_telegram_id)

    # Assert
    assert len(proposals) == 0
    mock_session.execute.assert_called_once() 