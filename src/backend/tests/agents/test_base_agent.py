# pylint: disable=import-error, wrong-import-position, missing-module-docstring
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from contextlib import contextmanager

# Mocking necessary modules and environment variables
sys.modules["azure.monitor.events.extension"] = MagicMock()

# Mocking environment variables
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Importing the module to test
from src.backend.agents.base_agent import BaseAgent
from src.backend.models.messages import ActionRequest, Step, StepStatus
from autogen_core.base import AgentId


# Context manager for setting up mocks
@contextmanager
def mock_context():
    mock_runtime = MagicMock()
    with patch("autogen_core.base._agent_instantiation.AgentInstantiationContext.AGENT_INSTANTIATION_CONTEXT_VAR") as mock_context_var:
        mock_context_instance = MagicMock()
        mock_context_var.get.return_value = mock_context_instance
        mock_context_instance.set.return_value = None
        yield mock_runtime


@pytest.fixture
def mock_dependencies():
    model_client = MagicMock()
    model_context = MagicMock()
    tools = [MagicMock(schema="tool_schema")]
    tool_agent_id = MagicMock()
    return {
        "model_client": model_client,
        "model_context": model_context,
        "tools": tools,
        "tool_agent_id": tool_agent_id,
    }


@pytest.fixture
def base_agent(mock_dependencies):
    with mock_context():
        return BaseAgent(
            agent_name="test_agent",
            model_client=mock_dependencies["model_client"],
            session_id="test_session",
            user_id="test_user",
            model_context=mock_dependencies["model_context"],
            tools=mock_dependencies["tools"],
            tool_agent_id=mock_dependencies["tool_agent_id"],
            system_message="This is a system message.",
        )


def test_save_state(base_agent, mock_dependencies):
    mock_dependencies["model_context"].save_state = MagicMock(return_value={"state_key": "state_value"})
    state = base_agent.save_state()
    assert state == {"memory": {"state_key": "state_value"}}


def test_load_state(base_agent, mock_dependencies):
    mock_dependencies["model_context"].load_state = MagicMock()
    state = {"memory": {"state_key": "state_value"}}
    base_agent.load_state(state)
    mock_dependencies["model_context"].load_state.assert_called_once_with({"state_key": "state_value"})


@pytest.mark.asyncio
async def test_handle_action_request_error(base_agent, mock_dependencies):
    """Test handle_action_request when tool_agent_caller_loop raises an error."""
    step = Step(
        id="step_1",
        status=StepStatus.approved,
        human_feedback="feedback",
        agent_reply="",
        plan_id="plan_id",
        action="action",
        agent="HumanAgent",
        session_id="session_id",
        user_id="user_id",
    )
    mock_dependencies["model_context"].get_step = AsyncMock(return_value=step)
    mock_dependencies["model_context"].add_item = AsyncMock()

    with patch("src.backend.agents.base_agent.tool_agent_caller_loop", AsyncMock(side_effect=Exception("Mock error"))):
        message = ActionRequest(
            step_id="step_1",
            session_id="test_session",
            action="test_action",
            plan_id="plan_id",
            agent="HumanAgent",
        )
        ctx = MagicMock()
        with pytest.raises(ValueError) as excinfo:
            await base_agent.handle_action_request(message, ctx)
        assert "Return type <class 'NoneType'> not in return types" in str(excinfo.value)


@pytest.mark.asyncio
async def test_handle_action_request_success(base_agent, mock_dependencies):
    """Test handle_action_request with a successful tool_agent_caller_loop."""
    step = Step(
        id="step_1",
        status=StepStatus.approved,
        human_feedback="feedback",
        agent_reply="",
        plan_id="plan_id",
        action="action",
        agent="HumanAgent",
        session_id="session_id",
        user_id="user_id"
    )
    mock_dependencies["model_context"].get_step = AsyncMock(return_value=step)
    mock_dependencies["model_context"].update_step = AsyncMock()
    mock_dependencies["model_context"].add_item = AsyncMock()

    with patch("src.backend.agents.base_agent.tool_agent_caller_loop", new=AsyncMock(return_value=[MagicMock(content="result")])):
        base_agent._runtime.publish_message = AsyncMock()
        message = ActionRequest(
            step_id="step_1",
            session_id="test_session",
            action="test_action",
            plan_id="plan_id",
            agent="HumanAgent"
        )
        ctx = MagicMock()
        response = await base_agent.handle_action_request(message, ctx)

        assert response.status == StepStatus.completed
        assert response.result == "result"
        assert response.plan_id == "plan_id"
        assert response.session_id == "test_session"

        base_agent._runtime.publish_message.assert_awaited_once_with(
            response,
            AgentId(type="group_chat_manager", key="test_session"),
            sender=base_agent.id,
            cancellation_token=None
        )
        mock_dependencies["model_context"].update_step.assert_called_once_with(step)
