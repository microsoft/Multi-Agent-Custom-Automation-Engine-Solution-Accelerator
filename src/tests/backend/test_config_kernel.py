"""Test cases for ProcurementTools class."""
import sys
import types
import os
from unittest.mock import MagicMock
from enum import Enum
import pytest

# ---------------------
# Step 1: Mocks
# ---------------------

#Mock app_config
mock_app_config = types.ModuleType("app_config")
mock_config = MagicMock()
mock_config.get_azure_credentials.return_value = "mock_credentials"
mock_config.get_cosmos_database_client.return_value = "mock_cosmos_client"
mock_config.create_kernel.return_value = "mock_kernel"
mock_config.get_ai_project_client.return_value = "mock_ai_project"
mock_app_config.config = mock_config
sys.modules["app_config"] = mock_app_config

#Mock semantic_kernel base and all submodules
sk_pkg = types.ModuleType("semantic_kernel")
sk_pkg.__path__ = []
sys.modules["semantic_kernel"] = sk_pkg

# semantic_kernel.functions
sk_funcs = types.ModuleType("semantic_kernel.functions")
def kernel_function(name=None, description=None):
    """A mock kernel function decorator."""
    class DummyKernelFunction:
        """A dummy kernel function class."""
        def __init__(self, description):
            self.description = description
    def decorator(func):
        setattr(func, "__kernel_name__", name or func.__name__)
        setattr(func, "__kernel_function__", DummyKernelFunction(description))
        return func
    return decorator
sk_funcs.kernel_function = kernel_function
sys.modules["semantic_kernel.functions"] = sk_funcs

# semantic_kernel.kernel
sk_kernel = types.ModuleType("semantic_kernel.kernel")
sk_kernel.Kernel = MagicMock(name="Kernel")
sys.modules["semantic_kernel.kernel"] = sk_kernel

# semantic_kernel.contents
sk_contents = types.ModuleType("semantic_kernel.contents")
sk_contents.ChatHistory = MagicMock(name="ChatHistory")
sys.modules["semantic_kernel.contents"] = sk_contents

# semantic_kernel.connectors fallback
sk_connectors = types.ModuleType("semantic_kernel.connectors")
sk_ai = types.ModuleType("semantic_kernel.connectors.ai")
sk_chat = types.ModuleType("semantic_kernel.connectors.ai.chat_completion_client")
sk_chat.ChatHistory = MagicMock(name="ChatHistory")
sys.modules["semantic_kernel.connectors"] = sk_connectors
sys.modules["semantic_kernel.connectors.ai"] = sk_ai
sys.modules["semantic_kernel.connectors.ai.chat_completion_client"] = sk_chat

#Mock semantic_kernel.agents.azure_ai.azure_ai_agent.AzureAIAgent
sk_agents = types.ModuleType("semantic_kernel.agents")
sk_azure_ai = types.ModuleType("semantic_kernel.agents.azure_ai")
sk_azure_ai_agent = types.ModuleType("semantic_kernel.agents.azure_ai.azure_ai_agent")
sk_azure_ai_agent.AzureAIAgent = MagicMock(name="AzureAIAgent")
sys.modules["semantic_kernel.agents"] = sk_agents
sys.modules["semantic_kernel.agents.azure_ai"] = sk_azure_ai
sys.modules["semantic_kernel.agents.azure_ai.azure_ai_agent"] = sk_azure_ai_agent

#Mock models.messages_kernel.AgentType
models_pkg = types.ModuleType("models")
msgs_mod = types.ModuleType("models.messages_kernel")

class AgentType(Enum):
    """Mock AgentType Enum."""
    HR = 'hr_agent'
    PROCUREMENT = 'procurement_agent'
    MARKETING = 'marketing_agent'
    PRODUCT = 'product_agent'
    TECH_SUPPORT = 'tech_support_agent'
msgs_mod.AgentType = AgentType
models_pkg.messages_kernel = msgs_mod
sys.modules['models'] = models_pkg
sys.modules['models.messages_kernel'] = msgs_mod

#Ensure src is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

#Import Config AFTER all mocks
from backend.config_kernel import Config

# ---------------------
# Step 2: Fixtures
# ---------------------
@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set environment variables for the tests."""
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-11-20")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example-openai-endpoint.com")
    monkeypatch.setenv("AZURE_AI_SUBSCRIPTION_ID", "fake-subscription-id")
    monkeypatch.setenv("AZURE_AI_RESOURCE_GROUP", "fake-resource-group")
    monkeypatch.setenv("AZURE_AI_PROJECT_NAME", "fake-project-name")
    monkeypatch.setenv("AZURE_AI_AGENT_PROJECT_CONNECTION_STRING", "fake-connection-string")
    monkeypatch.setenv("AZURE_TENANT_ID", "fake-tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "fake-client-id")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "fake-client-secret")
    monkeypatch.setenv("COSMOSDB_ENDPOINT", "https://fake-cosmos-endpoint.com")
    monkeypatch.setenv("COSMOSDB_DATABASE", "fake-database")
    monkeypatch.setenv("COSMOSDB_CONTAINER", "fake-container")
    monkeypatch.setenv("AZURE_OPENAI_SCOPE", "https://customscope.com/.default")
    monkeypatch.setenv("FRONTEND_SITE_NAME", "http://localhost:3000")

# ---------------------
# Step 3: Tests
# ---------------------
def test_get_azure_credentials():
    """Test the GetAzureCredentials method."""
    result = Config.GetAzureCredentials()
    assert result == "mock_credentials"
    mock_config.get_azure_credentials.assert_called_once()

def test_get_cosmos_database_client():
    """Test the GetCosmosDatabaseClient method."""
    result = Config.GetCosmosDatabaseClient()
    assert result == "mock_cosmos_client"
    mock_config.get_cosmos_database_client.assert_called_once()

def test_create_kernel():
    """Test the CreateKernel method."""
    result = Config.CreateKernel()
    assert result == "mock_kernel"
    mock_config.create_kernel.assert_called_once()

def test_get_ai_project_client():
    """Test the GetAIProjectClient method."""
    result = Config.GetAIProjectClient()
    assert result == "mock_ai_project"
    mock_config.get_ai_project_client.assert_called_once()
