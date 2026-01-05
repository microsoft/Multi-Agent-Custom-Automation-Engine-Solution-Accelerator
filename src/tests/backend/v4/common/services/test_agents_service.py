"""
Comprehensive unit tests for AgentsService.

This module contains extensive test coverage for:
- AgentsService initialization and configuration
- Agent descriptor creation from TeamConfiguration objects
- Agent descriptor creation from raw dictionaries
- Error handling and edge cases
- Different agent types and configurations
- Agent instantiation placeholder functionality
"""

import pytest
import os
import sys
import asyncio
import logging
import importlib.util
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass

# Add the src directory to sys.path for proper import
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
if src_path not in sys.path:
    sys.path.insert(0, os.path.abspath(src_path))

# Mock problematic modules and imports first
sys.modules['common.models.messages_af'] = MagicMock()
sys.modules['v4'] = MagicMock()
sys.modules['v4.common'] = MagicMock()
sys.modules['v4.common.services'] = MagicMock()
sys.modules['v4.common.services.team_service'] = MagicMock()

# Create mock data models for testing
class MockTeamAgent:
    """Mock TeamAgent class for testing."""
    def __init__(self, input_key, type, name, **kwargs):
        self.input_key = input_key
        self.type = type
        self.name = name
        self.system_message = kwargs.get('system_message', '')
        self.description = kwargs.get('description', '')
        self.icon = kwargs.get('icon', '')
        self.index_name = kwargs.get('index_name', '')
        self.use_rag = kwargs.get('use_rag', False)
        self.use_mcp = kwargs.get('use_mcp', False)
        self.coding_tools = kwargs.get('coding_tools', False)

class MockTeamConfiguration:
    """Mock TeamConfiguration class for testing."""
    def __init__(self, agents=None, **kwargs):
        self.agents = agents or []
        self.id = kwargs.get('id', 'test-id')
        self.name = kwargs.get('name', 'Test Team')
        self.status = kwargs.get('status', 'active')

class MockTeamService:
    """Mock TeamService class for testing."""
    def __init__(self):
        self.logger = logging.getLogger(__name__)

# Set up mock models
mock_messages_af = MagicMock()
mock_messages_af.TeamAgent = MockTeamAgent
mock_messages_af.TeamConfiguration = MockTeamConfiguration
sys.modules['common.models.messages_af'] = mock_messages_af

# Mock the TeamService module
mock_team_service_module = MagicMock()
mock_team_service_module.TeamService = MockTeamService
sys.modules['v4.common.services.team_service'] = mock_team_service_module

# Now import the real AgentsService using direct file import with proper mocking
import importlib.util

with patch.dict('sys.modules', {
    'common.models.messages_af': mock_messages_af,
    'v4.common.services.team_service': mock_team_service_module,
}):
    agents_service_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend', 'v4', 'common', 'services', 'agents_service.py')
    agents_service_path = os.path.abspath(agents_service_path)
    spec = importlib.util.spec_from_file_location("backend.v4.common.services.agents_service", agents_service_path)
    agents_service_module = importlib.util.module_from_spec(spec)
    
    # Set the proper module name for coverage tracking (matching --cov=backend pattern)
    agents_service_module.__name__ = "backend.v4.common.services.agents_service"
    agents_service_module.__file__ = agents_service_path
    
    # Add to sys.modules BEFORE execution for coverage tracking (both variations)
    sys.modules['backend.v4.common.services.agents_service'] = agents_service_module
    sys.modules['src.backend.v4.common.services.agents_service'] = agents_service_module
    
    spec.loader.exec_module(agents_service_module)

AgentsService = agents_service_module.AgentsService


class TestAgentsServiceInitialization:
    """Test cases for AgentsService initialization."""

    def test_init_with_team_service(self):
        """Test AgentsService initialization with a TeamService instance."""
        mock_team_service = MockTeamService()
        service = AgentsService(team_service=mock_team_service)
        
        assert service.team_service == mock_team_service
        assert service.logger is not None
        assert service.logger.name == "backend.v4.common.services.agents_service"

    def test_init_team_service_attribute(self):
        """Test that team_service attribute is properly set."""
        mock_team_service = MockTeamService()
        service = AgentsService(team_service=mock_team_service)
        
        # Verify team_service can be accessed and used
        assert hasattr(service, 'team_service')
        assert service.team_service is not None
        assert isinstance(service.team_service, MockTeamService)

    def test_init_logger_configuration(self):
        """Test that logger is properly configured."""
        mock_team_service = MockTeamService()
        service = AgentsService(team_service=mock_team_service)
        
        assert service.logger is not None
        assert isinstance(service.logger, logging.Logger)


