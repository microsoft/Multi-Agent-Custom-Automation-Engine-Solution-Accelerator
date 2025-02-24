import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# --- MOCK EXTERNAL DEPENDENCIES ---
# Prevent import errors for Azure modules.
sys.modules["azure.monitor"] = MagicMock()
sys.modules["azure.monitor.events.extension"] = MagicMock()
sys.modules["azure.monitor.opentelemetry"] = MagicMock()

# Set required environment variables
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ[
    "APPLICATIONINSIGHTS_INSTRUMENTATION_KEY"
] = "InstrumentationKey=mock-instrumentation-key;IngestionEndpoint=https://mock-ingestion-endpoint"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Prevent telemetry initialization errors
with patch("azure.monitor.opentelemetry.configure_azure_monitor", MagicMock()):
    from src.backend.app import app

client = TestClient(app)


class FakePlan:
    id = "fake_plan_id"
    summary = "Fake plan summary"


class FakeRuntime:
    async def send_message(self, message, agent_id):
        return FakePlan()


# Allow any arguments so that both (session_id, user_id) and keyword usage work.
async def fake_initialize_runtime_and_context(*args, **kwargs):
    return FakeRuntime(), None


# Our Fake Cosmos returns dictionaries that fully satisfy our Pydantic models.
class FakeCosmos:
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id

    async def get_plan_by_session(self, session_id: str):
        if session_id == "existing":
            user_id = self.user_id  # capture from the outer instance

            class FakePlanBySession:
                id = "existing_plan_id"

                def model_dump(inner_self):
                    return {
                        "id": inner_self.id,
                        "session_id": session_id,
                        "initial_goal": "Test goal",
                        "overall_status": "in_progress",
                        "user_id": user_id,
                    }
            return FakePlanBySession()
        return None

    async def get_steps_by_plan(self, plan_id: str):
        return [{
            "id": "step1",
            "plan_id": plan_id,
            "action": "Test action",
            "agent": "TechSupportAgent",  # Allowed enum value
            "status": "planned",
            "session_id": self.session_id,
            "user_id": self.user_id,
        }]

    async def get_all_plans(self):
        user_id = self.user_id

        class FakePlanAll:
            id = "plan1"

            def model_dump(inner_self):
                return {
                    "id": inner_self.id,
                    "session_id": "sess1",
                    "initial_goal": "Goal1",
                    "overall_status": "completed",
                    "user_id": user_id,
                }
        return [FakePlanAll()]

    async def get_data_by_type(self, type_str: str):
        return [{
            "id": "agent_msg1",
            "session_id": self.session_id,
            "plan_id": "plan1",
            "content": "Fake agent message",
            "source": "TechSupportAgent",
            "ts": 123456789,
            "step_id": "step1",
            "user_id": self.user_id,
        }]

    async def delete_all_messages(self, type_str: str):
        return

    async def get_all_messages(self):
        return [{
            "id": "msg1",
            "data_type": "plan",
            "session_id": "sess1",
            "user_id": self.user_id,
            "content": "Test content",
            "ts": 123456789,
        }]


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    # Override authentication so that the headers always yield a valid user.
    monkeypatch.setattr(
        "src.backend.auth.auth_utils.get_authenticated_user_details",
        lambda headers: {"user_principal_id": "mock-user-id"},
    )

    monkeypatch.setattr(
        "src.backend.utils.retrieve_all_agent_tools",
        lambda: [{
            "agent": "TechSupportAgent",
            "function": "test_function",
            "description": "desc",
            "arguments": "args"
        }],
    )
    monkeypatch.setattr("src.backend.app.initialize_runtime_and_context", fake_initialize_runtime_and_context)
    monkeypatch.setattr("src.backend.app.CosmosBufferedChatCompletionContext", FakeCosmos)
    monkeypatch.setattr("src.backend.app.track_event_if_configured", lambda event, props: None)


def test_input_task_invalid_json():
    invalid_json = "Invalid JSON data"
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/input_task", data=invalid_json, headers=headers)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_input_task_missing_description():
    payload = {"session_id": ""}
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/input_task", json=payload, headers=headers)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_human_feedback_valid():
    payload = {
        "step_id": "step1",
        "plan_id": "plan1",
        "session_id": "sess1",
        "approved": True,
        "human_feedback": "Feedback text",
        "updated_action": "No change"
    }
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/human_feedback", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Feedback received"
    assert data["session_id"] == payload["session_id"]
    assert data["step_id"] == payload["step_id"]


def test_human_clarification_valid():
    payload = {
        "plan_id": "plan1",
        "session_id": "sess1",
        "human_clarification": "Clarification details"
    }
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/human_clarification_on_plan", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Clarification received"
    assert data["session_id"] == payload["session_id"]


def test_approve_step_with_step_id():
    payload = {
        "step_id": "step1",
        "plan_id": "plan1",
        "session_id": "sess1",
        "approved": True,
        "human_feedback": "Approved",
        "updated_action": "None"
    }
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/approve_step_or_steps", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "Step step1" in data["status"]


def test_approve_all_steps():
    payload = {
        "step_id": "",
        "plan_id": "plan1",
        "session_id": "sess1",
        "approved": True,
        "human_feedback": "All approved",
        "updated_action": "None"
    }
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/approve_step_or_steps", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "All steps approved"


def test_get_plans_with_session():
    headers = {"Authorization": "Bearer mock-token"}
    response = client.get("/plans", params={"session_id": "existing"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    plan = data[0]
    assert plan["id"] == "existing_plan_id"
    assert "steps" in plan


def test_get_plans_without_session():
    headers = {"Authorization": "Bearer mock-token"}
    response = client.get("/plans", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    plan = data[0]
    assert plan["id"] == "plan1"
    assert "steps" in plan


def test_get_steps_by_plan():
    headers = {"Authorization": "Bearer mock-token"}
    response = client.get("/steps/plan1", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["plan_id"] == "plan1"


def test_get_agent_messages():
    headers = {"Authorization": "Bearer mock-token"}
    response = client.get("/agent_messages/sess1", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["session_id"] == "sess1"


def test_delete_all_messages():
    headers = {"Authorization": "Bearer mock-token"}
    response = client.delete("/messages", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "All messages deleted"


def test_get_all_messages():
    headers = {"Authorization": "Bearer mock-token"}
    response = client.get("/messages", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["data_type"] == "plan"


def test_get_agent_tools():
    response = client.get("/api/agent-tools")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Our override now returns "TechSupportAgent"
    assert data[0]["agent"] == "TechSupportAgent"


def test_basic_endpoint():
    response = client.get("/")
    assert response.status_code == 404


def test_input_task_rai_failure(monkeypatch):
    """
    Test the /input_task endpoint when the RAI check fails.
    The endpoint should print "RAI failed", track the event, and return {"status": "Plan not created"}.
    """
    # Override rai_success to return False
    monkeypatch.setattr("src.backend.app.rai_success", lambda description: False)
    payload = {"session_id": "", "description": "This should fail RAI"}
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/input_task", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Plan not created"


def test_get_plans_not_found():
    """
    Test the /plans endpoint when a session_id is provided that does not exist.
    Expect a 404 error with detail "Plan not found".
    """
    headers = {"Authorization": "Bearer mock-token"}
    response = client.get("/plans", params={"session_id": "nonexistent"}, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Plan not found"


if __name__ == "__main__":
    pytest.main()
