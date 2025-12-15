"""
Unit tests for v4 HumanApprovalMagenticManager.

Tests cover:
- HumanApprovalMagenticManager initialization
- plan method with approval workflow
- replan method
- create_progress_ledger (normal and max rounds exceeded)
- _wait_for_user_approval (success, timeout, cancellation, errors)
- prepare_final_answer method
- plan_to_obj conversion
- Error handling and edge cases
"""

import asyncio
import pytest
import re
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
import sys
from pathlib import Path
from typing import Optional, Any

# Add the backend path to sys.path for imports
backend_path = Path(__file__).parent.parent.parent.parent.parent.parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

# Create mock agent_framework classes
class MockChatMessage:
    def __init__(self, role=None, content=None, contents=None, text=None, **kwargs):
        self.role = role
        self.content = content or contents or text or ""
        self.contents = contents or []
        self.text = text or content or ""

class MockRole:
    USER = "user"
    ASSISTANT = "assistant"

class MockTextContent:
    def __init__(self, text=None, **kwargs):
        self.text = text or ""

class MockMagenticContext:
    def __init__(self, task=None, participant_descriptions=None, **kwargs):
        self.task = task
        self.participant_descriptions = participant_descriptions or []
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockStandardMagenticManager:
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.task_ledger = None
    
    async def plan(self, context):
        return MockChatMessage(text="Plan text", role="assistant")
    
    async def replan(self, context):
        return MockChatMessage(text="Replan text", role="assistant")
    
    async def create_progress_ledger(self, context):
        return MockChatMessage(text="Progress ledger", role="assistant")
    
    async def prepare_final_answer(self, context):
        return MockChatMessage(text="Final answer", role="assistant")
    
    def plan_to_obj(self, context, ledger):
        return MPlan(id="plan-123")

# Use mocks instead of importing from agent_framework
ChatMessage = MockChatMessage
Role = MockRole
TextContent = MockTextContent
MagenticContext = MockMagenticContext
StandardMagenticManager = MockStandardMagenticManager

# Load human_approval_manager.py using exec() to avoid v4 import issues
manager_file = backend_path / "v4" / "orchestration" / "human_approval_manager.py"
with open(manager_file, "r", encoding="utf-8") as f:
    manager_code = f.read()

# Replace v4 imports to avoid ModuleNotFoundError
manager_code = manager_code.replace("import v4.models.messages as messages", "# import v4.models.messages as messages")
manager_code = manager_code.replace("from v4.config.settings import connection_config, orchestration_config", "# from v4.config.settings import connection_config, orchestration_config")
manager_code = manager_code.replace("from v4.models.models import MPlan", "# from v4.models.models import MPlan")
manager_code = manager_code.replace("from v4.orchestration.helper.plan_to_mplan_converter import PlanToMPlanConverter", "# from v4.orchestration.helper.plan_to_mplan_converter import PlanToMPlanConverter")
manager_code = manager_code.replace("from agent_framework import ChatMessage", "# from agent_framework import ChatMessage")
manager_code = re.sub(
    r'from agent_framework\._workflows\._magentic import \([^)]+\)',
    '# from agent_framework._workflows._magentic import (...)',
    manager_code,
    flags=re.DOTALL
)

# Create mock classes for dependencies
class MockConnectionConfig:
    def send_status_update_async(self, *args, **kwargs):
        pass

class MockOrchestrationConfig:
    default_timeout = 300
    max_rounds = 10
    plans = {}
    approvals = {}
    
    def set_plan_pending(self, plan_id):
        pass
    
    def set_approval_pending(self, plan_id):
        pass
    
    def wait_for_plan_approval(self, plan_id):
        pass
    
    def wait_for_approval(self, plan_id):
        pass
    
    def cleanup_plan(self, plan_id):
        pass
    
    def cleanup_approval(self, plan_id):
        pass

class MPlan:
    def __init__(self, id=None, user_id=None, **kwargs):
        self.id = id or "plan-123"
        self.user_id = user_id
        for k, v in kwargs.items():
            setattr(self, k, v)

class PlanApprovalRequest:
    def __init__(self, plan=None, status=None, context=None, **kwargs):
        self.plan = plan
        self.status = status
        self.context = context

