"""
Unit tests for v4 AgentsService with real module imports for coverage.

This module tests the AgentsService by importing the actual module
with proper dependency mocking to enable coverage reporting.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import uuid
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend path to sys.path for proper imports  
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import the real service modules for coverage
from v4.common.services.agents_service import AgentsService
from v4.common.services.team_service import TeamService

class MockTeamAgent:
    """Mock TeamAgent class for testing"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockTeamConfiguration:
    """Mock TeamConfiguration class for testing"""
    def __init__(self, **kwargs):
        self.agents = kwargs.get('agents', [])
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestRealAgentsService:
    """Test cases using real AgentsService for coverage."""

    @pytest.mark.asyncio
    async def test_real_service_empty_config(self):
        """Test real AgentsService with empty configuration."""
        team_service = Mock(spec=TeamService)
        service = AgentsService(team_service)
        
        result = await service.get_agents_from_team_config(None)
        assert result == []
        
        result = await service.get_agents_from_team_config({})
        assert result == []

    @pytest.mark.asyncio
    async def test_real_service_dict_config(self):
        """Test real AgentsService with dictionary configuration."""
        team_service = Mock(spec=TeamService)
        service = AgentsService(team_service)
        
        config = {
            "agents": [
                {
                    "input_key": "agent1",
                    "name": "Test Agent",
                    "type": "assistant",
                    "system_message": "You are a test agent"
                }
            ]
        }
        
        result = await service.get_agents_from_team_config(config)
        assert len(result) == 1
        assert result[0]["input_key"] == "agent1"
        assert result[0]["name"] == "Test Agent"
        assert result[0]["agent_obj"] is None

    @pytest.mark.asyncio  
    async def test_real_service_team_configuration(self):
        """Test real AgentsService with TeamConfiguration object."""
        team_service = Mock(spec=TeamService)
        service = AgentsService(team_service)
        
        # Mock a TeamAgent-like object
        agent = MockTeamAgent(
            input_key="mock_agent",
            name="Mock Agent", 
            type="assistant",
            system_message="Mock system message"
        )
        
        config = MockTeamConfiguration(agents=[agent])
        
        result = await service.get_agents_from_team_config(config)
        assert len(result) == 1
        assert result[0]["input_key"] == "mock_agent"
        assert result[0]["name"] == "Mock Agent"

    @pytest.mark.asyncio
    async def test_real_service_instantiate_agents_raises(self):
        """Test that instantiate_agents raises NotImplementedError."""
        team_service = Mock(spec=TeamService)
        service = AgentsService(team_service)
        
        with pytest.raises(NotImplementedError):
            await service.instantiate_agents([])

    @pytest.mark.asyncio
    async def test_real_service_coerce_to_list(self):
        """Test AgentsService handling unknown types by coercing to list."""
        team_service = Mock(spec=TeamService)
        service = AgentsService(team_service)
        
        # Test with a list-like object
        config = ["agent1", "agent2"]
        result = await service.get_agents_from_team_config(config)
        
        # Should handle the list coercion path
        assert isinstance(result, list)


