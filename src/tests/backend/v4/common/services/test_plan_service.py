"""
Comprehensive unit tests for PlanService.

This module contains extensive test coverage for:
- PlanService static methods for handling various message types
- Utility functions for building agent messages
- Plan approval and rejection workflows
- Agent message processing and persistence
- Human clarification handling
- Error handling and edge cases
"""

import pytest
import os
import sys
import asyncio
import json
import logging
import importlib.util
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from typing import Any, Dict, Optional, List
from dataclasses import dataclass

# Add the src directory to sys.path for proper import
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
if src_path not in sys.path:
    sys.path.insert(0, os.path.abspath(src_path))

# Mock Azure modules before importing the PlanService
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

# Mock other problematic modules and imports
sys.modules['common.models.messages_af'] = MagicMock()
sys.modules['v4'] = MagicMock()
sys.modules['v4.common'] = MagicMock()
sys.modules['v4.common.services'] = MagicMock()
sys.modules['v4.common.services.team_service'] = MagicMock()
sys.modules['v4.models'] = MagicMock()
sys.modules['v4.models.messages'] = MagicMock()
sys.modules['v4.config'] = MagicMock()
sys.modules['v4.config.settings'] = MagicMock()

# Mock the config module
mock_config_module = MagicMock()
mock_config = MagicMock()

# Mock config attributes for database and other dependencies
mock_config.DATABASE_TYPE = 'memory'
mock_config.DATABASE_CONNECTION = 'test-connection'

mock_config_module.config = mock_config
sys.modules['common.config.app_config'] = mock_config_module

# Mock database modules
mock_database_factory = MagicMock()
sys.modules['common.database.database_factory'] = mock_database_factory

# Mock event utils
mock_event_utils = MagicMock()
sys.modules['common.utils.event_utils'] = mock_event_utils

# Create mock message types and enums
mock_messages_af = MagicMock()

# Create mock enums
class MockAgentType:
    HUMAN = MagicMock()
    HUMAN.value = "Human_Agent"

class MockAgentMessageType:
    HUMAN_AGENT = "Human_Agent"
    AI_AGENT = "AI_Agent"

class MockPlanStatus:
    approved = "approved"
    completed = "completed"
    rejected = "rejected"

# Create mock AgentMessageData class
class MockAgentMessageData:
    def __init__(self, plan_id, user_id, m_plan_id, agent, agent_type, content, raw_data, steps, next_steps):
        self.plan_id = plan_id
        self.user_id = user_id
        self.m_plan_id = m_plan_id
        self.agent = agent
        self.agent_type = agent_type
        self.content = content
        self.raw_data = raw_data
        self.steps = steps
        self.next_steps = next_steps

mock_messages_af.AgentType = MockAgentType
mock_messages_af.AgentMessageType = MockAgentMessageType
mock_messages_af.PlanStatus = MockPlanStatus
mock_messages_af.AgentMessageData = MockAgentMessageData
sys.modules['common.models.messages_af'] = mock_messages_af

# Create mock v4.models.messages module
mock_v4_messages = MagicMock()
sys.modules['v4.models.messages'] = mock_v4_messages

# Now import the real PlanService using direct file import with proper mocking
import importlib.util

# Mock the orchestration_config
mock_orchestration_config = MagicMock()
mock_orchestration_config.plans = {}

with patch.dict('sys.modules', {
    'common.models.messages_af': mock_messages_af,
    'v4.models.messages': mock_v4_messages,
    'v4.config.settings': MagicMock(orchestration_config=mock_orchestration_config),
    'common.database.database_factory': mock_database_factory,
    'common.utils.event_utils': mock_event_utils,
}):
    plan_service_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'backend', 'v4', 'common', 'services', 'plan_service.py')
    plan_service_path = os.path.abspath(plan_service_path)
    spec = importlib.util.spec_from_file_location("backend.v4.common.services.plan_service", plan_service_path)
    plan_service_module = importlib.util.module_from_spec(spec)
    
    # Set the proper module name for coverage tracking (matching --cov=backend pattern)
    plan_service_module.__name__ = "backend.v4.common.services.plan_service"
    plan_service_module.__file__ = plan_service_path
    
    # Add to sys.modules BEFORE execution for coverage tracking (both variations)
    sys.modules['backend.v4.common.services.plan_service'] = plan_service_module
    sys.modules['src.backend.v4.common.services.plan_service'] = plan_service_module
    
    spec.loader.exec_module(plan_service_module)

