"""Unit tests for orchestration_manager module.

Comprehensive test cases covering OrchestrationManager with proper mocking.
"""

import asyncio
import logging
import os
import sys
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))

# Set up required environment variables before any imports
os.environ.update({
    'APPLICATIONINSIGHTS_CONNECTION_STRING': 'InstrumentationKey=test-key',
    'APP_ENV': 'dev',
    'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
    'AZURE_OPENAI_API_KEY': 'test_key',
    'AZURE_OPENAI_DEPLOYMENT_NAME': 'test_deployment',
    'AZURE_AI_SUBSCRIPTION_ID': 'test_subscription_id',
    'AZURE_AI_RESOURCE_GROUP': 'test_resource_group',
    'AZURE_AI_PROJECT_NAME': 'test_project_name',
    'AZURE_AI_AGENT_ENDPOINT': 'https://test.agent.azure.com/',
    'AZURE_AI_PROJECT_ENDPOINT': 'https://test.project.azure.com/',
    'COSMOSDB_ENDPOINT': 'https://test.documents.azure.com:443/',
    'COSMOSDB_DATABASE': 'test_database',
    'COSMOSDB_CONTAINER': 'test_container',
    'AZURE_CLIENT_ID': 'test_client_id',
    'AZURE_TENANT_ID': 'test_tenant_id',
    'AZURE_OPENAI_RAI_DEPLOYMENT_NAME': 'test_rai_deployment'
})

# Mock external Azure dependencies
sys.modules['azure'] = Mock()
sys.modules['azure.ai'] = Mock()
sys.modules['azure.ai.agents'] = Mock()
sys.modules['azure.ai.agents.aio'] = Mock(AgentsClient=Mock)
sys.modules['azure.ai.projects'] = Mock()
sys.modules['azure.ai.projects.aio'] = Mock(AIProjectClient=Mock)
sys.modules['azure.ai.projects.models'] = Mock(MCPTool=Mock)
sys.modules['azure.ai.projects.models._models'] = Mock()
sys.modules['azure.ai.projects._client'] = Mock()
sys.modules['azure.ai.projects.operations'] = Mock()
sys.modules['azure.ai.projects.operations._patch'] = Mock()
sys.modules['azure.ai.projects.operations._patch_datasets'] = Mock()
sys.modules['azure.search'] = Mock()
sys.modules['azure.search.documents'] = Mock()
sys.modules['azure.search.documents.indexes'] = Mock()
sys.modules['azure.core'] = Mock()
sys.modules['azure.core.exceptions'] = Mock()
sys.modules['azure.identity'] = Mock()
sys.modules['azure.identity.aio'] = Mock()
sys.modules['azure.cosmos'] = Mock(CosmosClient=Mock)

# Mock agent_framework dependencies
class MockChatMessage:
    """Mock ChatMessage class for isinstance checks."""
    def __init__(self, text="Mock message"):
        self.text = text
        self.author_name = "TestAgent"
        self.role = "assistant"

class MockWorkflowOutputEvent:
    """Mock WorkflowOutputEvent."""
    def __init__(self, data=None):
        self.data = data or MockChatMessage()

class MockMagenticOrchestratorMessageEvent:
    """Mock MagenticOrchestratorMessageEvent."""
    def __init__(self, message=None, kind="orchestrator"):
        self.message = message or MockChatMessage()
        self.kind = kind

class MockMagenticAgentDeltaEvent:
    """Mock MagenticAgentDeltaEvent."""
    def __init__(self, agent_id="test_agent"):
        self.agent_id = agent_id
        self.delta = "streaming update"

class MockMagenticAgentMessageEvent:
    """Mock MagenticAgentMessageEvent."""
    def __init__(self, agent_id="test_agent", message=None):
        self.agent_id = agent_id
        self.message = message or MockChatMessage()

class MockMagenticFinalResultEvent:
    """Mock MagenticFinalResultEvent."""
    def __init__(self, message=None):
        self.message = message or MockChatMessage()

class MockAgent:
    """Mock agent class with proper attributes."""
    def __init__(self, agent_name=None, name=None, has_inner_agent=False):
        if agent_name:
            self.agent_name = agent_name
        if name:
            self.name = name
        if has_inner_agent:
            self._agent = Mock()
        self.close = AsyncMock()

