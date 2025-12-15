"""
Unit tests for v4 TeamService with real class import for coverage.

Tests cover:
- Team configuration validation and parsing
- Team service initialization  
- Error handling and edge cases
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
import uuid
from dataclasses import dataclass

# Add backend path to sys.path for proper imports  
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import necessary models for tests
from common.models.messages_af import TeamAgent, TeamConfiguration, StartingTask

# Import real TeamService for coverage
from v4.common.services.team_service import TeamService

# Mock Azure exceptions
class ClientAuthenticationError(Exception):
    pass

class HttpResponseError(Exception):
    pass

class ResourceNotFoundError(Exception):
    pass

# Mock common.models.messages_af classes
@dataclass
class StartingTask:
    id: str
    name: str
    prompt: str
    created: str
    creator: str
    logo: str

@dataclass
class UserCurrentTeam:
    user_id: str
    team_configuration_id: str
    team_configuration: Any
    selected_at: str


class TestRealTeamService:
    """Test cases using real TeamService for coverage."""

    def test_real_team_service_init_default(self):
        """Test TeamService initialization with default parameters."""
        with patch('v4.common.services.team_service.config') as mock_config:
            mock_config.AZURE_SEARCH_ENDPOINT = "https://test.search.windows.net"
            mock_config.get_azure_credentials = Mock(return_value="mock_creds")
            
            service = TeamService()
            
            assert service.memory_context is None
            assert hasattr(service, 'logger')
            assert service.search_endpoint == "https://test.search.windows.net"
            assert service.search_credential == "mock_creds"

    def test_real_team_service_init_with_memory(self):
        """Test TeamService initialization with memory context."""
        mock_memory = Mock()
        
        with patch('v4.common.services.team_service.config') as mock_config:
            mock_config.AZURE_SEARCH_ENDPOINT = "https://test.search.windows.net"
            mock_config.get_azure_credentials = Mock(return_value="mock_creds")
            
            service = TeamService(memory_context=mock_memory)
            
            assert service.memory_context is mock_memory
            assert hasattr(service, 'logger')

    @pytest.mark.asyncio
    async def test_real_validate_and_parse_team_config_basic(self):
        """Test real validate_and_parse_team_config with basic valid data."""
        with patch('v4.common.services.team_service.config') as mock_config:
            mock_config.AZURE_SEARCH_ENDPOINT = "https://test.search.windows.net"
            mock_config.get_azure_credentials = Mock(return_value="mock_creds")
            
            service = TeamService()
            
            # Mock the dependencies
            with patch('v4.common.services.team_service.TeamConfiguration') as mock_team_config:
                mock_team_config.return_value = Mock()
                
                test_data = {
                    "name": "Test Team",
                    "agents": []
                }
                
                # Mock validation methods that will be called
                with patch.object(service, '_validate_team_structure') as mock_validate:
                    result = await service.validate_and_parse_team_config(test_data, "user123")
                    
                    # Verify validation was called
                    mock_validate.assert_called_once_with(test_data)
                    
                    # Verify TeamConfiguration was instantiated
                    mock_team_config.assert_called_once()
    deployment_name: str
    system_message: str = ""
    description: str = ""
    icon: str = ""
    index_name: str = ""
    use_rag: bool = False
    use_mcp: bool = False
    use_bing: bool = False
    use_reasoning: bool = False
    coding_tools: bool = False

@dataclass
class TeamConfiguration:
    team_id: str
    session_id: str
    name: str
    status: str
    created: str
    created_by: str
    deployment_name: str
    user_id: str
    id: Optional[str] = None
    agents: Optional[List[TeamAgent]] = None
    description: str = ""
    logo: str = ""
    plan: str = ""
    starting_tasks: Optional[List[StartingTask]] = None
    data_type: Optional[str] = "team_config"

@dataclass
class UserCurrentTeam:
    user_id: str
    team_id: str
    team_name: str = ""
    data_type: Optional[str] = "user_current_team"

# REMOVED: Massive sys.modules pollution that causes isinstance() failures across test files
# Each test should use @patch decorators for its specific mocking needs

# Restore minimal required module structure for test functionality
import types
if 'v4.common.services' not in sys.modules:
    sys.modules['v4.common.services'] = types.ModuleType('v4.common.services')
sys.modules['common.database'].database_base = Mock()

# Read and exec the team_service.py file
team_service_path = Path(__file__).parent.parent.parent.parent.parent.parent / "backend" / "v4" / "common" / "services" / "team_service.py"
team_service_content = team_service_path.read_text()

# Replace imports
modified_content = team_service_content.replace(
    "from azure.core.exceptions import (",
    "# azure.core.exceptions imported via mock #("
).replace(
    "from azure.search.documents.indexes import SearchIndexClient",
    "# SearchIndexClient imported via mock"
).replace(
    "from common.config.app_config import config",
    "# config imported via mock"
).replace(
    "from common.database.database_base import DatabaseBase",
    "# DatabaseBase imported via mock"
).replace(
    "from common.models.messages_af import (",
    "# messages_af imported via mock #("
).replace(
    "from v4.common.services.foundry_service import FoundryService",
    "# FoundryService imported via mock"
)

# Remove commented import lines
import re
modified_content = re.sub(r'# azure\.core\.exceptions imported via mock #\([^)]+\)', '', modified_content)
modified_content = re.sub(r'# messages_af imported via mock #\([^)]+\)', '', modified_content)

# Create namespace for exec
team_namespace = {
    'logging': logging,
    'uuid': uuid,
    'datetime': datetime,
    'timezone': timezone,
    'Optional': Optional,
    'Any': Any,
    'Dict': Dict,
    'List': List,
    'Tuple': Tuple,
    'ClientAuthenticationError': ClientAuthenticationError,
    'HttpResponseError': HttpResponseError,
    'ResourceNotFoundError': ResourceNotFoundError,
    'SearchIndexClient': Mock,
    'config': Mock(),
    'DatabaseBase': Mock,
    'StartingTask': StartingTask,
    'TeamAgent': TeamAgent,
    'TeamConfiguration': TeamConfiguration,
    'UserCurrentTeam': UserCurrentTeam,
    'FoundryService': Mock,
}

exec(modified_content, team_namespace)

# Extract TeamService
TeamService = team_namespace['TeamService']

# Create mock module for patches
team_service_module = type(sys)('team_service')
team_service_module.TeamService = TeamService
team_service_module.config = Mock()
team_service_module.SearchIndexClient = Mock
team_service_module.FoundryService = Mock
sys.modules['v4.common.services'].team_service = team_service_module


class TestTeamServiceInit:
    """Test cases for TeamService initialization."""

    @patch("v4.common.services.team_service.config")
    def test_init_without_memory_context(self, mock_config):
        """Test initialization without memory context."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        service = TeamService()
        
        assert service.memory_context is None
        # Note: search_endpoint gets mock_config.AZURE_SEARCH_ENDPOINT, which is a Mock attribute
        assert service.logger is not None

    @patch("v4.common.services.team_service.config")
    def test_init_with_memory_context(self, mock_config):
        """Test initialization with memory context."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        mock_memory = Mock()
        
        service = TeamService(memory_context=mock_memory)
        
        assert service.memory_context == mock_memory


class TestValidateAndParseAgent:
    """Test cases for _validate_and_parse_agent method."""

    @patch("v4.common.services.team_service.config")
    def test_validate_agent_with_all_required_fields(self, mock_config):
        """Test agent validation with all required fields."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        agent_data = {
            "input_key": "agent1",
            "type": "assistant",
            "name": "Agent One",
            "icon": "🤖"
        }
        
        agent = service._validate_and_parse_agent(agent_data)
        
        assert agent.input_key == "agent1"
        assert agent.type == "assistant"
        assert agent.name == "Agent One"
        assert agent.icon == "🤖"

    @patch("v4.common.services.team_service.config")
    def test_validate_agent_with_optional_fields(self, mock_config):
        """Test agent validation with optional fields."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        agent_data = {
            "input_key": "agent1",
            "type": "assistant",
            "name": "Agent One",
            "icon": "🤖",
            "deployment_name": "gpt-4",
            "system_message": "You are helpful",
            "description": "A helpful agent",
            "use_rag": True,
            "use_mcp": True,
            "use_bing": False,
            "use_reasoning": True,
            "index_name": "my-index",
            "coding_tools": True
        }
        
        agent = service._validate_and_parse_agent(agent_data)
        
        assert agent.deployment_name == "gpt-4"
        assert agent.system_message == "You are helpful"
        assert agent.description == "A helpful agent"
        assert agent.use_rag is True
        assert agent.use_mcp is True
        assert agent.use_bing is False
        assert agent.use_reasoning is True
        assert agent.index_name == "my-index"
        assert agent.coding_tools is True

    @patch("v4.common.services.team_service.config")
    def test_validate_agent_missing_required_field(self, mock_config):
        """Test agent validation with missing required field."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        agent_data = {
            "input_key": "agent1",
            "type": "assistant",
            # Missing "name" and "icon"
        }
        
        with pytest.raises(ValueError) as exc_info:
            service._validate_and_parse_agent(agent_data)
        
        assert "missing required field" in str(exc_info.value).lower()


