# Copyright (c) Microsoft. All rights reserved.
"""Tests for services/team_service.py."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src/backend to sys.path
_backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')
)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# Mock Azure modules before any imports
sys.modules.setdefault('azure', MagicMock())
sys.modules.setdefault('azure.ai', MagicMock())
sys.modules.setdefault('azure.ai.projects', MagicMock())
sys.modules.setdefault('azure.ai.projects.aio', MagicMock())
sys.modules.setdefault('azure.core', MagicMock())

# Mock azure.core.exceptions with real exception subclasses
class MockClientAuthenticationError(Exception):
    pass

class MockHttpResponseError(Exception):
    pass

class MockResourceNotFoundError(Exception):
    pass

mock_azure_core_exceptions = MagicMock()
mock_azure_core_exceptions.ClientAuthenticationError = MockClientAuthenticationError
mock_azure_core_exceptions.HttpResponseError = MockHttpResponseError
mock_azure_core_exceptions.ResourceNotFoundError = MockResourceNotFoundError
sys.modules['azure.core.exceptions'] = mock_azure_core_exceptions

# Mock azure.search
sys.modules.setdefault('azure.search', MagicMock())
sys.modules.setdefault('azure.search.documents', MagicMock())
mock_search_indexes = MagicMock()
mock_search_index_client_class = MagicMock()
mock_search_indexes.SearchIndexClient = mock_search_index_client_class
sys.modules['azure.search.documents.indexes'] = mock_search_indexes

# Mock common modules
mock_config = MagicMock()
mock_config.AZURE_SEARCH_ENDPOINT = 'https://test-search.search.windows.net'
mock_config.AZURE_OPENAI_DEPLOYMENT_NAME = 'gpt-4'
mock_config.AZURE_OPENAI_ENDPOINT = 'https://test-openai.openai.azure.com/'
mock_config.get_azure_credentials = MagicMock(return_value=MagicMock())

mock_config_module = MagicMock()
mock_config_module.config = mock_config
sys.modules['common.config.app_config'] = mock_config_module

# Mock database_base with a real class
class MockDatabaseBase:
    pass

mock_database_base_module = MagicMock()
mock_database_base_module.DatabaseBase = MockDatabaseBase
sys.modules['common.database.database_base'] = mock_database_base_module

# Mock common.models.messages with real dataclasses
from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class MockTeamAgent:
    input_key: str = ""
    type: str = ""
    name: str = ""
    deployment_name: str = ""
    system_message: str = ""
    description: str = ""
    use_file_search: bool = False
    vector_store_name: str = None
    use_knowledge_base: bool = False
    knowledge_base_name: str = None
    use_toolbox: bool = False
    toolbox_filter: str = None
    user_responses: bool = False
    coding_tools: bool = False
    temperature: float = None

@dataclass
class MockStartingTask:
    id: str = ""
    name: str = ""
    prompt: str = ""
    created: str = ""
    creator: str = ""
    logo: str = ""

@dataclass
class MockTeamConfiguration:
    id: str = ""
    session_id: str = ""
    team_id: str = ""
    name: str = ""
    status: str = ""
    deployment_name: str = ""
    created: str = ""
    created_by: str = ""
    agents: List[Any] = field(default_factory=list)
    description: str = ""
    logo: str = ""
    plan: str = ""
    starting_tasks: List[Any] = field(default_factory=list)
    user_id: str = ""
    is_default: bool = False

@dataclass
class MockUserCurrentTeam:
    user_id: str = ""
    team_id: str = ""

mock_messages = MagicMock()
mock_messages.TeamAgent = MockTeamAgent
mock_messages.StartingTask = MockStartingTask
mock_messages.TeamConfiguration = MockTeamConfiguration
mock_messages.UserCurrentTeam = MockUserCurrentTeam
sys.modules['common.models.messages'] = mock_messages

# Mock services.foundry_service
mock_foundry_service_module = MagicMock()
sys.modules.setdefault('services', MagicMock())
sys.modules['services.foundry_service'] = mock_foundry_service_module

import backend.services.team_service as team_service_module
from backend.services.team_service import TeamService

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _valid_agent_data(
    input_key="agent1",
    type="ai",
    name="TestAgent",
    **kwargs
):
    data = {"input_key": input_key, "type": type, "name": name}
    data.update(kwargs)
    return data


def _valid_task_data(
    id="task1",
    name="Test Task",
    prompt="Do something",
    created="2024-01-01",
    creator="user1",
    logo="logo.png",
    **kwargs
):
    data = {
        "id": id,
        "name": name,
        "prompt": prompt,
        "created": created,
        "creator": creator,
        "logo": logo,
    }
    data.update(kwargs)
    return data


def _valid_team_data(**kwargs):
    data = {
        "name": "Test Team",
        "status": "active",
        "agents": [_valid_agent_data()],
        "starting_tasks": [_valid_task_data()],
    }
    data.update(kwargs)
    return data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTeamServiceInitialization:
    def test_init_without_memory_context(self):
        service = TeamService()
        assert service.memory_context is None
        assert service.logger is not None
        assert service.search_endpoint == 'https://test-search.search.windows.net'

    def test_init_with_memory_context(self):
        mock_context = MagicMock(spec=MockDatabaseBase)
        service = TeamService(memory_context=mock_context)
        assert service.memory_context == mock_context

    def test_init_config_attributes(self):
        service = TeamService()
        assert service.search_endpoint == mock_config.AZURE_SEARCH_ENDPOINT


class TestTeamConfigurationValidation:
    @pytest.mark.asyncio
    async def test_validate_basic_valid_config(self):
        service = TeamService()
        result = await service.validate_and_parse_team_config(_valid_team_data(), "test-user")
        assert isinstance(result, MockTeamConfiguration)
        assert result.name == "Test Team"
        assert result.status == "active"
        assert result.created_by == "test-user"
        assert result.user_id == "test-user"
        assert len(result.agents) == 1
        assert len(result.starting_tasks) == 1

    @pytest.mark.asyncio
    async def test_validate_missing_name_raises_error(self):
        data = _valid_team_data()
        del data["name"]
        service = TeamService()
        with pytest.raises(ValueError, match="name"):
            await service.validate_and_parse_team_config(data, "user")

    @pytest.mark.asyncio
    async def test_validate_missing_status_raises_error(self):
        data = _valid_team_data()
        del data["status"]
        service = TeamService()
        with pytest.raises(ValueError, match="status"):
            await service.validate_and_parse_team_config(data, "user")

    @pytest.mark.asyncio
    async def test_validate_empty_agents_raises_error(self):
        data = _valid_team_data(agents=[])
        service = TeamService()
        with pytest.raises(ValueError, match="empty"):
            await service.validate_and_parse_team_config(data, "user")

    @pytest.mark.asyncio
    async def test_validate_invalid_agents_type_raises_error(self):
        data = _valid_team_data(agents="not_a_list")
        service = TeamService()
        with pytest.raises(ValueError, match="agents"):
            await service.validate_and_parse_team_config(data, "user")

    @pytest.mark.asyncio
    async def test_validate_empty_starting_tasks_raises_error(self):
        data = _valid_team_data(starting_tasks=[])
        service = TeamService()
        with pytest.raises(ValueError, match="empty"):
            await service.validate_and_parse_team_config(data, "user")

    @pytest.mark.asyncio
    async def test_validate_with_optional_fields(self):
        data = _valid_team_data(
            description="Test description",
            logo="team_logo.png",
            plan="weekly",
            deployment_name="gpt-4"
        )
        service = TeamService()
        result = await service.validate_and_parse_team_config(data, "user1")
        assert result.description == "Test description"
        assert result.logo == "team_logo.png"
        assert result.plan == "weekly"
        assert result.deployment_name == "gpt-4"

    @pytest.mark.asyncio
    async def test_validate_generates_unique_ids(self):
        service = TeamService()
        result1 = await service.validate_and_parse_team_config(_valid_team_data(), "user")
        result2 = await service.validate_and_parse_team_config(_valid_team_data(), "user")
        assert result1.id != result2.id
        assert result1.team_id != result2.team_id

    @pytest.mark.asyncio
    async def test_validate_multiple_agents(self):
        data = _valid_team_data(
            agents=[
                _valid_agent_data(input_key="a1", name="Agent1"),
                _valid_agent_data(input_key="a2", name="Agent2"),
            ]
        )
        service = TeamService()
        result = await service.validate_and_parse_team_config(data, "user")
        assert len(result.agents) == 2

    def test_validate_and_parse_agent_missing_field_raises_error(self):
        service = TeamService()
        for field in ["input_key", "type", "name"]:
            agent_data = _valid_agent_data()
            del agent_data[field]
            with pytest.raises(ValueError, match=field):
                service._validate_and_parse_agent(agent_data)

    def test_validate_and_parse_agent_valid(self):
        service = TeamService()
        agent_data = _valid_agent_data(
            deployment_name="gpt-4",
            system_message="You are helpful.",
            use_toolbox=True
        )
        result = service._validate_and_parse_agent(agent_data)
        assert isinstance(result, MockTeamAgent)
        assert result.name == "TestAgent"
        assert result.deployment_name == "gpt-4"
        assert result.use_toolbox is True

    def test_validate_and_parse_task_missing_field_raises_error(self):
        service = TeamService()
        for f in ["id", "name", "prompt", "created", "creator", "logo"]:
            task_data = _valid_task_data()
            del task_data[f]
            with pytest.raises(ValueError, match=f):
                service._validate_and_parse_task(task_data)

    def test_validate_and_parse_task_valid(self):
        service = TeamService()
        task_data = _valid_task_data()
        result = service._validate_and_parse_task(task_data)
        assert isinstance(result, MockStartingTask)
        assert result.name == "Test Task"
        assert result.prompt == "Do something"


class TestTeamCrudOperations:
    @pytest.mark.asyncio
    async def test_save_team_configuration_success(self):
        mock_context = MagicMock()
        mock_context.add_team = AsyncMock()
        service = TeamService(memory_context=mock_context)

        team_config = MockTeamConfiguration(id="test-id-123", name="Test Team")
        result = await service.save_team_configuration(team_config)
        assert result == "test-id-123"
        mock_context.add_team.assert_called_once_with(team_config)

    @pytest.mark.asyncio
    async def test_save_team_configuration_raises_on_db_error(self):
        mock_context = MagicMock()
        mock_context.add_team = AsyncMock(side_effect=Exception("DB error"))
        service = TeamService(memory_context=mock_context)

        team_config = MockTeamConfiguration(id="test-id", name="Test")
        with pytest.raises(ValueError, match="Failed to save"):
            await service.save_team_configuration(team_config)

    @pytest.mark.asyncio
    async def test_get_team_configuration_success(self):
        mock_context = MagicMock()
        expected = MockTeamConfiguration(id="test-id", name="Test Team")
        mock_context.get_team = AsyncMock(return_value=expected)
        service = TeamService(memory_context=mock_context)

        result = await service.get_team_configuration("test-id", "user1")
        assert result == expected
        mock_context.get_team.assert_called_once_with("test-id")

    @pytest.mark.asyncio
    async def test_get_team_configuration_not_found_returns_none(self):
        mock_context = MagicMock()
        mock_context.get_team = AsyncMock(return_value=None)
        service = TeamService(memory_context=mock_context)

        result = await service.get_team_configuration("nonexistent", "user1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_team_configuration_error_returns_none(self):
        mock_context = MagicMock()
        mock_context.get_team = AsyncMock(side_effect=ValueError("DB error"))
        service = TeamService(memory_context=mock_context)

        result = await service.get_team_configuration("test-id", "user1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_team_configuration_success(self):
        mock_context = MagicMock()
        mock_context.delete_team = AsyncMock(return_value=True)
        service = TeamService(memory_context=mock_context)

        result = await service.delete_team_configuration("test-id", "user1")
        assert result is True
        mock_context.delete_team.assert_called_once_with("test-id")

    @pytest.mark.asyncio
    async def test_delete_team_configuration_not_found(self):
        mock_context = MagicMock()
        mock_context.delete_team = AsyncMock(return_value=False)
        service = TeamService(memory_context=mock_context)

        result = await service.delete_team_configuration("nonexistent", "user1")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_user_current_team_success(self):
        mock_context = MagicMock()
        mock_context.delete_current_team = AsyncMock()
        service = TeamService(memory_context=mock_context)

        result = await service.delete_user_current_team("user1")
        assert result is True
        mock_context.delete_current_team.assert_called_once_with("user1")

    @pytest.mark.asyncio
    async def test_delete_user_current_team_exception_returns_false(self):
        mock_context = MagicMock()
        mock_context.delete_current_team = AsyncMock(side_effect=Exception("Error"))
        service = TeamService(memory_context=mock_context)

        result = await service.delete_user_current_team("user1")
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_team_selection_success(self):
        mock_context = MagicMock()
        mock_context.delete_current_team = AsyncMock()
        mock_context.set_current_team = AsyncMock()
        service = TeamService(memory_context=mock_context)

        result = await service.handle_team_selection("user1", "team1")
        assert isinstance(result, MockUserCurrentTeam)
        assert result.user_id == "user1"
        assert result.team_id == "team1"
        mock_context.delete_current_team.assert_called_once_with("user1")
        mock_context.set_current_team.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_team_selection_exception_returns_none(self):
        mock_context = MagicMock()
        mock_context.delete_current_team = AsyncMock(side_effect=Exception("Error"))
        service = TeamService(memory_context=mock_context)

        result = await service.handle_team_selection("user1", "team1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_team_configurations_success(self):
        mock_context = MagicMock()
        configs = [
            MockTeamConfiguration(id="team1"),
            MockTeamConfiguration(id="team2"),
        ]
        mock_context.get_all_teams = AsyncMock(return_value=configs)
        service = TeamService(memory_context=mock_context)

        result = await service.get_all_team_configurations()
        assert len(result) == 2
        assert result[0].id == "team1"

    @pytest.mark.asyncio
    async def test_get_all_team_configurations_error_returns_empty(self):
        mock_context = MagicMock()
        mock_context.get_all_teams = AsyncMock(side_effect=ValueError("Error"))
        service = TeamService(memory_context=mock_context)

        result = await service.get_all_team_configurations()
        assert result == []


class TestExtractModelsFromAgent:
    def test_extract_from_agent_deployment_name(self):
        service = TeamService()
        agent = {"name": "TestAgent", "deployment_name": "gpt-4o"}
        models = service.extract_models_from_agent(agent)
        assert "gpt-4o" in models

    def test_agent_without_deployment_name_returns_empty(self):
        service = TeamService()
        agent = {"name": "SomeAgent"}
        models = service.extract_models_from_agent(agent)
        assert models == set()

    def test_extract_from_agent_model_field(self):
        service = TeamService()
        agent = {"name": "TestAgent", "model": "gpt-35-turbo"}
        models = service.extract_models_from_agent(agent)
        assert "gpt-35-turbo" in models

    def test_extract_from_agent_config_fields(self):
        service = TeamService()
        agent = {
            "name": "TestAgent",
            "config": {"model": "gpt-4", "engine": "gpt-35-turbo"}
        }
        models = service.extract_models_from_agent(agent)
        assert "gpt-4" in models
        assert "gpt-35-turbo" in models

    def test_extract_from_empty_agent(self):
        service = TeamService()
        agent = {"name": "TestAgent"}
        models = service.extract_models_from_agent(agent)
        assert isinstance(models, set)

    def test_extract_from_agent_instructions(self):
        service = TeamService()
        agent = {"name": "A", "instructions": "Use gpt-5.1 for this"}
        models = service.extract_models_from_agent(agent)
        assert any("gpt-5" in m for m in models)

    def test_extract_from_agent_system_message_fallback(self):
        service = TeamService()
        agent = {"name": "A", "system_message": "Prefer claude-3-opus"}
        models = service.extract_models_from_agent(agent)
        assert any("claude-3" in m for m in models)


class TestExtractModelsFromText:
    def test_matches_gpt5_variants(self):
        service = TeamService()
        models = service.extract_models_from_text("gpt-5.4-mini and gpt-5")
        assert any("gpt-5" in m for m in models)

    def test_matches_other_families(self):
        service = TeamService()
        models = service.extract_models_from_text(
            "claude-2 mistral-large gemini-pro text-embedding-ada davinci-3"
        )
        assert len(models) >= 3

    def test_no_matches_returns_empty(self):
        service = TeamService()
        assert service.extract_models_from_text("no model here") == set()


class TestExtractTeamLevelModels:
    def test_top_level_fields(self):
        service = TeamService()
        models = service.extract_team_level_models(
            {"default_model": "GPT-4", "model": "gpt-35", "llm_model": "o3"}
        )
        assert "gpt-4" in models
        assert "o3" in models

    def test_nested_settings_and_environment(self):
        service = TeamService()
        cfg = {
            "settings": {"model": "gpt-4", "deployment_name": "dep1"},
            "environment": {"model": "gpt-5", "openai_deployment": "dep2"},
        }
        models = service.extract_team_level_models(cfg)
        assert "dep1" in models
        assert "dep2" in models

    def test_empty_config(self):
        service = TeamService()
        assert service.extract_team_level_models({}) == set()


class TestValidateTeamModels:
    @pytest.mark.asyncio
    async def test_all_models_available(self):
        service = TeamService()
        foundry = MagicMock()
        foundry.list_model_deployments = AsyncMock(
            return_value=[{"name": "custom-model", "status": "Succeeded"}]
        )
        with patch.object(team_service_module, "FoundryService", return_value=foundry):
            cfg = {"agents": [{"deployment_name": "custom-model"}]}
            is_valid, missing = await service.validate_team_models(cfg)
        assert is_valid is True
        assert missing == []

    @pytest.mark.asyncio
    async def test_missing_model_reported(self):
        service = TeamService()
        foundry = MagicMock()
        foundry.list_model_deployments = AsyncMock(return_value=[])
        with patch.object(team_service_module, "FoundryService", return_value=foundry):
            cfg = {"agents": [{"deployment_name": "not-deployed"}]}
            is_valid, missing = await service.validate_team_models(cfg)
        assert is_valid is False
        assert "not-deployed" in missing

    @pytest.mark.asyncio
    async def test_bypassed_models_skipped(self):
        service = TeamService()
        foundry = MagicMock()
        foundry.list_model_deployments = AsyncMock(return_value=[])
        with patch.object(team_service_module, "FoundryService", return_value=foundry):
            cfg = {"agents": [{"deployment_name": "gpt-5.4-mini"}]}
            is_valid, missing = await service.validate_team_models(cfg)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_default_model_when_no_agents(self):
        service = TeamService()
        mock_config.AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-5"
        foundry = MagicMock()
        foundry.list_model_deployments = AsyncMock(return_value=[])
        with patch.object(team_service_module, "FoundryService", return_value=foundry):
            is_valid, missing = await service.validate_team_models({"agents": []})
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_exception_returns_valid(self):
        service = TeamService()
        with patch.object(
            team_service_module, "FoundryService", side_effect=Exception("boom")
        ):
            is_valid, missing = await service.validate_team_models({"agents": []})
        assert is_valid is True
        assert missing == []


class TestDeploymentStatusSummary:
    @pytest.mark.asyncio
    async def test_summary_categorizes_deployments(self):
        service = TeamService()
        foundry = MagicMock()
        foundry.list_model_deployments = AsyncMock(
            return_value=[
                {"name": "ok", "status": "Succeeded"},
                {"name": "bad", "status": "Failed"},
                {"name": "wait", "status": "Running"},
            ]
        )
        with patch.object(team_service_module, "FoundryService", return_value=foundry):
            summary = await service.get_deployment_status_summary()
        assert summary["total_deployments"] == 3
        assert "ok" in summary["successful_deployments"]
        assert "bad" in summary["failed_deployments"]
        assert "wait" in summary["pending_deployments"]

    @pytest.mark.asyncio
    async def test_summary_error(self):
        service = TeamService()
        with patch.object(
            team_service_module, "FoundryService", side_effect=Exception("boom")
        ):
            summary = await service.get_deployment_status_summary()
        assert "error" in summary


class TestSearchIndexExtraction:
    def test_extract_index_names_from_rag_agents(self):
        service = TeamService()
        cfg = {
            "agents": [
                {"type": "RAG", "index_name": "idx-1"},
                {"type": "ai", "index_name": "ignored"},
                {"type": "rag", "index_name": "idx-1"},
            ]
        }
        names = service.extract_index_names(cfg)
        assert names == ["idx-1"]

    def test_extract_index_names_empty(self):
        service = TeamService()
        assert service.extract_index_names({"agents": []}) == []

    def test_has_rag_or_search_agents_true(self):
        service = TeamService()
        assert service.has_rag_or_search_agents({"agents": [{"type": "rag"}]}) is True

    def test_has_rag_or_search_agents_false(self):
        service = TeamService()
        assert service.has_rag_or_search_agents({"agents": [{"type": "ai"}]}) is False


class TestValidateTeamSearchIndexes:
    @pytest.mark.asyncio
    async def test_no_indexes_no_rag_skips(self):
        service = TeamService()
        is_valid, errors = await service.validate_team_search_indexes(
            {"agents": [{"type": "ai"}]}
        )
        assert is_valid is True
        assert errors == []

    @pytest.mark.asyncio
    async def test_rag_but_no_endpoint(self):
        service = TeamService()
        service.search_endpoint = ""
        cfg = {"agents": [{"type": "rag", "index_name": "idx-1"}]}
        is_valid, errors = await service.validate_team_search_indexes(cfg)
        assert is_valid is False
        assert errors

    @pytest.mark.asyncio
    async def test_rag_without_specific_index(self):
        service = TeamService()
        service.search_endpoint = "https://s.search.windows.net"
        cfg = {"agents": [{"type": "rag"}]}
        is_valid, errors = await service.validate_team_search_indexes(cfg)
        assert is_valid is True
        assert errors == []

    @pytest.mark.asyncio
    async def test_valid_indexes(self):
        service = TeamService()
        service.search_endpoint = "https://s.search.windows.net"
        cfg = {"agents": [{"type": "rag", "index_name": "idx-1"}]}
        client = MagicMock()
        client.get_index = MagicMock(return_value=MagicMock())
        with patch.object(team_service_module, "SearchIndexClient", return_value=client):
            is_valid, errors = await service.validate_team_search_indexes(cfg)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_invalid_index(self):
        service = TeamService()
        service.search_endpoint = "https://s.search.windows.net"
        cfg = {"agents": [{"type": "rag", "index_name": "missing"}]}
        client = MagicMock()
        client.get_index = MagicMock(
            side_effect=team_service_module.ResourceNotFoundError("nope")
        )
        with patch.object(team_service_module, "SearchIndexClient", return_value=client):
            is_valid, errors = await service.validate_team_search_indexes(cfg)
        assert is_valid is False
        assert errors

    @pytest.mark.asyncio
    async def test_validation_exception(self):
        service = TeamService()
        service.search_endpoint = "https://s.search.windows.net"
        cfg = {"agents": [{"type": "rag", "index_name": "idx"}]}
        with patch.object(
            team_service_module,
            "SearchIndexClient",
            side_effect=Exception("boom"),
        ):
            is_valid, errors = await service.validate_team_search_indexes(cfg)
        assert is_valid is False


class TestValidateSingleIndex:
    @pytest.mark.asyncio
    async def test_found(self):
        service = TeamService()
        client = MagicMock()
        client.get_index = MagicMock(return_value=MagicMock())
        with patch.object(team_service_module, "SearchIndexClient", return_value=client):
            is_valid, err = await service.validate_single_index("idx")
        assert is_valid is True
        assert err == ""

    @pytest.mark.asyncio
    async def test_index_none(self):
        service = TeamService()
        client = MagicMock()
        client.get_index = MagicMock(return_value=None)
        with patch.object(team_service_module, "SearchIndexClient", return_value=client):
            is_valid, err = await service.validate_single_index("idx")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_not_found(self):
        service = TeamService()
        client = MagicMock()
        client.get_index = MagicMock(
            side_effect=team_service_module.ResourceNotFoundError("x")
        )
        with patch.object(team_service_module, "SearchIndexClient", return_value=client):
            is_valid, err = await service.validate_single_index("idx")
        assert is_valid is False
        assert "does not exist" in err

    @pytest.mark.asyncio
    async def test_auth_error(self):
        service = TeamService()
        client = MagicMock()
        client.get_index = MagicMock(
            side_effect=team_service_module.ClientAuthenticationError("x")
        )
        with patch.object(team_service_module, "SearchIndexClient", return_value=client):
            is_valid, err = await service.validate_single_index("idx")
        assert is_valid is False
        assert "Authentication failed" in err

    @pytest.mark.asyncio
    async def test_http_error(self):
        service = TeamService()
        client = MagicMock()
        client.get_index = MagicMock(
            side_effect=team_service_module.HttpResponseError("x")
        )
        with patch.object(team_service_module, "SearchIndexClient", return_value=client):
            is_valid, err = await service.validate_single_index("idx")
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_generic_error(self):
        service = TeamService()
        client = MagicMock()
        client.get_index = MagicMock(side_effect=Exception("weird"))
        with patch.object(team_service_module, "SearchIndexClient", return_value=client):
            is_valid, err = await service.validate_single_index("idx")
        assert is_valid is False


class TestSearchIndexSummary:
    @pytest.mark.asyncio
    async def test_no_endpoint(self):
        service = TeamService()
        service.search_endpoint = ""
        summary = await service.get_search_index_summary()
        assert "error" in summary

    @pytest.mark.asyncio
    async def test_success(self):
        service = TeamService()
        service.search_endpoint = "https://s.search.windows.net"
        idx = MagicMock()
        idx.name = "idx-1"
        client = MagicMock()
        client.list_indexes = MagicMock(return_value=[idx])
        with patch.object(team_service_module, "SearchIndexClient", return_value=client):
            summary = await service.get_search_index_summary()
        assert summary["total_indexes"] == 1
        assert "idx-1" in summary["available_indexes"]

    @pytest.mark.asyncio
    async def test_error(self):
        service = TeamService()
        service.search_endpoint = "https://s.search.windows.net"
        with patch.object(
            team_service_module, "SearchIndexClient", side_effect=Exception("boom")
        ):
            summary = await service.get_search_index_summary()
        assert "error" in summary

