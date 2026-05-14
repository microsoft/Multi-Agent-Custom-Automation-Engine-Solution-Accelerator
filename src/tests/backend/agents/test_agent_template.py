"""Unit tests for agents.agent_template — MAF 1.0 section 6 pattern.

Covers:
  - Get path: list_agents() returns matching agent → create_agent() NOT called
  - Create path: list_agents() returns nothing → create_agent() IS called
  - Toolbox: created with correct tools per config flags
  - No toolbox when no tools configured
  - FoundryAgent is never referenced (import removed from module)
  - open() is idempotent
  - close() clears all state
  - Context manager support
  - invoke() streaming
"""

import logging
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Module stubs — prevent Azure SDK / Cosmos DB imports at collection time
# ---------------------------------------------------------------------------

_mock_agent_fw = Mock()
sys.modules["agent_framework"] = _mock_agent_fw

_mock_af_foundry = Mock()
sys.modules["agent_framework_foundry"] = _mock_af_foundry

# azure hierarchy
sys.modules.setdefault("azure", Mock())
sys.modules.setdefault("azure.identity", Mock())
sys.modules.setdefault("azure.identity.aio", Mock())
sys.modules.setdefault("azure.core", Mock())
sys.modules.setdefault("azure.core.exceptions", Mock(
    HttpResponseError=type('HttpResponseError', (Exception,), {}),
    ResourceNotFoundError=type('ResourceNotFoundError', (Exception,), {}),
))
sys.modules.setdefault("azure.ai", Mock())
sys.modules.setdefault("azure.ai.projects", Mock())
sys.modules.setdefault("azure.ai.projects.aio", Mock())
_mock_projects_models = Mock()
sys.modules["azure.ai.projects.models"] = _mock_projects_models

# common.*
sys.modules.setdefault("common", Mock())
sys.modules.setdefault("common.config", Mock())
sys.modules.setdefault("common.config.app_config", Mock())
sys.modules.setdefault("common.database", Mock())
sys.modules.setdefault("common.database.database_base", Mock())
sys.modules.setdefault("common.models", Mock())
sys.modules.setdefault("common.models.messages", Mock())
sys.modules.setdefault("common.utils", Mock())
sys.modules.setdefault("common.utils.agent_utils", Mock())

# config.*
_mock_config_agent_registry = Mock()
_mock_agent_registry = Mock()
_mock_config_agent_registry.agent_registry = _mock_agent_registry
sys.modules["config.agent_registry"] = _mock_config_agent_registry

_mock_config_mcp_config = Mock()
_mock_config_mcp_config.MCPConfig = Mock()
_mock_config_mcp_config.SearchConfig = Mock()
sys.modules["config.mcp_config"] = _mock_config_mcp_config

from backend.agents.agent_template import AgentTemplate  # noqa: E402

# ---------------------------------------------------------------------------
# Async-iterator helpers
# ---------------------------------------------------------------------------


async def _async_iter(items):
    """Yield each item as an async iterator (for mocking list_agents())."""
    for item in items:
        yield item


# ---------------------------------------------------------------------------
# Test data builders
# ---------------------------------------------------------------------------


def _make_mcp_config(**kw):
    m = Mock()
    m.url = kw.get("url", "https://mcp.example.com")
    m.name = kw.get("name", "TestMCP")
    m.description = kw.get("description", "Test MCP")
    m.connection_id = kw.get("connection_id", None)
    return m


def _make_search_config(**kw):
    m = Mock()
    m.connection_name = kw.get("connection_name", "search-conn")
    m.index_name = kw.get("index_name", "test-index")
    return m


def _make_agent_record(name="TestAgent", model="test-model", instructions="Portal instructions"):
    r = Mock()
    r.name = name
    r.model = model
    r.instructions = instructions
    return r


# ---------------------------------------------------------------------------
# Shared patching helpers
# ---------------------------------------------------------------------------


def _make_project_client_mock(agent_records=None):
    """Return a mock AIProjectClient that yields agent_records from list_agents()."""
    records = agent_records or []
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.agents.list_agents = Mock(return_value=_async_iter(records))
    client.agents.create_agent = AsyncMock(return_value=_make_agent_record())
    client.beta.toolboxes.create_toolbox_version = AsyncMock()
    return client


def _make_credential_mock():
    cred = AsyncMock()
    cred.__aenter__ = AsyncMock(return_value=cred)
    cred.__aexit__ = AsyncMock(return_value=False)
    return cred


