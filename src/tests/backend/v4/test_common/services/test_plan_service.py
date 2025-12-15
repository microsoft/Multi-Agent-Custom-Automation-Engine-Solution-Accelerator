"""
Unit tests for v4 PlanService with real function imports for coverage.

Tests cover:
- build_agent_message_from_user_clarification function
- build_agent_message_from_agent_message_response function  
- PlanService methods
- Error handling and edge cases
"""

import json
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from dataclasses import asdict, dataclass
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
from enum import Enum

# Add backend path to sys.path for proper imports  
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import real plan_service functions for coverage
from v4.common.services.plan_service import (
    build_agent_message_from_user_clarification,
    build_agent_message_from_agent_message_response
)

# Mock the v4.models.messages module
@dataclass
class UserClarificationResponse:
    plan_id: Optional[str] = None
    m_plan_id: Optional[str] = None
    answer: Optional[str] = None

@dataclass
class AgentMessageResponse:
    plan_id: str = ""
    user_id: str = ""
    m_plan_id: Optional[str] = None
    agent: str = ""
    content: str = ""
    agent_type: Optional[str] = None
    steps: Optional[List] = None
    next_steps: Optional[List] = None
    is_final: bool = False
    streaming_message: Optional[str] = None
    raw_data: Optional[Any] = None
    agent_name: Optional[str] = None
    source: Optional[str] = None
    text: Optional[str] = None

@dataclass
class PlanApprovalResponse:
    plan_id: str = ""
    user_id: str = ""
    approved: bool = False
    feedback: Optional[str] = None


class TestRealPlanServiceFunctions:
    """Test cases using real plan_service functions for coverage."""

    def test_real_build_agent_message_from_user_clarification(self):
        """Test real build_agent_message_from_user_clarification function."""
        # Create a real UserClarificationResponse using the mock structure
        user_feedback = UserClarificationResponse(
            plan_id="test-plan-123",
            m_plan_id="m-plan-456",
            answer="Yes, proceed with the plan"
        )
        user_id = "user-789"

        with patch('v4.common.services.plan_service.AgentMessageData') as mock_agent_msg:
            with patch('v4.common.services.plan_service.AgentType') as mock_agent_type:
                with patch('v4.common.services.plan_service.AgentMessageType') as mock_msg_type:
                    # Mock the enum values
                    mock_agent_type.HUMAN.value = "Human_Agent"
                    mock_msg_type.HUMAN_AGENT = "HUMAN_AGENT"
                    
                    # Mock json.dumps to avoid import issues
                    with patch('v4.common.services.plan_service.json.dumps', return_value='{"test": "data"}'):
                        result = build_agent_message_from_user_clarification(user_feedback, user_id)
                        
                        # Verify the function was called with correct parameters
                        mock_agent_msg.assert_called_once()
                        call_kwargs = mock_agent_msg.call_args[1]
                        assert call_kwargs['plan_id'] == "test-plan-123"
                        assert call_kwargs['user_id'] == "user-789"
                        assert call_kwargs['content'] == "Yes, proceed with the plan"

    def test_real_build_agent_message_from_agent_response(self):
        """Test real build_agent_message_from_agent_message_response function."""
        agent_response = AgentMessageResponse(
            plan_id="agent-plan-123",
            agent="test-agent",
            content="Agent response content",
            agent_type="AI_AGENT"
        )
        user_id = "user-456"

        with patch('v4.common.services.plan_service.AgentMessageData') as mock_agent_msg:
            with patch('v4.common.services.plan_service.AgentMessageType') as mock_msg_type:
                # Mock enum values
                mock_msg_type.AI_AGENT = "AI_AGENT"
                mock_msg_type.HUMAN_AGENT = "HUMAN_AGENT"
                
                # Mock json.dumps
                with patch('v4.common.services.plan_service.json.dumps', return_value='{"agent": "data"}'):
                    result = build_agent_message_from_agent_message_response(agent_response, user_id)
                    
                    # Verify the function was called
                    mock_agent_msg.assert_called_once()
                    call_kwargs = mock_agent_msg.call_args[1]
                    assert 'plan_id' in call_kwargs
                    assert 'user_id' in call_kwargs
    m_plan_id: str
    plan_id: str
    approved: bool
    feedback: Optional[str] = None