class PlanApprovalResponse:
    def __init__(self, plan_id=None, m_plan_id=None, approved=None, feedback=None, **kwargs):
        self.plan_id = plan_id or m_plan_id
        self.m_plan_id = m_plan_id or plan_id
        self.approved = approved
        self.feedback = feedback

class TimeoutNotification:
    def __init__(self, plan_id=None, message=None, timeout_type=None, **kwargs):
        self.plan_id = plan_id
        self.message = message
        self.timeout_type = timeout_type

class WebsocketMessageType:
    PLAN_APPROVAL_REQUEST = "plan_approval_request"
    PLAN_APPROVAL_RESPONSE = "plan_approval_response"
    TIMEOUT_NOTIFICATION = "timeout_notification"
    FINAL_RESULT = "final_result"
    FINAL_RESULT_MESSAGE = "final_result"

class FinalResultMessage:
    def __init__(self, result=None, user_id=None, **kwargs):
        self.result = result
        self.user_id = user_id

class PlanToMPlanConverter:
    @staticmethod
    def convert(magentic_context, task_ledger):
        return MPlan(id="plan-123")

# Create mock messages module
class MockMessages:
    PlanApprovalRequest = PlanApprovalRequest
    PlanApprovalResponse = PlanApprovalResponse
    TimeoutNotification = TimeoutNotification
    WebsocketMessageType = WebsocketMessageType
    FinalResultMessage = FinalResultMessage

mock_connection_config = MockConnectionConfig()
mock_orchestration_config = MockOrchestrationConfig()

# Create namespace with mocks
manager_namespace = {
    'messages': MockMessages(),
    'connection_config': mock_connection_config,
    'orchestration_config': mock_orchestration_config,
    'MPlan': MPlan,
    'PlanToMPlanConverter': PlanToMPlanConverter,
    'ChatMessage': ChatMessage,
    'MagenticContext': MagenticContext,
    'StandardMagenticManager': StandardMagenticManager,
    'ORCHESTRATOR_FINAL_ANSWER_PROMPT': "",
    'ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT': "",
    'ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT': "",
    'logging': __import__('logging'),
    'asyncio': asyncio,
    'Any': Any,
    'Optional': Optional,
}

exec(manager_code, manager_namespace)

# Extract class from namespace
HumanApprovalMagenticManager = manager_namespace['HumanApprovalMagenticManager']

# Make mocks available for tests
connection_config = mock_connection_config
orchestration_config = mock_orchestration_config
mock_orch_config = orchestration_config
mock_conn_config = connection_config


