"""Messages from the backend to the frontend via WebSocket (agent_framework variant)."""

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# Use the agent-framework friendly models (previously from messages_kernel)
from common.models.messages_af import AgentMessageType
from af.models.models import MPlan, PlanStatus


# ---------------------------------------------------------------------------
# Dataclass message payloads
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AgentMessage:
    """Message from the backend to the frontend via WebSocket."""
    agent_name: str
    timestamp: str
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentStreamStart:
    """Start of a streaming message."""
    agent_name: str


@dataclass(slots=True)
class AgentStreamEnd:
    """End of a streaming message."""
    agent_name: str


@dataclass(slots=True)
class AgentMessageStreaming:
    """Streaming chunk from an agent."""
    agent_name: str
    content: str
    is_final: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentToolMessage:
    """Message representing that an agent produced one or more tool calls."""
    agent_name: str
    tool_calls: List["AgentToolCall"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentToolCall:
    """A single tool invocation."""
    tool_name: str
    arguments: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlanApprovalRequest:
    """Request for plan approval from the frontend."""
    plan: MPlan
    status: PlanStatus
    context: dict | None = None


@dataclass(slots=True)
class PlanApprovalResponse:
    """Response for plan approval from the frontend."""
    m_plan_id: str
    approved: bool
    feedback: str | None = None
    plan_id: str | None = None


@dataclass(slots=True)
class ReplanApprovalRequest:
    """Request for replan approval from the frontend."""
    new_plan: MPlan
    reason: str
    context: dict | None = None


@dataclass(slots=True)
class ReplanApprovalResponse:
    """Response for replan approval from the frontend."""
    plan_id: str
    approved: bool
    feedback: str | None = None


@dataclass(slots=True)
class UserClarificationRequest:
    """Request for user clarification from the frontend."""
    question: str
    request_id: str


@dataclass(slots=True)
class UserClarificationResponse:
    """Response for user clarification from the frontend."""
    request_id: str
    answer: str = ""
    plan_id: str = ""
    m_plan_id: str = ""


@dataclass(slots=True)
class FinalResultMessage:
    """Final result message from the backend to the frontend."""
    content: str
    status: str = "completed"
    timestamp: Optional[float] = None
    summary: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "content": self.content,
            "status": self.status,
            "timestamp": self.timestamp or time.time(),
        }
        if self.summary:
            data["summary"] = self.summary
        return data


# ---------------------------------------------------------------------------
# Pydantic model replacing the previous KernelBaseModel
# ---------------------------------------------------------------------------

class ApprovalRequest(BaseModel):
    """Message sent to HumanAgent to request approval for a step."""
    step_id: str
    plan_id: str
    session_id: str
    user_id: str
    action: str
    agent_name: str

    def to_dict(self) -> Dict[str, Any]:
        # Consistent with dataclass pattern
        return self.model_dump()


@dataclass(slots=True)
class AgentMessageResponse:
    """Response message representing an agent's message (stream or final)."""
    plan_id: str
    agent: str
    content: str
    agent_type: AgentMessageType
    is_final: bool = False
    raw_data: str | None = None
    streaming_message: str | None = None


@dataclass(slots=True)
class TimeoutNotification:
    """Notification about a timeout (approval or clarification)."""
    timeout_type: str          # "approval" or "clarification"
    request_id: str            # plan_id or request_id
    message: str               # description
    timestamp: float           # epoch time
    timeout_duration: float    # seconds waited

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeout_type": self.timeout_type,
            "request_id": self.request_id,
            "message": self.message,
            "timestamp": self.timestamp,
            "timeout_duration": self.timeout_duration
        }


class WebsocketMessageType(str, Enum):
    """Types of WebSocket messages."""
    SYSTEM_MESSAGE = "system_message"
    AGENT_MESSAGE = "agent_message"
    AGENT_STREAM_START = "agent_stream_start"
    AGENT_STREAM_END = "agent_stream_end"
    AGENT_MESSAGE_STREAMING = "agent_message_streaming"
    AGENT_TOOL_MESSAGE = "agent_tool_message"
    PLAN_APPROVAL_REQUEST = "plan_approval_request"
    PLAN_APPROVAL_RESPONSE = "plan_approval_response"
    REPLAN_APPROVAL_REQUEST = "replan_approval_request"
    REPLAN_APPROVAL_RESPONSE = "replan_approval_response"
    USER_CLARIFICATION_REQUEST = "user_clarification_request"
    USER_CLARIFICATION_RESPONSE = "user_clarification_response"
    FINAL_RESULT_MESSAGE = "final_result_message"
    TIMEOUT_NOTIFICATION = "timeout_notification"