def _make_agent_cm_mock(inner=None):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=inner or Mock())
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_kwargs():
    return dict(
        agent_name="TestAgent",
        agent_description="Test Description",
        agent_instructions="Bootstrap instructions",
        use_reasoning=False,
        model_deployment_name="test-model",
        project_endpoint="https://test.project.azure.com/",
    )


@pytest.fixture
def mcp_config():
    return _make_mcp_config()


@pytest.fixture
def mcp_config_with_connection():
    return _make_mcp_config(connection_id="mcp-connection-id")


@pytest.fixture
def search_config():
    return _make_search_config()


# ---------------------------------------------------------------------------
# TestAgentTemplateInit
# ---------------------------------------------------------------------------


class TestAgentTemplateInit:
    def test_minimal_params(self, basic_kwargs):
        agent = AgentTemplate(**basic_kwargs)

        assert agent.agent_name == "TestAgent"
        assert agent.agent_description == "Test Description"
        assert agent.agent_instructions == "Bootstrap instructions"
        assert agent.use_reasoning is False
        assert agent.model_deployment_name == "test-model"
        assert agent.project_endpoint == "https://test.project.azure.com/"
        assert agent.enable_code_interpreter is False
        assert agent.mcp_cfg is None
        assert agent.search_config is None
        assert agent._agent is None
        assert agent._stack is None
        assert isinstance(agent.logger, logging.Logger)

    def test_all_params(self, basic_kwargs, mcp_config, search_config):
        agent = AgentTemplate(
            **{**basic_kwargs, "use_reasoning": True},
            enable_code_interpreter=True,
            mcp_config=mcp_config,
            search_config=search_config,
        )
        assert agent.use_reasoning is True
        assert agent.enable_code_interpreter is True
        assert agent.mcp_cfg is mcp_config
        assert agent.search_config is search_config

    def test_no_use_azure_search_attribute(self, basic_kwargs, search_config):
        """The old _use_azure_search attribute must not exist in the new pattern."""
        agent = AgentTemplate(**basic_kwargs, search_config=search_config)
        assert not hasattr(agent, "_use_azure_search")


# ---------------------------------------------------------------------------
# TestBuildTools
# ---------------------------------------------------------------------------


class TestBuildTools:
    def test_no_tools_returns_empty(self, basic_kwargs):
        agent = AgentTemplate(**basic_kwargs)
        with patch("backend.agents.agent_template.MCPTool") as mock_mcp, \
             patch("backend.agents.agent_template.AzureAISearchTool") as mock_search, \
             patch("backend.agents.agent_template.CodeInterpreterTool") as mock_ci:
            result = agent._build_tools()
        assert result == []
        mock_mcp.assert_not_called()
        mock_search.assert_not_called()
        mock_ci.assert_not_called()

    def test_mcp_tool_added(self, basic_kwargs, mcp_config):
        agent = AgentTemplate(**basic_kwargs, mcp_config=mcp_config)
        mock_tool = Mock()
        with patch("backend.agents.agent_template.MCPTool", return_value=mock_tool) as mock_cls:
            result = agent._build_tools()
        assert mock_tool in result
        call_kw = mock_cls.call_args[1]
        assert call_kw["server_label"] == mcp_config.name
        assert call_kw["server_url"] == mcp_config.url
        assert call_kw["require_approval"] == "never"
        assert "project_connection_id" not in call_kw  # no connection_id on this fixture

    def test_mcp_tool_includes_connection_id_when_set(self, basic_kwargs, mcp_config_with_connection):
        agent = AgentTemplate(**basic_kwargs, mcp_config=mcp_config_with_connection)
        with patch("backend.agents.agent_template.MCPTool") as mock_cls:
            agent._build_tools()
        call_kw = mock_cls.call_args[1]
        assert call_kw["project_connection_id"] == "mcp-connection-id"

    def test_search_tool_added(self, basic_kwargs, search_config):
        agent = AgentTemplate(**basic_kwargs, search_config=search_config)
        mock_tool = Mock()
        with patch("backend.agents.agent_template.AzureAISearchTool", return_value=mock_tool) as mock_cls:
            result = agent._build_tools()
        assert mock_tool in result
        call_kw = mock_cls.call_args[1]
        assert call_kw["index_connection_id"] == search_config.connection_name
        assert call_kw["index_name"] == search_config.index_name

    def test_search_tool_skipped_when_no_index(self, basic_kwargs):
        sc = _make_search_config(index_name=None)
        agent = AgentTemplate(**basic_kwargs, search_config=sc)
        with patch("backend.agents.agent_template.AzureAISearchTool") as mock_cls:
            agent._build_tools()
        mock_cls.assert_not_called()

    def test_code_interpreter_added(self, basic_kwargs):
        agent = AgentTemplate(**basic_kwargs, enable_code_interpreter=True)
        mock_tool = Mock()
        with patch("backend.agents.agent_template.CodeInterpreterTool", return_value=mock_tool):
            result = agent._build_tools()
        assert mock_tool in result

    def test_all_three_tools(self, basic_kwargs, mcp_config, search_config):
        agent = AgentTemplate(
            **basic_kwargs,
            mcp_config=mcp_config,
            search_config=search_config,
            enable_code_interpreter=True,
        )
        with patch("backend.agents.agent_template.MCPTool", return_value=Mock()), \
             patch("backend.agents.agent_template.AzureAISearchTool", return_value=Mock()), \
             patch("backend.agents.agent_template.CodeInterpreterTool", return_value=Mock()):
            result = agent._build_tools()
        assert len(result) == 3


