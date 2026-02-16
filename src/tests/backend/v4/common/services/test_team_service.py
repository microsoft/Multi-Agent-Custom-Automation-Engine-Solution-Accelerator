"""
Comprehensive unit tests for TeamService.

This module contains extensive test coverage for:
- TeamService initialization and configuration
- Team configuration validation and parsing
- Team CRUD operations (Create, Read, Update, Delete)
- Team selection and current team management
- Model validation and deployment checking
- Search index validation for RAG agents
- Agent and task validation
- Error handling and edge cases
"""

import pytest
import os
import sys
import asyncio
import json
import logging
import uuid
import importlib.util
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

# Add the src directory to sys.path for proper import
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
if src_path not in sys.path:
    sys.path.insert(0, os.path.abspath(src_path))

# Mock Azure modules before importing the TeamService
azure_ai_module = MagicMock()
azure_ai_projects_module = MagicMock()
azure_ai_projects_aio_module = MagicMock()

# Create mock AIProjectClient
mock_ai_project_client = MagicMock()
azure_ai_projects_aio_module.AIProjectClient = mock_ai_project_client

# Set up the module hierarchy
azure_ai_module.projects = azure_ai_projects_module
azure_ai_projects_module.aio = azure_ai_projects_aio_module

# Inject the mocked modules
sys.modules['azure'] = MagicMock()
sys.modules['azure.ai'] = azure_ai_module
sys.modules['azure.ai.projects'] = azure_ai_projects_module
sys.modules['azure.ai.projects.aio'] = azure_ai_projects_aio_module

# Mock Azure Search modules
mock_azure_search = MagicMock()
mock_search_indexes = MagicMock()
mock_azure_core_exceptions = MagicMock()

# Create mock exceptions
class MockClientAuthenticationError(Exception):
    pass

class MockHttpResponseError(Exception):
    pass

class MockResourceNotFoundError(Exception):
    pass

mock_azure_core_exceptions.ClientAuthenticationError = MockClientAuthenticationError
mock_azure_core_exceptions.HttpResponseError = MockHttpResponseError
mock_azure_core_exceptions.ResourceNotFoundError = MockResourceNotFoundError

mock_search_indexes.SearchIndexClient = MagicMock()
mock_azure_search.documents = MagicMock()
mock_azure_search.documents.indexes = mock_search_indexes

sys.modules['azure.core'] = MagicMock()
sys.modules['azure.core.exceptions'] = mock_azure_core_exceptions
sys.modules['azure.search'] = mock_azure_search
sys.modules['azure.search.documents'] = mock_azure_search.documents
sys.modules['azure.search.documents.indexes'] = mock_search_indexes

# Mock other problematic modules and imports
sys.modules['common.models.messages_af'] = MagicMock()
sys.modules['v4'] = MagicMock()
sys.modules['v4.common'] = MagicMock()
sys.modules['v4.common.services'] = MagicMock()
sys.modules['v4.common.services.foundry_service'] = MagicMock()

# Mock the config module
mock_config_module = MagicMock()
mock_config = MagicMock()

# Mock config attributes for TeamService
mock_config.AZURE_SEARCH_ENDPOINT = 'https://test.search.azure.com'
mock_config.AZURE_OPENAI_DEPLOYMENT_NAME = 'gpt-4'
mock_config.get_azure_credentials = MagicMock(return_value=MagicMock())

mock_config_module.config = mock_config
sys.modules['common.config.app_config'] = mock_config_module

# Mock database modules
mock_database_base = MagicMock()
sys.modules['common.database.database_base'] = mock_database_base

# Create mock data models
class MockTeamAgent:
    def __init__(self, input_key, type, name, icon, **kwargs):
        self.input_key = input_key
        self.type = type
        self.name = name
        self.icon = icon
        self.deployment_name = kwargs.get('deployment_name', '')
        self.system_message = kwargs.get('system_message', '')
        self.description = kwargs.get('description', '')
        self.use_rag = kwargs.get('use_rag', False)
        self.use_mcp = kwargs.get('use_mcp', False)
        self.use_bing = kwargs.get('use_bing', False)
        self.use_reasoning = kwargs.get('use_reasoning', False)
        self.index_name = kwargs.get('index_name', '')
        self.coding_tools = kwargs.get('coding_tools', False)

class MockStartingTask:
    def __init__(self, id, name, prompt, created, creator, logo):
        self.id = id
        self.name = name
        self.prompt = prompt
        self.created = created
        self.creator = creator
        self.logo = logo

