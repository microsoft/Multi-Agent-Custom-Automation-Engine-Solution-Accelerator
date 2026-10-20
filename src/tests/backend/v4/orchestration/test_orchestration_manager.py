"""Unit tests for orchestration_manager module.

Comprehensive test cases covering OrchestrationManager with proper mocking.
"""

import asyncio
import logging
import sys
from unittest import IsolatedAsyncioTestCase, main
from unittest.mock import AsyncMock, Mock, patch

from agent_framework import Agent, AgentResponseUpdate, Content, Message, Workflow
from agent_framework_orchestrations._base_group_chat_orchestrator import (
    GroupChatRequestSentEvent,
    GroupChatResponseReceivedEvent,
)

# Mock external Azure dependencies


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


class MockMagenticAgentDeltaEvent:
    """Mock MagenticAgentDeltaEvent."""

    def __init__(self, agent_id="test_agent"):
        self.agent_id = agent_id
        self.delta = "streaming update"


class MockAgent:
    """Mock agent class with proper attributes."""

    def __init__(self, agent_name=None, name=None, has_inner_agent=False):
        if agent_name:
            self.agent_name = agent_name
        if name:
            self.name = name
        if has_inner_agent:
            self._agent = Agent(client=Mock(), name=agent_name or name)
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


# Base class for orchestrator events - needed for isinstance() checks


# Set up agent_framework mocks
# agent_framework_orchestrations mocks (source imports from these paths)

# Mock common modules
mock_config = Mock()
mock_config.get_azure_credential.return_value = Mock()
mock_config.AZURE_CLIENT_ID = "test_client_id"
mock_config.AZURE_AI_PROJECT_ENDPOINT = "https://test.project.azure.com/"


class MockTeamConfiguration:
    """Mock TeamConfiguration."""

    def __init__(self, name="TestTeam", deployment_name="test_deployment"):
        self.name = name
        self.deployment_name = deployment_name


class MockDatabaseBase:
    """Mock DatabaseBase."""

    pass


# Mock v4 modules
class MockTeamService:
    """Mock TeamService."""

    def __init__(self):
        self.memory_context = MockDatabaseBase()


# Mock v4.config.settings
mock_connection_config = Mock()
mock_connection_config.send_status_update_async = AsyncMock()

mock_orchestration_config = Mock()
mock_orchestration_config.max_rounds = 10
mock_orchestration_config.orchestrations = {}
# Source stores/pops agent wrappers per user (cleanup on rebuild) — must be a real dict
mock_orchestration_config.agent_wrappers = {}
# Source stores the HumanApprovalMagenticManager per user (chat_history seeding)
mock_orchestration_config.managers = {}
mock_orchestration_config.get_current_orchestration = Mock(return_value=None)


# Mock v4.models.messages


# Mock v4.orchestration.human_approval_manager


# Mock v4.magentic_agents.magentic_agent_factory
class MockMagenticAgentFactory:
    """Mock MagenticAgentFactory."""

    def __init__(self, team_service=None):
        self.team_service = team_service

    async def get_agents(
        self,
        user_id,
        team_config_input,
        memory_store,
        user_access_token=None,
        workspace_id=None,
    ):
        # El workspace activo llega hasta la fábrica: sin él los agentes con MCP
        # llaman a las tools con un id inventado.
        self.workspace_id = workspace_id
        # Create mock agents
        agent1 = Mock()
        agent1.agent_name = "TestAgent1"
        agent1._agent = Mock()  # Inner agent for wrapper templates
        agent1.close = AsyncMock()

        agent2 = Mock()
        agent2.name = "TestAgent2"
        agent2.close = AsyncMock()

        return [agent1, agent2]


# Now import the module under test
import pytest

from v4.orchestration.orchestration_manager import (  # noqa: E402
    OrchestrationManager,
)

# Colaboradores del módulo bajo test: los mismos objetos que la fixture
# instala en su namespace durante cada test (setUp los resetea).
connection_config = mock_connection_config
orchestration_config = mock_orchestration_config
streaming_agent_response_callback = AsyncMock()


@pytest.fixture(autouse=True)
def _collaborators_patched(monkeypatch):
    """Colaboradores de v4.orchestration.orchestration_manager parcheados en SU namespace y sólo durante cada
    test. Antes eran Mocks instalados en sys.modules a nivel de módulo para
    todo el proceso (INC-2026-004)."""
    import importlib

    mod = importlib.import_module("v4.orchestration.orchestration_manager")
    for name, value in (
        ("connection_config", connection_config),
        ("orchestration_config", orchestration_config),
        ("streaming_agent_response_callback", streaming_agent_response_callback),
        ("config", mock_config),
        ("MagenticAgentFactory", MockMagenticAgentFactory),
    ):
        monkeypatch.setattr(mod, name, value)


