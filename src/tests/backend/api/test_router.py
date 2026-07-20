# Copyright (c) Microsoft. All rights reserved.
"""Tests for api/router.py.

These tests import the *real* router module and patch its collaborators at the
module level (never via sys.modules), so they do not pollute the shared
interpreter state for other test files that import the same real modules.
"""

import contextlib
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure flat backend imports (models.messages etc.) inside router resolve.
_backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")
)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)


def _import_router():
    """Import the real router module despite shared-process mock pollution.

    Earlier-collected tests (e.g. agents/) replace flat modules such as
    ``common.database`` with bare ``Mock()`` objects in ``sys.modules``. Those
    are not packages, so the router's flat imports would fail. We install proper
    package stubs for the flat namespaces the router walks and ``MagicMock``
    stand-ins for its heavy leaf dependencies, letting the lightweight message
    model modules import for real (so FastAPI request/response validation uses
    the genuine dataclasses/pydantic models). Afterwards ``sys.modules`` is
    restored to its exact prior state so no other test file is affected. The
    router's collaborators are patched per-test.
    """
    def _realpkg(name):
        module = ModuleType(name)
        module.__path__ = [os.path.join(_backend_path, *name.split("."))]
        sys.modules[name] = module

    packages = [
        "common", "common.models", "common.config", "common.database",
        "common.utils", "orchestration", "orchestration.helper", "services",
        "auth", "models",
    ]
    heavy_leaves = [
        "common.config.app_config", "common.database.database_factory",
        "common.utils.event_utils", "common.utils.team_utils",
        "orchestration.connection_config", "orchestration.orchestration_manager",
        "services.plan_service", "services.team_service", "auth.auth_utils",
    ]
    # Leaf modules that MUST load for real so FastAPI sees genuine model classes.
    force_real = ["common.models.messages", "models.messages", "models.plan_models"]
    snapshot = dict(sys.modules)
    try:
        for pkg in packages:
            _realpkg(pkg)
        for leaf in heavy_leaves:
            sys.modules[leaf] = MagicMock()
        for name in force_real:
            sys.modules.pop(name, None)
        import backend.api.router as router  # noqa: F401
        from fastapi import FastAPI

        # Build the app while the real message-model modules are importable, so
        # FastAPI resolves the route signatures against the genuine models.
        app = FastAPI()
        app.include_router(router.app_router)
        return router, app
    finally:
        router_mod_obj = sys.modules.get("backend.api.router")
        for key in list(sys.modules):
            if key not in snapshot and not key.startswith("backend"):
                del sys.modules[key]
        for key, value in snapshot.items():
            sys.modules[key] = value
        if router_mod_obj is not None:
            sys.modules["backend.api.router"] = router_mod_obj


