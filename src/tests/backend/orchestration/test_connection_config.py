"""Unit tests for backend.orchestration.connection_config.

Covers OrchestrationConfig (approval/clarification event helpers),
ConnectionConfig (WebSocket registry + status broadcasting), and
TeamConfig. WebSockets are represented by AsyncMock/MagicMock.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


def _import_connection_config():
    """Import backend.orchestration.connection_config with the REAL flat
    ``models.*`` / ``common.models.*`` packages, undoing any bare-Mock or
    empty-ModuleType pollution installed by earlier test modules in the same
    single-process collection run, then restore sys.modules exactly.
    """
    snapshot = dict(sys.modules)
    force_real = [
        "common",
        "common.models",
        "common.models.messages",
        "models",
        "models.messages",
        "models.plan_models",
        "backend.orchestration.connection_config",
    ]
    try:
        for name in force_real:
            sys.modules.pop(name, None)
        import backend.orchestration.connection_config as cc  # noqa: WPS433
        return cc
    finally:
        cc_mod = sys.modules.get("backend.orchestration.connection_config")
        for key in list(sys.modules):
            if key not in snapshot and not key.startswith("backend"):
                sys.modules.pop(key, None)
        sys.modules.update(snapshot)
        if cc_mod is not None:
            sys.modules["backend.orchestration.connection_config"] = cc_mod


_cc = _import_connection_config()
ConnectionConfig = _cc.ConnectionConfig
OrchestrationConfig = _cc.OrchestrationConfig
TeamConfig = _cc.TeamConfig
connection_config = _cc.connection_config
orchestration_config = _cc.orchestration_config
team_config = _cc.team_config


# ----------------------------------------------------------------------- #
# OrchestrationConfig
# ----------------------------------------------------------------------- #
class TestOrchestrationApproval:
    def test_get_current_orchestration(self):
        cfg = OrchestrationConfig()
        cfg.orchestrations["u1"] = "wf"
        assert cfg.get_current_orchestration("u1") == "wf"
        assert cfg.get_current_orchestration("missing") is None

    def test_set_approval_pending_creates_and_resets(self):
        cfg = OrchestrationConfig()
        cfg.set_approval_pending("p1")
        assert cfg.approvals["p1"] is None
        ev = cfg._approval_events["p1"]
        ev.set()
        cfg.set_approval_pending("p1")  # existing -> clear
        assert not cfg._approval_events["p1"].is_set()

    def test_set_approval_result_triggers_event(self):
        cfg = OrchestrationConfig()
        cfg.set_approval_pending("p1")
        cfg.set_approval_result("p1", True)
        assert cfg.approvals["p1"] is True
        assert cfg._approval_events["p1"].is_set()

    @pytest.mark.asyncio
    async def test_wait_for_approval_already_decided(self):
        cfg = OrchestrationConfig()
        cfg.approvals["p1"] = True
        assert await cfg.wait_for_approval("p1") is True

    @pytest.mark.asyncio
    async def test_wait_for_approval_missing_raises_keyerror(self):
        cfg = OrchestrationConfig()
        with pytest.raises(KeyError):
            await cfg.wait_for_approval("nope")

    @pytest.mark.asyncio
    async def test_wait_for_approval_waits_then_returns(self):
        cfg = OrchestrationConfig()
        cfg.set_approval_pending("p1")

        async def approve():
            await asyncio.sleep(0.01)
            cfg.set_approval_result("p1", True)

        task = asyncio.create_task(approve())
        result = await cfg.wait_for_approval("p1", timeout=1.0)
        await task
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_approval_timeout(self):
        cfg = OrchestrationConfig()
        cfg.set_approval_pending("p1")
        with pytest.raises(asyncio.TimeoutError):
            await cfg.wait_for_approval("p1", timeout=0.01)
        assert "p1" not in cfg.approvals  # cleaned up

    def test_cleanup_approval(self):
        cfg = OrchestrationConfig()
        cfg.set_approval_pending("p1")
        cfg.cleanup_approval("p1")
        assert "p1" not in cfg.approvals
        assert "p1" not in cfg._approval_events


class TestOrchestrationClarification:
    def test_set_clarification_pending_and_reset(self):
        cfg = OrchestrationConfig()
        cfg.set_clarification_pending("r1")
        assert cfg.clarifications["r1"] is None
        cfg._clarification_events["r1"].set()
        cfg.set_clarification_pending("r1")
        assert not cfg._clarification_events["r1"].is_set()

    def test_set_clarification_result(self):
        cfg = OrchestrationConfig()
        cfg.set_clarification_pending("r1")
        cfg.set_clarification_result("r1", "answer")
        assert cfg.clarifications["r1"] == "answer"
        assert cfg._clarification_events["r1"].is_set()

    @pytest.mark.asyncio
    async def test_wait_for_clarification_already_answered(self):
        cfg = OrchestrationConfig()
        cfg.clarifications["r1"] = "done"
        assert await cfg.wait_for_clarification("r1") == "done"

    @pytest.mark.asyncio
    async def test_wait_for_clarification_missing_keyerror(self):
        cfg = OrchestrationConfig()
        with pytest.raises(KeyError):
            await cfg.wait_for_clarification("nope")

    @pytest.mark.asyncio
    async def test_wait_for_clarification_waits(self):
        cfg = OrchestrationConfig()
        cfg.set_clarification_pending("r1")

        async def answer():
            await asyncio.sleep(0.01)
            cfg.set_clarification_result("r1", "hi")

        task = asyncio.create_task(answer())
        result = await cfg.wait_for_clarification("r1", timeout=1.0)
        await task
        assert result == "hi"

    @pytest.mark.asyncio
    async def test_wait_for_clarification_timeout(self):
        cfg = OrchestrationConfig()
        cfg.set_clarification_pending("r1")
        with pytest.raises(asyncio.TimeoutError):
            await cfg.wait_for_clarification("r1", timeout=0.01)
        assert "r1" not in cfg.clarifications

    def test_cleanup_clarification(self):
        cfg = OrchestrationConfig()
        cfg.set_clarification_pending("r1")
        cfg.cleanup_clarification("r1")
        assert "r1" not in cfg.clarifications
        assert "r1" not in cfg._clarification_events


# ----------------------------------------------------------------------- #
# ConnectionConfig
# ----------------------------------------------------------------------- #
class TestConnectionRegistry:
    @pytest.mark.asyncio
    async def test_add_connection_simple(self):
        cc = ConnectionConfig()
        ws = AsyncMock()
        cc.add_connection("proc1", ws)
        assert cc.get_connection("proc1") is ws

    @pytest.mark.asyncio
    async def test_add_connection_with_user(self):
        cc = ConnectionConfig()
        ws = AsyncMock()
        cc.add_connection("proc1", ws, user_id="u1")
        assert cc.user_to_process["u1"] == "proc1"

    @pytest.mark.asyncio
    async def test_add_connection_replaces_existing_process(self):
        cc = ConnectionConfig()
        old = AsyncMock()
        cc.add_connection("proc1", old)
        new = AsyncMock()
        cc.add_connection("proc1", new)  # triggers close of old via create_task
        await asyncio.sleep(0)
        assert cc.get_connection("proc1") is new

    @pytest.mark.asyncio
    async def test_add_connection_closes_old_process_for_user(self):
        cc = ConnectionConfig()
        first = AsyncMock()
        cc.add_connection("procA", first, user_id="u1")
        second = AsyncMock()
        cc.add_connection("procB", second, user_id="u1")
        await asyncio.sleep(0)
        assert cc.user_to_process["u1"] == "procB"
        assert "procA" not in cc.connections

    def test_remove_connection(self):
        cc = ConnectionConfig()
        cc.connections["proc1"] = MagicMock()
        cc.user_to_process["u1"] = "proc1"
        cc.remove_connection("proc1")
        assert "proc1" not in cc.connections
        assert "u1" not in cc.user_to_process

    @pytest.mark.asyncio
    async def test_close_connection_found(self):
        cc = ConnectionConfig()
        ws = AsyncMock()
        cc.connections["proc1"] = ws
        await cc.close_connection("proc1")
        ws.close.assert_awaited_once()
        assert "proc1" not in cc.connections

    @pytest.mark.asyncio
    async def test_close_connection_missing(self):
        cc = ConnectionConfig()
        await cc.close_connection("nope")  # warns, no error

    @pytest.mark.asyncio
    async def test_close_connection_error(self):
        cc = ConnectionConfig()
        ws = AsyncMock()
        ws.close.side_effect = RuntimeError("boom")
        cc.connections["proc1"] = ws
        await cc.close_connection("proc1")
        assert "proc1" not in cc.connections


class TestSendStatusUpdateAsync:
    @pytest.mark.asyncio
    async def test_no_user_id(self):
        cc = ConnectionConfig()
        await cc.send_status_update_async("m", user_id="")  # early return

    @pytest.mark.asyncio
    async def test_fallback_single_user(self):
        cc = ConnectionConfig()
        ws = AsyncMock()
        cc.connections["proc1"] = ws
        cc.user_to_process["real"] = "proc1"
        await cc.send_status_update_async({"k": "v"}, user_id="wrong")
        ws.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_process_multiple_users(self):
        cc = ConnectionConfig()
        cc.user_to_process["a"] = "p1"
        cc.user_to_process["b"] = "p2"
        await cc.send_status_update_async("m", user_id="wrong")  # returns, no send

    @pytest.mark.asyncio
    async def test_message_with_to_dict(self):
        cc = ConnectionConfig()
        ws = AsyncMock()
        cc.connections["p1"] = ws
        cc.user_to_process["u1"] = "p1"
        msg = MagicMock()
        msg.to_dict.return_value = {"x": 1}
        await cc.send_status_update_async(msg, user_id="u1")
        ws.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_message_to_dict_error_falls_back_to_str(self):
        cc = ConnectionConfig()
        ws = AsyncMock()
        cc.connections["p1"] = ws
        cc.user_to_process["u1"] = "p1"
        msg = MagicMock()
        msg.to_dict.side_effect = RuntimeError("bad")
        await cc.send_status_update_async(msg, user_id="u1")
        ws.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_error_removes_connection(self):
        cc = ConnectionConfig()
        ws = AsyncMock()
        ws.send_text.side_effect = RuntimeError("boom")
        cc.connections["p1"] = ws
        cc.user_to_process["u1"] = "p1"
        await cc.send_status_update_async("m", user_id="u1")
        assert "p1" not in cc.connections

    @pytest.mark.asyncio
    async def test_no_connection_for_process(self):
        cc = ConnectionConfig()
        cc.user_to_process["u1"] = "p1"  # mapped but no connection object
        await cc.send_status_update_async("m", user_id="u1")
        assert "u1" not in cc.user_to_process


class TestSendStatusUpdateSync:
    @pytest.mark.asyncio
    async def test_sync_send_found(self):
        cc = ConnectionConfig()
        ws = AsyncMock()
        cc.connections["p1"] = ws
        cc.send_status_update("hello", "p1")
        await asyncio.sleep(0)
        ws.send_text.assert_awaited_once_with("hello")

    def test_sync_send_not_found(self):
        cc = ConnectionConfig()
        cc.send_status_update("hello", "missing")  # warns, no error


# ----------------------------------------------------------------------- #
# TeamConfig
# ----------------------------------------------------------------------- #
class TestTeamConfig:
    def test_set_and_get(self):
        tc = TeamConfig()
        team = MagicMock()
        tc.set_current_team("u1", team)
        assert tc.get_current_team("u1") is team

    def test_get_missing(self):
        tc = TeamConfig()
        assert tc.get_current_team("nope") is None


def test_module_singletons():
    assert isinstance(orchestration_config, OrchestrationConfig)
    assert isinstance(connection_config, ConnectionConfig)
    assert isinstance(team_config, TeamConfig)
