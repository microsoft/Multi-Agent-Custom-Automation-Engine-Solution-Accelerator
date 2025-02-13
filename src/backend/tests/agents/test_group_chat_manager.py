import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock

# Adjust sys.path so that the project root is found.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Set required environment variables.
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Patch missing azure module so that event_utils imports without error.
sys.modules["azure.monitor.events.extension"] = MagicMock()


from autogen_core.base._agent_instantiation import AgentInstantiationContext


@pytest.fixture(autouse=True)
def dummy_agent_instantiation_context():
    token = AgentInstantiationContext.AGENT_INSTANTIATION_CONTEXT_VAR.set(("dummy_runtime", "dummy_agent_id"))
    yield
    AgentInstantiationContext.AGENT_INSTANTIATION_CONTEXT_VAR.reset(token)


# --- Import production classes ---
from src.backend.agents.group_chat_manager import GroupChatManager
from src.backend.models.messages import (
    AgentMessage,
    HumanFeedback,
    InputTask,
    Plan,
    PlanStatus,
    Step,
    StepStatus,
    HumanFeedbackStatus,
    BAgentType,
)
from autogen_core.base import AgentId, MessageContext


# --- Define a DummyMessageContext that supplies required parameters ---
class DummyMessageContext(MessageContext):
    def __init__(self):
        super().__init__(sender="dummy_sender", topic_id="dummy_topic", is_rpc=False, cancellation_token=None)


# --- Fake Memory implementation ---
class FakeMemory:
    def __init__(self):
        self.added_items = []
        self.updated_steps = []

    async def add_item(self, item: AgentMessage):
        self.added_items.append(item)

    async def update_step(self, step: Step):
        self.updated_steps.append(step)

    async def get_plan_by_session(self, session_id: str) -> Plan:
        return Plan.model_construct(
            id="plan1",
            session_id=session_id,
            user_id="user1",
            initial_goal="Test goal",
            overall_status=PlanStatus.in_progress,
            source="GroupChatManager",
            summary="Test summary",
            human_clarification_response="Plan feedback",
        )

    async def get_steps_by_plan(self, plan_id: str) -> list:
        step1 = Step.model_construct(
            id="step1",
            plan_id=plan_id,
            action="Action 1",
            agent=BAgentType.human_agent,
            status=StepStatus.planned,
            session_id="sess1",
            user_id="user1",
            human_feedback="",
            human_approval_status=HumanFeedbackStatus.requested,
        )
        step2 = Step.model_construct(
            id="step2",
            plan_id=plan_id,
            action="Action 2",
            agent=BAgentType.tech_support_agent,
            status=StepStatus.planned,
            session_id="sess1",
            user_id="user1",
            human_feedback="Existing feedback",
            human_approval_status=HumanFeedbackStatus.requested,
        )
        return [step1, step2]

    async def add_plan(self, plan: Plan):
        pass

    async def update_plan(self, plan: Plan):
        pass


# --- Fake send_message for GroupChatManager ---
async def fake_send_message(message, agent_id):
    return Plan.model_construct(
        id="plan1",
        session_id="sess1",
        user_id="user1",
        initial_goal="Test goal",
        overall_status=PlanStatus.in_progress,
        source="GroupChatManager",
        summary="Test summary",
        human_clarification_response="",
    )


# --- Fixture to create a GroupChatManager instance ---
@pytest.fixture
def group_chat_manager():
    mock_model_client = MagicMock()
    session_id = "sess1"
    user_id = "user1"
    fake_memory = FakeMemory()
    # Create a dummy agent_ids dictionary with valid enum values.
    agent_ids = {
        BAgentType.planner_agent: AgentId("planner_agent", session_id),
        BAgentType.human_agent: AgentId("human_agent", session_id),
        BAgentType.tech_support_agent: AgentId("tech_support_agent", session_id),
    }
    manager = GroupChatManager(
        model_client=mock_model_client,
        session_id=session_id,
        user_id=user_id,
        memory=fake_memory,
        agent_ids=agent_ids,
    )
    manager.send_message = AsyncMock(side_effect=fake_send_message)
    return manager, fake_memory


