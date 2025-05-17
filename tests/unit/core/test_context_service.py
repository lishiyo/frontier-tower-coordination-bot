import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_service import ContextService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.persistence.repositories.document_repository import DocumentRepository
from app.persistence.models.document_model import Document # For type hinting and asserting

@pytest.fixture
def mock_db_session_for_context():
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    # Add other methods if DocumentRepository starts using them directly in ContextService context
    return session

@pytest.fixture
def mock_llm_service():
    service = AsyncMock(spec=LLMService)
    service.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3]) # Default mock embedding
    return service

@pytest.fixture
def mock_vector_db_service():
    service = AsyncMock(spec=VectorDBService)
    service.store_embeddings = AsyncMock(return_value=["chroma_id_1", "chroma_id_2"])
    return service

@pytest.fixture
def mock_document_repository(mock_db_session_for_context):
    # This mock is for the repository instance *within* ContextService
    repo = AsyncMock(spec=DocumentRepository)
    
    # Mock the add_document method to return a Document-like object with an ID
    mock_sql_doc = Document(id=123, title="Mocked SQL Doc") # Create a real Document for structure
    mock_sql_doc.vector_ids = [] # Initialize as it would be before update
    repo.add_document = AsyncMock(return_value=mock_sql_doc)
    return repo

@pytest.fixture
def context_service(
    mock_db_session_for_context, 
    mock_llm_service, 
    mock_vector_db_service, 
    mock_document_repository
):
    # Patch the DocumentRepository instantiation within ContextService
    with patch('app.core.context_service.DocumentRepository', return_value=mock_document_repository):
        service = ContextService(
            db_session=mock_db_session_for_context,
            llm_service=mock_llm_service,
            vector_db_service=mock_vector_db_service
        )
    return service

@pytest.mark.asyncio
async def test_fetch_content_from_url_success(context_service: ContextService):
    # 1. Mock for the actual response object
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.text = "<html><body>Hello World</body></html>"
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock() # This is a synchronous method

    # 2. Mock for the client object that is yielded by the async context manager's __aenter__
    mock_client_in_context = MagicMock(spec=httpx.AsyncClient)
    mock_client_in_context.get = AsyncMock(return_value=mock_response)

    # 3. Mock for the AsyncClient instance returned by httpx.AsyncClient()
    # This mock needs to implement the async context manager protocol (__aenter__, __aexit__)
    mock_async_client_instance = MagicMock(spec=httpx.AsyncClient)
    mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client_in_context)
    mock_async_client_instance.__aexit__ = AsyncMock(return_value=False) # Or None

    # Patch httpx.AsyncClient class to return our mock_async_client_instance
    with patch('httpx.AsyncClient', return_value=mock_async_client_instance) as mock_async_client_constructor:
        content = await context_service._fetch_content_from_url("http://example.com")
        
        assert content == "<html><body>Hello World</body></html>"
        mock_async_client_constructor.assert_called_once() # Checks if httpx.AsyncClient() was called
        mock_async_client_instance.__aenter__.assert_awaited_once() # Check context manager entry
        mock_client_in_context.get.assert_awaited_once_with("http://example.com", timeout=10.0)
        mock_response.raise_for_status.assert_called_once()
        mock_async_client_instance.__aexit__.assert_awaited_once() # Check context manager exit

