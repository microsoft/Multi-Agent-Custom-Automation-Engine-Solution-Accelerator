"""
Test configuration for auth module tests.
"""

import pytest
import sys
import os
import base64
import json

# Add the backend directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

@pytest.fixture
def mock_sample_headers():
    """Mock headers with EasyAuth authentication data."""
    return {
        "x-ms-client-principal-id": "12345678-1234-1234-1234-123456789012",
        "x-ms-client-principal-name": "testuser@example.com",
        "x-ms-client-principal-idp": "aad",
        "x-ms-token-aad-id-token": "sample.jwt.token",
        "x-ms-client-principal": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsInRpZCI6IjEyMzQ1Njc4LTEyMzQtMTIzNC0xMjM0LTEyMzQ1Njc4OTAxMiJ9"
    }

@pytest.fixture
def mock_empty_headers():
    """Mock headers without authentication data."""
    return {
        "content-type": "application/json",
        "user-agent": "test-agent"
    }

@pytest.fixture
def mock_valid_base64_principal():
    """Mock valid base64 encoded principal with tenant ID."""
    mock_data = {
        "typ": "JWT",
        "alg": "RS256",
        "tid": "87654321-4321-4321-4321-210987654321",
        "oid": "12345678-1234-1234-1234-123456789012",
        "preferred_username": "testuser@example.com",
        "name": "Test User"
    }
    
    json_str = json.dumps(mock_data)
    return base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

@pytest.fixture
def mock_invalid_base64_principal():
    """Mock invalid base64 encoded principal."""
    return "invalid_base64_string!"

@pytest.fixture
def sample_user_mock():
    """Mock sample_user data for testing."""
    return {
        "x-ms-client-principal-id": "00000000-0000-0000-0000-000000000000",
        "x-ms-client-principal-name": "testusername@contoso.com",
        "x-ms-client-principal-idp": "aad",
        "x-ms-token-aad-id-token": "your_aad_id_token",
        "x-ms-client-principal": "your_base_64_encoded_token"
    }