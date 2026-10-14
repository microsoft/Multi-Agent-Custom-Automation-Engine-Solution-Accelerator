"""Unit tests for backend.config.agent_registry.AgentRegistry.

The registry is a pure-stdlib singleton (threading + weakref + asyncio) with
no external dependencies, so these tests exercise it directly.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.config.agent_registry import AgentRegistry, agent_registry


class _Agent:
    """Minimal stand-in agent (weak-referenceable)."""

    def __init__(self, name="A"):
        self.agent_name = name


class TestRegisterUnregister:
    def test_register_and_count(self):
        reg = AgentRegistry()
        a = _Agent("one")
        reg.register_agent(a, user_id="u1")
        assert reg.get_agent_count() == 1
        assert a in reg.get_all_agents()
        assert reg._agent_metadata[id(a)]["user_id"] == "u1"
        assert reg._agent_metadata[id(a)]["name"] == "one"

    def test_register_uses_name_attr_fallback(self):
        reg = AgentRegistry()
        obj = MagicMock(spec=["name"])
        obj.name = "viaName"
        reg.register_agent(obj)
        assert reg._agent_metadata[id(obj)]["name"] == "viaName"

    def test_register_handles_exception(self):
        reg = AgentRegistry()
        # int is not weak-referenceable -> WeakSet.add raises -> handled
        reg.register_agent(12345)
        assert reg.get_agent_count() == 0

    def test_unregister_removes_metadata(self):
        reg = AgentRegistry()
        a = _Agent()
        reg.register_agent(a)
        reg.unregister_agent(a)
        assert reg.get_agent_count() == 0
        assert id(a) not in reg._agent_metadata

    def test_unregister_unknown_is_noop(self):
        reg = AgentRegistry()
        reg.unregister_agent(_Agent())  # never registered
        assert reg.get_agent_count() == 0


class TestRegistryStatus:
    def test_status_groups_by_type(self):
        reg = AgentRegistry()
        a, b = _Agent("a"), _Agent("b")  # keep strong refs (WeakSet)
        reg.register_agent(a)
        reg.register_agent(b)
        status = reg.get_registry_status()
        assert status["total_agents"] == 2
        assert status["agent_types"]["_Agent"] == 2


class TestCleanupAllAgents:
    @pytest.mark.asyncio
    async def test_cleanup_no_agents(self):
        reg = AgentRegistry()
        await reg.cleanup_all_agents()  # returns early, no error
        assert reg.get_agent_count() == 0

    @pytest.mark.asyncio
    async def test_cleanup_closes_async_agents(self):
        reg = AgentRegistry()
        agent = MagicMock()
        agent.agent_name = "closer"
        agent.close = AsyncMock()
        reg.register_agent(agent)
        await reg.cleanup_all_agents()
        agent.close.assert_awaited_once()
        assert reg.get_agent_count() == 0

    @pytest.mark.asyncio
    async def test_cleanup_sync_close(self):
        reg = AgentRegistry()
        agent = MagicMock()
        agent.agent_name = "sync"
        agent.close = MagicMock()  # not a coroutine
        reg.register_agent(agent)
        await reg.cleanup_all_agents()
        agent.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_agent_without_close(self):
        reg = AgentRegistry()
        agent = _Agent("noclose")  # no close() method
        reg.register_agent(agent)
        await reg.cleanup_all_agents()
        assert reg.get_agent_count() == 0

    @pytest.mark.asyncio
    async def test_cleanup_handles_close_error(self):
        reg = AgentRegistry()
        agent = MagicMock()
        agent.agent_name = "boom"
        agent.close = AsyncMock(side_effect=RuntimeError("fail"))
        reg.register_agent(agent)
        await reg.cleanup_all_agents()  # error captured by gather, not raised
        assert reg.get_agent_count() == 0


class TestSafeCloseAgent:
    @pytest.mark.asyncio
    async def test_safe_close_sync(self):
        reg = AgentRegistry()
        agent = MagicMock()
        agent.name = "s"
        agent.close = MagicMock()
        await reg._safe_close_agent(agent)
        agent.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_close_swallows_error(self):
        reg = AgentRegistry()
        agent = MagicMock()
        agent.name = "s"
        agent.close = MagicMock(side_effect=ValueError("x"))
        await reg._safe_close_agent(agent)  # must not raise


def test_module_singleton_exists():
    assert isinstance(agent_registry, AgentRegistry)
