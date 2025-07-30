import os
import sys
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# Mock Azure dependencies to prevent import errors
sys.modules["azure.monitor"] = MagicMock()
sys.modules["azure.monitor.events.extension"] = MagicMock()
sys.modules["azure.monitor.opentelemetry"] = MagicMock()
sys.modules["azure.ai.projects"] = MagicMock()
sys.modules["azure.ai.projects.aio"] = MagicMock()

# Mock environment variables before importing app
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ[
    "APPLICATIONINSIGHTS_CONNECTION_STRING"
] = "InstrumentationKey=mock-instrumentation-key;IngestionEndpoint=https://mock-ingestion-endpoint"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"

# Mock telemetry initialization to prevent errors
with patch("azure.monitor.opentelemetry.configure_azure_monitor", MagicMock()):
    from app_kernel import app

# Initialize FastAPI test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    """Mock dependencies to simplify tests."""
    monkeypatch.setattr(
        "auth.auth_utils.get_authenticated_user_details",
        lambda headers: {"user_principal_id": "mock-user-id"},
    )


def test_input_task_invalid_json():
    """Test the case where the input JSON is invalid."""
    invalid_json = "Invalid JSON data"

    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/input_task", data=invalid_json, headers=headers)


def test_create_plan_endpoint_success():
    """Test the /api/create_plan endpoint with valid input."""
    headers = {"Authorization": "Bearer mock-token"}
    
    # Mock the RAI success function
    with patch("app_kernel.rai_success", return_value=True), \
         patch("app_kernel.initialize_runtime_and_context") as mock_init, \
         patch("app_kernel.track_event_if_configured") as mock_track:
        
        # Mock memory store
        mock_memory_store = MagicMock()
        mock_init.return_value = (MagicMock(), mock_memory_store)
        
        test_input = {
            "session_id": "test-session-123",
            "description": "Create a marketing plan for our new product"
        }
        
        response = client.post("/api/create_plan", json=test_input, headers=headers)
        
        # Print response details for debugging
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json()}")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "plan_id" in data
        assert "status" in data
        assert "session_id" in data
        assert data["status"] == "Plan created successfully"
        assert data["session_id"] == "test-session-123"
        
        # Verify memory store was called to add plan
        mock_memory_store.add_plan.assert_called_once()


def test_create_plan_endpoint_rai_failure():
    """Test the /api/create_plan endpoint when RAI check fails."""
    headers = {"Authorization": "Bearer mock-token"}
    
    # Mock the RAI failure
    with patch("app_kernel.rai_success", return_value=False), \
         patch("app_kernel.track_event_if_configured") as mock_track:
        
        test_input = {
            "session_id": "test-session-123",
            "description": "This is an unsafe description"
        }
        
        response = client.post("/api/create_plan", json=test_input, headers=headers)
        
        # Check response
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "safety validation" in data["detail"]


def test_create_plan_endpoint_harmful_content():
    """Test the /api/create_plan endpoint with harmful content that should fail RAI."""
    headers = {"Authorization": "Bearer mock-token"}
    
    # Mock the RAI failure for harmful content
    with patch("app_kernel.rai_success", return_value=False), \
         patch("app_kernel.track_event_if_configured") as mock_track:
        
        test_input = {
            "session_id": "test-session-456",
            "description": "I want to kill my neighbors cat"
        }
        
        response = client.post("/api/create_plan", json=test_input, headers=headers)
        
        # Print response details for debugging
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json()}")
        
        # Check response - should be 400 due to RAI failure
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "safety validation" in data["detail"]


def test_create_plan_endpoint_real_rai_check():
    """Test the /api/create_plan endpoint with real RAI check (no mocking)."""
    headers = {"Authorization": "Bearer mock-token"}
    
    # Don't mock RAI - let it run the real check
    with patch("app_kernel.initialize_runtime_and_context") as mock_init, \
         patch("app_kernel.track_event_if_configured") as mock_track:
        
        # Mock memory store
        mock_memory_store = MagicMock()
        mock_init.return_value = (MagicMock(), mock_memory_store)
        
        test_input = {
            "session_id": "test-session-789",
            "description": "I want to kill my neighbors cat"
        }
        
        response = client.post("/api/create_plan", json=test_input, headers=headers)
        
        # Print response details for debugging
        print(f"Real RAI Response status: {response.status_code}")
        print(f"Real RAI Response data: {response.json()}")
        
        # This should fail with real RAI check
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


def test_input_task_missing_description():
    """Test the case where the input task description is missing."""
    input_task = {
        "session_id": None,
        "user_id": "mock-user-id",
    }

    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/input_task", json=input_task, headers=headers)

    # Assert response for missing description
    assert response.status_code == 422
    assert "detail" in response.json()


def test_basic_endpoint():
    """Test a basic endpoint to ensure the app runs."""
    response = client.get("/")
    assert response.status_code == 404  # The root endpoint is not defined


def test_input_task_empty_description():
    """Tests if /input_task handles an empty description."""
    empty_task = {"session_id": None, "user_id": "mock-user-id", "description": ""}
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/input_task", json=empty_task, headers=headers)

    assert response.status_code == 422
    assert "detail" in response.json()  # Assert error message for missing description


if __name__ == "__main__":
    pytest.main()
