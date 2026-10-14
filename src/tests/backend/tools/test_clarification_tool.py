"""Unit tests for backend.tools.clarification_tool.

Covers the shared answer store (store_answer / pop_answer) and the
approval-gated request_user_clarification tool body (thread-local lookup,
fallback, and no-answer error path).
"""

import threading

import backend.tools.clarification_tool as ct
from backend.tools.clarification_tool import (
    pop_answer,
    request_user_clarification,
    store_answer,
)


def _clear_store():
    ct._pending_answers.clear()


class TestAnswerStore:
    def test_store_and_pop(self):
        _clear_store()
        store_answer("req1", "the answer")
        assert pop_answer("req1") == "the answer"
        # popped -> gone
        assert pop_answer("req1") == ""

    def test_pop_missing_returns_empty(self):
        _clear_store()
        assert pop_answer("nope") == ""


class TestRequestUserClarification:
    def test_thread_local_answer(self):
        _clear_store()
        thread_key = f"_clarification_{threading.current_thread().ident}"
        ct._pending_answers[thread_key] = "threaded answer"
        assert request_user_clarification("q?") == "threaded answer"

    def test_fallback_to_any_remaining(self):
        _clear_store()
        ct._pending_answers["some_request_id"] = "fallback answer"
        assert request_user_clarification("q?") == "fallback answer"

    def test_no_answer_returns_error(self):
        _clear_store()
        result = request_user_clarification("q?")
        assert result == "Error: No answer was provided by the user."