class TestGetAgentsFromTeamConfig:
    """Test cases for get_agents_from_team_config method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_team_service = MockTeamService()
        self.service = AgentsService(team_service=self.mock_team_service)

    @pytest.mark.asyncio
    async def test_get_agents_empty_config(self):
        """Test with empty team config."""
        result = await self.service.get_agents_from_team_config(None)
        assert result == []
        
        result = await self.service.get_agents_from_team_config({})
        assert result == []

    @pytest.mark.asyncio
    async def test_get_agents_from_team_configuration_object(self):
        """Test with TeamConfiguration object containing agents."""
        agent1 = MockTeamAgent(
            input_key="agent1",
            type="ai",
            name="Test Agent 1",
            system_message="You are a helpful assistant",
            description="Test agent description",
            icon="robot-icon",
            index_name="test-index",
            use_rag=True,
            use_mcp=False,
            coding_tools=True
        )
        
        agent2 = MockTeamAgent(
            input_key="agent2",
            type="rag",
            name="RAG Agent",
            use_rag=True
        )
        
        team_config = MockTeamConfiguration(agents=[agent1, agent2])
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 2
        
        # Check first agent descriptor
        desc1 = result[0]
        assert desc1["input_key"] == "agent1"
        assert desc1["type"] == "ai"
        assert desc1["name"] == "Test Agent 1"
        assert desc1["system_message"] == "You are a helpful assistant"
        assert desc1["description"] == "Test agent description"
        assert desc1["icon"] == "robot-icon"
        assert desc1["index_name"] == "test-index"
        assert desc1["use_rag"] is True
        assert desc1["use_mcp"] is False
        assert desc1["coding_tools"] is True
        assert desc1["agent_obj"] is None
        
        # Check second agent descriptor
        desc2 = result[1]
        assert desc2["input_key"] == "agent2"
        assert desc2["type"] == "rag"
        assert desc2["name"] == "RAG Agent"
        assert desc2["use_rag"] is True
        assert desc2["agent_obj"] is None

    @pytest.mark.asyncio
    async def test_get_agents_from_dict_config(self):
        """Test with raw dictionary configuration."""
        team_config = {
            "agents": [
                {
                    "input_key": "dict_agent1",
                    "type": "ai",
                    "name": "Dictionary Agent 1",
                    "system_message": "System message from dict",
                    "description": "Dict agent description",
                    "icon": "dict-icon",
                    "index_name": "dict-index",
                    "use_rag": False,
                    "use_mcp": True,
                    "coding_tools": False
                },
                {
                    "input_key": "dict_agent2",
                    "type": "proxy",
                    "name": "Proxy Agent",
                    "instructions": "Use instructions field",  # Test instructions fallback
                    "use_rag": True
                }
            ]
        }
        
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 2
        
        # Check first agent descriptor
        desc1 = result[0]
        assert desc1["input_key"] == "dict_agent1"
        assert desc1["type"] == "ai"
        assert desc1["name"] == "Dictionary Agent 1"
        assert desc1["system_message"] == "System message from dict"
        assert desc1["description"] == "Dict agent description"
        assert desc1["icon"] == "dict-icon"
        assert desc1["index_name"] == "dict-index"
        assert desc1["use_rag"] is False
        assert desc1["use_mcp"] is True
        assert desc1["coding_tools"] is False
        assert desc1["agent_obj"] is None
        
        # Check second agent descriptor with instructions fallback
        desc2 = result[1]
        assert desc2["input_key"] == "dict_agent2"
        assert desc2["type"] == "proxy"
        assert desc2["name"] == "Proxy Agent"
        assert desc2["system_message"] == "Use instructions field"  # Instructions used as system_message
        assert desc2["use_rag"] is True

    @pytest.mark.asyncio
    async def test_get_agents_from_dict_with_missing_fields(self):
        """Test with dictionary containing agents with missing fields."""
        team_config = {
            "agents": [
                {
                    "input_key": "minimal_agent",
                    "type": "ai",
                    "name": "Minimal Agent"
                    # Missing other fields - should use defaults
                },
                {
                    # Missing required fields - should handle gracefully
                    "description": "Agent with minimal info"
                }
            ]
        }
        
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 2
        
        # Check first agent with minimal fields
        desc1 = result[0]
        assert desc1["input_key"] == "minimal_agent"
        assert desc1["type"] == "ai"
        assert desc1["name"] == "Minimal Agent"
        assert desc1["system_message"] is None  # get() returns None for missing keys
        assert desc1["description"] is None
        assert desc1["icon"] is None
        assert desc1["index_name"] is None
        assert desc1["use_rag"] is False
        assert desc1["use_mcp"] is False
        assert desc1["coding_tools"] is False
        assert desc1["agent_obj"] is None
        
        # Check second agent with missing required fields
        desc2 = result[1]
        assert desc2["input_key"] is None
        assert desc2["type"] is None
        assert desc2["name"] is None
        assert desc2["description"] == "Agent with minimal info"
        assert desc2["agent_obj"] is None

    @pytest.mark.asyncio
    async def test_get_agents_empty_agents_list(self):
        """Test with team config containing empty agents list."""
        team_config = {"agents": []}
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_agents_no_agents_key(self):
        """Test with team config not containing agents key."""
        team_config = {"name": "Team without agents"}
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_agents_team_config_none_agents(self):
        """Test with TeamConfiguration object having None agents."""
        team_config = MockTeamConfiguration(agents=None)
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_agents_mixed_agent_types(self):
        """Test with mixed TeamAgent objects and dict objects."""
        agent_obj = MockTeamAgent(
            input_key="obj_agent",
            type="ai",
            name="Object Agent",
            system_message="Object message"
        )
        
        agent_dict = {
            "input_key": "dict_agent",
            "type": "rag",
            "name": "Dict Agent",
            "system_message": "Dict message"
        }
        
        team_config = MockTeamConfiguration(agents=[agent_obj, agent_dict])
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 2
        
        # Both should be converted to the same descriptor format
        assert result[0]["input_key"] == "obj_agent"
        assert result[0]["name"] == "Object Agent"
        assert result[0]["system_message"] == "Object message"
        
        assert result[1]["input_key"] == "dict_agent"
        assert result[1]["name"] == "Dict Agent"
        assert result[1]["system_message"] == "Dict message"

    @pytest.mark.asyncio
    async def test_get_agents_unknown_object_types(self):
        """Test with unknown agent object types (fallback handling)."""
        unknown_agent = "unknown_string_agent"
        another_unknown = 12345
        
        team_config = MockTeamConfiguration(agents=[unknown_agent, another_unknown])
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 2
        
        # Unknown objects should be wrapped in raw descriptor
        assert result[0]["raw"] == "unknown_string_agent"
        assert result[0]["agent_obj"] is None
        
        assert result[1]["raw"] == 12345
        assert result[1]["agent_obj"] is None

    @pytest.mark.asyncio
    async def test_get_agents_instructions_fallback(self):
        """Test system_message fallback to instructions field."""
        team_config = {
            "agents": [
                {
                    "input_key": "agent1",
                    "type": "ai",
                    "name": "Agent 1",
                    "instructions": "Use instructions as system message"
                },
                {
                    "input_key": "agent2",
                    "type": "ai",
                    "name": "Agent 2",
                    "system_message": "Primary system message",
                    "instructions": "Should not be used"
                },
                {
                    "input_key": "agent3",
                    "type": "ai",
                    "name": "Agent 3",
                    "system_message": "",  # Empty string
                    "instructions": "Should use instructions"
                }
            ]
        }
        
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 3
        
        # First agent should use instructions as system_message
        assert result[0]["system_message"] == "Use instructions as system message"
        
        # Second agent should use system_message (not instructions)
        assert result[1]["system_message"] == "Primary system message"
        
        # Third agent with empty system_message should use instructions
        assert result[2]["system_message"] == "Should use instructions"

    @pytest.mark.asyncio
    async def test_get_agents_boolean_defaults(self):
        """Test that boolean fields have correct defaults."""
        team_config = {
            "agents": [
                {
                    "input_key": "agent_defaults",
                    "type": "ai",
                    "name": "Defaults Agent"
                    # No boolean fields specified
                }
            ]
        }
        
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        desc = result[0]
        
        # All boolean fields should default to False
        assert desc["use_rag"] is False
        assert desc["use_mcp"] is False
        assert desc["coding_tools"] is False

    @pytest.mark.asyncio
    async def test_get_agents_unknown_config_type_list_coercion(self):
        """Test handling of unknown config type with list coercion."""
        # Create a custom object that can be converted to a list
        class CustomConfig:
            def __iter__(self):
                return iter([{"input_key": "custom", "type": "test", "name": "Custom"}])
        
        custom_config = CustomConfig()
        result = await self.service.get_agents_from_team_config(custom_config)
        
        assert len(result) == 1
        assert result[0]["input_key"] == "custom"
        assert result[0]["name"] == "Custom"

    @pytest.mark.asyncio
    async def test_get_agents_unknown_config_type_exception(self):
        """Test handling of unknown config type that can't be converted."""
        # Object that can't be converted to a list
        non_iterable_config = 42
        result = await self.service.get_agents_from_team_config(non_iterable_config)
        
        # Should return empty list when conversion fails
        assert result == []


