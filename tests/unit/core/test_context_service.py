import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CrawlResult

from app.core.context_service import ContextService
from app.services.llm_service import LLMService
from app.services.vector_db_service import VectorDBService
from app.persistence.repositories.document_repository import DocumentRepository
from app.persistence.models.document_model import Document # For type hinting and asserting

@pytest.fixture
def mock_db_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def mock_llm_service():
    return AsyncMock(spec=LLMService)

@pytest.fixture
def mock_vector_db_service():
    return AsyncMock(spec=VectorDBService)

@pytest.fixture
def context_service(mock_db_session, mock_llm_service, mock_vector_db_service):
    # Patch DocumentRepository within the service's __init__ if it's instantiated there
    with patch('app.core.context_service.DocumentRepository', autospec=True) as MockDocRepo:
        service = ContextService(mock_db_session, mock_llm_service, mock_vector_db_service)
        service.document_repository = MockDocRepo.return_value # Ensure the service uses the mocked repo
        return service

@pytest.mark.asyncio
async def test_fetch_content_from_url_success(context_service: ContextService):
    mock_crawl_result = MagicMock(spec=CrawlResult)
    mock_crawl_result.success = True
    mock_crawl_result.markdown = MagicMock()
    mock_crawl_result.markdown.fit_markdown = "Hello World Markdown"
    mock_crawl_result.markdown.raw_markdown = "Raw Hello World Markdown"

    # Patch AsyncWebCrawler's __aenter__ to return a mock crawler instance
    mock_crawler_instance = AsyncMock(spec=AsyncWebCrawler)
    mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)

    with patch('app.core.context_service.AsyncWebCrawler') as MockAsyncWebCrawler:
        MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance
        MockAsyncWebCrawler.return_value.__aexit__ = AsyncMock(return_value=False)

        content = await context_service._fetch_content_from_url("http://example.com")

        assert content == "Hello World Markdown"
        mock_crawler_instance.arun.assert_called_once()
        # You can add more specific assertions about how arun was called if needed
        # e.g., mock_crawler_instance.arun.assert_called_once_with(url="http://example.com", config=ANY)

@pytest.mark.asyncio
async def test_fetch_content_from_url_success_fallback_to_raw(context_service: ContextService):
    mock_crawl_result = MagicMock(spec=CrawlResult)
    mock_crawl_result.success = True
    mock_crawl_result.markdown = MagicMock()
    mock_crawl_result.markdown.fit_markdown = ""  # Empty fit_markdown to trigger fallback
    mock_crawl_result.markdown.raw_markdown = "Raw Hello World Markdown"

    mock_crawler_instance = AsyncMock(spec=AsyncWebCrawler)
    mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)

    with patch('app.core.context_service.AsyncWebCrawler') as MockAsyncWebCrawler:
        MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance
        MockAsyncWebCrawler.return_value.__aexit__ = AsyncMock(return_value=False)

        content = await context_service._fetch_content_from_url("http://example.com")
        assert content == "Raw Hello World Markdown"

@pytest.mark.asyncio
async def test_fetch_content_from_url_crawl_fail(context_service: ContextService, caplog):
    mock_crawl_result = MagicMock(spec=CrawlResult)
    mock_crawl_result.success = False
    mock_crawl_result.error_message = "Test crawl error"
    mock_crawl_result.markdown = None # Or an empty MarkdownResult

    mock_crawler_instance = AsyncMock(spec=AsyncWebCrawler)
    mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)

    with patch('app.core.context_service.AsyncWebCrawler') as MockAsyncWebCrawler:
        MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance
        MockAsyncWebCrawler.return_value.__aexit__ = AsyncMock(return_value=False)

        content = await context_service._fetch_content_from_url("http://example.com/notfound")

        assert content is None
        assert "Crawl4AI failed to fetch URL http://example.com/notfound. Error: Test crawl error" in caplog.text

