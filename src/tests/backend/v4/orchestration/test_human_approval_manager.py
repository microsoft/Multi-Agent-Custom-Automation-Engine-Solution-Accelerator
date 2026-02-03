"""Unit tests for human_approval_manager module.

Comprehensive test cases covering HumanApprovalMagenticManager with proper mocking.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Optional
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, AsyncMock, patch

import pytest

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
sys.modules['azure.core'] = Mock()
sys.modules['azure.core.exceptions'] = Mock()
sys.modules['azure.identity'] = Mock()
sys.modules['azure.identity.aio'] = Mock()
sys.modules['azure.cosmos'] = Mock(CosmosClient=Mock)

# Mock agent_framework dependencies
class MockChatMessage:
    """Mock ChatMessage class."""
    def __init__(self, text="Mock message"):
        self.text = text
        self.role = "assistant"

class MockMagenticContext:
    """Mock MagenticContext class."""
    def __init__(self, task=None, round_count=0):
        self.task = task or MockChatMessage("Test task")
        self.round_count = round_count
        self.participant_descriptions = {
            "TestAgent1": "A test agent",
            "TestAgent2": "Another test agent"
        }

class MockStandardMagenticManager:
    """Mock StandardMagenticManager class."""
    def __init__(self, *args, **kwargs):
        self.task_ledger = None
        self.kwargs = kwargs
    
    async def plan(self, magentic_context):
        """Mock plan method."""
        self.task_ledger = Mock()
        self.task_ledger.plan = Mock()
        self.task_ledger.plan.text = "Test plan text"
        self.task_ledger.facts = Mock()
        self.task_ledger.facts.text = "Test facts"
        return MockChatMessage("Test plan")
    
    async def replan(self, magentic_context):
        """Mock replan method."""
        return MockChatMessage("Test replan")
    
    async def create_progress_ledger(self, magentic_context):
        """Mock create_progress_ledger method."""
        ledger = Mock()
        ledger.is_request_satisfied = Mock()
        ledger.is_request_satisfied.answer = False
        ledger.is_request_satisfied.reason = "In progress"
        ledger.is_in_loop = Mock()
        ledger.is_in_loop.answer = True
        ledger.is_in_loop.reason = "Continuing"
        ledger.is_progress_being_made = Mock()
        ledger.is_progress_being_made.answer = True
        ledger.is_progress_being_made.reason = "Making progress"
        ledger.next_speaker = Mock()
        ledger.next_speaker.answer = "TestAgent1"
        ledger.next_speaker.reason = "Agent turn"
        ledger.instruction_or_question = Mock()
        ledger.instruction_or_question.answer = "Continue with task"
        ledger.instruction_or_question.reason = "Next step"
        return ledger
    
    async def prepare_final_answer(self, magentic_context):
        """Mock prepare_final_answer method."""
        return MockChatMessage("Final answer")

# Mock constants from agent_framework
ORCHESTRATOR_FINAL_ANSWER_PROMPT = "Final answer prompt"
ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT = "Task ledger plan prompt"
ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT = "Task ledger plan update prompt"

sys.modules['agent_framework'] = Mock(
    ChatMessage=MockChatMessage
)
sys.modules['agent_framework._workflows'] = Mock()
sys.modules['agent_framework._workflows._magentic'] = Mock(
    MagenticContext=MockMagenticContext,
    StandardMagenticManager=MockStandardMagenticManager,
    ORCHESTRATOR_FINAL_ANSWER_PROMPT=ORCHESTRATOR_FINAL_ANSWER_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT=ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT,
    ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT=ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT,
)

# Mock v4.models.messages
class MockWebsocketMessageType:
    """Mock WebsocketMessageType."""
    PLAN_APPROVAL_REQUEST = "plan_approval_request"
    PLAN_APPROVAL_RESPONSE = "plan_approval_response"
    FINAL_RESULT_MESSAGE = "final_result_message"
    TIMEOUT_NOTIFICATION = "timeout_notification"

class MockPlanApprovalRequest:
    """Mock PlanApprovalRequest."""
    def __init__(self, plan=None, status="PENDING_APPROVAL", context=None):
        self.plan = plan
        self.status = status
        self.context = context or {}

class MockPlanApprovalResponse:
    """Mock PlanApprovalResponse."""
    def __init__(self, approved=True, m_plan_id=None):
        self.approved = approved
        self.m_plan_id = m_plan_id

class MockFinalResultMessage:
    """Mock FinalResultMessage."""
    def __init__(self, content="", status="completed", summary=""):
        self.content = content
        self.status = status
        self.summary = summary

class MockTimeoutNotification:
    """Mock TimeoutNotification."""
    def __init__(self, timeout_type="approval", request_id=None, message="", timestamp=0, timeout_duration=30):
        self.timeout_type = timeout_type
        self.request_id = request_id
        self.message = message
        self.timestamp = timestamp
        self.timeout_duration = timeout_duration

sys.modules['v4'] = Mock()
sys.modules['v4.models'] = Mock()
sys.modules['v4.models.messages'] = Mock(
    WebsocketMessageType=MockWebsocketMessageType,
    PlanApprovalRequest=MockPlanApprovalRequest,
    PlanApprovalResponse=MockPlanApprovalResponse,  # This should use our custom class
    FinalResultMessage=MockFinalResultMessage,
    TimeoutNotification=MockTimeoutNotification,
)

# Mock v4.config.settings
mock_connection_config = Mock()
mock_connection_config.send_status_update_async = AsyncMock()

mock_orchestration_config = Mock()
mock_orchestration_config.max_rounds = 10
mock_orchestration_config.default_timeout = 30
mock_orchestration_config.plans = {}
mock_orchestration_config.approvals = {}
mock_orchestration_config.set_approval_pending = Mock()
mock_orchestration_config.wait_for_approval = AsyncMock(return_value=True)
mock_orchestration_config.cleanup_approval = Mock()

sys.modules['v4.config'] = Mock()
sys.modules['v4.config.settings'] = Mock(
    connection_config=mock_connection_config,
    orchestration_config=mock_orchestration_config
)

# Mock v4.models.models
class MockMPlan:
    """Mock MPlan."""
    def __init__(self):
        self.id = "test-plan-id"
        self.user_id = None

sys.modules['v4.models.models'] = Mock(MPlan=MockMPlan)

# Mock v4.orchestration.helper.plan_to_mplan_converter
class MockPlanToMPlanConverter:
    """Mock PlanToMPlanConverter."""
    @staticmethod
    def convert(plan_text, facts, team, task):
        plan = MockMPlan()
        return plan

sys.modules['v4.orchestration'] = Mock()
sys.modules['v4.orchestration.helper'] = Mock()
sys.modules['v4.orchestration.helper.plan_to_mplan_converter'] = Mock(
    PlanToMPlanConverter=MockPlanToMPlanConverter
)

# Now import the module under test
from backend.v4.orchestration.human_approval_manager import HumanApprovalMagenticManager

# Get mocked references for tests
connection_config = sys.modules['v4.config.settings'].connection_config
orchestration_config = sys.modules['v4.config.settings'].orchestration_config
messages = sys.modules['v4.models.messages']


class TestHumanApprovalMagenticManager(IsolatedAsyncioTestCase):
    """Test cases for HumanApprovalMagenticManager class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Reset mocks
        connection_config.send_status_update_async.reset_mock()
        connection_config.send_status_update_async.side_effect = None  # Reset side effects
        orchestration_config.plans.clear()
        orchestration_config.approvals.clear()
        orchestration_config.set_approval_pending.reset_mock()
        orchestration_config.wait_for_approval.reset_mock()
        orchestration_config.wait_for_approval.return_value = True  # Default return value
        orchestration_config.cleanup_approval.reset_mock()
        
        # Create test instance
        self.user_id = "test_user_123"
        self.manager = HumanApprovalMagenticManager(
            user_id=self.user_id,
            chat_client=Mock(),
            instructions="Test instructions"
        )
        self.test_context = MockMagenticContext()

    def test_init(self):
        """Test HumanApprovalMagenticManager initialization."""
        # Test basic initialization
        manager = HumanApprovalMagenticManager(
            user_id="test_user",
            chat_client=Mock(),
            instructions="Test instructions"
        )
        
        self.assertEqual(manager.current_user_id, "test_user")
        self.assertTrue(manager.approval_enabled)
        self.assertIsNone(manager.magentic_plan)
        
        # Verify parent was called with modified prompts
        self.assertIsNotNone(manager.kwargs)

    def test_init_with_additional_kwargs(self):
        """Test initialization with additional keyword arguments."""
        additional_kwargs = {
            "max_round_count": 5,
            "temperature": 0.7,
            "custom_param": "test_value"
        }
        
        manager = HumanApprovalMagenticManager(
            user_id="test_user",
            chat_client=Mock(),
            **additional_kwargs
        )
        
        self.assertEqual(manager.current_user_id, "test_user")
        # Verify kwargs were passed through
        self.assertIn("max_round_count", manager.kwargs)
        self.assertIn("temperature", manager.kwargs)
        self.assertIn("custom_param", manager.kwargs)

    async def test_plan_success_approved(self):
        """Test successful plan creation and approval."""
        # Reset any side effects first
        connection_config.send_status_update_async.side_effect = None
        
        # Setup
        orchestration_config.wait_for_approval.return_value = True
        
        # Execute
        result = await self.manager.plan(self.test_context)
        
        # Verify
        self.assertIsInstance(result, MockChatMessage)
        self.assertEqual(result.text, "Test plan")
        
        # Verify plan was created and stored
        self.assertIsNotNone(self.manager.magentic_plan)
        self.assertEqual(self.manager.magentic_plan.user_id, self.user_id)
        
        # Verify approval request was sent
        connection_config.send_status_update_async.assert_called()
        orchestration_config.set_approval_pending.assert_called()
        orchestration_config.wait_for_approval.assert_called()

    async def test_plan_success_rejected(self):
        """Test plan creation with user rejection."""
        # Reset any side effects first
        connection_config.send_status_update_async.side_effect = None
        
        # Setup - explicitly mock the wait_for_user_approval to return rejection
        with patch.object(self.manager, '_wait_for_user_approval') as mock_wait:
            mock_response = MockPlanApprovalResponse(approved=False, m_plan_id="test-plan-123")
            mock_wait.return_value = mock_response
            
            # Execute & Verify
            with self.assertRaises(Exception) as context:
                await self.manager.plan(self.test_context)
            
            self.assertIn("Plan execution cancelled by user", str(context.exception))
            
            # Verify the mocked _wait_for_user_approval was called
            mock_wait.assert_called_once()

    async def test_plan_task_ledger_none(self):
        """Test plan method when task_ledger is None."""
        # Setup - simulate task_ledger being None after super().plan()
        with patch.object(self.manager, 'plan', wraps=self.manager.plan):
            with patch('backend.v4.orchestration.human_approval_manager.StandardMagenticManager.plan') as mock_super_plan:
                mock_super_plan.return_value = MockChatMessage("Test plan")
                # Don't set task_ledger to simulate the error condition
                self.manager.task_ledger = None
                
                with self.assertRaises(RuntimeError) as context:
                    await self.manager.plan(self.test_context)
                
                self.assertIn("task_ledger not set after plan()", str(context.exception))

    async def test_plan_approval_storage_error(self):
        """Test plan method when storing in orchestration_config.plans fails."""
        # Reset any side effects first
        connection_config.send_status_update_async.side_effect = None
        
        # Setup - mock plans dict to raise exception
        original_plans = orchestration_config.plans
        orchestration_config.plans = Mock()
        orchestration_config.plans.__setitem__ = Mock(side_effect=Exception("Storage error"))
        
        try:
            # Execute & Verify - should still work despite storage error
            orchestration_config.wait_for_approval.return_value = True
            result = await self.manager.plan(self.test_context)
            
            self.assertIsInstance(result, MockChatMessage)
        finally:
            # Reset the plans
            orchestration_config.plans = original_plans

    async def test_plan_websocket_send_error(self):
        """Test plan method when WebSocket sending fails."""
        # Setup
        connection_config.send_status_update_async.side_effect = Exception("WebSocket error")
        
        # Execute & Verify - should still try to wait for approval
        with self.assertRaises(Exception):
            await self.manager.plan(self.test_context)
        
        # Reset side effect
        connection_config.send_status_update_async.side_effect = None

    async def test_replan(self):
        """Test replan method."""
        result = await self.manager.replan(self.test_context)
        
        self.assertIsInstance(result, MockChatMessage)
        self.assertEqual(result.text, "Test replan")

    async def test_create_progress_ledger_normal(self):
        """Test create_progress_ledger with normal round count."""
        # Setup
        context = MockMagenticContext(round_count=5)
        
        # Execute
        ledger = await self.manager.create_progress_ledger(context)
        
        # Verify
        self.assertIsNotNone(ledger)
        self.assertFalse(ledger.is_request_satisfied.answer)
        self.assertTrue(ledger.is_in_loop.answer)

    async def test_create_progress_ledger_max_rounds_exceeded(self):
        """Test create_progress_ledger when max rounds exceeded."""
        # Setup
        context = MockMagenticContext(round_count=15)  # Exceeds max_rounds=10
        
        # Execute
        ledger = await self.manager.create_progress_ledger(context)
        
        # Verify termination conditions
        self.assertTrue(ledger.is_request_satisfied.answer)
        self.assertEqual(ledger.is_request_satisfied.reason, "Maximum rounds exceeded")
        self.assertFalse(ledger.is_in_loop.answer)
        self.assertEqual(ledger.is_in_loop.reason, "Terminating")
        self.assertFalse(ledger.is_progress_being_made.answer)
        self.assertEqual(ledger.instruction_or_question.answer, "Process terminated due to maximum rounds exceeded")
        
        # Verify final message was sent
        connection_config.send_status_update_async.assert_called()

    async def test_wait_for_user_approval_success(self):
        """Test _wait_for_user_approval with successful approval."""
        # Setup
        plan_id = "test-plan-123"
        
        # Patch the PlanApprovalResponse directly
        with patch('backend.v4.orchestration.human_approval_manager.messages.PlanApprovalResponse', MockPlanApprovalResponse):
            orchestration_config.wait_for_approval = AsyncMock(return_value=True)
            
            # Execute
            result = await self.manager._wait_for_user_approval(plan_id)
            
            # Verify
            self.assertIsNotNone(result)
            self.assertTrue(result.approved)
            self.assertEqual(result.m_plan_id, plan_id)
        
        orchestration_config.set_approval_pending.assert_called_with(plan_id)
        orchestration_config.wait_for_approval.assert_called_with(plan_id)

    async def test_wait_for_user_approval_rejection(self):
        """Test _wait_for_user_approval with user rejection."""
        # Setup
        plan_id = "test-plan-123"
        
        # Patch the PlanApprovalResponse directly
        with patch('backend.v4.orchestration.human_approval_manager.messages.PlanApprovalResponse', MockPlanApprovalResponse):
            orchestration_config.wait_for_approval = AsyncMock(return_value=False)
            
            # Execute
            result = await self.manager._wait_for_user_approval(plan_id)
            
            # Verify
            self.assertIsNotNone(result)
            self.assertFalse(result.approved)
            self.assertEqual(result.m_plan_id, plan_id)

    async def test_wait_for_user_approval_no_plan_id(self):
        """Test _wait_for_user_approval with no plan ID."""
        # Patch the PlanApprovalResponse directly
        with patch('backend.v4.orchestration.human_approval_manager.messages.PlanApprovalResponse', MockPlanApprovalResponse):
            result = await self.manager._wait_for_user_approval(None)

            self.assertIsNotNone(result)
            self.assertFalse(result.approved)
            self.assertIsNone(result.m_plan_id)
        self.assertIsNone(result.m_plan_id)

    async def test_wait_for_user_approval_timeout(self):
        """Test _wait_for_user_approval with timeout."""
        # Setup
        plan_id = "test-plan-123"
        orchestration_config.wait_for_approval.side_effect = asyncio.TimeoutError()
        
        # Execute
        result = await self.manager._wait_for_user_approval(plan_id)
        
        # Verify
        self.assertIsNone(result)
        
        # Verify timeout notification was sent
        connection_config.send_status_update_async.assert_called()
        orchestration_config.cleanup_approval.assert_called_with(plan_id)

    async def test_wait_for_user_approval_timeout_websocket_error(self):
        """Test _wait_for_user_approval with timeout and WebSocket error."""
        # Setup
        plan_id = "test-plan-123"
        orchestration_config.wait_for_approval.side_effect = asyncio.TimeoutError()
        connection_config.send_status_update_async.side_effect = Exception("WebSocket error")
        
        # Execute
        result = await self.manager._wait_for_user_approval(plan_id)
        
        # Verify
        self.assertIsNone(result)
        orchestration_config.cleanup_approval.assert_called_with(plan_id)
        
        # Reset side effect
        connection_config.send_status_update_async.side_effect = None

    async def test_wait_for_user_approval_key_error(self):
        """Test _wait_for_user_approval with KeyError."""
        # Setup
        plan_id = "test-plan-123"
        orchestration_config.wait_for_approval.side_effect = KeyError("Plan not found")
        
        # Execute
        result = await self.manager._wait_for_user_approval(plan_id)
        
        # Verify
        self.assertIsNone(result)

    async def test_wait_for_user_approval_cancelled_error(self):
        """Test _wait_for_user_approval with CancelledError."""
        # Setup
        plan_id = "test-plan-123"
        orchestration_config.wait_for_approval.side_effect = asyncio.CancelledError()
        
        # Execute
        result = await self.manager._wait_for_user_approval(plan_id)
        
        # Verify
        self.assertIsNone(result)
        orchestration_config.cleanup_approval.assert_called_with(plan_id)

    async def test_wait_for_user_approval_unexpected_error(self):
        """Test _wait_for_user_approval with unexpected error."""
        # Setup
        plan_id = "test-plan-123"
        orchestration_config.wait_for_approval.side_effect = Exception("Unexpected error")
        
        # Execute
        result = await self.manager._wait_for_user_approval(plan_id)
        
        # Verify
        self.assertIsNone(result)
        orchestration_config.cleanup_approval.assert_called_with(plan_id)

    async def test_wait_for_user_approval_finally_cleanup(self):
        """Test _wait_for_user_approval finally block cleanup."""
        # Setup
        plan_id = "test-plan-123"
        orchestration_config.approvals = {plan_id: None}
        
        # Patch the PlanApprovalResponse directly
        with patch('backend.v4.orchestration.human_approval_manager.messages.PlanApprovalResponse', MockPlanApprovalResponse):
            orchestration_config.wait_for_approval = AsyncMock(return_value=True)
            
            # Execute
            result = await self.manager._wait_for_user_approval(plan_id)
            
            # Verify
            self.assertIsNotNone(result)
            self.assertTrue(result.approved)
            self.assertEqual(result.m_plan_id, plan_id)
        self.assertTrue(result.approved)

    async def test_prepare_final_answer(self):
        """Test prepare_final_answer method."""
        result = await self.manager.prepare_final_answer(self.test_context)
        
        self.assertIsInstance(result, MockChatMessage)
        self.assertEqual(result.text, "Final answer")

    def test_plan_to_obj_success(self):
        """Test plan_to_obj with valid ledger."""
        # Setup
        ledger = Mock()
        ledger.plan = Mock()
        ledger.plan.text = "Test plan text"
        ledger.facts = Mock()
        ledger.facts.text = "Test facts text"
        
        # Execute
        result = self.manager.plan_to_obj(self.test_context, ledger)
        
        # Verify
        self.assertIsInstance(result, MockMPlan)

    def test_plan_to_obj_invalid_ledger_none(self):
        """Test plan_to_obj with None ledger."""
        with self.assertRaises(ValueError) as context:
            self.manager.plan_to_obj(self.test_context, None)
        
        self.assertIn("Invalid ledger structure", str(context.exception))

    def test_plan_to_obj_invalid_ledger_no_plan(self):
        """Test plan_to_obj with ledger missing plan attribute."""
        ledger = Mock()
        del ledger.plan  # Remove plan attribute
        ledger.facts = Mock()
        
        with self.assertRaises(ValueError) as context:
            self.manager.plan_to_obj(self.test_context, ledger)
        
        self.assertIn("Invalid ledger structure", str(context.exception))

    def test_plan_to_obj_invalid_ledger_no_facts(self):
        """Test plan_to_obj with ledger missing facts attribute."""
        ledger = Mock()
        ledger.plan = Mock()
        del ledger.facts  # Remove facts attribute
        
        with self.assertRaises(ValueError) as context:
            self.manager.plan_to_obj(self.test_context, ledger)
        
        self.assertIn("Invalid ledger structure", str(context.exception))

    def test_plan_to_obj_with_string_task(self):
        """Test plan_to_obj with string task instead of ChatMessage."""
        # Setup
        context = MockMagenticContext(task="String task")
        ledger = Mock()
        ledger.plan = Mock()
        ledger.plan.text = "Test plan text"
        ledger.facts = Mock()
        ledger.facts.text = "Test facts text"
        
        # Execute
        result = self.manager.plan_to_obj(context, ledger)
        
        # Verify
        self.assertIsInstance(result, MockMPlan)

    async def test_plan_context_without_participant_descriptions(self):
        """Test plan method with context missing participant_descriptions."""
        # Setup
        context = MockMagenticContext()
        del context.participant_descriptions  # Remove the attribute
        
        # Mock the plan_to_obj method to handle missing attribute gracefully
        with patch.object(self.manager, 'plan_to_obj') as mock_plan_to_obj:
            mock_plan = MockMPlan()
            mock_plan.id = "test-plan-id"
            mock_plan_to_obj.return_value = mock_plan
            
            orchestration_config.wait_for_approval.return_value = True

            # Execute - should handle missing participant_descriptions
            result = await self.manager.plan(context)
            
            # Verify the plan_to_obj was called (showing it got past the participant_descriptions check)
            mock_plan_to_obj.assert_called_once()
            self.assertIsInstance(result, MockChatMessage)

    async def test_plan_with_chat_message_task(self):
        """Test plan method with ChatMessage task."""
        # Setup
        task = MockChatMessage("Test task from ChatMessage")
        context = MockMagenticContext(task=task)
        orchestration_config.wait_for_approval.return_value = True
        
        # Execute
        result = await self.manager.plan(context)
        
        # Verify
        self.assertIsInstance(result, MockChatMessage)

    def test_approval_enabled_default(self):
        """Test that approval_enabled is True by default."""
        manager = HumanApprovalMagenticManager(
            user_id="test_user",
            chat_client=Mock()
        )
        
        self.assertTrue(manager.approval_enabled)

    def test_magentic_plan_default(self):
        """Test that magentic_plan is None by default."""
        manager = HumanApprovalMagenticManager(
            user_id="test_user",
            chat_client=Mock()
        )
        
        self.assertIsNone(manager.magentic_plan)

    async def test_replan_with_none_message(self):
        """Test replan method when super().replan returns None."""
        with patch('backend.v4.orchestration.human_approval_manager.StandardMagenticManager.replan', return_value=None):
            result = await self.manager.replan(self.test_context)
            # Should handle None gracefully
            self.assertIsNone(result)

    async def test_create_progress_ledger_websocket_error(self):
        """Test create_progress_ledger when WebSocket sending fails for max rounds."""
        # Setup
        context = MockMagenticContext(round_count=15)  # Exceeds max_rounds=10
        
        # Mock websocket failure
        connection_config.send_status_update_async.side_effect = Exception("WebSocket error")
        
        # Execute - should handle the error gracefully but still raise it
        with self.assertRaises(Exception) as cm:
            await self.manager.create_progress_ledger(context)
        
        # Verify the exception message
        self.assertEqual(str(cm.exception), "WebSocket error")
        
        # Reset side effect for other tests
        connection_config.send_status_update_async.side_effect = None


if __name__ == '__main__':
    import unittest
    unittest.main()