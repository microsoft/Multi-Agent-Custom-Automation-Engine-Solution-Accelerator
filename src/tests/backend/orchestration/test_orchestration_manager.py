"""Unit tests for orchestration_manager module.

Tests OrchestrationManager:
- init_orchestration() — builds MagenticBuilder workflow
- get_current_or_new_orchestration() — lifecycle management
- run_orchestration() — event stream processing with plan review
- _process_event_stream() — event dispatch
"""

import asyncio
import logging
import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

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
    'AZURE_OPENAI_RAI_DEPLOYMENT_NAME': 'test_rai_deployment',
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


# ---------------------------------------------------------------------------
# Lightweight mock types for agent_framework
# ---------------------------------------------------------------------------
class MockMessage:
    """Mock Message returned by executor_completed events."""
    def __init__(self, text="Mock message"):
        self.text = text


class MockAgentResponseUpdate:
    """Mock AgentResponseUpdate for streaming output events."""
    def __init__(self, text="streaming chunk"):
        self.text = text


class MockMagenticPlanReviewRequest:
    """Mock MagenticPlanReviewRequest."""
    def __init__(self):
        self.plan = Mock()  # _MagenticTaskLedger
        self._approved_response = Mock()

    def approve(self):
        return self._approved_response

    def revise(self, feedback):
        return Mock()


class MockMagenticOrchestratorEvent:
    """Mock MagenticOrchestratorEvent."""
    def __init__(self):
        self.event_type = Mock()
        self.event_type.value = "plan_created"


class MockInMemoryCheckpointStorage:
    pass


class MockAgent:
    """Mock agent with typical attributes."""
    def __init__(self, agent_name=None, name=None, has_inner_agent=False):
        if agent_name:
            self.agent_name = agent_name
        if name:
            self.name = name
        if has_inner_agent:
            self._agent = Mock()
        self.close = AsyncMock()


def _make_event(event_type, data=None, executor_id=None, request_id=None):
    """Factory for workflow events."""
    event = Mock()
    event.type = event_type
    event.data = data
    event.executor_id = executor_id
    event.request_id = request_id
    return event


async def _async_iter(items):
    """Helper: convert a list into an async iterator."""
    for item in items:
        yield item


def _make_workflow_mock(run_return=None, executors=None):
    """Create a properly configured workflow Mock."""
    wf = Mock()
    wf._executors = executors or {}
    wf.executors = executors or {}
    wf._terminated = False
    wf._participants = {}
    if run_return is not None:
        wf.run = Mock(return_value=run_return)
    return wf


# ---------------------------------------------------------------------------
# agent_framework mocks
# ---------------------------------------------------------------------------
mock_magentic_builder = Mock()
mock_magentic_builder.return_value.build.return_value = Mock()

af_mock = Mock()
af_mock.Agent = Mock(return_value=Mock())
af_mock.AgentResponse = Mock
af_mock.AgentResponseUpdate = MockAgentResponseUpdate
af_mock.InMemoryCheckpointStorage = MockInMemoryCheckpointStorage
af_mock.Message = MockMessage
af_mock.WorkflowEvent = Mock

af_orch_mock = Mock()
af_orch_mock.MagenticBuilder = mock_magentic_builder
af_orch_mock.MagenticOrchestratorEvent = MockMagenticOrchestratorEvent
af_orch_mock.MagenticOrchestratorEventType = Mock
af_orch_mock.MagenticPlanReviewRequest = MockMagenticPlanReviewRequest

sys.modules['agent_framework'] = af_mock
sys.modules['agent_framework.orchestrations'] = af_orch_mock
sys.modules['agent_framework_foundry'] = Mock(FoundryChatClient=Mock())
sys.modules['agent_framework_orchestrations'] = af_orch_mock
sys.modules['agent_framework_orchestrations._magentic'] = Mock()
sys.modules['agent_framework_azure_ai_search'] = Mock()