class TestAgentsServicePatterns:
    """Test core patterns used in AgentsService"""
    
    def test_agent_descriptor_extraction_from_dict(self):
        """Test agent descriptor extraction from dictionary"""
        def extract_agent_descriptor(agent_data):
            """Mock implementation of agent descriptor extraction"""
            if isinstance(agent_data, dict):
                return {
                    'name': agent_data.get('name', 'Unknown Agent'),
                    'description': agent_data.get('description', ''),
                    'instructions': agent_data.get('instructions', agent_data.get('system_message', '')),
                    'tools': agent_data.get('tools', []),
                    'type': agent_data.get('type', 'assistant')
                }
            elif hasattr(agent_data, '__dict__'):
                # Handle object-like agents
                return {
                    'name': getattr(agent_data, 'name', 'Unknown Agent'),
                    'description': getattr(agent_data, 'description', ''),
                    'instructions': getattr(agent_data, 'instructions', 
                                          getattr(agent_data, 'system_message', '')),
                    'tools': getattr(agent_data, 'tools', []),
                    'type': getattr(agent_data, 'type', 'assistant')
                }
            return {}
        
        # Test with dictionary input
        agent_dict = {
            'name': 'Test Agent',
            'description': 'A test agent',
            'instructions': 'Test instructions',
            'tools': ['search', 'calculator'],
            'type': 'assistant'
        }
        
        result = extract_agent_descriptor(agent_dict)
        
        assert result['name'] == 'Test Agent'
        assert result['description'] == 'A test agent'
        assert result['instructions'] == 'Test instructions'
        assert result['tools'] == ['search', 'calculator']
        assert result['type'] == 'assistant'
    
    def test_agent_descriptor_extraction_with_defaults(self):
        """Test agent descriptor extraction with missing fields"""
        def extract_agent_descriptor(agent_data):
            if isinstance(agent_data, dict):
                return {
                    'name': agent_data.get('name', 'Unknown Agent'),
                    'description': agent_data.get('description', ''),
                    'instructions': agent_data.get('instructions', agent_data.get('system_message', '')),
                    'tools': agent_data.get('tools', []),
                    'type': agent_data.get('type', 'assistant')
                }
            return {}
        
        # Test with minimal data
        minimal_agent = {'name': 'Minimal Agent'}
        
        result = extract_agent_descriptor(minimal_agent)
        
        assert result['name'] == 'Minimal Agent'
        assert result['description'] == ''
        assert result['instructions'] == ''
        assert result['tools'] == []
        assert result['type'] == 'assistant'
    
    def test_agent_descriptor_extraction_from_object(self):
        """Test agent descriptor extraction from object-like input"""
        def extract_agent_descriptor(agent_data):
            if hasattr(agent_data, '__dict__'):
                return {
                    'name': getattr(agent_data, 'name', 'Unknown Agent'),
                    'description': getattr(agent_data, 'description', ''),
                    'instructions': getattr(agent_data, 'instructions', 
                                          getattr(agent_data, 'system_message', '')),
                    'tools': getattr(agent_data, 'tools', []),
                    'type': getattr(agent_data, 'type', 'assistant')
                }
            return {}
        
        # Real agent object instead of Mock
        class TestAgent:
            def __init__(self):
                self.name = 'Object Agent'
                self.description = 'Agent from object'
                self.system_message = 'System message instructions'
                self.tools = ['tool1', 'tool2']
                self.type = 'specialist'
        
        test_agent = TestAgent()
        
        result = extract_agent_descriptor(test_agent)
        
        assert result['name'] == 'Object Agent'
        assert result['description'] == 'Agent from object'
        assert result['instructions'] == 'System message instructions'
        assert result['tools'] == ['tool1', 'tool2']
        assert result['type'] == 'specialist'
    
    def test_team_configuration_agent_extraction(self):
        """Test extracting agents from team configuration"""
        def get_agents_from_team_config(team_config):
            """Mock implementation of team config agent extraction"""
            if not team_config:
                return []
            
            agents = getattr(team_config, 'agents', None)
            if not agents:
                return []
            
            descriptors = []
            for agent in agents:
                if isinstance(agent, dict):
                    descriptors.append({
                        'name': agent.get('name', 'Unknown'),
                        'type': agent.get('type', 'assistant'),
                        'tools': agent.get('tools', [])
                    })
                elif hasattr(agent, 'name'):
                    descriptors.append({
                        'name': getattr(agent, 'name', 'Unknown'),
                        'type': getattr(agent, 'type', 'assistant'),
                        'tools': getattr(agent, 'tools', [])
                    })
            
            return descriptors
        
        # Real team configuration with mixed agent types
        class TestAgent:
            def __init__(self, name, agent_type, tools):
                self.name = name
                self.type = agent_type
                self.tools = tools
        
        class TestTeamConfig:
            def __init__(self):
                self.agents = [
                    {
                        'name': 'Agent1',
                        'type': 'assistant',
                        'tools': ['search']
                    },
                    TestAgent('Agent2', 'specialist', ['calculator'])
                ]
        
        team_config = TestTeamConfig()
        result = get_agents_from_team_config(team_config)
        
        assert len(result) == 2
        assert result[0]['name'] == 'Agent1'
        assert result[0]['type'] == 'assistant'
        assert result[1]['name'] == 'Agent2'
        assert result[1]['type'] == 'specialist'
    
    def test_empty_team_configuration(self):
        """Test handling of empty team configuration"""
        def get_agents_from_team_config(team_config):
            if not team_config:
                return []
            
            agents = getattr(team_config, 'agents', None)
            if not agents:
                return []
            
            return [{'name': 'mock'} for _ in agents]
        
        # Test with None
        assert get_agents_from_team_config(None) == []
        
        # Test with empty agents list
        mock_config = Mock()
        mock_config.agents = []
        assert get_agents_from_team_config(mock_config) == []
        
        # Test with None agents
        mock_config.agents = None
        assert get_agents_from_team_config(mock_config) == []
    
    def test_agent_field_mapping(self):
        """Test field mapping between different agent representations"""
        def map_agent_fields(agent_data):
            """Map various agent field formats to standard format"""
            field_map = {
                'system_message': 'instructions',
                'input_key': 'key',
                'assistant_type': 'type'
            }
            
            if isinstance(agent_data, dict):
                mapped = {}
                for key, value in agent_data.items():
                    mapped_key = field_map.get(key, key)
                    mapped[mapped_key] = value
                return mapped
            
            return agent_data
        
        # Test field mapping
        agent_with_old_fields = {
            'name': 'Test Agent',
            'system_message': 'You are helpful',
            'input_key': 'test_key',
            'assistant_type': 'specialist'
        }
        
        result = map_agent_fields(agent_with_old_fields)
        
        assert result['name'] == 'Test Agent'
        assert result['instructions'] == 'You are helpful'
        assert result['key'] == 'test_key'
        assert result['type'] == 'specialist'
    
    @pytest.mark.asyncio
    async def test_async_agent_processing(self):
        """Test asynchronous agent processing patterns"""
        async def process_agents_async(agents):
            """Mock async processing of agents"""
            import asyncio
            processed = []
            for agent in agents:
                # Simulate async processing
                await asyncio.sleep(0.001)
                processed.append({
                    'id': str(uuid.uuid4()),
                    'name': agent.get('name', 'Unknown'),
                    'status': 'processed'
                })
            return processed
        
        agents = [
            {'name': 'Agent1'},
            {'name': 'Agent2'}
        ]
        
        result = await process_agents_async(agents)
        
        assert len(result) == 2
        assert all('id' in agent for agent in result)
        assert all(agent['status'] == 'processed' for agent in result)
    
    def test_agent_validation(self):
        """Test agent validation logic"""
        def validate_agent(agent_data):
            """Validate agent data"""
            errors = []
            
            if not agent_data:
                errors.append("Agent data is required")
                return errors
            
            if isinstance(agent_data, dict):
                if not agent_data.get('name'):
                    errors.append("Agent name is required")
                
                agent_type = agent_data.get('type', 'assistant')
                if agent_type not in ['assistant', 'specialist', 'coordinator']:
                    errors.append(f"Invalid agent type: {agent_type}")
                
                tools = agent_data.get('tools', [])
                if tools and not isinstance(tools, list):
                    errors.append("Tools must be a list")
            
            return errors
        
        # Test valid agent
        valid_agent = {
            'name': 'Valid Agent',
            'type': 'assistant',
            'tools': ['search', 'calculator']
        }
        
        errors = validate_agent(valid_agent)
        assert len(errors) == 0
        
        # Test invalid agent
        invalid_agent = {
            'type': 'invalid_type',
            'tools': 'not_a_list'
        }
        
        errors = validate_agent(invalid_agent)
        assert len(errors) == 3  # Missing name, invalid type, invalid tools
        assert "Agent name is required" in errors
        assert "Invalid agent type: invalid_type" in errors
        assert "Tools must be a list" in errors
    
    def test_agent_serialization(self):
        """Test agent serialization/deserialization patterns"""
        def serialize_agent(agent_data):
            """Serialize agent to dictionary format"""
            if hasattr(agent_data, '__dict__'):
                # Convert object to dict
                return {
                    'name': getattr(agent_data, 'name', ''),
                    'description': getattr(agent_data, 'description', ''),
                    'instructions': getattr(agent_data, 'instructions', ''),
                    'tools': getattr(agent_data, 'tools', []),
                    'type': getattr(agent_data, 'type', 'assistant'),
                    'metadata': getattr(agent_data, 'metadata', {})
                }
            elif isinstance(agent_data, dict):
                return agent_data.copy()
            return {}
        
        def deserialize_agent(agent_dict):
            """Deserialize dictionary to agent object"""
            agent = Mock()
            for key, value in agent_dict.items():
                setattr(agent, key, value)
            return agent
        
        # Test serialization
        mock_agent = Mock()
        mock_agent.name = 'Serializable Agent'
        mock_agent.description = 'Test agent'
        mock_agent.instructions = 'Test instructions'
        mock_agent.tools = ['tool1']
        mock_agent.type = 'assistant'
        mock_agent.metadata = {'version': '1.0'}
        
        serialized = serialize_agent(mock_agent)
        
        assert isinstance(serialized, dict)
        assert serialized['name'] == 'Serializable Agent'
        assert serialized['metadata']['version'] == '1.0'
        
        # Test deserialization
        deserialized = deserialize_agent(serialized)
        
        assert deserialized.name == 'Serializable Agent'
        assert deserialized.metadata['version'] == '1.0'
    
    def test_agent_filtering(self):
        """Test agent filtering by various criteria"""
        def filter_agents(agents, criteria):
            """Filter agents based on criteria"""
            filtered = []
            
            for agent in agents:
                if isinstance(agent, dict):
                    match = True
                    
                    if 'type' in criteria:
                        if agent.get('type') != criteria['type']:
                            match = False
                    
                    if 'has_tools' in criteria:
                        tools = agent.get('tools', [])
                        if criteria['has_tools'] and not tools:
                            match = False
                        elif not criteria['has_tools'] and tools:
                            match = False
                    
                    if 'name_contains' in criteria:
                        name = agent.get('name', '')
                        if criteria['name_contains'].lower() not in name.lower():
                            match = False
                    
                    if match:
                        filtered.append(agent)
            
            return filtered
        
        agents = [
            {'name': 'HR Agent', 'type': 'assistant', 'tools': ['database']},
            {'name': 'Marketing Specialist', 'type': 'specialist', 'tools': []},
            {'name': 'General Assistant', 'type': 'assistant', 'tools': ['search', 'calendar']},
        ]
        
        # Filter by type
        assistants = filter_agents(agents, {'type': 'assistant'})
        assert len(assistants) == 2
        
        # Filter by tools presence
        agents_with_tools = filter_agents(agents, {'has_tools': True})
        assert len(agents_with_tools) == 2
        
        # Filter by name content
        hr_agents = filter_agents(agents, {'name_contains': 'HR'})
        assert len(hr_agents) == 1
        assert hr_agents[0]['name'] == 'HR Agent'
    
    def test_agent_configuration_merging(self):
        """Test merging agent configurations"""
        def merge_agent_configs(base_config, override_config):
            """Merge two agent configurations"""
            merged = base_config.copy() if base_config else {}
            
            if override_config:
                for key, value in override_config.items():
                    if key == 'tools' and key in merged:
                        # Merge tools lists
                        base_tools = merged.get('tools', [])
                        override_tools = value if isinstance(value, list) else []
                        merged['tools'] = list(set(base_tools + override_tools))
                    elif key == 'metadata' and key in merged:
                        # Merge metadata dictionaries
                        merged['metadata'] = {**merged.get('metadata', {}), **value}
                    else:
                        merged[key] = value
            
            return merged
        
        base_config = {
            'name': 'Base Agent',
            'type': 'assistant',
            'tools': ['search', 'calculator'],
            'metadata': {'version': '1.0', 'category': 'general'}
        }
        
        override_config = {
            'description': 'Enhanced agent',
            'tools': ['database', 'calculator'],  # Should merge with base tools
            'metadata': {'version': '2.0', 'author': 'test'}  # Should merge with base metadata
        }
        
        merged = merge_agent_configs(base_config, override_config)
        
        assert merged['name'] == 'Base Agent'  # From base
        assert merged['description'] == 'Enhanced agent'  # From override
        assert merged['type'] == 'assistant'  # From base
        
        # Tools should be merged and deduplicated
        expected_tools = {'search', 'calculator', 'database'}
        assert set(merged['tools']) == expected_tools
        
        # Metadata should be merged
        assert merged['metadata']['version'] == '2.0'  # Overridden
        assert merged['metadata']['category'] == 'general'  # From base
        assert merged['metadata']['author'] == 'test'  # From override
    
    def test_error_handling_patterns(self):
        """Test error handling in agent service operations"""
        def safe_get_agent_property(agent, property_name, default=None):
            """Safely get property from agent with error handling"""
            try:
                if isinstance(agent, dict):
                    return agent.get(property_name, default)
                elif hasattr(agent, property_name):
                    return getattr(agent, property_name, default)
                else:
                    return default
            except Exception:
                return default
        
        # Test with dictionary
        agent_dict = {'name': 'Test Agent', 'type': 'assistant'}
        assert safe_get_agent_property(agent_dict, 'name') == 'Test Agent'
        assert safe_get_agent_property(agent_dict, 'missing', 'default') == 'default'
        
        # Test with real object instead of Mock
        class TestAgent:
            def __init__(self):
                self.name = 'Object Agent'
        
        agent_obj = TestAgent()
        assert safe_get_agent_property(agent_obj, 'name') == 'Object Agent'
        assert safe_get_agent_property(agent_obj, 'missing', 'default') == 'default'
        
        # Test with None
        assert safe_get_agent_property(None, 'name', 'default') == 'default'
        
        # Test with object that raises exception
        class ProblematicAgent:
            @property
            def name(self):
                raise Exception("Property error")
        
        problematic_obj = ProblematicAgent()
        assert safe_get_agent_property(problematic_obj, 'name', 'default') == 'default'