router_mod, _app = _import_router()
from fastapi.testclient import TestClient  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture: TestClient with all collaborators mocked
# ---------------------------------------------------------------------------
@pytest.fixture
def rt(monkeypatch):
    """Patch every collaborator referenced from the router namespace."""
    store = MagicMock()
    store.get_plan_by_plan_id = AsyncMock(return_value=None)
    store.get_current_team = AsyncMock(return_value=None)
    store.get_team_by_id = AsyncMock(return_value=MagicMock())
    store.get_plan = AsyncMock(return_value=None)
    store.get_agent_messages = AsyncMock(return_value=[])
    store.get_all_plans_by_team_id_status = AsyncMock(return_value=[])
    store.delete_current_team = AsyncMock()
    store.add_plan = AsyncMock()

    database_factory = MagicMock()
    database_factory.get_database = AsyncMock(return_value=store)

    team_service = MagicMock()
    team_service.get_team_configuration = AsyncMock(return_value=None)
    team_service.handle_team_selection = AsyncMock(return_value=MagicMock())
    team_service.get_all_team_configurations = AsyncMock(return_value=[])
    team_service.delete_team_configuration = AsyncMock(return_value=True)
    team_service.validate_team_models = AsyncMock(return_value=(True, []))
    team_service.validate_team_search_indexes = AsyncMock(return_value=(True, []))
    team_service.validate_and_parse_team_config = AsyncMock(return_value=MagicMock())
    team_service.save_team_configuration = AsyncMock(return_value="team-123")
    team_service_cls = MagicMock(return_value=team_service)

    plan_service = MagicMock()
    plan_service.handle_plan_approval = AsyncMock(return_value=True)
    plan_service.handle_human_clarification = AsyncMock(return_value=True)
    plan_service.handle_agent_messages = AsyncMock(return_value=True)

    orchestration_manager = MagicMock()
    orchestration_manager.get_current_or_new_orchestration = AsyncMock()
    orchestration_manager.return_value.run_orchestration = AsyncMock()

    connection_config = MagicMock()
    connection_config.send_status_update_async = AsyncMock()
    connection_config.close_connection = AsyncMock()
    connection_config.add_connection = MagicMock()
    connection_config.wait_for_clarification = AsyncMock(return_value="the answer")

    orchestration_config = MagicMock()
    orchestration_config.wait_for_clarification = AsyncMock(return_value="the answer")
    orchestration_config.approvals = {}
    orchestration_config.clarifications = {}
    orchestration_config.plans = {}
    orchestration_config.active_tasks = {}
    orchestration_config.get_current_orchestration = MagicMock(return_value=None)
    orchestration_config.set_approval_result = MagicMock()
    orchestration_config.set_clarification_result = MagicMock()
    orchestration_config.set_clarification_pending = MagicMock()

    team_config = MagicMock()

    find_first_available_team = AsyncMock(return_value="team-abc")
    rai_success = AsyncMock(return_value=True)
    rai_validate_team_config = AsyncMock(return_value=(True, None))
    get_user = MagicMock(return_value={"user_principal_id": "user-1"})

    monkeypatch.setattr(router_mod, "get_authenticated_user_details", get_user)
    monkeypatch.setattr(router_mod, "DatabaseFactory", database_factory)
    monkeypatch.setattr(router_mod, "TeamService", team_service_cls)
    monkeypatch.setattr(router_mod, "PlanService", plan_service)
    monkeypatch.setattr(router_mod, "OrchestrationManager", orchestration_manager)
    monkeypatch.setattr(router_mod, "connection_config", connection_config)
    monkeypatch.setattr(router_mod, "orchestration_config", orchestration_config)
    monkeypatch.setattr(router_mod, "team_config", team_config)
    monkeypatch.setattr(router_mod, "track_event_if_configured", MagicMock())
    monkeypatch.setattr(
        router_mod, "find_first_available_team", find_first_available_team
    )
    monkeypatch.setattr(router_mod, "rai_success", rai_success)
    monkeypatch.setattr(router_mod, "rai_validate_team_config", rai_validate_team_config)

    app = _app
    client = TestClient(app)

    return SimpleNamespace(
        client=client,
        store=store,
        database_factory=database_factory,
        team_service=team_service,
        team_service_cls=team_service_cls,
        plan_service=plan_service,
        orchestration_manager=orchestration_manager,
        connection_config=connection_config,
        orchestration_config=orchestration_config,
        team_config=team_config,
        find_first_available_team=find_first_available_team,
        rai_success=rai_success,
        rai_validate_team_config=rai_validate_team_config,
        get_user=get_user,
    )


def _no_user(rt):
    rt.get_user.return_value = {"user_principal_id": None}


# ---------------------------------------------------------------------------
# /init_team
# ---------------------------------------------------------------------------
class TestInitTeam:
    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.get("/api/v4/init_team")
        assert resp.status_code == 400

    def test_no_teams_configured(self, rt):
        rt.find_first_available_team.return_value = None
        rt.store.get_current_team.return_value = None
        resp = rt.client.get("/api/v4/init_team")
        assert resp.status_code == 200
        body = resp.json()
        assert body["requires_team_upload"] is True

    def test_first_available_team_used(self, rt):
        rt.find_first_available_team.return_value = "team-abc"
        rt.store.get_current_team.return_value = None
        selected = MagicMock()
        selected.team_id = "team-abc"
        rt.team_service.handle_team_selection.return_value = selected
        team_conf = MagicMock()
        rt.team_service.get_team_configuration.return_value = team_conf
        resp = rt.client.get("/api/v4/init_team")
        assert resp.status_code == 200
        assert resp.json()["status"] == "Request started successfully"

    def test_current_team_used(self, rt):
        current = MagicMock()
        current.team_id = "team-current"
        rt.store.get_current_team.return_value = current
        rt.team_service.get_team_configuration.return_value = MagicMock()
        resp = rt.client.get("/api/v4/init_team")
        assert resp.status_code == 200
        assert resp.json()["team_id"] == "team-current"

    def test_team_configuration_missing_clears(self, rt):
        current = MagicMock()
        current.team_id = "team-current"
        rt.store.get_current_team.return_value = current
        rt.team_service.get_team_configuration.return_value = None
        resp = rt.client.get("/api/v4/init_team")
        assert resp.status_code == 200
        assert resp.json()["requires_team_upload"] is True
        rt.store.delete_current_team.assert_awaited()

    def test_exception_returns_400(self, rt):
        rt.database_factory.get_database = AsyncMock(side_effect=Exception("boom"))
        resp = rt.client.get("/api/v4/init_team")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /process_request
