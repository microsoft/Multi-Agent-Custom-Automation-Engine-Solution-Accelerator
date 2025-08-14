import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from semantic_kernel.kernel_pydantic import Field, KernelBaseModel


# Classes specifically for handling runtime interrupts
class GetHumanInputMessage(KernelBaseModel):
    """Message requesting input from a human."""

    content: str


class GroupChatMessage(KernelBaseModel):
    """Message in a group chat."""

    body: Any
    source: str
    session_id: str
    target: str = ""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    def __str__(self):
        content = self.body.content if hasattr(self.body, "content") else str(self.body)
        return f"GroupChatMessage(source={self.source}, content={content})"


class DataType(str, Enum):
    """Enumeration of possible data types for documents in the database."""

    session = "session"
    plan = "plan"
    step = "step"
    message = "message"


class AgentType(str, Enum):
    """Enumeration of agent types."""

    HUMAN = "Human_Agent"
    HR = "Hr_Agent"
    MARKETING = "Marketing_Agent"
    PROCUREMENT = "Procurement_Agent"
    PRODUCT = "Product_Agent"
    GENERIC = "Generic_Agent"
    TECH_SUPPORT = "Tech_Support_Agent"
    GROUP_CHAT_MANAGER = "Group_Chat_Manager"
    PLANNER = "Planner_Agent"

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
    """Enumeration of human feedback statuses."""

    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"


class MessageRole(str, Enum):
    """Message roles compatible with Semantic Kernel."""

    system = "system"
    user = "user"
    assistant = "assistant"
    function = "function"


