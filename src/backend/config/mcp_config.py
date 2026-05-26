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
DOMAIN_ALLOWED_TOOLS: dict[str, list[str]] = {
    "image": ["generate_marketing_image"],
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

        # NOTE: URL rewriting to /<domain>/mcp is disabled because the
        # currently-deployed MCP server only exposes the catch-all /mcp
        # endpoint. We rely on the client-side ``allowed_tools`` filter
        # below to scope the LLM's tool surface to the right domain.
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
        """Build KnowledgeBaseConfig from environment variables."""
        search_endpoint = config.AZURE_AI_SEARCH_ENDPOINT
        connection_name = config.AZURE_AI_SEARCH_CONNECTION_NAME

        if not all([knowledge_base_name, search_endpoint, connection_name]):
            raise ValueError(
                f"{cls.__name__}: missing required environment variables "
                "(AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_CONNECTION_NAME)"
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
