"""Unit tests for backend.v4.magentic_agents.magentic_agent_factory module."""
import asyncio
import json
import logging
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest

# Mock the dependencies before importing the module under test
sys.modules['common'] = Mock()
sys.modules['common.config'] = Mock()
sys.modules['common.config.app_config'] = Mock()
sys.modules['common.database'] = Mock()
sys.modules['common.database.database_base'] = Mock()
sys.modules['common.models'] = Mock()
sys.modules['common.models.messages_af'] = Mock()
sys.modules['v4'] = Mock()
sys.modules['v4.common'] = Mock()
sys.modules['v4.common.services'] = Mock()
sys.modules['v4.common.services.team_service'] = Mock()
sys.modules['v4.magentic_agents'] = Mock()
sys.modules['v4.magentic_agents.foundry_agent'] = Mock()
sys.modules['v4.magentic_agents.models'] = Mock()
sys.modules['v4.magentic_agents.models.agent_models'] = Mock()
sys.modules['v4.magentic_agents.proxy_agent'] = Mock()

# Create mock classes
mock_config = Mock()
mock_config.SUPPORTED_MODELS = '["gpt-4", "gpt-4-32k", "gpt-35-turbo"]'
mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test-endpoint.com"

mock_database_base = Mock()
mock_team_configuration = Mock()
mock_team_service = Mock()
mock_foundry_agent_template = Mock()
mock_mcp_config = Mock()
mock_search_config = Mock()
mock_proxy_agent = Mock()

# Set up the mock modules
sys.modules['common.config.app_config'].config = mock_config
sys.modules['common.database.database_base'].DatabaseBase = mock_database_base
sys.modules['common.models.messages_af'].TeamConfiguration = mock_team_configuration
sys.modules['v4.common.services.team_service'].TeamService = mock_team_service
sys.modules['v4.magentic_agents.foundry_agent'].FoundryAgentTemplate = mock_foundry_agent_template
sys.modules['v4.magentic_agents.models.agent_models'].MCPConfig = mock_mcp_config
sys.modules['v4.magentic_agents.models.agent_models'].SearchConfig = mock_search_config
sys.modules['v4.magentic_agents.proxy_agent'].ProxyAgent = mock_proxy_agent

# Import the module under test
from backend.v4.magentic_agents.magentic_agent_factory import (
    MagenticAgentFactory,
    UnsupportedModelError,
    InvalidConfigurationError
)