class BaseDataModel(KernelBaseModel):
    """Base data model with common fields."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


# Basic message class for Semantic Kernel compatibility
class ChatMessage(KernelBaseModel):
    """Base class for chat messages in Semantic Kernel format."""

    role: MessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_semantic_kernel_dict(self) -> Dict[str, Any]:
        """Convert to format expected by Semantic Kernel."""
        return {
            "role": self.role.value,
            "content": self.content,
            "metadata": self.metadata,
        }


class StoredMessage(BaseDataModel):
    """Message stored in the database with additional metadata."""

    data_type: Literal["message"] = Field("message", Literal=True)
    session_id: str
    user_id: str
    role: MessageRole
    content: str
    plan_id: Optional[str] = None
    step_id: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_chat_message(self) -> ChatMessage:
        """Convert to ChatMessage format."""
        return ChatMessage(
            role=self.role,
            content=self.content,
            metadata={
                "source": self.source,
                "plan_id": self.plan_id,
                "step_id": self.step_id,
                "session_id": self.session_id,
                "user_id": self.user_id,
                "message_id": self.id,
                **self.metadata,
            },
        )


class AgentMessage(BaseDataModel):
    """Base class for messages sent between agents."""

    data_type: Literal["agent_message"] = Field("agent_message", Literal=True)
    session_id: str
    user_id: str
    plan_id: str
    content: str
    source: str
    step_id: Optional[str] = None


class Session(BaseDataModel):
    """Represents a user session."""

    data_type: Literal["session"] = Field("session", Literal=True)
    user_id: str
    current_status: str
    message_to_user: Optional[str] = None


class Plan(BaseDataModel):
    """Represents a plan containing multiple steps."""

    data_type: Literal["plan"] = Field("plan", Literal=True)
    session_id: str
    user_id: str
    initial_goal: str
    overall_status: PlanStatus = PlanStatus.in_progress
    source: str = AgentType.PLANNER.value
    summary: Optional[str] = None
    human_clarification_request: Optional[str] = None
    human_clarification_response: Optional[str] = None


class Step(BaseDataModel):
    """Represents an individual step (task) within a plan."""

    data_type: Literal["step"] = Field("step", Literal=True)
    plan_id: str
    session_id: str  # Partition key
    user_id: str
    action: str
    agent: AgentType
    status: StepStatus = StepStatus.planned
    agent_reply: Optional[str] = None
    human_feedback: Optional[str] = None
    human_approval_status: Optional[HumanFeedbackStatus] = HumanFeedbackStatus.requested
    updated_action: Optional[str] = None


class ThreadIdAgent(BaseDataModel):
    """Represents an individual thread_id."""

    data_type: Literal["thread"] = Field("thread", Literal=True)
    session_id: str  # Partition key
    user_id: str
    thread_id: str


class AzureIdAgent(BaseDataModel):
    """Represents an individual thread_id."""

    data_type: Literal["agent"] = Field("agent", Literal=True)
    session_id: str  # Partition key
    user_id: str
    action: str
    agent: AgentType
    agent_id: str


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
class InputTask(KernelBaseModel):
    """Message representing the initial input task from the user."""

    session_id: str
    description: str  # Initial goal


class UserLanguage(KernelBaseModel):
    language: str


class ApprovalRequest(KernelBaseModel):
    """Message sent to HumanAgent to request approval for a step."""

    step_id: str
    plan_id: str
    session_id: str
    user_id: str
    action: str
    agent: AgentType


class HumanFeedback(KernelBaseModel):
    """Message containing human feedback on a step."""

    step_id: Optional[str] = None
    plan_id: str
    session_id: str
    approved: bool
    human_feedback: Optional[str] = None
    updated_action: Optional[str] = None


class HumanClarification(KernelBaseModel):
    """Message containing human clarification on a plan."""

    plan_id: str
    session_id: str
    human_clarification: str


class ActionRequest(KernelBaseModel):
    """Message sent to an agent to perform an action."""

    step_id: str
    plan_id: str
    session_id: str
    action: str
    agent: AgentType


class ActionResponse(KernelBaseModel):
    """Message containing the response from an agent after performing an action."""

    step_id: str
    plan_id: str
    session_id: str
    result: str
    status: StepStatus  # Should be 'completed' or 'failed'


class PlanStateUpdate(KernelBaseModel):
    """Optional message for updating the plan state."""

    plan_id: str
    session_id: str
    overall_status: PlanStatus


# Semantic Kernel chat message handler
class SKChatHistory:
    """Helper class to work with Semantic Kernel chat history."""

    def __init__(self, memory_store):
        """Initialize with a memory store."""
        self.memory_store = memory_store

    async def add_system_message(
        self, session_id: str, user_id: str, content: str, **kwargs
    ):
        """Add a system message to the chat history."""
        message = StoredMessage(
            session_id=session_id,
            user_id=user_id,
            role=MessageRole.system,
            content=content,
            **kwargs,
        )
        await self._store_message(message)
        return message

    async def add_user_message(
        self, session_id: str, user_id: str, content: str, **kwargs
    ):
        """Add a user message to the chat history."""
        message = StoredMessage(
            session_id=session_id,
            user_id=user_id,
            role=MessageRole.user,
            content=content,
            **kwargs,
        )
        await self._store_message(message)
        return message

    async def add_assistant_message(
        self, session_id: str, user_id: str, content: str, **kwargs
    ):
        """Add an assistant message to the chat history."""
        message = StoredMessage(
            session_id=session_id,
            user_id=user_id,
            role=MessageRole.assistant,
            content=content,
            **kwargs,
        )
        await self._store_message(message)
        return message

    async def add_function_message(
        self, session_id: str, user_id: str, content: str, **kwargs
    ):
        """Add a function result message to the chat history."""
        message = StoredMessage(
            session_id=session_id,
            user_id=user_id,
            role=MessageRole.function,
            content=content,
            **kwargs,
        )
        await self._store_message(message)
        return message

    async def _store_message(self, message: StoredMessage):
        """Store a message in the memory store."""
        # Convert to dictionary for storage
        message_dict = message.model_dump()

        # Use memory store to save the message
        # This assumes your memory store has an upsert_async method that takes a collection name and data
        await self.memory_store.upsert_async(
            f"message_{message.session_id}", message_dict
        )

    async def get_chat_history(
        self, session_id: str, limit: int = 100
    ) -> List[ChatMessage]:
        """Retrieve chat history for a session."""
        # Query messages from the memory store
        # This assumes your memory store has a method to query items
        messages = await self.memory_store.query_items(
            f"message_{session_id}", limit=limit
        )

        # Convert to ChatMessage objects
        chat_messages = []
        for msg_dict in messages:
            msg = StoredMessage.model_validate(msg_dict)
            chat_messages.append(msg.to_chat_message())

        return chat_messages

    async def clear_history(self, session_id: str):
        """Clear chat history for a session."""
        # This assumes your memory store has a method to delete a collection
        await self.memory_store.delete_collection_async(f"message_{session_id}")


# Define the expected structure of the LLM response
class PlannerResponseStep(KernelBaseModel):
    action: str
    agent: AgentType


class PlannerResponsePlan(KernelBaseModel):
    initial_goal: str
    steps: List[PlannerResponseStep]
    summary_plan_and_steps: str
    human_clarification_request: Optional[str] = None


# Helper class for Semantic Kernel function calling
class SKFunctionRegistry:
    """Helper class to register and execute functions in Semantic Kernel."""

    def __init__(self, kernel):
        """Initialize with a Semantic Kernel instance."""
        self.kernel = kernel
        self.functions = {}

    def register_function(self, name: str, function_obj, description: str = None):
        """Register a function with the kernel."""
        self.functions[name] = {
            "function": function_obj,
            "description": description or "",
        }

        # Register with the kernel's function registry
        # The exact implementation depends on Semantic Kernel's API
        # This is a placeholder - adjust according to the actual SK API
        if hasattr(self.kernel, "register_function"):
            self.kernel.register_function(name, function_obj, description)

    async def execute_function(self, name: str, **kwargs):
        """Execute a registered function."""
        if name not in self.functions:
            raise ValueError(f"Function {name} not registered")

        function_obj = self.functions[name]["function"]
        # Execute the function
        # This might vary based on SK's execution model
        return await function_obj(**kwargs)
