"""
Unit tests for v4 OrchestrationManager.

Tests cover:
- OrchestrationManager initialization
- init_orchestration (workflow creation with agents, clients, callbacks)
- get_current_or_new_orchestration (retrieval, creation, team switching)
- run_orchestration (execution flow, event handling, error handling)
- Agent extraction (inner agents vs direct agents)
- State clearing between runs
- Error handling and edge cases
"""

import asyncio
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
import sys
from pathlib import Path
from typing import List
import re

# Add the backend path to sys.path for imports
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# ===== Mock agent_framework classes =====
class Role:
    ASSISTANT = "assistant"
    USER = "user"

class TextContent:
    def __init__(self, text=""):
        self.text = text

class ChatMessage:
    def __init__(self, role=None, contents=None):
        self.role = role or Role.ASSISTANT
        self.contents = contents or []

class WorkflowOutputEvent:
    def __init__(self, data=None):
        self.data = data

class MagenticOrchestratorMessageEvent:
    def __init__(self, message=None):
        self.message = message

class MagenticAgentDeltaEvent:
    def __init__(self, message=None, agent_name="", agent_id="", delta=""):
        self.message = message
        self.agent_name = agent_name
        self.agent_id = agent_id
        self.delta = delta

class MagenticAgentMessageEvent:
    def __init__(self, message=None, agent_name="", agent_id=""):
        self.message = message
        self.agent_name = agent_name
        self.agent_id = agent_id

class MagenticFinalResultEvent:
    def __init__(self, message=None):
        self.message = message

# ===== Mock v4 classes =====
class TeamConfiguration:
    def __init__(self, name="", deployment_name="", agents=None):
        self.name = name
        self.deployment_name = deployment_name
        self.agents = agents or []

class WebsocketMessageType:
    PLAN_APPROVAL_REQUEST = "plan_approval_request"
    PLAN_APPROVAL_RESPONSE = "plan_approval_response"
    ERROR = "error"
    FINAL_RESULT_MESSAGE = "final_result"

class DatabaseBase:
    """Mock DatabaseBase class."""
    pass

class TeamService:
    """Mock TeamService class."""
    pass

class Config:
    """Mock config class."""
    def __init__(self):
        self.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint.com"
        self.AZURE_CLIENT_ID = "client-123"
        self.get_azure_credential = Mock(return_value=Mock())

config = Config()
connection_config = Mock()
connection_config.send_status_update_async = AsyncMock()
orchestration_config = Mock()
mock_orch_config = orchestration_config
mock_conn_config = connection_config
mock_config = config

# Create mock class variables for tests (these will be used in exec namespace)
mock_client_class = Mock(return_value=Mock())
mock_manager_class = Mock(return_value=Mock())
mock_builder_class = Mock(return_value=Mock())
mock_storage_class = Mock(return_value=Mock())
mock_factory_class = Mock(return_value=Mock())
mock_callback = Mock()
mock_streaming_callback = Mock()

# Make the classes use the mocks
AzureAIAgentClient = mock_client_class
HumanApprovalMagenticManager = mock_manager_class
MagenticBuilder = mock_builder_class
InMemoryCheckpointStorage = mock_storage_class
MagenticAgentFactory = mock_factory_class

def agent_response_callback(*args, **kwargs):
    return mock_callback(*args, **kwargs)

def streaming_agent_response_callback(*args, **kwargs):
    return mock_streaming_callback(*args, **kwargs)

# ===== Load OrchestrationManager with exec() =====
manager_file_path = backend_path / "v4" / "orchestration" / "orchestration_manager.py"
with open(manager_file_path, "r", encoding="utf-8") as f:
    manager_code = f.read()