# ---------------------------------------------------------------------------
# TestAgentTemplateOpen
# ---------------------------------------------------------------------------


class TestAgentTemplateOpen:
    @pytest.mark.asyncio
    async def test_open_creates_agent_when_not_found(self, basic_kwargs):
        """list_agents() returns nothing → create_agent() called with bootstrap config."""
        project_client = _make_project_client_mock(agent_records=[])
        cred = _make_credential_mock()
        agent_cm = _make_agent_cm_mock()
        chat_client_mock = Mock()
        chat_client_mock.get_toolbox = AsyncMock(return_value=Mock())

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=chat_client_mock),
            patch("backend.agents.agent_template.Agent", return_value=agent_cm),
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs)
            result = await agent.open()

        project_client.agents.create_agent.assert_called_once()
        call_kw = project_client.agents.create_agent.call_args[1]
        assert call_kw["name"] == "TestAgent"
        assert call_kw["instructions"] == "Bootstrap instructions"
        assert call_kw["model"] == "test-model"
        assert result is agent
        assert agent._agent is not None

    @pytest.mark.asyncio
    async def test_open_reuses_agent_when_found(self, basic_kwargs):
        """list_agents() returns matching agent → create_agent() NOT called."""
        existing = _make_agent_record(name="TestAgent", instructions="Portal instructions")
        project_client = _make_project_client_mock(agent_records=[existing])
        cred = _make_credential_mock()
        agent_cm = _make_agent_cm_mock()
        chat_client_mock = Mock()
        chat_client_mock.get_toolbox = AsyncMock(return_value=Mock())

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=chat_client_mock),
            patch("backend.agents.agent_template.Agent", return_value=agent_cm) as mock_agent_cls,
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs)
            await agent.open()

        project_client.agents.create_agent.assert_not_called()
        # Agent() must receive portal instructions, not bootstrap instructions
        call_kw = mock_agent_cls.call_args[1]
        assert call_kw["instructions"] == "Portal instructions"

    @pytest.mark.asyncio
    async def test_open_no_toolbox_when_no_tools(self, basic_kwargs):
        """No tools configured → toolbox is NOT created and Agent gets tools=None."""
        project_client = _make_project_client_mock()
        cred = _make_credential_mock()
        agent_cm = _make_agent_cm_mock()
        chat_client_mock = Mock()

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=chat_client_mock),
            patch("backend.agents.agent_template.Agent", return_value=agent_cm) as mock_agent_cls,
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs)
            await agent.open()

        project_client.beta.toolboxes.create_toolbox_version.assert_not_called()
        call_kw = mock_agent_cls.call_args[1]
        assert call_kw["tools"] is None

    @pytest.mark.asyncio
    async def test_open_creates_toolbox_with_mcp(self, basic_kwargs, mcp_config):
        """MCP configured → toolbox created and wired to Agent."""
        project_client = _make_project_client_mock()
        cred = _make_credential_mock()
        agent_cm = _make_agent_cm_mock()
        mock_toolbox = Mock()
        chat_client_mock = Mock()
        chat_client_mock.get_toolbox = AsyncMock(return_value=mock_toolbox)

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=chat_client_mock),
            patch("backend.agents.agent_template.Agent", return_value=agent_cm) as mock_agent_cls,
            patch("backend.agents.agent_template.MCPTool", return_value=Mock()),
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs, mcp_config=mcp_config)
            await agent.open()

        project_client.beta.toolboxes.create_toolbox_version.assert_called_once()
        call_kw = project_client.beta.toolboxes.create_toolbox_version.call_args[1]
        assert call_kw["toolbox_name"] == "macae-TestAgent-tools"
        chat_client_mock.get_toolbox.assert_called_once_with("macae-TestAgent-tools")
        agent_call_kw = mock_agent_cls.call_args[1]
        assert agent_call_kw["tools"] == [mock_toolbox]

    @pytest.mark.asyncio
    async def test_open_registers_agent(self, basic_kwargs):
        project_client = _make_project_client_mock()
        cred = _make_credential_mock()
        agent_cm = _make_agent_cm_mock()

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=agent_cm),
            patch("backend.agents.agent_template.agent_registry") as mock_reg,
        ):
            agent = AgentTemplate(**basic_kwargs)
            await agent.open()

        mock_reg.register_agent.assert_called_once_with(agent)

    @pytest.mark.asyncio
    async def test_open_is_idempotent(self, basic_kwargs):
        project_client = _make_project_client_mock()
        cred = _make_credential_mock()
        agent_cm = _make_agent_cm_mock()

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=agent_cm),
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs)
            r1 = await agent.open()
            r2 = await agent.open()

        # list_agents() called only once (second open() returns early)
        project_client.agents.list_agents.assert_called_once()
        assert r1 is r2

    @pytest.mark.asyncio
    async def test_open_cleans_up_on_error(self, basic_kwargs):
        cred = _make_credential_mock()
        project_client = _make_project_client_mock()
        project_client.agents.list_agents = Mock(side_effect=RuntimeError("boom"))

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs)
            with pytest.raises(RuntimeError, match="boom"):
                await agent.open()

        assert agent._stack is None
        assert agent._agent is None