class TestOrchestrationManager(IsolatedAsyncioTestCase):
    """Test cases for OrchestrationManager class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Reset mocks — reset_mock() does NOT clear side_effect,
        # so we must do it explicitly to avoid cross-test pollution.
        orchestration_config.orchestrations.clear()
        orchestration_config.agent_wrappers.clear()
        orchestration_config.managers.clear()
        orchestration_config.get_current_orchestration.return_value = None
        connection_config.send_status_update_async.reset_mock()
        connection_config.send_status_update_async.side_effect = None
        streaming_agent_response_callback.reset_mock()
        streaming_agent_response_callback.side_effect = None

        # Create test instance
        self.orchestration_manager = OrchestrationManager()
        self.test_user_id = "test_user_123"
        self.test_session_id = "test_session_456"
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
        agent2 = Agent(client=Mock(), name="TestAgent2")

        agents = [agent1, agent2]

        workflow = await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=self.test_team_config,
            memory_store=MockDatabaseBase(),
            user_id=self.test_user_id,
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
                user_id=None,
            )

        self.assertIn("user_id is required", str(context.exception))

    @patch("v4.orchestration.orchestration_manager.Agent")
    @patch("v4.orchestration.orchestration_manager.AzureAIClient")
    async def test_the_manager_thinks_with_the_orchestrator_inference_contract(
        self, mock_client_class, mock_agent_class
    ):
        """Un solo cerebro: el manager del plan piensa con el modelo y el
        reasoning del orquestador del chat; el modelo del equipo es el de los
        participantes, no el del que planifica y juzga."""
        agents = [
            MockAgent(agent_name="TestAgent1", has_inner_agent=True),
            Agent(client=Mock(), name="TestAgent2"),
        ]
        await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=self.test_team_config,
            memory_store=MockDatabaseBase(),
            user_id=self.test_user_id,
        )
        client_kwargs = mock_client_class.call_args.kwargs
        self.assertIs(
            client_kwargs["model_deployment_name"], mock_config.CHAT_ORCHESTRATOR_MODEL
        )
        self.assertNotEqual(
            client_kwargs["model_deployment_name"],
            self.test_team_config.deployment_name,
        )
        agent_kwargs = next(
            c.kwargs
            for c in mock_agent_class.call_args_list
            if c.kwargs.get("name") == "MagenticManager"
        )
        self.assertEqual(
            agent_kwargs["default_options"],
            {"reasoning": {"effort": mock_config.CHAT_ORCHESTRATOR_REASONING_EFFORT}},
        )

    @patch("v4.orchestration.orchestration_manager.AzureAIClient")
    async def test_init_orchestration_client_creation_failure(self, mock_client_class):
        """Test orchestration initialization when client creation fails."""
        mock_client_class.side_effect = Exception("Client creation failed")

        agents = [Mock()]

        with self.assertRaises(Exception) as context:
            await OrchestrationManager.init_orchestration(
                agents=agents,
                team_config=self.test_team_config,
                memory_store=MockDatabaseBase(),
                user_id=self.test_user_id,
            )

        self.assertIn("Client creation failed", str(context.exception))

    @patch("v4.orchestration.orchestration_manager.HumanApprovalMagenticManager")
    async def test_init_orchestration_manager_creation_failure(
        self, mock_manager_class
    ):
        """Test orchestration initialization when manager creation fails."""
        mock_manager_class.side_effect = Exception("Manager creation failed")

        agents = [Mock()]

        with self.assertRaises(Exception) as context:
            await OrchestrationManager.init_orchestration(
                agents=agents,
                team_config=self.test_team_config,
                memory_store=MockDatabaseBase(),
                user_id=self.test_user_id,
            )

        self.assertIn("Manager creation failed", str(context.exception))

    async def test_init_orchestration_participants_mapping(self):
        """Test proper participant mapping in orchestration initialization."""
        # Use MockAgent to avoid attribute issues
        # Un wrapper con agente interno (el builder recibe ._agent) y un agente
        # directo. Un participante sin nombre no existe en el contrato real:
        # MagenticBuilder rechaza SupportsAgentRun sin nombre.
        agent_with_agent_name = MockAgent(
            agent_name="AgentWithAgentName", has_inner_agent=True
        )
        agent_with_name = Agent(client=Mock(), name="AgentWithName")

        agents = [agent_with_agent_name, agent_with_name]

        workflow = await OrchestrationManager.init_orchestration(
            agents=agents,
            team_config=self.test_team_config,
            memory_store=MockDatabaseBase(),
            user_id=self.test_user_id,
        )

        self.assertIsInstance(workflow, Workflow)

    async def test_get_current_or_new_orchestration_existing(self):
        """Test getting existing orchestration."""
        # Set up existing orchestration
        mock_workflow = Mock()
        orchestration_config.get_current_orchestration.return_value = mock_workflow

        result = await OrchestrationManager.get_current_or_new_orchestration(
            user_id=self.test_user_id,
            team_config=self.test_team_config,
            team_switched=False,
            team_service=self.test_team_service,
        )

        self.assertEqual(result, mock_workflow)
        orchestration_config.get_current_orchestration.assert_called_with(
            self.test_user_id
        )

    async def test_get_current_or_new_orchestration_new(self):
        """Test creating new orchestration when none exists."""
        # No existing orchestration
        orchestration_config.get_current_orchestration.return_value = None

        with patch.object(
            OrchestrationManager, "init_orchestration", new_callable=AsyncMock
        ) as mock_init:
            mock_workflow = Mock()
            mock_init.return_value = mock_workflow

            await OrchestrationManager.get_current_or_new_orchestration(
                user_id=self.test_user_id,
                team_config=self.test_team_config,
                team_switched=False,
                team_service=self.test_team_service,
            )

            # Verify new orchestration was created and stored
            mock_init.assert_called_once()
            self.assertEqual(
                orchestration_config.orchestrations[self.test_user_id], mock_workflow
            )

    async def test_get_current_or_new_orchestration_team_switched(self):
        """Test creating new orchestration when team is switched."""
        # Set up existing orchestration; prior agent wrappers (tracked in
        # orchestration_config.agent_wrappers) are what gets closed on rebuild.
        mock_existing_workflow = Mock()
        mock_agent = MockAgent(agent_name="TestAgent")
        orchestration_config.agent_wrappers[self.test_user_id] = [mock_agent]

        orchestration_config.get_current_orchestration.return_value = (
            mock_existing_workflow
        )

        with patch.object(
            OrchestrationManager, "init_orchestration", new_callable=AsyncMock
        ) as mock_init:
            mock_new_workflow = Mock()
            mock_init.return_value = mock_new_workflow

            await OrchestrationManager.get_current_or_new_orchestration(
                user_id=self.test_user_id,
                team_config=self.test_team_config,
                team_switched=True,
                team_service=self.test_team_service,
            )

            # Verify agents were closed and new orchestration was created
            mock_agent.close.assert_called_once()
            mock_init.assert_called_once()
            self.assertEqual(
                orchestration_config.orchestrations[self.test_user_id],
                mock_new_workflow,
            )
            # New wrappers replace the closed ones
            new_wrappers = orchestration_config.agent_wrappers[self.test_user_id]
            self.assertNotIn(mock_agent, new_wrappers)
            self.assertEqual(len(new_wrappers), 2)

    async def test_get_current_or_new_orchestration_agent_creation_failure(self):
        """Test handling agent creation failure."""
        orchestration_config.get_current_orchestration.return_value = None

        # Mock agent factory to raise exception
        with patch(
            "v4.orchestration.orchestration_manager.MagenticAgentFactory"
        ) as mock_factory_class:
            mock_factory = Mock()
            mock_factory.get_agents = AsyncMock(
                side_effect=Exception("Agent creation failed")
            )
            mock_factory_class.return_value = mock_factory

            with self.assertRaises(Exception) as context:
                await OrchestrationManager.get_current_or_new_orchestration(
                    user_id=self.test_user_id,
                    team_config=self.test_team_config,
                    team_switched=False,
                    team_service=self.test_team_service,
                )

            self.assertIn("Agent creation failed", str(context.exception))

    async def test_get_current_or_new_orchestration_init_failure(self):
        """Test handling orchestration initialization failure."""
        orchestration_config.get_current_orchestration.return_value = None

        with patch.object(
            OrchestrationManager, "init_orchestration", new_callable=AsyncMock
        ) as mock_init:
            mock_init.side_effect = Exception("Orchestration init failed")

            with self.assertRaises(Exception) as context:
                await OrchestrationManager.get_current_or_new_orchestration(
                    user_id=self.test_user_id,
                    team_config=self.test_team_config,
                    team_switched=False,
                    team_service=self.test_team_service,
                )

            self.assertIn("Orchestration init failed", str(context.exception))

    async def test_run_orchestration_success(self):
        """Test successful orchestration execution."""
        mock_workflow = Mock()
        # El producto despacha por isinstance sobre las clases reales del framework.
        mock_events = [
            Mock(
                type="magentic_orchestrator",
                data=Message(role="assistant", text="Plan message"),
            ),
            Mock(
                type="group_chat",
                data=GroupChatRequestSentEvent(
                    round_index=1, participant_name="agent_1"
                ),
            ),
            Mock(
                type="output",
                executor_id="agent_1",
                data=AgentResponseUpdate(
                    contents=[Content.from_text("Agent streaming update")]
                ),
            ),
            Mock(
                type="group_chat",
                data=GroupChatResponseReceivedEvent(
                    round_index=1, participant_name="agent_1"
                ),
            ),
            Mock(
                type="output",
                executor_id=None,
                data=Message(role="assistant", text="Final result"),
            ),
        ]
        mock_workflow.run = AsyncGeneratorMock(mock_events)
        mock_workflow.executors = {
            "magentic_orchestrator": Mock(_conversation=[]),
            "agent_1": Mock(_chat_history=[]),
        }

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        # Mock input task (context must be a real str — source seeds it into task_text)
        input_task = Mock()
        input_task.description = "Test task description"
        input_task.context = ""

        # Execute orchestration
        self.orchestration_manager._persist_agent_message = AsyncMock()
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        # Verify streaming callback was called (for AgentRunUpdateEvent)
        streaming_agent_response_callback.assert_called()

        # Verify final result was sent
        connection_config.send_status_update_async.assert_called()

    async def test_final_result_is_durable_before_the_websocket_signal(self):
        """The UI reloads the session the moment FINAL_RESULT arrives (it drops
        planId → GET /chat/sessions). Measured on revision 132 the reload ran
        424 ms before the write-back, so the page showed stale state. Every
        durable write (plan store, chat session) must precede the signal."""
        order: list[str] = []
        mock_workflow = Mock()
        mock_workflow.name = "wf"
        mock_workflow.run = AsyncGeneratorMock(
            [
                Mock(
                    type="output",
                    executor_id=None,
                    data=Message(role="assistant", text="Final result"),
                )
            ]
        )
        mock_workflow.executors = {}
        orchestration_config.get_current_orchestration.return_value = mock_workflow

        async def _persist(**_kw):
            order.append("plan_store")

        async def _signal(_payload, _user, message_type=None, process_id=None):
            order.append(f"ws:{getattr(message_type, 'value', message_type)}")

        chat_svc = Mock()

        async def _add_message(**_kw):
            order.append("chat_session")

        chat_svc.add_message = _add_message
        self.orchestration_manager._persist_agent_message = _persist
        self.orchestration_manager._purge_checkpoint_lineage_by_id = AsyncMock()
        connection_config.send_status_update_async.side_effect = _signal

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = ""
        with patch(
            "common.services.chat_cosmos_service.get_chat_cosmos_service",
            AsyncMock(return_value=chat_svc),
        ):
            await self.orchestration_manager.run_orchestration(
                user_id=self.test_user_id,
                session_id=self.test_session_id,
                input_task=input_task,
                plan_id="plan-1",
            )

        final_idx = order.index("ws:final_result_message")
        self.assertIn("plan_store", order[:final_idx])
        self.assertIn("chat_session", order[:final_idx])

    async def test_turn_log_is_capped_and_overflow_count_persisted(self):
        """A plan that produces more deeds than ``_LEDGER_MAX_DEEDS`` must cap
        ``turn_log`` and persist the exact overflow count in ``turn_log_dropped``
        so the chat session item stays under the 2 MB Cosmos limit (regression
        guard against unbounded appends)."""
        from v4.api.router import _LEDGER_MAX_DEEDS

        overflow = 4
        total_rounds = _LEDGER_MAX_DEEDS + overflow

        # Each round contributes exactly one deed: a request-sent opens the
        # response window, a streamed chunk fills the buffer, and a
        # response-received flushes it into the turn_log.
        events: list = []
        for round_index in range(1, total_rounds + 1):
            events.append(
                Mock(
                    type="group_chat",
                    data=GroupChatRequestSentEvent(
                        round_index=round_index, participant_name="agent_1"
                    ),
                )
            )
            events.append(
                Mock(
                    type="output",
                    executor_id="agent_1",
                    data=AgentResponseUpdate(
                        contents=[Content.from_text(f"response {round_index}")]
                    ),
                )
            )
            events.append(
                Mock(
                    type="group_chat",
                    data=GroupChatResponseReceivedEvent(
                        round_index=round_index, participant_name="agent_1"
                    ),
                )
            )
        events.append(
            Mock(
                type="output",
                executor_id=None,
                data=Message(role="assistant", text="Final result"),
            )
        )

        mock_workflow = Mock()
        mock_workflow.run = AsyncGeneratorMock(events)
        mock_workflow.executors = {}
        orchestration_config.get_current_orchestration.return_value = mock_workflow

        captured_metadata: dict = {}
        chat_svc = Mock()

        async def _add_message(**kwargs):
            captured_metadata.update(kwargs.get("metadata") or {})

        chat_svc.add_message = _add_message
        self.orchestration_manager._persist_agent_message = AsyncMock()

        input_task = Mock()
        input_task.description = "Test overflow"
        input_task.context = ""

        with patch(
            "common.services.chat_cosmos_service.get_chat_cosmos_service",
            AsyncMock(return_value=chat_svc),
        ):
            await self.orchestration_manager.run_orchestration(
                user_id=self.test_user_id,
                session_id=self.test_session_id,
                input_task=input_task,
                plan_id="plan-overflow",
            )

        self.assertEqual(len(captured_metadata["turn_log"]), _LEDGER_MAX_DEEDS)
        self.assertEqual(captured_metadata["turn_log_dropped"], overflow)

    async def test_run_orchestration_no_workflow(self):
        """Test run_orchestration when no workflow exists."""
        orchestration_config.get_current_orchestration.return_value = None

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = ""

        with self.assertRaises(ValueError) as context:
            await self.orchestration_manager.run_orchestration(
                user_id=self.test_user_id,
                session_id=self.test_session_id,
                input_task=input_task,
            )

        self.assertIn("Orchestration not initialized", str(context.exception))

    async def test_run_orchestration_workflow_execution_error(self):
        """Test run_orchestration when workflow execution fails."""
        # Set up mock workflow that raises exception
        mock_workflow = Mock()
        mock_workflow.run = AsyncGeneratorMock([])
        mock_workflow.run = Mock(side_effect=Exception("Workflow execution failed"))
        mock_workflow.executors = {}

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = ""

        with self.assertRaises(Exception):
            await self.orchestration_manager.run_orchestration(
                user_id=self.test_user_id,
                session_id=self.test_session_id,
                input_task=input_task,
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
            "agent_1": mock_agent_executor,
        }
        mock_workflow.run = AsyncGeneratorMock([])

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = ""

        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
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
        mock_workflow.executors = {"magentic_orchestrator": mock_executor}
        mock_workflow.run = AsyncGeneratorMock([])

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = ""

        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
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
        mock_workflow.executors = {"magentic_orchestrator": mock_executor}
        mock_workflow.run = AsyncGeneratorMock([])

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = ""

        # Should not raise exception - clearing failures are handled gracefully
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        # Verify workflow still executed
        mock_workflow.run.assert_called_once()

    async def test_run_orchestration_event_processing_error(self):
        """Test handling of errors during event processing."""
        # Set up workflow with events that cause processing errors
        mock_workflow = Mock()
        mock_events = [MockMagenticAgentDeltaEvent()]
        mock_workflow.run = AsyncGeneratorMock(mock_events)
        mock_workflow.executors = {}

        # Make streaming callback raise exception
        streaming_agent_response_callback.side_effect = Exception("Callback error")

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = ""

        # Should not raise exception - event processing errors are handled
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        # Reset side effect for other tests
        streaming_agent_response_callback.side_effect = None

    def test_run_orchestration_requires_initialized_workflow(self):
        """No workflow for the user -> ValueError before any work starts."""
        orchestration_config.get_current_orchestration.return_value = None

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = ""

        # Run should fail due to no workflow, but we can test the setup
        with self.assertRaises(ValueError):
            asyncio.run(
                self.orchestration_manager.run_orchestration(
                    user_id=self.test_user_id,
                    session_id=self.test_session_id,
                    input_task=input_task,
                )
            )

    async def test_run_orchestration_string_input_task(self):
        """Test run_orchestration with string input task."""
        mock_workflow = Mock()
        mock_workflow.run = AsyncGeneratorMock([])
        mock_workflow.executors = {}

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        # Use string input instead of object
        input_task = "Simple string task"

        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        # Verify workflow was called with the string
        mock_workflow.run.assert_called_once_with("Simple string task", stream=True)

    async def test_run_orchestration_websocket_error_handling(self):
        """Test handling of WebSocket sending errors."""
        mock_workflow = Mock()
        mock_workflow.run = AsyncGeneratorMock([])
        mock_workflow.executors = {}

        # Make WebSocket sending fail
        connection_config.send_status_update_async.side_effect = Exception(
            "WebSocket error"
        )

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = ""

        # The method should handle WebSocket errors gracefully by catching them
        # and trying to send error status, which will also fail, but shouldn't raise
        try:
            await self.orchestration_manager.run_orchestration(
                user_id=self.test_user_id,
                session_id=self.test_session_id,
                input_task=input_task,
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
        events = [
            Mock(
                type="magentic_orchestrator",
                data=Message(role="assistant", text="Plan message"),
            ),
            Mock(
                type="group_chat",
                data=GroupChatRequestSentEvent(
                    round_index=1, participant_name="agent_1"
                ),
            ),
            Mock(
                type="output",
                executor_id="agent_1",
                data=AgentResponseUpdate(
                    contents=[Content.from_text("Agent streaming update")]
                ),
            ),
            Mock(
                type="group_chat",
                data=GroupChatResponseReceivedEvent(
                    round_index=1, participant_name="agent_1"
                ),
            ),
            Mock(type="executor_completed", executor_id="agent_1"),
            Mock(),  # Unknown event type - should be safely ignored
        ]
        mock_workflow.run = AsyncGeneratorMock(events)
        mock_workflow.executors = {}

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test all events"
        input_task.context = ""

        # Should process all events without errors
        self.orchestration_manager._persist_agent_message = AsyncMock()
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        # Verify streaming callback was called (for output event with AgentResponseUpdate data)
        streaming_agent_response_callback.assert_called()

    # ── Harvested from upstream dev-v4 (functional spec, anti-zombie plans) ──
    # Adapted: session_id added (local signature requires it — mechanical drift)
    # and DatabaseFactory patched on the module attribute instead of upstream's
    # global sys.modules mock, which would poison the rest of the suite.

    async def test_run_orchestration_marks_plan_failed_on_exception(self):
        """When orchestration raises and plan_id is set, plan.overall_status must be
        updated to FAILED via DatabaseFactory/get_plan_by_plan_id/update_plan."""
        mock_workflow = Mock()
        mock_workflow.executors = {}
        mock_workflow.run = Mock(side_effect=Exception("Workflow execution failed"))
        orchestration_config.get_current_orchestration.return_value = mock_workflow

        mock_plan = Mock()
        mock_plan.overall_status = "in_progress"
        mock_memory_store = Mock()
        mock_memory_store.get_plan_by_plan_id = AsyncMock(return_value=mock_plan)
        mock_memory_store.update_plan = AsyncMock()

        db_factory_mock = Mock()
        db_factory_mock.get_database = AsyncMock(return_value=mock_memory_store)

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = (
            ""  # local seeding does len(context) — a bare Mock breaks it
        )

        with patch.dict(
            sys.modules,
            {"common.database.database_factory": Mock(DatabaseFactory=db_factory_mock)},
        ):
            with self.assertRaises(Exception):
                await self.orchestration_manager.run_orchestration(
                    user_id=self.test_user_id,
                    session_id=self.test_session_id,
                    input_task=input_task,
                    plan_id="plan-123",
                )

        db_factory_mock.get_database.assert_awaited_with(user_id=self.test_user_id)
        mock_memory_store.get_plan_by_plan_id.assert_awaited_with(plan_id="plan-123")
        mock_memory_store.update_plan.assert_awaited_once()
        self.assertEqual(mock_plan.overall_status, "failed")

    async def test_run_orchestration_db_failure_does_not_mask_original_error(self):
        """If the DB update itself fails, the original orchestration error must still
        propagate (the DB error is logged and swallowed)."""
        mock_workflow = Mock()
        mock_workflow.executors = {}
        original_error = RuntimeError("Workflow boom")
        mock_workflow.run = Mock(side_effect=original_error)
        orchestration_config.get_current_orchestration.return_value = mock_workflow

        db_factory_mock = Mock()
        db_factory_mock.get_database = AsyncMock(
            side_effect=Exception("DB unavailable")
        )

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = (
            ""  # local seeding does len(context) — a bare Mock breaks it
        )

        with patch.dict(
            sys.modules,
            {"common.database.database_factory": Mock(DatabaseFactory=db_factory_mock)},
        ):
            with self.assertRaises(RuntimeError) as ctx:
                await self.orchestration_manager.run_orchestration(
                    user_id=self.test_user_id,
                    session_id=self.test_session_id,
                    input_task=input_task,
                    plan_id="plan-123",
                )
        self.assertIn("Workflow boom", str(ctx.exception))

    async def test_run_orchestration_skips_db_update_when_no_plan_id(self):
        """When plan_id is not provided, the orchestration must not touch the DB on failure."""
        mock_workflow = Mock()
        mock_workflow.executors = {}
        mock_workflow.run = Mock(side_effect=Exception("Workflow execution failed"))
        orchestration_config.get_current_orchestration.return_value = mock_workflow

        db_factory_mock = Mock()
        db_factory_mock.get_database = AsyncMock()

        input_task = Mock()
        input_task.description = "Test task"
        input_task.context = (
            ""  # local seeding does len(context) — a bare Mock breaks it
        )

        with patch.dict(
            sys.modules,
            {"common.database.database_factory": Mock(DatabaseFactory=db_factory_mock)},
        ):
            with self.assertRaises(Exception):
                await self.orchestration_manager.run_orchestration(
                    user_id=self.test_user_id,
                    session_id=self.test_session_id,
                    input_task=input_task,
                )

        db_factory_mock.get_database.assert_not_awaited()


class TestExtractResponseText(IsolatedAsyncioTestCase):
    """Test _extract_response_text method for various input types."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = OrchestrationManager()

    def test_extract_response_text_none(self):
        """Test extracting text from None returns empty string."""
        result = self.manager._extract_response_text(None)
        self.assertEqual(result, "")

    def test_extract_response_text_chat_message(self):
        """Test extracting text from ChatMessage."""
        msg = MockChatMessage("Hello world")
        result = self.manager._extract_response_text(msg)
        self.assertEqual(result, "Hello world")

    def test_extract_response_text_chat_message_empty_text(self):
        """Test extracting text from ChatMessage with empty text."""
        msg = MockChatMessage("")
        result = self.manager._extract_response_text(msg)
        self.assertEqual(result, "")

    def test_extract_response_text_object_with_text_attr(self):
        """Test extracting text from object with text attribute."""
        obj = Mock()
        obj.text = "Agent response"
        result = self.manager._extract_response_text(obj)
        self.assertEqual(result, "Agent response")

    def test_extract_response_text_object_with_empty_text(self):
        """Test extracting text from object with empty text attribute."""
        # Use spec to ensure only specified attributes exist
        obj = Mock(spec_set=["text"])
        obj.text = ""
        result = self.manager._extract_response_text(obj)
        self.assertEqual(result, "")

    def test_extract_response_text_agent_executor_response_with_agent_response(self):
        """Test extracting text from AgentExecutorResponse with agent_response.text."""
        agent_resp = Mock(spec_set=["text"])
        agent_resp.text = "Agent executor response"

        executor_resp = Mock(spec_set=["agent_response"])
        executor_resp.agent_response = agent_resp

        result = self.manager._extract_response_text(executor_resp)
        self.assertEqual(result, "Agent executor response")

    def test_extract_response_text_agent_executor_response_fallback_to_conversation(
        self,
    ):
        """Test extracting text from AgentExecutorResponse falling back to full_conversation."""
        agent_resp = Mock(spec_set=["text"])
        agent_resp.text = None

        last_msg = Message(role="assistant", text="Last conversation message")

        executor_resp = Mock(spec_set=["agent_response", "full_conversation"])
        executor_resp.agent_response = agent_resp
        executor_resp.full_conversation = [
            Message(role="assistant", text="First"),
            last_msg,
        ]

        result = self.manager._extract_response_text(executor_resp)
        self.assertEqual(result, "Last conversation message")

    def test_extract_response_text_agent_executor_response_empty_conversation(self):
        """Test extracting text from AgentExecutorResponse with empty conversation."""
        agent_resp = Mock(spec_set=["text"])
        agent_resp.text = None

        executor_resp = Mock(spec_set=["agent_response", "full_conversation"])
        executor_resp.agent_response = agent_resp
        executor_resp.full_conversation = []

        result = self.manager._extract_response_text(executor_resp)
        self.assertEqual(result, "")

    def test_extract_response_text_list_of_chat_messages(self):
        """Test extracting text from list of ChatMessages."""
        messages = [
            MockChatMessage("First message"),
            MockChatMessage("Second message"),
            MockChatMessage("Last message"),
        ]
        result = self.manager._extract_response_text(messages)
        # Should return the last non-empty message
        self.assertEqual(result, "Last message")

    def test_extract_response_text_list_with_mixed_types(self):
        """Test extracting text from list with mixed types."""
        obj = Mock()
        obj.text = "Object text"

        messages = [MockChatMessage("Chat message"), obj]
        result = self.manager._extract_response_text(messages)
        self.assertEqual(result, "Object text")

    def test_extract_response_text_empty_list(self):
        """Test extracting text from empty list."""
        result = self.manager._extract_response_text([])
        self.assertEqual(result, "")

    def test_extract_response_text_list_with_empty_items(self):
        """Test extracting text from list where all items have empty text."""
        messages = [MockChatMessage(""), MockChatMessage("")]
        result = self.manager._extract_response_text(messages)
        self.assertEqual(result, "")

    def test_extract_response_text_unknown_type(self):
        """Test extracting text from unknown type returns empty string."""
        # Create object without text attribute
        obj = Mock(spec=[])
        result = self.manager._extract_response_text(obj)
        self.assertEqual(result, "")

    def test_extract_response_text_nested_list(self):
        """Test extracting text handles nested structures correctly."""
        # Test that recursive extraction works
        inner_list = [MockChatMessage("Inner message")]
        outer_list = [inner_list]
        result = self.manager._extract_response_text(outer_list)
        self.assertEqual(result, "Inner message")