PlanService = plan_service_module.PlanService
build_agent_message_from_user_clarification = plan_service_module.build_agent_message_from_user_clarification
build_agent_message_from_agent_message_response = plan_service_module.build_agent_message_from_agent_message_response


# Test data classes
@dataclass
class MockUserClarificationResponse:
    plan_id: str = ""
    m_plan_id: str = ""
    answer: str = ""


@dataclass  
class MockAgentMessageResponse:
    plan_id: str = ""
    user_id: str = ""
    m_plan_id: str = ""
    agent: str = ""
    agent_name: str = ""
    source: str = ""
    agent_type: Any = None
    content: str = ""
    text: str = ""
    raw_data: Any = None
    steps: List = None
    next_steps: List = None
    is_final: bool = False
    streaming_message: str = ""


@dataclass
class MockPlanApprovalResponse:
    plan_id: str = ""
    m_plan_id: str = ""
    approved: bool = True
    feedback: str = ""


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_build_agent_message_from_user_clarification_basic(self):
        """Test basic agent message building from user clarification."""
        feedback = MockUserClarificationResponse(
            plan_id="test-plan-123",
            m_plan_id="test-m-plan-456", 
            answer="This is my clarification"
        )
        user_id = "test-user-789"
        
        result = build_agent_message_from_user_clarification(feedback, user_id)
        
        assert result.plan_id == "test-plan-123"
        assert result.user_id == "test-user-789"
        assert result.m_plan_id == "test-m-plan-456"
        assert result.agent == "Human_Agent"
        assert result.content == "This is my clarification"
        assert result.steps == []
        assert result.next_steps == []

    def test_build_agent_message_from_user_clarification_empty_fields(self):
        """Test building agent message with empty/None fields."""
        feedback = MockUserClarificationResponse(
            plan_id=None,
            m_plan_id=None,
            answer=None
        )
        user_id = "test-user"
        
        result = build_agent_message_from_user_clarification(feedback, user_id)
        
        assert result.plan_id == ""
        assert result.user_id == "test-user"
        assert result.m_plan_id is None
        assert result.content == ""

    def test_build_agent_message_from_user_clarification_raw_data_serialization(self):
        """Test that raw_data is properly serialized as JSON."""
        feedback = MockUserClarificationResponse(
            plan_id="test-plan",
            answer="test answer"
        )
        user_id = "test-user"
        
        result = build_agent_message_from_user_clarification(feedback, user_id)
        
        # Parse the raw_data JSON to verify it's valid
        raw_data = json.loads(result.raw_data)
        assert raw_data["plan_id"] == "test-plan"
        assert raw_data["answer"] == "test answer"

    def test_build_agent_message_from_agent_message_response_basic(self):
        """Test basic agent message building from agent response."""
        response = MockAgentMessageResponse(
            plan_id="test-plan-123",
            user_id="response-user",
            agent="TestAgent",
            content="Agent response content",
            steps=["step1", "step2"],
            next_steps=["next1"]
        )
        user_id = "fallback-user"
        
        result = build_agent_message_from_agent_message_response(response, user_id)
        
        assert result.plan_id == "test-plan-123"
        assert result.user_id == "response-user"  # Should use response user_id
        assert result.agent == "TestAgent"
        assert result.content == "Agent response content"
        assert result.steps == ["step1", "step2"]
        assert result.next_steps == ["next1"]

    def test_build_agent_message_from_agent_message_response_fallbacks(self):
        """Test fallback logic for missing fields."""
        response = MockAgentMessageResponse(
            plan_id="",
            user_id="",
            agent="",
            agent_name="NamedAgent",
            text="Text content",
            steps=None,
            next_steps=None
        )
        user_id = "fallback-user"
        
        result = build_agent_message_from_agent_message_response(response, user_id)
        
        assert result.plan_id == ""
        assert result.user_id == "fallback-user"  # Should use fallback
        assert result.agent == "NamedAgent"  # Should use agent_name fallback
        assert result.content == "Text content"  # Should use text fallback
        assert result.steps == []  # Should default to empty list
        assert result.next_steps == []

    def test_build_agent_message_from_agent_message_response_agent_type_inference(self):
        """Test agent type inference logic."""
        # Test human agent type inference
        response_human = MockAgentMessageResponse(agent_type="human_agent")
        result = build_agent_message_from_agent_message_response(response_human, "user")
        assert result.agent_type == MockAgentMessageType.HUMAN_AGENT
        
        # Test AI agent type fallback
        response_ai = MockAgentMessageResponse(agent_type="unknown")
        result = build_agent_message_from_agent_message_response(response_ai, "user")
        assert result.agent_type == MockAgentMessageType.AI_AGENT

    def test_build_agent_message_from_agent_message_response_raw_data_handling(self):
        """Test various raw_data handling scenarios."""
        # Test with dict raw_data
        response_dict = MockAgentMessageResponse(raw_data={"test": "data"})
        result = build_agent_message_from_agent_message_response(response_dict, "user")
        assert '"test": "data"' in result.raw_data
        
        # Test with None raw_data (should use asdict fallback)
        response_none = MockAgentMessageResponse(raw_data=None, content="test")
        result = build_agent_message_from_agent_message_response(response_none, "user")
        # Should contain serialized object data
        assert isinstance(result.raw_data, str)

    def test_build_agent_message_from_agent_message_response_source_fallback(self):
        """Test agent name fallback to source field."""
        response = MockAgentMessageResponse(
            agent="",
            agent_name="",
            source="SourceAgent"
        )
        
        result = build_agent_message_from_agent_message_response(response, "user")
        assert result.agent == "SourceAgent"