@pytest.mark.asyncio
async def test_fetch_content_from_url_no_markdown(context_service: ContextService, caplog):
    mock_crawl_result = MagicMock(spec=CrawlResult)
    mock_crawl_result.success = True
    mock_crawl_result.markdown = MagicMock()
    mock_crawl_result.markdown.fit_markdown = None # No markdown content
    mock_crawl_result.markdown.raw_markdown = None # No markdown content


    mock_crawler_instance = AsyncMock(spec=AsyncWebCrawler)
    mock_crawler_instance.arun = AsyncMock(return_value=mock_crawl_result)

    with patch('app.core.context_service.AsyncWebCrawler') as MockAsyncWebCrawler:
        MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance
        MockAsyncWebCrawler.return_value.__aexit__ = AsyncMock(return_value=False)

        content = await context_service._fetch_content_from_url("http://example.com/nomarkdown")

        assert content is None
        assert "Crawl4AI fetched URL http://example.com/nomarkdown successfully, but no usable markdown content was generated from fit_markdown or raw_markdown." in caplog.text


@pytest.mark.asyncio
async def test_fetch_content_from_url_exception_in_crawl(context_service: ContextService, caplog):
    mock_crawler_instance = AsyncMock(spec=AsyncWebCrawler)
    mock_crawler_instance.arun = AsyncMock(side_effect=Exception("Network issue"))

    with patch('app.core.context_service.AsyncWebCrawler') as MockAsyncWebCrawler:
        MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance
        MockAsyncWebCrawler.return_value.__aexit__ = AsyncMock(return_value=False)

        content = await context_service._fetch_content_from_url("http://example.com/exception")

        assert content is None
        assert "Unexpected error fetching URL http://example.com/exception with Crawl4AI: Network issue" in caplog.text

@pytest.mark.asyncio
async def test_process_and_store_document_url_success(context_service: ContextService, mock_llm_service, mock_vector_db_service):
    test_url = "http://example.com/doc"
    fetched_content = "This is fetched content from the URL. It needs to be long enough for chunking."
    title = "Test Document from URL"
    document_sql_id = 123
    chroma_ids = ["chroma1", "chroma2"]

    # Mock _fetch_content_from_url
    context_service._fetch_content_from_url = AsyncMock(return_value=fetched_content)

    # Mock LLMService methods
    mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])

    # Mock DocumentRepository methods (via the instance on context_service)
    mock_sql_document = MagicMock(spec=Document)
    mock_sql_document.id = document_sql_id
    mock_sql_document.vector_ids = [] # Initial state
    context_service.document_repository.add_document = AsyncMock(return_value=mock_sql_document)

    # Mock VectorDBService methods
    mock_vector_db_service.store_embeddings = AsyncMock(return_value=chroma_ids)

    # Mock db_session commit and refresh
    context_service.db_session.commit = AsyncMock()
    context_service.db_session.refresh = AsyncMock()
    
    # Patch simple_chunk_text
    with patch('app.core.context_service.simple_chunk_text', return_value=["chunk1", "chunk2"]) as mock_chunk_text:
        stored_doc_id = await context_service.process_and_store_document(
            content_source=test_url,
            source_type="user_url",
            title=title
        )

    assert stored_doc_id == document_sql_id
    context_service._fetch_content_from_url.assert_called_once_with(test_url)
    mock_chunk_text.assert_called_once_with(fetched_content, chunk_size=1000, overlap=100)
    assert mock_llm_service.generate_embedding.call_count == 2 # For two chunks
    context_service.document_repository.add_document.assert_called_once()
    # Verify call to add_document
    args, kwargs = context_service.document_repository.add_document.call_args
    assert kwargs['title'] == title
    assert kwargs['source_url'] == test_url
    assert kwargs['raw_content'] == fetched_content
    assert kwargs['vector_ids'] is None # Initially None

    mock_vector_db_service.store_embeddings.assert_called_once()
    args_store_emb, kwargs_store_emb = mock_vector_db_service.store_embeddings.call_args
    assert kwargs_store_emb['doc_id'] == document_sql_id
    assert kwargs_store_emb['text_chunks'] == ["chunk1", "chunk2"]
    assert len(kwargs_store_emb['embeddings']) == 2
    assert len(kwargs_store_emb['chunk_metadatas']) == 2
    assert kwargs_store_emb['chunk_metadatas'][0]['document_sql_id'] == str(document_sql_id)


    context_service.db_session.commit.assert_awaited_once()
    context_service.db_session.refresh.assert_awaited_once_with(mock_sql_document)
    assert mock_sql_document.vector_ids == chroma_ids


