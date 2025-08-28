import os
import sys
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# Mock Azure dependencies to prevent import errors
sys.modules["azure.monitor"] = MagicMock()
sys.modules["azure.monitor.events.extension"] = MagicMock()
sys.modules["azure.monitor.opentelemetry"] = MagicMock()

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

# Ensure repo root is on sys.path so `src.backend...` imports work
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Provide safe defaults for vars that app_config reads at import-time
os.environ.setdefault("AZURE_AI_SUBSCRIPTION_ID", "00000000-0000-0000-0000-000000000000")
os.environ.setdefault("AZURE_AI_RESOURCE_GROUP", "rg-test")
os.environ.setdefault("AZURE_AI_PROJECT_NAME", "proj-test")
os.environ.setdefault("AZURE_AI_AGENT_ENDPOINT", "https://agents.example.com/")
os.environ.setdefault("USER_LOCAL_BROWSER_LANGUAGE", "en-US")

# Mock telemetry initialization to prevent errors
with patch("azure.monitor.opentelemetry.configure_azure_monitor", MagicMock()):
    try:
        from src.backend.app import app  # preferred if file exists
    except ModuleNotFoundError:
        # fallback to app_kernel which exists in this repo
        import importlib
        mod = importlib.import_module("src.backend.app_kernel")
        app = getattr(mod, "app", None)
        if app is None:
            create_app = getattr(mod, "create_app", None)
            if create_app is not None:
                app = create_app()
            else:
                raise

# Initialize FastAPI test client
client = TestClient(app)

from fastapi.routing import APIRoute

def _find_input_task_path(app):
    for r in app.routes:
        if isinstance(r, APIRoute):
            # prefer exact or known names, but fall back to substring
            if r.name in ("input_task", "handle_input_task"):
                return r.path
            if "input_task" in r.path:
                return r.path
    return "/input_task"  # fallback

INPUT_TASK_PATH = _find_input_task_path(app)


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    """Mock dependencies to simplify tests."""
    monkeypatch.setattr(
        "src.backend.auth.auth_utils.get_authenticated_user_details",
        lambda headers: {"user_principal_id": "mock-user-id"},
    )
    monkeypatch.setattr(
        "src.backend.utils_kernel.retrieve_all_agent_tools",
        lambda: [{"agent": "test_agent", "function": "test_function"}],
        raising=False,  # allow creating the attr if it doesn't exist
    )


def test_input_task_invalid_json():
    """Test the case where the input JSON is invalid."""
    headers = {"Authorization": "Bearer mock-token"}
    # syntactically valid but fails validation -> 422
    response = client.post(INPUT_TASK_PATH, json={}, headers=headers)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_input_task_missing_description():
    """Test the case where the input task description is missing."""
    input_task = {"session_id": None, "user_id": "mock-user-id"}
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post(INPUT_TASK_PATH, json=input_task, headers=headers)
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
    response = client.post(INPUT_TASK_PATH, json=empty_task, headers=headers)
    assert response.status_code == 422
    assert "detail" in response.json()


if __name__ == "__main__":
    pytest.main()
