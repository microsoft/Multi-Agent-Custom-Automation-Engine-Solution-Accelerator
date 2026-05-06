"""Unit tests for agents.agent_template (AgentTemplate — GA agent_framework 1.2.2).

Ported from src/tests/backend/v4/magentic_agents/test_foundry_agent.py.
Key changes:
  - FoundryAgentTemplate → AgentTemplate
  - agent.search attribute → agent.search_config
  - _azure_server_agent_id removed (no server-side agent in GA path)
  - _collect_tools() removed (inlined in AgentTemplate._open_mcp_path)
  - agent_framework mocks reflect new GA type names
"""

import logging
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Module stubs (avoid Azure SDK / Cosmos DB at import time)
# pytest's pythonpath=["src"] means modules are imported as backend.xxx
# The AgentTemplate code uses short absolute imports (from agents.x import ...);
# those are resolved via sys.modules when the parent backend.* module is loaded.
# ---------------------------------------------------------------------------

# --- agent_framework
_mock_agent_fw = Mock()
sys.modules["agent_framework"] = _mock_agent_fw

# --- agent_framework_foundry
_mock_af_foundry = Mock()
sys.modules["agent_framework_foundry"] = _mock_af_foundry

# --- azure.identity.aio  (keep azure hierarchy intact)
sys.modules.setdefault("azure", Mock())
sys.modules.setdefault("azure.identity", Mock())
sys.modules.setdefault("azure.identity.aio", Mock())

# --- common.*
sys.modules.setdefault("common", Mock())
sys.modules.setdefault("common.config", Mock())
sys.modules.setdefault("common.config.app_config", Mock())
sys.modules.setdefault("common.database", Mock())
sys.modules.setdefault("common.database.database_base", Mock())
sys.modules.setdefault("common.models", Mock())
sys.modules.setdefault("common.models.messages", Mock())
sys.modules.setdefault("common.utils", Mock())
sys.modules.setdefault("common.utils.agent_utils", Mock())

# --- config.*  (short-path as used by agent_template.py)
_mock_config_agent_registry = Mock()
_mock_agent_registry = Mock()
_mock_config_agent_registry.agent_registry = _mock_agent_registry
sys.modules.setdefault("config", Mock())
sys.modules["config.agent_registry"] = _mock_config_agent_registry

_mock_mcp_config_cls = Mock()
_mock_search_config_cls = Mock()
_mock_config_mcp_config = Mock()
_mock_config_mcp_config.MCPConfig = _mock_mcp_config_cls
_mock_config_mcp_config.SearchConfig = _mock_search_config_cls
sys.modules["config.mcp_config"] = _mock_config_mcp_config

# Now import the module under test (full backend.* path as per project convention)
from backend.agents.agent_template import AgentTemplate


# ---------------------------------------------------------------------------
# Helpers — mock fixtures with proper shape
# ---------------------------------------------------------------------------


def _make_mcp_config(**kw):
    m = Mock()
    m.url = kw.get("url", "https://test-mcp.example.com")
    m.name = kw.get("name", "TestMCP")
    m.description = kw.get("description", "Test MCP Server")
    m.tenant_id = kw.get("tenant_id", "tenant-123")
    m.client_id = kw.get("client_id", "client-456")
    return m


def _make_search_config(**kw):
    m = Mock()
    m.connection_name = kw.get("connection_name", "TestConnection")
    m.endpoint = kw.get("endpoint", "https://test-search.example.com")
    m.index_name = kw.get("index_name", "test-index")
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_kwargs() -> dict:
    return dict(
        agent_name="TestAgent",
        agent_description="Test Description",
        agent_instructions="Test Instructions",
        use_reasoning=False,
        model_deployment_name="test-model",
        project_endpoint="https://test.project.azure.com/",
    )


@pytest.fixture
def mcp_config():
    return _make_mcp_config()


@pytest.fixture
def search_config():
    return _make_search_config()