class TestWorkflowOutputEventHandling(IsolatedAsyncioTestCase):
    """Test WorkflowOutputEvent handling with different data types."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset mocks — reset_mock() does NOT clear side_effect,
        # so we must do it explicitly to avoid cross-test pollution.
        orchestration_config.orchestrations.clear()
        orchestration_config.agent_wrappers.clear()
        orchestration_config.managers.clear()
        orchestration_config.get_current_orchestration.return_value = None
        connection_config.send_status_update_async.reset_mock()
        connection_config.send_status_update_async.side_effect = None
        streaming_agent_response_callback.reset_mock()
        streaming_agent_response_callback.side_effect = None

        self.orchestration_manager = OrchestrationManager()
        self.test_user_id = "test_user_123"
        self.test_session_id = "test_session_456"

    async def test_workflow_output_with_list_of_chat_messages(self):
        """Test WorkflowOutputEvent with list of ChatMessage objects."""
        mock_workflow = Mock()

        # Create list of ChatMessages
        messages = [
            MockChatMessage("First response"),
            MockChatMessage("Second response"),
            MockChatMessage("Final response"),
        ]
        output_event = MockWorkflowOutputEvent(messages)

        mock_workflow.run = AsyncGeneratorMock([output_event])
        mock_workflow.executors = {}

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test list output"
        input_task.context = ""

        # Should process without raising an exception
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        # Should have sent status update for final result
        connection_config.send_status_update_async.assert_called()

    async def test_workflow_output_with_mixed_list(self):
        """Test WorkflowOutputEvent with list containing non-ChatMessage items."""
        mock_workflow = Mock()

        # Create list with mixed types (ChatMessage and other objects)
        messages = [
            MockChatMessage("Chat message"),
            "plain string item",  # Not a ChatMessage
            123,  # Integer item
        ]
        output_event = MockWorkflowOutputEvent(messages)

        mock_workflow.run = AsyncGeneratorMock([output_event])
        mock_workflow.executors = {}

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test mixed list output"
        input_task.context = ""

        # Should handle mixed list without error
        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        connection_config.send_status_update_async.assert_called()

    async def test_workflow_output_with_object_with_text(self):
        """Test WorkflowOutputEvent with object that has text attribute."""
        mock_workflow = Mock()

        # Create object with text attribute
        obj_with_text = Mock(spec_set=["text"])
        obj_with_text.text = "Object response"
        output_event = MockWorkflowOutputEvent(obj_with_text)

        mock_workflow.run = AsyncGeneratorMock([output_event])
        mock_workflow.executors = {}

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test object output"
        input_task.context = ""

        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        connection_config.send_status_update_async.assert_called()

    async def test_workflow_output_with_unknown_type(self):
        """Test WorkflowOutputEvent with unknown data type."""
        mock_workflow = Mock()

        # Create object without text attribute that will be str() converted
        output_event = MockWorkflowOutputEvent(12345)

        mock_workflow.run = AsyncGeneratorMock([output_event])
        mock_workflow.executors = {}

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test unknown type output"
        input_task.context = ""

        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        connection_config.send_status_update_async.assert_called()

    async def test_workflow_output_with_empty_list(self):
        """Test WorkflowOutputEvent with empty list."""
        mock_workflow = Mock()

        output_event = MockWorkflowOutputEvent([])

        mock_workflow.run = AsyncGeneratorMock([output_event])
        mock_workflow.executors = {}

        orchestration_config.get_current_orchestration.return_value = mock_workflow

        input_task = Mock()
        input_task.description = "Test empty list output"
        input_task.context = ""

        await self.orchestration_manager.run_orchestration(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            input_task=input_task,
        )

        # Empty list should still result in a status update being sent
        connection_config.send_status_update_async.assert_called()


if __name__ == "__main__":
    main()


# ── etapas de sequential: posición + paso propio ─────────────────────────────


def test_a_stage_receives_its_predecessor_output_and_its_own_step():
    from agent_framework import Message

    from v4.orchestration.orchestration_manager import _stage_context

    full = [
        Message(role="user", text="Auditar ruff"),
        Message(
            role="assistant",
            text="src/backend y src/mcp_server tienen pyproject",
            author_name="SrcAgent",
        ),
    ]
    out = _stage_context("SrcAgent", "correr ruff en cada uno")(full)
    assert [m.text for m in out] == [
        "src/backend y src/mcp_server tienen pyproject",
        "correr ruff en cada uno",
    ]
    assert str(getattr(out[-1].role, "value", out[-1].role)) == "user"
    # Sin paso equivale a last_agent; sin firma del predecesor, la última
    # respuesta del asistente.
    assert [m.text for m in _stage_context("SrcAgent", "")(full)] == [
        "src/backend y src/mcp_server tienen pyproject"
    ]
    unsigned = [
        Message(role="user", text="t"),
        Message(role="assistant", text="r1"),
        Message(role="assistant", text="r2"),
    ]
    assert [m.text for m in _stage_context("Otro", "paso")(unsigned)] == [
        "r1",
        "r2",
        "paso",
    ]


def test_a_stage_receives_the_predecessor_text_not_its_files():
    # El archivo del predecesor ya llegó al usuario; como contenido assistant
    # el framework lo serializa como input_file y el API lo rechaza (400).
    from agent_framework import Content, Message

    from v4.orchestration.orchestration_manager import _stage_context

    full = [
        Message(role="user", text="Graficá"),
        Message(
            role="assistant",
            contents=[
                Content.from_text("Acá está: [g.png](sandbox:/mnt/data/g.png)"),
                Content.from_hosted_file(
                    "cfile_1",
                    name="g.png",
                    additional_properties={"container_id": "cntr_1"},
                ),
            ],
            author_name="ChartAgent",
        ),
    ]
    out = _stage_context("ChartAgent", "ahora la imagen")(full)
    assert [m.text for m in out] == [
        "Acá está: [g.png](sandbox:/mnt/data/g.png)",
        "ahora la imagen",
    ]
    assert [c.type for m in out for c in m.contents] == ["text", "text"]
    assert out[0].author_name == "ChartAgent"


def test_sequential_wraps_each_later_stage_with_its_own_context():
    from unittest.mock import patch

    from v4.orchestration.orchestration_manager import OrchestrationManager

    a = MockAgent(agent_name="SrcAgent", has_inner_agent=True)
    b = MockAgent(agent_name="RuffAgent", has_inner_agent=True)
    with patch("v4.orchestration.orchestration_manager.SequentialBuilder") as sb:
        sb.return_value.build.return_value = "wf"
        OrchestrationManager.build_pattern_workflow(
            "sequential", [a, b], steps={"RuffAgent": "correr ruff"}
        )
    executors = sb.call_args.kwargs["participants"]
    assert [e._context_mode for e in executors] == ["last_agent", "custom"]
    from agent_framework import Message

    out = executors[1]._context_filter(
        [Message(role="assistant", text="lista", author_name="SrcAgent")]
    )
    assert [m.text for m in out] == ["lista", "correr ruff"]
