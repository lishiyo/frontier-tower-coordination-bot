import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.vector_db_service import VectorDBService, CHROMA_DATA_PATH, DEFAULT_COLLECTION_NAME

# Mock chromadb parts
@pytest.fixture
def mock_chroma_client_and_collection():
    mock_collection = MagicMock()
    mock_collection.add = MagicMock()
    mock_collection.query = MagicMock()

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