# Create a messages module mock
class MessagesMock:
    UserClarificationResponse = UserClarificationResponse
    AgentMessageResponse = AgentMessageResponse
    PlanApprovalResponse = PlanApprovalResponse

messages = MessagesMock()

# Mock the common.models.messages_af enums and types
class AgentType(Enum):
    HUMAN = "Human_Agent"
    AI = "AI_Agent"

class AgentMessageType(Enum):
    HUMAN_AGENT = "Human_Agent"
    AI_AGENT = "AI_Agent"

class PlanStatus(Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    in_progress = "in_progress"
    completed = "completed"

@dataclass
class AgentMessageData:
    plan_id: str
    user_id: str
    m_plan_id: Optional[str]
    agent: str
    agent_type: AgentMessageType
    content: str
    raw_data: str
    steps: List
    next_steps: List

# REMOVED sys.modules pollution - these lines cause test failures when running full test suite
# The problem: These lines modify sys.modules at MODULE IMPORT TIME, which means
# pytest imports all test files and pollutes shared modules before any tests run.
# This causes isinstance() checks to fail because imports get Mock objects instead of real classes.

# We'll use patch() decorators on individual tests instead of global sys.modules mocking

# Read and exec the plan_service.py file
plan_service_path = Path(__file__).parent.parent.parent.parent.parent.parent / "backend" / "v4" / "common" / "services" / "plan_service.py"
plan_service_content = plan_service_path.read_text()

# Create a dynamic module that provides v4.models.messages
class V4ModulesMock:
    class messages:
        UserClarificationResponse = UserClarificationResponse
        AgentMessageResponse = AgentMessageResponse
        PlanApprovalResponse = PlanApprovalResponse

# Replace the import statements
modified_content = plan_service_content.replace(
    "import v4.models.messages as messages",
    "# v4.models.messages imported via mock"
).replace(
    "from common.database.database_factory import DatabaseFactory",
    "# DatabaseFactory imported via mock"
).replace(
    "from common.models.messages_af import (",
    "# messages_af imports mocked #("
).replace(
    "from common.utils.event_utils import track_event_if_configured",
    "# track_event_if_configured imported via mock"
).replace(
    "from v4.config.settings import orchestration_config",
    "# orchestration_config imported via mock"
).replace(
    "if orchestration_config is None:",
    "if _get_config() is None:"
).replace(
    "mplan = orchestration_config.plans[human_feedback.m_plan_id]",
    "mplan = _get_config().plans[human_feedback.m_plan_id]"
).replace(
    "                orchestration_config.plans[human_feedback.m_plan_id],",
    "                _get_config().plans[human_feedback.m_plan_id],"
).replace(
    "                orchestration_config.plans[human_feedback.m_plan_id] = mplan",
    "                _get_config().plans[human_feedback.m_plan_id] = mplan"
).replace(
    "track_event_if_configured(",
    "_track_event("
).replace(
    "agent_msg = build_agent_message_from_agent_message_response(",
    "agent_msg = _get_build_from_response()("
).replace(
    "agent_msg = build_agent_message_from_user_clarification(",
    "agent_msg = _get_build_from_clarification()("
)

# Remove the actual import lines that were commented
import re
from pathlib import Path

# Add backend path to sys.path for proper imports
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

modified_content = re.sub(r'# messages_af imports mocked #\([^)]+\)', '', modified_content)

# Create dynamic accessor that gets values from the module at runtime
class DynamicModuleAccessor:
    def __getattr__(self, name):
        module = sys.modules.get('v4.common.services')
        if module and hasattr(module, 'plan_service'):
            return getattr(module.plan_service, name)
        return None

_accessor = DynamicModuleAccessor()

# Create proxy class for DatabaseFactory that accesses the module dynamically
class DatabaseFactoryProxy:
    @staticmethod
    async def get_database(*args, **kwargs):
        # Get the actual DatabaseFactory from the module which may be mocked
        df = _accessor.DatabaseFactory
        if df and hasattr(df, 'get_database'):
            result = df.get_database(*args, **kwargs)
            # If it's a coroutine, await it; otherwise return directly
            if hasattr(result, '__await__'):
                return await result
            return result
        return None

# Create helper functions that access module dynamically
def _get_config():
    # First try to get from the module (for patches)
    module = sys.modules.get('v4.common.services')
    if module and hasattr(module, 'plan_service') and hasattr(module.plan_service, 'orchestration_config'):
        return module.plan_service.orchestration_config
    # Fallback to accessor
    return _accessor.orchestration_config

def _track_event(*args, **kwargs):
    # First try to get from the module (for patches)
    module = sys.modules.get('v4.common.services')
    if module and hasattr(module, 'plan_service') and hasattr(module.plan_service, 'track_event_if_configured'):
        fn = module.plan_service.track_event_if_configured
        if fn:
            return fn(*args, **kwargs)
    # Fallback to accessor
    fn = _accessor.track_event_if_configured
    if fn:
        return fn(*args, **kwargs)

def _get_build_from_response():
    # First try to get from the module (for patches)
    module = sys.modules.get('v4.common.services')
    if module and hasattr(module, 'plan_service') and hasattr(module.plan_service, 'build_agent_message_from_agent_message_response'):
        return module.plan_service.build_agent_message_from_agent_message_response
    # Fallback to accessor
    return _accessor.build_agent_message_from_agent_message_response

def _get_build_from_clarification():
    # First try to get from the module (for patches)
    module = sys.modules.get('v4.common.services')
    if module and hasattr(module, 'plan_service') and hasattr(module.plan_service, 'build_agent_message_from_user_clarification'):
        return module.plan_service.build_agent_message_from_user_clarification
    # Fallback to accessor
    return _accessor.build_agent_message_from_user_clarification

# Create namespace for exec
plan_namespace = {
    'json': json,
    'logging': logging,
    'asdict': asdict,
    'messages': messages,
    'DatabaseFactory': DatabaseFactoryProxy,
    'AgentMessageData': AgentMessageData,
    'AgentMessageType': AgentMessageType,
    'AgentType': AgentType,
    'PlanStatus': PlanStatus,
    'logger': logging.getLogger(__name__),
    '_get_config': _get_config,
    '_track_event': _track_event,
    '_get_build_from_response': _get_build_from_response,
    '_get_build_from_clarification': _get_build_from_clarification
}

exec(modified_content, plan_namespace)

# Extract the functions and class we need
build_agent_message_from_user_clarification = plan_namespace['build_agent_message_from_user_clarification']
build_agent_message_from_agent_message_response = plan_namespace['build_agent_message_from_agent_message_response']
PlanService = plan_namespace['PlanService']

# Create a mock module that contains these for the @patch decorators
plan_service_module = type(sys)('plan_service')
plan_service_module.build_agent_message_from_user_clarification = build_agent_message_from_user_clarification
plan_service_module.build_agent_message_from_agent_message_response = build_agent_message_from_agent_message_response
plan_service_module.PlanService = PlanService
plan_service_module.DatabaseFactory = Mock()
plan_service_module.track_event_if_configured = Mock()
plan_service_module.orchestration_config = None

# REMOVED: sys.modules pollution that causes isinstance() failures across test files


class TestBuildAgentMessageFromUserClarification:
    """Test cases for build_agent_message_from_user_clarification function."""

    def test_basic_user_clarification(self):
        """Test building agent message from basic user clarification."""
        clarification = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer="This is my clarification answer"
        )
        
        result = build_agent_message_from_user_clarification(clarification, "user-789")
        
        assert result.plan_id == "plan-123"
        assert result.user_id == "user-789"
        assert result.m_plan_id == "m-plan-456"
        assert result.agent == AgentType.HUMAN.value
        assert result.agent_type == AgentMessageType.HUMAN_AGENT
        assert result.content == "This is my clarification answer"
        assert result.steps == []
        assert result.next_steps == []

    def test_user_clarification_with_none_plan_id(self):
        """Test user clarification with None plan_id."""
        clarification = messages.UserClarificationResponse(
            plan_id=None,
            m_plan_id="m-plan-456",
            answer="Answer text"
        )
        
        result = build_agent_message_from_user_clarification(clarification, "user-123")
        
        assert result.plan_id == ""
        assert result.user_id == "user-123"

    def test_user_clarification_with_none_m_plan_id(self):
        """Test user clarification with None m_plan_id."""
        clarification = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id=None,
            answer="Answer text"
        )
        
        result = build_agent_message_from_user_clarification(clarification, "user-123")
        
        assert result.m_plan_id is None

    def test_user_clarification_with_empty_answer(self):
        """Test user clarification with None answer."""
        clarification = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer=None
        )
        
        result = build_agent_message_from_user_clarification(clarification, "user-123")
        
        assert result.content == ""

    def test_user_clarification_raw_data_serialization(self):
        """Test that raw_data is properly serialized to JSON."""
        clarification = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer="My answer"
        )
        
        result = build_agent_message_from_user_clarification(clarification, "user-123")
        
        assert isinstance(result.raw_data, str)
        raw_dict = json.loads(result.raw_data)
        assert raw_dict["plan_id"] == "plan-123"
        assert raw_dict["answer"] == "My answer"

    def test_user_clarification_with_special_characters(self):
        """Test user clarification with special characters in answer."""
        clarification = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer="Answer with special chars: @#$%^&*() 中文 émojis 🎉"
        )
        
        result = build_agent_message_from_user_clarification(clarification, "user-123")
        
        assert result.content == "Answer with special chars: @#$%^&*() 中文 émojis 🎉"