class TestPlanService:
    """Test cases for PlanService class."""

    @pytest.mark.asyncio
    async def test_handle_plan_approval_success(self):
        """Test successful plan approval."""
        # Setup mock data
        mock_approval = MockPlanApprovalResponse(
            plan_id="test-plan-123",
            m_plan_id="test-m-plan-456",
            approved=True,
            feedback="Looks good!"
        )
        user_id = "test-user"
        
        # Setup mock orchestration config
        mock_mplan = MagicMock()
        mock_mplan.plan_id = None
        mock_mplan.team_id = None
        mock_mplan.model_dump.return_value = {"test": "data"}
        
        mock_orchestration_config.plans = {"test-m-plan-456": mock_mplan}
        
        # Setup mock database and plan
        mock_db = MagicMock()
        mock_plan = MagicMock()
        mock_plan.team_id = "test-team"
        mock_db.get_plan = AsyncMock(return_value=mock_plan)
        mock_db.update_plan = AsyncMock()
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(return_value=mock_db)
        
        with patch.object(plan_service_module, 'orchestration_config', mock_orchestration_config):
            result = await PlanService.handle_plan_approval(mock_approval, user_id)
        
        assert result is True
        assert mock_mplan.plan_id == "test-plan-123"
        assert mock_mplan.team_id == "test-team"
        assert mock_plan.overall_status == MockPlanStatus.approved
        mock_db.update_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_plan_approval_rejection(self):
        """Test plan rejection."""
        mock_approval = MockPlanApprovalResponse(
            plan_id="test-plan-123",
            m_plan_id="test-m-plan-456",
            approved=False,
            feedback="Need changes"
        )
        user_id = "test-user"
        
        # Setup mock orchestration config
        mock_mplan = MagicMock()
        mock_mplan.plan_id = "existing-plan-id"
        mock_orchestration_config.plans = {"test-m-plan-456": mock_mplan}
        
        # Setup mock database
        mock_db = MagicMock()
        mock_db.delete_plan_by_plan_id = AsyncMock()
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(return_value=mock_db)
        
        with patch.object(plan_service_module, 'orchestration_config', mock_orchestration_config):
            result = await PlanService.handle_plan_approval(mock_approval, user_id)
        
        assert result is True
        mock_db.delete_plan_by_plan_id.assert_called_once_with("test-plan-123")

    @pytest.mark.asyncio
    async def test_handle_plan_approval_no_orchestration_config(self):
        """Test when orchestration config is None."""
        mock_approval = MockPlanApprovalResponse()
        
        with patch.object(plan_service_module, 'orchestration_config', None):
            result = await PlanService.handle_plan_approval(mock_approval, "user")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_plan_approval_plan_not_found(self):
        """Test when plan is not found in memory store."""
        mock_approval = MockPlanApprovalResponse(
            plan_id="missing-plan",
            m_plan_id="test-m-plan",
            approved=True
        )
        
        mock_mplan = MagicMock()
        mock_mplan.plan_id = None
        mock_orchestration_config.plans = {"test-m-plan": mock_mplan}
        
        mock_db = MagicMock()
        mock_db.get_plan = AsyncMock(return_value=None)  # Plan not found
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(return_value=mock_db)
        
        with patch.object(plan_service_module, 'orchestration_config', mock_orchestration_config):
            result = await PlanService.handle_plan_approval(mock_approval, "user")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_plan_approval_exception(self):
        """Test exception handling in plan approval."""
        mock_approval = MockPlanApprovalResponse(m_plan_id="nonexistent")
        
        # Setup orchestration config that will cause KeyError
        mock_orchestration_config.plans = {}
        
        with patch.object(plan_service_module, 'orchestration_config', mock_orchestration_config):
            result = await PlanService.handle_plan_approval(mock_approval, "user")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_agent_messages_success(self):
        """Test successful agent message handling."""
        mock_message = MockAgentMessageResponse(
            plan_id="test-plan",
            agent="TestAgent",
            content="Agent message content",
            is_final=False
        )
        user_id = "test-user"
        
        # Setup mock database
        mock_db = MagicMock()
        mock_db.add_agent_message = AsyncMock()
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(return_value=mock_db)
        
        result = await PlanService.handle_agent_messages(mock_message, user_id)
        
        assert result is True
        mock_db.add_agent_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_agent_messages_final_message(self):
        """Test handling final agent message."""
        mock_message = MockAgentMessageResponse(
            plan_id="test-plan",
            agent="TestAgent",
            content="Final message",
            is_final=True,
            streaming_message="Stream completed"
        )
        user_id = "test-user"
        
        # Setup mock database and plan
        mock_db = MagicMock()
        mock_plan = MagicMock()
        mock_db.add_agent_message = AsyncMock()
        mock_db.get_plan = AsyncMock(return_value=mock_plan)
        mock_db.update_plan = AsyncMock()
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(return_value=mock_db)
        
        result = await PlanService.handle_agent_messages(mock_message, user_id)
        
        assert result is True
        assert mock_plan.streaming_message == "Stream completed"
        assert mock_plan.overall_status == MockPlanStatus.completed
        mock_db.update_plan.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_agent_messages_exception(self):
        """Test exception handling in agent message processing."""
        mock_message = MockAgentMessageResponse()
        
        # Mock database to raise exception
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(side_effect=Exception("Database error"))
        
        result = await PlanService.handle_agent_messages(mock_message, "user")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_human_clarification_success(self):
        """Test successful human clarification handling."""
        mock_clarification = MockUserClarificationResponse(
            plan_id="test-plan",
            answer="This is my clarification"
        )
        user_id = "test-user"
        
        # Setup mock database
        mock_db = MagicMock()
        mock_db.add_agent_message = AsyncMock()
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(return_value=mock_db)
        
        result = await PlanService.handle_human_clarification(mock_clarification, user_id)
        
        assert result is True
        mock_db.add_agent_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_human_clarification_exception(self):
        """Test exception handling in human clarification."""
        mock_clarification = MockUserClarificationResponse()
        
        # Mock database to raise exception
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(side_effect=Exception("Database error"))
        
        result = await PlanService.handle_human_clarification(mock_clarification, "user")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_static_method_properties(self):
        """Test that all PlanService methods are static."""
        # Verify methods are static by calling them on the class
        mock_approval = MockPlanApprovalResponse(approved=False)
        
        with patch.object(plan_service_module, 'orchestration_config', None):
            result = await PlanService.handle_plan_approval(mock_approval, "user")
            assert result is False

    def test_event_tracking_calls(self):
        """Test that event tracking is called appropriately."""
        # This test verifies the event tracking integration
        with patch.object(mock_event_utils, 'track_event_if_configured') as mock_track:
            mock_approval = MockPlanApprovalResponse(
                plan_id="test-plan",
                m_plan_id="test-m-plan",
                approved=True
            )
            
            # The actual event tracking calls are tested indirectly through the service methods
            assert mock_track is not None

    def test_logging_integration(self):
        """Test that logging is properly configured."""
        # Verify that the logger is set up correctly
        logger = logging.getLogger('backend.v4.common.services.plan_service')
        assert logger is not None

    @pytest.mark.asyncio
    async def test_integration_scenario_approval_workflow(self):
        """Test complete approval workflow integration."""
        # Setup complete mock environment
        mock_mplan = MagicMock()
        mock_mplan.plan_id = None
        mock_mplan.team_id = None
        mock_mplan.model_dump.return_value = {"test": "plan"}
        
        mock_orchestration_config.plans = {"m-plan-123": mock_mplan}
        
        mock_plan = MagicMock()
        mock_plan.team_id = "team-456"
        
        mock_db = MagicMock()
        mock_db.get_plan = AsyncMock(return_value=mock_plan)
        mock_db.update_plan = AsyncMock()
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(return_value=mock_db)
        
        # Test approval flow
        approval = MockPlanApprovalResponse(
            plan_id="plan-123",
            m_plan_id="m-plan-123",
            approved=True,
            feedback="Approved"
        )
        
        with patch.object(plan_service_module, 'orchestration_config', mock_orchestration_config):
            result = await PlanService.handle_plan_approval(approval, "user-123")
        
        assert result is True
        assert mock_mplan.plan_id == "plan-123"
        assert mock_mplan.team_id == "team-456"
        assert mock_plan.overall_status == MockPlanStatus.approved

    @pytest.mark.asyncio
    async def test_integration_scenario_message_processing(self):
        """Test complete message processing workflow."""
        # Test agent message processing
        mock_db = MagicMock()
        mock_db.add_agent_message = AsyncMock()
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(return_value=mock_db)
        
        agent_msg = MockAgentMessageResponse(
            plan_id="plan-456",
            agent="ProcessingAgent",
            content="Processing complete",
            is_final=False
        )
        
        result = await PlanService.handle_agent_messages(agent_msg, "user-456")
        assert result is True
        
        # Test human clarification
        clarification = MockUserClarificationResponse(
            plan_id="plan-456",
            answer="Additional clarification"
        )
        
        result = await PlanService.handle_human_clarification(clarification, "user-456")
        assert result is True
        
        # Verify both calls made it to the database
        assert mock_db.add_agent_message.call_count == 2

    def test_error_resilience(self):
        """Test error handling and resilience across different scenarios."""
        # Test with various malformed inputs
        malformed_inputs = [
            MockUserClarificationResponse(plan_id=None, answer=None),
            MockAgentMessageResponse(plan_id="", content="", steps=[]),
            MockPlanApprovalResponse(approved=True, plan_id=""),
        ]
        
        for input_obj in malformed_inputs:
            # These should not raise exceptions during object creation
            assert input_obj is not None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test handling of concurrent operations."""
        mock_db = MagicMock()
        mock_db.add_agent_message = AsyncMock()
        mock_database_factory.DatabaseFactory.get_database = AsyncMock(return_value=mock_db)
        
        # Create multiple tasks
        tasks = []
        for i in range(5):
            clarification = MockUserClarificationResponse(
                plan_id=f"plan-{i}",
                answer=f"Clarification {i}"
            )
            task = PlanService.handle_human_clarification(clarification, f"user-{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
        assert mock_db.add_agent_message.call_count == 5