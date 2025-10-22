"""
Agent Framework model equivalents for former agent framework -backed data models.

"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DataType(str, Enum):
    session = "session"
    plan = "plan"
    step = "step"
    agent_message = "agent_message"
    team_config = "team_config"
    user_current_team = "user_current_team"
    m_plan = "m_plan"
    m_plan_message = "m_plan_message"


class AgentType(str, Enum):
    HUMAN = "Human_Agent"
    HR = "Hr_Agent"
    MARKETING = "Marketing_Agent"
    PROCUREMENT = "Procurement_Agent"
    PRODUCT = "Product_Agent"
    GENERIC = "Generic_Agent"
    TECH_SUPPORT = "Tech_Support_Agent"
    GROUP_CHAT_MANAGER = "Group_Chat_Manager"
    PLANNER = "Planner_Agent"
    # Extend as needed


class StepStatus(str, Enum):
    planned = "planned"
    awaiting_feedback = "awaiting_feedback"
    approved = "approved"
    rejected = "rejected"
    action_requested = "action_requested"
    completed = "completed"
    failed = "failed"


class PlanStatus(str, Enum):
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"
    approved = "approved"
    created = "created"


class HumanFeedbackStatus(str, Enum):
    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"


class MessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    function = "function"


class AgentMessageType(str, Enum):
    # Removed trailing commas to avoid tuple enum values
    HUMAN_AGENT = "Human_Agent"
    AI_AGENT = "AI_Agent"


# ---------------------------------------------------------------------------
# Base Models
# ---------------------------------------------------------------------------

class BaseDataModel(BaseModel):
    """Base data model with common fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMessage(BaseDataModel):
    """Base class for messages sent between agents."""
    data_type: Literal[DataType.agent_message] = DataType.agent_message
    plan_id: str
    content: str
    source: str
    step_id: Optional[str] = None


class Session(BaseDataModel):
    """Represents a user session."""
    data_type: Literal[DataType.session] = DataType.session
    user_id: str
    current_status: str
    message_to_user: Optional[str] = None


class UserCurrentTeam(BaseDataModel):
    """Represents the current team of a user."""
    data_type: Literal[DataType.user_current_team] = DataType.user_current_team
    user_id: str
    team_id: str


class Plan(BaseDataModel):
    """Represents a plan containing multiple steps."""
    data_type: Literal[DataType.plan] = DataType.plan
    plan_id: str
    user_id: str
    initial_goal: str
    overall_status: PlanStatus = PlanStatus.in_progress
    approved: bool = False
    source: str = AgentType.PLANNER.value
    m_plan: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    team_id: Optional[str] = None
    streaming_message: Optional[str] = None
    human_clarification_request: Optional[str] = None
    human_clarification_response: Optional[str] = None


class Step(BaseDataModel):
    """Represents an individual step (task) within a plan."""
    data_type: Literal[DataType.step] = DataType.step
    plan_id: str
    user_id: str
    action: str
    agent: AgentType
    status: StepStatus = StepStatus.planned
    agent_reply: Optional[str] = None
    human_feedback: Optional[str] = None
    human_approval_status: Optional[HumanFeedbackStatus] = HumanFeedbackStatus.requested
    updated_action: Optional[str] = None


class TeamSelectionRequest(BaseDataModel):
    """Request model for team selection."""
    team_id: str


class TeamAgent(BaseModel):
    """Represents an agent within a team."""
    input_key: str
    type: str
    name: str
    deployment_name: str
    system_message: str = ""
    description: str = ""
    icon: str
    index_name: str = ""
    use_rag: bool = False
    use_mcp: bool = False
    use_bing: bool = False
    use_reasoning: bool = False
    coding_tools: bool = False


class StartingTask(BaseModel):
    """Represents a starting task for a team."""
    id: str
    name: str
    prompt: str
    created: str
    creator: str
    logo: str


class TeamConfiguration(BaseDataModel):
    """Represents a team configuration stored in the database."""
    team_id: str
    data_type: Literal[DataType.team_config] = DataType.team_config
    session_id: str  # partition key
    name: str
    status: str
    created: str
    created_by: str
    agents: List[TeamAgent] = Field(default_factory=list)
    description: str = ""
    logo: str = ""
    plan: str = ""
    starting_tasks: List[StartingTask] = Field(default_factory=list)
    user_id: str  # who uploaded this configuration


class PlanWithSteps(Plan):
    """Plan model that includes the associated steps."""
    steps: List[Step] = Field(default_factory=list)
    total_steps: int = 0
    planned: int = 0
    awaiting_feedback: int = 0
    approved: int = 0
    rejected: int = 0
    action_requested: int = 0
    completed: int = 0
    failed: int = 0

    def update_step_counts(self) -> None:
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
        if self.total_steps > 0 and (self.completed + self.failed) == self.total_steps:
            self.overall_status = PlanStatus.completed


class InputTask(BaseModel):
    """Message representing the initial input task from the user."""
    session_id: str
    description: str


class UserLanguage(BaseModel):
    language: str


class AgentMessageData(BaseDataModel):
    """Represents a multi-plan agent message."""
    data_type: Literal[DataType.m_plan_message] = DataType.m_plan_message
    plan_id: str
    user_id: str
    agent: str
    m_plan_id: Optional[str] = None
    agent_type: AgentMessageType = AgentMessageType.AI_AGENT
    content: str
    raw_data: str
    steps: List[Any] = Field(default_factory=list)
    next_steps: List[Any] = Field(default_factory=list)
