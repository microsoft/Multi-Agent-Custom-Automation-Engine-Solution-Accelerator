import base64
import json
import logging
import os
import threading
import time

import jwt

# Signing keys are refreshed at most once per minute for an unknown key id
# (prevents key-download storms from forged tokens) and at least once a day.
_JWKS_MIN_REFRESH_SECONDS = 60
_JWKS_MAX_AGE_SECONDS = 24 * 60 * 60
_jwks_lock = threading.Lock()
_jwks_keys = {}
_jwks_fetched_at = None


def is_auth_enabled() -> bool:
    """API authentication is enforced when AUTH_CLIENT_ID (the Entra ID app registration) is set."""
    return bool(os.getenv("AUTH_CLIENT_ID", "").strip())


def _get_signing_key(tenant_id, kid):
    global _jwks_keys, _jwks_fetched_at
    with _jwks_lock:
        now = time.monotonic()
        age = None if _jwks_fetched_at is None else now - _jwks_fetched_at
        if age is None or age > _JWKS_MAX_AGE_SECONDS or (
            kid not in _jwks_keys and age > _JWKS_MIN_REFRESH_SECONDS
        ):
            _jwks_fetched_at = now
            try:
                client = jwt.PyJWKClient(
                    f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
                    cache_jwk_set=False,
                    timeout=10,
                )
                _jwks_keys = {key.key_id: key for key in client.get_signing_keys()}
            except Exception as ex:
                logging.warning("Failed to fetch Entra ID signing keys: %s", ex)
        return _jwks_keys.get(kid)


def _validate_token(token):
    """Validate an Entra ID token and return its claims, or None if invalid."""
    client_id = os.getenv("AUTH_CLIENT_ID", "").strip()
    tenant_id = os.getenv("AZURE_TENANT_ID", "").strip()
    if not token or not client_id or not tenant_id:
        return None
    try:
        signing_key = _get_signing_key(tenant_id, jwt.get_unverified_header(token).get("kid"))
        if signing_key is None:
            return None
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=[client_id, f"api://{client_id}"],
            issuer=[
                f"https://login.microsoftonline.com/{tenant_id}/v2.0",
                f"https://sts.windows.net/{tenant_id}/",
            ],
            options={"require": ["exp", "iss", "aud", "oid"]},
            leeway=60,
        )
    except jwt.PyJWTError as ex:
        logging.warning("Rejected access token: %s", ex)
        return None


def _get_user_from_bearer_token(request_headers):
    auth_header = next(
        (v for k, v in request_headers.items() if k.lower() == "authorization"), ""
    )
    scheme, _, token = auth_header.partition(" ")
    token = token.strip()
    claims = _validate_token(token) if scheme.lower() == "bearer" else None
    if not claims:
        return {
            "user_principal_id": None,
            "user_name": None,
            "auth_provider": None,
            "auth_token": None,
            "client_principal_b64": None,
            "aad_id_token": None,
        }
    return {
        "user_principal_id": claims["oid"],
        "user_name": claims.get("preferred_username") or claims.get("upn") or claims.get("name"),
        "auth_provider": "aad",
        "auth_token": token,
        "client_principal_b64": None,
        "aad_id_token": token,
    }


def get_authenticated_user_details(request_headers):
    # When API authentication is enabled, identity comes only from a validated
    # Entra ID bearer token; client-supplied identity headers are ignored.
    if is_auth_enabled():
        return _get_user_from_bearer_token(request_headers)

    user_object = {}

    # check the headers for the Principal-Id (the guid of the signed in user)
    if "x-ms-client-principal-id" not in request_headers:
        logging.info("No user principal found in headers")
        # if it's not, assume we're in development mode and return a default user
        from . import sample_user

        raw_user_object = sample_user.sample_user
    else:
        # if it is, get the user details from the EasyAuth headers
        raw_user_object = {k: v for k, v in request_headers.items()}

    normalized_headers = {k.lower(): v for k, v in raw_user_object.items()}
    user_object["user_principal_id"] = normalized_headers.get(
        "x-ms-client-principal-id"
    )
    user_object["user_name"] = normalized_headers.get("x-ms-client-principal-name")
    user_object["auth_provider"] = normalized_headers.get("x-ms-client-principal-idp")
    user_object["auth_token"] = normalized_headers.get("x-ms-token-aad-id-token")
    user_object["client_principal_b64"] = normalized_headers.get(
        "x-ms-client-principal"
    )
    user_object["aad_id_token"] = normalized_headers.get("x-ms-token-aad-id-token")

    return user_object


def get_tenantid(client_principal_b64):
    logger = logging.getLogger(__name__)
    tenant_id = ""
    if client_principal_b64:
        try:
            # Decode the base64 header to get the JSON string
            decoded_bytes = base64.b64decode(client_principal_b64)
            decoded_string = decoded_bytes.decode("utf-8")
            # Convert the JSON string into a Python dictionary
            user_info = json.loads(decoded_string)
            # Extract the tenant ID
            tenant_id = user_info.get("tid")  # 'tid' typically holds the tenant ID
        except Exception as ex:
            logger.exception(ex)
    return tenant_id
