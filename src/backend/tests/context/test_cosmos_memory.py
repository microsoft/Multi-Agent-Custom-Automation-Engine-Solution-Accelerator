# src/backend/tests/context/test_cosmos_memory.py
# Drop-in test that self-stubs all external imports used by cosmos_memory_kernel
# so we don't need to modify the repo structure or CI env.

import sys
import types
import pytest
from unittest.mock import AsyncMock

# ----------------- Preload stub modules so the SUT can import cleanly -----------------

# 1) helpers.azure_credential_utils.get_azure_credential
helpers_mod = types.ModuleType("helpers")
helpers_cred_mod = types.ModuleType("helpers.azure_credential_utils")
def _fake_get_azure_credential(*_a, **_k):
    return object()
helpers_cred_mod.get_azure_credential = _fake_get_azure_credential
helpers_mod.azure_credential_utils = helpers_cred_mod
sys.modules.setdefault("helpers", helpers_mod)
sys.modules.setdefault("helpers.azure_credential_utils", helpers_cred_mod)

# 2) app_config.config (the SUT does: from app_config import config)
app_config_mod = types.ModuleType("app_config")
app_config_mod.config = types.SimpleNamespace(
    COSMOSDB_CONTAINER="mock-container",
    COSMOSDB_ENDPOINT="https://mock-endpoint",
    COSMOSDB_DATABASE="mock-database",
)
sys.modules.setdefault("app_config", app_config_mod)

# 3) models.messages_kernel (the SUT does: from models.messages_kernel import ...)
models_mod = types.ModuleType("models")
models_messages_mod = types.ModuleType("models.messages_kernel")

# Minimal stand-ins so type hints/imports succeed (not used in this test path)
class _Base: ...
class BaseDataModel(_Base): ...
class Plan(_Base): ...
class Session(_Base): ...
class Step(_Base): ...
class AgentMessage(_Base): ...

models_messages_mod.BaseDataModel = BaseDataModel
models_messages_mod.Plan = Plan
models_messages_mod.Session = Session
models_messages_mod.Step = Step
models_messages_mod.AgentMessage = AgentMessage
models_mod.messages_kernel = models_messages_mod
sys.modules.setdefault("models", models_mod)
sys.modules.setdefault("models.messages_kernel", models_messages_mod)

# 4) azure.cosmos.partition_key.PartitionKey (provide if sdk isn't installed)
try:
    from azure.cosmos.partition_key import PartitionKey  # type: ignore
except Exception:  # pragma: no cover
    azure_mod = sys.modules.setdefault("azure", types.ModuleType("azure"))
    azure_cosmos_mod = sys.modules.setdefault("azure.cosmos", types.ModuleType("azure.cosmos"))
    azure_cosmos_pk_mod = types.ModuleType("azure.cosmos.partition_key")
    class PartitionKey:  # minimal shim
        def __init__(self, path: str): self.path = path
    azure_cosmos_pk_mod.PartitionKey = PartitionKey
    sys.modules.setdefault("azure.cosmos.partition_key", azure_cosmos_pk_mod)

# 5) azure.cosmos.aio.CosmosClient (we’ll patch it in a fixture, but ensure import exists)
try:
    from azure.cosmos.aio import CosmosClient  # type: ignore
except Exception:  # pragma: no cover
    azure_cosmos_aio_mod = types.ModuleType("azure.cosmos.aio")
    class CosmosClient:  # placeholder; we patch this class below
        def __init__(self, *a, **k): ...
        def get_database_client(self, *a, **k): ...
    azure_cosmos_aio_mod.CosmosClient = CosmosClient
    sys.modules.setdefault("azure.cosmos.aio", azure_cosmos_aio_mod)

# ----------------- Import the SUT (after stubs are in place) -----------------
try:
    # If you added an alias file src/backend/context/cosmos_memory.py, this will work:
    from src.backend.context.cosmos_memory import CosmosMemoryContext as CosmosBufferedChatCompletionContext
except Exception:
    # Fallback to the kernel module (your provided code)
    from src.backend.context.cosmos_memory_kernel import CosmosMemoryContext as CosmosBufferedChatCompletionContext  # type: ignore

# Import PartitionKey (either real or our shim) for assertions
try:
    from azure.cosmos.partition_key import PartitionKey  # type: ignore
except Exception:  # already defined above in shim
    pass

# ----------------- Fixtures -----------------

@pytest.fixture
def fake_cosmos_stack(monkeypatch):
    """
    Patch the *SUT's* CosmosClient symbol so initialize() uses our AsyncMocks:
      CosmosClient(...).get_database_client() -> mock_db
      mock_db.create_container_if_not_exists(...) -> mock_container
    """
    import sys

    mock_container = AsyncMock()
    mock_db = AsyncMock()
    mock_db.create_container_if_not_exists = AsyncMock(return_value=mock_container)

    def _fake_ctor(*_a, **_k):
        # mimic a client object with get_database_client returning our mock_db
        return types.SimpleNamespace(
            get_database_client=lambda *_a2, **_k2: mock_db
        )

    # Find the actual module where CosmosBufferedChatCompletionContext is defined
    sut_module_name = CosmosBufferedChatCompletionContext.__module__
    sut_module = sys.modules[sut_module_name]

    # Patch the symbol the SUT imported (its local binding), not the SDK module
    monkeypatch.setattr(sut_module, "CosmosClient", _fake_ctor, raising=False)

    return mock_db, mock_container

@pytest.fixture
def mock_env(monkeypatch):
    # Optional: not strictly needed because we stubbed app_config.config above,
    # but keeps parity with your previous env fixture.
    env_vars = {
        "COSMOSDB_ENDPOINT": "https://mock-endpoint",
        "COSMOSDB_KEY": "mock-key",
        "COSMOSDB_DATABASE": "mock-database",
        "COSMOSDB_CONTAINER": "mock-container",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)

# ----------------- Test -----------------

@pytest.mark.asyncio
async def test_initialize(fake_cosmos_stack, mock_env):
    mock_db, mock_container = fake_cosmos_stack

    ctx = CosmosBufferedChatCompletionContext(
        session_id="test_session",
        user_id="test_user",
    )
    await ctx.initialize()

    mock_db.create_container_if_not_exists.assert_called_once()
    # Strict arg check:
    args, kwargs = mock_db.create_container_if_not_exists.call_args
    assert kwargs.get("id") == "mock-container"
    pk = kwargs.get("partition_key")
    assert isinstance(pk, PartitionKey) and getattr(pk, "path", None) == "/session_id"

    assert ctx._container == mock_container