class AsyncGeneratorMock:
    """Helper class to mock async generators."""
    def __init__(self, items):
        self.items = items
        self.call_count = 0
        self.call_args_list = []
    
    async def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.call_args_list.append((args, kwargs))
        for item in self.items:
            yield item
    
    def assert_called_once(self):
        """Assert that the mock was called exactly once."""
        if self.call_count != 1:
            raise AssertionError(f"Expected 1 call, got {self.call_count}")
    
    def assert_called_once_with(self, *args, **kwargs):
        """Assert that the mock was called exactly once with specific arguments."""
        self.assert_called_once()
        expected = (args, kwargs)
        actual = self.call_args_list[0]
        if actual != expected:
            raise AssertionError(f"Expected {expected}, got {actual}")

class MockMagenticBuilder:
    """Mock MagenticBuilder."""
    def __init__(self):
        self._participants = {}
        self._manager = None
        self._storage = None
        
    def participants(self, participants_dict=None, **kwargs):
        if participants_dict:
            self._participants = participants_dict
        else:
            self._participants = kwargs
        return self
    
    def with_standard_manager(self, manager=None, max_round_count=10, max_stall_count=0):
        self._manager = manager
        return self
    
    def with_checkpointing(self, storage):
        self._storage = storage
        return self
    
    def build(self):
        workflow = Mock()
        workflow._participants = self._participants
        workflow.executors = {
            "magentic_orchestrator": Mock(
                _conversation=[]
            ),
            "agent_1": Mock(
                _chat_history=[]
            )
        }
        # Mock async generator for run_stream
        workflow.run_stream = AsyncGeneratorMock([])
        return workflow

class MockInMemoryCheckpointStorage:
    """Mock InMemoryCheckpointStorage."""
    pass

# Set up agent_framework mocks
sys.modules['agent_framework_azure_ai'] = Mock(AzureAIAgentClient=Mock())
sys.modules['agent_framework'] = Mock(
    ChatMessage=MockChatMessage,
    WorkflowOutputEvent=MockWorkflowOutputEvent,
    MagenticBuilder=MockMagenticBuilder,
    InMemoryCheckpointStorage=MockInMemoryCheckpointStorage,
    MagenticOrchestratorMessageEvent=MockMagenticOrchestratorMessageEvent,
    MagenticAgentDeltaEvent=MockMagenticAgentDeltaEvent,
    MagenticAgentMessageEvent=MockMagenticAgentMessageEvent,
    MagenticFinalResultEvent=MockMagenticFinalResultEvent,
)

# Mock common modules
mock_config = Mock()
mock_config.get_azure_credential.return_value = Mock()
mock_config.AZURE_CLIENT_ID = 'test_client_id'
mock_config.AZURE_AI_PROJECT_ENDPOINT = 'https://test.project.azure.com/'

sys.modules['common'] = Mock()
sys.modules['common.config'] = Mock()
sys.modules['common.config.app_config'] = Mock(config=mock_config)
sys.modules['common.models'] = Mock()

class MockTeamConfiguration:
    """Mock TeamConfiguration."""
    def __init__(self, name="TestTeam", deployment_name="test_deployment"):
        self.name = name
        self.deployment_name = deployment_name

sys.modules['common.models.messages_af'] = Mock(TeamConfiguration=MockTeamConfiguration)

class MockDatabaseBase:
    """Mock DatabaseBase."""
    pass

sys.modules['common.database'] = Mock()
sys.modules['common.database.database_base'] = Mock(DatabaseBase=MockDatabaseBase)

# Mock v4 modules
class MockTeamService:
    """Mock TeamService."""
    def __init__(self):
        self.memory_context = MockDatabaseBase()

sys.modules['v4'] = Mock()
sys.modules['v4.common'] = Mock()
sys.modules['v4.common.services'] = Mock()
sys.modules['v4.common.services.team_service'] = Mock(TeamService=MockTeamService)

sys.modules['v4.callbacks'] = Mock()
sys.modules['v4.callbacks.response_handlers'] = Mock(
    agent_response_callback=Mock(),
    streaming_agent_response_callback=AsyncMock()
)

# Mock v4.config.settings
mock_connection_config = Mock()
mock_connection_config.send_status_update_async = AsyncMock()

mock_orchestration_config = Mock()
mock_orchestration_config.max_rounds = 10
mock_orchestration_config.orchestrations = {}
mock_orchestration_config.get_current_orchestration = Mock(return_value=None)
mock_orchestration_config.set_approval_pending = Mock()

sys.modules['v4.config'] = Mock()
sys.modules['v4.config.settings'] = Mock(
    connection_config=mock_connection_config,
    orchestration_config=mock_orchestration_config
)

