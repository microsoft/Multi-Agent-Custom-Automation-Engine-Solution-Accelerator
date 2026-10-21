"""
MCP Connection Models — Cosmos DB index for external MCP server connections.

Two document types stored in the `mcp_connections` container:

1. MCPServerEntry (pk = "catalog")
   - Shared catalog of available MCP servers
   - Registered by admin, discovered by agents at runtime
   - NO secrets — only endpoint URLs and metadata

2. MCPUserConnection (pk = user_id)
   - Per-user connection status to each MCP server
   - Tracks which servers each user has active
   - Secret references point to Key Vault via CredentialResolver
   - NO tokens stored here — only `secret_ref` URIs

Credential flow:
  Agent needs MCP server → MCPConnectionsService.get_user_connections(user_id)
  → finds server entry → CredentialResolver.resolve_credentials(project_id, server_name)
  → Key Vault → token → InspectorService.connect_mcp_server(url, headers)
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MCPTransportType(StrEnum):
    """Supported MCP transport protocols."""

    STREAMABLE_HTTP = "streamable-http"
    SSE = "sse"
    STDIO = "stdio"


class MCPAuthType(StrEnum):
    """How the MCP server authenticates clients."""

    NONE = "none"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BEARER_TOKEN = "bearer_token"
    MANAGED_IDENTITY = "managed_identity"


class MCPCredentialSource(StrEnum):
    """How the platform OBTAINS a valid token for the server.

    Distinct from ``auth_type`` (what the target server sees on the wire — almost
    always a Bearer). This says HOW we produce that token:

    - ``static_secret``     — a fixed token stored in Key Vault. Expires; dev/fallback only.
    - ``oauth_refresh``     — OAuth2 with a stored refresh_token; the resolver refreshes
                              the access_token on expiry and writes the rotation back to
                              Key Vault, for user-connected servers).
    - ``managed_identity``  — mint a fresh AAD token per call from the platform's Managed
                              Identity for ``audience``. Azure-only, operator-configured;
                              nothing is stored.
    """

    STATIC_SECRET = "static_secret"
    OAUTH_REFRESH = "oauth_refresh"
    MANAGED_IDENTITY = "managed_identity"


class MCPConnectionStatus(StrEnum):
    """User-level connection status to an MCP server."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_AUTH = "pending_auth"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Cosmos DB Documents
# ---------------------------------------------------------------------------


