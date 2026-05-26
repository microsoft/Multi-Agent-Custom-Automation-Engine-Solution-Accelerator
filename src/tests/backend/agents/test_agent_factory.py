"""Unit tests for agents.agent_factory (AgentFactory — GA agent_framework 1.6.0).

Ported from src/tests/backend/v4/magentic_agents/test_magentic_agent_factory.py.
Key changes:
  - MagenticAgentFactory → AgentFactory
  - FoundryAgentTemplate → AgentTemplate
  - Mock paths updated to new package layout
  - cleanup_all_agents now lives on AgentFactory as a static method
  - get_agents skips per-agent errors (UnsupportedModelError, InvalidConfigurationError,
    and unexpected exceptions) rather than propagating them
"""

import logging
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Module stubs
# pytest sets pythonpath=["src"] so imports use the `backend.` prefix.
# The factory code itself uses short absolute imports (`from agents.x import ...`);
# those are satisfied via sys.modules mocks below.
# ---------------------------------------------------------------------------

# --- common.*
sys.modules.setdefault("common", Mock())
sys.modules.setdefault("common.config", Mock())
_mock_app_config_mod = Mock()
sys.modules["common.config.app_config"] = _mock_app_config_mod
sys.modules.setdefault("common.database", Mock())
_mock_db_base_mod = Mock()
sys.modules["common.database.database_base"] = _mock_db_base_mod
sys.modules.setdefault("common.models", Mock())
_mock_messages_mod = Mock()
sys.modules["common.models.messages"] = _mock_messages_mod

mock_config = Mock()
mock_config.SUPPORTED_MODELS = '["gpt-4", "gpt-4-32k", "gpt-35-turbo"]'
mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test-endpoint.com"
_mock_app_config_mod.config = mock_config
_mock_db_base_mod.DatabaseBase = Mock()
_mock_messages_mod.TeamConfiguration = Mock()

# --- agents sub-modules (short absolute imports in factory code)
mock_agent_template_cls = Mock()
mock_mcp_config_cls = Mock()

sys.modules.setdefault("agents", Mock())  # parent package stub
_mock_agent_template_mod = Mock()
_mock_agent_template_mod.AgentTemplate = mock_agent_template_cls
sys.modules["agents.agent_template"] = _mock_agent_template_mod

mock_vector_store_config_cls = Mock()

_mock_mcp_config_mod = Mock()
_mock_mcp_config_mod.MCPConfig = mock_mcp_config_cls
_mock_mcp_config_mod.VectorStoreConfig = mock_vector_store_config_cls
sys.modules["config.mcp_config"] = _mock_mcp_config_mod

# Now import the module under test (full backend.* path as per project convention)
from backend.agents.agent_factory import AgentFactory, UnsupportedModelError

# ---------------------------------------------------------------------------
# Helper builder
# ---------------------------------------------------------------------------


