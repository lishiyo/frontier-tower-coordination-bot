import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage, ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.create_embedding_response import CreateEmbeddingResponse, Usage
from openai.types.embedding import Embedding
from datetime import datetime, timezone

from app.services.llm_service import LLMService
from app.config import ConfigService # To mock its methods

# Test API Key
TEST_OPENAI_API_KEY = "sk-testkey12345"

@pytest.fixture
def mock_config_service_with_key():
    with patch('app.services.llm_service.ConfigService.get_openai_api_key', return_value=TEST_OPENAI_API_KEY) as mock_config:
        yield mock_config

@pytest.fixture
def mock_config_service_no_key():
    with patch('app.services.llm_service.ConfigService.get_openai_api_key', return_value=None) as mock_config:
        yield mock_config

@pytest.fixture
def llm_service_with_mocked_config(mock_config_service_with_key):
    # This fixture will use the ConfigService mock that returns an API key
    return LLMService()

# --- Test __init__ ---
def test_llm_service_init_success(mock_config_service_with_key):
    service = LLMService()
    assert service.client is not None
    assert isinstance(service.client, AsyncOpenAI)
    mock_config_service_with_key.assert_called_once()

def test_llm_service_init_no_api_key(mock_config_service_no_key, caplog):
    # LLMService constructor catches ValueError and logs an error.
    # It doesn't re-raise, so we check for log and self.client being None.
    service = LLMService()
    assert service.client is None
    assert "OpenAI API key is not configured" in caplog.text or "OpenAI API key is missing" in caplog.text
    mock_config_service_no_key.assert_called_once()

# --- Mocks for OpenAI client methods ---
@pytest.fixture
def mock_openai_client():
    client = AsyncMock(spec=AsyncOpenAI)
    client.chat = AsyncMock()
    client.chat.completions = AsyncMock()
    client.embeddings = AsyncMock()
    return client

@pytest.fixture
def llm_service_with_mock_client(mock_config_service_with_key, mock_openai_client):
    # Create LLMService instance, then replace its client with our mock
    service = LLMService() 
    service.client = mock_openai_client # Replace the actual client with the mock
    return service

# --- Test parse_natural_language_duration ---
@pytest.mark.asyncio
async def test_parse_duration_client_not_initialized(mock_config_service_no_key, caplog):
    service = LLMService() # Initializes with no client due to no API key
    assert service.client is None
    result = await service.parse_natural_language_duration("tomorrow")
    assert result is None
    assert "LLMService client not initialized. Cannot parse duration." in caplog.text

@pytest.mark.asyncio
async def test_parse_duration_success(llm_service_with_mock_client: LLMService, mock_openai_client):
    text_input = "next Friday at 2 PM"
    llm_response_date_str = "2024-07-26 14:00:00 UTC" # Example fixed date
    expected_datetime = datetime(2024, 7, 26, 14, 0, 0, tzinfo=timezone.utc)

    # Mock the get_completion method directly as it's called by parse_duration
    llm_service_with_mock_client.get_completion = AsyncMock(return_value=llm_response_date_str)
    
    with patch('app.services.llm_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 7, 19, 10, 0, 0, tzinfo=timezone.utc) # Mock current time
        mock_datetime.strptime = datetime.strptime # Use real strptime

        result = await llm_service_with_mock_client.parse_natural_language_duration(text_input)

    assert result == expected_datetime
    llm_service_with_mock_client.get_completion.assert_called_once()

@pytest.mark.asyncio
async def test_parse_duration_llm_error_cannot_parse(llm_service_with_mock_client: LLMService, caplog):
    llm_service_with_mock_client.get_completion = AsyncMock(return_value="ERROR_CANNOT_PARSE")
    result = await llm_service_with_mock_client.parse_natural_language_duration("gibberish")
    assert result is None
    assert "LLM could not parse duration string" in caplog.text

@pytest.mark.asyncio
async def test_parse_duration_llm_malformed_date(llm_service_with_mock_client: LLMService, caplog):
    llm_service_with_mock_client.get_completion = AsyncMock(return_value="2023-13-01 10:00:00 UTC") # Invalid month
    result = await llm_service_with_mock_client.parse_natural_language_duration("a date")
    assert result is None
    assert "Failed to parse LLM response" in caplog.text

@pytest.mark.asyncio
async def test_parse_duration_get_completion_fails(llm_service_with_mock_client: LLMService, caplog):
    llm_service_with_mock_client.get_completion = AsyncMock(return_value=None)
    result = await llm_service_with_mock_client.parse_natural_language_duration("some input")
    assert result is None
    assert "LLM could not parse duration string" in caplog.text # Because None is treated like ERROR_CANNOT_PARSE

@pytest.mark.asyncio
async def test_parse_duration_get_completion_exception(llm_service_with_mock_client: LLMService, caplog):
    llm_service_with_mock_client.get_completion = AsyncMock(side_effect=Exception("API Error"))
    result = await llm_service_with_mock_client.parse_natural_language_duration("some input")
    assert result is None
    assert "Unexpected error during natural language duration parsing" in caplog.text

# --- Test generate_embedding ---
@pytest.mark.asyncio
async def test_generate_embedding_client_not_initialized(mock_config_service_no_key, caplog):
    service = LLMService()
    result = await service.generate_embedding("text")
    assert result is None
    assert "LLMService client not initialized. Cannot generate embedding." in caplog.text

@pytest.mark.asyncio
async def test_generate_embedding_success(llm_service_with_mock_client: LLMService, mock_openai_client):
    text_input = "embed this"
    expected_embedding = [0.1, 0.2, 0.3]
    
    # Mock the structure of OpenAI's embedding response
    mock_embedding_obj = Embedding(embedding=expected_embedding, index=0, object="embedding")
    mock_create_embedding_response = CreateEmbeddingResponse(
        data=[mock_embedding_obj],
        model="text-embedding-3-small",
        object="list",
        usage=Usage(prompt_tokens=0, total_tokens=0) # Usage can be minimal for test
    )
    mock_openai_client.embeddings.create = AsyncMock(return_value=mock_create_embedding_response)
    
    result = await llm_service_with_mock_client.generate_embedding(text_input)
    assert result == expected_embedding
    mock_openai_client.embeddings.create.assert_called_once_with(input=[text_input.replace('\n', ' ')], model="text-embedding-3-small")

@pytest.mark.asyncio
async def test_generate_embedding_api_error(llm_service_with_mock_client: LLMService, mock_openai_client, caplog):
    mock_openai_client.embeddings.create = AsyncMock(side_effect=Exception("API Down"))
    result = await llm_service_with_mock_client.generate_embedding("text")
    assert result is None
    assert "Error generating embedding" in caplog.text

# --- Test get_completion (method used by others, but also test directly) ---
@pytest.mark.asyncio
async def test_get_completion_client_not_initialized(mock_config_service_no_key, caplog):
    service = LLMService()
    result = await service.get_completion("prompt")
    assert result is None
    assert "LLMService client not initialized. Cannot get completion." in caplog.text

@pytest.mark.asyncio
async def test_get_completion_success(llm_service_with_mock_client: LLMService, mock_openai_client):
    prompt_input = "Hello AI"
    expected_response_text = "Hello human!"

    mock_choice = Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content=expected_response_text, role="assistant"))
    mock_chat_completion = ChatCompletion(
        id="chatcmpl-test", created=12345, model="gpt-4o", object="chat.completion", choices=[mock_choice]
    )
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)

    result = await llm_service_with_mock_client.get_completion(prompt_input)
    assert result == expected_response_text.strip()
    mock_openai_client.chat.completions.create.assert_called_once()
    call_args = mock_openai_client.chat.completions.create.call_args
    assert call_args[1]['model'] == "gpt-4o"
    assert call_args[1]['messages'][-1]['content'] == prompt_input