class TestBuildAgentMessageFromAgentMessageResponse:
    """Test cases for build_agent_message_from_agent_message_response function."""

    def test_basic_agent_message_response(self):
        """Test building agent message from basic agent response."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            m_plan_id="m-plan-789",
            agent="TestAgent",
            agent_type=AgentMessageType.AI_AGENT,
            content="Agent response content",
            steps=["step1", "step2"],
            next_steps=["next1", "next2"]
        )
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert result.plan_id == "plan-123"
        assert result.user_id == "user-456"
        assert result.m_plan_id == "m-plan-789"
        assert result.agent == "TestAgent"
        assert result.agent_type == AgentMessageType.AI_AGENT
        assert result.content == "Agent response content"
        assert result.steps == ["step1", "step2"]
        assert result.next_steps == ["next1", "next2"]

    def test_agent_response_with_missing_fields(self):
        """Test agent response with missing optional fields."""
        agent_response = messages.AgentMessageResponse(
            plan_id="",
            user_id="",
            m_plan_id="",
            agent="",
            content=""
        )
        
        result = build_agent_message_from_agent_message_response(agent_response, "fallback-user")
        
        assert result.user_id == "fallback-user"
        assert result.steps == []
        assert result.next_steps == []

    def test_agent_response_infer_human_agent_type(self):
        """Test that 'human' string in agent_type is inferred correctly."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="HumanAgent",
            content="Human content"
        )
        agent_response.agent_type = "human_agent"
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert result.agent_type == AgentMessageType.HUMAN_AGENT

    def test_agent_response_default_to_ai_agent_type(self):
        """Test that unknown agent_type defaults to AI_AGENT."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="UnknownAgent",
            content="Content"
        )
        agent_response.agent_type = None
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert result.agent_type == AgentMessageType.AI_AGENT

    def test_agent_response_with_agent_name_fallback(self):
        """Test agent name fallback to agent_name or source attributes."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="",
            content="Content"
        )
        agent_response.agent_name = "FallbackAgentName"
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert result.agent == "FallbackAgentName"

    def test_agent_response_with_source_fallback(self):
        """Test agent name fallback to source attribute."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="",
            content="Content"
        )
        agent_response.source = "SourceAgent"
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert result.agent == "SourceAgent"

    def test_agent_response_with_text_content_fallback(self):
        """Test content fallback to text attribute."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content=""
        )
        agent_response.text = "Text content fallback"
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert result.content == "Text content fallback"

    def test_agent_response_raw_data_dict(self):
        """Test raw_data serialization when it's a dict."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content="Content"
        )
        agent_response.raw_data = {"key": "value", "nested": {"data": 123}}
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert isinstance(result.raw_data, str)
        raw_dict = json.loads(result.raw_data)
        assert raw_dict["key"] == "value"
        assert raw_dict["nested"]["data"] == 123

    def test_agent_response_raw_data_list(self):
        """Test raw_data serialization when it's a list."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content="Content"
        )
        agent_response.raw_data = [1, 2, 3, "data"]
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert isinstance(result.raw_data, str)
        raw_list = json.loads(result.raw_data)
        assert raw_list == [1, 2, 3, "data"]

    def test_agent_response_raw_data_none(self):
        """Test raw_data serialization when it's None."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content="Content"
        )
        agent_response.raw_data = None
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert isinstance(result.raw_data, str)
        # Should attempt to serialize the object itself

    def test_agent_response_none_steps_defaulting(self):
        """Test that None steps default to empty list."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content="Content"
        )
        agent_response.steps = None
        agent_response.next_steps = None
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert result.steps == []
        assert result.next_steps == []


