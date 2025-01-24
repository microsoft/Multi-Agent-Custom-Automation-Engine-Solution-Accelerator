import pytest
import os
from unittest.mock import patch, AsyncMock
from src.backend.utils import initialize_runtime_and_context, runtime_dict, rai_success
from uuid import uuid4

# Mock environment variables
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-cosmosdb.documents.azure.com:443/"
os.environ["COSMOSDB_KEY"] = "mock_key"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint.azure.com/"
os.environ["AZURE_OPENAI_API_VERSION"] = "2024-05-01-preview"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment"
os.environ["COSMOSDB_DATABASE"] = "mock_database"
os.environ["COSMOSDB_CONTAINER"] = "mock_container"


@pytest.mark.asyncio
@patch("src.backend.utils.SingleThreadedAgentRuntime")
@patch("src.backend.utils.CosmosBufferedChatCompletionContext")
@patch("src.backend.utils.ToolAgent.register")
async def test_initialize_runtime_and_context_new_session(
    _mock_tool_agent_register, _mock_context, _mock_runtime
):
    session_id = None
    user_id = "test-user-id"

    _mock_runtime.return_value = AsyncMock()
    _mock_context.return_value = AsyncMock()

    runtime, context = await initialize_runtime_and_context(session_id, user_id)

    assert runtime is not None
    assert context is not None
    assert len(runtime_dict) > 0


@pytest.mark.asyncio
@patch("src.backend.utils.SingleThreadedAgentRuntime")
@patch("src.backend.utils.CosmosBufferedChatCompletionContext")
@patch("src.backend.utils.ToolAgent.register")
async def test_initialize_runtime_and_context_reuse_existing_session(
    _mock_tool_agent_register, _mock_context, _mock_runtime
):
    session_id = str(uuid4())
    user_id = "test-user-id"

    mock_runtime_instance = AsyncMock()
    mock_context_instance = AsyncMock()
    runtime_dict[session_id] = (mock_runtime_instance, mock_context_instance)

    runtime, context = await initialize_runtime_and_context(session_id, user_id)

    assert runtime == mock_runtime_instance
    assert context == mock_context_instance


@patch("src.backend.utils.requests.post")
@patch("src.backend.utils.DefaultAzureCredential")
def test_rai_success_true(mock_credential, mock_post):
    mock_credential.return_value.get_token.return_value.token = "mock_token"
    mock_post.return_value.json.return_value = {"choices": [{"message": {"content": "FALSE"}}]}
    mock_post.return_value.status_code = 200

    result = rai_success("This is a valid description.")
    assert result is True
