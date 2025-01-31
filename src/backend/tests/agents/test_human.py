"""
Test cases for HumanAgent class in the backend agents module.
"""

# Standard library imports
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# Function to set environment variables
def setup_environment_variables():
    """Set environment variables required for the tests."""
    os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
    os.environ["COSMOSDB_KEY"] = "mock-key"
    os.environ["COSMOSDB_DATABASE"] = "mock-database"
    os.environ["COSMOSDB_CONTAINER"] = "mock-container"
    os.environ["APPLICATIONINSIGHTS_INSTRUMENTATION_KEY"] = "mock-instrumentation-key"
    os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
    os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"


# Call the function to set environment variables
setup_environment_variables()

# Mock Azure and event_utils dependencies globally
sys.modules["azure.monitor.events.extension"] = MagicMock()
sys.modules["src.backend.event_utils"] = MagicMock()

# Project-specific imports (must come after environment setup)
from autogen_core.base import AgentInstantiationContext, AgentRuntime
from src.backend.agents.human import HumanAgent
from src.backend.models.messages import HumanFeedback, Step, StepStatus, BAgentType


@pytest.fixture(autouse=True)
def ensure_env_variables(monkeypatch):
    """
    Fixture to ensure environment variables are set for all tests.
    This overrides any modifications made by individual tests.
    """
    env_vars = {
        "COSMOSDB_ENDPOINT": "https://mock-endpoint",
        "COSMOSDB_KEY": "mock-key",
        "COSMOSDB_DATABASE": "mock-database",
        "COSMOSDB_CONTAINER": "mock-container",
        "APPLICATIONINSIGHTS_INSTRUMENTATION_KEY": "mock-instrumentation-key",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "mock-deployment-name",
        "AZURE_OPENAI_API_VERSION": "2023-01-01",
        "AZURE_OPENAI_ENDPOINT": "https://mock-openai-endpoint",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def setup_agent():
    """
    Fixture to set up a HumanAgent and its dependencies.
    """
    memory = AsyncMock()
    user_id = "test_user"
    group_chat_manager_id = "group_chat_manager"

    # Mock runtime and agent ID
    mock_runtime = MagicMock(spec=AgentRuntime)
    mock_agent_id = "test_agent_id"

    # Set up the context
    with patch.object(AgentInstantiationContext, "current_runtime", return_value=mock_runtime):
        with patch.object(AgentInstantiationContext, "current_agent_id", return_value=mock_agent_id):
            agent = HumanAgent(memory, user_id, group_chat_manager_id)

    session_id = "session123"
    step_id = "step123"
    plan_id = "plan123"

    # Mock HumanFeedback message
    feedback_message = HumanFeedback(
        session_id=session_id,
        step_id=step_id,
        plan_id=plan_id,
        approved=True,
        human_feedback="Great job!",
    )

    # Mock Step with all required fields
    step = Step(
        plan_id=plan_id,
        action="Test Action",
        agent=BAgentType.human_agent,
        status=StepStatus.planned,
        session_id=session_id,
        user_id=user_id,
        human_feedback=None,
    )

    return agent, memory, feedback_message, step, session_id, step_id, plan_id


@patch("src.backend.agents.human.logging.info")
@patch("src.backend.agents.human.track_event_if_configured")
@pytest.mark.asyncio
async def test_handle_step_feedback_step_not_found(mock_track_event, mock_logging, setup_agent):
    """
    Test scenario where the step is not found in memory.
    """
    agent, memory, feedback_message, _, _, step_id, _ = setup_agent

    # Mock no step found
    memory.get_step.return_value = None

    # Run the method
    await agent.handle_step_feedback(feedback_message, MagicMock())

    # Check if log and return were called correctly
    mock_logging.assert_called_with(f"No step found with id: {step_id}")
    memory.update_step.assert_not_called()
    mock_track_event.assert_not_called()
