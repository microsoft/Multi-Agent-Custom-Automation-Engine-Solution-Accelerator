# src/backend/tests/agents/test_planner.py
import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

# --- Setup environment and module search path ---
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"
sys.modules["azure.monitor.events.extension"] = MagicMock()  # Patch missing azure module

# Ensure the project root is in sys.path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from autogen_core.base._agent_instantiation import AgentInstantiationContext


@pytest.fixture(autouse=True)
def patch_instantiation_context(monkeypatch):
    monkeypatch.setattr(AgentInstantiationContext, "current_runtime", lambda: "dummy_runtime")
    monkeypatch.setattr(AgentInstantiationContext, "current_agent_id", lambda: "dummy_agent_id")


# --- Imports from the module under test ---
from autogen_core.components.models import UserMessage
from autogen_core.base import MessageContext
from src.backend.agents.planner import PlannerAgent
from src.backend.models.messages import (
    BAgentType,
    InputTask,
    Plan,
    PlanStatus,
    Step,
    StepStatus,
    HumanFeedbackStatus,
)


class DummyMessageContext(MessageContext):
    def __init__(self, sender="dummy_sender", topic_id="dummy_topic", is_rpc=False, cancellation_token=None):
        self.sender = sender
        self.topic_id = topic_id
        self.is_rpc = is_rpc
        self.cancellation_token = cancellation_token


class FakeMemory:
    def __init__(self):
        self.added_plans = []
        self.added_steps = []
        self.added_items = []
        self.updated_plan = None
        self.updated_steps = []

    async def add_plan(self, plan):
        self.added_plans.append(plan)

    async def add_step(self, step):
        self.added_steps.append(step)

    async def add_item(self, item):
        self.added_items.append(item)

    async def update_plan(self, plan):
        self.updated_plan = plan

    async def update_step(self, step):
        self.updated_steps.append(step)

    async def get_plan_by_session(self, session_id: str) -> Plan:
        return Plan(
            id="plan_test",
            session_id=session_id,
            user_id="user_test",
            initial_goal="Test initial goal",
            overall_status=PlanStatus.in_progress,
            source="PlannerAgent",
            summary="Test summary",
            human_clarification_request="Test clarification",
        )

    async def get_steps_by_plan(self, plan_id: str) -> list:
        step = Step(
            id="step_test",
            plan_id=plan_id,
            action="Test step action",
            agent=BAgentType.human_agent,
            status=StepStatus.planned,
            session_id="session_test",
            user_id="user_test",
            human_approval_status=HumanFeedbackStatus.requested,
        )
        return [step]

# --- Dummy model client simulating LLM responses ---


class DummyModelClient:
    async def create(self, messages, extra_create_args=None):
        # Simulate a valid structured response based on the expected schema.
        response_dict = {
            "initial_goal": "Achieve test goal",
            "steps": [{"action": "Do step 1", "agent": BAgentType.human_agent.value}],
            "summary_plan_and_steps": "Test plan summary",
            "human_clarification_request": "Need details"
        }
        dummy_resp = MagicMock()
        dummy_resp.content = json.dumps(response_dict)
        return dummy_resp

# --- Fixture for PlannerAgent ---


@pytest.fixture
def planner_agent():
    dummy_model_client = DummyModelClient()
    session_id = "session_test"
    user_id = "user_test"
    fake_memory = FakeMemory()
    available_agents = [BAgentType.human_agent, BAgentType.tech_support_agent]
    agent_tools_list = ["tool1", "tool2"]
    agent = PlannerAgent(
        model_client=dummy_model_client,
        session_id=session_id,
        user_id=user_id,
        memory=fake_memory,
        available_agents=available_agents,
        agent_tools_list=agent_tools_list,
    )
    return agent, fake_memory

# ------------------- Tests for handle_input_task -------------------


@pytest.mark.asyncio
async def test_handle_input_task_success(planner_agent):
    """Test that handle_input_task returns a valid plan and calls memory.add_item."""
    agent, fake_memory = planner_agent
    input_task = InputTask(description="Test objective", session_id="session_test")
    ctx = DummyMessageContext()
    # Patch _create_structured_plan to simulate a valid LLM response.
    dummy_plan = Plan(
        id="plan_success",
        session_id="session_test",
        user_id="user_test",
        initial_goal="Achieve test goal",
        overall_status=PlanStatus.in_progress,
        source="PlannerAgent",
        summary="Dummy summary",
        human_clarification_request="Request info"
    )
    dummy_steps = [
        Step(
            id="step1",
            plan_id="plan_success",
            action="Do step 1",
            agent=BAgentType.human_agent,
            status=StepStatus.planned,
            session_id="session_test",
            user_id="user_test",
            human_approval_status=HumanFeedbackStatus.requested,
        )
    ]
    agent._create_structured_plan = AsyncMock(return_value=(dummy_plan, dummy_steps))
    fake_memory.add_item = AsyncMock()
    result = await agent.handle_input_task(input_task, ctx)
    assert result.id == "plan_success"
    fake_memory.add_item.assert_called()


@pytest.mark.asyncio
async def test_handle_input_task_no_steps(planner_agent):
    """Test that _create_structured_plan raising ValueError causes exception."""
    agent, fake_memory = planner_agent
    input_task = InputTask(description="Test objective", session_id="session_test")
    ctx = DummyMessageContext()
    # Patch _create_structured_plan to return no steps.
    agent._create_structured_plan = AsyncMock(side_effect=ValueError("No steps found"))
    with pytest.raises(ValueError, match="No steps found"):
        await agent.handle_input_task(input_task, ctx)

# ------------------- Tests for _generate_instruction -------------------


def test_generate_instruction_contains_content(planner_agent):
    agent, _ = planner_agent
    instruction = agent._generate_instruction("Test objective")
    assert "Test objective" in instruction
    # Check that available agents and tool list are included.
    for ag in agent._available_agents:
        # BAgentType enum values are strings via .value
        assert ag.value in instruction
    if agent._agent_tools_list:
        for tool in agent._agent_tools_list:
            assert tool in instruction

# ------------------- Tests for _create_structured_plan -------------------


@pytest.mark.asyncio
async def test_create_structured_plan_success(planner_agent):
    """Test _create_structured_plan returns a valid plan and steps."""
    agent, fake_memory = planner_agent
    structured_response = {
        "initial_goal": "Goal A",
        "steps": [{"action": "Step 1 action", "agent": BAgentType.human_agent.value}],
        "summary_plan_and_steps": "Plan summary A",
        "human_clarification_request": "Clarify details"
    }
    dummy_response = MagicMock()
    dummy_response.content = json.dumps(structured_response)
    agent._model_client.create = AsyncMock(return_value=dummy_response)
    fake_memory.add_plan = AsyncMock()
    fake_memory.add_step = AsyncMock()
    messages = [UserMessage(content="Dummy instruction", source="PlannerAgent")]
    plan, steps = await agent._create_structured_plan(messages)
    assert plan.initial_goal == "Goal A"
    assert len(steps) == 1
    fake_memory.add_plan.assert_called_once()
    fake_memory.add_step.assert_called_once()


@pytest.mark.asyncio
async def test_create_structured_plan_exception(planner_agent):
    """Test _create_structured_plan exception handling when model client fails."""
    agent, fake_memory = planner_agent
    agent._model_client.create = AsyncMock(side_effect=Exception("LLM error"))
    messages = [UserMessage(content="Dummy instruction", source="PlannerAgent")]
    plan, steps = await agent._create_structured_plan(messages)
    assert plan.overall_status == PlanStatus.failed
    assert plan.id == ""
    assert steps == []
