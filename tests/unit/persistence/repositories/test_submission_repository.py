import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional # Import Optional
from datetime import datetime, timezone # Import timezone

from app.persistence.models.submission_model import Submission
from app.persistence.repositories.submission_repository import SubmissionRepository

@pytest.mark.asyncio
async def test_get_submissions_by_user_found():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    submitter_id = 12345
    
    # Sample submission data
    submission1_data = {
        "id": 1, "proposal_id": 101, "submitter_id": submitter_id, 
        "response_content": "Vote for Option A", 
        "timestamp": datetime.now(timezone.utc) # Add timezone.utc
    }
    submission2_data = {
        "id": 2, "proposal_id": 102, "submitter_id": submitter_id, 
        "response_content": "My great idea!", 
        "timestamp": datetime.now(timezone.utc) # Add timezone.utc
    }
    
    mock_submission1 = Submission(**submission1_data)
    mock_submission2 = Submission(**submission2_data)
    
    # Mock the execute method to return a result that has scalars().all()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_submission1, mock_submission2]
    mock_session.execute.return_value = mock_result
    
    repo = SubmissionRepository(mock_session)

    # Act
    submissions = await repo.get_submissions_by_user(submitter_id)

    # Assert
    assert len(submissions) == 2
    assert submissions[0].id == 1
    assert submissions[1].id == 2
    assert submissions[0].submitter_id == submitter_id
    assert submissions[1].submitter_id == submitter_id
    
    # Check that select was called correctly (basic check)
    assert mock_session.execute.call_args is not None
    called_stmt = mock_session.execute.call_args[0][0]
    assert str(called_stmt.compile(compile_kwargs={"literal_binds": True})).startswith(
        "SELECT submissions.id, submissions.proposal_id, submissions.submitter_id, submissions.response_content, submissions.timestamp"
    ) # Updated to reflect actual fields
    assert f"WHERE submissions.submitter_id = {submitter_id}" in str(called_stmt.compile(compile_kwargs={"literal_binds": True}))

@pytest.mark.asyncio
async def test_get_submissions_by_user_not_found():
    # Arrange
    mock_session = AsyncMock(spec=AsyncSession)
    submitter_id = 12345
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [] # No submissions found
    mock_session.execute.return_value = mock_result
    
    repo = SubmissionRepository(mock_session)

    # Act
    submissions = await repo.get_submissions_by_user(submitter_id)

    # Assert
    assert len(submissions) == 0
    mock_session.execute.assert_called_once() 