class MCPServerEntry(BaseModel):
    """
    Catalog entry for an available MCP server.

    Stored in Cosmos `mcp_connections` container with pk="catalog" (shared)
    or pk="catalog#{tenant_id}" (tenant-scoped).
    Represents a server that CAN be connected to — no secrets stored here.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pk: str = "catalog"  # partition key — set by MCPConnectionsService before write
    doc_type: str = "mcp_server"

    # Multi-tenancy — empty string means globally shared catalog entry
    tenant_id: str | None = Field(
        default=None,
        description="AAD tenant ID. None / empty = shared catalog visible to all tenants.",
    )

    # Identity
    server_name: str  # unique key, e.g. "github-corp", "slack-workspace"
    display_name: str  # UI-friendly name, e.g. "GitHub Corporate"
    description: str = ""
    icon_url: str | None = None

    # Connection
    endpoint: str  # full URL, e.g. "https://mcp-github.corp.com/mcp"
    transport: MCPTransportType = MCPTransportType.STREAMABLE_HTTP

    # Auth metadata (NO secrets — just what type and what fields are needed)
    auth_type: MCPAuthType = MCPAuthType.NONE

    # How the platform OBTAINS the token (independent of auth_type, which is what
    # the wire looks like). See MCPCredentialSource. The resolver dispatches on this.
    credential_source: MCPCredentialSource = MCPCredentialSource.STATIC_SECRET
    audience: str | None = Field(
        default=None,
        description=(
            "AAD audience/scope to mint a token for when credential_source is "
            "managed_identity, e.g. 'ce34e7e5-485f-4d76-964f-b3d2b16d1e4f/.default'."
        ),
    )
    auth_fields: list[str] = Field(
        default_factory=list,
        description="Credential field names required, e.g. ['api_key'] or ['client_id','client_secret']",
    )
    oauth_scopes: list[str] = Field(
        default_factory=list,
        description="OAuth2 scopes if auth_type is oauth2",
    )

    # OAuth2 provider endpoints (only used when auth_type == oauth2)
    oauth_authorize_url: str | None = Field(
        default=None,
        description="OAuth2 authorization endpoint, e.g. 'https://github.com/login/oauth/authorize'",
    )
    oauth_token_url: str | None = Field(
        default=None,
        description="OAuth2 token exchange endpoint, e.g. 'https://github.com/login/oauth/access_token'",
    )
    oauth_client_id_env: str | None = Field(
        default=None,
        description="Env var name holding the OAuth client_id (e.g. 'GITHUB_CLIENT_ID')",
    )
    oauth_client_secret_env: str | None = Field(
        default=None,
        description="Env var name holding the OAuth client_secret (e.g. 'GITHUB_CLIENT_SECRET')",
    )
    # Discovered at runtime (RFC 9728/8414/7591) for servers registered by URL
    # with no operator pre-configuration. The dynamic client credentials live
    # in Key Vault (``oauth_client_ref``), never here.
    oauth_registration_url: str | None = Field(
        default=None, description="RFC 7591 registration_endpoint (discovered)."
    )
    oauth_resource: str | None = Field(
        default=None,
        description="RFC 8707 resource indicator (canonical MCP server URI).",
    )
    oauth_client_ref: str | None = Field(
        default=None,
        description="Key Vault secret URI holding the dynamically registered client.",
    )

    # Capabilities discovered on last connect (cached)
    capabilities: list[str] = Field(
        default_factory=list,
        description="['tools', 'resources', 'prompts']",
    )
    tool_count: int = 0
    resource_count: int = 0

    # Access control
    allowed_agents: list[str] = Field(
        default_factory=list,
        description="Agent types allowed to use this server. Empty = all agents.",
    )
    enabled: bool = True

    # Audit
    added_by: str | None = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("added_by", mode="before")
    @classmethod
    def _normalize_added_by(cls, value):
        """Accept legacy/null catalog rows and coerce them to an empty string."""
        return value or ""

    # Azure first-party data planes: an endpoint on one of these hosts is
    # token-authenticated by AAD, so the platform mints the token itself
    # (managed identity) — there is no durable static token a user could paste
    # (an az-cli/portal token expires within the hour). Suffixes starting with
    # "." match subdomains; bare hosts match exactly. Audience = what the
    # resolver mints for. Extend here when a new Azure data plane is proven.
    _AZURE_HOST_AUDIENCES: ClassVar[dict[str, str]] = {
        ".search.windows.net": "https://search.azure.com/.default",
        ".grafana.azure.com": "ce34e7e5-485f-4d76-964f-b3d2b16d1e4f/.default",
        ".services.ai.azure.com": "https://ai.azure.com/.default",
        "management.azure.com": "https://management.azure.com/.default",
    }

    @classmethod
    def _azure_audience_for(cls, endpoint: str | None) -> str | None:
        """Audience to mint for ``endpoint`` if it lives on a known Azure data
        plane, else None."""
        host = (urlparse(endpoint or "").hostname or "").lower()
        if not host:
            return None
        for suffix, audience in cls._AZURE_HOST_AUDIENCES.items():
            bare = suffix.lstrip(".")
            if host == bare or host.endswith("." + bare):
                return audience
        return None

    @model_validator(mode="before")
    @classmethod
    def _derive_credential_source(cls, data):
        """Infer credential_source from auth_type + endpoint when not explicit.

        Keeps the App UI free of infra concepts: a user only picks an auth_type
        (OAuth / API Key / Bearer) and the durable token strategy is derived —
        oauth2 → oauth_refresh (refresh + write-back), api_key → static_secret,
        and an endpoint on a known Azure data plane (Search knowledge bases,
        Managed Grafana, Foundry, ARM) → managed_identity + the right audience,
        minted per call by the platform MI. Without that last rule an Azure
        endpoint registered as "none"/bearer goes out with NO Authorization
        header and 401s (foundry-iq-kb, 2026-07-24) — the registration endpoint
        must produce a working entry by itself, not rely on an operator PUT.
        An EXPLICIT credential_source (operator PUT, or a row already stored
        with one) is always respected and never overwritten.
        """
        if isinstance(data, dict) and not data.get("credential_source"):
            auth_type = data.get("auth_type")
            auth_type = getattr(auth_type, "value", auth_type)  # accept enum or str
            azure_audience = cls._azure_audience_for(data.get("endpoint"))
            if auth_type == MCPAuthType.OAUTH2.value:
                data["credential_source"] = MCPCredentialSource.OAUTH_REFRESH.value
            elif auth_type == MCPAuthType.API_KEY.value:
                # An explicit API key is a deliberate choice — keep it.
                data["credential_source"] = MCPCredentialSource.STATIC_SECRET.value
            elif azure_audience:
                # none / bearer / absent on an Azure data plane → platform mints.
                data["credential_source"] = MCPCredentialSource.MANAGED_IDENTITY.value
                if not data.get("audience"):
                    data["audience"] = azure_audience
                # Wire format is a standard Bearer regardless of how it's minted.
                data["auth_type"] = MCPAuthType.BEARER_TOKEN.value
            elif auth_type == MCPAuthType.BEARER_TOKEN.value:
                data["credential_source"] = MCPCredentialSource.STATIC_SECRET.value
        return data


class MCPUserConnection(BaseModel):
    """
    Per-user connection status to an MCP server.

    Stored in Cosmos `mcp_connections` container.
    Partition key (pk):
      - Legacy / single-tenant:  pk = user_id
      - Multi-tenant:             pk = "{tenant_id}#{user_id}"
    The pk value is computed by MCPConnectionsService before write.

    Tracks WHICH servers a user has active — NOT the tokens themselves.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pk: str = ""  # computed and set by MCPConnectionsService before upsert
    doc_type: str = "mcp_user_connection"

    # Multi-tenancy — empty string = single-tenant / legacy mode
    tenant_id: str = Field(
        default="",
        description="AAD tenant ID. Empty = legacy single-tenant mode (pk = user_id).",
    )

    # Links
    user_id: str  # AAD object ID
    server_id: str  # references MCPServerEntry.id
    server_name: str  # denormalized for fast reads

    # Status
    status: MCPConnectionStatus = MCPConnectionStatus.PENDING_AUTH
    last_error: str | None = None

    # Credential reference (points to Key Vault, NOT the actual token)
    secret_ref: str | None = Field(
        default=None,
        description="Key Vault secret URI, e.g. 'https://kv.vault.azure.net/secrets/mcp-user-github-abc123'",
    )
    scopes_granted: list[str] = Field(default_factory=list)

    # Timestamps
    connected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_used_at: datetime | None = None
    token_expires_at: datetime | None = None

    # TTL (Cosmos auto-delete expired connections after 30 days of inactivity)
    ttl: int = Field(
        default=2592000,  # 30 days in seconds
        description="Cosmos DB TTL for auto-cleanup of stale connections",
    )