@pytest.mark.asyncio
async def test_process_and_store_document_text_success(context_service: ContextService, mock_llm_service, mock_vector_db_service):
    text_content = "This is direct text content. It also needs to be long enough for proper chunking to test."
    title = "Test Document from Text"
    document_sql_id = 456
    chroma_ids = ["chroma3", "chroma4"]

    # Mock LLMService methods
    mock_llm_service.generate_embedding = AsyncMock(return_value=[0.4, 0.5, 0.6])

    # Mock DocumentRepository methods
    mock_sql_document = MagicMock(spec=Document)
    mock_sql_document.id = document_sql_id
    mock_sql_document.vector_ids = []
    context_service.document_repository.add_document = AsyncMock(return_value=mock_sql_document)

    # Mock VectorDBService methods
    mock_vector_db_service.store_embeddings = AsyncMock(return_value=chroma_ids)

    # Mock db_session commit and refresh
    context_service.db_session.commit = AsyncMock()
    context_service.db_session.refresh = AsyncMock()

    with patch('app.core.context_service.simple_chunk_text', return_value=["text_chunk1", "text_chunk2"]) as mock_chunk_text:
        stored_doc_id = await context_service.process_and_store_document(
            content_source=text_content,
            source_type="user_text",
            title=title
        )

    assert stored_doc_id == document_sql_id
    mock_chunk_text.assert_called_once_with(text_content, chunk_size=1000, overlap=100)
    assert mock_llm_service.generate_embedding.call_count == 2
    context_service.document_repository.add_document.assert_called_once()
    args, kwargs = context_service.document_repository.add_document.call_args
    assert kwargs['title'] == title
    assert kwargs['source_url'] is None
    assert kwargs['raw_content'] == text_content
    assert kwargs['vector_ids'] is None

    mock_vector_db_service.store_embeddings.assert_called_once()
    args_store_emb, kwargs_store_emb = mock_vector_db_service.store_embeddings.call_args
    assert kwargs_store_emb['doc_id'] == document_sql_id

    context_service.db_session.commit.assert_awaited_once()
    context_service.db_session.refresh.assert_awaited_once_with(mock_sql_document)
    assert mock_sql_document.vector_ids == chroma_ids

@pytest.mark.asyncio
async def test_process_and_store_document_fetch_url_fails(context_service: ContextService, caplog):
    test_url = "http://example.com/doc_fails"
    context_service._fetch_content_from_url = AsyncMock(return_value=None)

    stored_doc_id = await context_service.process_and_store_document(
        content_source=test_url,
        source_type="user_url",
        title="Failed URL Doc"
    )
    assert stored_doc_id is None
    assert f"Failed to fetch content from URL: {test_url}" in caplog.text
    context_service.document_repository.add_document.assert_not_called()

@pytest.mark.asyncio
async def test_process_and_store_document_no_text_content(context_service: ContextService, caplog):
    stored_doc_id = await context_service.process_and_store_document(
        content_source="", # Empty text
        source_type="user_text",
        title="Empty Text Doc"
    )
    assert stored_doc_id is None
    assert "No text content to process." in caplog.text
    context_service.document_repository.add_document.assert_not_called()

@pytest.mark.asyncio
async def test_process_and_store_document_no_chunks(context_service: ContextService, caplog):
    with patch('app.core.context_service.simple_chunk_text', return_value=[]): # No chunks
        stored_doc_id = await context_service.process_and_store_document(
            content_source="Some text",
            source_type="user_text",
            title="No Chunks Doc"
        )
    assert stored_doc_id is None
    assert "Text content resulted in no chunks." in caplog.text
    context_service.document_repository.add_document.assert_not_called()


@pytest.mark.asyncio
async def test_process_and_store_document_embedding_fails(context_service: ContextService, mock_llm_service, caplog):
    mock_llm_service.generate_embedding = AsyncMock(return_value=None) # Embedding generation fails

    with patch('app.core.context_service.simple_chunk_text', return_value=["chunk1"]):
        stored_doc_id = await context_service.process_and_store_document(
            content_source="Some text",
            source_type="user_text",
            title="Embedding Fail Doc"
        )
    assert stored_doc_id is None
    assert "Failed to generate embedding for chunk 0" in caplog.text
    context_service.document_repository.add_document.assert_not_called() # Should not proceed to DB if embedding fails early

