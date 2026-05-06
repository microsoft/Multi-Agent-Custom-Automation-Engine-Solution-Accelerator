# Copyright (c) Microsoft. All rights reserved.
"""Tests for models/messages.py — all message dataclasses."""

import dataclasses
import os
import sys

import pytest

# backend/models/messages.py has internal imports from common.models.messages
# and models.plan_models using paths relative to src/backend/.  Add src/backend/
# to sys.path so those internal imports resolve when we load backend.models.messages.
_backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')
)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from backend.models.messages import (AgentMessage, AgentMessageStreaming,
                                     AgentStreamEnd, AgentStreamStart,
                                     AgentToolCall, AgentToolMessage,
                                     PlanApprovalRequest, PlanApprovalResponse,
                                     ReplanApprovalRequest,
                                     ReplanApprovalResponse,
                                     UserClarificationRequest,
                                     UserClarificationResponse)
from backend.models.plan_models import MPlan, MStep, PlanStatus


class TestAgentMessage:
    def test_construction(self):
        msg = AgentMessage(agent_name="Bot", timestamp="2026-01-01T00:00:00", content="hello")
        assert msg.agent_name == "Bot"
        assert msg.timestamp == "2026-01-01T00:00:00"
        assert msg.content == "hello"

    def test_to_dict(self):
        msg = AgentMessage(agent_name="Bot", timestamp="t", content="c")
        d = msg.to_dict()
        assert d == {"agent_name": "Bot", "timestamp": "t", "content": "c"}

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(AgentMessage)


class TestAgentStreamStart:
    def test_construction(self):
        obj = AgentStreamStart(agent_name="A")
        assert obj.agent_name == "A"

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(AgentStreamStart)


class TestAgentStreamEnd:
    def test_construction(self):
        obj = AgentStreamEnd(agent_name="A")
        assert obj.agent_name == "A"

    def test_is_dataclass(self):
        assert dataclasses.is_dataclass(AgentStreamEnd)


class TestAgentMessageStreaming:
    def test_defaults(self):
        obj = AgentMessageStreaming(agent_name="Bot", content="chunk")
        assert obj.is_final is False

    def test_final_flag(self):
        obj = AgentMessageStreaming(agent_name="Bot", content="last", is_final=True)
        assert obj.is_final is True

    def test_to_dict(self):
        obj = AgentMessageStreaming(agent_name="Bot", content="x", is_final=False)
        d = obj.to_dict()
        assert d == {"agent_name": "Bot", "content": "x", "is_final": False}


class TestAgentToolCall:
    def test_construction(self):
        tc = AgentToolCall(tool_name="search", arguments={"query": "foo"})
        assert tc.tool_name == "search"
        assert tc.arguments == {"query": "foo"}

    def test_to_dict(self):
        tc = AgentToolCall(tool_name="t", arguments={"k": "v"})
        assert tc.to_dict() == {"tool_name": "t", "arguments": {"k": "v"}}


class TestAgentToolMessage:
    def test_default_empty_tools(self):
        msg = AgentToolMessage(agent_name="Bot")
        assert msg.tool_calls == []

    def test_with_tool_calls(self):
        tc = AgentToolCall(tool_name="fn", arguments={})
        msg = AgentToolMessage(agent_name="Bot", tool_calls=[tc])
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].tool_name == "fn"

    def test_to_dict(self):
        tc = AgentToolCall(tool_name="fn", arguments={"a": 1})
        msg = AgentToolMessage(agent_name="Bot", tool_calls=[tc])
        d = msg.to_dict()
        assert d["agent_name"] == "Bot"
        assert d["tool_calls"][0]["tool_name"] == "fn"


class TestPlanApprovalRequest:
    def test_construction(self):
        plan = MPlan(user_request="do x")
        req = PlanApprovalRequest(plan=plan, status=PlanStatus.CREATED)
        assert req.plan.user_request == "do x"
        assert req.status == PlanStatus.CREATED
        assert req.context is None

    def test_with_context(self):
        plan = MPlan()
        req = PlanApprovalRequest(plan=plan, status=PlanStatus.RUNNING, context={"key": "val"})
        assert req.context == {"key": "val"}


class TestPlanApprovalResponse:
    def test_defaults(self):
        resp = PlanApprovalResponse(m_plan_id="mp1", approved=True)
        assert resp.feedback is None
        assert resp.plan_id is None

    def test_rejection(self):
        resp = PlanApprovalResponse(m_plan_id="mp1", approved=False, feedback="not good")
        assert resp.approved is False
        assert resp.feedback == "not good"


class TestReplanApprovalRequest:
    def test_construction(self):
        plan = MPlan()
        req = ReplanApprovalRequest(new_plan=plan, reason="step failed")
        assert req.reason == "step failed"
        assert req.context is None

    def test_with_context(self):
        plan = MPlan()
        req = ReplanApprovalRequest(new_plan=plan, reason="r", context={"x": 1})
        assert req.context == {"x": 1}


class TestReplanApprovalResponse:
    def test_defaults(self):
        resp = ReplanApprovalResponse(plan_id="p1", approved=True)
        assert resp.feedback is None

    def test_rejection(self):
        resp = ReplanApprovalResponse(plan_id="p1", approved=False, feedback="redo it")
        assert resp.approved is False
        assert resp.feedback == "redo it"


class TestUserClarificationRequest:
    def test_construction(self):
        req = UserClarificationRequest(question="Which region?", request_id="r1")
        assert req.question == "Which region?"
        assert req.request_id == "r1"


class TestUserClarificationResponse:
    def test_defaults(self):
        resp = UserClarificationResponse(request_id="r1")
        assert resp.answer == ""
        assert resp.plan_id == ""
        assert resp.m_plan_id == ""

    def test_with_answer(self):
        resp = UserClarificationResponse(request_id="r1", answer="East US", plan_id="p1", m_plan_id="mp1")
        assert resp.answer == "East US"
        assert resp.plan_id == "p1"
        assert resp.m_plan_id == "mp1"
