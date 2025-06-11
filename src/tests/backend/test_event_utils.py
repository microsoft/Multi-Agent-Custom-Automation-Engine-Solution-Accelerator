# src/tests/backend/test_event_utils.py

import os
import logging
import types
import sys
import pytest

# --- Stub out azure.monitor.events.extension.track_event so import won't fail ---
azure_pkg = types.ModuleType("azure")
monitor_pkg = types.ModuleType("azure.monitor")
events_pkg = types.ModuleType("azure.monitor.events")
extension_pkg = types.ModuleType("azure.monitor.events.extension")

# we don't need a real implementation here
extension_pkg.track_event = lambda name, data: None

azure_pkg.monitor = monitor_pkg
monitor_pkg.events = events_pkg
events_pkg.extension = extension_pkg

sys.modules["azure"] = azure_pkg
sys.modules["azure.monitor"] = monitor_pkg
sys.modules["azure.monitor.events"] = events_pkg
sys.modules["azure.monitor.events.extension"] = extension_pkg

# now import the function under test
import backend.event_utils as eu

@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # ensure the Application Insights key is unset by default
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    yield

def test_skip_when_not_configured(caplog):
    caplog.set_level(logging.WARNING)
    called = False
    # patch eu.track_event itself so even if config were set, nothing runs
    def fake(name, data):
        nonlocal called
        called = True

    setattr(eu, "track_event", fake)
    eu.track_event_if_configured("TestEvent", {"foo": "bar"})
    assert not called
    assert "Skipping track_event for TestEvent as Application Insights is not configured" in caplog.text

def test_track_when_configured(monkeypatch):
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "ikey")
    calls = []
    def fake(name, data):
        calls.append((name, data))

    setattr(eu, "track_event", fake)
    eu.track_event_if_configured("MyEvent", {"a": 1})
    assert calls == [("MyEvent", {"a": 1})]

def test_attribute_error_is_caught(monkeypatch, caplog):
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "ikey")
    caplog.set_level(logging.WARNING)

    def bad(name, data):
        raise AttributeError("missing resource")
    setattr(eu, "track_event", bad)

    eu.track_event_if_configured("Evt", {"x": 2})
    assert "ProxyLogger error in track_event: missing resource" in caplog.text

def test_other_exception_is_caught(monkeypatch, caplog):
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "ikey")
    caplog.set_level(logging.WARNING)

    def bad(name, data):
        raise RuntimeError("boom")
    setattr(eu, "track_event", bad)

    eu.track_event_if_configured("Evt2", {"y": 3})
    assert "Error in track_event: boom" in caplog.text