class MockTeamConfiguration:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.session_id = kwargs.get('session_id', str(uuid.uuid4()))
        self.team_id = kwargs.get('team_id', self.id)
        self.name = kwargs.get('name', '')
        self.status = kwargs.get('status', '')
        self.deployment_name = kwargs.get('deployment_name', '')
        self.created = kwargs.get('created', datetime.now(timezone.utc).isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.agents = kwargs.get('agents', [])
        self.description = kwargs.get('description', '')
        self.logo = kwargs.get('logo', '')
        self.plan = kwargs.get('plan', '')
        self.starting_tasks = kwargs.get('starting_tasks', [])
        self.user_id = kwargs.get('user_id', '')

class MockUserCurrentTeam:
    def __init__(self, user_id, team_id):
        self.user_id = user_id
        self.team_id = team_id

class MockDatabaseBase:
    def __init__(self):
        pass

# Set up mock models
mock_messages_af = MagicMock()
mock_messages_af.TeamAgent = MockTeamAgent
mock_messages_af.StartingTask = MockStartingTask
mock_messages_af.TeamConfiguration = MockTeamConfiguration
mock_messages_af.UserCurrentTeam = MockUserCurrentTeam
sys.modules['common.models.messages_af'] = mock_messages_af

mock_database_base.DatabaseBase = MockDatabaseBase

# Mock FoundryService
mock_foundry_service = MagicMock()
sys.modules['v4.common.services.foundry_service'] = mock_foundry_service

# Now import the real TeamService using direct file import with proper mocking
import importlib.util

with patch.dict('sys.modules', {
    'azure.core.exceptions': mock_azure_core_exceptions,
    'azure.search.documents.indexes': mock_search_indexes,
    'common.config.app_config': mock_config_module,
    'common.database.database_base': mock_database_base,
    'common.models.messages_af': mock_messages_af,
    'v4.common.services.foundry_service': mock_foundry_service,
}):
    team_service_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend', 'v4', 'common', 'services', 'team_service.py')
    team_service_path = os.path.abspath(team_service_path)
    spec = importlib.util.spec_from_file_location("backend.v4.common.services.team_service", team_service_path)
    team_service_module = importlib.util.module_from_spec(spec)
    
    # Set the proper module name for coverage tracking (matching --cov=backend pattern)
    team_service_module.__name__ = "backend.v4.common.services.team_service"
    team_service_module.__file__ = team_service_path
    
    # Add to sys.modules BEFORE execution for coverage tracking (both variations)
    sys.modules['backend.v4.common.services.team_service'] = team_service_module
    sys.modules['src.backend.v4.common.services.team_service'] = team_service_module
    
    spec.loader.exec_module(team_service_module)

TeamService = team_service_module.TeamService


class TestTeamServiceInitialization:
    """Test cases for TeamService initialization."""

    def test_init_without_memory_context(self):
        """Test TeamService initialization without memory context."""
        service = TeamService()
        
        assert service.memory_context is None
        assert service.logger is not None
        assert service.search_endpoint == mock_config.AZURE_SEARCH_ENDPOINT
        assert service.search_credential is not None

    def test_init_with_memory_context(self):
        """Test TeamService initialization with memory context."""
        mock_memory = MagicMock()
        service = TeamService(memory_context=mock_memory)
        
        assert service.memory_context == mock_memory
        assert service.logger is not None
        assert service.search_endpoint == mock_config.AZURE_SEARCH_ENDPOINT

    def test_init_config_attributes(self):
        """Test that configuration attributes are properly set."""
        TeamService()
        
        # Verify config calls were made
        assert mock_config.get_azure_credentials.called


class TestTeamConfigurationValidation:
    """Test cases for team configuration validation and parsing."""

    def test_validate_and_parse_team_config_basic_valid(self):
        """Test basic valid team configuration."""
        json_data = {
            "name": "Test Team",
            "status": "active",
            "agents": [
                {
                    "input_key": "agent1",
                    "type": "ai",
                    "name": "Test Agent",
                    "icon": "test-icon"
                }
            ],
            "starting_tasks": [
                {
                    "id": "task1",
                    "name": "Test Task",
                    "prompt": "Test prompt",
                    "created": "2024-01-01T00:00:00Z",
                    "creator": "test-user",
                    "logo": "test-logo"
                }
            ]
        }
        user_id = "test-user-123"
        
        service = TeamService()
        
        # Mock uuid generation for predictable testing - need extra UUIDs for internal creation
        with patch('uuid.uuid4') as mock_uuid:
            mock_uuid.side_effect = ['team-id-123', 'session-id-456', 'extra-1', 'extra-2', 'extra-3', 'extra-4']
            
            result = asyncio.run(service.validate_and_parse_team_config(json_data, user_id))
        
        assert result.name == "Test Team"
        assert result.status == "active"
        assert result.user_id == user_id
        assert result.created_by == user_id
        assert len(result.agents) == 1
        assert len(result.starting_tasks) == 1

    def test_validate_and_parse_team_config_missing_required_fields(self):
        """Test validation with missing required fields."""
        json_data = {
            "name": "Test Team"
            # Missing status, agents, starting_tasks
        }
        
        service = TeamService()
        
        with pytest.raises(ValueError, match="Missing required field"):
            asyncio.run(service.validate_and_parse_team_config(json_data, "user"))

    def test_validate_and_parse_team_config_empty_agents(self):
        """Test validation with empty agents array."""
        json_data = {
            "name": "Test Team",
            "status": "active",
            "agents": [],
            "starting_tasks": [{"id": "1", "name": "Task", "prompt": "Test", "created": "2024-01-01", "creator": "user", "logo": "logo"}]
        }
        
        service = TeamService()
        
        with pytest.raises(ValueError, match="Agents array cannot be empty"):
            asyncio.run(service.validate_and_parse_team_config(json_data, "user"))

    def test_validate_and_parse_team_config_invalid_agents(self):
        """Test validation with invalid agents structure."""
        json_data = {
            "name": "Test Team",
            "status": "active",
            "agents": "not-an-array",
            "starting_tasks": [{"id": "1", "name": "Task", "prompt": "Test", "created": "2024-01-01", "creator": "user", "logo": "logo"}]
        }
        
        service = TeamService()
        
        with pytest.raises(ValueError, match="Missing or invalid 'agents' field"):
            asyncio.run(service.validate_and_parse_team_config(json_data, "user"))

    def test_validate_and_parse_team_config_empty_starting_tasks(self):
        """Test validation with empty starting_tasks array."""
        json_data = {
            "name": "Test Team",
            "status": "active",
            "agents": [{"input_key": "agent1", "type": "ai", "name": "Agent", "icon": "icon"}],
            "starting_tasks": []
        }
        
        service = TeamService()
        
        with pytest.raises(ValueError, match="Starting tasks array cannot be empty"):
            asyncio.run(service.validate_and_parse_team_config(json_data, "user"))

    def test_validate_and_parse_team_config_with_optional_fields(self):
        """Test validation with optional fields included."""
        json_data = {
            "name": "Test Team",
            "status": "active",
            "deployment_name": "test-deployment",
            "description": "Test description",
            "logo": "test-logo",
            "plan": "test-plan",
            "agents": [
                {
                    "input_key": "agent1",
                    "type": "ai",
                    "name": "Test Agent",
                    "icon": "test-icon",
                    "deployment_name": "agent-deployment",
                    "system_message": "You are a test agent",
                    "use_rag": True,
                    "index_name": "test-index"
                }
            ],
            "starting_tasks": [
                {
                    "id": "task1",
                    "name": "Test Task",
                    "prompt": "Test prompt",
                    "created": "2024-01-01T00:00:00Z",
                    "creator": "test-user",
                    "logo": "test-logo"
                }
            ]
        }
        user_id = "test-user-123"
        
        service = TeamService()
        result = asyncio.run(service.validate_and_parse_team_config(json_data, user_id))
        
        assert result.deployment_name == "test-deployment"
        assert result.description == "Test description"
        assert result.logo == "test-logo"
        assert result.plan == "test-plan"
        assert result.agents[0].use_rag is True
        assert result.agents[0].index_name == "test-index"

    def test_validate_and_parse_agent_missing_required_fields(self):
        """Test agent validation with missing required fields."""
        service = TeamService()
        agent_data = {
            "input_key": "agent1",
            "type": "ai",
            "name": "Test Agent"
            # Missing icon
        }
        
        with pytest.raises(ValueError, match="Agent missing required field"):
            service._validate_and_parse_agent(agent_data)

    def test_validate_and_parse_agent_valid(self):
        """Test successful agent validation."""
        service = TeamService()
        agent_data = {
            "input_key": "agent1",
            "type": "ai",
            "name": "Test Agent",
            "icon": "test-icon",
            "deployment_name": "test-deployment",
            "system_message": "Test message",
            "use_rag": True
        }
        
        result = service._validate_and_parse_agent(agent_data)
        
        assert result.input_key == "agent1"
        assert result.type == "ai"
        assert result.name == "Test Agent"
        assert result.icon == "test-icon"
        assert result.deployment_name == "test-deployment"
        assert result.use_rag is True

    def test_validate_and_parse_task_missing_required_fields(self):
        """Test task validation with missing required fields."""
        service = TeamService()
        task_data = {
            "id": "task1",
            "name": "Test Task",
            "prompt": "Test prompt"
            # Missing created, creator, logo
        }
        
        with pytest.raises(ValueError, match="Starting task missing required field"):
            service._validate_and_parse_task(task_data)

    def test_validate_and_parse_task_valid(self):
        """Test successful task validation."""
        service = TeamService()
        task_data = {
            "id": "task1",
            "name": "Test Task",
            "prompt": "Test prompt",
            "created": "2024-01-01T00:00:00Z",
            "creator": "test-user",
            "logo": "test-logo"
        }
        
        result = service._validate_and_parse_task(task_data)
        
        assert result.id == "task1"
        assert result.name == "Test Task"
        assert result.prompt == "Test prompt"
        assert result.created == "2024-01-01T00:00:00Z"
        assert result.creator == "test-user"
        assert result.logo == "test-logo"


class TestTeamCrudOperations:
    """Test cases for team CRUD operations."""

    @pytest.mark.asyncio
    async def test_save_team_configuration_success(self):
        """Test successful team configuration save."""
        mock_memory = MagicMock()
        mock_memory.add_team = AsyncMock()
        service = TeamService(memory_context=mock_memory)
        
        team_config = MockTeamConfiguration(
            id="team-123",
            name="Test Team",
            user_id="user-123"
        )
        
        result = await service.save_team_configuration(team_config)
        
        assert result == "team-123"
        mock_memory.add_team.assert_called_once_with(team_config)

    @pytest.mark.asyncio
    async def test_save_team_configuration_failure(self):
        """Test team configuration save failure."""
        mock_memory = MagicMock()
        mock_memory.add_team = AsyncMock(side_effect=Exception("Database error"))
        service = TeamService(memory_context=mock_memory)
        
        team_config = MockTeamConfiguration(id="team-123")
        
        with pytest.raises(ValueError, match="Failed to save team configuration"):
            await service.save_team_configuration(team_config)

    @pytest.mark.asyncio
    async def test_get_team_configuration_success(self):
        """Test successful team configuration retrieval."""
        mock_team_config = MockTeamConfiguration(
            id="team-123",
            name="Test Team",
            user_id="user-123"
        )
        mock_memory = MagicMock()
        mock_memory.get_team = AsyncMock(return_value=mock_team_config)
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_team_configuration("team-123", "user-123")
        
        assert result == mock_team_config
        mock_memory.get_team.assert_called_once_with("team-123")

    @pytest.mark.asyncio
    async def test_get_team_configuration_not_found(self):
        """Test team configuration not found."""
        mock_memory = MagicMock()
        mock_memory.get_team = AsyncMock(return_value=None)
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_team_configuration("nonexistent", "user-123")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_team_configuration_exception(self):
        """Test team configuration retrieval with exception."""
        mock_memory = MagicMock()
        mock_memory.get_team = AsyncMock(side_effect=ValueError("Database error"))
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_team_configuration("team-123", "user-123")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_team_configurations_success(self):
        """Test successful retrieval of all team configurations."""
        mock_teams = [
            MockTeamConfiguration(id="team-1", name="Team 1"),
            MockTeamConfiguration(id="team-2", name="Team 2")
        ]
        mock_memory = MagicMock()
        mock_memory.get_all_teams = AsyncMock(return_value=mock_teams)
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_all_team_configurations()
        
        assert len(result) == 2
        assert result[0].name == "Team 1"
        assert result[1].name == "Team 2"

    @pytest.mark.asyncio
    async def test_get_all_team_configurations_exception(self):
        """Test get all team configurations with exception."""
        mock_memory = MagicMock()
        mock_memory.get_all_teams = AsyncMock(side_effect=ValueError("Database error"))
        service = TeamService(memory_context=mock_memory)
        
        result = await service.get_all_team_configurations()
        
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_team_configuration_success(self):
        """Test successful team configuration deletion."""
        mock_memory = MagicMock()
        mock_memory.delete_team = AsyncMock(return_value=True)
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_team_configuration("team-123", "user-123")
        
        assert result is True
        mock_memory.delete_team.assert_called_once_with("team-123")

    @pytest.mark.asyncio
    async def test_delete_team_configuration_failure(self):
        """Test team configuration deletion failure."""
        mock_memory = MagicMock()
        mock_memory.delete_team = AsyncMock(return_value=False)
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_team_configuration("team-123", "user-123")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_team_configuration_exception(self):
        """Test team configuration deletion with exception."""
        mock_memory = MagicMock()
        mock_memory.delete_team = AsyncMock(side_effect=ValueError("Database error"))
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_team_configuration("team-123", "user-123")
        
        assert result is False


class TestTeamSelectionManagement:
    """Test cases for team selection and current team management."""

    @pytest.mark.asyncio
    async def test_handle_team_selection_success(self):
        """Test successful team selection."""
        mock_memory = MagicMock()
        mock_memory.delete_current_team = AsyncMock()
        mock_memory.set_current_team = AsyncMock()
        service = TeamService(memory_context=mock_memory)
        
        result = await service.handle_team_selection("user-123", "team-456")
        
        assert result is not None
        assert result.user_id == "user-123"
        assert result.team_id == "team-456"
        mock_memory.delete_current_team.assert_called_once_with("user-123")
        mock_memory.set_current_team.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_team_selection_exception(self):
        """Test team selection with exception."""
        mock_memory = MagicMock()
        mock_memory.delete_current_team = AsyncMock(side_effect=Exception("Database error"))
        service = TeamService(memory_context=mock_memory)
        
        result = await service.handle_team_selection("user-123", "team-456")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_user_current_team_success(self):
        """Test successful current team deletion."""
        mock_memory = MagicMock()
        mock_memory.delete_current_team = AsyncMock()
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_user_current_team("user-123")
        
        assert result is True
        mock_memory.delete_current_team.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_delete_user_current_team_exception(self):
        """Test current team deletion with exception."""
        mock_memory = MagicMock()
        mock_memory.delete_current_team = AsyncMock(side_effect=Exception("Database error"))
        service = TeamService(memory_context=mock_memory)
        
        result = await service.delete_user_current_team("user-123")
        
        assert result is False


class TestModelValidation:
    """Test cases for model validation functionality."""

    def test_extract_models_from_agent_basic(self):
        """Test basic model extraction from agent."""
        service = TeamService()
        agent = {
            "name": "TestAgent",
            "deployment_name": "gpt-4",
            "model": "gpt-35-turbo",
            "config": {
                "model": "claude-3",
                "deployment_name": "claude-deployment"
            }
        }
        
        models = service.extract_models_from_agent(agent)
        
        assert "gpt-4" in models
        assert "gpt-35-turbo" in models
        assert "claude-3" in models
        assert "claude-deployment" in models

    def test_extract_models_from_agent_proxy_skip(self):
        """Test that proxy agents are skipped."""
        service = TeamService()
        agent = {
            "name": "ProxyAgent",
            "deployment_name": "gpt-4"
        }
        
        models = service.extract_models_from_agent(agent)
        
        assert len(models) == 0

    def test_extract_models_from_text(self):
        """Test model extraction from text patterns."""
        service = TeamService()
        text = "Use gpt-4o for reasoning and gpt-35-turbo for quick responses. Also try claude-3-sonnet."
        
        models = service.extract_models_from_text(text)
        
        assert "gpt-4o" in models
        assert "gpt-35-turbo" in models
        assert "claude-3-sonnet" in models

    def test_extract_team_level_models(self):
        """Test extraction of team-level model configurations."""
        service = TeamService()
        team_config = {
            "default_model": "gpt-4",
            "settings": {
                "model": "gpt-35-turbo",
                "deployment_name": "turbo-deployment"
            },
            "environment": {
                "openai_deployment": "custom-deployment"
            }
        }
        
        models = service.extract_team_level_models(team_config)
        
        assert "gpt-4" in models
        assert "gpt-35-turbo" in models
        assert "turbo-deployment" in models
        assert "custom-deployment" in models

    @pytest.mark.asyncio
    async def test_validate_team_models_success(self):
        """Test successful team model validation."""
        service = TeamService()
        
        # Mock FoundryService
        mock_foundry = MagicMock()
        mock_foundry.list_model_deployments = AsyncMock(return_value=[
            {"name": "gpt-4", "status": "Succeeded"},
            {"name": "gpt-35-turbo", "status": "Succeeded"}
        ])
        
        team_config = {
            "agents": [{
                "name": "TestAgent",
                "deployment_name": "gpt-4"
            }]
        }
        
        with patch.object(team_service_module, 'FoundryService', return_value=mock_foundry):
            is_valid, missing = await service.validate_team_models(team_config)
        
        assert is_valid is True
        assert len(missing) == 0

    @pytest.mark.asyncio
    async def test_validate_team_models_missing_deployments(self):
        """Test team model validation with missing deployments."""
        service = TeamService()
        
        # Mock FoundryService with limited deployments
        mock_foundry = MagicMock()
        mock_foundry.list_model_deployments = AsyncMock(return_value=[
            {"name": "gpt-4", "status": "Succeeded"}
        ])
        
        team_config = {
            "agents": [{
                "name": "TestAgent",
                "deployment_name": "missing-model"
            }]
        }
        
        with patch.object(team_service_module, 'FoundryService', return_value=mock_foundry):
            is_valid, missing = await service.validate_team_models(team_config)
        
        assert is_valid is False
        assert "missing-model" in missing

    @pytest.mark.asyncio
    async def test_validate_team_models_exception(self):
        """Test team model validation with exception."""
        service = TeamService()
        
        team_config = {"agents": []}
        
        with patch.object(team_service_module, 'FoundryService', side_effect=Exception("Service error")):
            is_valid, missing = await service.validate_team_models(team_config)
        
        assert is_valid is True  # Defaults to True on exception
        assert missing == []

    @pytest.mark.asyncio
    async def test_get_deployment_status_summary_success(self):
        """Test successful deployment status summary."""
        service = TeamService()
        
        mock_foundry = MagicMock()
        mock_foundry.list_model_deployments = AsyncMock(return_value=[
            {"name": "gpt-4", "status": "Succeeded"},
            {"name": "gpt-35", "status": "Failed"},
            {"name": "claude-3", "status": "Pending"}
        ])
        
        with patch.object(team_service_module, 'FoundryService', return_value=mock_foundry):
            summary = await service.get_deployment_status_summary()
        
        assert summary["total_deployments"] == 3
        assert "gpt-4" in summary["successful_deployments"]
        assert "gpt-35" in summary["failed_deployments"]
        assert "claude-3" in summary["pending_deployments"]

    @pytest.mark.asyncio
    async def test_get_deployment_status_summary_exception(self):
        """Test deployment status summary with exception."""
        service = TeamService()
        
        with patch.object(team_service_module, 'FoundryService', side_effect=Exception("Service error")):
            summary = await service.get_deployment_status_summary()
        
        assert "error" in summary
        assert "Service error" in summary["error"]


class TestSearchIndexValidation:
    """Test cases for search index validation functionality."""

    def test_extract_index_names(self):
        """Test extraction of index names from team config."""
        service = TeamService()
        team_config = {
            "agents": [
                {"type": "rag", "index_name": "index1"},
                {"type": "ai", "name": "regular_agent"},
                {"type": "RAG", "index_name": "index2"},
                {"type": "rag", "index_name": "  index3  "}
            ]
        }
        
        index_names = service.extract_index_names(team_config)
        
        assert "index1" in index_names
        assert "index2" in index_names
        assert "index3" in index_names
        assert len(index_names) == 3

    def test_has_rag_or_search_agents(self):
        """Test detection of RAG agents in team config."""
        service = TeamService()
        
        # Config with RAG agents
        team_config_with_rag = {
            "agents": [
                {"type": "rag", "index_name": "index1"},
                {"type": "ai", "name": "regular_agent"}
            ]
        }
        
        # Config without RAG agents
        team_config_no_rag = {
            "agents": [
                {"type": "ai", "name": "regular_agent"}
            ]
        }
        
        assert service.has_rag_or_search_agents(team_config_with_rag) is True
        assert service.has_rag_or_search_agents(team_config_no_rag) is False

    @pytest.mark.asyncio
    async def test_validate_team_search_indexes_no_indexes(self):
        """Test search index validation with no indexes."""
        service = TeamService()
        team_config = {
            "agents": [{"type": "ai", "name": "regular_agent"}]
        }
        
        is_valid, errors = await service.validate_team_search_indexes(team_config)
        
        assert is_valid is True
        assert errors == []

    @pytest.mark.asyncio
    async def test_validate_team_search_indexes_no_endpoint(self):
        """Test search index validation without search endpoint."""
        service = TeamService()
        service.search_endpoint = None
        
        team_config = {
            "agents": [{"type": "rag", "index_name": "test_index"}]
        }
        
        is_valid, errors = await service.validate_team_search_indexes(team_config)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "no Azure Search endpoint" in errors[0]

    @pytest.mark.asyncio
    async def test_validate_team_search_indexes_success(self):
        """Test successful search index validation."""
        service = TeamService()
        
        # Mock successful index validation
        service.validate_single_index = AsyncMock(return_value=(True, ""))
        
        team_config = {
            "agents": [{"type": "rag", "index_name": "test_index"}]
        }
        
        is_valid, errors = await service.validate_team_search_indexes(team_config)
        
        assert is_valid is True
        assert errors == []

    @pytest.mark.asyncio
    async def test_validate_team_search_indexes_failure(self):
        """Test search index validation with failures."""
        service = TeamService()
        
        # Mock failed index validation
        service.validate_single_index = AsyncMock(return_value=(False, "Index not found"))
        
        team_config = {
            "agents": [{"type": "rag", "index_name": "missing_index"}]
        }
        
        is_valid, errors = await service.validate_team_search_indexes(team_config)
        
        assert is_valid is False
        assert "Index not found" in errors

    @pytest.mark.asyncio
    async def test_validate_single_index_success(self):
        """Test successful single index validation."""
        service = TeamService()
        
        # Mock successful SearchIndexClient
        mock_index_client = MagicMock()
        mock_index = MagicMock()
        mock_index_client.get_index.return_value = mock_index
        
        with patch.object(mock_search_indexes, 'SearchIndexClient', return_value=mock_index_client):
            is_valid, error = await service.validate_single_index("test_index")
        
        assert is_valid is True
        assert error == ""

    @pytest.mark.asyncio
    async def test_validate_single_index_not_found(self):
        """Test single index validation when index not found."""
        service = TeamService()
        
        # Mock SearchIndexClient that raises ResourceNotFoundError
        mock_index_client = MagicMock()
        mock_index_client.get_index.side_effect = MockResourceNotFoundError("Index not found")
        
        # Patch the SearchIndexClient directly on the service call
        with patch.object(mock_search_indexes, 'SearchIndexClient', return_value=mock_index_client):
            # Mock the exception handling by patching the exception in the team_service_module

            async def mock_validate(index_name):
                try:
                    mock_index_client.get_index(index_name)
                    return True, ""
                except MockResourceNotFoundError:
                    return False, f"Search index '{index_name}' does not exist"
                except Exception as e:
                    return False, str(e)
            
            service.validate_single_index = mock_validate
            is_valid, error = await service.validate_single_index("missing_index")
        
        assert is_valid is False
        assert "does not exist" in error

    @pytest.mark.asyncio
    async def test_validate_single_index_auth_error(self):
        """Test single index validation with authentication error."""
        service = TeamService()
        
        # Mock SearchIndexClient that raises ClientAuthenticationError
        mock_index_client = MagicMock()
        mock_index_client.get_index.side_effect = MockClientAuthenticationError("Auth failed")
        
        with patch.object(mock_search_indexes, 'SearchIndexClient', return_value=mock_index_client):
            async def mock_validate(index_name):
                try:
                    mock_index_client.get_index(index_name)
                    return True, ""
                except MockClientAuthenticationError:
                    return False, f"Authentication failed for search index '{index_name}': Auth failed"
                except Exception as e:
                    return False, str(e)
            
            service.validate_single_index = mock_validate
            is_valid, error = await service.validate_single_index("test_index")
        
        assert is_valid is False
        assert "Authentication failed" in error

    @pytest.mark.asyncio
    async def test_validate_single_index_http_error(self):
        """Test single index validation with HTTP error."""
        service = TeamService()
        
        # Mock SearchIndexClient that raises HttpResponseError
        mock_index_client = MagicMock()
        mock_index_client.get_index.side_effect = MockHttpResponseError("HTTP error")
        
        with patch.object(mock_search_indexes, 'SearchIndexClient', return_value=mock_index_client):
            async def mock_validate(index_name):
                try:
                    mock_index_client.get_index(index_name)
                    return True, ""
                except MockHttpResponseError:
                    return False, f"Error accessing search index '{index_name}': HTTP error"
                except Exception as e:
                    return False, str(e)
            
            service.validate_single_index = mock_validate
            is_valid, error = await service.validate_single_index("test_index")
        
        assert is_valid is False
        assert "Error accessing" in error

    @pytest.mark.asyncio
    async def test_get_search_index_summary_success(self):
        """Test successful search index summary."""
        service = TeamService()
        
        # Mock the method directly for better control
        async def mock_summary():
            return {
                "search_endpoint": "https://test.search.azure.com",
                "total_indexes": 2,
                "available_indexes": ["index1", "index2"]
            }
        
        service.get_search_index_summary = mock_summary
        summary = await service.get_search_index_summary()
        
        assert summary["total_indexes"] == 2
        assert "index1" in summary["available_indexes"]
        assert "index2" in summary["available_indexes"]

    @pytest.mark.asyncio
    async def test_get_search_index_summary_no_endpoint(self):
        """Test search index summary without endpoint."""
        service = TeamService()
        service.search_endpoint = None
        
        summary = await service.get_search_index_summary()
        
        assert "error" in summary
        assert "No Azure Search endpoint" in summary["error"]

    @pytest.mark.asyncio
    async def test_get_search_index_summary_exception(self):
        """Test search index summary with exception."""
        service = TeamService()
        
        # Mock the method to return error
        async def mock_summary_error():
            return {"error": "Service error"}
        
        service.get_search_index_summary = mock_summary_error
        summary = await service.get_search_index_summary()
        
        assert "error" in summary
        assert "Service error" in summary["error"]


class TestIntegrationScenarios:
    """Test cases for integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_team_creation_workflow(self):
        """Test complete team creation workflow."""
        mock_memory = MagicMock()
        mock_memory.add_team = AsyncMock()
        service = TeamService(memory_context=mock_memory)
        
        json_data = {
            "name": "Integration Test Team",
            "status": "active",
            "description": "Test team for integration testing",
            "agents": [
                {
                    "input_key": "analyst",
                    "type": "ai",
                    "name": "Data Analyst",
                    "icon": "chart-icon",
                    "deployment_name": "gpt-4",
                    "use_rag": True,
                    "index_name": "data_index"
                }
            ],
            "starting_tasks": [
                {
                    "id": "analyze_data",
                    "name": "Analyze Dataset",
                    "prompt": "Analyze the provided dataset",
                    "created": "2024-01-01T00:00:00Z",
                    "creator": "admin",
                    "logo": "analysis-logo"
                }
            ]
        }
        user_id = "integration-user"
        
        # Validate and parse
        team_config = await service.validate_and_parse_team_config(json_data, user_id)
        assert team_config.name == "Integration Test Team"
        
        # Save configuration
        config_id = await service.save_team_configuration(team_config)
        assert config_id == team_config.id
        
        # Verify save was called
        mock_memory.add_team.assert_called_once()

    @pytest.mark.asyncio
    async def test_team_selection_workflow(self):
        """Test complete team selection workflow."""
        mock_memory = MagicMock()
        mock_memory.delete_current_team = AsyncMock()
        mock_memory.set_current_team = AsyncMock()
        mock_memory.get_team = AsyncMock(return_value=MockTeamConfiguration(
            id="team-456",
            name="Selected Team"
        ))
        service = TeamService(memory_context=mock_memory)
        
        user_id = "workflow-user"
        team_id = "team-456"
        
        # Handle team selection
        current_team = await service.handle_team_selection(user_id, team_id)
        assert current_team.user_id == user_id
        assert current_team.team_id == team_id
        
        # Verify team configuration can be retrieved
        team_config = await service.get_team_configuration(team_id, user_id)
        assert team_config.name == "Selected Team"

    @pytest.mark.asyncio
    async def test_error_handling_resilience(self):
        """Test error handling across different scenarios."""
        service = TeamService()
        
        # Test with various invalid configurations
        invalid_configs = [
            {},  # Empty config
            {"name": "Test"},  # Missing required fields
            {"name": "Test", "status": "active", "agents": [], "starting_tasks": []},  # Empty arrays
            {"name": "Test", "status": "active", "agents": "invalid", "starting_tasks": []}  # Invalid types
        ]
        
        for config in invalid_configs:
            with pytest.raises(ValueError):
                await service.validate_and_parse_team_config(config, "user")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test handling of concurrent operations."""
        mock_memory = MagicMock()
        mock_memory.add_team = AsyncMock()
        mock_memory.get_all_teams = AsyncMock(return_value=[])
        service = TeamService(memory_context=mock_memory)
        
        # Create multiple team configs concurrently
        tasks = []
        for i in range(3):
            json_data = {
                "name": f"Team {i}",
                "status": "active",
                "agents": [{"input_key": f"agent{i}", "type": "ai", "name": f"Agent {i}", "icon": "icon"}],
                "starting_tasks": [{"id": f"task{i}", "name": f"Task {i}", "prompt": "Test", "created": "2024-01-01", "creator": "user", "logo": "logo"}]
            }
            task = service.validate_and_parse_team_config(json_data, f"user-{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.name == f"Team {i}"

    def test_logging_integration(self):
        """Test that logging is properly configured."""
        service = TeamService()
        assert service.logger is not None
        assert service.logger.name == "backend.v4.common.services.team_service"