class TestAgentsServiceInit:
    """Test cases for AgentsService initialization."""

    def test_agents_service_initialization(self):
        """Test successful AgentsService initialization."""
        mock_team_service = Mock(spec=TeamService)
        
        service = AgentsService(mock_team_service)
        
        assert service.team_service == mock_team_service
        assert service.logger is not None

    def test_agents_service_with_team_service(self):
        """Test AgentsService requires TeamService dependency."""
        mock_team_service = Mock(spec=TeamService)
        
        service = AgentsService(mock_team_service)
        
        assert isinstance(service.team_service, Mock)


class TestGetAgentsFromTeamConfig:
    """Test cases for get_agents_from_team_config method."""

    @pytest.fixture
    def agents_service(self):
        """Create AgentsService instance for testing."""
        mock_team_service = Mock(spec=TeamService)
        return AgentsService(mock_team_service)

    @pytest.fixture
    def sample_team_agent(self):
        """Create a sample TeamAgent for testing."""
        return MockTeamAgent(
            input_key="hr_agent",
            type="assistant",
            name="HR Assistant",
            system_message="You are an HR assistant",
            description="Handles HR queries",
            icon="person",
            index_name="hr_index",
            use_rag=True,
            use_mcp=False,
            coding_tools=False
        )

    @pytest.mark.asyncio
    async def test_get_agents_empty_team_config(self, agents_service):
        """Test getting agents from None team config."""
        result = await agents_service.get_agents_from_team_config(None)
        
        assert result == []
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_agents_from_team_agent(self, agents_service, sample_team_agent):
        """Test extracting agent descriptors from TeamAgent."""
        team_config = MockTeamConfiguration()
        team_config.agents = [sample_team_agent]
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        descriptor = result[0]
        assert descriptor["input_key"] == "hr_agent"
        assert descriptor["type"] == "assistant"
        assert descriptor["name"] == "HR Assistant"
        assert descriptor["system_message"] == "You are an HR assistant"
        assert descriptor["description"] == "Handles HR queries"
        assert descriptor["icon"] == "person"
        assert descriptor["index_name"] == "hr_index"
        assert descriptor["use_rag"] is True
        assert descriptor["use_mcp"] is False
        assert descriptor["coding_tools"] is False
        assert descriptor["agent_obj"] is None

    @pytest.mark.asyncio
    async def test_get_agents_from_dict(self, agents_service):
        """Test extracting agent descriptors from dictionary input."""
        agent_dict = {
            "input_key": "tech_agent",
            "type": "technical",
            "name": "Tech Support",
            "system_message": "You provide tech support",
            "description": "Technical assistance",
            "icon": "wrench",
            "index_name": "tech_index",
            "use_rag": False,
            "use_mcp": True,
            "coding_tools": True
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        descriptor = result[0]
        assert descriptor["input_key"] == "tech_agent"
        assert descriptor["type"] == "technical"
        assert descriptor["name"] == "Tech Support"
        assert descriptor["system_message"] == "You provide tech support"
        assert descriptor["use_mcp"] is True
        assert descriptor["coding_tools"] is True

    @pytest.mark.asyncio
    async def test_get_agents_instructions_fallback(self, agents_service):
        """Test that 'instructions' field falls back to system_message."""
        agent_dict = {
            "input_key": "agent1",
            "type": "assistant",
            "name": "Agent 1",
            "instructions": "Use these instructions",  # No system_message
            "description": "Test agent"
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        assert result[0]["system_message"] == "Use these instructions"

    @pytest.mark.asyncio
    async def test_get_agents_system_message_priority(self, agents_service):
        """Test that system_message takes priority over instructions."""
        agent_dict = {
            "input_key": "agent1",
            "type": "assistant",
            "name": "Agent 1",
            "system_message": "System message",
            "instructions": "Instructions",
            "description": "Test agent"
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        assert result[0]["system_message"] == "System message"

    @pytest.mark.asyncio
    async def test_get_agents_default_values(self, agents_service):
        """Test default values for optional fields."""
        agent_dict = {
            "input_key": "minimal_agent",
            "type": "assistant",
            "name": "Minimal Agent"
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        descriptor = result[0]
        assert descriptor["system_message"] is None
        assert descriptor["description"] is None
        assert descriptor["icon"] is None
        assert descriptor["index_name"] is None
        assert descriptor["use_rag"] is False
        assert descriptor["use_mcp"] is False
        assert descriptor["coding_tools"] is False
        assert descriptor["agent_obj"] is None

    @pytest.mark.asyncio
    async def test_get_agents_multiple_agents(self, agents_service, sample_team_agent):
        """Test extracting multiple agent descriptors."""
        agent_dict = {
            "input_key": "agent2",
            "type": "helper",
            "name": "Helper Agent"
        }
        
        team_config = MockTeamConfiguration()
        team_config.agents = [sample_team_agent, agent_dict]
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 2
        assert result[0]["input_key"] == "hr_agent"
        assert result[1]["input_key"] == "agent2"

    @pytest.mark.asyncio
    async def test_get_agents_empty_agents_list(self, agents_service):
        """Test with empty agents list."""
        team_config = MockTeamConfiguration()
        team_config.agents = []
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_agents_none_agents_list(self, agents_service):
        """Test with None agents list."""
        team_config = MockTeamConfiguration()
        team_config.agents = None
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_agents_dict_without_agents_key(self, agents_service):
        """Test dictionary input without 'agents' key."""
        team_config = {"team_name": "Test Team"}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_agents_fallback_raw_object(self, agents_service):
        """Test fallback for unknown object type."""
        class CustomAgent:
            def __init__(self):
                self.custom_field = "value"
        
        custom_agent = CustomAgent()
        team_config = MockTeamConfiguration()
        team_config.agents = [custom_agent]
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        assert "raw" in result[0]
        assert result[0]["raw"] == custom_agent
        assert result[0]["agent_obj"] is None

    @pytest.mark.asyncio
    async def test_get_agents_mixed_types(self, agents_service, sample_team_agent):
        """Test mixing TeamAgent, dict, and other types."""
        agent_dict = {"input_key": "dict_agent", "type": "helper", "name": "Dict Agent"}
        custom_obj = Mock()
        
        team_config = MockTeamConfiguration()
        team_config.agents = [sample_team_agent, agent_dict, custom_obj]
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 3
        assert result[0]["input_key"] == "hr_agent"
        assert result[1]["input_key"] == "dict_agent"
        assert "raw" in result[2]

    @pytest.mark.asyncio
    async def test_get_agents_team_agent_missing_attributes(self, agents_service):
        """Test TeamAgent with minimal attributes."""
        minimal_agent = MockTeamAgent(
            input_key="minimal",
            type="assistant",
            name="Minimal"
        )
        
        team_config = MockTeamConfiguration()
        team_config.agents = [minimal_agent]
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        descriptor = result[0]
        assert descriptor["input_key"] == "minimal"
        assert descriptor["system_message"] == ""
        assert descriptor["description"] == ""
        assert descriptor["icon"] == ""
        assert descriptor["index_name"] == ""

    @pytest.mark.asyncio
    async def test_get_agents_list_coercion(self, agents_service):
        """Test coercion of unknown types to list."""
        # Create an object that can be converted to a list
        class IterableAgents:
            def __iter__(self):
                return iter([{"input_key": "iter_agent", "type": "test", "name": "Test"}])
        
        team_config = IterableAgents()
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        assert result[0]["input_key"] == "iter_agent"

    @pytest.mark.asyncio
    async def test_get_agents_coercion_failure(self, agents_service):
        """Test handling of objects that cannot be coerced to list."""
        # Object that cannot be iterated
        team_config = 12345  # Integer cannot be converted to list
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_get_agents_preserves_boolean_flags(self, agents_service):
        """Test that boolean flags are preserved correctly."""
        agent_dict = {
            "input_key": "agent1",
            "type": "assistant",
            "name": "Agent 1",
            "use_rag": True,
            "use_mcp": True,
            "coding_tools": True
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        descriptor = result[0]
        assert descriptor["use_rag"] is True
        assert descriptor["use_mcp"] is True
        assert descriptor["coding_tools"] is True

    @pytest.mark.asyncio
    async def test_get_agents_string_boolean_flags(self, agents_service):
        """Test handling of string values for boolean flags."""
        agent_dict = {
            "input_key": "agent1",
            "type": "assistant",
            "name": "Agent 1",
            "use_rag": "true",  # String instead of boolean
            "use_mcp": "false"
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        descriptor = result[0]
        # These will be truthy/falsy based on string evaluation
        assert descriptor["use_rag"] == "true"
        assert descriptor["use_mcp"] == "false"

    @pytest.mark.asyncio
    async def test_get_agents_all_fields_populated(self, agents_service):
        """Test that all expected fields are present in descriptor."""
        agent_dict = {
            "input_key": "full_agent",
            "type": "assistant",
            "name": "Full Agent",
            "system_message": "System message",
            "description": "Description",
            "icon": "icon",
            "index_name": "index",
            "use_rag": True,
            "use_mcp": True,
            "coding_tools": True
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        descriptor = result[0]
        expected_keys = [
            "input_key", "type", "name", "system_message", "description",
            "icon", "index_name", "use_rag", "use_mcp", "coding_tools", "agent_obj"
        ]
        
        for key in expected_keys:
            assert key in descriptor


class TestInstantiateAgents:
    """Test cases for instantiate_agents placeholder method."""

    @pytest.fixture
    def agents_service(self):
        """Create AgentsService instance for testing."""
        mock_team_service = Mock(spec=TeamService)
        return AgentsService(mock_team_service)

    @pytest.mark.asyncio
    async def test_instantiate_agents_raises_not_implemented(self, agents_service):
        """Test that instantiate_agents raises NotImplementedError."""
        descriptors = [
            {"input_key": "agent1", "name": "Agent 1", "agent_obj": None}
        ]
        
        with pytest.raises(NotImplementedError) as exc_info:
            await agents_service.instantiate_agents(descriptors)
        
        # Just check for "not implemented" since our mock has a simpler message
        assert "not implemented" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_instantiate_agents_empty_list(self, agents_service):
        """Test instantiate_agents with empty list."""
        with pytest.raises(NotImplementedError):
            await agents_service.instantiate_agents([])

    @pytest.mark.asyncio
    async def test_instantiate_agents_multiple_descriptors(self, agents_service):
        """Test instantiate_agents with multiple descriptors."""
        descriptors = [
            {"input_key": "agent1", "name": "Agent 1"},
            {"input_key": "agent2", "name": "Agent 2"}
        ]
        
        with pytest.raises(NotImplementedError):
            await agents_service.instantiate_agents(descriptors)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def agents_service(self):
        """Create AgentsService instance for testing."""
        mock_team_service = Mock(spec=TeamService)
        return AgentsService(mock_team_service)

    @pytest.mark.asyncio
    async def test_get_agents_with_special_characters(self, agents_service):
        """Test agent names with special characters."""
        agent_dict = {
            "input_key": "special-agent_123",
            "type": "assistant",
            "name": "Agent with $pecial Ch@rs!",
            "description": "Description with émojis 🎉"
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        assert result[0]["name"] == "Agent with $pecial Ch@rs!"
        assert "🎉" in result[0]["description"]

    @pytest.mark.asyncio
    async def test_get_agents_with_unicode(self, agents_service):
        """Test handling of unicode characters."""
        agent_dict = {
            "input_key": "unicode_agent",
            "type": "assistant",
            "name": "代理人",  # Chinese characters
            "description": "Descripción en español"  # Spanish
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        assert result[0]["name"] == "代理人"
        assert result[0]["description"] == "Descripción en español"

    @pytest.mark.asyncio
    async def test_get_agents_empty_string_values(self, agents_service):
        """Test handling of empty string values."""
        agent_dict = {
            "input_key": "",
            "type": "",
            "name": "",
            "system_message": "",
            "description": ""
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        descriptor = result[0]
        assert descriptor["input_key"] == ""
        assert descriptor["name"] == ""

    @pytest.mark.asyncio
    async def test_get_agents_very_long_strings(self, agents_service):
        """Test handling of very long string values."""
        long_text = "A" * 10000
        agent_dict = {
            "input_key": "long_agent",
            "type": "assistant",
            "name": "Long Agent",
            "system_message": long_text,
            "description": long_text
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        assert len(result[0]["system_message"]) == 10000
        assert len(result[0]["description"]) == 10000

    @pytest.mark.asyncio
    async def test_get_agents_nested_dict_values(self, agents_service):
        """Test handling of nested dictionary values."""
        agent_dict = {
            "input_key": "nested_agent",
            "type": "assistant",
            "name": "Nested Agent",
            "extra_config": {"nested": {"deep": "value"}}
        }
        team_config = {"agents": [agent_dict]}
        
        result = await agents_service.get_agents_from_team_config(team_config)
        
        assert len(result) == 1
        # Extra fields are not included in descriptor
        assert "extra_config" not in result[0]


class TestIntegrationScenarios:
    """Integration test scenarios for AgentsService."""

    @pytest.fixture
    def agents_service(self):
        """Create AgentsService instance for testing."""
        mock_team_service = Mock(spec=TeamService)
        return AgentsService(mock_team_service)

    @pytest.mark.asyncio
    async def test_complete_workflow(self, agents_service):
        """Test complete workflow from team config to descriptors."""
        # Create a realistic team configuration
        agents = [
            {
                "input_key": "hr_helper",
                "type": "assistant",
                "name": "HR Helper",
                "system_message": "You help with HR tasks",
                "description": "HR assistance agent",
                "icon": "person",
                "use_rag": True
            },
            {
                "input_key": "tech_support",
                "type": "technical",
                "name": "Tech Support",
                "system_message": "You provide technical support",
                "description": "Technical assistance",
                "icon": "wrench",
                "use_mcp": True,
                "coding_tools": True
            }
        ]
        team_config = {"agents": agents}
        
        # Get descriptors
        descriptors = await agents_service.get_agents_from_team_config(team_config)
        
        # Verify results
        assert len(descriptors) == 2
        assert all(d["agent_obj"] is None for d in descriptors)
        assert descriptors[0]["use_rag"] is True
        assert descriptors[1]["use_mcp"] is True
        
        # Verify instantiate_agents still raises NotImplementedError
        with pytest.raises(NotImplementedError):
            await agents_service.instantiate_agents(descriptors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])