class TestHandlePlanApproval:
    """Test cases for PlanService.handle_plan_approval method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.orchestration_config")
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    @patch("v4.common.services.plan_service.track_event_if_configured")
    async def test_handle_plan_approval_approved(self, mock_track, mock_get_db, mock_config):
        """Test successful plan approval."""
        # Mock orchestration config
        mock_mplan = Mock()
        mock_mplan.plan_id = None
        mock_mplan.team_id = None
        mock_mplan.model_dump.return_value = {"mplan": "data"}
        mock_config.plans = {"m-plan-123": mock_mplan}
        
        # Mock database
        mock_memory = AsyncMock()
        mock_plan = Mock()
        mock_plan.team_id = "team-456"
        mock_plan.overall_status = PlanStatus.pending
        mock_memory.get_plan = AsyncMock(return_value=mock_plan)
        mock_memory.update_plan = AsyncMock()
        mock_get_db.return_value = mock_memory
        
        # Create approval response
        approval = messages.PlanApprovalResponse(
            m_plan_id="m-plan-123",
            plan_id="plan-789",
            approved=True,
            feedback="Looks good"
        )
        
        result = await PlanService.handle_plan_approval(approval, "user-123")
        
        assert result is True
        assert mock_mplan.plan_id == "plan-789"
        assert mock_mplan.team_id == "team-456"
        assert mock_plan.overall_status == PlanStatus.approved
        mock_memory.update_plan.assert_called_once_with(mock_plan)
        mock_track.assert_called_once()
        assert mock_track.call_args[0][0] == "PlanApproved"

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.orchestration_config")
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    @patch("v4.common.services.plan_service.track_event_if_configured")
    async def test_handle_plan_approval_rejected(self, mock_track, mock_get_db, mock_config):
        """Test plan rejection."""
        # Mock orchestration config
        mock_mplan = Mock()
        mock_mplan.plan_id = None
        mock_config.plans = {"m-plan-123": mock_mplan}
        
        # Mock database
        mock_memory = AsyncMock()
        mock_memory.delete_plan_by_plan_id = AsyncMock()
        mock_get_db.return_value = mock_memory
        
        # Create rejection response
        approval = messages.PlanApprovalResponse(
            m_plan_id="m-plan-123",
            plan_id="plan-789",
            approved=False,
            feedback="Not good enough"
        )
        
        result = await PlanService.handle_plan_approval(approval, "user-123")
        
        assert result is True
        mock_memory.delete_plan_by_plan_id.assert_called_once_with("plan-789")
        mock_track.assert_called_once()
        assert mock_track.call_args[0][0] == "PlanRejected"

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.orchestration_config", None)
    async def test_handle_plan_approval_no_config(self):
        """Test plan approval when orchestration_config is None."""
        approval = messages.PlanApprovalResponse(
            m_plan_id="m-plan-123",
            plan_id="plan-789",
            approved=True,
            feedback="Test"
        )
        
        result = await PlanService.handle_plan_approval(approval, "user-123")
        
        assert result is False

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.orchestration_config")
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    async def test_handle_plan_approval_plan_not_found(self, mock_get_db, mock_config):
        """Test plan approval when plan is not found in memory store."""
        # Mock orchestration config
        mock_mplan = Mock()
        mock_mplan.plan_id = None
        mock_config.plans = {"m-plan-123": mock_mplan}
        
        # Mock database returning None plan
        mock_memory = AsyncMock()
        mock_memory.get_plan = AsyncMock(return_value=None)
        mock_get_db.return_value = mock_memory
        
        approval = messages.PlanApprovalResponse(
            m_plan_id="m-plan-123",
            plan_id="plan-789",
            approved=True,
            feedback="Test"
        )
        
        result = await PlanService.handle_plan_approval(approval, "user-123")
        
        assert result is False

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.orchestration_config")
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    async def test_handle_plan_approval_exception(self, mock_get_db, mock_config):
        """Test plan approval with exception."""
        mock_config.plans = {"m-plan-123": Mock()}
        mock_get_db.side_effect = Exception("Database error")
        
        approval = messages.PlanApprovalResponse(
            m_plan_id="m-plan-123",
            plan_id="plan-789",
            approved=True,
            feedback="Test"
        )
        
        result = await PlanService.handle_plan_approval(approval, "user-123")
        
        assert result is False

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.orchestration_config")
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    async def test_handle_plan_approval_missing_mplan_attribute(self, mock_get_db, mock_config):
        """Test plan approval when mplan doesn't have plan_id attribute."""
        # Mock mplan without plan_id attribute
        mock_mplan = Mock(spec=[])  # spec=[] means no attributes
        mock_config.plans = {"m-plan-123": mock_mplan}
        
        approval = messages.PlanApprovalResponse(
            m_plan_id="m-plan-123",
            plan_id="plan-789",
            approved=True,
            feedback="Test"
        )
        
        result = await PlanService.handle_plan_approval(approval, "user-123")
        
        # Should return True since it doesn't enter the hasattr block
        assert result is True