# --- To simulate a missing agent in a step, define a dummy subclass ---
class DummyStepMissingAgent(Step):
    @property
    def agent(self):
        return ""


# ---------------------- Tests ----------------------

@pytest.mark.asyncio
async def test_handle_input_task(group_chat_manager):
    manager, fake_memory = group_chat_manager
    # Use production InputTask via model_construct.
    input_task = InputTask.model_construct(description="Test input description", session_id="sess1")
    ctx = DummyMessageContext()
    plan = await manager.handle_input_task(input_task, ctx)
    # Verify an AgentMessage was added with the input description.
    assert any("Test input description" in item.content for item in fake_memory.added_items)
    assert plan.id == "plan1"


@pytest.mark.asyncio
async def test_handle_human_approval_feedback_specific_step(group_chat_manager):
    manager, fake_memory = group_chat_manager
    feedback = HumanFeedback.model_construct(session_id="sess1", plan_id="plan1", step_id="step1", approved=True, human_clarification="Approved")
    step = Step.model_construct(
        id="step1",
        plan_id="plan1",
        action="Action for step1",
        agent=BAgentType.human_agent,
        status=StepStatus.planned,
        session_id="sess1",
        user_id="user1",
        human_feedback="",
        human_approval_status=HumanFeedbackStatus.requested,
    )
    fake_memory.get_steps_by_plan = AsyncMock(return_value=[step])
    fake_memory.get_plan_by_session = AsyncMock(return_value=Plan.model_construct(
        id="plan1",
        session_id="sess1",
        user_id="user1",
        initial_goal="Goal",
        overall_status=PlanStatus.in_progress,
        source="GroupChatManager",
        summary="Test summary",
        human_clarification_response="Plan feedback",
    ))
    manager._update_step_status = AsyncMock()
    manager._execute_step = AsyncMock()
    await manager.handle_human_approval_feedback(feedback, DummyMessageContext())
    manager._update_step_status.assert_called_once()
    manager._execute_step.assert_called_once_with("sess1", step)


@pytest.mark.asyncio
async def test_handle_human_approval_feedback_all_steps(group_chat_manager):
    manager, fake_memory = group_chat_manager
    feedback = HumanFeedback.model_construct(session_id="sess1", plan_id="plan1", step_id="", approved=False, human_clarification="Rejected")
    step1 = Step.model_construct(
        id="step1",
        plan_id="plan1",
        action="Action 1",
        agent=BAgentType.tech_support_agent,
        status=StepStatus.planned,
        session_id="sess1",
        user_id="user1",
        human_feedback="",
        human_approval_status=HumanFeedbackStatus.requested,
    )
    step2 = Step.model_construct(
        id="step2",
        plan_id="plan1",
        action="Action 2",
        agent=BAgentType.human_agent,
        status=StepStatus.planned,
        session_id="sess1",
        user_id="user1",
        human_feedback="Existing",
        human_approval_status=HumanFeedbackStatus.requested,
    )
    fake_memory.get_steps_by_plan = AsyncMock(return_value=[step1, step2])
    fake_memory.get_plan_by_session = AsyncMock(return_value=Plan.model_construct(
        id="plan1",
        session_id="sess1",
        user_id="user1",
        initial_goal="Goal",
        overall_status=PlanStatus.in_progress,
        source="GroupChatManager",
        summary="Test summary",
        human_clarification_response="",
    ))
    manager._update_step_status = AsyncMock()
    manager._execute_step = AsyncMock()
    await manager.handle_human_approval_feedback(feedback, DummyMessageContext())
    # Expect _update_step_status to be called for each step
    assert manager._update_step_status.call_count == 2
    manager._execute_step.assert_not_called()