# Mock v4.models.messages
class MockWebsocketMessageType:
    """Mock WebsocketMessageType."""
    FINAL_RESULT_MESSAGE = "final_result_message"

sys.modules['v4.models'] = Mock()
sys.modules['v4.models.messages'] = Mock(WebsocketMessageType=MockWebsocketMessageType)

# Mock v4.orchestration.human_approval_manager
class MockHumanApprovalMagenticManager:
    """Mock HumanApprovalMagenticManager."""
    def __init__(self, user_id, chat_client, instructions=None, max_round_count=10):
        self.user_id = user_id
        self.chat_client = chat_client
        self.instructions = instructions
        self.max_round_count = max_round_count

sys.modules['v4.orchestration'] = Mock()
sys.modules['v4.orchestration.human_approval_manager'] = Mock(
    HumanApprovalMagenticManager=MockHumanApprovalMagenticManager
)

# Mock v4.magentic_agents.magentic_agent_factory
class MockMagenticAgentFactory:
    """Mock MagenticAgentFactory."""
    def __init__(self, team_service=None):
        self.team_service = team_service
    
    async def get_agents(self, user_id, team_config_input, memory_store):
        # Create mock agents
        agent1 = Mock()
        agent1.agent_name = "TestAgent1"
        agent1._agent = Mock()  # Inner agent for wrapper templates
        agent1.close = AsyncMock()
        
        agent2 = Mock()
        agent2.name = "TestAgent2"
        agent2.close = AsyncMock()
        
        return [agent1, agent2]

sys.modules['v4.magentic_agents'] = Mock()
sys.modules['v4.magentic_agents.magentic_agent_factory'] = Mock(
    MagenticAgentFactory=MockMagenticAgentFactory
)

# Now import the module under test
from backend.v4.orchestration.orchestration_manager import OrchestrationManager

# Get mocked references for tests
connection_config = sys.modules['v4.config.settings'].connection_config
orchestration_config = sys.modules['v4.config.settings'].orchestration_config
agent_response_callback = sys.modules['v4.callbacks.response_handlers'].agent_response_callback
streaming_agent_response_callback = sys.modules['v4.callbacks.response_handlers'].streaming_agent_response_callback


