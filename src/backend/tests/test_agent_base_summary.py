import asyncio
import asyncio
import os
import sys
from unittest.mock import MagicMock
import types

# Ensure modules under src/backend are importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Azure dependencies required by app_config
azure_module = types.ModuleType("azure")
sys.modules["azure"] = azure_module
sys.modules["azure.ai"] = types.ModuleType("azure.ai")
sys.modules["azure.ai.projects"] = types.ModuleType("azure.ai.projects")
projects_aio = types.ModuleType("azure.ai.projects.aio")
projects_aio.AIProjectClient = MagicMock()
sys.modules["azure.ai.projects.aio"] = projects_aio
cosmos_module = types.ModuleType("azure.cosmos")
sys.modules["azure.cosmos"] = cosmos_module
cosmos_aio = types.ModuleType("azure.cosmos.aio")
cosmos_aio.CosmosClient = MagicMock()
sys.modules["azure.cosmos.aio"] = cosmos_aio
partition_key_module = types.ModuleType("azure.cosmos.partition_key")
partition_key_module.PartitionKey = MagicMock()
sys.modules["azure.cosmos.partition_key"] = partition_key_module
azure_monitor_module = types.ModuleType("azure.monitor")
sys.modules["azure.monitor"] = azure_monitor_module
events_module = types.ModuleType("azure.monitor.events")
sys.modules["azure.monitor.events"] = events_module
events_ext_module = types.ModuleType("azure.monitor.events.extension")
events_ext_module.track_event = MagicMock()
sys.modules["azure.monitor.events.extension"] = events_ext_module
sys.modules["azure.monitor.opentelemetry"] = types.ModuleType("azure.monitor.opentelemetry")
identity_module = types.ModuleType("azure.identity")
identity_module.ManagedIdentityCredential = MagicMock()
identity_module.DefaultAzureCredential = MagicMock()
sys.modules["azure.identity"] = identity_module
identity_aio_module = types.ModuleType("azure.identity.aio")
identity_aio_module.ManagedIdentityCredential = MagicMock()
identity_aio_module.DefaultAzureCredential = MagicMock()
sys.modules["azure.identity.aio"] = identity_aio_module

# Mock semantic kernel dependencies
sys.modules["semantic_kernel"] = types.ModuleType("semantic_kernel")
kernel_module = types.ModuleType("semantic_kernel.kernel")
class Kernel:  # pragma: no cover - simple stub for testing
    pass
kernel_module.Kernel = Kernel
sys.modules["semantic_kernel.kernel"] = kernel_module
sys.modules["semantic_kernel.agents"] = types.ModuleType("semantic_kernel.agents")
sys.modules["semantic_kernel.agents.azure_ai"] = types.ModuleType("semantic_kernel.agents.azure_ai")
azure_ai_agent_module = types.ModuleType("semantic_kernel.agents.azure_ai.azure_ai_agent")
class AzureAIAgent:  # pragma: no cover - simple stub for testing
    def __init__(self, *args, **kwargs):
        pass
azure_ai_agent_module.AzureAIAgent = AzureAIAgent
sys.modules["semantic_kernel.agents.azure_ai.azure_ai_agent"] = azure_ai_agent_module
functions_module = types.ModuleType("semantic_kernel.functions")
class KernelFunction:  # pragma: no cover - simple stub for testing
    pass
functions_module.KernelFunction = KernelFunction
sys.modules["semantic_kernel.functions"] = functions_module
numpy_module = types.ModuleType("numpy")
class ndarray:  # pragma: no cover - stub
    pass
numpy_module.ndarray = ndarray
sys.modules["numpy"] = numpy_module
sys.modules["semantic_kernel.memory"] = types.ModuleType("semantic_kernel.memory")
memory_record_module = types.ModuleType("semantic_kernel.memory.memory_record")
class MemoryRecord:  # pragma: no cover - stub
    pass
memory_record_module.MemoryRecord = MemoryRecord
sys.modules["semantic_kernel.memory.memory_record"] = memory_record_module
memory_store_module = types.ModuleType("semantic_kernel.memory.memory_store_base")
class MemoryStoreBase:  # pragma: no cover - stub
    pass
memory_store_module.MemoryStoreBase = MemoryStoreBase
sys.modules["semantic_kernel.memory.memory_store_base"] = memory_store_module
contents_module = types.ModuleType("semantic_kernel.contents")
class ChatMessageContent:  # pragma: no cover - stub
    def __init__(self, *args, **kwargs):
        pass
class ChatHistory(list):
    pass
class AuthorRole:  # pragma: no cover - stub
    pass
contents_module.ChatMessageContent = ChatMessageContent
contents_module.ChatHistory = ChatHistory
contents_module.AuthorRole = AuthorRole
sys.modules["semantic_kernel.contents"] = contents_module
kernel_pydantic_module = types.ModuleType("semantic_kernel.kernel_pydantic")
class Field:  # pragma: no cover - stub
    def __init__(self, *args, **kwargs):
        pass
class KernelBaseModel:  # pragma: no cover - stub
    def __init__(self, **data):
        for k, v in data.items():
            setattr(self, k, v)

    def model_dump(self):
        return self.__dict__
kernel_pydantic_module.Field = Field
kernel_pydantic_module.KernelBaseModel = KernelBaseModel
sys.modules["semantic_kernel.kernel_pydantic"] = kernel_pydantic_module

# Provide required environment variables for AppConfig
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT_NAME", "test")
os.environ.setdefault("AZURE_OPENAI_API_VERSION", "2024-05-01")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test")
os.environ.setdefault("AZURE_AI_SUBSCRIPTION_ID", "sub")
os.environ.setdefault("AZURE_AI_RESOURCE_GROUP", "rg")
os.environ.setdefault("AZURE_AI_PROJECT_NAME", "proj")
os.environ.setdefault("AZURE_AI_AGENT_ENDPOINT", "https://agent")

from src.backend.kernel_agents.agent_base import BaseAgent
from src.backend.models.messages_kernel import AgentMessage


class StubMemoryStore:
    def __init__(self):
        self.items = []

    async def add_item(self, item):
        self.items.append(item)


class DummyAgent(BaseAgent):
    def __init__(self, memory_store, summary_after_n_turns=4):
        # Bypass parent initialization for testing summarization helpers
        self._agent_name = "dummy"
        self._session_id = "session"
        self._user_id = "user"
        self._memory_store = memory_store
        self._tools = []
        self._system_message = "system"
        self._chat_history = [{"role": "system", "content": self._system_message}]
        self._summary_after_n_turns = summary_after_n_turns
        self.name = self._agent_name

    @classmethod
    async def create(cls, **kwargs) -> "BaseAgent":
        raise NotImplementedError


def test_chat_history_summarization_and_truncation():
    store = StubMemoryStore()
    agent = DummyAgent(store, summary_after_n_turns=4)

    async def run():
        for i in range(6):
            await agent._add_message_to_history("user", f"message {i}")

    asyncio.run(run())

    # system message + summary + last 4 messages
    assert len(agent._chat_history) == 6
    summary_entry = agent._chat_history[1]
    assert summary_entry["role"] == "system"
    assert "message 0" in summary_entry["content"]
    assert "message 1" in summary_entry["content"]
    assert agent._chat_history[-1]["content"] == "message 5"

    assert len(store.items) >= 1
    assert store.items[-1].content == summary_entry["content"]