class TestHumanApprovalMagenticManagerInit:
    """Test cases for HumanApprovalMagenticManager initialization."""

    def test_init_with_user_id(self):
        """Test initialization with user_id."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        assert manager.current_user_id == "user123"
        assert manager.approval_enabled is True
        assert manager.magentic_plan is None

    def test_init_custom_prompts_appended(self):
        """Test initialization appends custom prompts."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        # Verify custom prompts were set (appended to base prompts)
        assert "Never ask the user for information" in manager.task_ledger_plan_prompt
        assert "DO NOT EVER OFFER TO HELP FURTHER" in manager.final_answer_prompt

    def test_init_with_additional_kwargs(self):
        """Test initialization passes through additional kwargs."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()],
            max_rounds=10
        )
        
        assert manager.current_user_id == "user123"


class TestPlanMethod:
    """Test cases for plan method."""

    @pytest.mark.asyncio
    async def test_plan_approved(self):
        """Test plan method with approved plan."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.plans = {}
        mock_orch_config.wait_for_approval = AsyncMock(return_value=True)
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        # Mock parent plan method
        mock_plan_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text="Plan: Step 1, Step 2")]
        )
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'plan',
            new_callable=AsyncMock,
            return_value=mock_plan_message
        ):
            # Mock task ledger
            mock_ledger = Mock()
            mock_ledger.plan.text = "Step 1\nStep 2"
            mock_ledger.facts.text = "Fact 1"
            manager.task_ledger = mock_ledger
            
            # Mock plan_to_obj
            mock_mplan = MPlan(
                id="plan-123",
                task="Test task",
                facts="Fact 1",
                team=["Agent1"],
                steps=[]
            )
            manager.plan_to_obj = Mock(return_value=mock_mplan)
            
            # Create mock context
            mock_context = Mock(spec=MagenticContext)
            mock_context.task = Mock()
            mock_context.task.text = "Test task"
            mock_context.participant_descriptions = {"Agent1": "Description"}
            
            result = await manager.plan(mock_context)
            
            assert result == mock_plan_message
            mock_conn_config.send_status_update_async.assert_called()
            mock_orch_config.wait_for_approval.assert_called_once_with("plan-123")

    @pytest.mark.asyncio
    async def test_plan_rejected(self):
        """Test plan method with rejected plan."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.plans = {}
        mock_orch_config.wait_for_approval = AsyncMock(return_value=False)
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_plan_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text="Plan: Step 1")]
        )
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'plan',
            new_callable=AsyncMock,
            return_value=mock_plan_message
        ):
            mock_ledger = Mock()
            mock_ledger.plan.text = "Step 1"
            mock_ledger.facts.text = "Fact 1"
            manager.task_ledger = mock_ledger
            
            mock_mplan = MPlan(
                id="plan-123",
                task="Test task",
                facts="Fact 1",
                team=["Agent1"],
                steps=[]
            )
            manager.plan_to_obj = Mock(return_value=mock_mplan)
            
            mock_context = Mock(spec=MagenticContext)
            mock_context.task = Mock()
            mock_context.task.text = "Test task"
            mock_context.participant_descriptions = {"Agent1": "Description"}
            
            with pytest.raises(Exception) as exc_info:
                await manager.plan(mock_context)
            
            assert "cancelled by user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_plan_no_task_ledger(self):
        """Test plan method raises error when task_ledger not set."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_plan_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text="Plan")]
        )
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'plan',
            new_callable=AsyncMock,
            return_value=mock_plan_message
        ):
            manager.task_ledger = None
            
            mock_context = Mock(spec=MagenticContext)
            mock_context.task = Mock()
            mock_context.task.text = "Test task"
            
            with pytest.raises(RuntimeError) as exc_info:
                await manager.plan(mock_context)
            
            assert "task_ledger not set" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_plan_stores_in_orchestration_config(self):
        """Test plan method stores plan in orchestration_config.plans."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.plans = {}
        mock_orch_config.wait_for_approval = AsyncMock(return_value=True)
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_plan_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text="Plan")]
        )
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'plan',
            new_callable=AsyncMock,
            return_value=mock_plan_message
        ):
            mock_ledger = Mock()
            mock_ledger.plan.text = "Step 1"
            mock_ledger.facts.text = "Fact 1"
            manager.task_ledger = mock_ledger
            
            mock_mplan = MPlan(
                id="plan-456",
                task="Test",
                facts="Fact 1",
                team=["Agent1"],
                steps=[]
            )
            manager.plan_to_obj = Mock(return_value=mock_mplan)
            
            mock_context = Mock(spec=MagenticContext)
            mock_context.task = Mock()
            mock_context.task.text = "Test"
            mock_context.participant_descriptions = {"Agent1": "Desc"}
            
            await manager.plan(mock_context)
            
            assert "plan-456" in mock_orch_config.plans
            assert mock_orch_config.plans["plan-456"] == mock_mplan


class TestReplanMethod:
    """Test cases for replan method."""

    @pytest.mark.asyncio
    async def test_replan_success(self):
        """Test replan method calls parent and returns message."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_replan_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text="Revised plan")]
        )
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'replan',
            new_callable=AsyncMock,
            return_value=mock_replan_message
        ) as mock_parent_replan:
            mock_context = Mock(spec=MagenticContext)
            
            result = await manager.replan(mock_context)
            
            assert result == mock_replan_message
            mock_parent_replan.assert_called_once_with(magentic_context=mock_context)