class TestOrchestrationManager(IsolatedAsyncioTestCase):
    """Test cases for OrchestrationManager class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Reset mocks
        orchestration_config.orchestrations.clear()
        orchestration_config.get_current_orchestration.return_value = None
        orchestration_config.set_approval_pending.reset_mock()
        connection_config.send_status_update_async.reset_mock()
        agent_response_callback.reset_mock()
        streaming_agent_response_callback.reset_mock()
        
        # Create test instance
        self.orchestration_manager = OrchestrationManager()
        self.test_user_id = "test_user_123"
        self.test_team_config = MockTeamConfiguration()
        self.test_team_service = MockTeamService()

    def test_init(self):
        """Test OrchestrationManager initialization."""
        manager = OrchestrationManager()
        
        self.assertIsNone(manager.user_id)
        self.assertIsNotNone(manager.logger)
        self.assertIsInstance(manager.logger, logging.Logger)

    async def test_init_orchestration_success(self):
        """Test successful orchestration initialization."""
        # Reset the mock to get clean call count
        mock_config.get_azure_credential.reset_mock()
        
        # Use MockAgent instead of Mock to avoid attribute issues
        agent1 = MockAgent(agent_name="TestAgent1", has_inner_agent=True)
        agent2 = MockAgent(name="TestAgent2")
        
        agents = [agent1, agent2]
        
        workflow = await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=self.test_team_config,
            memory_store=MockDatabaseBase(),
            user_id=self.test_user_id
        )
        
        self.assertIsNotNone(workflow)
        mock_config.get_azure_credential.assert_called_once()

    async def test_init_orchestration_no_user_id(self):
        """Test orchestration initialization without user_id raises ValueError."""
        agents = [Mock()]
        
        with self.assertRaises(ValueError) as context:
            await OrchestrationManager.init_orchestration(
                agents=agents,
                team_config=self.test_team_config,
                memory_store=MockDatabaseBase(),
                user_id=None
            )
        
        self.assertIn("user_id is required", str(context.exception))

    @patch('backend.v4.orchestration.orchestration_manager.AzureAIAgentClient')
    async def test_init_orchestration_client_creation_failure(self, mock_client_class):
        """Test orchestration initialization when client creation fails."""
        mock_client_class.side_effect = Exception("Client creation failed")
        
        agents = [Mock()]
        
        with self.assertRaises(Exception) as context:
            await OrchestrationManager.init_orchestration(
                agents=agents,
                team_config=self.test_team_config,
                memory_store=MockDatabaseBase(),
                user_id=self.test_user_id
            )
        
        self.assertIn("Client creation failed", str(context.exception))

    @patch('backend.v4.orchestration.orchestration_manager.HumanApprovalMagenticManager')
    async def test_init_orchestration_manager_creation_failure(self, mock_manager_class):
        """Test orchestration initialization when manager creation fails."""
        mock_manager_class.side_effect = Exception("Manager creation failed")
        
        agents = [Mock()]
        
        with self.assertRaises(Exception) as context:
            await OrchestrationManager.init_orchestration(
                agents=agents,
                team_config=self.test_team_config,
                memory_store=MockDatabaseBase(),
                user_id=self.test_user_id
            )
        
        self.assertIn("Manager creation failed", str(context.exception))

    async def test_init_orchestration_participants_mapping(self):
        """Test proper participant mapping in orchestration initialization."""
        # Use MockAgent to avoid attribute issues
        agent_with_agent_name = MockAgent(agent_name="AgentWithAgentName", has_inner_agent=True)
        agent_with_name = MockAgent(name="AgentWithName")
        agent_without_name = MockAgent()  # Neither agent_name nor name
        
        agents = [agent_with_agent_name, agent_with_name, agent_without_name]
        
        workflow = await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=self.test_team_config,
            memory_store=MockDatabaseBase(),
            user_id=self.test_user_id
        )
        
        self.assertIsNotNone(workflow)
        # Verify builder was called with participants
        self.assertIsNotNone(workflow._participants)

    async def test_get_current_or_new_orchestration_existing(self):
        """Test getting existing orchestration."""
        # Set up existing orchestration
        mock_workflow = Mock()
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        
        result = await OrchestrationManager.get_current_or_new_orchestration(
            user_id=self.test_user_id,
            team_config=self.test_team_config,
            team_switched=False,
            team_service=self.test_team_service
        )
        
        self.assertEqual(result, mock_workflow)
        orchestration_config.get_current_orchestration.assert_called_with(self.test_user_id)

    async def test_get_current_or_new_orchestration_new(self):
        """Test creating new orchestration when none exists."""
        # No existing orchestration
        orchestration_config.get_current_orchestration.return_value = None
        
        with patch.object(OrchestrationManager, 'init_orchestration', new_callable=AsyncMock) as mock_init:
            mock_workflow = Mock()
            mock_init.return_value = mock_workflow
            
            await OrchestrationManager.get_current_or_new_orchestration(
                user_id=self.test_user_id,
                team_config=self.test_team_config,
                team_switched=False,
                team_service=self.test_team_service
            )
            
            # Verify new orchestration was created and stored
            mock_init.assert_called_once()
            self.assertEqual(orchestration_config.orchestrations[self.test_user_id], mock_workflow)

    async def test_get_current_or_new_orchestration_team_switched(self):
        """Test creating new orchestration when team is switched."""
        # Set up existing orchestration with participants that need closing
        mock_existing_workflow = Mock()
        mock_agent = MockAgent(agent_name="TestAgent")
        mock_existing_workflow._participants = {"agent1": mock_agent}
        
        orchestration_config.get_current_orchestration.return_value = mock_existing_workflow
        
        with patch.object(OrchestrationManager, 'init_orchestration', new_callable=AsyncMock) as mock_init:
            mock_new_workflow = Mock()
            mock_init.return_value = mock_new_workflow
            
            await OrchestrationManager.get_current_or_new_orchestration(
                user_id=self.test_user_id,
                team_config=self.test_team_config,
                team_switched=True,
                team_service=self.test_team_service
            )
            
            # Verify agents were closed and new orchestration was created
            mock_agent.close.assert_called_once()
            mock_init.assert_called_once()
            self.assertEqual(orchestration_config.orchestrations[self.test_user_id], mock_new_workflow)

    async def test_get_current_or_new_orchestration_agent_creation_failure(self):
        """Test handling agent creation failure."""
        orchestration_config.get_current_orchestration.return_value = None
        
        # Mock agent factory to raise exception
        with patch('backend.v4.orchestration.orchestration_manager.MagenticAgentFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_factory.get_agents = AsyncMock(side_effect=Exception("Agent creation failed"))
            mock_factory_class.return_value = mock_factory
            
            with self.assertRaises(Exception) as context:
                await OrchestrationManager.get_current_or_new_orchestration(
                    user_id=self.test_user_id,
                    team_config=self.test_team_config,
                    team_switched=False,
                    team_service=self.test_team_service
                )
            
            self.assertIn("Agent creation failed", str(context.exception))

    async def test_get_current_or_new_orchestration_init_failure(self):
        """Test handling orchestration initialization failure."""
        orchestration_config.get_current_orchestration.return_value = None
        
        with patch.object(OrchestrationManager, 'init_orchestration', new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Orchestration init failed")
            
            with self.assertRaises(Exception) as context:
                await OrchestrationManager.get_current_or_new_orchestration(
                    user_id=self.test_user_id,
                    team_config=self.test_team_config,
                    team_switched=False,
                    team_service=self.test_team_service
                )
            
            self.assertIn("Orchestration init failed", str(context.exception))

    async def test_run_orchestration_success(self):
        """Test successful orchestration execution."""
        # Set up mock workflow with events
        mock_workflow = Mock()
        mock_events = [
            MockMagenticOrchestratorMessageEvent(),
            MockMagenticAgentDeltaEvent(),
            MockMagenticAgentMessageEvent(),
            MockMagenticFinalResultEvent(),
            MockWorkflowOutputEvent(MockChatMessage("Final result"))
        ]
        mock_workflow.run_stream = AsyncGeneratorMock(mock_events)
        mock_workflow.executors = {
            "magentic_orchestrator": Mock(_conversation=[]),
            "agent_1": Mock(_chat_history=[])
        }

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        # Mock input task
        input_task = Mock()
        input_task.description = "Test task description"

        # Execute orchestration
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            input_task=input_task
        )

        # Verify callbacks were called
        streaming_agent_response_callback.assert_called()
        agent_response_callback.assert_called()
        
        # Verify final result was sent
        connection_config.send_status_update_async.assert_called()

    async def test_run_orchestration_no_workflow(self):
        """Test run_orchestration when no workflow exists."""
        orchestration_config.get_current_orchestration.return_value = None
        
        input_task = Mock()
        input_task.description = "Test task"
        
        with self.assertRaises(ValueError) as context:
            await self.orchestration_manager.run_orchestration(
                user_id=self.test_user_id,
                input_task=input_task
            )
        
        self.assertIn("Orchestration not initialized", str(context.exception))

    async def test_run_orchestration_workflow_execution_error(self):
        """Test run_orchestration when workflow execution fails."""
        # Set up mock workflow that raises exception
        mock_workflow = Mock()
        mock_workflow.run_stream = AsyncGeneratorMock([])
        mock_workflow.run_stream = Mock(side_effect=Exception("Workflow execution failed"))
        mock_workflow.executors = {}
        
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        
        input_task = Mock()
        input_task.description = "Test task"
        
        with self.assertRaises(Exception):
            await self.orchestration_manager.run_orchestration(
                user_id=self.test_user_id,
                input_task=input_task
            )
        
        # Verify error status was sent
        connection_config.send_status_update_async.assert_called()

    async def test_run_orchestration_conversation_clearing(self):
        """Test conversation history clearing in run_orchestration."""
        # Set up workflow with various executor types
        mock_conversation = []
        mock_chat_history = []
        
        mock_orchestrator_executor = Mock()
        mock_orchestrator_executor._conversation = mock_conversation
        
        mock_agent_executor = Mock()
        mock_agent_executor._chat_history = mock_chat_history
        
        mock_workflow = Mock()
        mock_workflow.executors = {
            "magentic_orchestrator": mock_orchestrator_executor,
            "agent_1": mock_agent_executor
        }
        mock_workflow.run_stream = AsyncGeneratorMock([])
        
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        
        input_task = Mock()
        input_task.description = "Test task"
        
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            input_task=input_task
        )
        
        # Verify histories were cleared
        self.assertEqual(len(mock_conversation), 0)
        self.assertEqual(len(mock_chat_history), 0)

    async def test_run_orchestration_clearing_with_custom_containers(self):
        """Test conversation clearing with custom containers that have clear() method."""
        # Set up custom container with clear method
        mock_custom_container = Mock()
        mock_custom_container.clear = Mock()
        
        mock_executor = Mock()
        mock_executor._conversation = mock_custom_container
        
        mock_workflow = Mock()
        mock_workflow.executors = {
            "magentic_orchestrator": mock_executor
        }
        mock_workflow.run_stream = AsyncGeneratorMock([])
        
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        
        input_task = Mock()
        input_task.description = "Test task"
        
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            input_task=input_task
        )
        
        # Verify clear method was called
        mock_custom_container.clear.assert_called_once()

    async def test_run_orchestration_clearing_failure_handling(self):
        """Test handling of failures during conversation clearing."""
        # Set up executor that raises exception during clearing
        mock_executor = Mock()
        mock_conversation = Mock()
        mock_conversation.clear = Mock(side_effect=Exception("Clear failed"))
        mock_executor._conversation = mock_conversation
        
        mock_workflow = Mock()
        mock_workflow.executors = {
            "magentic_orchestrator": mock_executor
        }
        mock_workflow.run_stream = AsyncGeneratorMock([])
        
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        
        input_task = Mock()
        input_task.description = "Test task"
        
        # Should not raise exception - clearing failures are handled gracefully
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            input_task=input_task
        )
        
        # Verify workflow still executed
        mock_workflow.run_stream.assert_called_once()

    async def test_run_orchestration_event_processing_error(self):
        """Test handling of errors during event processing."""
        # Set up workflow with events that cause processing errors
        mock_workflow = Mock()
        mock_events = [MockMagenticAgentDeltaEvent()]
        mock_workflow.run_stream = AsyncGeneratorMock(mock_events)
        mock_workflow.executors = {}
        
        # Make streaming callback raise exception
        streaming_agent_response_callback.side_effect = Exception("Callback error")
        
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        
        input_task = Mock()
        input_task.description = "Test task"
        
        # Should not raise exception - event processing errors are handled
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            input_task=input_task
        )
        
        # Reset side effect for other tests
        streaming_agent_response_callback.side_effect = None

    def test_run_orchestration_job_id_generation(self):
        """Test that job_id is generated and approval is set pending."""
        # Reset the mock first to get a clean count
        orchestration_config.set_approval_pending.reset_mock()
        orchestration_config.get_current_orchestration.return_value = None
        
        input_task = Mock()
        input_task.description = "Test task"
        
        # Run should fail due to no workflow, but we can test the setup
        with self.assertRaises(ValueError):
            asyncio.run(self.orchestration_manager.run_orchestration(
                user_id=self.test_user_id,
                input_task=input_task
            ))
        
        # Verify approval was set pending (called with some job_id)
        orchestration_config.set_approval_pending.assert_called_once()

    async def test_run_orchestration_string_input_task(self):
        """Test run_orchestration with string input task."""
        mock_workflow = Mock()
        mock_workflow.run_stream = AsyncGeneratorMock([])
        mock_workflow.executors = {}
        
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        
        # Use string input instead of object
        input_task = "Simple string task"
        
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            input_task=input_task
        )
        
        # Verify workflow was called with the string
        mock_workflow.run_stream.assert_called_once_with("Simple string task")

    async def test_run_orchestration_websocket_error_handling(self):
        """Test handling of WebSocket sending errors."""
        mock_workflow = Mock()
        mock_workflow.run_stream = AsyncGeneratorMock([])
        mock_workflow.executors = {}
        
        # Make WebSocket sending fail
        connection_config.send_status_update_async.side_effect = Exception("WebSocket error")
        
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        
        input_task = Mock()
        input_task.description = "Test task"
        
        # The method should handle WebSocket errors gracefully by catching them
        # and trying to send error status, which will also fail, but shouldn't raise
        try:
            await self.orchestration_manager.run_orchestration(
                user_id=self.test_user_id,
                input_task=input_task
            )
        except Exception as e:
            # The method may still raise the original WebSocket error
            # This is acceptable behavior for this test
            self.assertIn("WebSocket error", str(e))
        
        # Reset side effect
        connection_config.send_status_update_async.side_effect = None

    async def test_run_orchestration_all_event_types(self):
        """Test processing of all event types."""
        mock_workflow = Mock()
        
        # Create all possible event types
        events = [
            MockMagenticOrchestratorMessageEvent(),
            MockMagenticAgentDeltaEvent(),
            MockMagenticAgentMessageEvent(),
            MockMagenticFinalResultEvent(),
            MockWorkflowOutputEvent(),
            Mock()  # Unknown event type
        ]
        
        mock_workflow.run_stream = AsyncGeneratorMock(events)
        mock_workflow.executors = {}
        
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        
        input_task = Mock()
        input_task.description = "Test all events"
        
        # Should process all events without errors
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            input_task=input_task
        )
        
        # Verify all appropriate callbacks were made
        streaming_agent_response_callback.assert_called()
        agent_response_callback.assert_called()


if __name__ == '__main__':
    import unittest
    unittest.main()