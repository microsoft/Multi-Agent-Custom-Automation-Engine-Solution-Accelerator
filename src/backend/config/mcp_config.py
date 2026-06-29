# Copyright (c) Microsoft. All rights reserved.
"""
Unified MCP configuration for toolbox and knowledge base connections.

This module merges the two previously separate MCPConfig definitions:
- v4/config/settings.py::MCPConfig (url, name, description, get_headers())
- v4/magentic_agents/models/agent_models.py::MCPConfig (all fields + from_env())
"""

import logging
from dataclasses import dataclass

from common.config.app_config import config

logger = logging.getLogger(__name__)


# Mapping of mcp_domain → list of MCP tool names the agent is allowed to call.
# When set, agent_template will pass this as MCPStreamableHTTPTool(allowed_tools=...)
# so the LLM only sees the relevant subset (avoids cross-pack tool confusion when
# the MCP server exposes every function at the base /mcp endpoint).
# The ``ask_user`` tool is auto-registered as a shared service on every domain
# endpoint by the MCP server, so it does not need to be listed here.
DOMAIN_ALLOWED_TOOLS: dict[str, list[str]] = {
    "hr": [
        "get_workflow_blueprint",
        "schedule_orientation_session",
        "assign_mentor",
        "register_for_benefits",
        "provide_employee_handbook",
        "initiate_background_check",
        "request_id_card",
        "set_up_payroll"
    ],
    "tech_support": [
        "get_workflow_blueprint",
        "send_welcome_email",
        "set_up_office_365_account",
        "configure_laptop",
        "setup_vpn_access",
        "create_system_accounts"
    ],
    "marketing": [
        "generate_press_release",
        "handle_influencer_collaboration"
    ],
    "product": [
        "get_product_info"
    ],
    "image": [
        "generate_marketing_image"
    ],
}


@dataclass(slots=True)
class MCPConfig:
    """Configuration for connecting to an MCP server."""

    url: str = ""
    name: str = "MCP"
    description: str = ""
    tenant_id: str = ""
    client_id: str = ""
    connection_id: str | None = None
    allowed_tools: list[str] | None = None

    @classmethod
    def from_env(cls, domain: str | None = None) -> "MCPConfig":
        """Build MCPConfig from environment variables.

        Args:
            domain: Optional MCP domain (e.g. "hr", "tech_support").
                    When provided the base URL is rewritten so the agent
                    connects to the domain-scoped endpoint
                    (e.g. ``http://host:9000/hr/mcp``).
        """
        url = config.MCP_SERVER_ENDPOINT
        name = config.MCP_SERVER_NAME
        description = config.MCP_SERVER_DESCRIPTION
        tenant_id = config.AZURE_TENANT_ID
        client_id = config.AZURE_CLIENT_ID

        if not all([url, name, description, tenant_id, client_id]):
            raise ValueError(f"{cls.__name__}: missing required environment variables")

        # Rewrite base URL to the domain-scoped endpoint so the agent
        # connects to e.g. ``http://host:9000/hr/mcp`` instead of the
        # catch-all ``/mcp``.  The MCP server mounts per-domain FastMCP
        # sub-apps at ``/<domain>`` (see mcp_server.py), each serving
        # only that domain's tools plus shared services (ask_user).
        # The ``allowed_tools`` client-side filter below acts as a
        # redundant safety net in case the server layout changes.
        if domain:
            stripped = url.rstrip("/")
            if stripped.endswith("/mcp"):
                # Base URL includes the /mcp path (e.g. https://host/mcp)
                # → insert domain before /mcp: https://host/hr/mcp
                stripped = stripped[: -len("/mcp")]
                url = stripped + f"/{domain}/mcp"
            else:
                # Base URL has no /mcp suffix → append /{domain}
                url = stripped + f"/{domain}"

        allowed_tools = DOMAIN_ALLOWED_TOOLS.get(domain) if domain else None

        return cls(
            url=url,
            name=name,
            description=description,
            tenant_id=tenant_id,
            client_id=client_id,
            connection_id=config.MCP_SERVER_CONNECTION_ID,
            allowed_tools=allowed_tools,
        )

    def get_headers(self, token: str) -> dict:
        """Return MCP request headers with bearer token authentication."""
        headers = (
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            if token
            else {}
        )
        logger.debug("MCP headers created (token present: %s)", bool(token))
        return headers


@dataclass(slots=True)
class VectorStoreConfig:
    """Configuration for Foundry IQ (FileSearchTool + managed vector stores)."""

    vector_store_name: str = ""


@dataclass(slots=True)
class KnowledgeBaseConfig:
    """Configuration for Foundry IQ Knowledge Base (MCP endpoint on Azure AI Search)."""

    knowledge_base_name: str = ""
    search_endpoint: str = ""
    search_connection_name: str = ""

    @classmethod
    def from_env(cls, knowledge_base_name: str) -> "KnowledgeBaseConfig":
        """Build KnowledgeBaseConfig from environment variables.

        The connection name defaults to ``{knowledge_base_name}-mcp`` which
        matches the per-KB ``RemoteTool`` / ``ProjectManagedIdentity``
        connection required by Foundry IQ.  Falls back to the legacy shared
        ``AZURE_AI_SEARCH_CONNECTION_NAME`` env var if set.
        """
        search_endpoint = config.AZURE_AI_SEARCH_ENDPOINT
        # Per-KB RemoteTool connection: "{kb_name}-mcp"
        connection_name = (
            config.AZURE_AI_SEARCH_CONNECTION_NAME
            or f"{knowledge_base_name}-mcp"
        )

        if not all([knowledge_base_name, search_endpoint]):
            raise ValueError(
                f"{cls.__name__}: missing required environment variables "
                "(AZURE_AI_SEARCH_ENDPOINT) or knowledge_base_name"
            )

        return cls(
            knowledge_base_name=knowledge_base_name,
            search_endpoint=search_endpoint,
            search_connection_name=connection_name,
        )

    @property
    def mcp_url(self) -> str:
        """Return the KB MCP endpoint URL."""
        base = self.search_endpoint.rstrip("/")
        return f"{base}/knowledgebases/{self.knowledge_base_name}/mcp?api-version=2025-11-01-preview"
