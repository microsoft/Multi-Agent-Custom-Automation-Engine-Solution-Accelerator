import os
import unittest
from unittest.mock import MagicMock
from autogen_core.components.models import AzureOpenAIChatCompletionClient
from autogen_core.base import AgentId
from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext
from src.backend.agents.generic import get_generic_tools, dummy_function


# Set environment variables to mock Config dependencies before any import
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"


class TestGenericAgent(unittest.TestCase):
    def setUp(self):
        self.mock_model_client = MagicMock(spec=AzureOpenAIChatCompletionClient)
        self.mock_session_id = "test_session_id"
        self.mock_user_id = "test_user_id"
        self.mock_memory = MagicMock(spec=CosmosBufferedChatCompletionContext)
        self.mock_tools = get_generic_tools()
        self.mock_agent_id = MagicMock(spec=AgentId)


class TestDummyFunction(unittest.IsolatedAsyncioTestCase):
    async def test_dummy_function(self):
        result = await dummy_function()
        self.assertEqual(result, "This is a placeholder function")


if __name__ == "__main__":
    unittest.main()