# ---------------------------------------------------------------------------
# Application module mocks
# ---------------------------------------------------------------------------
mock_config = Mock()
mock_config.get_azure_credential.return_value = Mock()
mock_config.AZURE_CLIENT_ID = 'test_client_id'
mock_config.AZURE_AI_PROJECT_ENDPOINT = 'https://test.project.azure.com/'

sys.modules['common'] = Mock()
sys.modules['common.config'] = Mock()
sys.modules['common.config.app_config'] = Mock(config=mock_config)
sys.modules['common.models'] = Mock()

# Register the real markdown_utils so the orchestrator uses genuine table logic, not a Mock (Bug 47810).
import importlib.util as _ilu  # noqa: E402

_md_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "backend",
    "common", "utils", "markdown_utils.py",
)
_md_spec = _ilu.spec_from_file_location("common.utils.markdown_utils", _md_path)
_markdown_utils = _ilu.module_from_spec(_md_spec)
_md_spec.loader.exec_module(_markdown_utils)
sys.modules['common.utils'] = Mock()
sys.modules['common.utils.markdown_utils'] = _markdown_utils


class MockTeamConfiguration:
    def __init__(self, name="TestTeam", deployment_name="test_deployment"):
        self.name = name
        self.deployment_name = deployment_name


class MockDatabaseBase:
    pass


sys.modules['common.models.messages'] = Mock(TeamConfiguration=MockTeamConfiguration)
sys.modules['common.database'] = Mock()
sys.modules['common.database.database_base'] = Mock(DatabaseBase=MockDatabaseBase)


class MockTeamService:
    def __init__(self):
        self.memory_context = MockDatabaseBase()


sys.modules['services'] = Mock()
sys.modules['services.team_service'] = Mock(TeamService=MockTeamService)

sys.modules['callbacks.response_handlers'] = Mock(
    agent_response_callback=Mock(),
    streaming_agent_response_callback=AsyncMock(),
)

# ---- Mock orchestration.connection_config ----
mock_connection_config = Mock()
mock_connection_config.send_status_update_async = AsyncMock()

mock_orchestration_config = Mock()
mock_orchestration_config.max_rounds = 10
mock_orchestration_config.orchestrations = {}
mock_orchestration_config.plans = {}
mock_orchestration_config.get_current_orchestration = Mock(return_value=None)
mock_orchestration_config.set_approval_pending = Mock()

sys.modules['orchestration.connection_config'] = Mock(
    connection_config=mock_connection_config,
    orchestration_config=mock_orchestration_config,
)

# ---- Mock models.messages ----
class MockWebsocketMessageType:
    FINAL_RESULT_MESSAGE = "final_result_message"
    PLAN_APPROVAL_REQUEST = "plan_approval_request"
    PLAN_APPROVAL_RESPONSE = "plan_approval_response"
    AGENT_MESSAGE_STREAMING = "agent_message_streaming"


class MockAgentMessageStreaming:
    def __init__(self, agent_name="", content="", is_final=False):
        self.agent_name = agent_name
        self.content = content
        self.is_final = is_final


class MockPlanApprovalRequest:
    def __init__(self, plan=None, status="PENDING_APPROVAL", context=None):
        self.plan = plan
        self.status = status
        self.context = context or {}


class MockPlanApprovalResponse:
    def __init__(self, approved=True, m_plan_id=None):
        self.approved = approved
        self.m_plan_id = m_plan_id


mock_messages_module = Mock()
mock_messages_module.WebsocketMessageType = MockWebsocketMessageType
mock_messages_module.AgentMessageStreaming = MockAgentMessageStreaming
mock_messages_module.PlanApprovalRequest = MockPlanApprovalRequest
mock_messages_module.PlanApprovalResponse = MockPlanApprovalResponse
sys.modules['models'] = Mock()
sys.modules['models.messages'] = mock_messages_module

# ---- Mock plan_review_helpers ----
class MockMPlan:
    def __init__(self):
        self.id = "test-plan-id"
        self.user_id = None