@pytest.mark.asyncio
async def test_update_step_status(group_chat_manager):
    manager, fake_memory = group_chat_manager
    step = Step.model_construct(
        id="step_update",
        plan_id="plan1",
        action="Test action",
        agent=BAgentType.human_agent,
        status=StepStatus.planned,
        session_id="sess1",
        user_id="user1",
        human_feedback="",
        human_approval_status=HumanFeedbackStatus.requested,
    )
    fake_memory.update_step = AsyncMock()
    await manager._update_step_status(step, True, "Positive feedback")
    assert step.status == StepStatus.completed
    assert step.human_feedback == "Positive feedback"
    fake_memory.update_step.assert_called_once_with(step)


@pytest.mark.asyncio
async def test_execute_step_non_human(group_chat_manager):
    manager, fake_memory = group_chat_manager
    step = Step.model_construct(
        id="step_nonhuman",
        plan_id="plan1",
        action="Perform diagnostic",
        agent=BAgentType.tech_support_agent,
        status=StepStatus.planned,
        session_id="sess1",
        user_id="user1",
        human_feedback="",
        human_approval_status=HumanFeedbackStatus.requested,
    )
    fake_memory.update_step = AsyncMock()
    manager.send_message = AsyncMock(return_value=Plan.model_construct(
        id="plan1",
        session_id="sess1",
        user_id="user1",
        initial_goal="Goal",
        overall_status=PlanStatus.in_progress,
        source="GroupChatManager",
        summary="Test summary",
        human_clarification_response="",
    ))
    fake_memory.get_plan_by_session = AsyncMock(return_value=Plan.model_construct(
        id="plan1",
        session_id="sess1",
        user_id="user1",
        initial_goal="Goal",
        overall_status=PlanStatus.in_progress,
        source="GroupChatManager",
        summary="Test summary",
        human_clarification_response="",
    ))
    fake_memory.get_steps_by_plan = AsyncMock(return_value=[step])
    await manager._execute_step("sess1", step)
    fake_memory.update_step.assert_called()
    manager.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_execute_step_human_agent(group_chat_manager):
    manager, fake_memory = group_chat_manager
    step = Step.model_construct(
        id="step_human",
        plan_id="plan1",
        action="Verify details",
        agent=BAgentType.human_agent,
        status=StepStatus.planned,
        session_id="sess1",
        user_id="user1",
        human_feedback="",
        human_approval_status=HumanFeedbackStatus.requested,
    )
    fake_memory.update_step = AsyncMock()
    manager.send_message = AsyncMock()
    fake_memory.get_plan_by_session = AsyncMock(return_value=Plan.model_construct(
        id="plan1",
        session_id="sess1",
        user_id="user1",
        initial_goal="Goal",
        overall_status=PlanStatus.in_progress,
        source="GroupChatManager",
        summary="Test summary",
        human_clarification_response="",
    ))
    fake_memory.get_steps_by_plan = AsyncMock(return_value=[step])
    await manager._execute_step("sess1", step)
    # For human agent, _execute_step should mark the step as complete and not call send_message.
    assert step.status == StepStatus.completed
    manager.send_message.assert_not_called()


# --- Test for missing agent error in _execute_step ---
@pytest.mark.asyncio
async def test_execute_step_missing_agent_raises(group_chat_manager):
    manager, fake_memory = group_chat_manager

    # Create a dummy step using a subclass that forces agent to be an empty string.
    class DummyStepMissingAgent(Step):
        @property
        def agent(self):
            return ""
    DummyStepMissingAgent.model_construct(
        id="step_missing",
        plan_id="plan1",
        action="Do something",
        agent=BAgentType.human_agent,  # initial value (will be overridden by the property)
        status=StepStatus.planned,
        session_id="sess1",
        user_id="user1",
        human_feedback="",
        human_approval_status=HumanFeedbackStatus.requested,
    )
