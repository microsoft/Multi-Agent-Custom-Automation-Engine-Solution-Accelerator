"""
Test configuration for v4 API router tests.
Sets up mocks before module imports to enable proper test discovery.
"""

import os
import sys
from enum import Enum
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

# Add backend to path FIRST
# From src/tests/backend/v4/api/conftest.py, go up to src/ then into backend/
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Set up environment variables before any imports
os.environ.update({
    'APPLICATIONINSIGHTS_CONNECTION_STRING': 'InstrumentationKey=test-key',
    'AZURE_AI_SUBSCRIPTION_ID': 'test-subscription',
    'AZURE_AI_RESOURCE_GROUP': 'test-rg',
    'AZURE_AI_PROJECT_NAME': 'test-project',
    'AZURE_AI_AGENT_ENDPOINT': 'https://test.agent.endpoint.com',
    'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
    'AZURE_OPENAI_API_KEY': 'test-key',
    'AZURE_OPENAI_API_VERSION': '2023-05-15',
    'COSMOSDB_ENDPOINT': 'https://mock-endpoint',
    'COSMOSDB_KEY': 'mock-key',
    'COSMOSDB_DATABASE': 'mock-database',
    'COSMOSDB_CONTAINER': 'mock-container',
    'USER_LOCAL_BROWSER_LANGUAGE': 'en-US',
})

# Mock Azure dependencies with proper module structure
azure_monitor_mock = MagicMock()
sys.modules["azure.monitor"] = azure_monitor_mock
sys.modules["azure.monitor.events"] = MagicMock()
sys.modules["azure.monitor.events.extension"] = MagicMock()
sys.modules["azure.monitor.opentelemetry"] = MagicMock()
azure_monitor_mock.opentelemetry = sys.modules["azure.monitor.opentelemetry"]
azure_monitor_mock.opentelemetry.configure_azure_monitor = MagicMock()

azure_ai_mock = type(sys)("azure.ai")
azure_ai_agents_mock = type(sys)("azure.ai.agents")
azure_ai_agents_mock.aio = MagicMock()
azure_ai_mock.agents = azure_ai_agents_mock
sys.modules["azure.ai"] = azure_ai_mock
sys.modules["azure.ai.agents"] = azure_ai_agents_mock
sys.modules["azure.ai.agents.aio"] = azure_ai_agents_mock.aio

azure_ai_projects_mock = type(sys)("azure.ai.projects")
azure_ai_projects_mock.models = MagicMock()
azure_ai_projects_mock.aio = MagicMock()
sys.modules["azure.ai.projects"] = azure_ai_projects_mock
sys.modules["azure.ai.projects.models"] = azure_ai_projects_mock.models
sys.modules["azure.ai.projects.aio"] = azure_ai_projects_mock.aio

# Cosmos DB mocks with nested structure
sys.modules["azure.cosmos"] = MagicMock()
cosmos_aio_mock = type(sys)("azure.cosmos.aio")  # Create a real module object
cosmos_aio_mock.CosmosClient = MagicMock()  # Add CosmosClient
cosmos_aio_mock._database = MagicMock()
cosmos_aio_mock._database.DatabaseProxy = MagicMock()
cosmos_aio_mock._container = MagicMock()
cosmos_aio_mock._container.ContainerProxy = MagicMock()
sys.modules["azure.cosmos.aio"] = cosmos_aio_mock
sys.modules["azure.cosmos.aio._database"] = cosmos_aio_mock._database
sys.modules["azure.cosmos.aio._container"] = cosmos_aio_mock._container

sys.modules["azure.identity"] = MagicMock()
sys.modules["azure.identity.aio"] = MagicMock()

