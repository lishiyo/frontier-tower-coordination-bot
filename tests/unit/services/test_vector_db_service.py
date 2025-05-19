import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.vector_db_service import VectorDBService, CHROMA_DATA_PATH, DEFAULT_COLLECTION_NAME, PROPOSALS_COLLECTION_NAME

# Mock chromadb parts
@pytest.fixture
def mock_chroma_client_and_collection():
    mock_collection = MagicMock()
    mock_collection.add = MagicMock()
    mock_collection.query = MagicMock()
    mock_collection.upsert = MagicMock()  # Add upsert mock for proposal tests

    mock_client = MagicMock()
    mock_client.get_or_create_collection = MagicMock(return_value=mock_collection)
    
    return mock_client, mock_collection

@pytest.fixture
@patch('chromadb.PersistentClient')
def vector_db_service_with_mocked_client(MockPersistentClient, mock_chroma_client_and_collection):
    mock_client, _ = mock_chroma_client_and_collection
    MockPersistentClient.return_value = mock_client
    service = VectorDBService(path=".test_chroma_data_vdb") # Path doesn't matter due to mock
    service.client = mock_client # Ensure the instance uses our fully mocked client object
    return service, mock_client, _ # service, client_mock, collection_mock

@pytest.mark.asyncio
async def test_vector_db_service_init_success(vector_db_service_with_mocked_client):
    service, mock_client, _ = vector_db_service_with_mocked_client
    assert service.client is not None
    # Check if PersistentClient was called with the correct path during actual init (before override)
    # This is a bit tricky as we are patching PersistentClient globally for the fixture scope.
    # For this test, we mostly care that service.client is the mock_client.
    assert service.client == mock_client

@pytest.mark.asyncio
async def test_get_or_create_collection(vector_db_service_with_mocked_client):
    service, mock_client, mock_collection = vector_db_service_with_mocked_client
    collection_name = "my_test_collection"
    
    ret_collection = service._get_or_create_collection(collection_name)
    
    mock_client.get_or_create_collection.assert_called_once_with(name=collection_name)
    assert ret_collection == mock_collection

@pytest.mark.asyncio
async def test_store_embeddings_success(vector_db_service_with_mocked_client):
    service, mock_client, mock_collection = vector_db_service_with_mocked_client
    doc_id = 1
    text_chunks = ["chunk1", "chunk2"]
    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    # User provided metadatas (can be None or list of dicts)
    user_provided_chunk_metadatas = [
        {"custom_key": "val1", "document_sql_id": "override_me", "chunk_index": -1},
        {"another_key": "val2"}
    ]

    expected_chroma_ids = [f"doc_{doc_id}_chunk_0", f"doc_{doc_id}_chunk_1"]
    
    # This is how final_metadatas will be constructed inside store_embeddings
    expected_final_metadatas = [
        {
            "document_sql_id": str(doc_id), 
            "chunk_text_preview": "chunk1"[:100],
            "custom_key": "val1", # from user_provided_chunk_metadatas
            "chunk_index": 0 # also from user_provided_chunk_metadatas, if it exists, or default
        },
        {
            "document_sql_id": str(doc_id), 
            "chunk_text_preview": "chunk2"[:100],
            "another_key": "val2" # from user_provided_chunk_metadatas
        }
    ]
    # The user_provided_metadatas will be updated by default ones, so we need to reconstruct
    # what the service will actually pass to collection.add()
    # Let's refine `expected_final_metadatas` based on the logic in `store_embeddings`

    # Re-calculate expected_final_metadatas based on the actual logic in store_embeddings:
    # Default metadata: {"document_sql_id": str(doc_id), "chunk_text_preview": chunk[:100]}
    # Then user_provided_chunk_metadatas[i] is updated into it.

    recalculated_expected_final_metadatas = []
    for i, chunk in enumerate(text_chunks):
        base_meta = {"document_sql_id": str(doc_id), "chunk_text_preview": chunk[:100]}
        if user_provided_chunk_metadatas and i < len(user_provided_chunk_metadatas) and user_provided_chunk_metadatas[i]:
            base_meta.update(user_provided_chunk_metadatas[i])
        recalculated_expected_final_metadatas.append(base_meta)


    # Mock _get_or_create_collection to return the mock_collection
    service._get_or_create_collection = MagicMock(return_value=mock_collection)

    result_ids = await service.store_embeddings(doc_id, text_chunks, embeddings, user_provided_chunk_metadatas, "test_coll")

    service._get_or_create_collection.assert_called_once_with("test_coll")
    mock_collection.add.assert_called_once_with(
        embeddings=embeddings,
        documents=text_chunks,
        metadatas=recalculated_expected_final_metadatas, # Use the accurately constructed one
        ids=expected_chroma_ids
    )
    assert result_ids == expected_chroma_ids