# ---------------------------------------------------------------------------
class TestProcessRequest:
    def _payload(self):
        return {"session_id": "sess-1", "description": "do the thing"}

    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.post("/api/v4/process_request", json=self._payload())
        assert resp.status_code == 400

    def test_team_not_found(self, rt):
        rt.store.get_current_team.return_value = None
        rt.store.get_team_by_id.return_value = None
        resp = rt.client.post("/api/v4/process_request", json=self._payload())
        assert resp.status_code == 400

    def test_rai_failure(self, rt):
        rt.store.get_team_by_id.return_value = MagicMock()
        rt.rai_success.return_value = False
        resp = rt.client.post("/api/v4/process_request", json=self._payload())
        assert resp.status_code == 400

    def test_success(self, rt):
        team = MagicMock()
        rt.store.get_team_by_id.return_value = team
        current = MagicMock()
        current.team_id = "team-x"
        rt.store.get_current_team.return_value = current
        rt.rai_success.return_value = True
        resp = rt.client.post("/api/v4/process_request", json=self._payload())
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "Request started successfully"
        assert body["plan_id"]

    def test_success_generates_session_id(self, rt):
        rt.store.get_team_by_id.return_value = MagicMock()
        rt.rai_success.return_value = True
        resp = rt.client.post(
            "/api/v4/process_request", json={"session_id": "", "description": "x"}
        )
        assert resp.status_code == 200
        assert resp.json()["session_id"]


