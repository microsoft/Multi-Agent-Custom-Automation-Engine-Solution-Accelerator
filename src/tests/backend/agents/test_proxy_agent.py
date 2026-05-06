"""Unit tests for agents.proxy_agent (ProxyAgent — GA agent_framework 1.2.2).

Ported from src/tests/backend/v4/magentic_agents/test_proxy_agent.py.
Key changes:
  - Mock paths updated to GA type names (AgentResponse, AgentResponseUpdate, etc.)
  - Import path: agents.proxy_agent (not backend.v4.magentic_agents.proxy_agent)
  - Tests directly exercise ProxyAgent methods rather than standalone logic helpers
  - GA BaseAgent uses name/description kwargs instead of positional args
"""

import asyncio
import logging
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Module stubs — must be set before importing proxy_agent
# ---------------------------------------------------------------------------

# GA agent_framework mocks
# BaseAgent must be a real class so ProxyAgent can inherit from it and call
# super().__init__() without hitting Mock's side_effect iterator machinery.
class _FakeBaseAgent:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.name = kwargs.get("name", "")
        self.description = kwargs.get("description", "")


# Message must be a real class so isinstance(x, Message) works in proxy_agent code.
class _FakeMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text


mock_agent_response_cls = Mock()
mock_agent_response_update_cls = Mock()
mock_message_cls = _FakeMessage
mock_content_cls = Mock()
mock_response_stream_cls = Mock()
mock_agent_session_cls = Mock()
mock_usage_details_cls = Mock()

mock_agent_fw = Mock()
mock_agent_fw.BaseAgent = _FakeBaseAgent
mock_agent_fw.AgentResponse = mock_agent_response_cls
mock_agent_fw.AgentResponseUpdate = mock_agent_response_update_cls
mock_agent_fw.Message = mock_message_cls
mock_agent_fw.Content = mock_content_cls
mock_agent_fw.ResponseStream = mock_response_stream_cls
mock_agent_fw.AgentSession = mock_agent_session_cls
mock_agent_fw.UsageDetails = mock_usage_details_cls

sys.modules["agent_framework"] = mock_agent_fw

# orchestration.connection_config stubs
mock_connection_config = Mock()
mock_orchestration_config = Mock()
mock_orchestration_config.default_timeout = 300

mock_connection_config_mod = Mock()
mock_connection_config_mod.connection_config = mock_connection_config
mock_connection_config_mod.orchestration_config = mock_orchestration_config
sys.modules.setdefault("orchestration", Mock())
sys.modules["orchestration.connection_config"] = mock_connection_config_mod

# v4.models.messages stubs
mock_user_clarification_request_cls = Mock()
mock_user_clarification_response_cls = Mock()
mock_timeout_notification_cls = Mock()
mock_ws_message_type = Mock()
mock_ws_message_type.USER_CLARIFICATION_REQUEST = "USER_CLARIFICATION_REQUEST"
mock_ws_message_type.TIMEOUT_NOTIFICATION = "TIMEOUT_NOTIFICATION"

mock_v4_messages = Mock()
mock_v4_messages.UserClarificationRequest = mock_user_clarification_request_cls
mock_v4_messages.UserClarificationResponse = mock_user_clarification_response_cls
mock_v4_messages.TimeoutNotification = mock_timeout_notification_cls
mock_v4_messages.WebsocketMessageType = mock_ws_message_type
sys.modules.setdefault("v4", Mock())
sys.modules.setdefault("v4.models", Mock())
sys.modules["v4.models.messages"] = mock_v4_messages

# Now import the module under test (full backend.* path as per project convention)
from backend.agents.proxy_agent import ProxyAgent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(text: str) -> _FakeMessage:
    """Return a _FakeMessage instance (passes isinstance(x, Message) check)."""
    return _FakeMessage(text)


def _make_session(session_id: str = "sess-1"):
    session = Mock()
    session.session_id = session_id
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProxyAgentInit:
    """Tests for ProxyAgent.__init__."""

    def test_default_params(self):
        agent = ProxyAgent()
        assert agent.user_id == ""
        assert agent._timeout == 300  # from mock_orchestration_config.default_timeout

    def test_with_user_id(self):
        agent = ProxyAgent(user_id="alice")
        assert agent.user_id == "alice"

    def test_custom_timeout(self):
        agent = ProxyAgent(timeout_seconds=60)
        assert agent._timeout == 60

    def test_custom_name_and_description(self):
        agent = ProxyAgent(name="MyProxy", description="custom desc")
        # BaseAgent.__init__ would receive name and description via super().__init__


