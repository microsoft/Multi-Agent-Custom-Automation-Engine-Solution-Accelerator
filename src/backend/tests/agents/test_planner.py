import os
import sys
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.backend.agents.planner import PlannerAgent
from src.backend.models.messages import InputTask, HumanClarification, Plan, PlanStatus
from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext


# Mock azure.monitor.events.extension globally
sys.modules['azure.monitor.events.extension'] = MagicMock()

# Mock environment variables
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"


@pytest.fixture
def mock_context():
    """Mock the CosmosBufferedChatCompletionContext."""
    return MagicMock(spec=CosmosBufferedChatCompletionContext)


@pytest.fixture
def mock_model_client():
    """Mock the Azure OpenAI model client."""
    return MagicMock()


@pytest.fixture
def mock_runtime_context():
    """Mock the runtime context for AgentInstantiationContext."""
    with patch(
        "autogen_core.base._agent_instantiation.AgentInstantiationContext.AGENT_INSTANTIATION_CONTEXT_VAR",
        new=MagicMock(),
    ) as mock_context_var:
        yield mock_context_var


@pytest.fixture
def planner_agent(mock_model_client, mock_context, mock_runtime_context):
    """Return an instance of PlannerAgent with mocked dependencies."""
    # Mock the context variable to ensure runtime context is properly simulated
    mock_runtime_context.get.return_value = (MagicMock(), "mock-agent-id")
    return PlannerAgent(
        model_client=mock_model_client,
        session_id="test-session",
        user_id="test-user",
        memory=mock_context,
        available_agents=["HumanAgent", "MarketingAgent", "TechSupportAgent"],
        agent_tools_list=["tool1", "tool2"],
    )


@pytest.mark.asyncio
async def test_handle_plan_clarification(planner_agent, mock_context):
    """Test the handle_plan_clarification method."""
    # Prepare mock clarification and context
    mock_clarification = HumanClarification(
        session_id="test-session",
        plan_id="plan-1",
        human_clarification="Test clarification",
    )

    mock_context.get_plan_by_session = AsyncMock(return_value=Plan(
        id="plan-1",
        session_id="test-session",
        user_id="test-user",
        initial_goal="Test Goal",
        overall_status="in_progress",
        source="PlannerAgent",
        summary="Mock Summary",
        human_clarification_request=None,
    ))
    mock_context.update_plan = AsyncMock()
    mock_context.add_item = AsyncMock()

    # Execute the method
    await planner_agent.handle_plan_clarification(mock_clarification, None)

    # Assertions
    mock_context.get_plan_by_session.assert_called_with(session_id="test-session")
    mock_context.update_plan.assert_called()
    mock_context.add_item.assert_called()


@pytest.mark.asyncio
async def test_generate_instruction_with_special_characters(planner_agent):
    """Test _generate_instruction with special characters in the objective."""
    special_objective = "Solve this task: @$%^&*()"
    instruction = planner_agent._generate_instruction(special_objective)

    # Assertions
    assert "Solve this task: @$%^&*()" in instruction
    assert "HumanAgent" in instruction
    assert "tool1" in instruction


@pytest.mark.asyncio
async def test_handle_plan_clarification_updates_plan_correctly(planner_agent, mock_context):
    """Test handle_plan_clarification ensures correct plan updates."""
    mock_clarification = HumanClarification(
        session_id="test-session",
        plan_id="plan-1",
        human_clarification="Updated clarification text",
    )

    mock_plan = Plan(
        id="plan-1",
        session_id="test-session",
        user_id="test-user",
        initial_goal="Test Goal",
        overall_status="in_progress",
        source="PlannerAgent",
        summary="Mock Summary",
        human_clarification_request="Previous clarification needed",
    )

    # Mock get_plan_by_session and update_plan
    mock_context.get_plan_by_session = AsyncMock(return_value=mock_plan)
    mock_context.update_plan = AsyncMock()

    # Execute the method
    await planner_agent.handle_plan_clarification(mock_clarification, None)

    # Assertions
    assert mock_plan.human_clarification_response == "Updated clarification text"
    mock_context.update_plan.assert_called_with(mock_plan)


@pytest.mark.asyncio
async def test_handle_input_task_with_exception(planner_agent, mock_context):
    """Test handle_input_task gracefully handles exceptions."""
    # Mock InputTask
    input_task = InputTask(description="Test task causing exception", session_id="test-session")

    # Mock _create_structured_plan to raise an exception
    planner_agent._create_structured_plan = AsyncMock(side_effect=Exception("Mocked exception"))

    # Execute the method
    with pytest.raises(Exception, match="Mocked exception"):
        await planner_agent.handle_input_task(input_task, None)

    # Assertions
    planner_agent._create_structured_plan.assert_called()
    mock_context.add_item.assert_not_called()
    mock_context.add_plan.assert_not_called()
    mock_context.add_step.assert_not_called()


@pytest.mark.asyncio
async def test_handle_plan_clarification_handles_memory_error(planner_agent, mock_context):
    """Test handle_plan_clarification gracefully handles memory errors."""
    mock_clarification = HumanClarification(
        session_id="test-session",
        plan_id="plan-1",
        human_clarification="Test clarification",
    )

    # Mock get_plan_by_session to raise an exception
    mock_context.get_plan_by_session = AsyncMock(side_effect=Exception("Memory error"))

    # Execute the method
    with pytest.raises(Exception, match="Memory error"):
        await planner_agent.handle_plan_clarification(mock_clarification, None)

    # Ensure no updates or messages are added after failure
    mock_context.update_plan.assert_not_called()
    mock_context.add_item.assert_not_called()


@pytest.mark.asyncio
async def test_generate_instruction_with_missing_objective(planner_agent):
    """Test _generate_instruction with a missing or empty objective."""
    instruction = planner_agent._generate_instruction("")
    assert "Your objective is:" in instruction
    assert "The agents you have access to are:" in instruction
    assert "These agents have access to the following functions:" in instruction


@pytest.mark.asyncio
async def test_create_structured_plan_with_error(planner_agent, mock_context):
    """Test _create_structured_plan when an error occurs during plan creation."""
    planner_agent._model_client.create = AsyncMock(side_effect=Exception("Mocked error"))

    messages = [{"content": "Test message", "source": "PlannerAgent"}]
    plan, steps = await planner_agent._create_structured_plan(messages)

    # Assertions
    assert plan.initial_goal == "Error generating plan"
    assert plan.overall_status == PlanStatus.failed
    assert len(steps) == 0
    mock_context.add_plan.assert_not_called()
    mock_context.add_step.assert_not_called()


@pytest.mark.asyncio
async def test_create_structured_plan_with_multiple_steps(planner_agent, mock_context):
    """Test _create_structured_plan with multiple steps."""
    planner_agent._model_client.create = AsyncMock(
        return_value=MagicMock(content=json.dumps({
            "initial_goal": "Task with multiple steps",
            "steps": [
                {"action": "Step 1", "agent": "HumanAgent"},
                {"action": "Step 2", "agent": "TechSupportAgent"},
            ],
            "summary_plan_and_steps": "Generated summary with multiple steps",
            "human_clarification_request": None,
        }))
    )

    messages = [{"content": "Test message", "source": "PlannerAgent"}]
    plan, steps = await planner_agent._create_structured_plan(messages)

    # Assertions
    assert len(steps) == 2
    assert steps[0].action == "Step 1"
    assert steps[1].action == "Step 2"
    mock_context.add_step.assert_called()