class OAuthCallbackQuery(BaseModel):
    """Query contract for GET /api/v4/mcp/connections/oauth/callback.

    extra="ignore": OAuth providers may append additional query parameters
    (e.g., `session_state`). We still validate that required `code` and `state`
    are present and non-empty.
    """

    model_config = ConfigDict(extra="ignore")
    # min_length: an empty code or state is meaningless in OAuth — declaring
    # it in the schema keeps the contract the source of truth (empty -> 422).
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class McpReadResourceRequest(BaseModel):
    """Request body for POST /api/v4/mcp/resources/read."""

    uri: str


class MCPServerUpdateRequest(BaseModel):
    """Partial-update body for PUT /api/v4/mcp/connections/servers/{server_id}.

    All fields are optional — only the provided ones are applied.
    Identity / partition fields (id, pk, doc_type, created_at) are never
    accepted from the client.
    """

    server_name: str | None = None
    display_name: str | None = None
    description: str | None = None
    icon_url: str | None = None
    endpoint: str | None = None
    transport: MCPTransportType | None = None
    auth_type: MCPAuthType | None = None
    credential_source: MCPCredentialSource | None = None
    audience: str | None = None
    auth_fields: list[str] | None = None
    oauth_scopes: list[str] | None = None
    oauth_authorize_url: str | None = None
    oauth_token_url: str | None = None
    oauth_client_id_env: str | None = None
    oauth_client_secret_env: str | None = None
    allowed_agents: list[str] | None = None
    enabled: bool | None = None
    tenant_id: str | None = None
