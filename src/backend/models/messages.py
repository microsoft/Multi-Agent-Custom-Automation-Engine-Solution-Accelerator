import uuid
from enum import Enum
from typing import Literal, Optional

from autogen_core.components.models import (
    AssistantMessage,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from pydantic import BaseModel, Field


class DataType(str, Enum):
    """Enumeration of possible data types for documents in the database."""

    session = "session"
    plan = "plan"
    step = "step"


class BAgentType(str, Enum):
    """Enumeration of agent types."""

    human_agent = "HumanAgent"
    hr_agent = "HrAgent"
    marketing_agent = "MarketingAgent"
    procurement_agent = "ProcurementAgent"
    product_agent = "ProductAgent"
    generic_agent = "GenericAgent"
    tech_support_agent = "TechSupportAgent"
    group_chat_manager = "GroupChatManager"
    planner_agent = "PlannerAgent"

    # Add other agents as needed


class StepStatus(str, Enum):
    """Enumeration of possible statuses for a step."""

    planned = "planned"
    awaiting_feedback = "awaiting_feedback"
    approved = "approved"
    rejected = "rejected"
    action_requested = "action_requested"
    completed = "completed"
    failed = "failed"


class PlanStatus(str, Enum):
    """Enumeration of possible statuses for a plan."""

    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class HumanFeedbackStatus(str, Enum):
    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"


class BaseDataModel(BaseModel):
    """Base data model with common fields."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: Optional[int] = None


# Session model


class AgentMessage(BaseModel):
    """Base class for messages sent between agents."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_type: Literal["agent_message"] = Field("agent_message", Literal=True)
    session_id: str
    user_id: str
    plan_id: str
    content: str
    source: str
    ts: Optional[int] = None
    step_id: Optional[str] = None


class Session(BaseDataModel):
    """Represents a user session."""

    data_type: Literal["session"] = Field("session", Literal=True)
    current_status: str
    message_to_user: Optional[str] = None
    ts: Optional[int] = None


# plan model


class Plan(BaseDataModel):
    """Represents a plan containing multiple steps."""

    data_type: Literal["plan"] = Field("plan", Literal=True)
    session_id: str
    user_id: str
    initial_goal: str
    overall_status: PlanStatus = PlanStatus.in_progress
    source: str = "PlannerAgent"
    summary: Optional[str] = None
    human_clarification_request: Optional[str] = None
    human_clarification_response: Optional[str] = None
    ts: Optional[int] = None


# Step model


class Step(BaseDataModel):
    """Represents an individual step (task) within a plan."""

    data_type: Literal["step"] = Field("step", Literal=True)
    plan_id: str
    action: str
    agent: BAgentType
    status: StepStatus = StepStatus.planned
    agent_reply: Optional[str] = None
    human_feedback: Optional[str] = None
    human_approval_status: Optional[HumanFeedbackStatus] = HumanFeedbackStatus.requested
    updated_action: Optional[str] = None
    session_id: (
        str  # Added session_id to the Step model to partition the steps by session_id
    )
    user_id: str
    ts: Optional[int] = None


# Plan with steps
class PlanWithSteps(Plan):
    steps: list[Step] = []
    total_steps: int = 0
    planned: int = 0
    awaiting_feedback: int = 0
    approved: int = 0
    rejected: int = 0
    action_requested: int = 0
    completed: int = 0
    failed: int = 0

    def update_step_counts(self):
        """Update the counts of steps by their status."""
        status_counts = {
            StepStatus.planned: 0,
            StepStatus.awaiting_feedback: 0,
            StepStatus.approved: 0,
            StepStatus.rejected: 0,
            StepStatus.action_requested: 0,
            StepStatus.completed: 0,
            StepStatus.failed: 0,
        }

        for step in self.steps:
            status_counts[step.status] += 1

        self.total_steps = len(self.steps)
        self.planned = status_counts[StepStatus.planned]
        self.awaiting_feedback = status_counts[StepStatus.awaiting_feedback]
        self.approved = status_counts[StepStatus.approved]
        self.rejected = status_counts[StepStatus.rejected]
        self.action_requested = status_counts[StepStatus.action_requested]
        self.completed = status_counts[StepStatus.completed]
        self.failed = status_counts[StepStatus.failed]

        # Mark the plan as complete if the sum of completed and failed steps equals the total number of steps
        if self.completed + self.failed == self.total_steps:
            self.overall_status = PlanStatus.completed


# Message classes for communication between agents
class InputTask(BaseModel):
    """Message representing the initial input task from the user."""

    session_id: str
    description: str  # Initial goal


class ApprovalRequest(BaseModel):
    """Message sent to HumanAgent to request approval for a step."""

    step_id: str
    plan_id: str
    session_id: str
    user_id: str
    action: str
    agent: BAgentType


class HumanFeedback(BaseModel):
    """Message containing human feedback on a step."""

    step_id: Optional[str] = None
    plan_id: str
    session_id: str
    approved: bool
    human_feedback: Optional[str] = None
    updated_action: Optional[str] = None


class HumanClarification(BaseModel):
    """Message containing human clarification on a plan."""

    plan_id: str
    session_id: str
    human_clarification: str


class ActionRequest(BaseModel):
    """Message sent to an agent to perform an action."""

    step_id: str
    plan_id: str
    session_id: str
    action: str
    agent: BAgentType


class ActionResponse(BaseModel):
    """Message containing the response from an agent after performing an action."""

    step_id: str
    plan_id: str
    session_id: str
    result: str
    status: StepStatus  # Should be 'completed' or 'failed'


# Additional message classes as needed


class PlanStateUpdate(BaseModel):
    """Optional message for updating the plan state."""

    plan_id: str
    session_id: str
    overall_status: PlanStatus


class GroupChatMessage(BaseModel):
    body: LLMMessage
    source: str
    session_id: str
    target: str = ""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        body_dict = self.body.to_dict()
        body_dict["type"] = self.body.__class__.__name__
        return {
            "body": body_dict,
            "source": self.source,
            "session_id": self.session_id,
            "target": self.target,
            "id": self.id,
        }

    @staticmethod
    def from_dict(data: dict) -> "GroupChatMessage":
        body_data = data["body"]
        body_type = body_data.pop("type")

        if body_type == "SystemMessage":
            body = SystemMessage.from_dict(body_data)
        elif body_type == "UserMessage":
            body = UserMessage.from_dict(body_data)
        elif body_type == "AssistantMessage":
            body = AssistantMessage.from_dict(body_data)
        elif body_type == "FunctionExecutionResultMessage":
            body = FunctionExecutionResultMessage.from_dict(body_data)
        else:
            raise ValueError(f"Unknown message type: {body_type}")

        return GroupChatMessage(
            body=body,
            source=data["source"],
            session_id=data["session_id"],
            target=data["target"],
            id=data["id"],
        )


class RequestToSpeak(BaseModel):
    pass

    def to_dict(self):
        return self.model_dump()