class TestCreateSession:
    """Tests for ProxyAgent.create_session."""

    def test_returns_agent_session(self):
        mock_session = Mock()
        mock_agent_session_cls.return_value = mock_session

        agent = ProxyAgent()
        result = agent.create_session()

        mock_agent_session_cls.assert_called_once_with(session_id=None)
        assert result is mock_session

    def test_with_session_id(self):
        mock_session = Mock()
        mock_agent_session_cls.return_value = mock_session

        agent = ProxyAgent()
        agent.create_session(session_id="my-session")

        mock_agent_session_cls.assert_called_with(session_id="my-session")


class TestExtractMessageText:
    """Tests for ProxyAgent._extract_message_text."""

    def setup_method(self):
        self.agent = ProxyAgent()

    def test_none(self):
        assert self.agent._extract_message_text(None) == ""

    def test_empty_string(self):
        assert self.agent._extract_message_text("") == ""

    def test_plain_string(self):
        assert self.agent._extract_message_text("hello") == "hello"

    def test_message_object_with_text(self):
        # _FakeMessage is the Message class seen by proxy_agent (set in sys.modules).
        # isinstance(msg, Message) is True so _extract_message_text returns msg.text.
        msg = _make_message("from message")
        assert self.agent._extract_message_text(msg) == "from message"

    def test_list_of_strings(self):
        assert self.agent._extract_message_text(["hello", "world"]) == "hello world"

    def test_empty_list(self):
        assert self.agent._extract_message_text([]) == ""

    def test_arbitrary_object_fallback(self):
        obj = SimpleNamespace()  # not str, Message, or list
        result = self.agent._extract_message_text(obj)
        assert isinstance(result, str)


class TestRun:
    """Tests for ProxyAgent.run dispatch."""

    def test_streaming_returns_response_stream(self):
        """run(stream=True) wraps _invoke_stream_internal in a ResponseStream."""
        mock_stream = Mock()
        mock_response_stream_cls.return_value = mock_stream

        agent = ProxyAgent()
        result = agent.run("hello", stream=True)

        assert result is mock_stream
        mock_response_stream_cls.assert_called_once()

    def test_non_streaming_returns_coroutine(self):
        """run(stream=False) returns an awaitable (coroutine)."""
        import inspect

        agent = ProxyAgent()
        result = agent.run("hello", stream=False)
        assert inspect.isawaitable(result)

        # Clean up coroutine to avoid RuntimeWarning
        result.close()


class TestWaitForUserClarification:
    """Tests for ProxyAgent._wait_for_user_clarification."""

    @pytest.mark.asyncio
    async def test_successful_response(self):
        """Returns UserClarificationResponse when clarification arrives."""
        mock_orchestration_config.set_clarification_pending = Mock()
        mock_orchestration_config.wait_for_clarification = AsyncMock(return_value="my answer")
        mock_orchestration_config.clarifications = {}

        mock_response = Mock()
        mock_user_clarification_response_cls.return_value = mock_response

        agent = ProxyAgent()
        result = await agent._wait_for_user_clarification("req-123")

        assert result is mock_response
        mock_user_clarification_response_cls.assert_called_once_with(
            request_id="req-123", answer="my answer"
        )

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        """asyncio.TimeoutError causes None return (and timeout notification sent)."""
        mock_orchestration_config.set_clarification_pending = Mock()
        mock_orchestration_config.wait_for_clarification = AsyncMock(
            side_effect=asyncio.TimeoutError
        )
        mock_orchestration_config.cleanup_clarification = Mock()
        mock_orchestration_config.clarifications = {}
        mock_connection_config.send_status_update_async = AsyncMock()

        agent = ProxyAgent(user_id="alice")
        result = await agent._wait_for_user_clarification("req-timeout")

        assert result is None

    @pytest.mark.asyncio
    async def test_cancelled_returns_none(self):
        """asyncio.CancelledError causes None return and cleanup."""
        mock_orchestration_config.set_clarification_pending = Mock()
        mock_orchestration_config.wait_for_clarification = AsyncMock(
            side_effect=asyncio.CancelledError
        )
        mock_orchestration_config.cleanup_clarification = Mock()
        mock_orchestration_config.clarifications = {}

        agent = ProxyAgent()
        result = await agent._wait_for_user_clarification("req-cancel")

        assert result is None
        mock_orchestration_config.cleanup_clarification.assert_called_with("req-cancel")

    @pytest.mark.asyncio
    async def test_key_error_returns_none(self):
        """KeyError returns None without cleanup call."""
        mock_orchestration_config.set_clarification_pending = Mock()
        mock_orchestration_config.wait_for_clarification = AsyncMock(
            side_effect=KeyError("bad-id")
        )
        mock_orchestration_config.clarifications = {}

        agent = ProxyAgent()
        result = await agent._wait_for_user_clarification("req-keyerr")

        assert result is None

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_none(self):
        """Unexpected exception returns None and triggers cleanup."""
        mock_orchestration_config.set_clarification_pending = Mock()
        mock_orchestration_config.wait_for_clarification = AsyncMock(
            side_effect=RuntimeError("unexpected")
        )
        mock_orchestration_config.cleanup_clarification = Mock()
        mock_orchestration_config.clarifications = {}

        agent = ProxyAgent()
        result = await agent._wait_for_user_clarification("req-err")

        assert result is None
        mock_orchestration_config.cleanup_clarification.assert_called_with("req-err")