@pytest.mark.asyncio
async def test_fetch_content_from_url_http_error(context_service: ContextService, caplog):
    # 1. Mock for the 'response' attribute of the HTTPStatusError
    mock_error_detail_response = MagicMock(spec=httpx.Response)
    mock_error_detail_response.status_code = 404
    mock_error_detail_response.text = "Detailed error from server"

    # 2. The HTTPStatusError that will be raised
    http_error = httpx.HTTPStatusError(
        message="404 Client Error: Not Found for url", 
        request=MagicMock(spec=httpx.Request),
        response=mock_error_detail_response
    )

    # 3. Mock for the actual response object whose raise_for_status will raise the error
    mock_response_that_raises = MagicMock(spec=httpx.Response)
    # Configure text and status_code as if it was a real response before erroring
    mock_response_that_raises.text = "Error content" 
    mock_response_that_raises.status_code = 404
    mock_response_that_raises.raise_for_status = MagicMock(side_effect=http_error)

    # 4. Mock for the client object that is yielded by __aenter__
    mock_client_in_context = MagicMock(spec=httpx.AsyncClient)
    mock_client_in_context.get = AsyncMock(return_value=mock_response_that_raises)

    # 5. Mock for the AsyncClient instance
    mock_async_client_instance = MagicMock(spec=httpx.AsyncClient)
    mock_async_client_instance.__aenter__ = AsyncMock(return_value=mock_client_in_context)
    mock_async_client_instance.__aexit__ = AsyncMock(return_value=False)

    with patch('httpx.AsyncClient', return_value=mock_async_client_instance) as mock_async_client_constructor:
        content = await context_service._fetch_content_from_url("http://example.com/notfound")
        
        assert content is None
        assert "HTTP error fetching URL http://example.com/notfound: 404" in caplog.text
        
        mock_async_client_constructor.assert_called_once()
        mock_async_client_instance.__aenter__.assert_awaited_once()
        mock_client_in_context.get.assert_awaited_once_with("http://example.com/notfound", timeout=10.0)
        mock_response_that_raises.raise_for_status.assert_called_once()
        mock_async_client_instance.__aexit__.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.core.context_service.simple_chunk_text', return_value=["chunk1", "chunk2"]) # Mock chunker
async def test_process_and_store_document_text_success(
    mock_simple_chunk_text, 
    context_service: ContextService, 
    mock_llm_service: LLMService, 
    mock_vector_db_service: VectorDBService, 
    mock_document_repository: DocumentRepository,
    mock_db_session_for_context: AsyncSession
):
    content_source = "This is a test document content."
    source_type = "user_text"
    title = "Test Doc Title"
    proposal_id = 1

    # The mock_document_repository.add_document already returns a mock_sql_doc with id=123
    # and mock_vector_db_service.store_embeddings returns ["chroma_id_1", "chroma_id_2"]

    doc_id = await context_service.process_and_store_document(
        content_source, source_type, title, proposal_id
    )

    assert doc_id == 123 # from mock_document_repository
    mock_simple_chunk_text.assert_called_once_with(content_source, chunk_size=1000, overlap=100)
    
    # Check LLMService calls (one per chunk)
    assert mock_llm_service.generate_embedding.call_count == 2
    mock_llm_service.generate_embedding.assert_any_call("chunk1")
    mock_llm_service.generate_embedding.assert_any_call("chunk2")

    # Check DocumentRepository call
    # The actual call to add_document is inside the patched DocumentRepository instance
    # So mock_document_repository.add_document is what we check
    mock_document_repository.add_document.assert_awaited_once()
    # Get the args from the call to add_document
    add_doc_args = mock_document_repository.add_document.call_args[1]
    assert add_doc_args['title'] == title
    assert add_doc_args['proposal_id'] == proposal_id
    assert add_doc_args['vector_ids'] is None # Initially called with None

    # Check VectorDBService call
    mock_vector_db_service.store_embeddings.assert_awaited_once()
    store_embed_args = mock_vector_db_service.store_embeddings.call_args[1]
    assert store_embed_args['doc_id'] == 123
    assert store_embed_args['text_chunks'] == ["chunk1", "chunk2"]
    assert len(store_embed_args['embeddings']) == 2
    assert store_embed_args['chunk_metadatas'][0]['document_sql_id'] == "123"

    # Check that the db session commit was called (for the final update of vector_ids)
    mock_db_session_for_context.commit.assert_awaited_once()
    # And refresh was called on the sql_document instance
    # The instance is the one returned by mock_document_repository.add_document
    returned_sql_doc = await mock_document_repository.add_document() # get the instance again for assertion
    mock_db_session_for_context.refresh.assert_awaited_once_with(returned_sql_doc)
    assert returned_sql_doc.vector_ids == ["chroma_id_1", "chroma_id_2"] # Check if updated

