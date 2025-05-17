import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence.models.document_model import Document
from app.persistence.repositories.document_repository import DocumentRepository
from datetime import datetime

@pytest.fixture
def mock_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session

@pytest.mark.asyncio
async def test_add_document(mock_db_session):
    document_repo = DocumentRepository(mock_db_session)

    title = "Test Document"
    content_hash = "testhash123"
    source_url = "http://example.com/doc"
    vector_ids = ["vec1", "vec2"]
    proposal_id = 1

    # Call the method
    added_document = await document_repo.add_document(
        title=title,
        content_hash=content_hash,
        source_url=source_url,
        vector_ids=vector_ids,
        proposal_id=proposal_id
    )

    # Assert that session.add was called once
    mock_db_session.add.assert_called_once()
    
    # Get the actual Document object passed to session.add
    added_instance = mock_db_session.add.call_args[0][0]
    
    # Assert that the object passed to session.add is an instance of Document
    assert isinstance(added_instance, Document)
    
    # Assert attributes of the Document instance
    assert added_instance.title == title
    assert added_instance.content_hash == content_hash
    assert added_instance.source_url == source_url
    assert added_instance.vector_ids == vector_ids
    assert added_instance.proposal_id == proposal_id
    # upload_date is server_default, so we don't check its exact value here
    # but we can check it's a datetime if it were set by the constructor directly

    # Assert that commit and refresh were called
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once_with(added_instance)

    # Assert that the returned document is the one that was processed
    # (refresh is mocked, so added_document is the same instance as added_instance before refresh)
    assert added_document == added_instance

@pytest.mark.asyncio
async def test_add_document_minimal_args(mock_db_session):
    document_repo = DocumentRepository(mock_db_session)

    # Test with only required or minimal arguments, others None
    title = "Minimal Doc"

    added_document = await document_repo.add_document(
        title=title,
        content_hash=None,
        source_url=None,
        vector_ids=None,
        proposal_id=None
    )

    mock_db_session.add.assert_called_once()
    added_instance = mock_db_session.add.call_args[0][0]
    assert isinstance(added_instance, Document)
    assert added_instance.title == title
    assert added_instance.content_hash is None
    assert added_instance.source_url is None
    assert added_instance.vector_ids is None
    assert added_instance.proposal_id is None

    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once_with(added_instance)
    assert added_document == added_instance 