class TestMagenticAgentFactory:
    """Test cases for MagenticAgentFactory class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_team_service = Mock()
        self.factory = MagenticAgentFactory(team_service=self.mock_team_service)
        
        # Setup mock agent object
        self.mock_agent_obj = SimpleNamespace()
        self.mock_agent_obj.name = "TestAgent"
        self.mock_agent_obj.deployment_name = "gpt-4"
        self.mock_agent_obj.description = "Test agent description"
        self.mock_agent_obj.system_message = "Test system message"
        self.mock_agent_obj.use_reasoning = False
        self.mock_agent_obj.use_bing = False
        self.mock_agent_obj.coding_tools = False
        self.mock_agent_obj.use_rag = False
        self.mock_agent_obj.use_mcp = False
        self.mock_agent_obj.index_name = None
        
        # Setup mock team configuration
        self.mock_team_config = Mock()
        self.mock_team_config.name = "Test Team"
        self.mock_team_config.agents = [self.mock_agent_obj]
        
        # Setup mock memory store
        self.mock_memory_store = Mock()
        
        # Reset mocks
        mock_foundry_agent_template.reset_mock()
        mock_proxy_agent.reset_mock()
        mock_mcp_config.reset_mock()
        mock_search_config.reset_mock()

    def test_init_with_team_service(self):
        """Test MagenticAgentFactory initialization with team service."""
        factory = MagenticAgentFactory(team_service=self.mock_team_service)
        
        assert factory.team_service is self.mock_team_service
        assert factory._agent_list == []
        assert isinstance(factory.logger, logging.Logger)

    def test_init_without_team_service(self):
        """Test MagenticAgentFactory initialization without team service."""
        factory = MagenticAgentFactory()
        
        assert factory.team_service is None
        assert factory._agent_list == []
        assert isinstance(factory.logger, logging.Logger)

    def test_extract_use_reasoning_with_true_bool(self):
        """Test extract_use_reasoning with explicit boolean True."""
        agent_obj = SimpleNamespace()
        agent_obj.use_reasoning = True
        
        result = self.factory.extract_use_reasoning(agent_obj)
        assert result is True

    def test_extract_use_reasoning_with_false_bool(self):
        """Test extract_use_reasoning with explicit boolean False."""
        agent_obj = SimpleNamespace()
        agent_obj.use_reasoning = False
        
        result = self.factory.extract_use_reasoning(agent_obj)
        assert result is False

    def test_extract_use_reasoning_with_dict_true(self):
        """Test extract_use_reasoning with dict containing True."""
        agent_obj = {"use_reasoning": True}
        
        result = self.factory.extract_use_reasoning(agent_obj)
        assert result is True

    def test_extract_use_reasoning_with_dict_false(self):
        """Test extract_use_reasoning with dict containing False."""
        agent_obj = {"use_reasoning": False}
        
        result = self.factory.extract_use_reasoning(agent_obj)
        assert result is False

    def test_extract_use_reasoning_with_dict_missing_key(self):
        """Test extract_use_reasoning with dict missing use_reasoning key."""
        agent_obj = {"name": "TestAgent"}
        
        result = self.factory.extract_use_reasoning(agent_obj)
        assert result is False

    def test_extract_use_reasoning_with_non_bool_value(self):
        """Test extract_use_reasoning with non-boolean value."""
        agent_obj = SimpleNamespace()
        agent_obj.use_reasoning = "true"  # String instead of boolean
        
        result = self.factory.extract_use_reasoning(agent_obj)
        assert result is False

    def test_extract_use_reasoning_with_missing_attribute(self):
        """Test extract_use_reasoning with missing attribute."""
        agent_obj = SimpleNamespace()
        
        result = self.factory.extract_use_reasoning(agent_obj)
        assert result is False

    @pytest.mark.asyncio
    async def test_create_agent_from_config_proxy_agent(self):
        """Test creating a ProxyAgent from configuration."""
        self.mock_agent_obj.name = "proxyagent"
        self.mock_agent_obj.deployment_name = None
        
        mock_proxy_instance = Mock()
        mock_proxy_agent.return_value = mock_proxy_instance
        
        result = await self.factory.create_agent_from_config(
            "user123", self.mock_agent_obj, self.mock_team_config, self.mock_memory_store
        )
        
        assert result is mock_proxy_instance
        mock_proxy_agent.assert_called_once_with(user_id="user123")

    @pytest.mark.asyncio
    async def test_create_agent_from_config_unsupported_model(self):
        """Test creating agent with unsupported model raises error."""
        self.mock_agent_obj.deployment_name = "unsupported-model"
        
        with pytest.raises(UnsupportedModelError) as exc_info:
            await self.factory.create_agent_from_config(
                "user123", self.mock_agent_obj, self.mock_team_config, self.mock_memory_store
            )
        
        assert "unsupported-model" in str(exc_info.value)
        assert "not supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_agent_from_config_reasoning_with_bing_error(self):
        """Test creating reasoning agent with Bing search raises error."""
        self.mock_agent_obj.use_reasoning = True
        self.mock_agent_obj.use_bing = True
        
        with pytest.raises(InvalidConfigurationError) as exc_info:
            await self.factory.create_agent_from_config(
                "user123", self.mock_agent_obj, self.mock_team_config, self.mock_memory_store
            )
        
        assert "cannot use Bing search" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_agent_from_config_reasoning_with_coding_tools_error(self):
        """Test creating reasoning agent with coding tools raises error."""
        self.mock_agent_obj.use_reasoning = True
        self.mock_agent_obj.coding_tools = True
        
        with pytest.raises(InvalidConfigurationError) as exc_info:
            await self.factory.create_agent_from_config(
                "user123", self.mock_agent_obj, self.mock_team_config, self.mock_memory_store
            )
        
        assert "cannot use Bing search or coding tools" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_agent_from_config_foundry_agent_basic(self):
        """Test creating a basic FoundryAgent from configuration."""
        mock_agent_instance = Mock()
        mock_agent_instance.open = AsyncMock()
        mock_foundry_agent_template.return_value = mock_agent_instance
        
        result = await self.factory.create_agent_from_config(
            "user123", self.mock_agent_obj, self.mock_team_config, self.mock_memory_store
        )
        
        assert result is mock_agent_instance
        mock_foundry_agent_template.assert_called_once()
        mock_agent_instance.open.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_from_config_with_search_config(self):
        """Test creating agent with search configuration."""
        self.mock_agent_obj.use_rag = True
        self.mock_agent_obj.index_name = "test-index"
        
        mock_search_instance = Mock()
        mock_search_config.from_env.return_value = mock_search_instance
        
        mock_agent_instance = Mock()
        mock_agent_instance.open = AsyncMock()
        mock_foundry_agent_template.return_value = mock_agent_instance
        
        result = await self.factory.create_agent_from_config(
            "user123", self.mock_agent_obj, self.mock_team_config, self.mock_memory_store
        )
        
        mock_search_config.from_env.assert_called_once_with("test-index")
        assert result is mock_agent_instance

    @pytest.mark.asyncio
    async def test_create_agent_from_config_with_mcp_config(self):
        """Test creating agent with MCP configuration."""
        self.mock_agent_obj.use_mcp = True
        
        mock_mcp_instance = Mock()
        mock_mcp_config.from_env.return_value = mock_mcp_instance
        
        mock_agent_instance = Mock()
        mock_agent_instance.open = AsyncMock()
        mock_foundry_agent_template.return_value = mock_agent_instance
        
        result = await self.factory.create_agent_from_config(
            "user123", self.mock_agent_obj, self.mock_team_config, self.mock_memory_store
        )
        
        mock_mcp_config.from_env.assert_called_once()
        assert result is mock_agent_instance

    @pytest.mark.asyncio
    async def test_create_agent_from_config_with_reasoning(self):
        """Test creating agent with reasoning enabled."""
        self.mock_agent_obj.use_reasoning = True
        
        mock_agent_instance = Mock()
        mock_agent_instance.open = AsyncMock()
        mock_foundry_agent_template.return_value = mock_agent_instance
        
        result = await self.factory.create_agent_from_config(
            "user123", self.mock_agent_obj, self.mock_team_config, self.mock_memory_store
        )
        
        # Verify FoundryAgentTemplate was called with use_reasoning=True
        call_args = mock_foundry_agent_template.call_args
        assert call_args[1]['use_reasoning'] is True
        assert result is mock_agent_instance

    @pytest.mark.asyncio
    async def test_create_agent_from_config_with_coding_tools(self):
        """Test creating agent with coding tools enabled."""
        self.mock_agent_obj.coding_tools = True
        
        mock_agent_instance = Mock()
        mock_agent_instance.open = AsyncMock()
        mock_foundry_agent_template.return_value = mock_agent_instance
        
        result = await self.factory.create_agent_from_config(
            "user123", self.mock_agent_obj, self.mock_team_config, self.mock_memory_store
        )
        
        # Verify FoundryAgentTemplate was called with enable_code_interpreter=True
        call_args = mock_foundry_agent_template.call_args
        assert call_args[1]['enable_code_interpreter'] is True
        assert result is mock_agent_instance

    @pytest.mark.asyncio
    async def test_get_agents_single_agent_success(self):
        """Test get_agents with single successful agent creation."""
        mock_agent_instance = Mock()
        mock_agent_instance.open = AsyncMock()
        mock_foundry_agent_template.return_value = mock_agent_instance
        
        result = await self.factory.get_agents(
            "user123", self.mock_team_config, self.mock_memory_store
        )
        
        assert len(result) == 1
        assert result[0] is mock_agent_instance
        assert len(self.factory._agent_list) == 1
        assert self.factory._agent_list[0] is mock_agent_instance

    @pytest.mark.asyncio
    async def test_get_agents_multiple_agents_success(self):
        """Test get_agents with multiple successful agent creations."""
        # Create multiple agent objects
        agent_obj_2 = SimpleNamespace()
        agent_obj_2.name = "TestAgent2"
        agent_obj_2.deployment_name = "gpt-4"
        agent_obj_2.description = "Test agent 2 description"
        agent_obj_2.system_message = "Test system message 2"
        agent_obj_2.use_reasoning = False
        agent_obj_2.use_bing = False
        agent_obj_2.coding_tools = False
        agent_obj_2.use_rag = False
        agent_obj_2.use_mcp = False
        agent_obj_2.index_name = None
        
        self.mock_team_config.agents = [self.mock_agent_obj, agent_obj_2]
        
        mock_agent_instance_1 = Mock()
        mock_agent_instance_1.open = AsyncMock()
        mock_agent_instance_2 = Mock()
        mock_agent_instance_2.open = AsyncMock()
        
        mock_foundry_agent_template.side_effect = [mock_agent_instance_1, mock_agent_instance_2]
        
        result = await self.factory.get_agents(
            "user123", self.mock_team_config, self.mock_memory_store
        )
        
        assert len(result) == 2
        assert result[0] is mock_agent_instance_1
        assert result[1] is mock_agent_instance_2
        assert len(self.factory._agent_list) == 2

    @pytest.mark.asyncio
    async def test_get_agents_with_unsupported_model_error(self):
        """Test get_agents handles UnsupportedModelError gracefully."""
        # Create an agent with unsupported model - it should be skipped
        self.mock_agent_obj.deployment_name = "unsupported-model"
        
        result = await self.factory.get_agents(
            "user123", self.mock_team_config, self.mock_memory_store
        )
        
        # Should have skipped the agent with unsupported model
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_agents_with_invalid_configuration_error(self):
        """Test get_agents handles InvalidConfigurationError gracefully."""
        # Create agent with invalid configuration (reasoning + bing) - it should be skipped
        self.mock_agent_obj.use_reasoning = True
        self.mock_agent_obj.use_bing = True  # This will cause InvalidConfigurationError
        
        result = await self.factory.get_agents(
            "user123", self.mock_team_config, self.mock_memory_store
        )
        
        # Should have skipped the agent with invalid configuration
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_agents_with_general_exception(self):
        """Test get_agents handles general exceptions gracefully."""
        # Mock foundry agent to raise exception for first agent
        mock_foundry_agent_template.side_effect = [Exception("Test error"), Mock()]
        
        # Create a second valid agent
        agent_obj_2 = SimpleNamespace()
        agent_obj_2.name = "TestAgent2"
        agent_obj_2.deployment_name = "gpt-4"
        agent_obj_2.description = "Test agent 2 description"
        agent_obj_2.system_message = "Test system message 2"
        agent_obj_2.use_reasoning = False
        agent_obj_2.use_bing = False
        agent_obj_2.coding_tools = False
        agent_obj_2.use_rag = False
        agent_obj_2.use_mcp = False
        agent_obj_2.index_name = None
        
        self.mock_team_config.agents = [self.mock_agent_obj, agent_obj_2]
        
        mock_agent_instance = Mock()
        mock_agent_instance.open = AsyncMock()
        mock_foundry_agent_template.side_effect = [Exception("Test error"), mock_agent_instance]
        
        result = await self.factory.get_agents(
            "user123", self.mock_team_config, self.mock_memory_store
        )
        
        # Should have skipped the first agent but created the second one
        assert len(result) == 1
        assert result[0] is mock_agent_instance

    @pytest.mark.asyncio
    async def test_get_agents_empty_team(self):
        """Test get_agents with empty team configuration."""
        self.mock_team_config.agents = []
        
        result = await self.factory.get_agents(
            "user123", self.mock_team_config, self.mock_memory_store
        )
        
        assert result == []
        assert self.factory._agent_list == []

    @pytest.mark.asyncio
    async def test_get_agents_exception_during_loading(self):
        """Test get_agents handles exceptions during team configuration loading."""
        # Make the team config agents property raise an exception
        self.mock_team_config.agents = Mock()
        self.mock_team_config.agents.__iter__ = Mock(side_effect=Exception("Test loading error"))
        
        with pytest.raises(Exception) as exc_info:
            await self.factory.get_agents(
                "user123", self.mock_team_config, self.mock_memory_store
            )
        
        assert "Test loading error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cleanup_all_agents_success(self):
        """Test successful cleanup of all agents."""
        mock_agent_1 = Mock()
        mock_agent_1.close = AsyncMock()
        mock_agent_1.agent_name = "Agent1"
        
        mock_agent_2 = Mock()
        mock_agent_2.close = AsyncMock()
        mock_agent_2.agent_name = "Agent2"
        
        agent_list = [mock_agent_1, mock_agent_2]
        
        await MagenticAgentFactory.cleanup_all_agents(agent_list)
        
        mock_agent_1.close.assert_called_once()
        mock_agent_2.close.assert_called_once()
        assert len(agent_list) == 0

    @pytest.mark.asyncio
    async def test_cleanup_all_agents_with_exceptions(self):
        """Test cleanup of agents when some agents raise exceptions."""
        mock_agent_1 = Mock()
        mock_agent_1.close = AsyncMock(side_effect=Exception("Close error"))
        mock_agent_1.agent_name = "Agent1"
        
        mock_agent_2 = Mock()
        mock_agent_2.close = AsyncMock()
        mock_agent_2.agent_name = "Agent2"
        
        agent_list = [mock_agent_1, mock_agent_2]
        
        # Should not raise exception even if some agents fail to close
        await MagenticAgentFactory.cleanup_all_agents(agent_list)
        
        mock_agent_1.close.assert_called_once()
        mock_agent_2.close.assert_called_once()
        assert len(agent_list) == 0

    @pytest.mark.asyncio
    async def test_cleanup_all_agents_with_agent_without_name(self):
        """Test cleanup of agents that don't have agent_name attribute."""
        mock_agent = Mock()
        mock_agent.close = AsyncMock(side_effect=Exception("Close error"))
        # No agent_name attribute
        
        agent_list = [mock_agent]
        
        # Should not raise exception even if agent doesn't have name
        await MagenticAgentFactory.cleanup_all_agents(agent_list)
        
        mock_agent.close.assert_called_once()
        assert len(agent_list) == 0

    @pytest.mark.asyncio
    async def test_cleanup_all_agents_empty_list(self):
        """Test cleanup with empty agent list."""
        agent_list = []
        
        await MagenticAgentFactory.cleanup_all_agents(agent_list)
        
        assert len(agent_list) == 0


class TestExceptionClasses:
    """Test cases for custom exception classes."""

    def test_unsupported_model_error(self):
        """Test UnsupportedModelError exception."""
        error_msg = "Test unsupported model error"
        exc = UnsupportedModelError(error_msg)
        
        assert str(exc) == error_msg
        assert isinstance(exc, Exception)

    def test_invalid_configuration_error(self):
        """Test InvalidConfigurationError exception."""
        error_msg = "Test invalid configuration error"
        exc = InvalidConfigurationError(error_msg)
        
        assert str(exc) == error_msg
        assert isinstance(exc, Exception)