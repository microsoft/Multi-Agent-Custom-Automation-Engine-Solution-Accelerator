# src/backend/tests/agents/test_human.py
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Adjust sys.path so that the project root is found.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Set required environment variables.
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["APPLICATIONINSIGHTS_INSTRUMENTATION_KEY"] = "mock-instrumentation-key"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Patch azure module so that event_utils imports correctly.
sys.modules["azure.monitor.events.extension"] = MagicMock()

from autogen_core.base._agent_instantiation import AgentInstantiationContext
dummy_runtime = MagicMock()
dummy_agent_id = "dummy_agent_id"


@pytest.fixture(autouse=True)
def patch_instantiation_context(monkeypatch):
    monkeypatch.setattr(AgentInstantiationContext, "current_runtime", lambda: dummy_runtime)
    monkeypatch.setattr(AgentInstantiationContext, "current_agent_id", lambda: dummy_agent_id)


# --- Patch ApprovalRequest so that required fields get default values ---
from src.backend.models.messages import ApprovalRequest as RealApprovalRequest, Plan


class DummyApprovalRequest(RealApprovalRequest):
    def __init__(self, **data):
        # Provide default values for missing fields.
        data.setdefault("action", "dummy_action")
        data.setdefault("agent", "dummy_agent")
        super().__init__(**data)


@pytest.fixture(autouse=True)
def patch_approval_request(monkeypatch):
    monkeypatch.setattr("src.backend.agents.human.ApprovalRequest", DummyApprovalRequest)


# Now import the module under test.
from autogen_core.base import MessageContext, AgentId
from src.backend.agents.human import HumanAgent
from src.backend.models.messages import HumanFeedback, Step, StepStatus, BAgentType


# Define a minimal dummy MessageContext implementation.
class DummyMessageContext(MessageContext):
    def __init__(self, sender="dummy_sender", topic_id="dummy_topic", is_rpc=False, cancellation_token=None):
        self.sender = sender
        self.topic_id = topic_id
        self.is_rpc = is_rpc
        self.cancellation_token = cancellation_token


# Define a fake memory implementation.
class FakeMemory:
    def __init__(self):
        self.added_items = []
        self.updated_steps = []
        self.fake_step = None

    async def get_step(self, step_id: str, session_id: str) -> Step:
        return self.fake_step  # Controlled by the test

    async def update_step(self, step: Step):
        self.updated_steps.append(step)
        return

    async def add_item(self, item):
        self.added_items.append(item)
        return

    async def get_plan_by_session(self, session_id: str) -> Plan:
        # Import Plan here to avoid circular import issues.
        from src.backend.models.messages import Plan, PlanStatus
        return Plan(
            id="plan123",
            session_id=session_id,
            user_id="test_user",
            initial_goal="Test goal",
            overall_status=PlanStatus.in_progress,
            source="HumanAgent",
            summary="Test summary",
            human_clarification_response=None,
        )


# Fixture to create a HumanAgent instance with fake memory.
@pytest.fixture
def human_agent():
    fake_memory = FakeMemory()
    user_id = "test_user"
    group_chat_manager_id = AgentId("group_chat_manager", "session123")
    agent = HumanAgent(memory=fake_memory, user_id=user_id, group_chat_manager_id=group_chat_manager_id)
    return agent, fake_memory


# ------------------- Existing Tests -------------------
def test_human_agent_init():
    fake_memory = MagicMock()
    user_id = "test_user"
    group_chat_manager_id = AgentId("group_chat_manager", "session123")
    agent = HumanAgent(memory=fake_memory, user_id=user_id, group_chat_manager_id=group_chat_manager_id)
    assert agent.user_id == user_id
    assert agent.group_chat_manager_id == group_chat_manager_id
    assert agent._memory == fake_memory


@pytest.mark.asyncio
async def test_handle_step_feedback_no_step_found(human_agent):
    """
    Test the case where no step is found.
    Expect that the method logs the "No step found" message and returns without updating.
    """
    agent, fake_memory = human_agent
    feedback = HumanFeedback(
        session_id="session123",
        step_id="nonexistent",
        plan_id="plan123",
        approved=True,
        human_feedback="Good job!"
    )
    fake_memory.get_step = AsyncMock(return_value=None)
    fake_memory.update_step = AsyncMock()
    fake_memory.add_item = AsyncMock()
    ctx = DummyMessageContext()
    with patch("src.backend.agents.human.logging.info") as mock_log:
        await agent.handle_step_feedback(feedback, ctx)
        mock_log.assert_called_with("No step found with id: nonexistent")
    fake_memory.update_step.assert_not_called()
    fake_memory.add_item.assert_not_called()


@pytest.mark.asyncio
async def test_handle_step_feedback_update_exception(human_agent):
    """
    Test that if update_step raises an exception, the exception propagates.
    """
    agent, fake_memory = human_agent
    fake_step = Step(
        id="step999",
        plan_id="plan999",
        action="Do something",
        agent=BAgentType.human_agent,
        status=StepStatus.planned,
        session_id="session999",
        user_id="test_user",
        human_feedback=None,
        human_approval_status="requested"
    )
    fake_memory.fake_step = fake_step
    fake_memory.get_step = AsyncMock(return_value=fake_step)
    fake_memory.update_step = AsyncMock(side_effect=Exception("Update failed"))
    fake_memory.add_item = AsyncMock()
    feedback = HumanFeedback(
        session_id="session999",
        step_id="step999",
        plan_id="plan999",
        approved=True,
        human_feedback="Feedback"
    )
    ctx = DummyMessageContext()
    with pytest.raises(Exception, match="Update failed"):
        await agent.handle_step_feedback(feedback, ctx)


@pytest.mark.asyncio
async def test_handle_step_feedback_add_item_exception(human_agent):
    """
    Test that if add_item (for AgentMessage) raises an exception, the exception propagates.
    """
    agent, fake_memory = human_agent
    fake_step = Step(
        id="step888",
        plan_id="plan888",
        action="Test action",
        agent=BAgentType.human_agent,
        status=StepStatus.planned,
        session_id="session888",
        user_id="test_user",
        human_feedback=None,
        human_approval_status="requested"
    )
    fake_memory.fake_step = fake_step
    fake_memory.get_step = AsyncMock(return_value=fake_step)
    fake_memory.update_step = AsyncMock()
    fake_memory.add_item = AsyncMock(side_effect=Exception("AddItem failed"))
    feedback = HumanFeedback(
        session_id="session888",
        step_id="step888",
        plan_id="plan888",
        approved=True,
        human_feedback="Test feedback"
    )
    ctx = DummyMessageContext()
    with pytest.raises(Exception, match="AddItem failed"):
        await agent.handle_step_feedback(feedback, ctx)