class TestValidateAndParseTask:
    """Test cases for _validate_and_parse_task method."""

    @patch("v4.common.services.team_service.config")
    def test_validate_task_with_all_fields(self, mock_config):
        """Test task validation with all required fields."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        task_data = {
            "id": "task-1",
            "name": "Task One",
            "prompt": "Do something",
            "created": "2025-12-10T00:00:00Z",
            "creator": "user-123",
            "logo": "📝"
        }
        
        task = service._validate_and_parse_task(task_data)
        
        assert task.id == "task-1"
        assert task.name == "Task One"
        assert task.prompt == "Do something"
        assert task.created == "2025-12-10T00:00:00Z"
        assert task.creator == "user-123"
        assert task.logo == "📝"

    @patch("v4.common.services.team_service.config")
    def test_validate_task_missing_required_field(self, mock_config):
        """Test task validation with missing required field."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        task_data = {
            "id": "task-1",
            "name": "Task One",
            # Missing other required fields
        }
        
        with pytest.raises(ValueError) as exc_info:
            service._validate_and_parse_task(task_data)
        
        assert "missing required field" in str(exc_info.value).lower()


class TestValidateAndParseTeamConfig:
    """Test cases for validate_and_parse_team_config method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_validate_team_config_success(self, mock_config):
        """Test successful team configuration validation."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        json_data = {
            "name": "Test Team",
            "status": "active",
            "agents": [
                {
                    "input_key": "agent1",
                    "type": "assistant",
                    "name": "Agent One",
                    "icon": "🤖"
                }
            ],
            "starting_tasks": [
                {
                    "id": "task-1",
                    "name": "Task One",
                    "prompt": "Do something",
                    "created": "2025-12-10T00:00:00Z",
                    "creator": "user-123",
                    "logo": "📝"
                }
            ]
        }
        
        result = await service.validate_and_parse_team_config(json_data, "user-456")
        
        assert isinstance(result, TeamConfiguration)
        assert result.name == "Test Team"
        assert result.status == "active"
        assert result.user_id == "user-456"
        assert result.created_by == "user-456"
        assert len(result.agents) == 1
        assert len(result.starting_tasks) == 1
        assert result.id is not None
        assert result.team_id is not None

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_validate_team_config_with_optional_fields(self, mock_config):
        """Test team configuration validation with optional fields."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        json_data = {
            "name": "Test Team",
            "status": "active",
            "deployment_name": "gpt-4",
            "description": "A test team",
            "logo": "🏢",
            "plan": "Premium plan",
            "agents": [
                {
                    "input_key": "agent1",
                    "type": "assistant",
                    "name": "Agent One",
                    "icon": "🤖"
                }
            ],
            "starting_tasks": [
                {
                    "id": "task-1",
                    "name": "Task One",
                    "prompt": "Do something",
                    "created": "2025-12-10T00:00:00Z",
                    "creator": "user-123",
                    "logo": "📝"
                }
            ]
        }
        
        result = await service.validate_and_parse_team_config(json_data, "user-456")
        
        assert result.deployment_name == "gpt-4"
        assert result.description == "A test team"
        assert result.logo == "🏢"
        assert result.plan == "Premium plan"

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_validate_team_config_missing_name(self, mock_config):
        """Test team configuration validation with missing name."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        json_data = {
            "status": "active",
            "agents": [],
            "starting_tasks": []
        }
        
        with pytest.raises(ValueError) as exc_info:
            await service.validate_and_parse_team_config(json_data, "user-456")
        
        assert "missing required field" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_validate_team_config_empty_agents(self, mock_config):
        """Test team configuration validation with empty agents array."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        json_data = {
            "name": "Test Team",
            "status": "active",
            "agents": [],
            "starting_tasks": [
                {
                    "id": "task-1",
                    "name": "Task One",
                    "prompt": "Do something",
                    "created": "2025-12-10T00:00:00Z",
                    "creator": "user-123",
                    "logo": "📝"
                }
            ]
        }
        
        with pytest.raises(ValueError) as exc_info:
            await service.validate_and_parse_team_config(json_data, "user-456")
        
        assert "agents array cannot be empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_validate_team_config_empty_starting_tasks(self, mock_config):
        """Test team configuration validation with empty starting_tasks array."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        json_data = {
            "name": "Test Team",
            "status": "active",
            "agents": [
                {
                    "input_key": "agent1",
                    "type": "assistant",
                    "name": "Agent One",
                    "icon": "🤖"
                }
            ],
            "starting_tasks": []
        }
        
        with pytest.raises(ValueError) as exc_info:
            await service.validate_and_parse_team_config(json_data, "user-456")
        
        assert "starting tasks array cannot be empty" in str(exc_info.value).lower()