# ---------------------------------------------------------------------------
# TestAgentTemplateClose
# ---------------------------------------------------------------------------


class TestAgentTemplateClose:
    @pytest.mark.asyncio
    async def test_close_clears_state(self, basic_kwargs):
        project_client = _make_project_client_mock()
        cred = _make_credential_mock()
        agent_cm = _make_agent_cm_mock()

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=agent_cm),
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
        await agent.close()  # must not raise

    @pytest.mark.asyncio
    async def test_context_manager(self, basic_kwargs):
        project_client = _make_project_client_mock()
        cred = _make_credential_mock()
        agent_cm = _make_agent_cm_mock()

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=agent_cm),
            patch("backend.agents.agent_template.agent_registry"),
        ):
            async with AgentTemplate(**basic_kwargs) as agent:
                assert agent._agent is not None
        assert agent._agent is None


# ---------------------------------------------------------------------------
# TestAgentTemplateInvoke
# ---------------------------------------------------------------------------


class TestAgentTemplateInvoke:
    @pytest.mark.asyncio
    async def test_invoke_before_open_raises(self, basic_kwargs):
        agent = AgentTemplate(**basic_kwargs)
        with pytest.raises(RuntimeError, match="not initialized"):
            async for _ in agent.invoke("hello"):
                pass

    @pytest.mark.asyncio
    async def test_invoke_streams_updates(self, basic_kwargs):
        update1, update2 = Mock(), Mock()

        async def _fake_run(message, *, stream=False):
            for u in [update1, update2]:
                yield u

        mock_inner = Mock()
        mock_inner.run = _fake_run
        project_client = _make_project_client_mock()
        cred = _make_credential_mock()
        agent_cm = _make_agent_cm_mock(inner=mock_inner)

        with (
            patch("backend.agents.agent_template.DefaultAzureCredential", return_value=cred),
            patch("backend.agents.agent_template.AIProjectClient", return_value=project_client),
            patch("backend.agents.agent_template.FoundryChatClient", return_value=Mock()),
            patch("backend.agents.agent_template.Agent", return_value=agent_cm),
            patch("backend.agents.agent_template.agent_registry"),
        ):
            agent = AgentTemplate(**basic_kwargs)
            await agent.open()

        collected = []
        async for update in agent.invoke("hi"):
            collected.append(update)

        assert collected == [update1, update2]


