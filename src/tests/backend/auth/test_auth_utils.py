# src/tests/backend/auth/test_auth_utils.py

import sys
import os
import types
import base64
import json
import pytest

# --- Stub out backend.auth.sample_user.sample_user for dev mode ---
sample_pkg = types.ModuleType("backend.auth.sample_user")
sample_pkg.sample_user = {
    "x-ms-client-principal-id": "dev-id",
    "x-ms-client-principal-name": "dev-name",
    "x-ms-client-principal-idp": "dev-idp",
    "x-ms-token-aad-id-token": "dev-token",
    "x-ms-client-principal": base64.b64encode(
        json.dumps({"tid": "tenant123"}).encode("utf-8")
    ).decode("utf-8"),
}
sys.modules["backend.auth.sample_user"] = sample_pkg

# --- Ensure src is on PYTHONPATH ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from backend.auth.auth_utils import get_authenticated_user_details, get_tenantid

def test_get_authenticated_user_details_dev_mode():
    # No EasyAuth headers => uses sample_user stub
    headers = {}
    user = get_authenticated_user_details(headers)
    assert user["user_principal_id"] == "dev-id"
    assert user["user_name"] == "dev-name"
    assert user["auth_provider"] == "dev-idp"
    assert user["auth_token"] == "dev-token"
    assert user["client_principal_b64"] == sample_pkg.sample_user["x-ms-client-principal"]
    assert user["aad_id_token"] == "dev-token"

def test_get_authenticated_user_details_prod_mode():
    # Lowercase header names to trigger the prod branch
    headers = {
        "x-ms-client-principal-id": "real-id",
        "x-ms-client-principal-name": "real-name",
        "x-ms-client-principal-idp": "real-idp",
        "x-ms-token-aad-id-token": "real-token",
        "x-ms-client-principal": "b64payload",
    }
    user = get_authenticated_user_details(headers)
    assert user["user_principal_id"] == "real-id"
    assert user["user_name"] == "real-name"
    assert user["auth_provider"] == "real-idp"
    assert user["auth_token"] == "real-token"
    assert user["client_principal_b64"] == "b64payload"
    assert user["aad_id_token"] == "real-token"

def test_get_tenantid_with_valid_b64():
    payload = {"tid": "tenantXYZ", "foo": "bar"}
    b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    assert get_tenantid(b64) == "tenantXYZ"

def test_get_tenantid_with_invalid_b64(caplog):
    caplog.set_level("ERROR")
    # Malformed base64 should be caught and return empty string
    assert get_tenantid("not-a-valid-b64") == ""
    assert "Exception" in caplog.text or caplog.text  # ensure we logged something