class TestCreateProgressLedger:
    """Test cases for create_progress_ledger method."""

    @pytest.mark.asyncio
    async def test_create_progress_ledger_max_rounds_exceeded(self):
        """Test create_progress_ledger when max rounds exceeded."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.max_rounds = 5
        mock_conn_config.send_status_update_async = AsyncMock()
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        # Mock parent method to return ledger
        mock_ledger = Mock()
        mock_ledger.is_request_satisfied = Mock()
        mock_ledger.is_in_loop = Mock()
        mock_ledger.is_progress_being_made = Mock()
        mock_ledger.next_speaker = Mock()
        mock_ledger.instruction_or_question = Mock()
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'create_progress_ledger',
            new_callable=AsyncMock,
            return_value=mock_ledger
        ):
            mock_context = Mock(spec=MagenticContext)
            mock_context.round_count = 6  # Exceeds max_rounds
            
            result = await manager.create_progress_ledger(mock_context)
            
            # Verify termination flags set
            assert result.is_request_satisfied.answer is True
            assert result.is_in_loop.answer is False
            assert result.is_progress_being_made.answer is False
            assert "Maximum rounds exceeded" in result.is_request_satisfied.reason
            
            # Verify final message sent
            mock_conn_config.send_status_update_async.assert_called_once()
            call_args = mock_conn_config.send_status_update_async.call_args
            assert isinstance(call_args[1]["message"], FinalResultMessage)
            assert call_args[1]["message_type"] == WebsocketMessageType.FINAL_RESULT_MESSAGE

    @pytest.mark.asyncio
    async def test_create_progress_ledger_normal(self):
        """Test create_progress_ledger under normal conditions."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.max_rounds = 10
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_ledger = Mock()
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'create_progress_ledger',
            new_callable=AsyncMock,
            return_value=mock_ledger
        ) as mock_parent_method:
            mock_context = Mock(spec=MagenticContext)
            mock_context.round_count = 3  # Under max_rounds
            
            result = await manager.create_progress_ledger(mock_context)
            
            assert result == mock_ledger
            mock_parent_method.assert_called_once_with(mock_context)


class TestWaitForUserApproval:
    """Test cases for _wait_for_user_approval method."""

    @pytest.mark.asyncio
    async def test_wait_for_approval_success(self):
        """Test successful approval wait."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.set_approval_pending = Mock()
        mock_orch_config.wait_for_approval = AsyncMock(return_value=True)
        mock_orch_config.approvals = {}
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        result = await manager._wait_for_user_approval("plan-123")
        
        assert isinstance(result, PlanApprovalResponse)
        assert result.approved is True
        assert result.m_plan_id == "plan-123"
        mock_orch_config.set_approval_pending.assert_called_once_with("plan-123")

    @pytest.mark.asyncio
    async def test_wait_for_approval_rejected(self):
        """Test rejected approval wait."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.set_approval_pending = Mock()
        mock_orch_config.wait_for_approval = AsyncMock(return_value=False)
        mock_orch_config.approvals = {}
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        result = await manager._wait_for_user_approval("plan-123")
        
        assert isinstance(result, PlanApprovalResponse)
        assert result.approved is False

    @pytest.mark.asyncio
    async def test_wait_for_approval_no_plan_id(self):
        """Test approval wait with no plan ID."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        result = await manager._wait_for_user_approval(None)
        
        assert isinstance(result, PlanApprovalResponse)
        assert result.approved is False

    @pytest.mark.asyncio
    async def test_wait_for_approval_timeout(self):
        """Test approval wait timeout."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.set_approval_pending = Mock()
        mock_orch_config.wait_for_approval = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_orch_config.cleanup_approval = Mock()
        mock_orch_config.approvals = {}
        mock_conn_config.send_status_update_async = AsyncMock()
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        result = await manager._wait_for_user_approval("plan-123")
        
        assert result is None
        mock_orch_config.cleanup_approval.assert_called_with("plan-123")
        
        # Verify timeout notification sent
        mock_conn_config.send_status_update_async.assert_called_once()
        call_args = mock_conn_config.send_status_update_async.call_args
        assert isinstance(call_args[1]["message"], TimeoutNotification)
        assert call_args[1]["message_type"] == WebsocketMessageType.TIMEOUT_NOTIFICATION

    @pytest.mark.asyncio
    async def test_wait_for_approval_cancelled(self):
        """Test approval wait cancellation."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.set_approval_pending = Mock()
        mock_orch_config.wait_for_approval = AsyncMock(side_effect=asyncio.CancelledError())
        mock_orch_config.cleanup_approval = Mock()
        mock_orch_config.approvals = {}
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        result = await manager._wait_for_user_approval("plan-123")
        
        assert result is None
        mock_orch_config.cleanup_approval.assert_called_with("plan-123")

    @pytest.mark.asyncio
    async def test_wait_for_approval_key_error(self):
        """Test approval wait with invalid plan ID."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.set_approval_pending = Mock()
        mock_orch_config.wait_for_approval = AsyncMock(side_effect=KeyError())
        mock_orch_config.approvals = {}
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        result = await manager._wait_for_user_approval("invalid-plan")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_approval_generic_error(self):
        """Test approval wait with generic error."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.set_approval_pending = Mock()
        mock_orch_config.wait_for_approval = AsyncMock(side_effect=Exception("Generic error"))
        mock_orch_config.cleanup_approval = Mock()
        mock_orch_config.approvals = {}
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        result = await manager._wait_for_user_approval("plan-123")
        
        assert result is None
        mock_orch_config.cleanup_approval.assert_called_with("plan-123")

    @pytest.mark.asyncio
    async def test_wait_for_approval_cleanup_safety_net(self):
        """Test approval wait cleanup safety net."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.set_approval_pending = Mock()
        mock_orch_config.wait_for_approval = AsyncMock(return_value=True)
        mock_orch_config.approvals = {"plan-123": None}
        mock_orch_config.cleanup_approval = Mock()
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        result = await manager._wait_for_user_approval("plan-123")
        
        # Safety net should cleanup pending approvals
        mock_orch_config.cleanup_approval.assert_called_with("plan-123")

    @pytest.mark.asyncio
    async def test_wait_for_approval_timeout_notification_error(self):
        """Test approval wait handles timeout notification send error."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.set_approval_pending = Mock()
        mock_orch_config.wait_for_approval = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_orch_config.cleanup_approval = Mock()
        mock_orch_config.approvals = {}
        mock_conn_config.send_status_update_async = AsyncMock(side_effect=Exception("Send error"))
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        # Should not raise exception
        result = await manager._wait_for_user_approval("plan-123")
        
        assert result is None
        mock_orch_config.cleanup_approval.assert_called_with("plan-123")


class TestPrepareFinalAnswer:
    """Test cases for prepare_final_answer method."""

    @pytest.mark.asyncio
    async def test_prepare_final_answer(self):
        """Test prepare_final_answer calls parent method."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_final_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text="Final answer")]
        )
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'prepare_final_answer',
            new_callable=AsyncMock,
            return_value=mock_final_message
        ) as mock_parent_method:
            mock_context = Mock(spec=MagenticContext)
            
            result = await manager.prepare_final_answer(mock_context)
            
            assert result == mock_final_message
            mock_parent_method.assert_called_once_with(mock_context)