class TestSaveTeamConfiguration:
    """Test cases for save_team_configuration method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_save_team_configuration_success(self, mock_config):
        """Test successful team configuration save."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        mock_memory = AsyncMock()
        mock_memory.add_team = AsyncMock()
        
        service = TeamService(memory_context=mock_memory)
        
        team_config = TeamConfiguration(
            id="team-123",
            session_id="session-456",
            team_id="team-123",
            name="Test Team",
            status="active",
            created="2025-12-10T00:00:00Z",
            created_by="user-789",
            deployment_name="gpt-4",
            agents=[],
            starting_tasks=[],
            user_id="user-789"
        )
        
        result = await service.save_team_configuration(team_config)
        
        assert result == "team-123"
        mock_memory.add_team.assert_called_once_with(team_config)

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_save_team_configuration_exception(self, mock_config):
        """Test team configuration save with exception."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        mock_memory = AsyncMock()
        mock_memory.add_team = AsyncMock(side_effect=Exception("Database error"))
        
        service = TeamService(memory_context=mock_memory)
        
        team_config = TeamConfiguration(
            id="team-123",
            session_id="session-456",
            team_id="team-123",
            name="Test Team",
            status="active",
            created="2025-12-10T00:00:00Z",
            created_by="user-789",
            deployment_name="gpt-4",
            agents=[],
            starting_tasks=[],
            user_id="user-789"
        )
        
        with pytest.raises(ValueError) as exc_info:
            await service.save_team_configuration(team_config)
        
        assert "failed to save" in str(exc_info.value).lower()


class TestGetTeamConfiguration:
    """Test cases for get_team_configuration method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_get_team_configuration_success(self, mock_config):
        """Test successful team configuration retrieval."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_team_config = TeamConfiguration(
            id="team-123",
            session_id="session-456",
            team_id="team-123",
            name="Test Team",
            status="active",
            created="2025-12-10T00:00:00Z",
            created_by="user-789",
            deployment_name="gpt-4",
            agents=[],
            starting_tasks=[],
            user_id="user-789"
        )
        
        mock_memory = AsyncMock()
        mock_memory.get_team = AsyncMock(return_value=mock_team_config)
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_team_configuration("team-123", "user-789")
        
        assert result == mock_team_config
        mock_memory.get_team.assert_called_once_with("team-123")

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_get_team_configuration_not_found(self, mock_config):
        """Test team configuration retrieval when not found."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.get_team = AsyncMock(return_value=None)
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_team_configuration("nonexistent", "user-789")
        
        assert result is None

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_get_team_configuration_exception(self, mock_config):
        """Test team configuration retrieval with exception."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.get_team = AsyncMock(side_effect=ValueError("Database error"))
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_team_configuration("team-123", "user-789")
        
        assert result is None


class TestDeleteUserCurrentTeam:
    """Test cases for delete_user_current_team method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_delete_user_current_team_success(self, mock_config):
        """Test successful current team deletion."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.delete_current_team = AsyncMock()
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_user_current_team("user-123")
        
        assert result is True
        mock_memory.delete_current_team.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_delete_user_current_team_exception(self, mock_config):
        """Test current team deletion with exception."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.delete_current_team = AsyncMock(side_effect=Exception("Error"))
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_user_current_team("user-123")
        
        assert result is False