# Replace all v4 imports
manager_code = manager_code.replace("from agent_framework_azure_ai import AzureAIAgentClient", "# AzureAIAgentClient")
manager_code = re.sub(
    r'from agent_framework import \([^)]+\)',
    '# agent_framework imports',
    manager_code,
    flags=re.DOTALL
)
manager_code = manager_code.replace("from common.config.app_config import config", "# config")
manager_code = manager_code.replace("from common.models.messages_af import TeamConfiguration", "# TeamConfiguration")
manager_code = manager_code.replace("from common.database.database_base import DatabaseBase", "# DatabaseBase")
manager_code = manager_code.replace("from v4.common.services.team_service import TeamService", "# TeamService")
manager_code = re.sub(
    r'from v4\.callbacks\.response_handlers import \([^)]+\)',
    '# response_handlers',
    manager_code,
    flags=re.DOTALL
)
manager_code = manager_code.replace("from v4.config.settings import connection_config, orchestration_config", "# settings")
manager_code = manager_code.replace("from v4.models.messages import WebsocketMessageType", "# WebsocketMessageType")
manager_code = manager_code.replace("from v4.orchestration.human_approval_manager import HumanApprovalMagenticManager", "# HumanApprovalMagenticManager")
manager_code = manager_code.replace("from v4.magentic_agents.magentic_agent_factory import MagenticAgentFactory", "# MagenticAgentFactory")

# Create namespace with all dependencies
manager_namespace = {
    'asyncio': asyncio,
    'logging': __import__('logging'),
    'uuid': uuid,
    'List': List,
    'Optional': __import__('typing').Optional,
    'ChatMessage': ChatMessage,
    'WorkflowOutputEvent': WorkflowOutputEvent,
    'MagenticOrchestratorMessageEvent': MagenticOrchestratorMessageEvent,
    'MagenticAgentDeltaEvent': MagenticAgentDeltaEvent,
    'MagenticAgentMessageEvent': MagenticAgentMessageEvent,
    'MagenticFinalResultEvent': MagenticFinalResultEvent,
    'TeamConfiguration': TeamConfiguration,
    'WebsocketMessageType': WebsocketMessageType,
    'DatabaseBase': DatabaseBase,
    'TeamService': TeamService,
    'MagenticAgentFactory': MagenticAgentFactory,
    'HumanApprovalMagenticManager': HumanApprovalMagenticManager,
    'AzureAIAgentClient': AzureAIAgentClient,
    'MagenticBuilder': MagenticBuilder,
    'InMemoryCheckpointStorage': InMemoryCheckpointStorage,
    'config': config,
    'connection_config': connection_config,
    'orchestration_config': orchestration_config,
    'agent_response_callback': agent_response_callback,
    'streaming_agent_response_callback': streaming_agent_response_callback,
    'Role': Role,
    'TextContent': TextContent,
}

exec(manager_code, manager_namespace)
OrchestrationManager = manager_namespace['OrchestrationManager']


