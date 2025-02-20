from unittest.mock import patch, MagicMock
import pytest
from src.backend.utils import (
    initialize_runtime_and_context,
    retrieve_all_agent_tools,
    rai_success,
    runtime_dict,
)
from autogen_core.application import SingleThreadedAgentRuntime
from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext


@pytest.fixture(scope="function", autouse=True)
def mock_telemetry():
    """Mock telemetry and threading-related components to prevent access violations."""
    with patch("opentelemetry.sdk.trace.export.BatchSpanProcessor", MagicMock()):
        yield


@patch("src.backend.utils.get_hr_tools", MagicMock(return_value=[]))
@patch("src.backend.utils.get_marketing_tools", MagicMock(return_value=[]))
@patch("src.backend.utils.get_procurement_tools", MagicMock(return_value=[]))
@patch("src.backend.utils.get_product_tools", MagicMock(return_value=[]))
@patch("src.backend.utils.get_tech_support_tools", MagicMock(return_value=[]))
def test_retrieve_all_agent_tools():
    """Test retrieval of all agent tools with mocked dependencies."""
    tools = retrieve_all_agent_tools()
    assert isinstance(tools, list)
    assert len(tools) == 0  # Mocked to return no tools


@pytest.mark.asyncio
@patch("src.backend.utils.Config.GetAzureOpenAIChatCompletionClient", MagicMock())
async def test_initialize_runtime_and_context():
    """Test initialization of runtime and context with mocked Azure client."""
    session_id = "test-session-id"
    user_id = "test-user-id"

    runtime, context = await initialize_runtime_and_context(session_id, user_id)

    # Validate runtime and context types
    assert isinstance(runtime, SingleThreadedAgentRuntime)
    assert isinstance(context, CosmosBufferedChatCompletionContext)

    # Validate caching
    assert session_id in runtime_dict
    assert runtime_dict[session_id] == (runtime, context)


@pytest.mark.asyncio
async def test_initialize_runtime_and_context_missing_user_id():
    """Test ValueError when user_id is missing."""
    with pytest.raises(ValueError, match="The 'user_id' parameter cannot be None"):
        await initialize_runtime_and_context(session_id="test-session-id", user_id=None)


@patch("src.backend.utils.requests.post")
@patch("src.backend.utils.DefaultAzureCredential")
def test_rai_success(mock_credential, mock_post):
    """Test successful RAI response with mocked requests and credentials."""
    mock_credential.return_value.get_token.return_value.token = "mock-token"
    mock_post.return_value.json.return_value = {
        "choices": [{"message": {"content": "FALSE"}}]
    }

    description = "Test RAI success"
    result = rai_success(description)
    assert result is True
    mock_post.assert_called_once()


@patch("src.backend.utils.requests.post")
@patch("src.backend.utils.DefaultAzureCredential")
def test_rai_success_invalid_response(mock_credential, mock_post):
    """Test RAI response with an invalid format."""
    mock_credential.return_value.get_token.return_value.token = "mock-token"
    mock_post.return_value.json.return_value = {"unexpected_key": "value"}

    description = "Test invalid response"
    result = rai_success(description)
    assert result is False