def _agent_obj(**overrides) -> SimpleNamespace:
    defaults = dict(
        name="TestAgent",
        deployment_name="gpt-4",
        description="Test agent description",
        system_message="Test system message",
        coding_tools=False,
        use_toolbox=False,
        use_file_search=False,
        user_responses=False,
        vector_store_name=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAgentFactoryInit:
    """AgentFactory.__init__ tests."""

    def test_init_with_team_service(self):
        svc = Mock()
        factory = AgentFactory(team_service=svc)
        assert factory.team_service is svc
        assert factory._agent_list == []
        assert isinstance(factory.logger, logging.Logger)

    def test_init_without_team_service(self):
        factory = AgentFactory()
        assert factory.team_service is None
        assert factory._agent_list == []


class TestCreateAgentFromConfig:
    """AgentFactory.create_agent_from_config tests."""

    def setup_method(self):
        self.factory = AgentFactory(team_service=Mock())
        self.team_config = Mock(name="Test Team")
        self.memory_store = Mock()
        mock_agent_template_cls.reset_mock()
        mock_mcp_config_cls.reset_mock()
        mock_vector_store_config_cls.reset_mock()

    @pytest.mark.asyncio
    async def test_user_responses_true_does_not_create_mcp_config(self):
        """user_responses=True alone does NOT create MCPConfig (use_toolbox needed)."""
        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        await self.factory.create_agent_from_config(
            "user123",
            _agent_obj(user_responses=True),
            self.team_config,
            self.memory_store,
        )

        mock_mcp_config_cls.from_env.assert_not_called()
        call_kwargs = mock_agent_template_cls.call_args[1]
        assert call_kwargs["mcp_config"] is None

    @pytest.mark.asyncio
    async def test_user_responses_appends_interaction_prompt(self):
        """user_responses=True appends universal interaction prompt to instructions."""
        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        await self.factory.create_agent_from_config(
            "user123",
            _agent_obj(user_responses=True, system_message="Be helpful."),
            self.team_config,
            self.memory_store,
        )

        call_kwargs = mock_agent_template_cls.call_args[1]
        assert "CRITICAL RULES" in call_kwargs["agent_instructions"]
        assert "Be helpful." in call_kwargs["agent_instructions"]

    @pytest.mark.asyncio
    async def test_user_responses_false_no_mcp_config(self):
        """user_responses=False (default) does not create MCPConfig."""
        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        await self.factory.create_agent_from_config(
            "user123", _agent_obj(), self.team_config, self.memory_store
        )

        mock_mcp_config_cls.from_env.assert_not_called()

    @pytest.mark.asyncio
    async def test_use_toolbox_takes_priority_over_user_responses(self):
        """use_toolbox=True takes priority; MCPConfig uses the toolbox_filter, not 'user_responses'."""
        mcp_instance = Mock()
        mock_mcp_config_cls.from_env.return_value = mcp_instance

        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        await self.factory.create_agent_from_config(
            "user123",
            _agent_obj(use_toolbox=True, toolbox_filter="hr", user_responses=True),
            self.team_config,
            self.memory_store,
        )

        mock_mcp_config_cls.from_env.assert_called_once_with(domain="hr")

    @pytest.mark.asyncio
    async def test_unsupported_model_raises(self):
        """Unsupported deployment_name raises UnsupportedModelError."""
        with pytest.raises(UnsupportedModelError):
            await self.factory.create_agent_from_config(
                "user123",
                _agent_obj(deployment_name="unsupported-model"),
                self.team_config,
                self.memory_store,
            )

    @pytest.mark.asyncio
    async def test_basic_agent_created(self):
        """A standard config creates and opens an AgentTemplate."""
        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        result = await self.factory.create_agent_from_config(
            "user123", _agent_obj(), self.team_config, self.memory_store
        )

        assert result is agent_instance
        mock_agent_template_cls.assert_called_once()
        agent_instance.open.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_file_search_config(self):
        """use_file_search=True + vector_store_name creates VectorStoreConfig."""
        vs_instance = Mock()
        mock_vector_store_config_cls.return_value = vs_instance

        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        await self.factory.create_agent_from_config(
            "user123",
            _agent_obj(use_file_search=True, vector_store_name="my-vector-store"),
            self.team_config,
            self.memory_store,
        )

        mock_vector_store_config_cls.assert_called_once_with(vector_store_name="my-vector-store")
        call_kwargs = mock_agent_template_cls.call_args[1]
        assert call_kwargs["vector_store_config"] is vs_instance

    @pytest.mark.asyncio
    async def test_file_search_without_vector_store_name_skips(self):
        """use_file_search=True but no vector_store_name → no VectorStoreConfig."""
        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        await self.factory.create_agent_from_config(
            "user123",
            _agent_obj(use_file_search=True, vector_store_name=None),
            self.team_config,
            self.memory_store,
        )

        mock_vector_store_config_cls.assert_not_called()
        call_kwargs = mock_agent_template_cls.call_args[1]
        assert call_kwargs["vector_store_config"] is None

    @pytest.mark.asyncio
    async def test_with_toolbox_config(self):
        """use_toolbox=True loads MCPConfig from env."""
        mcp_instance = Mock()
        mock_mcp_config_cls.from_env.return_value = mcp_instance

        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        await self.factory.create_agent_from_config(
            "user123", _agent_obj(use_toolbox=True), self.team_config, self.memory_store
        )

        mock_mcp_config_cls.from_env.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_coding_tools(self):
        """coding_tools=True passes enable_code_interpreter=True to AgentTemplate."""
        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        await self.factory.create_agent_from_config(
            "user123", _agent_obj(coding_tools=True), self.team_config, self.memory_store
        )

        call_kwargs = mock_agent_template_cls.call_args[1]
        assert call_kwargs["enable_code_interpreter"] is True


class TestGetAgents:
    """AgentFactory.get_agents tests."""

    def setup_method(self):
        self.factory = AgentFactory(team_service=Mock())
        self.memory_store = Mock()
        mock_agent_template_cls.reset_mock()

    def _team_config(self, *agent_objs):
        cfg = Mock()
        cfg.agents = list(agent_objs)
        return cfg

    @pytest.mark.asyncio
    async def test_single_agent_success(self):
        agent_instance = Mock()
        agent_instance.open = AsyncMock()
        mock_agent_template_cls.return_value = agent_instance

        result = await self.factory.get_agents(
            "user123", self._team_config(_agent_obj()), self.memory_store
        )

        assert len(result) == 1
        assert result[0] is agent_instance
        assert len(self.factory._agent_list) == 1

    @pytest.mark.asyncio
    async def test_multiple_agents_success(self):
        a1 = Mock()
        a1.open = AsyncMock()
        a2 = Mock()
        a2.open = AsyncMock()
        mock_agent_template_cls.side_effect = [a1, a2]

        result = await self.factory.get_agents(
            "user123",
            self._team_config(_agent_obj(name="A1"), _agent_obj(name="A2")),
            self.memory_store,
        )

        assert len(result) == 2
        assert result[0] is a1
        assert result[1] is a2

    @pytest.mark.asyncio
    async def test_unsupported_model_is_skipped(self):
        """Agent with unsupported model is skipped; result is empty."""
        result = await self.factory.get_agents(
            "user123",
            self._team_config(_agent_obj(deployment_name="unsupported-model")),
            self.memory_store,
        )
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_unexpected_exception_skips_agent(self):
        """Unexpected exception on one agent is logged and skipped; others succeed."""
        good_instance = Mock()
        good_instance.open = AsyncMock()
        mock_agent_template_cls.side_effect = [Exception("boom"), good_instance]

        result = await self.factory.get_agents(
            "user123",
            self._team_config(_agent_obj(name="Bad"), _agent_obj(name="Good")),
            self.memory_store,
        )

        assert len(result) == 1
        assert result[0] is good_instance

    @pytest.mark.asyncio
    async def test_empty_team(self):
        result = await self.factory.get_agents(
            "user123", self._team_config(), self.memory_store
        )
        assert result == []
        assert self.factory._agent_list == []

    @pytest.mark.asyncio
    async def test_iterating_config_raises_propagates(self):
        """Config-level failure (iterating agents) propagates the exception."""
        cfg = Mock()
        cfg.agents = Mock()
        cfg.agents.__iter__ = Mock(side_effect=Exception("config load error"))

        with pytest.raises(Exception, match="config load error"):
            await self.factory.get_agents("user123", cfg, self.memory_store)


class TestCleanupAllAgents:
    """AgentFactory.cleanup_all_agents static method tests."""

    @pytest.mark.asyncio
    async def test_cleanup_all_success(self):
        a1 = Mock()
        a1.close = AsyncMock()
        a1.agent_name = "Agent1"
        a2 = Mock()
        a2.close = AsyncMock()
        a2.agent_name = "Agent2"
        lst = [a1, a2]

        await AgentFactory.cleanup_all_agents(lst)

        a1.close.assert_called_once()
        a2.close.assert_called_once()
        assert lst == []

    @pytest.mark.asyncio
    async def test_cleanup_with_exceptions(self):
        """Close errors are swallowed; other agents still closed; list cleared."""
        a1 = Mock()
        a1.close = AsyncMock(side_effect=Exception("fail"))
        a1.agent_name = "Agent1"
        a2 = Mock()
        a2.close = AsyncMock()
        a2.agent_name = "Agent2"
        lst = [a1, a2]

        await AgentFactory.cleanup_all_agents(lst)

        a1.close.assert_called_once()
        a2.close.assert_called_once()
        assert lst == []

    @pytest.mark.asyncio
    async def test_cleanup_agent_without_name(self):
        """Agent without agent_name attribute is still closed."""
        a = Mock(spec=["close"])
        a.close = AsyncMock(side_effect=Exception("fail"))
        lst = [a]

        await AgentFactory.cleanup_all_agents(lst)
        assert lst == []

    @pytest.mark.asyncio
    async def test_cleanup_empty_list(self):
        lst = []
        await AgentFactory.cleanup_all_agents(lst)
        assert lst == []

    @pytest.mark.asyncio
    async def test_close_all_instance_method(self):
        """close_all() delegates to cleanup_all_agents and clears _agent_list."""
        factory = AgentFactory()
        a = Mock()
        a.close = AsyncMock()
        a.agent_name = "A"
        factory._agent_list.append(a)

        await factory.close_all()

        a.close.assert_called_once()
        assert factory._agent_list == []