@pytest.fixture
def search_config_no_index():
    return _make_search_config(index_name=None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAgentTemplateInit:
    """Tests for AgentTemplate.__init__."""

    def test_minimal_params(self, basic_kwargs):
        agent = AgentTemplate(**basic_kwargs)

        assert agent.agent_name == "TestAgent"
        assert agent.agent_description == "Test Description"
        assert agent.agent_instructions == "Test Instructions"
        assert agent.use_reasoning is False
        assert agent.model_deployment_name == "test-model"
        assert agent.project_endpoint == "https://test.project.azure.com/"
        assert agent.enable_code_interpreter is False
        assert agent.mcp_cfg is None
        assert agent.search_config is None
        assert agent._agent is None
        assert agent._use_azure_search is False
        assert isinstance(agent.logger, logging.Logger)

    def test_all_params(self, basic_kwargs, mcp_config, search_config):
        # basic_kwargs includes use_reasoning=False; override it here
        kw = {k: v for k, v in basic_kwargs.items() if k != "use_reasoning"}
        agent = AgentTemplate(
            **kw,
            use_reasoning=True,
            enable_code_interpreter=True,
            mcp_config=mcp_config,
            search_config=search_config,
        )

        assert agent.use_reasoning is True
        assert agent.enable_code_interpreter is True
        assert agent.mcp_cfg is mcp_config
        assert agent.search_config is search_config
        assert agent._use_azure_search is True  # search_config has index_name

    def test_search_config_no_index_does_not_trigger_azure_search(
        self, basic_kwargs, search_config_no_index
    ):
        agent = AgentTemplate(**basic_kwargs, search_config=search_config_no_index)
        assert agent._use_azure_search is False


class TestIsAzureSearchRequested:
    """Tests for AgentTemplate._is_azure_search_requested."""

    def test_no_search_config(self, basic_kwargs):
        agent = AgentTemplate(**basic_kwargs)
        assert agent._is_azure_search_requested() is False

    def test_with_valid_index(self, basic_kwargs, search_config):
        agent = AgentTemplate(**basic_kwargs, search_config=search_config)
        assert agent._is_azure_search_requested() is True

    def test_no_index_name(self, basic_kwargs, search_config_no_index):
        agent = AgentTemplate(**basic_kwargs, search_config=search_config_no_index)
        assert agent._is_azure_search_requested() is False


class TestAgentTemplateOpen:
    """Tests for AgentTemplate.open() (MCP path)."""

    @pytest.mark.asyncio
    async def test_open_mcp_path_creates_agent(self, basic_kwargs):
        """open() on MCP path initialises FoundryChatClient + Agent and registers."""
        mock_inner = Mock()
        mock_agent_cm = AsyncMock()
        mock_agent_cm.__aenter__ = AsyncMock(return_value=mock_inner)
        mock_agent_cm.__aexit__ = AsyncMock(return_value=False)

        mock_credential = AsyncMock()
        mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
        mock_credential.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=mock_agent_cm),
            patch("backend.agents.agent_template.agent_registry") as mock_reg,
        ):
            agent = AgentTemplate(**basic_kwargs)
            result = await agent.open()

        assert result is agent
        assert agent._agent is not None
        mock_reg.register_agent.assert_called_once_with(agent)

    @pytest.mark.asyncio
    async def test_open_azure_search_path(self, basic_kwargs, search_config):
        """open() on Azure Search path calls FoundryAgent."""
        mock_fa = AsyncMock()
        mock_fa.__aenter__ = AsyncMock(return_value=Mock())
        mock_fa.__aexit__ = AsyncMock(return_value=False)

        mock_credential = AsyncMock()
        mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
        mock_credential.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
            patch("backend.agents.agent_template.FoundryAgent", return_value=mock_fa) as mock_fa_cls,
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs, search_config=search_config)
            await agent.open()

        mock_fa_cls.assert_called_once()
        kw = mock_fa_cls.call_args[1]
        assert kw["agent_name"] == "TestAgent"
        assert kw["project_endpoint"] == "https://test.project.azure.com/"

    @pytest.mark.asyncio
    async def test_open_is_idempotent(self, basic_kwargs):
        """Calling open() twice does not re-initialise the agent."""
        mock_agent_cm = AsyncMock()
        mock_agent_cm.__aenter__ = AsyncMock(return_value=Mock())
        mock_agent_cm.__aexit__ = AsyncMock(return_value=False)

        mock_credential = AsyncMock()
        mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
        mock_credential.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=mock_agent_cm),
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs)
            r1 = await agent.open()
            r2 = await agent.open()

        assert r1 is r2

    @pytest.mark.asyncio
    async def test_open_with_mcp_tool(self, basic_kwargs, mcp_config):
        """open() with mcp_config attaches MCPStreamableHTTPTool."""
        mock_mcp_tool = AsyncMock()
        mock_mcp_tool.__aenter__ = AsyncMock(return_value=mock_mcp_tool)
        mock_mcp_tool.__aexit__ = AsyncMock(return_value=False)

        mock_agent_cm = AsyncMock()
        mock_agent_cm.__aenter__ = AsyncMock(return_value=Mock())
        mock_agent_cm.__aexit__ = AsyncMock(return_value=False)

        mock_credential = AsyncMock()
        mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
        mock_credential.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
            patch("backend.agents.agent_template.MCPStreamableHTTPTool", return_value=mock_mcp_tool) as mock_mcp_cls,
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=mock_agent_cm) as mock_agent_cls,
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs, mcp_config=mcp_config)
            await agent.open()

        mock_mcp_cls.assert_called_once_with(
            name=mcp_config.name,
            description=mcp_config.description,
            url=mcp_config.url,
        )
        kw = mock_agent_cls.call_args[1]
        assert mock_mcp_tool in kw["tools"]