@pytest.mark.asyncio
async def test_store_embeddings_mismatch_lengths(vector_db_service_with_mocked_client):
    service, _, _ = vector_db_service_with_mocked_client
    result = await service.store_embeddings(1, ["chunk1"], [[0.1,0.2], [0.3,0.4]])
    assert result is None
    result = await service.store_embeddings(1, ["c1", "c2"], [[0.1,0.2]], chunk_metadatas=[{},{},{}])
    assert result is None

@pytest.mark.asyncio
async def test_search_similar_chunks_success(vector_db_service_with_mocked_client):
    service, mock_client, mock_collection = vector_db_service_with_mocked_client
    query_embedding = [0.5, 0.6]
    top_n = 3
    mock_query_results = {
        'ids': [['id1', 'id2']],
        'distances': [[0.1, 0.2]],
        'metadatas': [[{'info': 'meta1'}, {'info': 'meta2'}]],
        'documents': [["doc_content1", "doc_content2"]]
    }
    mock_collection.query = MagicMock(return_value=mock_query_results)
    service._get_or_create_collection = MagicMock(return_value=mock_collection) # Ensure mock collection is used

    results = await service.search_similar_chunks(query_embedding, top_n, collection_name="search_coll")

    service._get_or_create_collection.assert_called_once_with("search_coll")
    mock_collection.query.assert_called_once_with(
        query_embeddings=[query_embedding],
        n_results=top_n,
        where=None,
        include=['metadatas', 'documents', 'distances']
    )
    assert len(results) == 2
    assert results[0]["id"] == "id1"
    assert results[1]["metadata"] == {'info': 'meta2'}

@pytest.mark.asyncio
async def test_search_similar_chunks_with_filter(vector_db_service_with_mocked_client):
    service, mock_client, mock_collection = vector_db_service_with_mocked_client
    query_embedding = [0.7, 0.8]
    proposal_id_filter = 123
    expected_where_filter = {"proposal_id": str(proposal_id_filter)}
    
    mock_collection.query = MagicMock(return_value={'ids': [[]]}) # Empty results for simplicity
    service._get_or_create_collection = MagicMock(return_value=mock_collection)

    await service.search_similar_chunks(query_embedding, proposal_id_filter=proposal_id_filter)

    mock_collection.query.assert_called_once()
    call_args = mock_collection.query.call_args
    assert call_args[1]['where'] == expected_where_filter

@pytest.mark.asyncio
async def test_vector_db_service_client_not_initialized(vector_db_service_with_mocked_client):
    service, _, _ = vector_db_service_with_mocked_client
    service.client = None # Simulate client initialization failure

    assert await service.store_embeddings(1, ["c"], [[0.1]], [{}]) is None
    assert await service.search_similar_chunks([0.1]) is None
    with pytest.raises(ConnectionError):
        service._get_or_create_collection("any_collection")

# Tests for proposal embedding functionality - converted from unittest style to pytest style
@pytest.mark.asyncio
async def test_add_proposal_embedding(vector_db_service_with_mocked_client):
    """Test adding a proposal embedding to ChromaDB"""
    service, _, mock_collection = vector_db_service_with_mocked_client
    
    # Test data
    proposal_id = 123
    text_content = "Test Title Test Description"
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Simplified embedding vector
    metadata = {
        "status": "open",
        "deadline_date_iso": "2023-12-31T23:59:59",
        "creation_date_iso": "2023-01-01T12:00:00",
        "proposal_type": "multiple_choice",
        "target_channel_id": "-1001234567890"
    }
    
    # Mock _get_or_create_collection before calling the method that uses it
    service._get_or_create_collection = MagicMock(return_value=mock_collection)

    # Call the method
    result = await service.add_proposal_embedding(
        proposal_id=proposal_id,
        text_content=text_content,
        embedding=embedding,
        metadata=metadata
    )
    
    # Assertions
    expected_chroma_id = f"proposal_{proposal_id}"
    assert result == expected_chroma_id
    
    # Verify ChromaDB interactions
    service._get_or_create_collection.assert_called_once_with(PROPOSALS_COLLECTION_NAME)
    
    # Verify upsert call
    mock_collection.upsert.assert_called_once()
    call_args = mock_collection.upsert.call_args[1]
    
    assert call_args["ids"] == [expected_chroma_id]
    assert call_args["embeddings"] == [embedding]
    assert call_args["documents"] == [text_content]
    
    # Verify metadata
    actual_metadata = call_args["metadatas"][0]
    assert actual_metadata["proposal_id"] == str(proposal_id)
    for key, value in metadata.items():
        assert actual_metadata[key] == value

