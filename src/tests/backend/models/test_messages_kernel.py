import sys
import os
import types
import pytest
from datetime import datetime

# --- Stub out semantic_kernel.kernel_pydantic.Field and KernelBaseModel ---
pyd_pkg = types.ModuleType("semantic_kernel.kernel_pydantic")

def Field(*args, **kwargs):
    default = kwargs.get("default", None)
    return default

class KernelBaseModel:
    def __init__(self, **data):
        for k, v in data.items():
            setattr(self, k, v)
    def dict(self):
        return self.__dict__

pyd_pkg.Field = Field
pyd_pkg.KernelBaseModel = KernelBaseModel
sys.modules["semantic_kernel.kernel_pydantic"] = pyd_pkg

# --- Ensure src is on PYTHONPATH ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# --- Now import your models ---
from backend.models.messages_kernel import (
    GetHumanInputMessage,
    GroupChatMessage,
    DataType,
    AgentType,
    StepStatus,
    PlanStatus,
    HumanFeedbackStatus,
    MessageRole,
    ChatMessage,
    StoredMessage,
    AgentMessage,
    Session,
    Plan,
    Step,
    ThreadIdAgent,
    AzureIdAgent,
    PlanWithSteps,
)

def test_get_human_input_message():
    msg = GetHumanInputMessage(content="Need your input")
    assert msg.content == "Need your input"

def test_group_chat_message_str():
    msg = GroupChatMessage(body={"content": "Hello"}, source="tester", session_id="abc123")
    assert "GroupChatMessage" in str(msg)
    assert "tester" in str(msg)
    assert "Hello" in str(msg)

def test_chat_message_to_semantic_kernel_dict():
    chat_msg = ChatMessage(role=MessageRole.user, content="Test message", metadata={})
    sk_dict = chat_msg.to_semantic_kernel_dict()
    assert sk_dict["role"] == "user"
    assert sk_dict["content"] == "Test message"
    assert isinstance(sk_dict["metadata"], dict)

def test_stored_message_to_chat_message():
    stored = StoredMessage(
        session_id="s1", user_id="u1", role=MessageRole.assistant, content="reply",
        plan_id="p1", step_id="step1", source="source", metadata={}
    )
    chat = stored.to_chat_message()
    assert chat.role == MessageRole.assistant
    assert chat.content == "reply"
    assert chat.metadata["plan_id"] == "p1"

# def test_agent_message_fields():
#     agent_msg = AgentMessage(
#         session_id="s", user_id="u", plan_id="p", content="hi", source="system"
#     )
#     # Use actual defined enum
#     agent_msg.data_type = DataType.AGENT
#     assert agent_msg.data_type == DataType.AGENT
#     assert agent_msg.content == "hi"

# def test_session_defaults():
#     session = Session(user_id="u", current_status="active")
#     session.data_type = DataType.SESSION_DATA
#     assert session.data_type == DataType.SESSION_DATA
#     assert session.current_status == "active"


def test_plan_status_and_source():
    plan = Plan(session_id="s", user_id="u", initial_goal="goal")
    assert plan.overall_status == PlanStatus.in_progress
    assert plan.source == AgentType.PLANNER

def test_step_defaults():
    step = Step(
        plan_id="p",
        session_id="s",
        user_id="u",
        action="act",
        agent=AgentType.HUMAN,
    )
    assert step.status == StepStatus.planned
    assert step.human_approval_status == HumanFeedbackStatus.requested

def test_azure_id_agent():
    azure = AzureIdAgent(
        session_id="s", user_id="u", action="a", agent=AgentType.HR, agent_id="a1"
    )
    assert azure.agent == AgentType.HR
    assert azure.agent_id == "a1"

def test_plan_with_steps_update_counts():
    steps = [
        Step(
            plan_id="p",
            session_id="s",
            user_id="u",
            action="a1",
            agent=AgentType.HR,
            status=StepStatus.planned,
        ),
        Step(
            plan_id="p",
            session_id="s",
            user_id="u",
            action="a2",
            agent=AgentType.HR,
            status=StepStatus.completed,
        ),
        Step(
            plan_id="p",
            session_id="s",
            user_id="u",
            action="a3",
            agent=AgentType.HR,
            status=StepStatus.failed,
        ),
    ]
    plan_with_steps = PlanWithSteps(
        session_id="s", user_id="u", initial_goal="goal", steps=steps
    )
    plan_with_steps.update_step_counts()
    assert plan_with_steps.total_steps == 3
    assert plan_with_steps.planned == 1
    assert plan_with_steps.completed == 1
    assert plan_with_steps.failed == 1

def test_thread_id_agent():
    thread = ThreadIdAgent(
        session_id="s", user_id="u", action="a", agent=AgentType.HR, thread_id="t1"
    )
    assert thread.agent == AgentType.HR
    assert thread.thread_id == "t1"
