# Copyright (c) Microsoft. All rights reserved.
"""
Unified MCP and Azure AI Search configuration.

This module merges the two previously separate MCPConfig definitions:
- v4/config/settings.py::MCPConfig (url, name, description, get_headers())
- v4/magentic_agents/models/agent_models.py::MCPConfig (all fields + from_env())

SearchConfig is carried forward from v4/magentic_agents/models/agent_models.py.
"""

import logging
from dataclasses import dataclass

from common.config.app_config import config

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MCPConfig:
    """Configuration for connecting to an MCP server."""

    url: str = ""
    name: str = "MCP"
    description: str = ""
    tenant_id: str = ""
    client_id: str = ""
    connection_id: str | None = None

    @classmethod
    def from_env(cls) -> "MCPConfig":
        """Build MCPConfig from environment variables."""
        url = config.MCP_SERVER_ENDPOINT
        name = config.MCP_SERVER_NAME
        description = config.MCP_SERVER_DESCRIPTION
        tenant_id = config.AZURE_TENANT_ID
        client_id = config.AZURE_CLIENT_ID

        if not all([url, name, description, tenant_id, client_id]):
            raise ValueError(f"{cls.__name__}: missing required environment variables")

        return cls(
            url=url,
            name=name,
            description=description,
            tenant_id=tenant_id,
            client_id=client_id,
            connection_id=config.MCP_SERVER_CONNECTION_ID,
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
class SearchConfig:
    """Configuration for connecting to Azure AI Search."""

    connection_name: str | None = None
    endpoint: str | None = None
    index_name: str | None = None
    search_query_type: str = "simple"

    @classmethod
    def from_env(cls, index_name: str) -> "SearchConfig":
        """Build SearchConfig from environment variables."""
        connection_name = config.AZURE_AI_SEARCH_CONNECTION_NAME
        endpoint = config.AZURE_AI_SEARCH_ENDPOINT

        if not all([connection_name, index_name, endpoint]):
            raise ValueError(
                f"{cls.__name__}: missing required Azure Search environment variables"
            )

        return cls(
            connection_name=connection_name,
            endpoint=endpoint,
            index_name=index_name,
        )