@pytest.mark.asyncio
async def test_add_proposal_embedding_null_client(vector_db_service_with_mocked_client):
    """Test handling when client is not initialized"""
    service, _, _ = vector_db_service_with_mocked_client
    service.client = None
    
    result = await service.add_proposal_embedding(
        proposal_id=123,
        text_content="Test",
        embedding=[0.1, 0.2],
        metadata={}
    )
    
    assert result is None

@pytest.mark.asyncio
async def test_add_proposal_embedding_null_embedding(vector_db_service_with_mocked_client):
    """Test handling when embedding is None"""
    service, _, mock_collection = vector_db_service_with_mocked_client
    
    result = await service.add_proposal_embedding(
        proposal_id=123,
        text_content="Test",
        embedding=None,
        metadata={}
    )
    
    assert result is None
    mock_collection.upsert.assert_not_called()

@pytest.mark.asyncio
async def test_search_proposal_embeddings(vector_db_service_with_mocked_client):
    """Test searching proposal embeddings"""
    service, _, mock_collection = vector_db_service_with_mocked_client
    
    # Mock query results
    mock_results = {
        'ids': [['proposal_123', 'proposal_456']],
        'distances': [[0.1, 0.2]],
        'metadatas': [[
            {"proposal_id": "123", "status": "open"},
            {"proposal_id": "456", "status": "closed"}
        ]],
        'documents': [["Test 1", "Test 2"]]
    }
    mock_collection.query.return_value = mock_results
    service._get_or_create_collection = MagicMock(return_value=mock_collection)
    
    # Call the method
    query_embedding = [0.1, 0.2, 0.3]
    results = await service.search_proposal_embeddings(
        query_embedding=query_embedding,
        top_n=5,
        filter_proposal_ids=[123, 789]
    )
    
    # Assertions
    assert len(results) == 2
    
    # Verify first result
    assert results[0]["id"] == "proposal_123"
    assert results[0]["distance"] == 0.1
    assert results[0]["metadata"]["proposal_id"] == "123"
    assert results[0]["metadata"]["status"] == "open"
    assert results[0]["document_content"] == "Test 1"
    
    # Verify query call
    service._get_or_create_collection.assert_called_once_with(PROPOSALS_COLLECTION_NAME)
    mock_collection.query.assert_called_once()
    call_args = mock_collection.query.call_args[1]
    
    assert call_args["query_embeddings"] == [query_embedding]
    assert call_args["n_results"] == 5
    
    # Verify filter was correctly built
    where_filter = call_args["where"]
    assert where_filter == {"proposal_id": {"$in": ["123", "789"]}}

@pytest.mark.asyncio
async def test_search_proposal_embeddings_null_client(vector_db_service_with_mocked_client):
    """Test handling when client is not initialized during search"""
    service, _, _ = vector_db_service_with_mocked_client
    service.client = None
    
    result = await service.search_proposal_embeddings(
        query_embedding=[0.1, 0.2]
    )
    
    assert result is None

@pytest.mark.asyncio
async def test_search_proposal_embeddings_no_results(vector_db_service_with_mocked_client):
    """Test handling when search returns no results"""
    service, _, mock_collection = vector_db_service_with_mocked_client
    
    # Mock empty query results
    mock_collection.query.return_value = {
        'ids': [[]],
        'distances': [[]],
        'metadatas': [[]],
        'documents': [[]]
    }
    service._get_or_create_collection = MagicMock(return_value=mock_collection)
    
    results = await service.search_proposal_embeddings(
        query_embedding=[0.1, 0.2, 0.3]
    )
    
    assert len(results) == 0 