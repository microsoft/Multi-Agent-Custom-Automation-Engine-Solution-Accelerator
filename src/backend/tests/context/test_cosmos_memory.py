import os
import pytest
from unittest.mock import AsyncMock, patch
from azure.cosmos.partition_key import PartitionKey
from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext

# Set environment variables globally before importing modules
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"


async def async_iterable(mock_items):
    """Helper to create an async iterable."""
    for item in mock_items:
        yield item


@pytest.fixture(autouse=True)
def mock_env_variables(monkeypatch):
    """Mock all required environment variables."""
    env_vars = {
        "COSMOSDB_ENDPOINT": "https://mock-endpoint",
        "COSMOSDB_KEY": "mock-key",
        "COSMOSDB_DATABASE": "mock-database",
        "COSMOSDB_CONTAINER": "mock-container",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "mock-deployment-name",
        "AZURE_OPENAI_API_VERSION": "2023-01-01",
        "AZURE_OPENAI_ENDPOINT": "https://mock-openai-endpoint",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def mock_cosmos_client():
    """Fixture for mocking Cosmos DB client and container."""
    mock_client = AsyncMock()
    mock_container = AsyncMock()
    mock_client.create_container_if_not_exists.return_value = mock_container
    return mock_client, mock_container


@pytest.fixture
def mock_config(mock_cosmos_client):
    """Fixture to patch Config with mock Cosmos DB client."""
    mock_client, _ = mock_cosmos_client
    with patch(
        "src.backend.config.Config.GetCosmosDatabaseClient", return_value=mock_client
    ), patch("src.backend.config.Config.COSMOSDB_CONTAINER", "mock-container"):
        yield


@pytest.mark.asyncio
async def test_initialize(mock_config, mock_cosmos_client):
    """Test if the Cosmos DB container is initialized correctly."""
    mock_client, mock_container = mock_cosmos_client
    context = CosmosBufferedChatCompletionContext(
        session_id="test_session", user_id="test_user"
    )
    await context.initialize()
    mock_client.create_container_if_not_exists.assert_called_once_with(
        id="mock-container", partition_key=PartitionKey(path="/session_id")
    )
    assert context._container == mock_container