class TestPlanToObj:
    """Test cases for plan_to_obj method."""

    def test_plan_to_obj_success(self):
        """Test plan_to_obj converts ledger to MPlan."""
        mock_orch_config.default_timeout = 300
        
        mock_mplan = MPlan(
            id="plan-123",
            task="Test task",
            facts="Fact 1",
            team=["Agent1"],
            steps=[]
        )
        
        # Mock PlanToMPlanConverter.convert
        with patch.object(PlanToMPlanConverter, 'convert', return_value=mock_mplan):
            manager = HumanApprovalMagenticManager(
                user_id="user123",
                orchestrator=Mock(),
                participants=[Mock()]
            )
            
            mock_ledger = Mock()
            mock_ledger.plan.text = "Step 1\nStep 2"
            mock_ledger.facts.text = "Fact 1\nFact 2"
            
            mock_context = Mock(spec=MagenticContext)
            mock_context.task = Mock()
            mock_context.task.text = "Test task"
            mock_context.participant_descriptions = {"Agent1": "Description"}
            
            result = manager.plan_to_obj(mock_context, mock_ledger)
            
            assert result == mock_mplan
            PlanToMPlanConverter.convert.assert_called_once_with(
                plan_text="Step 1\nStep 2",
                facts="Fact 1\nFact 2",
                team=["Agent1"],
                task="Test task"
            )

    def test_plan_to_obj_none_ledger(self):
        """Test plan_to_obj raises error with None ledger."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_context = Mock(spec=MagenticContext)
        
        with pytest.raises(ValueError) as exc_info:
            manager.plan_to_obj(mock_context, None)
        
        assert "Invalid ledger structure" in str(exc_info.value)

    def test_plan_to_obj_missing_plan_attribute(self):
        """Test plan_to_obj raises error when ledger missing plan attribute."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_ledger = Mock()
        del mock_ledger.plan  # Remove plan attribute
        
        mock_context = Mock(spec=MagenticContext)
        
        with pytest.raises(ValueError) as exc_info:
            manager.plan_to_obj(mock_context, mock_ledger)
        
        assert "Invalid ledger structure" in str(exc_info.value)

    def test_plan_to_obj_missing_facts_attribute(self):
        """Test plan_to_obj raises error when ledger missing facts attribute."""
        mock_orch_config.default_timeout = 300
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_ledger = Mock()
        mock_ledger.plan = Mock()
        del mock_ledger.facts  # Remove facts attribute
        
        mock_context = Mock(spec=MagenticContext)
        
        with pytest.raises(ValueError) as exc_info:
            manager.plan_to_obj(mock_context, mock_ledger)
        
        assert "Invalid ledger structure" in str(exc_info.value)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_plan_with_string_task(self):
        """Test plan method with string task instead of object."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.plans = {}
        mock_orch_config.wait_for_approval = AsyncMock(return_value=True)
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_plan_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text="Plan")]
        )
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'plan',
            new_callable=AsyncMock,
            return_value=mock_plan_message
        ):
            mock_ledger = Mock()
            mock_ledger.plan.text = "Step 1"
            mock_ledger.facts.text = "Fact 1"
            manager.task_ledger = mock_ledger
            
            mock_mplan = MPlan(
                id="plan-789",
                task="String task",
                facts="Fact 1",
                team=["Agent1"],
                steps=[]
            )
            manager.plan_to_obj = Mock(return_value=mock_mplan)
            
            # Task is just a string
            mock_context = Mock(spec=MagenticContext)
            mock_context.task = "String task"
            mock_context.participant_descriptions = {"Agent1": "Desc"}
            
            result = await manager.plan(mock_context)
            
            assert result == mock_plan_message

    @pytest.mark.asyncio
    async def test_plan_exception_storing_plan(self):
        """Test plan method handles exception when storing plan."""
        mock_orch_config.default_timeout = 300
        
        # Mock plans to raise exception
        class ExceptionDict(dict):
            def __setitem__(self, key, value):
                raise Exception("Storage error")
        
        mock_orch_config.plans = ExceptionDict()
        mock_orch_config.wait_for_approval = AsyncMock(return_value=True)
        mock_orch_config.set_approval_pending = Mock()
        mock_conn_config.send_status_update_async = AsyncMock()
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_plan_message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[TextContent(text="Plan")]
        )
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'plan',
            new_callable=AsyncMock,
            return_value=mock_plan_message
        ):
            mock_ledger = Mock()
            mock_ledger.plan.text = "Step 1"
            mock_ledger.facts.text = "Fact 1"
            manager.task_ledger = mock_ledger
            
            mock_mplan = MPlan(
                id="plan-error",
                task="Test",
                facts="Fact 1",
                team=["Agent1"],
                steps=[]
            )
            manager.plan_to_obj = Mock(return_value=mock_mplan)
            
            mock_context = Mock(spec=MagenticContext)
            mock_context.task = Mock()
            mock_context.task.text = "Test"
            mock_context.participant_descriptions = {"Agent1": "Desc"}
            
            # Should continue despite storage error
            result = await manager.plan(mock_context)
            
            assert result == mock_plan_message

    @pytest.mark.asyncio
    async def test_create_progress_ledger_at_max_rounds_boundary(self):
        """Test create_progress_ledger at exact max rounds boundary."""
        mock_orch_config.default_timeout = 300
        mock_orch_config.max_rounds = 5
        mock_conn_config.send_status_update_async = AsyncMock()
        
        manager = HumanApprovalMagenticManager(
            user_id="user123",
            orchestrator=Mock(),
            participants=[Mock()]
        )
        
        mock_ledger = Mock()
        mock_ledger.is_request_satisfied = Mock()
        mock_ledger.is_in_loop = Mock()
        mock_ledger.is_progress_being_made = Mock()
        mock_ledger.next_speaker = Mock()
        mock_ledger.instruction_or_question = Mock()
        
        with patch.object(
            HumanApprovalMagenticManager.__bases__[0],
            'create_progress_ledger',
            new_callable=AsyncMock,
            return_value=mock_ledger
        ):
            mock_context = Mock(spec=MagenticContext)
            mock_context.round_count = 5  # Exactly at max_rounds
            
            result = await manager.create_progress_ledger(mock_context)
            
            # Should NOT trigger termination at exactly max_rounds
            # Only when exceeding (>= check in code)
            assert result.is_request_satisfied.answer is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])