class TestHandleAgentMessages:
    """Test cases for PlanService.handle_agent_messages method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    @patch("v4.common.services.plan_service.build_agent_message_from_agent_message_response")
    async def test_handle_agent_messages_success(self, mock_build, mock_get_db):
        """Test successful agent message handling."""
        # Mock agent message
        mock_agent_msg = Mock()
        mock_agent_msg.plan_id = "plan-123"
        mock_build.return_value = mock_agent_msg
        
        # Mock database
        mock_memory = AsyncMock()
        mock_memory.add_agent_message = AsyncMock()
        mock_get_db.return_value = mock_memory
        
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content="Test content",
            is_final=False
        )
        
        result = await PlanService.handle_agent_messages(agent_response, "user-456")
        
        assert result is True
        mock_build.assert_called_once_with(agent_response, "user-456")
        mock_memory.add_agent_message.assert_called_once_with(mock_agent_msg)

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    @patch("v4.common.services.plan_service.build_agent_message_from_agent_message_response")
    async def test_handle_agent_messages_final_message(self, mock_build, mock_get_db):
        """Test handling final agent message."""
        # Mock agent message
        mock_agent_msg = Mock()
        mock_agent_msg.plan_id = "plan-123"
        mock_build.return_value = mock_agent_msg
        
        # Mock database and plan
        mock_plan = Mock()
        mock_plan.overall_status = PlanStatus.in_progress
        mock_memory = AsyncMock()
        mock_memory.add_agent_message = AsyncMock()
        mock_memory.get_plan = AsyncMock(return_value=mock_plan)
        mock_memory.update_plan = AsyncMock()
        mock_get_db.return_value = mock_memory
        
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content="Final content",
            is_final=True,
            streaming_message="Final message"
        )
        
        result = await PlanService.handle_agent_messages(agent_response, "user-456")
        
        assert result is True
        assert mock_plan.overall_status == PlanStatus.completed
        assert mock_plan.streaming_message == "Final message"
        mock_memory.update_plan.assert_called_once_with(mock_plan)

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    async def test_handle_agent_messages_exception(self, mock_get_db):
        """Test agent message handling with exception."""
        mock_get_db.side_effect = Exception("Database error")
        
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content="Test content"
        )
        
        result = await PlanService.handle_agent_messages(agent_response, "user-456")
        
        assert result is False

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    @patch("v4.common.services.plan_service.build_agent_message_from_agent_message_response")
    async def test_handle_agent_messages_non_final(self, mock_build, mock_get_db):
        """Test handling non-final agent message."""
        mock_agent_msg = Mock()
        mock_agent_msg.plan_id = "plan-123"
        mock_build.return_value = mock_agent_msg
        
        mock_memory = AsyncMock()
        mock_memory.add_agent_message = AsyncMock()
        mock_get_db.return_value = mock_memory
        
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content="Non-final content",
            is_final=False
        )
        
        result = await PlanService.handle_agent_messages(agent_response, "user-456")
        
        assert result is True
        # get_plan should not be called for non-final messages
        mock_memory.get_plan.assert_not_called()


class TestHandleHumanClarification:
    """Test cases for PlanService.handle_human_clarification method."""

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    @patch("v4.common.services.plan_service.build_agent_message_from_user_clarification")
    async def test_handle_human_clarification_success(self, mock_build, mock_get_db):
        """Test successful human clarification handling."""
        # Mock agent message
        mock_agent_msg = Mock()
        mock_build.return_value = mock_agent_msg
        
        # Mock database
        mock_memory = AsyncMock()
        mock_memory.add_agent_message = AsyncMock()
        mock_get_db.return_value = mock_memory
        
        clarification = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer="User's clarification"
        )
        
        result = await PlanService.handle_human_clarification(clarification, "user-789")
        
        assert result is True
        mock_build.assert_called_once_with(clarification, "user-789")
        mock_memory.add_agent_message.assert_called_once_with(mock_agent_msg)

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    async def test_handle_human_clarification_exception(self, mock_get_db):
        """Test human clarification handling with exception."""
        mock_get_db.side_effect = Exception("Database error")
        
        clarification = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer="User's clarification"
        )
        
        result = await PlanService.handle_human_clarification(clarification, "user-789")
        
        assert result is False

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    @patch("v4.common.services.plan_service.build_agent_message_from_user_clarification")
    async def test_handle_human_clarification_empty_answer(self, mock_build, mock_get_db):
        """Test human clarification with empty answer."""
        mock_agent_msg = Mock()
        mock_build.return_value = mock_agent_msg
        
        mock_memory = AsyncMock()
        mock_memory.add_agent_message = AsyncMock()
        mock_get_db.return_value = mock_memory
        
        clarification = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer=""
        )
        
        result = await PlanService.handle_human_clarification(clarification, "user-789")
        
        assert result is True

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    @patch("v4.common.services.plan_service.build_agent_message_from_user_clarification")
    async def test_handle_human_clarification_multiple_calls(self, mock_build, mock_get_db):
        """Test multiple human clarification calls."""
        mock_agent_msg1 = Mock()
        mock_agent_msg2 = Mock()
        mock_build.side_effect = [mock_agent_msg1, mock_agent_msg2]
        
        mock_memory = AsyncMock()
        mock_memory.add_agent_message = AsyncMock()
        mock_get_db.return_value = mock_memory
        
        clarification1 = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer="First clarification"
        )
        
        clarification2 = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer="Second clarification"
        )
        
        result1 = await PlanService.handle_human_clarification(clarification1, "user-789")
        result2 = await PlanService.handle_human_clarification(clarification2, "user-789")
        
        assert result1 is True
        assert result2 is True
        assert mock_memory.add_agent_message.call_count == 2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    @patch("v4.common.services.plan_service.orchestration_config")
    @patch("v4.common.services.plan_service.DatabaseFactory.get_database", new_callable=AsyncMock)
    async def test_plan_approval_key_error(self, mock_get_db, mock_config):
        """Test plan approval with missing m_plan_id key."""
        mock_config.plans = {}  # Empty plans dict
        
        approval = messages.PlanApprovalResponse(
            m_plan_id="nonexistent-mplan",
            plan_id="plan-789",
            approved=True,
            feedback="Test"
        )
        
        result = await PlanService.handle_plan_approval(approval, "user-123")
        
        assert result is False

    def test_build_functions_with_unicode_content(self):
        """Test build functions with unicode content."""
        clarification = messages.UserClarificationResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-456",
            answer="Unicode: 中文 日本語 한국어 العربية"
        )
        
        result = build_agent_message_from_user_clarification(clarification, "user-123")
        
        assert "中文" in result.content
        assert "日本語" in result.content

    def test_agent_response_with_complex_steps(self):
        """Test agent response with complex nested steps."""
        agent_response = messages.AgentMessageResponse(
            plan_id="plan-123",
            user_id="user-456",
            agent="TestAgent",
            content="Content",
            steps=[
                {"step": 1, "action": "do_something"},
                {"step": 2, "action": "do_something_else", "nested": {"data": "value"}}
            ],
            next_steps=[
                {"step": 3, "action": "future_action"}
            ]
        )
        
        result = build_agent_message_from_agent_message_response(agent_response, "user-456")
        
        assert len(result.steps) == 2
        assert len(result.next_steps) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