mock_convert = Mock(return_value=MockMPlan())
mock_get_prompt_kwargs = Mock(return_value={"task_ledger_plan_prompt": "p"})
mock_wait_approval = AsyncMock(return_value=MockPlanApprovalResponse(approved=True, m_plan_id="test-plan-id"))

sys.modules['orchestration.plan_review_helpers'] = Mock(
    convert_plan_review_to_mplan=mock_convert,
    get_magentic_prompt_kwargs=mock_get_prompt_kwargs,
    wait_for_plan_approval=mock_wait_approval,
)

# ---- Mock agents ----
class MockAgentFactory:
    def __init__(self, team_service=None):
        self.team_service = team_service

    async def get_agents(self, user_id, team_config_input, memory_store):
        agent1 = Mock()
        agent1.agent_name = "TestAgent1"
        agent1._agent = Mock()
        agent1.close = AsyncMock()
        agent2 = Mock()
        agent2.name = "TestAgent2"
        agent2.close = AsyncMock()
        return [agent1, agent2]


sys.modules.setdefault('agents', Mock())
sys.modules['agents.agent_factory'] = Mock(AgentFactory=MockAgentFactory)

# ---- Import module under test ----
from backend.orchestration.orchestration_manager import OrchestrationManager

# Re-bind mocked singletons for convenient assertions
connection_config = sys.modules['orchestration.connection_config'].connection_config
orchestration_config = sys.modules['orchestration.connection_config'].orchestration_config
agent_response_callback = sys.modules['callbacks.response_handlers'].agent_response_callback
streaming_agent_response_callback = sys.modules['callbacks.response_handlers'].streaming_agent_response_callback


