# File: test_message.py

import uuid
from src.backend.common.models.messages_kernel import (
    DataType,
    AgentType as BAgentType,   # map to your enum
    StepStatus,
    PlanStatus,
    HumanFeedbackStatus,
    PlanWithSteps,
    Step,
    Plan,
    AgentMessage,
    ActionRequest,
    HumanFeedback,
)


def test_enum_values():
    """Test enumeration values for consistency."""
    assert DataType.session == "session"
    assert DataType.plan == "plan"
    assert BAgentType.HUMAN == "Human_Agent"   # was human_agent / "HumanAgent"
    assert StepStatus.completed == "completed"
    assert PlanStatus.in_progress == "in_progress"
    assert HumanFeedbackStatus.requested == "requested"


def test_plan_with_steps_update_counts():
    """Test the update_step_counts method in PlanWithSteps."""
    step1 = Step(
        plan_id=str(uuid.uuid4()),
        action="Review document",
        agent=BAgentType.HUMAN,
        status=StepStatus.completed,
        session_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )
    step2 = Step(
        plan_id=str(uuid.uuid4()),
        action="Approve document",
        agent=BAgentType.HR,
        status=StepStatus.failed,
        session_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )
    plan = PlanWithSteps(
        steps=[step1, step2],
        session_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        initial_goal="Test plan goal",
    )
    plan.update_step_counts()

    assert plan.total_steps == 2
    assert plan.completed == 1
    assert plan.failed == 1
    assert plan.overall_status == PlanStatus.completed


def test_agent_message_creation():
    """Test creation of an AgentMessage."""
    agent_message = AgentMessage(
        session_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        plan_id=str(uuid.uuid4()),
        content="Test message content",
        source="System",
    )
    assert agent_message.data_type == "agent_message"
    assert agent_message.content == "Test message content"


def test_action_request_creation():
    """Test the creation of ActionRequest."""
    action_request = ActionRequest(
        step_id=str(uuid.uuid4()),
        plan_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        action="Review and approve",
        agent=BAgentType.PROCUREMENT,
    )
    assert action_request.action == "Review and approve"
    assert action_request.agent == BAgentType.PROCUREMENT


def test_human_feedback_creation():
    """Test HumanFeedback creation."""
    human_feedback = HumanFeedback(
        step_id=str(uuid.uuid4()),
        plan_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        approved=True,
        human_feedback="Looks good!",
    )
    assert human_feedback.approved is True
    assert human_feedback.human_feedback == "Looks good!"


def test_plan_initialization():
    """Test Plan model initialization."""
    plan = Plan(
        session_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        initial_goal="Complete document processing",
    )
    assert plan.data_type == "plan"
    assert plan.initial_goal == "Complete document processing"
    assert plan.overall_status == PlanStatus.in_progress


def test_step_defaults():
    """Test default values for Step model."""
    step = Step(
        plan_id=str(uuid.uuid4()),
        action="Prepare report",
        agent=BAgentType.GENERIC,
        session_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )
    assert step.status == StepStatus.planned
    assert step.human_approval_status == HumanFeedbackStatus.requested