# Create proper enum mocks for agent_framework
class MockRole(str, Enum):
    """Mock Role enum for agent_framework."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

# Create proper base classes for agent_framework
class MockBaseAgent:
    """Mock base agent class."""
    __name__ = "BaseAgent"
    __module__ = "agent_framework"
    __qualname__ = "BaseAgent"

class MockChatAgent:
    """Mock chat agent class."""
    __name__ = "ChatAgent"
    __module__ = "agent_framework"
    __qualname__ = "ChatAgent"

# Mock agent framework dependencies
agent_framework_mock = type(sys)("agent_framework")
agent_framework_mock.azure = type(sys)("agent_framework.azure")
agent_framework_mock.azure.AzureOpenAIChatClient = MagicMock()
agent_framework_mock._workflows = type(sys)("agent_framework._workflows")
agent_framework_mock._workflows._magentic = type(sys)("agent_framework._workflows._magentic")
agent_framework_mock._workflows._magentic.MagenticContext = MagicMock()
agent_framework_mock._workflows._magentic.StandardMagenticManager = MagicMock()
agent_framework_mock._workflows._magentic.ORCHESTRATOR_FINAL_ANSWER_PROMPT = "mock_prompt"
agent_framework_mock._workflows._magentic.ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT = "mock_prompt"
agent_framework_mock._workflows._magentic.ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT = "mock_prompt"
agent_framework_mock._workflows._magentic.ORCHESTRATOR_PROGRESS_LEDGER_PROMPT = "mock_prompt"
agent_framework_mock.AgentResponse = MagicMock()
agent_framework_mock.AgentResponseUpdate = MagicMock()
agent_framework_mock.AgentRunUpdateEvent = MagicMock()
agent_framework_mock.AgentThread = MagicMock()
agent_framework_mock.BaseAgent = MockBaseAgent
agent_framework_mock.ChatAgent = MockChatAgent
agent_framework_mock.ChatMessage = MagicMock()
agent_framework_mock.ChatOptions = MagicMock()
agent_framework_mock.Content = MagicMock()
agent_framework_mock.ExecutorCompletedEvent = MagicMock()
agent_framework_mock.GroupChatRequestSentEvent = MagicMock()
agent_framework_mock.GroupChatResponseReceivedEvent = MagicMock()
agent_framework_mock.HostedCodeInterpreterTool = MagicMock()
agent_framework_mock.HostedMCPTool = MagicMock()
agent_framework_mock.ImageContent = MagicMock()
agent_framework_mock.ImageDetail = MagicMock()
agent_framework_mock.ImageUrl = MagicMock()
agent_framework_mock.InMemoryCheckpointStorage = MagicMock()
agent_framework_mock.MagenticBuilder = MagicMock()
agent_framework_mock.MagenticOrchestratorEvent = MagicMock()
agent_framework_mock.MagenticProgressLedger = MagicMock()
agent_framework_mock.MCPStreamableHTTPTool = MagicMock()
agent_framework_mock.Role = MockRole
agent_framework_mock.TemplatedChatAgent = MagicMock()
agent_framework_mock.TextContent = MagicMock()
agent_framework_mock.UsageDetails = MagicMock()
agent_framework_mock.WorkflowOutputEvent = MagicMock()
sys.modules["agent_framework"] = agent_framework_mock
sys.modules["agent_framework.azure"] = agent_framework_mock.azure
sys.modules["agent_framework._workflows"] = agent_framework_mock._workflows
sys.modules["agent_framework._workflows._magentic"] = agent_framework_mock._workflows._magentic
sys.modules["agent_framework_azure_ai"] = MagicMock()
sys.modules["magentic"] = MagicMock()

# OpenTelemetry mocks
otel_mock = type(sys)("opentelemetry")
otel_mock.trace = MagicMock()
sys.modules["opentelemetry"] = otel_mock
sys.modules["opentelemetry.trace"] = otel_mock.trace
sys.modules["opentelemetry.sdk"] = MagicMock()
sys.modules["opentelemetry.sdk.trace"] = MagicMock()

# ---------------------------------------------------------------------------
# Shared Fixtures - Simple approach: create test client and don't pre-patch
# ---------------------------------------------------------------------------

@pytest.fixture
def create_test_client():
    """Create FastAPI TestClient with inline mocks."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    
    # Import router - all dependencies are stubbed in sys.modules
    from v4.api import router as router_module
    
    # Now replace everything in router's namespace with mocks
    # Auth
    router_module.get_authenticated_user_details = MagicMock(return_value={"user_principal_id": "test-user-123"})
    
    # Database
    mock_db = AsyncMock()
    mock_db.get_current_team = AsyncMock(return_value=None)
    mock_db.get_team_by_id = AsyncMock(return_value=None)
    mock_db.get_plan_by_plan_id = AsyncMock(return_value=None)
    mock_db.get_all_plans_by_team_id_status = AsyncMock(return_value=[])
    mock_db.add_plan = AsyncMock()
    mock_db_factory = MagicMock()
    mock_db_factory.get_database = AsyncMock(return_value=mock_db)
    router_module.DatabaseFactory = mock_db_factory
    
    # Services
    router_module.PlanService = MagicMock()
    router_module.PlanService.handle_plan_approval = AsyncMock(return_value={"status": "success"})
    router_module.PlanService.handle_human_clarification = AsyncMock(return_value={"status": "success"})
    router_module.PlanService.handle_agent_messages = AsyncMock(return_value={"status": "success"})
    
    team_svc_instance = AsyncMock()
    team_svc_instance.handle_team_selection = AsyncMock(return_value=MagicMock(team_id="team-123"))
    team_svc_instance.get_team_configuration = AsyncMock(return_value=None)
    team_svc_instance.get_all_team_configurations = AsyncMock(return_value=[])
    team_svc_instance.delete_team_configuration = AsyncMock(return_value=True)
    team_svc_instance.validate_team_models = AsyncMock(return_value=(True, []))
    team_svc_instance.validate_team_search_indexes = AsyncMock(return_value=(True, []))
    team_svc_instance.validate_and_parse_team_config = AsyncMock()
    team_svc_instance.save_team_configuration = AsyncMock(return_value="team-123")
    router_module.TeamService = MagicMock(return_value=team_svc_instance)
    
    orch_mgr_instance = AsyncMock()
    orch_mgr_instance.run_orchestration = AsyncMock()
    router_module.OrchestrationManager = MagicMock(return_value=orch_mgr_instance)
    router_module.OrchestrationManager.get_current_or_new_orchestration = AsyncMock(return_value=orch_mgr_instance)
    
    # Utils
    router_module.find_first_available_team = MagicMock(return_value="team-123")
    router_module.rai_success = AsyncMock(return_value=True)
    router_module.rai_validate_team_config = MagicMock(return_value=(True, None))
    router_module.track_event_if_configured = MagicMock(return_value=None)
    
    # Configs
    conn_cfg = MagicMock()
    conn_cfg.add_connection = AsyncMock()
    conn_cfg.close_connection = AsyncMock()
    conn_cfg.send_status_update_async = AsyncMock()
    router_module.connection_config = conn_cfg
    
    orch_cfg = MagicMock()
    orch_cfg.approvals = {}
    orch_cfg.clarifications = {}
    orch_cfg.set_approval_result = Mock()
    orch_cfg.set_clarification_result = Mock()
    router_module.orchestration_config = orch_cfg
    
    team_cfg = MagicMock()
    team_cfg.set_current_team = Mock()
    router_module.team_config = team_cfg
    
    # Create test app with router
    app = FastAPI()
    app.include_router(router_module.app_v4)
    
    client = TestClient(app)
    client.headers = {"Authorization": "Bearer test-token"}
    
    # Store mocks as client attributes for test access
    client._mock_db = mock_db
    client._mock_team_svc = team_svc_instance
    client._mock_auth = router_module.get_authenticated_user_details
    client._mock_utils = {
        "find_first_available_team": router_module.find_first_available_team,
        "rai_success": router_module.rai_success,
        "rai_validate_team_config": router_module.rai_validate_team_config,
    }
    client._mock_configs = {
        "connection_config": conn_cfg,
        "orchestration_config": orch_cfg,
        "team_config": team_cfg,
    }
    
    yield client


# ---------------------------------------------------------------------------
# Additional Fixtures for Test Access
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_database(create_test_client):
    """Provide access to the mock database."""
    return create_test_client._mock_db


@pytest.fixture
def mock_services(create_test_client):
    """Provide access to mock services."""
    # Return a callable that always returns the same instance
    class ServiceGetter:
        def __call__(self):
            return create_test_client._mock_team_svc
    
    return {
        "team_service": ServiceGetter()
    }


@pytest.fixture
def mock_auth(create_test_client):
    """Provide access to mock authentication."""
    return create_test_client._mock_auth


@pytest.fixture
def mock_utils(create_test_client):
    """Provide access to mock utilities."""
    return create_test_client._mock_utils


@pytest.fixture
def mock_configs(create_test_client):
    """Provide access to mock configurations."""
    return create_test_client._mock_configs