@pytest.mark.asyncio
async def test_process_and_store_document_sql_storage_fails(context_service: ContextService, mock_llm_service, mock_vector_db_service, caplog):
    context_service.document_repository.add_document = AsyncMock(return_value=None) # SQL storage fails
    mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1,0.2])

    with patch('app.core.context_service.simple_chunk_text', return_value=["chunk1"]):
        stored_doc_id = await context_service.process_and_store_document(
            content_source="Some text",
            source_type="user_text",
            title="SQL Fail Doc"
        )
    assert stored_doc_id is None
    assert "Failed to store document metadata in SQL DB" in caplog.text
    mock_vector_db_service.store_embeddings.assert_not_called()

@pytest.mark.asyncio
async def test_process_and_store_document_vector_storage_fails(context_service: ContextService, mock_llm_service, mock_vector_db_service, caplog):
    document_sql_id = 789
    mock_sql_doc = MagicMock(spec=Document); mock_sql_doc.id = document_sql_id; mock_sql_doc.vector_ids = []
    context_service.document_repository.add_document = AsyncMock(return_value=mock_sql_doc)
    mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1,0.2])
    mock_vector_db_service.store_embeddings = AsyncMock(return_value=None) # Vector storage fails

    context_service.db_session.commit = AsyncMock() # Mock commit for the final update
    context_service.db_session.refresh = AsyncMock()

    with patch('app.core.context_service.simple_chunk_text', return_value=["chunk1"]):
        stored_doc_id = await context_service.process_and_store_document(
            content_source="Some text",
            source_type="user_text",
            title="Vector Fail Doc"
        )
    
    assert stored_doc_id == document_sql_id # SQL doc is created, but vector linking might be empty
    assert f"Failed to store embeddings in VectorDB for SQL document ID {document_sql_id}" in caplog.text
    context_service.db_session.commit.assert_awaited_once() # Commit is still called to save the document with (now empty) vector_ids
    assert mock_sql_doc.vector_ids == [] # Ensure vector_ids is empty list on the SQL object after failure

@pytest.mark.asyncio
async def test_process_and_store_document_vector_id_commit_fails(context_service: ContextService, mock_llm_service, mock_vector_db_service, caplog):
    document_sql_id = 101112
    chroma_ids = ["chroma_final_fail1"]
    mock_sql_doc = MagicMock(spec=Document); mock_sql_doc.id = document_sql_id; mock_sql_doc.vector_ids = []
    context_service.document_repository.add_document = AsyncMock(return_value=mock_sql_doc)
    mock_llm_service.generate_embedding = AsyncMock(return_value=[0.1,0.2])
    mock_vector_db_service.store_embeddings = AsyncMock(return_value=chroma_ids) # Vector storage succeeds

    context_service.db_session.commit = AsyncMock(side_effect=Exception("DB commit error")) # Final commit fails
    context_service.db_session.refresh = AsyncMock() # Won't be called if commit fails

    with patch('app.core.context_service.simple_chunk_text', return_value=["chunk1"]):
        stored_doc_id = await context_service.process_and_store_document(
            content_source="Some text",
            source_type="user_text",
            title="Final Commit Fail Doc"
        )
    
    assert stored_doc_id is None # If final commit fails, we treat it as overall failure for returning ID
    assert f"Error committing vector_ids to SQL document ID {document_sql_id}" in caplog.text
    assert mock_sql_doc.vector_ids == chroma_ids # vector_ids were set on the object, but commit failed

@pytest.mark.asyncio
async def test_get_document_content_success(context_service: ContextService):
    doc_id = 1
    expected_content = "This is the document's raw content."
    mock_document = Document(id=doc_id, title="Test Doc", raw_content=expected_content)
    context_service.document_repository.get_document_by_id = AsyncMock(return_value=mock_document)

    content = await context_service.get_document_content(doc_id)

    assert content == expected_content
    context_service.document_repository.get_document_by_id.assert_called_once_with(doc_id)

@pytest.mark.asyncio
async def test_get_document_content_no_content(context_service: ContextService, caplog):
    doc_id = 2
    mock_document = Document(id=doc_id, title="Test Doc No Content", raw_content=None)
    context_service.document_repository.get_document_by_id = AsyncMock(return_value=mock_document)

    content = await context_service.get_document_content(doc_id)

    assert content is None
    assert f"Document ID {doc_id} found, but it has no raw_content." in caplog.text