class TestInstantiateAgents:
    """Test cases for instantiate_agents placeholder method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_team_service = MockTeamService()
        self.service = AgentsService(team_service=self.mock_team_service)

    @pytest.mark.asyncio
    async def test_instantiate_agents_not_implemented(self):
        """Test that instantiate_agents raises NotImplementedError."""
        agent_descriptors = [
            {
                "input_key": "test_agent",
                "type": "ai",
                "name": "Test Agent",
                "agent_obj": None
            }
        ]
        
        with pytest.raises(NotImplementedError) as exc_info:
            await self.service.instantiate_agents(agent_descriptors)
        
        assert "Agent instantiation is not implemented in the skeleton" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_instantiate_agents_empty_list(self):
        """Test that instantiate_agents raises NotImplementedError even with empty list."""
        with pytest.raises(NotImplementedError):
            await self.service.instantiate_agents([])


class TestAgentsServiceIntegration:
    """Test cases for integration scenarios and edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_team_service = MockTeamService()
        self.service = AgentsService(team_service=self.mock_team_service)

    @pytest.mark.asyncio
    async def test_full_workflow_team_configuration(self):
        """Test complete workflow from TeamConfiguration to agent descriptors."""
        # Create comprehensive team configuration
        agents = [
            MockTeamAgent(
                input_key="coordinator",
                type="ai",
                name="Team Coordinator",
                system_message="You coordinate team activities",
                description="Main coordination agent",
                icon="coordinator-icon",
                use_rag=False,
                use_mcp=True,
                coding_tools=False
            ),
            MockTeamAgent(
                input_key="researcher",
                type="rag",
                name="Research Specialist",
                system_message="You conduct research using RAG",
                description="Research and information gathering",
                icon="research-icon",
                index_name="research-index",
                use_rag=True,
                use_mcp=False,
                coding_tools=False
            ),
            MockTeamAgent(
                input_key="coder",
                type="ai",
                name="Code Developer",
                system_message="You write and debug code",
                description="Software development specialist",
                icon="code-icon",
                use_rag=False,
                use_mcp=False,
                coding_tools=True
            )
        ]
        
        team_config = MockTeamConfiguration(
            agents=agents,
            name="Development Team",
            status="active"
        )
        
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 3
        
        # Verify each agent descriptor
        coordinator = result[0]
        assert coordinator["input_key"] == "coordinator"
        assert coordinator["type"] == "ai"
        assert coordinator["name"] == "Team Coordinator"
        assert coordinator["use_mcp"] is True
        assert coordinator["coding_tools"] is False
        
        researcher = result[1]
        assert researcher["input_key"] == "researcher"
        assert researcher["type"] == "rag"
        assert researcher["index_name"] == "research-index"
        assert researcher["use_rag"] is True
        
        coder = result[2]
        assert coder["input_key"] == "coder"
        assert coder["coding_tools"] is True

    @pytest.mark.asyncio
    async def test_full_workflow_dict_configuration(self):
        """Test complete workflow from dict configuration to agent descriptors."""
        team_config = {
            "name": "Marketing Team",
            "agents": [
                {
                    "input_key": "content_creator",
                    "type": "ai",
                    "name": "Content Creator",
                    "system_message": "You create marketing content",
                    "description": "Creates blog posts and marketing materials",
                    "icon": "content-icon",
                    "use_rag": True,
                    "use_mcp": False,
                    "coding_tools": False,
                    "index_name": "marketing-content-index"
                },
                {
                    "input_key": "analyst",
                    "type": "ai",
                    "name": "Marketing Analyst",
                    "instructions": "Analyze marketing data and trends",  # Using instructions
                    "description": "Data analysis and reporting",
                    "icon": "analyst-icon",
                    "use_rag": False,
                    "use_mcp": True,
                    "coding_tools": True
                }
            ]
        }
        
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 2
        
        # Verify content creator
        content_creator = result[0]
        assert content_creator["input_key"] == "content_creator"
        assert content_creator["name"] == "Content Creator"
        assert content_creator["system_message"] == "You create marketing content"
        assert content_creator["use_rag"] is True
        assert content_creator["index_name"] == "marketing-content-index"
        
        # Verify analyst with instructions fallback
        analyst = result[1]
        assert analyst["input_key"] == "analyst"
        assert analyst["name"] == "Marketing Analyst"
        assert analyst["system_message"] == "Analyze marketing data and trends"
        assert analyst["use_mcp"] is True
        assert analyst["coding_tools"] is True

    @pytest.mark.asyncio
    async def test_error_resilience(self):
        """Test service resilience to various error conditions."""
        # Test various invalid configurations that should work
        valid_empty_configs = [
            None,
            {},
            {"agents": []},
            {"name": "Team", "description": "No agents"},
            MockTeamConfiguration(agents=None),
            MockTeamConfiguration(agents=[])
        ]
        
        for config in valid_empty_configs:
            result = await self.service.get_agents_from_team_config(config)
            assert result == [], f"Failed for config: {config}"
        
        # Test configuration that causes TypeError (agents is None in dict)
        # This exposes a bug in the service but we test the actual behavior
        problematic_config = {"agents": None}
        
        with pytest.raises(TypeError, match="'NoneType' object is not iterable"):
            await self.service.get_agents_from_team_config(problematic_config)

    @pytest.mark.asyncio
    async def test_large_agent_list(self):
        """Test handling of large numbers of agents."""
        # Create a large number of agents
        agents = []
        for i in range(100):
            agent = MockTeamAgent(
                input_key=f"agent_{i}",
                type="ai",
                name=f"Agent {i}",
                system_message=f"System message {i}"
            )
            agents.append(agent)
        
        team_config = MockTeamConfiguration(agents=agents)
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 100
        
        # Verify a few random agents
        assert result[0]["input_key"] == "agent_0"
        assert result[50]["input_key"] == "agent_50"
        assert result[99]["input_key"] == "agent_99"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent calls to get_agents_from_team_config."""
        # Create multiple team configurations
        configs = []
        for i in range(5):
            agents = [
                MockTeamAgent(
                    input_key=f"agent_{i}_1",
                    type="ai",
                    name=f"Agent {i}-1"
                ),
                MockTeamAgent(
                    input_key=f"agent_{i}_2",
                    type="rag",
                    name=f"Agent {i}-2"
                )
            ]
            configs.append(MockTeamConfiguration(agents=agents))
        
        # Run concurrent operations
        tasks = [
            self.service.get_agents_from_team_config(config)
            for config in configs
        ]
        results = await asyncio.gather(*tasks)
        
        # Verify all results
        assert len(results) == 5
        for i, result in enumerate(results):
            assert len(result) == 2
            assert result[0]["input_key"] == f"agent_{i}_1"
            assert result[1]["input_key"] == f"agent_{i}_2"

    def test_service_attributes_access(self):
        """Test that service attributes are accessible."""
        mock_team_service = MockTeamService()
        service = AgentsService(team_service=mock_team_service)
        
        # Test team_service access
        assert service.team_service is not None
        assert service.team_service == mock_team_service
        
        # Test logger access
        assert service.logger is not None
        assert hasattr(service.logger, 'info')
        assert hasattr(service.logger, 'error')
        assert hasattr(service.logger, 'warning')

    @pytest.mark.asyncio
    async def test_descriptor_structure_completeness(self):
        """Test that all expected fields are present in agent descriptors."""
        agent = MockTeamAgent(
            input_key="complete_agent",
            type="ai",
            name="Complete Agent",
            system_message="Complete system message",
            description="Complete description",
            icon="complete-icon",
            index_name="complete-index",
            use_rag=True,
            use_mcp=True,
            coding_tools=True
        )
        
        team_config = MockTeamConfiguration(agents=[agent])
        result = await self.service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        desc = result[0]
        
        # Check all expected fields are present
        expected_fields = [
            "input_key", "type", "name", "system_message", "description",
            "icon", "index_name", "use_rag", "use_mcp", "coding_tools", "agent_obj"
        ]
        
        for field in expected_fields:
            assert field in desc, f"Missing field: {field}"
        
        # Verify agent_obj is always None in descriptors
        assert desc["agent_obj"] is None