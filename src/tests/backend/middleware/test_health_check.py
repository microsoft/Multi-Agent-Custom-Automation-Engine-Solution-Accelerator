# src/tests/backend/middleware/test_health_check.py

import pytest
import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.middleware.health_check import (
    HealthCheckResult,
    HealthCheckSummary,
    HealthCheckMiddleware,
)


# --- Tests for HealthCheckResult and HealthCheckSummary ---

def test_health_check_result_attributes():
    res = HealthCheckResult(status=True, message="All good")
    assert res.status is True
    assert res.message == "All good"


def test_health_check_summary_add_and_default():
    summary = HealthCheckSummary()
    # Initially status True, no results
    assert summary.status is True
    assert summary.results == {}

    # Add default
    summary.AddDefault()
    assert "Default" in summary.results
    assert isinstance(summary.results["Default"], HealthCheckResult)
    assert summary.results["Default"].status is True
    assert summary.status is True

    # Add a failing result
    summary.Add("FailTest", HealthCheckResult(False, "fail"))
    assert summary.results["FailTest"].status is False
    # Overall status now False
    assert summary.status is False


def test_health_check_summary_add_exception():
    summary = HealthCheckSummary()
    summary.AddDefault()

    class CustomError(Exception):
        pass

    summary.AddException("ErrTest", CustomError("oops"))
    assert "ErrTest" in summary.results
    assert summary.results["ErrTest"].status is False
    assert "oops" in summary.results["ErrTest"].message


# --- A real coroutine function that returns HealthCheckResult ---

async def real_pass_check():
    await asyncio.sleep(0)
    return HealthCheckResult(True, "ok")


async def real_fail_check():
    await asyncio.sleep(0)
    return HealthCheckResult(False, "not ok")


# --- Tests for HealthCheckMiddleware.check ---

@pytest.mark.asyncio
async def test_check_invalid_pass_and_fail(monkeypatch, caplog):
    """
    By default, HealthCheckMiddleware.check inspects `hasattr(check, "__await__")`
    on the check object itself. A bare `async def foo` is a function object that
    does NOT have __await__ at the function level—only its coroutine instance does.
    Hence both entries will be treated as invalid and immediately go to AddException.
    """
    caplog.set_level(logging.ERROR)

    checks = {
        "pass": real_pass_check,
        "fail": real_fail_check,
    }
    mw = HealthCheckMiddleware(app=None, checks=checks)
    summary = await mw.check()

    # "Default" should still be present
    assert "Default" in summary.results

    # Both "pass" and "fail" are treated as "not a coroutine function"
    assert summary.results["pass"].status is False
    assert "not a coroutine function" in summary.results["pass"].message

    assert summary.results["fail"].status is False
    assert "not a coroutine function" in summary.results["fail"].message

    # Overall status is False (because exceptions were raised)
    assert summary.status is False


@pytest.mark.asyncio
async def test_check_with_exception_in_coroutine(monkeypatch, caplog):
    caplog.set_level(logging.ERROR)

    # We build a fake awaitable object whose __await__ is present at the instance level
    async def raising_coro():
        raise RuntimeError("boom")

    class AsyncErrorCheck:
        def __call__(self):
            return raising_coro()

        def __await__(self):
            return raising_coro().__await__()

    checks = {
        "error": AsyncErrorCheck(),
    }
    mw = HealthCheckMiddleware(app=None, checks=checks)
    summary = await mw.check()

    # "Default" + "error"
    assert "Default" in summary.results
    assert "error" in summary.results

    # Because raising_coro throws, it should end up in AddException
    assert summary.results["error"].status is False
    assert "boom" in summary.results["error"].message

    # Overall status is False
    assert summary.status is False


# --- Tests for dispatch behavior using TestClient ---

@pytest.fixture
def app_with_middleware():
    app = FastAPI()

    # We build two awaitable‐styled objects: one that passes, one that fails
    class AsyncPassCheck:
        def __call__(self):
            return real_pass_check()

        def __await__(self):
            return real_pass_check().__await__()

    class AsyncFailCheck:
        def __call__(self):
            return real_fail_check()

        def __await__(self):
            return real_fail_check().__await__()

    checks = {
        "c1": AsyncPassCheck(),
        "c2": AsyncFailCheck(),
    }
    # Attach HealthCheckMiddleware with a password
    app.add_middleware(HealthCheckMiddleware, checks=checks, password="secret")

    @app.get("/hello")
    async def hello():
        return {"msg": "world"}

    return app


def test_dispatch_healthz_no_password(app_with_middleware):
    client = TestClient(app_with_middleware)
    # c2 returns False, so overall summary.status is False → 503
    response = client.get("/healthz")
    assert response.status_code == 503
    assert response.text == "Service Unavailable"


def test_dispatch_healthz_with_password_json(app_with_middleware):
    client = TestClient(app_with_middleware)
    response = client.get("/healthz?code=secret")
    assert response.status_code == 503  # still 503 because c2 failed

    json_body = response.json()
    # The JSON‐serialized HealthCheckSummary should contain keys "status" and "results"
    assert "status" in json_body
    assert "results" in json_body
    assert json_body["status"] is False
    # Both checks must appear
    assert "c1" in json_body["results"]
    assert "c2" in json_body["results"]


def test_dispatch_non_healthz_calls_next(app_with_middleware):
    client = TestClient(app_with_middleware)
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"msg": "world"}
