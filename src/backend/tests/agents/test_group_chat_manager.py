"""
Combined Test cases for GroupChatManager class in the backend agents module.
"""

import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

# Set mock environment variables for Azure and CosmosDB before importing anything else
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Mock Azure dependencies
sys.modules["azure.monitor.events.extension"] = MagicMock()

# Import after setting environment variables
from src.backend.agents.group_chat_manager import GroupChatManager
from src.backend.models.messages import (
    Step,
    StepStatus,
    BAgentType,
)
from autogen_core.base import AgentInstantiationContext, AgentRuntime
from autogen_core.components.models import AzureOpenAIChatCompletionClient
from src.backend.context.cosmos_memory import CosmosBufferedChatCompletionContext
from autogen_core.base import AgentId


@pytest.fixture
def setup_group_chat_manager():
    """
    Fixture to set up a GroupChatManager and its dependencies.
    """
    # Mock dependencies
    mock_model_client = MagicMock(spec=AzureOpenAIChatCompletionClient)
    session_id = "test_session_id"
    user_id = "test_user_id"
    mock_memory = AsyncMock(spec=CosmosBufferedChatCompletionContext)
    mock_agent_ids = {BAgentType.planner_agent: AgentId("planner_agent", session_id)}

    # Mock AgentInstantiationContext
    mock_runtime = MagicMock(spec=AgentRuntime)
    mock_agent_id = "test_agent_id"

    with patch.object(AgentInstantiationContext, "current_runtime", return_value=mock_runtime):
        with patch.object(AgentInstantiationContext, "current_agent_id", return_value=mock_agent_id):
            # Instantiate GroupChatManager
            group_chat_manager = GroupChatManager(
                model_client=mock_model_client,
                session_id=session_id,
                user_id=user_id,
                memory=mock_memory,
                agent_ids=mock_agent_ids,
            )

    return group_chat_manager, mock_memory, session_id, user_id, mock_agent_ids


@pytest.mark.asyncio
@patch("src.backend.agents.group_chat_manager.track_event_if_configured")
async def test_update_step_status(mock_track_event, setup_group_chat_manager):
    """
    Test the `_update_step_status` method.
    """
    group_chat_manager, mock_memory, session_id, user_id, mock_agent_ids = setup_group_chat_manager

    # Create a mock Step
    step = Step(
        id="test_step_id",
        session_id=session_id,
        plan_id="test_plan_id",
        user_id=user_id,
        action="Test Action",
        agent=BAgentType.human_agent,
        status=StepStatus.planned,
    )

    # Call the method
    await group_chat_manager._update_step_status(step, True, "Feedback message")

    # Assertions
    step.status = StepStatus.completed
    step.human_feedback = "Feedback message"
    mock_memory.update_step.assert_called_once_with(step)
    mock_track_event.assert_called_once_with(
        "Group Chat Manager - Received human feedback, Updating step and updated into the cosmos",
        {
            "status": StepStatus.completed,
            "session_id": step.session_id,
            "user_id": step.user_id,
            "human_feedback": "Feedback message",
            "source": step.agent,
        },
    )


@pytest.mark.asyncio
async def test_update_step_invalid_feedback_status(setup_group_chat_manager):
    """
    Test `_update_step_status` with invalid feedback status.
    Covers lines 210-211.
    """
    group_chat_manager, mock_memory, session_id, user_id, mock_agent_ids = setup_group_chat_manager

    # Create a mock Step
    step = Step(
        id="test_step_id",
        session_id=session_id,
        plan_id="test_plan_id",
        user_id=user_id,
        action="Test Action",
        agent=BAgentType.human_agent,
        status=StepStatus.planned,
    )

    # Call the method with invalid feedback status
    await group_chat_manager._update_step_status(step, None, "Feedback message")

    # Assertions
    step.status = StepStatus.planned  # Status should remain unchanged
    step.human_feedback = "Feedback message"
    mock_memory.update_step.assert_called_once_with(step)