class TestNotifyTimeout:
    """Tests for ProxyAgent._notify_timeout."""

    @pytest.mark.asyncio
    async def test_sends_notification_and_cleans_up(self):
        mock_connection_config.send_status_update_async = AsyncMock()
        mock_orchestration_config.cleanup_clarification = Mock()
        mock_notice = Mock()
        mock_timeout_notification_cls.return_value = mock_notice

        agent = ProxyAgent(user_id="bob", timeout_seconds=30)
        await agent._notify_timeout("req-notify")

        mock_connection_config.send_status_update_async.assert_called_once()
        mock_orchestration_config.cleanup_clarification.assert_called_with("req-notify")

    @pytest.mark.asyncio
    async def test_send_failure_is_swallowed(self):
        """If sending the notification fails, no exception propagates."""
        mock_connection_config.send_status_update_async = AsyncMock(
            side_effect=Exception("ws error")
        )
        mock_orchestration_config.cleanup_clarification = Mock()
        mock_timeout_notification_cls.return_value = Mock()

        agent = ProxyAgent()
        await agent._notify_timeout("req-err")  # should not raise

        mock_orchestration_config.cleanup_clarification.assert_called_with("req-err")


class TestInvokeStreamInternal:
    """Tests for ProxyAgent._invoke_stream_internal (end-to-end flow)."""

    @pytest.mark.asyncio
    async def test_successful_clarification_yields_updates(self):
        """Successful flow yields text update then usage update."""
        mock_orchestration_config.set_clarification_pending = Mock()
        mock_orchestration_config.wait_for_clarification = AsyncMock(return_value="42")
        mock_orchestration_config.cleanup_clarification = Mock()
        mock_orchestration_config.clarifications = {}
        mock_connection_config.send_status_update_async = AsyncMock()

        clarification_req = Mock()
        clarification_req.request_id = "req-1"
        mock_user_clarification_request_cls.return_value = clarification_req

        clarification_resp = Mock()
        clarification_resp.answer = "42"
        mock_user_clarification_response_cls.return_value = clarification_resp

        mock_text_content = Mock()
        mock_usage_content = Mock()
        mock_content_cls.from_text = Mock(return_value=mock_text_content)
        mock_content_cls.from_usage = Mock(return_value=mock_usage_content)

        mock_update_text = Mock()
        mock_update_usage = Mock()
        mock_agent_response_update_cls.side_effect = [mock_update_text, mock_update_usage]

        agent = ProxyAgent(user_id="user1")
        updates = []
        async for update in agent._invoke_stream_internal("What is 6×7?", None):
            updates.append(update)

        assert len(updates) == 2
        assert updates[0] is mock_update_text
        assert updates[1] is mock_update_usage

    @pytest.mark.asyncio
    async def test_timeout_yields_nothing(self):
        """Timeout path: no updates are yielded."""
        mock_orchestration_config.set_clarification_pending = Mock()
        mock_orchestration_config.wait_for_clarification = AsyncMock(
            side_effect=asyncio.TimeoutError
        )
        mock_orchestration_config.cleanup_clarification = Mock()
        mock_orchestration_config.clarifications = {}
        mock_connection_config.send_status_update_async = AsyncMock()

        clarification_req = Mock()
        clarification_req.request_id = "req-2"
        mock_user_clarification_request_cls.return_value = clarification_req
        mock_timeout_notification_cls.return_value = Mock()

        agent = ProxyAgent(user_id="user2")
        updates = []
        async for update in agent._invoke_stream_internal("help?", _make_session()):
            updates.append(update)

        assert updates == []
