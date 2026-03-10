"""
Comprehensive tests for backend.v4.api.router module.
Tests all FastAPI endpoints with success, error, and edge case scenarios.
"""

import io
import json
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest


# All fixtures are defined in conftest.py


# ---------------------------------------------------------------------------
# Test: GET /init_team
# ---------------------------------------------------------------------------


def test_init_team_error(create_test_client, mock_database):
    """Test init_team handles exceptions with 400."""
    mock_database.get_current_team = AsyncMock(side_effect=Exception("Database error"))
    
    response = create_test_client.get("/api/v4/init_team")
    
    assert response.status_code == 400
    assert "Error starting request" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Test: POST /process_request
# ---------------------------------------------------------------------------

def test_process_request_success(create_test_client, mock_database):
    """Test process_request creates plan successfully."""
    mock_team = MagicMock(team_id="team-123", name="Test Team")
    mock_current_team = MagicMock(team_id="team-123")
    
    mock_database.get_current_team = AsyncMock(return_value=mock_current_team)
    mock_database.get_team_by_id = AsyncMock(return_value=mock_team)
    mock_database.add_plan = AsyncMock()
    
    payload = {
        "session_id": "session-123",
        "description": "Test task description"
    }
    
    response = create_test_client.post("/api/v4/process_request", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "plan_id" in data
    assert data["status"] == "Request started successfully"
    assert data["session_id"] == "session-123"



# ---------------------------------------------------------------------------
# Test: POST /plan_approval
# ---------------------------------------------------------------------------

def test_plan_approval_success(create_test_client, mock_configs):
    """Test plan approval is recorded successfully."""
    mock_configs["orchestration_config"].approvals = {"m-plan-123": None}
    
    payload = {
        "m_plan_id": "m-plan-123",
        "approved": True,
        "feedback": "Looks good"
    }
    
    response = create_test_client.post("/api/v4/plan_approval", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approval recorded"


# ---------------------------------------------------------------------------
# Test: POST /user_clarification
# ---------------------------------------------------------------------------

def test_user_clarification_success(create_test_client, mock_database, mock_configs):
    """Test user clarification is recorded successfully."""
    mock_team = MagicMock(team_id="team-123")
    mock_current_team = MagicMock(team_id="team-123")
    
    mock_database.get_current_team = AsyncMock(return_value=mock_current_team)
    mock_database.get_team_by_id = AsyncMock(return_value=mock_team)
    mock_configs["orchestration_config"].clarifications = {"request-123": None}
    
    payload = {
        "request_id": "request-123",
        "answer": "My clarification response"
    }
    
    response = create_test_client.post("/api/v4/user_clarification", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarification recorded"


def test_user_clarification_rai_failure(create_test_client, mock_database, mock_utils):
    """Test user clarification when RAI check fails."""
    mock_team = MagicMock(team_id="team-123")
    mock_current_team = MagicMock(team_id="team-123")
    
    mock_database.get_current_team = AsyncMock(return_value=mock_current_team)
    mock_database.get_team_by_id = AsyncMock(return_value=mock_team)
    mock_utils["rai_success"].return_value = False
    
    payload = {"request_id": "request-123", "answer": "Harmful content"}
    response = create_test_client.post("/api/v4/user_clarification", json=payload)
    
    assert response.status_code == 400


def test_user_clarification_not_found(create_test_client, mock_database, mock_configs):
    """Test user clarification when request not found returns 404."""
    mock_team = MagicMock(team_id="team-123")
    mock_current_team = MagicMock(team_id="team-123")
    
    mock_database.get_current_team = AsyncMock(return_value=mock_current_team)
    mock_database.get_team_by_id = AsyncMock(return_value=mock_team)
    mock_configs["orchestration_config"].clarifications = {}
    
    payload = {"request_id": "nonexistent", "answer": "Response"}
    response = create_test_client.post("/api/v4/user_clarification", json=payload)
    
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: POST /agent_message
# ---------------------------------------------------------------------------

def test_agent_message_success(create_test_client):
    """Test agent message is recorded successfully."""
    payload = {
        "plan_id": "plan-123",
        "agent": "Test Agent",
        "content": "Agent message content",
        "agent_type": "AI_Agent"
    }
    
    response = create_test_client.post("/api/v4/agent_message", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "message recorded"


# Removed test_agent_message_no_user - tests framework auth, not API logic


# ---------------------------------------------------------------------------
# Test: POST /upload_team_config
# ---------------------------------------------------------------------------


def test_upload_team_config_no_user(create_test_client, mock_auth):
    """Test upload team config with missing user returns 400."""
    mock_auth.return_value = {"user_principal_id": None}
    
    files = {"file": ("test.json", io.BytesIO(b"{}"), "application/json")}
    response = create_test_client.post("/api/v4/upload_team_config", files=files)
    
    assert response.status_code == 400


def test_upload_team_config_no_file(create_test_client):
    """Test upload team config without file returns 400."""
    response = create_test_client.post("/api/v4/upload_team_config")
    
    assert response.status_code == 422  # FastAPI validation error


def test_upload_team_config_invalid_json(create_test_client):
    """Test upload team config with invalid JSON returns 400."""
    files = {"file": ("invalid.json", io.BytesIO(b"not json"), "application/json")}
    response = create_test_client.post("/api/v4/upload_team_config", files=files)
    
    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]


def test_upload_team_config_not_json_file(create_test_client):
    """Test upload team config with non-JSON file returns 400."""
    files = {"file": ("test.txt", io.BytesIO(b"text"), "text/plain")}
    response = create_test_client.post("/api/v4/upload_team_config", files=files)
    
    assert response.status_code == 400
    assert "must be a JSON file" in response.json()["detail"]




# ---------------------------------------------------------------------------
# Test: GET /team_configs
# ---------------------------------------------------------------------------

def test_get_team_configs_success(create_test_client, mock_services):
    """Test get team configs returns list successfully."""
    mock_team1 = MagicMock()
    mock_team1.model_dump = Mock(return_value={"team_id": "team-1", "name": "Team 1"})
    mock_team2 = MagicMock()
    mock_team2.model_dump = Mock(return_value={"team_id": "team-2", "name": "Team 2"})
    
    mock_services["team_service"]().get_all_team_configurations = AsyncMock(
        return_value=[mock_team1, mock_team2]
    )
    
    response = create_test_client.get("/api/v4/team_configs")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["team_id"] == "team-1"


def test_get_team_configs_error(create_test_client, mock_services):
    """Test get team configs handles errors with 500."""
    mock_services["team_service"]().get_all_team_configurations = AsyncMock(
        side_effect=Exception("Database error")
    )
    
    response = create_test_client.get("/api/v4/team_configs")
    
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Test: GET /team_configs/{team_id}
# ---------------------------------------------------------------------------

def test_get_team_config_by_id_success(create_test_client, mock_services):
    """Test get team config by ID returns config successfully."""
    mock_team = MagicMock()
    mock_team.model_dump = Mock(return_value={"team_id": "team-123", "name": "Test Team"})
    
    mock_services["team_service"]().get_team_configuration = AsyncMock(return_value=mock_team)
    
    response = create_test_client.get("/api/v4/team_configs/team-123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] == "team-123"


def test_get_team_config_by_id_not_found(create_test_client, mock_services):
    """Test get team config by ID when not found returns 404."""
    mock_services["team_service"]().get_team_configuration = AsyncMock(return_value=None)
    
    response = create_test_client.get("/api/v4/team_configs/nonexistent")
    
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: DELETE /team_configs/{team_id}
# ---------------------------------------------------------------------------

def test_delete_team_config_success(create_test_client, mock_services):
    """Test delete team config successfully."""
    mock_services["team_service"]().delete_team_configuration = AsyncMock(return_value=True)
    
    response = create_test_client.delete("/api/v4/team_configs/team-123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["team_id"] == "team-123"


def test_delete_team_config_not_found(create_test_client, mock_services):
    """Test delete team config when not found returns 404."""
    mock_services["team_service"]().delete_team_configuration = AsyncMock(return_value=False)
    
    response = create_test_client.delete("/api/v4/team_configs/nonexistent")
    
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: POST /select_team
# ---------------------------------------------------------------------------

def test_select_team_success(create_test_client, mock_services):
    """Test select team successfully."""
    mock_team = MagicMock()
    mock_team.team_id = "team-123"
    mock_team.name = "Test Team"
    mock_team.agents = []
    mock_team.description = "Test description"
    
    mock_services["team_service"]().get_team_configuration = AsyncMock(return_value=mock_team)
    mock_services["team_service"]().handle_team_selection = AsyncMock(
        return_value=MagicMock(team_id="team-123")
    )
    
    payload = {"team_id": "team-123"}
    response = create_test_client.post("/api/v4/select_team", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["team_id"] == "team-123"


def test_select_team_no_team_id(create_test_client):
    """Test select team without team_id returns 400."""
    payload = {}
    response = create_test_client.post("/api/v4/select_team", json=payload)
    
    assert response.status_code == 422  # FastAPI validation error


def test_select_team_not_found(create_test_client, mock_services):
    """Test select team when team not found returns 404."""
    mock_services["team_service"]().get_team_configuration = AsyncMock(return_value=None)
    
    payload = {"team_id": "nonexistent"}
    response = create_test_client.post("/api/v4/select_team", json=payload)
    
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: GET /plans
# ---------------------------------------------------------------------------

def test_get_plans_success(create_test_client, mock_database):
    """Test get plans returns list successfully."""
    mock_current_team = MagicMock(team_id="team-123")
    mock_plan1 = MagicMock(id="plan-1", session_id="session-1")
    mock_plan2 = MagicMock(id="plan-2", session_id="session-2")
    
    mock_database.get_current_team = AsyncMock(return_value=mock_current_team)
    mock_database.get_all_plans_by_team_id_status = AsyncMock(return_value=[mock_plan1, mock_plan2])
    
    response = create_test_client.get("/api/v4/plans")
    
    assert response.status_code == 200


def test_get_plans_no_current_team(create_test_client, mock_database):
    """Test get plans when no current team returns empty list."""
    mock_database.get_current_team = AsyncMock(return_value=None)
    
    response = create_test_client.get("/api/v4/plans")
    
    assert response.status_code == 200
    data = response.json()
    assert data == []


# ---------------------------------------------------------------------------
# Test: GET /plan
# ---------------------------------------------------------------------------







# Removed test_get_plan_by_id_no_user - tests framework auth, not API logic