# =========================================================================
# init_orchestration
# =========================================================================
class TestInitOrchestration:
    """Test OrchestrationManager.init_orchestration()."""

    def setup_method(self):
        mock_config.get_azure_credential.reset_mock()
        mock_magentic_builder.reset_mock()
        mock_magentic_builder.return_value.build.return_value = Mock()

    @pytest.mark.asyncio
    async def test_given_valid_args_when_init_then_returns_workflow(self):
        # Arrange
        agents = [MockAgent(agent_name="A1", has_inner_agent=True), MockAgent(name="A2")]

        # Act
        workflow = await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=MockTeamConfiguration(),
            memory_store=MockDatabaseBase(),
            user_id="user-1",
        )

        # Assert
        assert workflow is not None
        mock_config.get_azure_credential.assert_called_once()
        mock_magentic_builder.assert_called_once()
        call_kwargs = mock_magentic_builder.call_args.kwargs
        assert call_kwargs["enable_plan_review"] is True
        assert call_kwargs["intermediate_outputs"] is True

    @pytest.mark.asyncio
    async def test_given_no_user_id_when_init_then_raises_value_error(self):
        with pytest.raises(ValueError, match="user_id is required"):
            await OrchestrationManager.init_orchestration(
                agents=[Mock()],
                team_config=MockTeamConfiguration(),
                memory_store=MockDatabaseBase(),
                user_id=None,
            )

    @pytest.mark.asyncio
    async def test_given_empty_user_id_when_init_then_raises_value_error(self):
        with pytest.raises(ValueError, match="user_id is required"):
            await OrchestrationManager.init_orchestration(
                agents=[Mock()],
                team_config=MockTeamConfiguration(),
                memory_store=MockDatabaseBase(),
                user_id="",
            )

    @pytest.mark.asyncio
    async def test_given_client_failure_when_init_then_propagates(self):
        # Arrange
        with patch('backend.orchestration.orchestration_manager.FoundryChatClient',
                   side_effect=Exception("Client boom")):
            # Act & Assert
            with pytest.raises(Exception, match="Client boom"):
                await OrchestrationManager.init_orchestration(
                    agents=[Mock()],
                    team_config=MockTeamConfiguration(),
                    memory_store=MockDatabaseBase(),
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_given_agents_with_inner_agent_when_init_then_unwraps(self):
        # Arrange
        inner = Mock()
        outer = Mock()
        outer.agent_name = "Wrapped"
        outer._agent = inner
        outer.user_responses = False

        # Act
        await OrchestrationManager.init_orchestration(
            agents=[outer],
            team_config=MockTeamConfiguration(),
            memory_store=MockDatabaseBase(),
            user_id="user-1",
        )

        # Assert — participants list should contain the inner agent
        call_kwargs = mock_magentic_builder.call_args.kwargs
        assert inner in call_kwargs["participants"]

    @pytest.mark.asyncio
    async def test_given_agent_without_name_when_init_then_assigns_fallback(self):
        # Arrange — agent with neither agent_name nor name
        bare_agent = Mock(spec=[])

        # Act — should not raise
        await OrchestrationManager.init_orchestration(
            agents=[bare_agent],
            team_config=MockTeamConfiguration(),
            memory_store=MockDatabaseBase(),
            user_id="user-1",
        )

        # Assert
        mock_magentic_builder.assert_called_once()


# =========================================================================
# get_current_or_new_orchestration
# =========================================================================
class TestGetCurrentOrNewOrchestration:
    """Test OrchestrationManager.get_current_or_new_orchestration()."""

    def setup_method(self):
        orchestration_config.orchestrations.clear()
        orchestration_config.get_current_orchestration.reset_mock()
        orchestration_config.get_current_orchestration.return_value = None

    @pytest.mark.asyncio
    async def test_given_existing_workflow_when_no_switch_then_returns_it(self):
        # Arrange
        mock_workflow = Mock()
        mock_workflow._terminated = False
        orchestration_config.get_current_orchestration.return_value = mock_workflow

        # Act
        result = await OrchestrationManager.get_current_or_new_orchestration(
            user_id="user-1",
            team_config=MockTeamConfiguration(),
            team_switched=False,
            team_service=MockTeamService(),
        )

        # Assert
        assert result == mock_workflow

    @pytest.mark.asyncio
    async def test_given_no_workflow_when_called_then_creates_new(self):
        # Arrange
        orchestration_config.get_current_orchestration.return_value = None

        with patch.object(OrchestrationManager, 'init_orchestration', new_callable=AsyncMock) as mock_init:
            mock_workflow = Mock()
            mock_init.return_value = mock_workflow

            # Act
            await OrchestrationManager.get_current_or_new_orchestration(
                user_id="user-1",
                team_config=MockTeamConfiguration(),
                team_switched=False,
                team_service=MockTeamService(),
            )

            # Assert
            mock_init.assert_called_once()
            assert orchestration_config.orchestrations["user-1"] == mock_workflow

    @pytest.mark.asyncio
    async def test_given_team_switched_when_called_then_closes_old_agents(self):
        # Arrange
        mock_agent = MockAgent(agent_name="OldAgent")
        mock_executor = Mock()
        mock_executor.agent = mock_agent
        mock_old_workflow = Mock()
        mock_old_workflow._participants = {"a1": mock_agent}
        mock_old_workflow.get_executors_list.return_value = [mock_executor]
        mock_old_workflow._user_interaction_ctx = None
        orchestration_config.get_current_orchestration.return_value = mock_old_workflow

        with patch.object(OrchestrationManager, 'init_orchestration', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = Mock()

            # Act
            await OrchestrationManager.get_current_or_new_orchestration(
                user_id="user-1",
                team_config=MockTeamConfiguration(),
                team_switched=True,
                team_service=MockTeamService(),
            )

            # Assert
            mock_agent.close.assert_awaited_once()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_given_terminated_workflow_when_called_then_creates_new(self):
        # Arrange
        mock_old = Mock()
        mock_old._terminated = True
        mock_old._participants = {}
        mock_old.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_old

        with patch.object(OrchestrationManager, 'init_orchestration', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = Mock()

            # Act
            await OrchestrationManager.get_current_or_new_orchestration(
                user_id="user-1",
                team_config=MockTeamConfiguration(),
                team_switched=False,
                team_service=MockTeamService(),
            )

            # Assert
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_given_team_switched_when_closing_then_closes_all_agents(self):
        # Arrange
        agent_a = MockAgent(agent_name="AgentA")
        agent_b = MockAgent(agent_name="AgentB")
        exec_a = Mock()
        exec_a.agent = agent_a
        exec_b = Mock()
        exec_b.agent = agent_b
        mock_old = Mock()
        mock_old._participants = {"a": agent_a, "b": agent_b}
        mock_old.get_executors_list.return_value = [exec_a, exec_b]
        mock_old._user_interaction_ctx = None
        orchestration_config.get_current_orchestration.return_value = mock_old

        with patch.object(OrchestrationManager, 'init_orchestration', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = Mock()

            # Act
            await OrchestrationManager.get_current_or_new_orchestration(
                user_id="user-1",
                team_config=MockTeamConfiguration(),
                team_switched=True,
                team_service=MockTeamService(),
            )

            # Assert — all agents closed
            agent_a.close.assert_awaited_once()
            agent_b.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_given_agent_creation_failure_when_called_then_propagates(self):
        # Arrange
        orchestration_config.get_current_orchestration.return_value = None

        with patch('backend.orchestration.orchestration_manager.AgentFactory') as mock_factory_cls:
            mock_factory = Mock()
            mock_factory.get_agents = AsyncMock(side_effect=Exception("Agent boom"))
            mock_factory_cls.return_value = mock_factory

            # Act & Assert
            with pytest.raises(Exception, match="Agent boom"):
                await OrchestrationManager.get_current_or_new_orchestration(
                    user_id="user-1",
                    team_config=MockTeamConfiguration(),
                    team_switched=False,
                    team_service=MockTeamService(),
                )

    @pytest.mark.asyncio
    async def test_given_init_failure_when_called_then_propagates(self):
        # Arrange
        orchestration_config.get_current_orchestration.return_value = None

        with patch.object(OrchestrationManager, 'init_orchestration', new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Init boom")

            # Act & Assert
            with pytest.raises(Exception, match="Init boom"):
                await OrchestrationManager.get_current_or_new_orchestration(
                    user_id="user-1",
                    team_config=MockTeamConfiguration(),
                    team_switched=False,
                    team_service=MockTeamService(),
                )


# =========================================================================
# run_orchestration
# =========================================================================
class TestRunOrchestration:
    """Test OrchestrationManager.run_orchestration() and _process_event_stream()."""

    def setup_method(self):
        orchestration_config.orchestrations.clear()
        orchestration_config.plans.clear()
        orchestration_config.get_current_orchestration.reset_mock()
        orchestration_config.set_approval_pending.reset_mock()
        connection_config.send_status_update_async.reset_mock()
        connection_config.send_status_update_async.side_effect = None
        agent_response_callback.reset_mock()
        streaming_agent_response_callback.reset_mock()
        streaming_agent_response_callback.side_effect = None
        mock_wait_approval.reset_mock()
        mock_wait_approval.return_value = MockPlanApprovalResponse(approved=True, m_plan_id="test-plan-id")
        mock_convert.reset_mock()
        mock_convert.return_value = MockMPlan()

    @pytest.mark.asyncio
    async def test_given_no_workflow_when_run_then_raises_value_error(self):
        # Arrange
        orchestration_config.get_current_orchestration.return_value = None
        manager = OrchestrationManager()

        # Act & Assert
        with pytest.raises(ValueError, match="Orchestration not initialized"):
            await manager.run_orchestration(user_id="user-1", input_task="task")

    @pytest.mark.asyncio
    async def test_given_empty_stream_when_run_then_sends_final_result(self):
        # Arrange
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter([]))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act
        await manager.run_orchestration(user_id="user-1", input_task="do stuff")

        # Assert — final result WebSocket message sent
        connection_config.send_status_update_async.assert_awaited()

    @pytest.mark.asyncio
    async def test_given_executor_completed_when_run_then_captures_final_text(self):
        # Arrange
        final_msg = MockMessage(text="Final answer text")
        events = [
            _make_event("executor_completed", data=[final_msg], executor_id="magentic_orchestrator"),
        ]
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter(events))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act
        await manager.run_orchestration(user_id="user-1", input_task="do stuff")

        # Assert — the final WS message should contain the executor's text
        call_args = connection_config.send_status_update_async.call_args_list[-1]
        sent_message = call_args[0][0]
        assert sent_message["data"]["content"] == "Final answer text"

    @pytest.mark.asyncio
    async def test_given_agent_completed_event_when_run_then_calls_agent_callback(self):
        # Arrange
        agent_msg = MockMessage(text="Agent output")
        events = [
            _make_event("executor_completed", data=[agent_msg], executor_id="hr_agent"),
        ]
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter(events))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act
        await manager.run_orchestration(user_id="user-1", input_task="task")

        # Assert
        agent_response_callback.assert_called_once_with("hr_agent", agent_msg, "user-1")

    @pytest.mark.asyncio
    async def test_given_streaming_output_when_run_then_calls_streaming_callback(self):
        # Arrange
        update = MockAgentResponseUpdate(text="chunk")
        events = [
            _make_event("output", data=update, executor_id="hr_agent"),
        ]
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter(events))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act
        await manager.run_orchestration(user_id="user-1", input_task="task")

        # Assert
        streaming_agent_response_callback.assert_awaited()

    @pytest.mark.asyncio
    async def test_given_orchestrator_streaming_when_run_then_accumulates_chunks(self):
        # Arrange
        update1 = MockAgentResponseUpdate(text="Hello ")
        update2 = MockAgentResponseUpdate(text="world")
        events = [
            _make_event("output", data=update1, executor_id="magentic_orchestrator"),
            _make_event("output", data=update2, executor_id="magentic_orchestrator"),
        ]
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter(events))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act
        await manager.run_orchestration(user_id="user-1", input_task="task")

        # Assert — fallback to joined chunks when no executor_completed
        call_args = connection_config.send_status_update_async.call_args_list[-1]
        sent_message = call_args[0][0]
        assert sent_message["data"]["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_given_new_agent_when_streaming_then_sends_header(self):
        # Arrange
        update = MockAgentResponseUpdate(text="chunk")
        events = [
            _make_event("output", data=update, executor_id="hr_agent"),
        ]
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter(events))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act
        await manager.run_orchestration(user_id="user-1", input_task="task")

        # Assert — header sent for agent switch
        header_calls = [
            c for c in connection_config.send_status_update_async.call_args_list
            if len(c[0]) > 0 and isinstance(c[0][0], MockAgentMessageStreaming)
        ]
        assert len(header_calls) >= 1

    @pytest.mark.asyncio
    async def test_given_orchestrator_event_when_run_then_no_error(self):
        # Arrange
        orch_event = MockMagenticOrchestratorEvent()
        events = [
            _make_event("magentic_orchestrator", data=orch_event),
        ]
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter(events))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act — should not raise
        await manager.run_orchestration(user_id="user-1", input_task="task")

    @pytest.mark.asyncio
    async def test_given_string_input_when_run_then_uses_str(self):
        # Arrange
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter([]))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act
        await manager.run_orchestration(user_id="user-1", input_task="plain string task")

        # Assert — workflow.run was called with the string
        mock_workflow.run.assert_called_once()
        call_args = mock_workflow.run.call_args
        assert call_args[0][0] == "plain string task"

    @pytest.mark.asyncio
    async def test_given_object_input_when_run_then_uses_description(self):
        # Arrange
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter([]))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()
        task = Mock()
        task.description = "object task desc"

        # Act
        await manager.run_orchestration(user_id="user-1", input_task=task)

        # Assert
        call_args = mock_workflow.run.call_args
        assert call_args[0][0] == "object task desc"

    @pytest.mark.asyncio
    async def test_given_workflow_error_when_run_then_sends_error_ws_and_raises(self):
        # Arrange
        mock_workflow = Mock()
        mock_workflow.run = Mock(side_effect=Exception("Workflow boom"))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act & Assert
        with pytest.raises(Exception, match="Workflow boom"):
            await manager.run_orchestration(user_id="user-1", input_task="task")

        # Assert — error status sent
        connection_config.send_status_update_async.assert_awaited()

    @pytest.mark.asyncio
    async def test_given_event_processing_error_when_run_then_continues(self):
        # Arrange
        streaming_agent_response_callback.side_effect = Exception("Callback boom")
        update = MockAgentResponseUpdate(text="x")
        events = [
            _make_event("output", data=update, executor_id="hr_agent"),
        ]
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter(events))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act — should not raise; errors are logged and swallowed
        await manager.run_orchestration(user_id="user-1", input_task="task")


