"""
Unit tests for v4 MagenticAgentFactory.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List

# Add backend path to sys.path for proper imports
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Mock all problematic imports before importing the actual module
sys.modules['common.config.app_config'] = Mock()
sys.modules['common.database.database_base'] = Mock()
sys.modules['common.models.messages_af'] = Mock()
sys.modules['v4.common.services.team_service'] = Mock()
sys.modules['v4.magentic_agents.foundry_agent'] = Mock()
sys.modules['v4.magentic_agents.models.agent_models'] = Mock()
sys.modules['v4.magentic_agents.proxy_agent'] = Mock()

# Now import the actual module
from v4.magentic_agents.magentic_agent_factory import MagenticAgentFactory, UnsupportedModelError, InvalidConfigurationError

@pytest.fixture
def mock_foundry_agent():
    """Create a mock FoundryAgentTemplate."""
    with patch('v4.magentic_agents.magentic_agent_factory.FoundryAgentTemplate') as mock:
        mock_instance = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_proxy_agent():
    """Create a mock ProxyAgent.""" 
    with patch('v4.magentic_agents.magentic_agent_factory.ProxyAgent') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def factory():
    """Create MagenticAgentFactory instance with mocked dependencies."""
    with patch('v4.magentic_agents.magentic_agent_factory.config') as mock_config:
        mock_config.SUPPORTED_MODELS = '["gpt-4", "gpt-35-turbo"]'
        mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint"
        factory_instance = MagenticAgentFactory()
        return factory_instance

# Create mock classes for dependencies
class MockTeamConfiguration:
    def __init__(self, name="test_team", agents=None):
        self.name = name
        self.agents = agents or []

class MockTeamAgent:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class TestMagenticAgentFactoryInit:
    """Test cases for MagenticAgentFactory initialization."""

    def test_init_without_team_service(self):
        """Test initialization without team service."""
        factory = MagenticAgentFactory()
        
        assert factory.team_service is None
        assert factory._agent_list == []
        assert factory.logger is not None

    def test_init_with_team_service(self):
        """Test initialization with team service."""
        mock_team_service = Mock()
        
        factory = MagenticAgentFactory(team_service=mock_team_service)
        
        assert factory.team_service == mock_team_service
        assert factory._agent_list == []
        assert factory.logger is not None

class TestExtractUseReasoning:
    """Test cases for extract_use_reasoning method."""

    def test_extract_use_reasoning_dict_true(self, factory):
        """Test extract_use_reasoning with dict input - true."""
        agent_dict = {"use_reasoning": True}
        
        result = factory.extract_use_reasoning(agent_dict)
        
        assert result is True

    def test_extract_use_reasoning_dict_false(self, factory):
        """Test extract_use_reasoning with dict input - false."""
        agent_dict = {"use_reasoning": False}
        
        result = factory.extract_use_reasoning(agent_dict)
        
        assert result is False

    def test_extract_use_reasoning_dict_missing(self, factory):
        """Test extract_use_reasoning with dict input - missing key."""
        agent_dict = {"name": "test_agent"}
        
        result = factory.extract_use_reasoning(agent_dict)
        
        assert result is False

    def test_extract_use_reasoning_object_true(self, factory):
        """Test extract_use_reasoning with object input - true."""
        agent_obj = MockTeamAgent(use_reasoning=True)
        
        result = factory.extract_use_reasoning(agent_obj)
        
        assert result is True

    def test_extract_use_reasoning_object_false(self, factory):
        """Test extract_use_reasoning with object input - false."""
        agent_obj = MockTeamAgent(use_reasoning=False)
        
        result = factory.extract_use_reasoning(agent_obj)
        
        assert result is False

    def test_extract_use_reasoning_object_missing(self, factory):
        """Test extract_use_reasoning with object input - missing attribute."""
        agent_obj = MockTeamAgent(name="test_agent")
        
        result = factory.extract_use_reasoning(agent_obj)
        
        assert result is False

class TestCreateAgentFromConfig:
    """Test cases for create_agent_from_config method."""

    @pytest.mark.asyncio
    @patch('v4.magentic_agents.magentic_agent_factory.ProxyAgent')
    async def test_create_proxy_agent(self, mock_proxy_class, factory):
        """Test creating ProxyAgent."""
        mock_proxy_instance = Mock()
        mock_proxy_class.return_value = mock_proxy_instance
        
        agent_obj = MockTeamAgent(name="proxyagent")
        user_id = "test_user"
        team_config = MockTeamConfiguration()
        memory_store = Mock()
        
        result = await factory.create_agent_from_config(user_id, agent_obj, team_config, memory_store)
        
        mock_proxy_class.assert_called_once_with(user_id=user_id)
        assert result == mock_proxy_instance
        # Note: ProxyAgent is not added to _agent_list in create_agent_from_config, only in get_agents

    @pytest.mark.asyncio 
    @patch('v4.magentic_agents.magentic_agent_factory.FoundryAgentTemplate')
    async def test_create_foundry_agent_supported_model(self, mock_foundry_class, factory):
        """Test creating FoundryAgentTemplate with supported model."""
        mock_foundry_instance = AsyncMock()
        mock_foundry_class.return_value = mock_foundry_instance
        
        agent_obj = MockTeamAgent(name="TestAgent", deployment_name="gpt-4")
        user_id = "test_user"
        team_config = MockTeamConfiguration()
        memory_store = Mock()
        
        with patch('v4.magentic_agents.magentic_agent_factory.config') as mock_config:
            mock_config.SUPPORTED_MODELS = '["gpt-4", "gpt-35-turbo"]'
            mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint"
            
            result = await factory.create_agent_from_config(user_id, agent_obj, team_config, memory_store)
        
        mock_foundry_class.assert_called_once()
        mock_foundry_instance.open.assert_called_once()
        assert result == mock_foundry_instance

    @pytest.mark.asyncio
    async def test_create_agent_unsupported_model(self, factory):
        """Test creating agent with unsupported model."""
        agent_obj = MockTeamAgent(name="TestAgent", deployment_name="unsupported-model")
        user_id = "test_user"
        team_config = MockTeamConfiguration()
        memory_store = Mock()
        
        with patch('v4.magentic_agents.magentic_agent_factory.config') as mock_config:
            mock_config.SUPPORTED_MODELS = '["gpt-4", "gpt-35-turbo"]'
            
            with pytest.raises(UnsupportedModelError):
                await factory.create_agent_from_config(user_id, agent_obj, team_config, memory_store)

    @pytest.mark.asyncio
    async def test_create_agent_no_deployment_name_non_proxy(self, factory):
        """Test creating non-proxy agent without deployment name."""
        agent_obj = MockTeamAgent(name="TestAgent")
        user_id = "test_user"
        team_config = MockTeamConfiguration()
        memory_store = Mock()
        
        with patch('v4.magentic_agents.magentic_agent_factory.config') as mock_config:
            mock_config.SUPPORTED_MODELS = '["gpt-4", "gpt-35-turbo"]'
            
            with pytest.raises(UnsupportedModelError):  # No deployment_name means None not in supported models
                await factory.create_agent_from_config(user_id, agent_obj, team_config, memory_store)

class TestGetAgents:
    """Test cases for get_agents method."""

    @pytest.mark.asyncio
    @patch('v4.magentic_agents.magentic_agent_factory.ProxyAgent')
    async def test_get_agents_success(self, mock_proxy_class, factory):
        """Test get_agents with successful agent creation."""
        mock_proxy_instance = Mock()
        mock_proxy_class.return_value = mock_proxy_instance
        
        agent_configs = [MockTeamAgent(name="proxyagent")]
        team_config = MockTeamConfiguration(name="test_team", agents=agent_configs)
        user_id = "test_user"
        memory_store = Mock()
        
        with patch('v4.magentic_agents.magentic_agent_factory.config') as mock_config:
            mock_config.SUPPORTED_MODELS = '["gpt-4", "gpt-35-turbo"]'
            mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint"
            
            result = await factory.get_agents(user_id, team_config, memory_store)
        
        assert len(result) == 1
        assert result[0] == mock_proxy_instance
        assert len(factory._agent_list) == 1

    @pytest.mark.asyncio
    async def test_get_agents_with_failures(self, factory):
        """Test get_agents with some agent creation failures."""
        # Mix of valid and invalid agents
        agent_configs = [
            MockTeamAgent(name="proxyagent"),  # Valid
            MockTeamAgent(name="TestAgent", deployment_name="unsupported"),  # Invalid model
            MockTeamAgent(name="TestAgent2")  # Missing deployment_name
        ]
        team_config = MockTeamConfiguration(name="test_team", agents=agent_configs)
        user_id = "test_user"
        memory_store = Mock()
        
        with patch('v4.magentic_agents.magentic_agent_factory.ProxyAgent') as mock_proxy:
            mock_proxy_instance = Mock()
            mock_proxy.return_value = mock_proxy_instance
            
            with patch('v4.magentic_agents.magentic_agent_factory.config') as mock_config:
                mock_config.SUPPORTED_MODELS = '["gpt-4", "gpt-35-turbo"]'
                mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint"
                
                result = await factory.get_agents(user_id, team_config, memory_store)
            
            # Should only return successful agents
            assert len(result) == 1
            assert result[0] == mock_proxy_instance

    @pytest.mark.asyncio
    async def test_get_agents_empty_config(self, factory):
        """Test get_agents with empty agent configuration."""
        team_config = MockTeamConfiguration(name="empty_team", agents=[])
        user_id = "test_user"
        memory_store = Mock()
        
        result = await factory.get_agents(user_id, team_config, memory_store)
        
        assert len(result) == 0
        assert len(factory._agent_list) == 0

class TestCleanupAllAgents:
    """Test cases for cleanup_all_agents method."""

    @pytest.mark.asyncio
    async def test_cleanup_all_agents_success(self, factory):
        """Test cleanup_all_agents with successful cleanup."""
        mock_agent1 = AsyncMock()
        mock_agent2 = AsyncMock()
        agent_list = [mock_agent1, mock_agent2]
        
        await MagenticAgentFactory.cleanup_all_agents(agent_list)
        
        mock_agent1.close.assert_called_once()
        mock_agent2.close.assert_called_once()
        assert len(agent_list) == 0

    @pytest.mark.asyncio
    async def test_cleanup_all_agents_with_exceptions(self, factory):
        """Test cleanup_all_agents when some agents raise exceptions."""
        mock_agent1 = AsyncMock()
        mock_agent2 = AsyncMock()
        mock_agent1.close.side_effect = Exception("Close error")
        
        agent_list = [mock_agent1, mock_agent2]
        
        # Should not raise exception despite agent1 error
        await MagenticAgentFactory.cleanup_all_agents(agent_list)
        
        mock_agent1.close.assert_called_once()
        mock_agent2.close.assert_called_once()
        assert len(agent_list) == 0

    @pytest.mark.asyncio
    async def test_cleanup_all_agents_empty_list(self, factory):
        """Test cleanup_all_agents with empty agent list."""
        agent_list = []
        
        await MagenticAgentFactory.cleanup_all_agents(agent_list)
        
        assert len(agent_list) == 0

class TestMagenticAgentFactoryErrors:
    """Test cases for error conditions."""

    def test_unsupported_model_error(self):
        """Test UnsupportedModelError creation."""
        error = UnsupportedModelError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_invalid_configuration_error(self):
        """Test InvalidConfigurationError creation."""
        error = InvalidConfigurationError("Test config error")
        assert str(error) == "Test config error"
        assert isinstance(error, Exception)

class TestMagenticAgentFactoryIntegration:
    """Integration test cases."""

    @pytest.mark.asyncio
    @patch('v4.magentic_agents.magentic_agent_factory.ProxyAgent')
    @patch('v4.magentic_agents.magentic_agent_factory.FoundryAgentTemplate')
    async def test_full_workflow(self, mock_foundry_class, mock_proxy_class, factory):
        """Test complete workflow from initialization to cleanup."""
        # Setup mocks
        mock_proxy_instance = Mock()
        mock_foundry_instance = AsyncMock()
        mock_proxy_class.return_value = mock_proxy_instance
        mock_foundry_class.return_value = mock_foundry_instance
        
        # Create agents
        agent_configs = [
            MockTeamAgent(name="proxyagent"),
            MockTeamAgent(name="TestAgent", deployment_name="gpt-4")
        ]
        team_config = MockTeamConfiguration(name="test_team", agents=agent_configs)
        user_id = "test_user"
        memory_store = Mock()
        
        # Get agents with proper config mocking
        with patch('v4.magentic_agents.magentic_agent_factory.config') as mock_config:
            mock_config.SUPPORTED_MODELS = '["gpt-4", "gpt-35-turbo"]'
            mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint"
            
            result = await factory.get_agents(user_id, team_config, memory_store)
        
        # Verify agents created
        assert len(result) == 2
        assert mock_proxy_instance in result
        assert mock_foundry_instance in result
        assert len(factory._agent_list) == 2
        
        # Cleanup
        await MagenticAgentFactory.cleanup_all_agents(factory._agent_list)
        
        # Verify cleanup
        mock_foundry_instance.close.assert_called_once()
        assert len(factory._agent_list) == 0