# ---------------------------------------------------------------------------
# /plan_approval
# ---------------------------------------------------------------------------
class TestPlanApproval:
    def _payload(self, **kw):
        data = {"m_plan_id": "m-1", "approved": True, "plan_id": "p-1", "feedback": "ok"}
        data.update(kw)
        return data

    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.post("/api/v4/plan_approval", json=self._payload())
        assert resp.status_code == 401

    def test_approved_recorded(self, rt):
        rt.orchestration_config.approvals = {"m-1": True}
        plan = MagicMock()
        plan.session_id = "sess-1"
        rt.store.get_plan_by_plan_id.return_value = plan
        resp = rt.client.post("/api/v4/plan_approval", json=self._payload())
        assert resp.status_code == 200
        assert resp.json()["status"] == "approval recorded"
        rt.orchestration_config.set_approval_result.assert_called_once()

    def test_rejected_recorded(self, rt):
        rt.orchestration_config.approvals = {"m-1": True}
        rt.store.get_plan_by_plan_id.return_value = None
        resp = rt.client.post(
            "/api/v4/plan_approval", json=self._payload(approved=False)
        )
        assert resp.status_code == 200

    def test_no_active_plan(self, rt):
        # The 404 raised in the else-branch is caught by the surrounding
        # `except Exception` block and surfaced as a 500 by the endpoint.
        rt.orchestration_config.approvals = {}
        resp = rt.client.post("/api/v4/plan_approval", json=self._payload())
        assert resp.status_code == 500

    def test_plan_service_value_error(self, rt):
        rt.orchestration_config.approvals = {"m-1": True}
        rt.plan_service.handle_plan_approval = AsyncMock(side_effect=ValueError("bad"))
        resp = rt.client.post("/api/v4/plan_approval", json=self._payload())
        assert resp.status_code == 200

    def test_plan_service_generic_error(self, rt):
        rt.orchestration_config.approvals = {"m-1": True}
        rt.plan_service.handle_plan_approval = AsyncMock(side_effect=Exception("boom"))
        resp = rt.client.post("/api/v4/plan_approval", json=self._payload())
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /clarification/ask
# ---------------------------------------------------------------------------
class TestClarificationAsk:
    def test_missing_fields(self, rt):
        resp = rt.client.post("/api/v4/clarification/ask", json={"question": ""})
        assert resp.status_code == 400

    def test_success(self, rt):
        rt.orchestration_config.wait_for_clarification.return_value = "answer!"
        resp = rt.client.post(
            "/api/v4/clarification/ask",
            json={"question": "why?", "user_id": "user-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["answer"] == "answer!"

    def test_timeout(self, rt):
        import asyncio

        rt.orchestration_config.wait_for_clarification = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )
        resp = rt.client.post(
            "/api/v4/clarification/ask",
            json={"question": "why?", "user_id": "user-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["answer"] == ""

    def test_generic_error(self, rt):
        rt.orchestration_config.wait_for_clarification = AsyncMock(
            side_effect=Exception("boom")
        )
        resp = rt.client.post(
            "/api/v4/clarification/ask",
            json={"question": "why?", "user_id": "user-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["answer"] == ""


# ---------------------------------------------------------------------------
# /user_clarification
# ---------------------------------------------------------------------------
class TestUserClarification:
    def _payload(self, **kw):
        data = {"request_id": "r-1", "answer": "my answer", "plan_id": "p-1"}
        data.update(kw)
        return data

    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.post("/api/v4/user_clarification", json=self._payload())
        assert resp.status_code == 401

    def test_team_not_found(self, rt):
        rt.store.get_team_by_id.return_value = None
        resp = rt.client.post("/api/v4/user_clarification", json=self._payload())
        assert resp.status_code == 400

    def test_rai_failure(self, rt):
        rt.store.get_team_by_id.return_value = MagicMock()
        rt.rai_success.return_value = False
        resp = rt.client.post("/api/v4/user_clarification", json=self._payload())
        assert resp.status_code == 400

    def test_success(self, rt):
        rt.store.get_team_by_id.return_value = MagicMock()
        rt.rai_success.return_value = True
        rt.orchestration_config.clarifications = {"r-1": True}
        resp = rt.client.post("/api/v4/user_clarification", json=self._payload())
        assert resp.status_code == 200
        assert resp.json()["status"] == "clarification recorded"

    def test_no_active_clarification(self, rt):
        rt.store.get_team_by_id.return_value = MagicMock()
        rt.rai_success.return_value = True
        rt.orchestration_config.clarifications = {}
        resp = rt.client.post("/api/v4/user_clarification", json=self._payload())
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /agent_message
# ---------------------------------------------------------------------------
class TestAgentMessage:
    def _payload(self, **kw):
        data = {
            "plan_id": "p-1",
            "agent": "My Agent",
            "content": "hello",
            "agent_type": "AI_Agent",
        }
        data.update(kw)
        return data

    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.post("/api/v4/agent_message", json=self._payload())
        assert resp.status_code == 401

    def test_success(self, rt):
        plan = MagicMock()
        plan.session_id = "sess-1"
        rt.store.get_plan_by_plan_id.return_value = plan
        resp = rt.client.post("/api/v4/agent_message", json=self._payload())
        assert resp.status_code == 200
        assert resp.json()["status"] == "message recorded"

    def test_plan_service_error(self, rt):
        rt.plan_service.handle_agent_messages = AsyncMock(side_effect=Exception("boom"))
        resp = rt.client.post("/api/v4/agent_message", json=self._payload())
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /upload_team_config
# ---------------------------------------------------------------------------
class TestUploadTeamConfig:
    def _file(self, content=b'{"name": "t", "status": "active"}', name="team.json"):
        return {"file": (name, content, "application/json")}

    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.post("/api/v4/upload_team_config", files=self._file())
        assert resp.status_code == 400

    def test_non_json_file(self, rt):
        resp = rt.client.post(
            "/api/v4/upload_team_config", files=self._file(name="team.txt")
        )
        assert resp.status_code == 400

    def test_invalid_json(self, rt):
        resp = rt.client.post(
            "/api/v4/upload_team_config", files=self._file(content=b"not json")
        )
        assert resp.status_code == 400

    def test_rai_validation_failure(self, rt):
        rt.rai_validate_team_config.return_value = (False, "unsafe content")
        resp = rt.client.post("/api/v4/upload_team_config", files=self._file())
        assert resp.status_code == 400

    def test_model_validation_failure(self, rt):
        rt.rai_validate_team_config.return_value = (True, None)
        rt.team_service.validate_team_models.return_value = (False, ["gpt-4"])
        resp = rt.client.post("/api/v4/upload_team_config", files=self._file())
        assert resp.status_code == 400

    def test_search_validation_failure(self, rt):
        rt.rai_validate_team_config.return_value = (True, None)
        rt.team_service.validate_team_models.return_value = (True, [])
        rt.team_service.validate_team_search_indexes.return_value = (False, ["idx err"])
        resp = rt.client.post("/api/v4/upload_team_config", files=self._file())
        assert resp.status_code == 400

    def test_success(self, rt):
        rt.rai_validate_team_config.return_value = (True, None)
        rt.team_service.validate_team_models.return_value = (True, [])
        rt.team_service.validate_team_search_indexes.return_value = (True, [])
        team_conf = MagicMock()
        team_conf.agents = [1]
        team_conf.starting_tasks = [1]
        team_conf.name = "MyTeam"
        team_conf.model_dump.return_value = {"name": "MyTeam"}
        rt.team_service.validate_and_parse_team_config.return_value = team_conf
        rt.team_service.save_team_configuration.return_value = "team-999"
        resp = rt.client.post("/api/v4/upload_team_config", files=self._file())
        assert resp.status_code == 200
        assert resp.json()["team_id"] == "team-999"

    def test_success_with_team_id(self, rt):
        rt.team_service.validate_team_models.return_value = (True, [])
        rt.team_service.validate_team_search_indexes.return_value = (True, [])
        team_conf = MagicMock()
        team_conf.agents = []
        team_conf.starting_tasks = []
        team_conf.name = "MyTeam"
        team_conf.model_dump.return_value = {"name": "MyTeam"}
        rt.team_service.validate_and_parse_team_config.return_value = team_conf
        rt.team_service.save_team_configuration.return_value = "given-id"
        resp = rt.client.post(
            "/api/v4/upload_team_config?team_id=given-id", files=self._file()
        )
        assert resp.status_code == 200

    def test_parse_value_error(self, rt):
        rt.team_service.validate_team_models.return_value = (True, [])
        rt.team_service.validate_team_search_indexes.return_value = (True, [])
        rt.team_service.validate_and_parse_team_config = AsyncMock(
            side_effect=ValueError("bad config")
        )
        resp = rt.client.post("/api/v4/upload_team_config", files=self._file())
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /team_configs (GET all)
# ---------------------------------------------------------------------------
class TestGetTeamConfigs:
    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.get("/api/v4/team_configs")
        assert resp.status_code == 401

    def test_success(self, rt):
        c = MagicMock()
        c.model_dump.return_value = {"id": "1"}
        rt.team_service.get_all_team_configurations.return_value = [c]
        resp = rt.client.get("/api/v4/team_configs")
        assert resp.status_code == 200
        assert resp.json() == [{"id": "1"}]

    def test_error(self, rt):
        rt.team_service.get_all_team_configurations = AsyncMock(
            side_effect=Exception("boom")
        )
        resp = rt.client.get("/api/v4/team_configs")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# /team_configs/{team_id}
# ---------------------------------------------------------------------------
class TestGetTeamConfigById:
    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.get("/api/v4/team_configs/t1")
        assert resp.status_code == 401

    def test_not_found(self, rt):
        rt.team_service.get_team_configuration.return_value = None
        resp = rt.client.get("/api/v4/team_configs/t1")
        assert resp.status_code == 404

    def test_success(self, rt):
        conf = MagicMock()
        conf.model_dump.return_value = {"id": "t1"}
        rt.team_service.get_team_configuration.return_value = conf
        resp = rt.client.get("/api/v4/team_configs/t1")
        assert resp.status_code == 200
        assert resp.json() == {"id": "t1"}

    def test_error(self, rt):
        rt.team_service.get_team_configuration = AsyncMock(
            side_effect=Exception("boom")
        )
        resp = rt.client.get("/api/v4/team_configs/t1")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /team_configs/{team_id}
# ---------------------------------------------------------------------------
class TestDeleteTeamConfig:
    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.delete("/api/v4/team_configs/t1")
        assert resp.status_code == 401

    def test_not_found(self, rt):
        rt.team_service.delete_team_configuration.return_value = False
        resp = rt.client.delete("/api/v4/team_configs/t1")
        assert resp.status_code == 404

    def test_success(self, rt):
        rt.team_service.delete_team_configuration.return_value = True
        resp = rt.client.delete("/api/v4/team_configs/t1")
        assert resp.status_code == 200
        assert resp.json()["team_id"] == "t1"

    def test_error(self, rt):
        rt.team_service.delete_team_configuration = AsyncMock(
            side_effect=Exception("boom")
        )
        resp = rt.client.delete("/api/v4/team_configs/t1")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# /select_team
# ---------------------------------------------------------------------------
class TestSelectTeam:
    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.post("/api/v4/select_team", json={"team_id": "t1"})
        assert resp.status_code == 401

    def test_missing_team_id(self, rt):
        resp = rt.client.post("/api/v4/select_team", json={"team_id": ""})
        assert resp.status_code == 400

    def test_team_not_found(self, rt):
        rt.team_service.get_team_configuration.return_value = None
        resp = rt.client.post("/api/v4/select_team", json={"team_id": "t1"})
        assert resp.status_code == 404

    def test_selection_failed(self, rt):
        conf = MagicMock()
        conf.name = "TeamA"
        rt.team_service.get_team_configuration.return_value = conf
        rt.team_service.handle_team_selection.return_value = None
        resp = rt.client.post("/api/v4/select_team", json={"team_id": "t1"})
        assert resp.status_code == 404

    def test_success(self, rt):
        conf = MagicMock()
        conf.name = "TeamA"
        conf.agents = [1, 2]
        conf.description = "desc"
        rt.team_service.get_team_configuration.return_value = conf
        rt.team_service.handle_team_selection.return_value = MagicMock()
        resp = rt.client.post("/api/v4/select_team", json={"team_id": "t1"})
        assert resp.status_code == 200
        assert resp.json()["team_id"] == "t1"

    def test_error(self, rt):
        rt.team_service.get_team_configuration = AsyncMock(
            side_effect=Exception("boom")
        )
        resp = rt.client.post("/api/v4/select_team", json={"team_id": "t1"})
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# /plans
# ---------------------------------------------------------------------------
class TestGetPlans:
    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.get("/api/v4/plans")
        assert resp.status_code == 400

    def test_no_current_team(self, rt):
        rt.store.get_current_team.return_value = None
        resp = rt.client.get("/api/v4/plans")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_success(self, rt):
        current = MagicMock()
        current.team_id = "t1"
        rt.store.get_current_team.return_value = current
        rt.store.get_all_plans_by_team_id_status.return_value = []
        resp = rt.client.get("/api/v4/plans")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /plan
# ---------------------------------------------------------------------------
class TestGetPlanById:
    def test_no_user(self, rt):
        _no_user(rt)
        resp = rt.client.get("/api/v4/plan?plan_id=p1")
        assert resp.status_code == 400

    def test_no_plan_id(self, rt):
        resp = rt.client.get("/api/v4/plan")
        assert resp.status_code == 500

    def test_plan_not_found(self, rt):
        rt.store.get_plan_by_plan_id.return_value = None
        resp = rt.client.get("/api/v4/plan?plan_id=p1")
        assert resp.status_code == 500

    def test_success(self, rt):
        plan = MagicMock()
        plan.session_id = "sess-1"
        plan.team_id = "t1"
        plan.plan_id = "p1"
        plan.m_plan = {"x": 1}
        plan.streaming_message = "streaming"
        rt.store.get_plan_by_plan_id.return_value = plan
        rt.store.get_team_by_id.return_value = MagicMock()
        rt.store.get_agent_messages.return_value = []
        resp = rt.client.get("/api/v4/plan?plan_id=p1")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /images/{blob_name}
# ---------------------------------------------------------------------------
class TestGetGeneratedImage:
    def test_storage_not_configured(self, rt, monkeypatch):
        cfg = MagicMock()
        cfg.AZURE_STORAGE_BLOB_URL = ""
        monkeypatch.setattr(router_mod, "config", cfg)
        resp = rt.client.get("/api/v4/images/pic.png")
        assert resp.status_code == 503

    def test_invalid_name(self, rt, monkeypatch):
        cfg = MagicMock()
        cfg.AZURE_STORAGE_BLOB_URL = "https://blob"
        cfg.AZURE_STORAGE_IMAGES_CONTAINER = "images"
        monkeypatch.setattr(router_mod, "config", cfg)
        resp = rt.client.get("/api/v4/images/evil!.png")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# WebSocket /socket/{process_id}
# ---------------------------------------------------------------------------
class TestWebSocket:
    def test_connect_and_disconnect(self, rt):
        plan = MagicMock()
        plan.session_id = "sess-1"
        rt.store.get_plan_by_plan_id.return_value = plan
        with rt.client.websocket_connect(
            "/api/v4/socket/proc-1?user_id=user-1"
        ) as ws:
            ws.send_text("hello")
        rt.connection_config.add_connection.assert_called_once()

    def test_connect_default_user(self, rt):
        rt.store.get_plan_by_plan_id.return_value = None
        with contextlib.suppress(Exception):
            with rt.client.websocket_connect("/api/v4/socket/proc-2") as ws:
                ws.close()