# Fixture to reset global mocks before each test
@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all global mocks before each test to prevent test pollution."""
    mock_client_class.reset_mock()
    mock_client_class.side_effect = None
    mock_client_class.return_value = Mock()
    
    mock_manager_class.reset_mock()
    mock_manager_class.side_effect = None
    mock_manager_class.return_value = Mock()
    
    mock_builder_class.reset_mock()
    mock_builder_class.side_effect = None
    mock_builder_class.return_value = Mock()
    
    mock_storage_class.reset_mock()
    mock_storage_class.side_effect = None
    mock_storage_class.return_value = Mock()
    
    mock_factory_class.reset_mock()
    mock_factory_class.side_effect = None
    mock_factory_class.return_value = Mock()
    
    mock_callback.reset_mock()
    mock_callback.side_effect = None
    mock_callback.return_value = AsyncMock()
    
    mock_streaming_callback.reset_mock()
    mock_streaming_callback.side_effect = None
    
    # Reset config mocks
    mock_config.get_azure_credential = Mock(return_value=Mock())
    
    # Reset connection_config attributes explicitly
    connection_config.send_status_update_async = AsyncMock()
    connection_config.send_streaming_delta_async = AsyncMock()
    
    # Reset orchestration_config attributes explicitly (reset_mock doesn't clear attributes!)
    orchestration_config.get_current_orchestration = Mock(return_value=None)
    orchestration_config.get_or_create_orchestration = AsyncMock()
    orchestration_config.set_current_orchestration = Mock()
    orchestration_config.set_approval_pending = Mock()
    orchestration_config.is_approval_pending = Mock(return_value=False)
    orchestration_config.set_session_state = Mock()
    orchestration_config.get_session_state = Mock(return_value=None)
    orchestration_config.set_task_completed = Mock()
    orchestration_config.is_task_completed = Mock(return_value=False)
    
    yield


class TestOrchestrationManagerInit:
    """Test cases for OrchestrationManager initialization."""

    def test_init(self):
        """Test OrchestrationManager initialization."""
        manager = OrchestrationManager()
        
        assert manager.user_id is None
        assert manager.logger is not None


class TestInitOrchestration:
    """Test cases for init_orchestration class method."""

    @pytest.mark.asyncio
    async def test_init_orchestration_success(self):
        """Test successful orchestration initialization."""
        # Reset mocks
        mock_orch_config.max_rounds = 10
        mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.endpoint.com"
        mock_config.AZURE_CLIENT_ID = "client-123"
        mock_config.get_azure_credential.return_value = Mock()
        
        mock_chat_client = Mock()
        mock_client_class.return_value = mock_chat_client
        mock_client_class.reset_mock()
        
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager_class.reset_mock()
        
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage
        mock_storage_class.reset_mock()
        
        mock_workflow = Mock()
        mock_builder = MagicMock()
        mock_builder.participants = MagicMock(return_value=mock_builder)
        mock_builder.with_standard_manager = MagicMock(return_value=mock_builder)
        mock_builder.with_checkpointing = MagicMock(return_value=mock_builder)
        mock_builder.build = MagicMock(return_value=mock_workflow)
        mock_builder_class.return_value = mock_builder
        mock_builder_class.reset_mock()
        
        # Create mock agents with spec to prevent auto-attributes
        mock_agent1 = Mock(spec=['agent_name', '_agent'])
        mock_agent1.agent_name = "Agent1"
        mock_agent1._agent = Mock()  # Inner agent
        
        mock_agent2 = Mock(spec=['name', '_agent'])
        mock_agent2.name = "Agent2"
        mock_agent2._agent = None  # Direct agent (like ProxyAgent)
        
        agents = [mock_agent1, mock_agent2]
        
        team_config = TeamConfiguration(
            name="TestTeam",
            deployment_name="gpt-4",
            agents=[]
        )
        
        memory_store = Mock()
        
        result = await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=team_config,
            memory_store=memory_store,
            user_id="user123"
        )
        
        assert result == mock_workflow
        mock_client_class.assert_called_once()
        mock_manager_class.assert_called_once()
        mock_builder.build.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_orchestration_no_user_id(self):
        """Test init_orchestration raises error without user_id."""
        with pytest.raises(ValueError) as exc_info:
            await OrchestrationManager.init_orchestration(
                agents=[],
                team_config=Mock(),
                memory_store=Mock(),
                user_id=None
            )
        
        assert "user_id is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_init_orchestration_client_creation_error(self):
        """Test init_orchestration handles client creation error."""
        mock_orch_config.max_rounds = 10
        mock_config.get_azure_credential.return_value = Mock()
        mock_client_class.side_effect = Exception("Client creation failed")
        
        team_config = TeamConfiguration(
            name="TestTeam",
            deployment_name="gpt-4",
            agents=[]
        )
        
        with pytest.raises(Exception) as exc_info:
            await OrchestrationManager.init_orchestration(
                agents=[],
                team_config=team_config,
                memory_store=Mock(),
                user_id="user123"
            )
        
        assert "Client creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_init_orchestration_manager_creation_error(self):
        """Test init_orchestration handles manager creation error."""
        mock_orch_config.max_rounds = 10
        mock_config.get_azure_credential.return_value = Mock()
        mock_client_class.return_value = Mock()
        mock_manager_class.side_effect = Exception("Manager creation failed")
        
        team_config = TeamConfiguration(
            name="TestTeam",
            deployment_name="gpt-4",
            agents=[]
        )
        
        with pytest.raises(Exception) as exc_info:
            await OrchestrationManager.init_orchestration(
                agents=[],
                team_config=team_config,
                memory_store=Mock(),
                user_id="user123"
            )
        
        assert "Manager creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_init_orchestration_extracts_inner_agents(self):
        """Test init_orchestration extracts inner agents from wrappers."""
        mock_orch_config.max_rounds = 10
        mock_config.get_azure_credential.return_value = Mock()
        mock_client_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        mock_storage_class.return_value = Mock()
        
        mock_workflow = Mock()
        mock_builder = Mock()
        mock_builder.participants.return_value = mock_builder
        mock_builder.with_standard_manager.return_value = mock_builder
        mock_builder.with_checkpointing.return_value = mock_builder
        mock_builder.build.return_value = mock_workflow
        mock_builder_class.return_value = mock_builder
        
        # Agent with inner _agent
        mock_inner_agent = Mock()
        mock_wrapper_agent = Mock()
        mock_wrapper_agent.agent_name = "WrapperAgent"
        mock_wrapper_agent._agent = mock_inner_agent
        
        agents = [mock_wrapper_agent]
        
        team_config = TeamConfiguration(
            name="TestTeam",
            deployment_name="gpt-4",
            agents=[]
        )
        
        await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=team_config,
            memory_store=Mock(),
            user_id="user123"
        )
        
        # Verify participants called with inner agent
        call_kwargs = mock_builder.participants.call_args[1]
        assert call_kwargs["WrapperAgent"] == mock_inner_agent

    @pytest.mark.asyncio
    async def test_init_orchestration_direct_agents(self):
        """Test init_orchestration uses direct agents without inner extraction."""
        mock_orch_config.max_rounds = 10
        mock_config.get_azure_credential.return_value = Mock()
        mock_client_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        mock_storage_class.return_value = Mock()
        
        mock_workflow = Mock()
        mock_builder = Mock()
        mock_builder.participants.return_value = mock_builder
        mock_builder.with_standard_manager.return_value = mock_builder
        mock_builder.with_checkpointing.return_value = mock_builder
        mock_builder.build.return_value = mock_workflow
        mock_builder_class.return_value = mock_builder
        
        # Direct agent (no _agent or _agent is None) - use spec to prevent auto-attributes
        mock_direct_agent = Mock(spec=['name', '_agent'])
        mock_direct_agent.name = "DirectAgent"
        mock_direct_agent._agent = None
        
        agents = [mock_direct_agent]
        
        team_config = TeamConfiguration(
            name="TestTeam",
            deployment_name="gpt-4",
            agents=[]
        )
        
        await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=team_config,
            memory_store=Mock(),
            user_id="user123"
        )
        
        # Verify participants called with direct agent
        call_kwargs = mock_builder.participants.call_args[1]
        assert call_kwargs["DirectAgent"] == mock_direct_agent


class TestGetCurrentOrNewOrchestration:
    """Test cases for get_current_or_new_orchestration method."""

    @pytest.mark.asyncio
    async def test_get_existing_orchestration(self):
        """Test get_current_or_new_orchestration returns existing orchestration."""
        mock_workflow = Mock()
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        team_config = TeamConfiguration(name="TestTeam", deployment_name="gpt-4", agents=[])
        
        result = await OrchestrationManager.get_current_or_new_orchestration(
            user_id="user123",
            team_config=team_config,
            team_switched=False
        )
        
        assert result == mock_workflow
        mock_orch_config.get_current_orchestration.assert_called_with("user123")

    @pytest.mark.asyncio
    async def test_get_new_orchestration_when_none_exists(self):
        """Test get_current_or_new_orchestration creates new when none exists."""
        mock_orch_config.get_current_orchestration.side_effect = [None, Mock()]
        mock_orch_config.orchestrations = {}
        
        mock_factory = Mock()
        mock_factory.get_agents = AsyncMock(return_value=[])
        mock_factory_class.return_value = mock_factory
        
        team_config = TeamConfiguration(name="TestTeam", deployment_name="gpt-4", agents=[])
        
        mock_team_service = Mock()
        mock_team_service.memory_context = Mock()
        
        with patch.object(
            OrchestrationManager, 'init_orchestration', new_callable=AsyncMock
        ) as mock_init:
            mock_init.return_value = Mock()
            
            result = await OrchestrationManager.get_current_or_new_orchestration(
                user_id="user123",
                team_config=team_config,
                team_switched=False,
                team_service=mock_team_service
            )
            
            mock_factory.get_agents.assert_called_once()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_new_orchestration_when_team_switched(self):
        """Test get_current_or_new_orchestration creates new when team switched."""
        mock_old_workflow = Mock()
        mock_old_workflow._participants = {}
        
        mock_new_workflow = Mock()
        mock_orch_config.get_current_orchestration.side_effect = [
            mock_old_workflow,
            mock_new_workflow
        ]
        mock_orch_config.orchestrations = {}
        
        mock_factory = Mock()
        mock_factory.get_agents = AsyncMock(return_value=[])
        mock_factory_class.return_value = mock_factory
        
        team_config = TeamConfiguration(name="TestTeam", deployment_name="gpt-4", agents=[])
        
        mock_team_service = Mock()
        mock_team_service.memory_context = Mock()
        
        with patch.object(
            OrchestrationManager, 'init_orchestration', new_callable=AsyncMock
        ) as mock_init:
            mock_init.return_value = mock_new_workflow
            
            result = await OrchestrationManager.get_current_or_new_orchestration(
                user_id="user123",
                team_config=team_config,
                team_switched=True,
                team_service=mock_team_service
            )
            
            assert result == mock_new_workflow

    @pytest.mark.asyncio
    async def test_get_new_orchestration_closes_previous_agents(self):
        """Test get_current_or_new_orchestration closes previous agents when team switched."""
        mock_agent1 = Mock(spec=['agent_name', 'close'])
        mock_agent1.agent_name = "Agent1"
        mock_agent1.close = AsyncMock()
        
        mock_agent2 = Mock(spec=['name', 'close'])
        mock_agent2.name = "ProxyAgent"
        mock_agent2.close = AsyncMock()
        
        mock_old_workflow = Mock()
        mock_old_workflow._participants = {
            "Agent1": mock_agent1,
            "ProxyAgent": mock_agent2
        }
        
        mock_new_workflow = Mock()
        mock_orch_config.get_current_orchestration.side_effect = [
            mock_old_workflow,
            mock_new_workflow
        ]
        mock_orch_config.orchestrations = {}
        
        mock_factory = Mock()
        mock_factory.get_agents = AsyncMock(return_value=[])
        mock_factory_class.return_value = mock_factory
        
        team_config = TeamConfiguration(name="TestTeam", deployment_name="gpt-4", agents=[])
        
        mock_team_service = Mock()
        mock_team_service.memory_context = Mock()
        
        with patch.object(
            OrchestrationManager, 'init_orchestration', new_callable=AsyncMock
        ) as mock_init:
            mock_init.return_value = mock_new_workflow
            
            await OrchestrationManager.get_current_or_new_orchestration(
                user_id="user123",
                team_config=team_config,
                team_switched=True,
                team_service=mock_team_service
            )
            
            # Agent1 should be closed, but not ProxyAgent
            mock_agent1.close.assert_called_once()
            mock_agent2.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_new_orchestration_handles_agent_creation_error(self):
        """Test get_current_or_new_orchestration handles agent creation error."""
        mock_orch_config.get_current_orchestration.return_value = None
        
        mock_factory = Mock()
        mock_factory.get_agents = AsyncMock(side_effect=Exception("Agent creation failed"))
        mock_factory_class.return_value = mock_factory
        
        team_config = TeamConfiguration(name="TestTeam", deployment_name="gpt-4", agents=[])
        
        mock_team_service = Mock()
        mock_team_service.memory_context = Mock()
        
        with pytest.raises(Exception) as exc_info:
            await OrchestrationManager.get_current_or_new_orchestration(
                user_id="user123",
                team_config=team_config,
                team_switched=False,
                team_service=mock_team_service
            )
        
        assert "Agent creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_new_orchestration_handles_init_error(self):
        """Test get_current_or_new_orchestration handles initialization error."""
        mock_orch_config.get_current_orchestration.return_value = None
        mock_orch_config.orchestrations = {}
        
        mock_factory = Mock()
        mock_factory.get_agents = AsyncMock(return_value=[])
        mock_factory_class.return_value = mock_factory
        
        team_config = TeamConfiguration(name="TestTeam", deployment_name="gpt-4", agents=[])
        
        mock_team_service = Mock()
        mock_team_service.memory_context = Mock()
        
        with patch.object(
            OrchestrationManager, 'init_orchestration', new_callable=AsyncMock
        ) as mock_init:
            mock_init.side_effect = Exception("Init failed")
            
            with pytest.raises(Exception) as exc_info:
                await OrchestrationManager.get_current_or_new_orchestration(
                    user_id="user123",
                    team_config=team_config,
                    team_switched=False,
                    team_service=mock_team_service
                )
            
            assert "Init failed" in str(exc_info.value)


class TestRunOrchestration:
    """Test cases for run_orchestration method."""

    @pytest.mark.asyncio
    async def test_run_orchestration_success(self):
        """Test successful orchestration run."""
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        mock_workflow = Mock()
        
        # Mock workflow events
        async def mock_run_stream(task):
            yield WorkflowOutputEvent(
                data=ChatMessage(
                    role=Role.ASSISTANT,
                    contents=[TextContent(text="Final result")]
                )
            )
        
        mock_workflow.run_stream = mock_run_stream
        mock_workflow.executors = {}
        
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        manager = OrchestrationManager()
        
        mock_task = Mock()
        mock_task.description = "Test task"
        
        await manager.run_orchestration(user_id="user123", input_task=mock_task)
        
        # Verify final result sent
        mock_conn_config.send_status_update_async.assert_called()
        call_args = mock_conn_config.send_status_update_async.call_args
        assert call_args[1]["message_type"] == WebsocketMessageType.FINAL_RESULT_MESSAGE

    @pytest.mark.asyncio
    async def test_run_orchestration_no_workflow(self):
        """Test run_orchestration raises error when workflow not initialized."""
        mock_orch_config.get_current_orchestration.return_value = None
        mock_orch_config.set_approval_pending = Mock()
        
        manager = OrchestrationManager()
        
        with pytest.raises(ValueError) as exc_info:
            await manager.run_orchestration(user_id="user123", input_task="Test")
        
        assert "not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_orchestration_handles_agent_delta_event(self):
        """Test run_orchestration handles MagenticAgentDeltaEvent."""
        mock_orch_config.set_approval_pending = Mock()
        mock_callback.return_value = AsyncMock()
        
        mock_workflow = Mock()
        
        async def mock_run_stream(task):
            yield MagenticAgentDeltaEvent(
                agent_id="Agent1",
                delta="partial response"
            )
            yield WorkflowOutputEvent(data=ChatMessage(role=Role.ASSISTANT, contents=[]))
        
        mock_workflow.run_stream = mock_run_stream
        mock_workflow.executors = {}
        
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        manager = OrchestrationManager()
        
        await manager.run_orchestration(user_id="user123", input_task="Test")

    @pytest.mark.asyncio
    async def test_run_orchestration_handles_agent_message_event(self):
        """Test run_orchestration handles MagenticAgentMessageEvent."""
        mock_orch_config.set_approval_pending = Mock()
        
        mock_workflow = Mock()
        
        async def mock_run_stream(task):
            yield MagenticAgentMessageEvent(
                agent_id="Agent1",
                message=ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text="Response")])
            )
            yield WorkflowOutputEvent(data=ChatMessage(role=Role.ASSISTANT, contents=[]))
        
        mock_workflow.run_stream = mock_run_stream
        mock_workflow.executors = {}
        
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        manager = OrchestrationManager()
        
        await manager.run_orchestration(user_id="user123", input_task="Test")
        
        mock_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_orchestration_clears_executor_state(self):
        """Test run_orchestration clears executor state before run."""
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        # Mock orchestrator executor
        mock_orch_executor = Mock()
        mock_orch_conversation = []
        mock_orch_executor._conversation = mock_orch_conversation
        
        # Mock agent executor
        mock_agent_executor = Mock()
        mock_agent_history = ["old message"]
        mock_agent_executor._chat_history = mock_agent_history
        
        mock_workflow = Mock()
        mock_workflow.executors = {
            "magentic_orchestrator": mock_orch_executor,
            "Agent1": mock_agent_executor
        }
        
        async def mock_run_stream(task):
            yield WorkflowOutputEvent(data=ChatMessage(role=Role.ASSISTANT, contents=[]))
        
        mock_workflow.run_stream = mock_run_stream
        
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        manager = OrchestrationManager()
        
        await manager.run_orchestration(user_id="user123", input_task="Test")
        
        # Verify state cleared
        assert len(mock_agent_history) == 0

    @pytest.mark.asyncio
    async def test_run_orchestration_handles_workflow_error(self):
        """Test run_orchestration handles workflow execution error."""
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        mock_workflow = Mock()
        
        async def mock_run_stream(task):
            raise Exception("Workflow error")
            yield  # Make it a generator
        
        mock_workflow.run_stream = mock_run_stream
        mock_workflow.executors = {}
        
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        manager = OrchestrationManager()
        
        with pytest.raises(Exception) as exc_info:
            await manager.run_orchestration(user_id="user123", input_task="Test")
        
        assert "Workflow error" in str(exc_info.value)
        
        # Verify error status sent
        calls = mock_conn_config.send_status_update_async.call_args_list
        error_call = calls[-1]
        assert "error" in str(error_call)

    @pytest.mark.asyncio
    async def test_run_orchestration_handles_event_processing_error(self):
        """Test run_orchestration continues after event processing error."""
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        mock_workflow = Mock()
        
        async def mock_run_stream(task):
            # Event that will cause error in processing
            yield MagenticAgentMessageEvent(
                agent_id="Agent1",
                message=None  # This might cause error
            )
            yield WorkflowOutputEvent(data=ChatMessage(role=Role.ASSISTANT, contents=[]))
        
        mock_workflow.run_stream = mock_run_stream
        mock_workflow.executors = {}
        
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        manager = OrchestrationManager()
        
        # Set callback to raise exception
        mock_callback.side_effect = Exception("Callback error")
        
        # Should not raise, should continue
        await manager.run_orchestration(user_id="user123", input_task="Test")

    @pytest.mark.asyncio
    async def test_run_orchestration_with_string_task(self):
        """Test run_orchestration with string task instead of object."""
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        mock_workflow = Mock()
        
        async def mock_run_stream(task):
            yield WorkflowOutputEvent(data=ChatMessage(role=Role.ASSISTANT, contents=[]))
        
        mock_workflow.run_stream = mock_run_stream
        mock_workflow.executors = {}
        
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        manager = OrchestrationManager()
        
        # Task is just a string
        await manager.run_orchestration(user_id="user123", input_task="String task")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_init_orchestration_agent_without_name(self):
        """Test init_orchestration handles agent without name attribute."""
        mock_orch_config.max_rounds = 10
        mock_config.get_azure_credential.return_value = Mock()
        mock_client_class.return_value = Mock()
        mock_manager_class.return_value = Mock()
        mock_storage_class.return_value = Mock()
        
        mock_workflow = Mock()
        mock_builder = Mock()
        mock_builder.participants.return_value = mock_builder
        mock_builder.with_standard_manager.return_value = mock_builder
        mock_builder.with_checkpointing.return_value = mock_builder
        mock_builder.build.return_value = mock_workflow
        mock_builder_class.return_value = mock_builder
        
        # Agent without agent_name or name
        mock_agent = Mock(spec=[])  # Empty spec, no attributes
        
        agents = [mock_agent]
        
        team_config = TeamConfiguration(
            name="TestTeam",
            deployment_name="gpt-4",
            agents=[]
        )
        
        await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=team_config,
            memory_store=Mock(),
            user_id="user123"
        )
        
        # Should assign default name
        call_kwargs = mock_builder.participants.call_args[1]
        assert "agent_1" in call_kwargs

    @pytest.mark.asyncio
    async def test_run_orchestration_executor_state_clearing_error(self):
        """Test run_orchestration handles error during state clearing."""
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        # Mock executor that raises error on clear
        mock_executor = Mock()
        
        class ErrorList:
            def clear(self):
                raise Exception("Clear error")
        
        mock_executor._chat_history = ErrorList()
        
        mock_workflow = Mock()
        mock_workflow.executors = {"Agent1": mock_executor}
        
        async def mock_run_stream(task):
            yield WorkflowOutputEvent(data=ChatMessage(role=Role.ASSISTANT, contents=[]))
        
        mock_workflow.run_stream = mock_run_stream
        
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        manager = OrchestrationManager()
        
        # Should not raise, should continue
        await manager.run_orchestration(user_id="user123", input_task="Test")

    @pytest.mark.asyncio
    async def test_run_orchestration_send_error_status_fails(self):
        """Test run_orchestration handles failure to send error status."""
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock(
            side_effect=Exception("Send error")
        )
        
        mock_workflow = Mock()
        
        async def mock_run_stream(task):
            raise Exception("Workflow error")
            yield
        
        mock_workflow.run_stream = mock_run_stream
        mock_workflow.executors = {}
        
        mock_orch_config.get_current_orchestration.return_value = mock_workflow
        
        manager = OrchestrationManager()
        
        # Should still raise original workflow error
        with pytest.raises(Exception) as exc_info:
            await manager.run_orchestration(user_id="user123", input_task="Test")
        
        assert "Workflow error" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