class TestHandleTeamSelection:
    """Test cases for handle_team_selection method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_handle_team_selection_success(self, mock_config):
        """Test successful team selection."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.delete_current_team = AsyncMock()
        mock_memory.set_current_team = AsyncMock()
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.handle_team_selection("user-123", "team-456")
        
        assert isinstance(result, UserCurrentTeam)
        assert result.user_id == "user-123"
        assert result.team_id == "team-456"
        mock_memory.delete_current_team.assert_called_once_with("user-123")
        mock_memory.set_current_team.assert_called_once()

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_handle_team_selection_exception(self, mock_config):
        """Test team selection with exception."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.delete_current_team = AsyncMock(side_effect=Exception("Error"))
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.handle_team_selection("user-123", "team-456")
        
        assert result is None


class TestGetAllTeamConfigurations:
    """Test cases for get_all_team_configurations method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_get_all_team_configurations_success(self, mock_config):
        """Test successful retrieval of all team configurations."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_teams = [
            TeamConfiguration(
                id="team-1",
                session_id="session-1",
                team_id="team-1",
                name="Team One",
                status="active",
                created="2025-12-10T00:00:00Z",
                created_by="user-123",
                deployment_name="gpt-4",
                agents=[],
                starting_tasks=[],
                user_id="user-123"
            ),
            TeamConfiguration(
                id="team-2",
                session_id="session-2",
                team_id="team-2",
                name="Team Two",
                status="active",
                created="2025-12-10T00:00:00Z",
                created_by="user-123",
                deployment_name="gpt-4",
                agents=[],
                starting_tasks=[],
                user_id="user-123"
            )
        ]
        
        mock_memory = AsyncMock()
        mock_memory.get_all_teams = AsyncMock(return_value=mock_teams)
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_all_team_configurations()
        
        assert len(result) == 2
        assert result[0].name == "Team One"
        assert result[1].name == "Team Two"

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_get_all_team_configurations_empty(self, mock_config):
        """Test retrieval when no teams exist."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.get_all_teams = AsyncMock(return_value=[])
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_all_team_configurations()
        
        assert result == []

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_get_all_team_configurations_exception(self, mock_config):
        """Test retrieval with exception."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.get_all_teams = AsyncMock(side_effect=ValueError("Error"))
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_all_team_configurations()
        
        assert result == []


class TestDeleteTeamConfiguration:
    """Test cases for delete_team_configuration method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_delete_team_configuration_success(self, mock_config):
        """Test successful team configuration deletion."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.delete_team = AsyncMock(return_value=True)
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_team_configuration("team-123", "user-456")
        
        assert result is True
        mock_memory.delete_team.assert_called_once_with("team-123")

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_delete_team_configuration_not_found(self, mock_config):
        """Test deletion when team not found."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.delete_team = AsyncMock(return_value=False)
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_team_configuration("nonexistent", "user-456")
        
        assert result is False

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_delete_team_configuration_exception(self, mock_config):
        """Test deletion with exception."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_memory = AsyncMock()
        mock_memory.delete_team = AsyncMock(side_effect=ValueError("Error"))
        
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_team_configuration("team-123", "user-456")
        
        assert result is False


class TestExtractModelsFromAgent:
    """Test cases for extract_models_from_agent method."""

    @patch("v4.common.services.team_service.config")
    def test_extract_models_basic(self, mock_config):
        """Test extracting models from agent with deployment_name."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        agent = {
            "name": "TestAgent",
            "deployment_name": "gpt-4"
        }
        
        models = service.extract_models_from_agent(agent)
        
        assert "gpt-4" in models

    @patch("v4.common.services.team_service.config")
    def test_extract_models_skip_proxyagent(self, mock_config):
        """Test that proxy agents are skipped."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        agent = {
            "name": "ProxyAgent",
            "deployment_name": "gpt-4"
        }
        
        models = service.extract_models_from_agent(agent)
        
        assert len(models) == 0

    @patch("v4.common.services.team_service.config")
    def test_extract_models_from_config(self, mock_config):
        """Test extracting models from agent config."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        agent = {
            "name": "TestAgent",
            "config": {
                "model": "gpt-35-turbo",
                "deployment_name": "gpt-4"
            }
        }
        
        models = service.extract_models_from_agent(agent)
        
        assert "gpt-35-turbo" in models
        assert "gpt-4" in models


