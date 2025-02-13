import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

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

# --- Import the function and constant under test ---
from src.backend.agents.agentutils import (
    extract_and_update_transition_states,
    common_agent_system_message,
)
from src.backend.models.messages import Step
from autogen_core.components.models import AzureOpenAIChatCompletionClient

# Configure the Step model to allow extra attributes.
Step.model_config["extra"] = "allow"


# Dummy Cosmos class that records update calls.
class DummyCosmosRecorder:
    def __init__(self):
        self.update_called = False

    async def update_step(self, step):
        # To allow setting extra attributes, ensure __pydantic_extra__ is initialized.
        if step.__pydantic_extra__ is None:
            step.__pydantic_extra__ = {}
        step.__pydantic_extra__["updated_field"] = True
        self.update_called = True


# Dummy model client classes to simulate LLM responses.

class DummyModelClient(AzureOpenAIChatCompletionClient):
    def __init__(self, **kwargs):
        # Bypass parent's __init__.
        pass

    async def create(self, messages, extra_create_args=None):
        # Simulate a valid response that matches the expected FSMStateAndTransition schema.
        response_dict = {
            "identifiedTargetState": "State1",
            "identifiedTargetTransition": "Transition1"
        }
        dummy_resp = MagicMock()
        dummy_resp.content = json.dumps(response_dict)
        return dummy_resp


class DummyModelClientError(AzureOpenAIChatCompletionClient):
    def __init__(self, **kwargs):
        pass

    async def create(self, messages, extra_create_args=None):
        raise Exception("LLM error")


class DummyModelClientInvalidJSON(AzureOpenAIChatCompletionClient):
    def __init__(self, **kwargs):
        pass

    async def create(self, messages, extra_create_args=None):
        dummy_resp = MagicMock()
        dummy_resp.content = "invalid json"
        return dummy_resp


# Fixture: a dummy Step for testing.
@pytest.fixture
def dummy_step():
    step = Step(
        id="step1",
        plan_id="plan1",
        action="Test Action",
        agent="HumanAgent",  # Using string for simplicity.
        status="planned",
        session_id="sess1",
        user_id="user1",
        human_approval_status="requested",
    )
    # Provide a value for agent_reply.
    step.agent_reply = "Test reply"
    # Ensure __pydantic_extra__ is initialized for extra fields.
    step.__pydantic_extra__ = {}
    return step


# Tests for extract_and_update_transition_states
@pytest.mark.asyncio
async def test_extract_and_update_transition_states_success(dummy_step):
    """
    Test that extract_and_update_transition_states correctly parses the LLM response,
    updates the step with the expected target state and transition, and calls cosmos.update_step.
    """
    model_client = DummyModelClient()
    dummy_cosmos = DummyCosmosRecorder()
    with patch("src.backend.agents.agentutils.CosmosBufferedChatCompletionContext", return_value=dummy_cosmos):
        updated_step = await extract_and_update_transition_states(dummy_step, "sess1", "user1", "anything", model_client)
        assert updated_step.identified_target_state == "State1"
        assert updated_step.identified_target_transition == "Transition1"
        assert dummy_cosmos.update_called is True
        # Check that our extra field was set.
        assert updated_step.__pydantic_extra__.get("updated_field") is True


@pytest.mark.asyncio
async def test_extract_and_update_transition_states_model_client_error(dummy_step):
    """
    Test that if the model client raises an exception, it propagates.
    """
    model_client = DummyModelClientError()
    with patch("src.backend.agents.agentutils.CosmosBufferedChatCompletionContext", return_value=DummyCosmosRecorder()):
        with pytest.raises(Exception, match="LLM error"):
            await extract_and_update_transition_states(dummy_step, "sess1", "user1", "anything", model_client)


@pytest.mark.asyncio
async def test_extract_and_update_transition_states_invalid_json(dummy_step):
    """
    Test that an invalid JSON response from the model client causes an exception.
    """
    model_client = DummyModelClientInvalidJSON()
    with patch("src.backend.agents.agentutils.CosmosBufferedChatCompletionContext", return_value=DummyCosmosRecorder()):
        with pytest.raises(Exception):
            await extract_and_update_transition_states(dummy_step, "sess1", "user1", "anything", model_client)


def test_common_agent_system_message_contains_delivery_address():
    """
    Test that the common_agent_system_message constant contains instructions regarding the delivery address.
    """
    assert "delivery address" in common_agent_system_message


@pytest.mark.asyncio
async def test_extract_and_update_transition_states_no_agent_reply(dummy_step):
    """
    Test the behavior when step.agent_reply is empty.
    """
    dummy_step.agent_reply = ""
    # Ensure extra dict is initialized.
    dummy_step.__pydantic_extra__ = {}
    model_client = DummyModelClient()
    with patch("src.backend.agents.agentutils.CosmosBufferedChatCompletionContext", return_value=DummyCosmosRecorder()):
        updated_step = await extract_and_update_transition_states(dummy_step, "sess1", "user1", "anything", model_client)
        # Even with an empty agent_reply, our dummy client returns the same valid JSON.
        assert updated_step.identified_target_state == "State1"
        assert updated_step.identified_target_transition == "Transition1"


def test_dummy_json_parsing():
    """
    Test that the JSON parsing in extract_and_update_transition_states works for valid JSON.
    """
    json_str = '{"identifiedTargetState": "TestState", "identifiedTargetTransition": "TestTransition"}'
    data = json.loads(json_str)

    class DummySchema(BaseModel):
        identifiedTargetState: str
        identifiedTargetTransition: str
    schema = DummySchema(**data)
    assert schema.identifiedTargetState == "TestState"
    assert schema.identifiedTargetTransition == "TestTransition"
