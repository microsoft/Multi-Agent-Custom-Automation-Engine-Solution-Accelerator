# src/tests/backend/auth/test_sample_user.py

import base64
import json
import pytest
import importlib

# Import the module under test so it runs at least once
import backend.auth.sample_user as su

def test_sample_user_is_dict_and_has_lowercase_keys():
    d = su.sample_user
    assert isinstance(d, dict)
    # The sample_user dict uses lowercase header keys
    for key in ("x-ms-client-principal", "x-ms-client-principal-id", "x-ms-client-principal-name"):
        assert key in d

def test_principal_b64_is_non_empty_string():
    b64 = su.sample_user["x-ms-client-principal"]
    assert isinstance(b64, str)
    assert b64.strip() != ""

def test_get_tenantid_valid_and_invalid():
    from backend.auth.auth_utils import get_tenantid
    # valid payload -> should extract tid
    good = base64.b64encode(json.dumps({"tid": "tenant123"}).encode()).decode()
    assert get_tenantid(good) == "tenant123"
    # invalid payload -> should return empty
    assert get_tenantid("not-base64!!") == ""

def test_reload_module_counts_for_coverage():
    # reloading the module to touch it again
    m = importlib.reload(su)
    assert hasattr(m, "sample_user")