class TestExtractModelsFromText:
    """Test cases for extract_models_from_text method."""

    @patch("v4.common.services.team_service.config")
    def test_extract_gpt4_models(self, mock_config):
        """Test extracting GPT-4 models from text."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        text = "Use gpt-4 and gpt-4o for this task"
        models = service.extract_models_from_text(text)
        
        assert "gpt-4" in models or "gpt-4o" in models

    @patch("v4.common.services.team_service.config")
    def test_extract_gpt35_models(self, mock_config):
        """Test extracting GPT-3.5 models from text."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        text = "Use gpt-35-turbo for responses"
        models = service.extract_models_from_text(text)
        
        assert "gpt-35-turbo" in models


class TestValidateTeamModels:
    """Test cases for validate_team_models method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.FoundryService")
    @patch("v4.common.services.team_service.config")
    async def test_validate_team_models_success(self, mock_config, mock_foundry_class):
        """Test successful model validation."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        mock_config.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4"
        
        mock_foundry = AsyncMock()
        mock_foundry.list_model_deployments = AsyncMock(return_value=[
            {"name": "gpt-4", "status": "Succeeded"},
            {"name": "gpt-35-turbo", "status": "Succeeded"}
        ])
        mock_foundry_class.return_value = mock_foundry
        
        service = TeamService()
        
        team_config = {
            "agents": [
                {"name": "Agent1", "deployment_name": "gpt-4"}
            ]
        }
        
        is_valid, missing = await service.validate_team_models(team_config)
        
        assert is_valid is True
        assert len(missing) == 0

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_validate_team_models_missing_models(self, mock_config):
        """Test model validation with missing models."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        mock_config.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4"
        
        service = TeamService()
        
        # Directly modify the namespace to inject mock
        mock_foundry = AsyncMock()
        mock_foundry.list_model_deployments = AsyncMock(return_value=[
            {"name": "gpt-4", "status": "Succeeded"}
        ])
        mock_foundry_class = Mock(return_value=mock_foundry)
        original_foundry = team_namespace['FoundryService']
        team_namespace['FoundryService'] = mock_foundry_class
        
        try:
            team_config = {
                "agents": [
                    {"name": "Agent1", "deployment_name": "missing-model"}
                ]
            }
            
            is_valid, missing = await service.validate_team_models(team_config)
            
            assert is_valid is False
            assert "missing-model" in missing
        finally:
            team_namespace['FoundryService'] = original_foundry


class TestExtractIndexNames:
    """Test cases for extract_index_names method."""

    @patch("v4.common.services.team_service.config")
    def test_extract_index_names_rag_agents(self, mock_config):
        """Test extracting index names from RAG agents."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        team_config = {
            "agents": [
                {"type": "rag", "index_name": "index-1"},
                {"type": "rag", "index_name": "index-2"},
                {"type": "assistant", "index_name": "index-3"}
            ]
        }
        
        result = service.extract_index_names(team_config)
        
        assert "index-1" in result
        assert "index-2" in result
        assert "index-3" not in result

    @patch("v4.common.services.team_service.config")
    def test_extract_index_names_no_rag_agents(self, mock_config):
        """Test extracting index names when no RAG agents exist."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        service = TeamService()
        
        team_config = {
            "agents": [
                {"type": "assistant", "name": "Agent1"}
            ]
        }
        
        result = service.extract_index_names(team_config)
        
        assert len(result) == 0


class TestValidateSingleIndex:
    """Test cases for validate_single_index method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.SearchIndexClient")
    @patch("v4.common.services.team_service.config")
    async def test_validate_single_index_success(self, mock_config, mock_client_class):
        """Test successful index validation."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        mock_client = Mock()
        mock_client.get_index.return_value = Mock()
        mock_client_class.return_value = mock_client
        
        service = TeamService()
        
        is_valid, error = await service.validate_single_index("test-index")
        
        assert is_valid is True
        assert error == ""

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_validate_single_index_not_found(self, mock_config):
        """Test index validation when index not found."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        service = TeamService()
        
        # Directly modify the namespace to inject mock
        mock_client = Mock()
        mock_client.get_index.side_effect = ResourceNotFoundError("Not found")
        mock_client_class = Mock(return_value=mock_client)
        original_client = team_namespace['SearchIndexClient']
        team_namespace['SearchIndexClient'] = mock_client_class
        
        try:
            is_valid, error = await service.validate_single_index("nonexistent-index")
            
            assert is_valid is False
            assert "does not exist" in error
        finally:
            team_namespace['SearchIndexClient'] = original_client

    @pytest.mark.asyncio
    @patch("v4.common.services.team_service.config")
    async def test_validate_single_index_auth_error(self, mock_config):
        """Test index validation with authentication error."""
        mock_config.AZURE_SEARCH_ENDPOINT = "https://search.example.com"
        mock_config.get_azure_credentials.return_value = Mock()
        
        service = TeamService()
        
        # Directly modify the namespace to inject mock
        mock_client = Mock()
        mock_client.get_index.side_effect = ClientAuthenticationError("Auth failed")
        mock_client_class = Mock(return_value=mock_client)
        original_client = team_namespace['SearchIndexClient']
        team_namespace['SearchIndexClient'] = mock_client_class
        
        try:
            is_valid, error = await service.validate_single_index("test-index")
            
            assert is_valid is False
            assert "authentication failed" in error.lower()
        finally:
            team_namespace['SearchIndexClient'] = original_client


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