@pytest.mark.asyncio
async def test_get_document_content_not_found(context_service: ContextService, caplog):
    doc_id = 3
    context_service.document_repository.get_document_by_id = AsyncMock(return_value=None)

    content = await context_service.get_document_content(doc_id)

    assert content is None
    assert f"Document ID {doc_id} not found." in caplog.text

@pytest.mark.asyncio
async def test_list_documents_for_proposal_found(context_service: ContextService):
    proposal_id = 10
    mock_docs = [
        Document(id=1, title="Doc A", proposal_id=proposal_id),
        Document(id=2, title="Doc B", proposal_id=proposal_id)
    ]
    context_service.document_repository.get_documents_by_proposal_id = AsyncMock(return_value=mock_docs)

    documents = await context_service.list_documents_for_proposal(proposal_id)

    assert documents == mock_docs
    context_service.document_repository.get_documents_by_proposal_id.assert_called_once_with(proposal_id)

@pytest.mark.asyncio
async def test_list_documents_for_proposal_none_found(context_service: ContextService):
    proposal_id = 11
    context_service.document_repository.get_documents_by_proposal_id = AsyncMock(return_value=[])

    documents = await context_service.list_documents_for_proposal(proposal_id)

    assert documents == []
    context_service.document_repository.get_documents_by_proposal_id.assert_called_once_with(proposal_id)

@pytest.mark.asyncio
async def test_get_answer_for_question_success(context_service: ContextService, mock_llm_service, mock_vector_db_service):
    question = "What is the capital of France?"
    query_embedding = [0.1, 0.2]
    # Updated to match the structure used in ContextService
    # The actual text chunk is 'document_content'
    # 'title' comes from metadata.title
    # 'document_sql_id' comes from metadata.document_sql_id
    # 'proposal_id' (optional) comes from metadata.proposal_id
    similar_chunks = [
        {
            "document_content": "Paris is the capital and most populous city of France.",
            "metadata": {"document_sql_id": "doc1", "title": "France Info", "chunk_text_preview": "Paris is..."}
        }
    ]
    expected_answer_from_llm = "The capital of France is Paris."
    expected_final_answer = expected_answer_from_llm + "\n\nSources: 'France Info' (Doc ID: doc1)."

    mock_llm_service.generate_embedding = AsyncMock(return_value=query_embedding)
    mock_vector_db_service.search_similar_chunks = AsyncMock(return_value=similar_chunks)
    mock_llm_service.get_completion = AsyncMock(return_value=expected_answer_from_llm)

    answer = await context_service.get_answer_for_question(question)

    assert answer == expected_final_answer
    mock_llm_service.generate_embedding.assert_called_once_with(question)
    mock_vector_db_service.search_similar_chunks.assert_called_once_with(
        query_embedding=query_embedding, proposal_id_filter=None, top_n=3
    )
    mock_llm_service.get_completion.assert_called_once()
    # Optionally, inspect the prompt sent to get_completion

@pytest.mark.asyncio
async def test_get_answer_for_question_with_proposal_filter(context_service: ContextService, mock_llm_service, mock_vector_db_service):
    question = "Details about project X?"
    proposal_id = 123
    query_embedding = [0.3, 0.4]
    similar_chunks_proposal = [
        {
            "document_content": "Project X is about coding.",
            "metadata": {"document_sql_id": "doc_propX", "title": "Proposal 123 context: Project X is...", "proposal_id": str(proposal_id), "chunk_text_preview": "Project X is..."}
        }
    ]
    expected_answer_from_llm = "Project X is about coding."
    # Note: The source citation format for proposal-linked docs is different
    # The code generates: f"Proposal {linked_proposal_id} context: {preview_text[:30]}..."
    # If chunk_text_preview is "Project X is...", then preview_text[:30] is "Project X is..."
    # So doc_title_display becomes "Proposal 123 context: Project X is......"
    expected_final_answer = expected_answer_from_llm + "\n\nSources: 'Proposal 123 context: Project X is......' (Doc ID: doc_propX)."


    mock_llm_service.generate_embedding = AsyncMock(return_value=query_embedding)
    mock_vector_db_service.search_similar_chunks = AsyncMock(return_value=similar_chunks_proposal)
    mock_llm_service.get_completion = AsyncMock(return_value=expected_answer_from_llm)

    answer = await context_service.get_answer_for_question(question, proposal_id_filter=proposal_id)

    assert answer == expected_final_answer
    mock_vector_db_service.search_similar_chunks.assert_called_once_with(
        query_embedding=query_embedding, proposal_id_filter=proposal_id, top_n=3
    )