@pytest.mark.asyncio
@patch('app.core.context_service.simple_chunk_text', return_value=["url chunk1"]) # Mock chunker
@patch('app.core.context_service.ContextService._fetch_content_from_url', new_callable=AsyncMock, return_value="URL fetched content")
async def test_process_and_store_document_url_success(
    mock_fetch_url, 
    mock_simple_chunk_text, 
    context_service: ContextService, 
    mock_llm_service: LLMService, 
    mock_vector_db_service: VectorDBService, 
    mock_document_repository: DocumentRepository,
    mock_db_session_for_context: AsyncSession
):
    content_source_url = "http://example.com/docpage"
    source_type = "user_url"
    # Title should be auto-generated if None

    doc_id = await context_service.process_and_store_document(content_source_url, source_type, title=None)

    assert doc_id == 123
    mock_fetch_url.assert_awaited_once_with(content_source_url)
    mock_simple_chunk_text.assert_called_once_with("URL fetched content", chunk_size=1000, overlap=100)
    mock_llm_service.generate_embedding.assert_awaited_once_with("url chunk1")
    mock_document_repository.add_document.assert_awaited_once()
    add_doc_args = mock_document_repository.add_document.call_args[1]
    assert add_doc_args['title'] == "docpage" # Auto-generated from URL
    assert add_doc_args['source_url'] == content_source_url

    mock_vector_db_service.store_embeddings.assert_awaited_once()
    mock_db_session_for_context.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_process_and_store_document_fetch_url_fails(context_service: ContextService, caplog):
    with patch('app.core.context_service.ContextService._fetch_content_from_url', new_callable=AsyncMock, return_value=None) as mock_fetch:
        doc_id = await context_service.process_and_store_document("http://badurl.com", "user_url", "Bad URL Doc")
        assert doc_id is None
        mock_fetch.assert_awaited_once_with("http://badurl.com")
        assert "Failed to fetch content from URL: http://badurl.com" in caplog.text

@pytest.mark.asyncio
@patch('app.core.context_service.simple_chunk_text', return_value=["chunk1"])
async def test_process_and_store_document_embedding_fails(
    mock_simple_chunk_text,
    context_service: ContextService, 
    mock_llm_service: LLMService, 
    caplog
):
    mock_llm_service.generate_embedding = AsyncMock(return_value=None) # Simulate embedding failure
    doc_id = await context_service.process_and_store_document("Test content", "user_text", "Embedding Fail Doc")
    assert doc_id is None
    assert "Failed to generate embedding for chunk 0" in caplog.text

@pytest.mark.asyncio
@patch('app.core.context_service.simple_chunk_text', return_value=["chunk1"])
async def test_process_and_store_document_sql_storage_fails(
    mock_simple_chunk_text,
    context_service: ContextService, 
    mock_document_repository: DocumentRepository,
    caplog
):
    mock_document_repository.add_document = AsyncMock(return_value=None) # Simulate SQL storage failure
    doc_id = await context_service.process_and_store_document("Test content", "user_text", "SQL Fail Doc")
    assert doc_id is None
    assert "Failed to store document metadata in SQL DB" in caplog.text

@pytest.mark.asyncio
@patch('app.core.context_service.simple_chunk_text', return_value=["chunk1"])
async def test_process_and_store_document_vector_storage_fails(
    mock_simple_chunk_text,
    context_service: ContextService, 
    mock_vector_db_service: VectorDBService,
    mock_document_repository: DocumentRepository, # For the initial successful SQL add
    caplog
):
    # Initial SQL add succeeds (mock_document_repository.add_document returns a doc with id=123 by default)
    mock_vector_db_service.store_embeddings = AsyncMock(return_value=None) # Simulate vector storage failure
    
    doc_id = await context_service.process_and_store_document("Test content", "user_text", "Vector Fail Doc")
    
    # The current logic returns the SQL doc_id even if vector storage fails, but updates vector_ids to []
    # Let's adjust the test based on the current implementation which does NOT return None here.
    # It will attempt to commit the empty vector_ids list.
    # If the design is that it *should* return None, then the code in ContextService needs to change.
    # Based on current ContextService: it logs error, sets sql_document.vector_ids = [], then tries to commit.
    # If that commit succeeds, it returns sql_document.id
    
    assert doc_id == 123 # It still returns the SQL ID
    assert "Failed to store embeddings in VectorDB for SQL document ID 123" in caplog.text
    # Check that the sql_document.vector_ids was indeed set to [] before the commit
    returned_sql_doc = await mock_document_repository.add_document() # get the instance again for assertion
    assert returned_sql_doc.vector_ids == [] # This is checked after it's set due to failure


# Need to import httpx for the side_effect in test_fetch_content_from_url_http_error
# import httpx # This is now at the top

# # Need to import simple_chunk_text for the mock in test_process_and_store_document_text_success
# from app.core.context_service import simple_chunk_text # This import is not needed here as simple_chunk_text is mocked by @patch 