@pytest.mark.asyncio
async def test_get_completion_empty_content(llm_service_with_mock_client: LLMService, mock_openai_client, caplog):
    mock_choice = Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content=None, role="assistant"))
    mock_chat_completion = ChatCompletion(id="c", created=1, model="m", object="chat.completion", choices=[mock_choice])
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)
    result = await llm_service_with_mock_client.get_completion("prompt")
    assert result is None # Stripped None is None
    # No specific error log for this case by default in current code, but good to test behavior.

@pytest.mark.asyncio
async def test_get_completion_api_error(llm_service_with_mock_client: LLMService, mock_openai_client, caplog):
    mock_openai_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
    result = await llm_service_with_mock_client.get_completion("prompt")
    assert result is None
    assert "Error getting completion" in caplog.text

# --- Test cluster_and_summarize_texts ---
@pytest.mark.asyncio
async def test_cluster_summarize_client_not_initialized(mock_config_service_no_key, caplog):
    service = LLMService()
    result = await service.cluster_and_summarize_texts(["text1"])
    assert result is None
    assert "LLMService client not initialized. Cannot cluster and summarize texts." in caplog.text

@pytest.mark.asyncio
async def test_cluster_summarize_no_texts(llm_service_with_mock_client: LLMService, caplog):
    result = await llm_service_with_mock_client.cluster_and_summarize_texts([])
    assert result is None # Current code returns None
    assert "No texts provided to cluster_and_summarize_texts" in caplog.text

@pytest.mark.asyncio
async def test_cluster_summarize_success(llm_service_with_mock_client: LLMService):
    texts = ["Point A about topic X", "Point B about topic Y", "Another point A on X"]
    expected_summary = "Theme 1: Topic X...\nTheme 2: Topic Y..."
    
    # Mock get_completion as it's used internally
    llm_service_with_mock_client.get_completion = AsyncMock(return_value=expected_summary)

    result = await llm_service_with_mock_client.cluster_and_summarize_texts(texts)
    assert result == expected_summary
    llm_service_with_mock_client.get_completion.assert_called_once()
    # Can add assertion for the prompt if needed

@pytest.mark.asyncio
async def test_cluster_summarize_llm_returns_no_summary(llm_service_with_mock_client: LLMService, caplog):
    llm_service_with_mock_client.get_completion = AsyncMock(return_value=None) # LLM gives no output
    texts = ["text1"]
    result = await llm_service_with_mock_client.cluster_and_summarize_texts(texts)
    assert result == "No summary could be generated from the submissions." # Placeholder message
    assert "LLM returned no summary for clustering." in caplog.text

@pytest.mark.asyncio
async def test_cluster_summarize_exception(llm_service_with_mock_client: LLMService, caplog):
    llm_service_with_mock_client.get_completion = AsyncMock(side_effect=Exception("Clustering API Error"))
    texts = ["text1"]
    result = await llm_service_with_mock_client.cluster_and_summarize_texts(texts)
    assert result == "An error occurred while generating the summary." # Placeholder message
    assert "Unexpected error during text clustering and summarization" in caplog.text 