# =========================================================================
# _process_event_stream — plan review
# =========================================================================
class TestProcessEventStreamPlanReview:
    """Test plan review collection within _process_event_stream()."""

    def setup_method(self):
        orchestration_config.plans.clear()
        connection_config.send_status_update_async.reset_mock()
        connection_config.send_status_update_async.side_effect = None

    @pytest.mark.asyncio
    async def test_given_plan_review_event_when_processing_then_returns_collected_requests(self):
        # Arrange
        plan_review = MockMagenticPlanReviewRequest()
        event = _make_event("request_info", data=plan_review, request_id="req-1")

        manager = OrchestrationManager()

        # Act
        result = await manager._process_event_stream(
            _async_iter([event]),
            user_id="user-1",
            final_output_ref=[None],
            orchestrator_chunks=[],
            current_streaming_agent_ref=[None],
        )

        # Assert — returns dict with plan_reviews key
        assert result is not None
        assert "plan_reviews" in result
        assert "req-1" in result["plan_reviews"]
        assert result["plan_reviews"]["req-1"] is plan_review

    @pytest.mark.asyncio
    async def test_given_multiple_plan_reviews_when_processing_then_collects_all(self):
        # Arrange
        review1 = MockMagenticPlanReviewRequest()
        review2 = MockMagenticPlanReviewRequest()
        events = [
            _make_event("request_info", data=review1, request_id="req-1"),
            _make_event("request_info", data=review2, request_id="req-2"),
        ]

        manager = OrchestrationManager()

        # Act
        result = await manager._process_event_stream(
            _async_iter(events),
            user_id="user-1",
            final_output_ref=[None],
            orchestrator_chunks=[],
            current_streaming_agent_ref=[None],
        )

        # Assert
        assert result is not None
        assert "plan_reviews" in result
        assert len(result["plan_reviews"]) == 2
        assert "req-1" in result["plan_reviews"]
        assert "req-2" in result["plan_reviews"]

    @pytest.mark.asyncio
    async def test_given_no_plan_review_when_stream_completes_then_returns_none(self):
        # Arrange
        events = [_make_event("magentic_orchestrator", data=MockMagenticOrchestratorEvent())]
        manager = OrchestrationManager()

        # Act
        result = await manager._process_event_stream(
            _async_iter(events),
            user_id="user-1",
            final_output_ref=[None],
            orchestrator_chunks=[],
            current_streaming_agent_ref=[None],
        )

        # Assert
        assert result is None


