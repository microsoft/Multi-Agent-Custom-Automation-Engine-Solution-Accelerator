"""Tests for the simple chat API endpoint."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock Azure dependencies to avoid import errors during tests
sys.modules["azure.monitor"] = MagicMock()
sys.modules["azure.monitor.events.extension"] = MagicMock()
sys.modules["azure.monitor.opentelemetry"] = MagicMock()

# Set required environment variables before importing the app
os.environ["COSMOSDB_ENDPOINT"] = "https://mock-endpoint"
os.environ["COSMOSDB_KEY"] = "mock-key"
os.environ["COSMOSDB_DATABASE"] = "mock-database"
os.environ["COSMOSDB_CONTAINER"] = "mock-container"
os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = (
    "InstrumentationKey=mock;IngestionEndpoint=https://mock"
)
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "mock-deployment-name"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-01-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://mock-openai-endpoint"
os.environ["FRONTEND_SITE_NAME"] = "http://localhost"

with patch("azure.monitor.opentelemetry.configure_azure_monitor", MagicMock()):
    from src.backend.app_kernel import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    """Mock dependencies used by the chat endpoint."""

    # Mock authentication helper
    monkeypatch.setattr(
        "src.backend.app_kernel.get_authenticated_user_details",
        lambda request_headers: {"user_principal_id": "mock-user"},
    )

    # Mock runtime initialization
    async def mock_initialize_runtime_and_context(session_id, user_id):
        return None, MagicMock()

    monkeypatch.setattr(
        "src.backend.app_kernel.initialize_runtime_and_context",
        mock_initialize_runtime_and_context,
    )

    # Mock config client creation
    monkeypatch.setattr(
        "src.backend.app_kernel.config.get_ai_project_client",
        lambda: MagicMock(close=MagicMock()),
    )

    # Mock AgentFactory.create_agent to return an agent with handle_user_message
    async def mock_create_agent(*args, **kwargs):
        agent = MagicMock()
        agent.handle_user_message = AsyncMock(return_value="mock response")
        return agent

    monkeypatch.setattr(
        "src.backend.app_kernel.AgentFactory.create_agent",
        mock_create_agent,
    )


def test_chat_endpoint_returns_reply():
    """Ensure the chat endpoint returns the agent's reply."""

    payload = {"session_id": "123", "user_message": "Hello"}

    response = client.post("/api/chat", json=payload)

    assert response.status_code == 200
    assert response.json() == {"reply": "mock response"}

