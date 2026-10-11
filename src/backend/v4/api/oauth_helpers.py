"""OAuth2 flow helpers for MCP connections.

Provides:
- Signed `state` token generation/verification (HMAC-SHA256)
- Authorize URL construction (PKCE + RFC 8707 ``resource``)
- Code-for-token exchange (confidential OR public/PKCE client)
- Redirect URI builder
- Discovery for arbitrary MCP servers (no operator pre-registration):
    RFC 9728 protected-resource metadata (from the 401 ``WWW-Authenticate``
    ``resource_metadata`` hint or ``/.well-known/oauth-protected-resource``)
    -> RFC 8414 authorization-server metadata
    -> RFC 7591 dynamic client registration
- Pending-authorization context (code_verifier + dynamic client) stored in Key
  Vault keyed by (user, server) and bound to the signed ``state`` — the state
  itself stays a small HMAC token, secrets never travel in the URL.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

logger = logging.getLogger(__name__)

_STATE_TTL_SECONDS = 600
_PENDING_PROVIDER_SUFFIX = "oauth-pending"
_DCR_PROVIDER_SUFFIX = "oauth-client"


def _get_state_secret() -> str:
    secret = os.environ.get("OAUTH_STATE_SECRET")
    if not secret:
        secret = (
            os.environ.get("AZURE_CLIENT_SECRET")
            or os.environ.get("APP_SECRET_KEY")
            or "macae-oauth-state-fallback"
        )
    return secret


def sign_state(user_id: str, server_name: str) -> str:
    """Sign a short-lived state token binding user_id + server_name."""
    payload = json.dumps(
        {"u": user_id, "s": server_name, "e": int(time.time()) + _STATE_TTL_SECONDS},
        separators=(",", ":"),
    )
    sig = hmac.new(
        _get_state_secret().encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    raw = f"{payload}|{sig}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def verify_state(state: str) -> tuple[str, str]:
    """Verify a state token and return (user_id, server_name).

    Raises ValueError on invalid signature or expiration.
    """
    padded = state + "=" * (-len(state) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode()).decode()
    except Exception as exc:
        raise ValueError(f"Malformed state token: {exc}") from exc

    if "|" not in decoded:
        raise ValueError("Malformed state token: missing signature")

    payload, sig = decoded.rsplit("|", 1)
    expected = hmac.new(
        _get_state_secret().encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("Invalid state signature")

    data = json.loads(payload)
    if data.get("e", 0) < int(time.time()):
        raise ValueError("State token expired")

    return data["u"], data["s"]


def build_redirect_uri() -> str:
    """Build the OAuth callback URL from BACKEND_BASE_URL env var."""
    base = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")
    return f"{base}/api/v4/mcp/connections/oauth/callback"


def build_authorize_url(
    authorize_url: str,
    client_id: str,
    scopes: list[str],
    state: str,
    redirect_uri: str | None = None,
    code_challenge: str | None = None,
    resource: str | None = None,
) -> str:
    """Construct the provider authorize URL with required query params.

    ``code_challenge`` enables PKCE (S256, mandatory in OAuth 2.1 / MCP auth
    spec); ``resource`` is the RFC 8707 audience binding the token to the MCP
    server so it cannot be replayed elsewhere.
    """
    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri or build_redirect_uri(),
        "scope": " ".join(scopes) if scopes else "",
        "state": state,
        "response_type": "code",
    }
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    if resource:
        params["resource"] = resource
    sep = "&" if "?" in authorize_url else "?"
    return f"{authorize_url}{sep}{urlencode(params)}"


async def exchange_code_for_token(
    token_url: str,
    client_id: str,
    client_secret: str | None,
    code: str,
    redirect_uri: str | None = None,
    code_verifier: str | None = None,
    resource: str | None = None,
) -> dict:
    """Exchange an authorization code for an access token.

    ``client_secret`` is optional: a dynamically registered public client
    authenticates with PKCE (``code_verifier``) only.
    """
    data: dict[str, str] = {
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri or build_redirect_uri(),
        "grant_type": "authorization_code",
    }
    if client_secret:
        data["client_secret"] = client_secret
    if code_verifier:
        data["code_verifier"] = code_verifier
    if resource:
        data["resource"] = resource
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            token_url, data=data, headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# PKCE
# ---------------------------------------------------------------------------


def generate_pkce() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` per RFC 7636 (S256)."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


# ---------------------------------------------------------------------------
# Discovery (RFC 9728 -> RFC 8414) and Dynamic Client Registration (RFC 7591)
# ---------------------------------------------------------------------------


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _validated_resource_metadata_url(
    mcp_endpoint: str, resource_metadata_url: str | None
) -> str | None:
    """Return a safe resource_metadata URL or None.

    Safety policy:
    - must be absolute HTTPS URL
    - must not include userinfo
    - must be same-origin as the MCP endpoint
    """
    if not resource_metadata_url:
        return None

    try:
        candidate = urlparse(resource_metadata_url)
        mcp = urlparse(mcp_endpoint)

        if candidate.scheme != "https":
            return None
        if not candidate.netloc:
            return None
        if candidate.username or candidate.password:
            return None
        if candidate.hostname != mcp.hostname:
            return None
        if (candidate.port or 443) != (
            mcp.port or (443 if mcp.scheme == "https" else None)
        ):
            return None
    except (ValueError, UnicodeError):
        return None

    return resource_metadata_url


def parse_resource_metadata_hint(www_authenticate: str | None) -> str | None:
    """Extract ``resource_metadata="..."`` from a 401 ``WWW-Authenticate``."""
    if not www_authenticate:
        return None
    m = re.search(r'resource_metadata="([^"]+)"', www_authenticate)
    return m.group(1) if m else None


async def _get_json(client: httpx.AsyncClient, url: str) -> dict | None:
    try:
        r = await client.get(url, headers={"Accept": "application/json"})
        if r.status_code == 200:
            return r.json()
    except Exception as exc:
        logger.debug("discovery GET %s failed: %s", url, exc)
    return None


async def discover_oauth_metadata(
    mcp_endpoint: str, resource_metadata_url: str | None = None
) -> dict[str, Any] | None:
    """Discover the authorization server protecting ``mcp_endpoint``.

    Order (MCP authorization spec):
      1. RFC 9728 protected-resource metadata — the ``resource_metadata`` URL
         from the 401, else ``{origin}/.well-known/oauth-protected-resource``
         (path-suffixed variant first). Yields ``authorization_servers`` and
         the canonical ``resource``.
      2. RFC 8414 AS metadata at ``{as}/.well-known/oauth-authorization-server``
         (path-aware), falling back to OIDC ``/.well-known/openid-configuration``.
         If no PRM exists, the MCP origin itself is tried as the AS (legacy).

    Returns ``{authorization_endpoint, token_endpoint, registration_endpoint?,
    scopes_supported, resource, issuer, code_challenge_methods_supported}`` or
    None when nothing standards-compliant was found.
    """
    origin = _origin(mcp_endpoint)
    path = urlparse(mcp_endpoint).path.rstrip("/")
    safe_resource_metadata_url = _validated_resource_metadata_url(
        mcp_endpoint, resource_metadata_url
    )
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
        prm: dict | None = None
        prm_candidates = [u for u in [safe_resource_metadata_url] if u]
        if path:
            prm_candidates.append(
                f"{origin}/.well-known/oauth-protected-resource{path}"
            )
        prm_candidates.append(f"{origin}/.well-known/oauth-protected-resource")
        for u in prm_candidates:
            prm = await _get_json(client, u)
            if prm and prm.get("authorization_servers"):
                break
            prm = None

        as_candidates: list[str] = []
        resource = mcp_endpoint
        prm_scopes: list[str] = []
        if prm:
            as_candidates = [str(a).rstrip("/") for a in prm["authorization_servers"]]
            resource = prm.get("resource") or mcp_endpoint
            prm_scopes = list(prm.get("scopes_supported") or [])
        else:
            as_candidates = [origin]

        for as_url in as_candidates:
            as_path = urlparse(as_url).path.rstrip("/")
            as_origin = _origin(as_url)
            urls = []
            if as_path:
                urls.append(
                    f"{as_origin}/.well-known/oauth-authorization-server{as_path}"
                )
                urls.append(f"{as_url}/.well-known/openid-configuration")
            urls.append(f"{as_origin}/.well-known/oauth-authorization-server")
            urls.append(f"{as_origin}/.well-known/openid-configuration")
            for u in urls:
                meta = await _get_json(client, u)
                if (
                    meta
                    and meta.get("authorization_endpoint")
                    and meta.get("token_endpoint")
                ):
                    return {
                        "issuer": meta.get("issuer", as_url),
                        "authorization_endpoint": meta["authorization_endpoint"],
                        "token_endpoint": meta["token_endpoint"],
                        "registration_endpoint": meta.get("registration_endpoint"),
                        "scopes_supported": prm_scopes
                        or list(meta.get("scopes_supported") or []),
                        "code_challenge_methods_supported": list(
                            meta.get("code_challenge_methods_supported") or []
                        ),
                        "resource": resource,
                    }
    logger.info("OAuth discovery found no metadata for %s", mcp_endpoint)
    return None


async def dynamic_client_register(
    registration_endpoint: str,
    redirect_uri: str | None = None,
    client_name: str = "MACAE",
    scopes: list[str] | None = None,
) -> dict[str, Any]:
    """RFC 7591: obtain a client_id (and maybe client_secret) without
    pre-registration. Requests a PKCE-capable code client; ``token_endpoint_
    auth_method=none`` asks for a public client, servers may still issue a
    secret — both are handled downstream."""
    body: dict[str, Any] = {
        "client_name": client_name,
        "redirect_uris": [redirect_uri or build_redirect_uri()],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    if scopes:
        body["scope"] = " ".join(scopes)
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            registration_endpoint,
            json=body,
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
    if not data.get("client_id"):
        raise ValueError("DCR response had no client_id")
    return data


# ---------------------------------------------------------------------------
# Pending-authorization context (Key Vault, keyed by user+server, bound to state)
# ---------------------------------------------------------------------------


def pending_provider_id(server_name: str) -> str:
    return f"{server_name}-{_PENDING_PROVIDER_SUFFIX}"


def dcr_provider_id(server_name: str) -> str:
    return f"{server_name}-{_DCR_PROVIDER_SUFFIX}"


def _state_fingerprint(state: str) -> str:
    return hashlib.sha256(state.encode()).hexdigest()


async def store_pending_oauth(
    resolver, user_id: str, server_name: str, state: str, ctx: dict[str, Any]
) -> None:
    """Persist ``ctx`` (code_verifier, client_id, client_secret?, token_endpoint,
    resource, scopes) for the callback. Bound to ``state`` by fingerprint and
    to the state TTL so a stale blob cannot be replayed."""
    blob = dict(ctx)
    blob["state_fp"] = _state_fingerprint(state)
    blob["exp"] = str(int(time.time()) + _STATE_TTL_SECONDS)
    await resolver.store_credentials(user_id, pending_provider_id(server_name), blob)


async def load_pending_oauth(
    resolver, user_id: str, server_name: str, state: str
) -> dict[str, Any] | None:
    """Fetch the pending context for this (user, server) if it matches
    ``state`` and has not expired; else None (legacy env-var path applies)."""
    try:
        blob = await resolver.resolve_credentials(
            user_id, pending_provider_id(server_name)
        )
    except Exception as exc:
        logger.debug("pending oauth lookup failed: %s", exc)
        return None
    if not blob:
        return None
    if blob.get("state_fp") != _state_fingerprint(state):
        logger.warning("pending oauth ctx state mismatch for %s", server_name)
        return None
    try:
        if int(blob.get("exp", "0")) < int(time.time()):
            logger.warning("pending oauth ctx expired for %s", server_name)
            return None
    except ValueError:
        return None
    return blob