# =========================================================================
# run_orchestration — resume loop
# =========================================================================
class TestRunOrchestrationResumeLoop:
    """Test the resume loop in run_orchestration()."""

    def setup_method(self):
        orchestration_config.plans.clear()
        orchestration_config.set_approval_pending.reset_mock()
        connection_config.send_status_update_async.reset_mock()
        connection_config.send_status_update_async.side_effect = None
        mock_wait_approval.reset_mock()
        mock_convert.reset_mock()
        mock_convert.return_value = MockMPlan()

    @pytest.mark.asyncio
    async def test_given_plan_review_then_completion_when_run_then_resumes(self):
        # Arrange — first call returns plan review, second call completes
        plan_review = MockMagenticPlanReviewRequest()
        review_event = _make_event("request_info", data=plan_review, request_id="req-1")
        final_msg = MockMessage(text="Done")
        completion_event = _make_event("executor_completed", data=[final_msg], executor_id="magentic_orchestrator")

        call_count = [0]

        def mock_run(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _async_iter([review_event])
            return _async_iter([completion_event])

        mock_wait_approval.return_value = MockPlanApprovalResponse(approved=True, m_plan_id="test-plan-id")

        mock_workflow = Mock()
        mock_workflow.run = mock_run
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act
        await manager.run_orchestration(user_id="user-1", input_task="task")

        # Assert — workflow.run called twice (initial + resume)
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_given_approval_pending_when_run_then_sets_pending(self):
        # Arrange
        mock_workflow = Mock()
        mock_workflow.run = Mock(return_value=_async_iter([]))
        mock_workflow._executors = {}
        mock_workflow.executors = {}
        mock_workflow.get_executors_list.return_value = []
        orchestration_config.get_current_orchestration.return_value = mock_workflow
        manager = OrchestrationManager()

        # Act
        await manager.run_orchestration(user_id="user-1", input_task="task")

        # Assert
        orchestration_config.set_approval_pending.assert_called_once()


class TestOrchestrationManagerInit:
    """Test OrchestrationManager constructor."""

    def test_given_new_instance_when_init_then_user_id_is_none(self):
        manager = OrchestrationManager()

        assert manager.user_id is None

    def test_given_new_instance_when_init_then_logger_is_set(self):
        manager = OrchestrationManager()

        assert isinstance(manager.logger, logging.Logger)


# _normalize_markdown_tables (Bug 47810)
from backend.orchestration.orchestration_manager import (  # noqa: E402
    _normalize_markdown_tables,
)
from common.utils.markdown_utils import (  # noqa: E402
    reflow_collapsed_table_line as _reflow_collapsed_table_line,
)


class TestNormalizeMarkdownTables:
    """Test markdown table re-flow for collapsed orchestrator output (Bug 47810)."""

    def test_given_collapsed_table_when_normalized_then_rows_split_to_lines(self):
        collapsed = (
            "| Risk Type | Description | Rating | "
            "|-------|-------|-------| "
            "| Delivery | Undefined timeline | Medium | "
            "| Financial | Fixed budget | High |"
        )

        result = _normalize_markdown_tables(collapsed)

        lines = [ln for ln in result.split("\n") if ln.strip()]
        assert lines == [
            "| Risk Type | Description | Rating |",
            "| ------- | ------- | ------- |",
            "| Delivery | Undefined timeline | Medium |",
            "| Financial | Fixed budget | High |",
        ]

    def test_given_collapsed_table_with_prefix_then_prefix_kept_on_own_line(self):
        collapsed = (
            "Risk Analysis | A | B | |---|---| | 1 | 2 |"
        )

        result = _normalize_markdown_tables(collapsed)

        # Prefix prose separated from the table by a blank line for GFM.
        assert result.startswith("Risk Analysis\n\n| A | B |")

    def test_given_wellformed_table_when_normalized_then_unchanged(self):
        good = "| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |"

        assert _normalize_markdown_tables(good) == good

    def test_given_plain_text_when_normalized_then_unchanged(self):
        text = "Just some text with a - dash and | a pipe."

        assert _normalize_markdown_tables(text) == text

    def test_given_colon_aligned_delimiter_when_normalized_then_alignment_kept(self):
        collapsed = "| A | B | C | |:--|:-:|--:| | 1 | 2 | 3 |"

        result = _normalize_markdown_tables(collapsed)

        assert "| :-- | :-: | --: |" in result

    def test_given_empty_or_none_when_normalized_then_returns_input(self):
        assert _normalize_markdown_tables("") == ""
        assert _normalize_markdown_tables(None) is None

    def test_given_non_table_pipe_line_when_reflowed_then_returns_none(self):
        assert _reflow_collapsed_table_line("a | b | c") is None

