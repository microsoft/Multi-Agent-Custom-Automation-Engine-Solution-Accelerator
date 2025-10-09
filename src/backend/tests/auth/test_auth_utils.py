from unittest.mock import patch, Mock
import base64
import json

from src.backend.auth.auth_utils import get_authenticated_user_details, get_tenantid


def test_get_authenticated_user_details_with_headers():
    """Test get_authenticated_user_details with valid headers."""
    request_headers = {
        "x-ms-client-principal-id": "test-user-id",
        "x-ms-client-principal-name": "test-user-name",
        "x-ms-client-principal-idp": "test-auth-provider",
        "x-ms-token-aad-id-token": "test-auth-token",
        "x-ms-client-principal": "test-client-principal-b64",
    }

    result = get_authenticated_user_details(request_headers)

    assert result["user_principal_id"] == "test-user-id"
    assert result["user_name"] == "test-user-name"
    assert result["auth_provider"] == "test-auth-provider"
    assert result["auth_token"] == "test-auth-token"
    assert result["client_principal_b64"] == "test-client-principal-b64"
    assert result["aad_id_token"] == "test-auth-token"


def test_get_tenantid_with_valid_b64():
    """Test get_tenantid with a valid base64-encoded JSON string."""
    valid_b64 = base64.b64encode(
        json.dumps({"tid": "test-tenant-id"}).encode("utf-8")
    ).decode("utf-8")

    tenant_id = get_tenantid(valid_b64)

    assert tenant_id == "test-tenant-id"


def test_get_tenantid_with_empty_b64():
    """Test get_tenantid with an empty base64 string."""
    tenant_id = get_tenantid("")
    assert tenant_id == ""


@patch("auth.auth_utils.logging.getLogger", return_value=Mock())
def test_get_tenantid_with_invalid_b64(mock_logger):
    """Test get_tenantid with an invalid base64-encoded string."""
    invalid_b64 = "invalid-base64"

    tenant_id = get_tenantid(invalid_b64)

    assert tenant_id == ""
    mock_logger().exception.assert_called_once()