@pytest.mark.asyncio
async def test_get_answer_for_question_no_chunks_found_initially_then_found_globally(context_service: ContextService, mock_llm_service, mock_vector_db_service):
    question = "Obscure data point?"
    proposal_id = 777
    query_embedding = [0.5, 0.6]
    global_chunks = [
        {"document_content": "Global data point found.", "metadata": {"document_sql_id": "global_doc1", "title": "Global Data Doc"}}
    ]
    expected_answer_from_llm = "Global data point found."
    expected_final_answer = expected_answer_from_llm + "\n\nSources: 'Global Data Doc' (Doc ID: global_doc1)."

    mock_llm_service.generate_embedding = AsyncMock(return_value=query_embedding)
    # First call (with proposal filter) returns no chunks
    # Second call (global) returns chunks
    mock_vector_db_service.search_similar_chunks.side_effect = [
        [],  # No proposal-specific chunks
        global_chunks # Global chunks found on retry
    ]
    mock_llm_service.get_completion = AsyncMock(return_value=expected_answer_from_llm)

    answer = await context_service.get_answer_for_question(question, proposal_id_filter=proposal_id)

    assert answer == expected_final_answer
    assert mock_vector_db_service.search_similar_chunks.call_count == 2
    mock_vector_db_service.search_similar_chunks.assert_any_call(
        query_embedding=query_embedding, proposal_id_filter=proposal_id, top_n=3
    )
    mock_vector_db_service.search_similar_chunks.assert_any_call(
        query_embedding=query_embedding, proposal_id_filter=None, top_n=3
    )

@pytest.mark.asyncio
async def test_get_answer_for_question_no_chunks_found_at_all(context_service: ContextService, mock_llm_service, mock_vector_db_service):
    question = "Data not in DB?"
    query_embedding = [0.7, 0.8]

    mock_llm_service.generate_embedding = AsyncMock(return_value=query_embedding)
    mock_vector_db_service.search_similar_chunks = AsyncMock(return_value=[]) # No chunks found at all

    answer = await context_service.get_answer_for_question(question)

    assert answer == "I couldn't find any relevant information for your question."
    mock_llm_service.get_completion.assert_not_called()

@pytest.mark.asyncio
async def test_get_answer_for_question_embedding_failure_for_question(context_service: ContextService, mock_llm_service, mock_vector_db_service):
    question = "A question"
    mock_llm_service.generate_embedding = AsyncMock(return_value=None) # Embedding fails

    answer = await context_service.get_answer_for_question(question)

    assert answer == "I couldn't process your question at the moment. Please try again later."
    mock_vector_db_service.search_similar_chunks.assert_not_called()
    mock_llm_service.get_completion.assert_not_called()

@pytest.mark.asyncio
async def test_get_answer_for_question_empty_text_in_chunks(context_service: ContextService, mock_llm_service, mock_vector_db_service):
    question = "Question about empty context"
    query_embedding = [0.1, 0.2]
    similar_chunks_empty_text = [
        {"document_content": "", "metadata": {"document_sql_id": "doc_empty", "title": "Empty Doc Content"}}
    ]
    mock_llm_service.generate_embedding = AsyncMock(return_value=query_embedding)
    mock_vector_db_service.search_similar_chunks = AsyncMock(return_value=similar_chunks_empty_text)

    answer = await context_service.get_answer_for_question(question)
    assert answer == "I found some documents that might be related, but I couldn't extract specific text to answer your question."
    mock_llm_service.get_completion.assert_not_called()

# Placeholder for get_intelligent_help tests - to be implemented when method is fully defined
# @pytest.mark.asyncio
# async def test_get_intelligent_help_success(context_service: ContextService, mock_llm_service):
#     pass