class TestAgentTemplateClose:
    """Tests for AgentTemplate.close()."""

    @pytest.mark.asyncio
    async def test_close_clears_state(self, basic_kwargs):
        mock_agent_cm = AsyncMock()
        mock_agent_cm.__aenter__ = AsyncMock(return_value=Mock())
        mock_agent_cm.__aexit__ = AsyncMock(return_value=False)

        mock_credential = AsyncMock()
        mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
        mock_credential.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=mock_agent_cm),
            patch("backend.agents.agent_template.agent_registry") as mock_reg,
        ):
            agent = AgentTemplate(**basic_kwargs)
            await agent.open()
            await agent.close()

        assert agent._agent is None
        assert agent._stack is None
        assert agent._credential is None
        mock_reg.unregister_agent.assert_called_once_with(agent)

    @pytest.mark.asyncio
    async def test_close_safe_when_not_opened(self, basic_kwargs):
        agent = AgentTemplate(**basic_kwargs)
        await agent.close()  # should not raise

    @pytest.mark.asyncio
    async def test_context_manager(self, basic_kwargs):
        mock_agent_cm = AsyncMock()
        mock_agent_cm.__aenter__ = AsyncMock(return_value=Mock())
        mock_agent_cm.__aexit__ = AsyncMock(return_value=False)

        mock_credential = AsyncMock()
        mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
        mock_credential.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=mock_agent_cm),
            patch("backend.agents.agent_template.agent_registry"),
        ):
            async with AgentTemplate(**basic_kwargs) as agent:
                assert agent._agent is not None
            assert agent._agent is None


class TestAgentTemplateInvoke:
    """Tests for AgentTemplate.invoke()."""

    @pytest.mark.asyncio
    async def test_invoke_before_open_raises(self, basic_kwargs):
        agent = AgentTemplate(**basic_kwargs)
        with pytest.raises(RuntimeError, match="not initialized"):
            async for _ in agent.invoke("hello"):
                pass

    @pytest.mark.asyncio
    async def test_invoke_streams_updates(self, basic_kwargs):
        """invoke() yields each update from the inner agent."""
        update1 = Mock()
        update2 = Mock()

        async def _fake_run(message, *, stream=False):
            for u in [update1, update2]:
                yield u

        mock_inner = Mock()
        mock_inner.run = _fake_run

        mock_agent_cm = AsyncMock()
        mock_agent_cm.__aenter__ = AsyncMock(return_value=mock_inner)
        mock_agent_cm.__aexit__ = AsyncMock(return_value=False)

        mock_credential = AsyncMock()
        mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
        mock_credential.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=mock_credential),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=mock_agent_cm),
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs)
            await agent.open()

        collected = []
        async for update in agent.invoke("hi"):
            collected.append(update)

        assert collected == [update1, update2]

