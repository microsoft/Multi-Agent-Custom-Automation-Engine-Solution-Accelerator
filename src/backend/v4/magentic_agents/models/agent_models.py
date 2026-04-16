"""Models for agent configurations."""

from dataclasses import dataclass

from common.config.app_config import config


@dataclass(slots=True)
class MCPConfig:
    """Configuration for connecting to an MCP server."""

    url: str = ""
    name: str = "MCP"
    description: str = ""
    tenant_id: str = ""
    client_id: str = ""

    @classmethod
    def from_env(cls) -> "MCPConfig":
        url = config.MCP_SERVER_ENDPOINT
        name = config.MCP_SERVER_NAME
        description = config.MCP_SERVER_DESCRIPTION
        tenant_id = config.AZURE_TENANT_ID
        client_id = config.AZURE_CLIENT_ID

        # Raise exception if any required environment variable is missing
        if not all([url, name, description, tenant_id, client_id]):
            raise ValueError(f"{cls.__name__} Missing required environment variables")

        return cls(
            url=url,
            name=name,
            description=description,
            tenant_id=tenant_id,
            client_id=client_id,
        )


@dataclass(slots=True)
class SearchConfig:
    """Configuration for connecting to Azure AI Search."""

    connection_name: str | None = None
    endpoint: str | None = None
    index_name: str | None = None
    search_query_type: str = "simple"  # Options: "simple", "vector_simple", "vector", "semantic", "hybrid"
    top_k: int = 5  # Number of results to return

    @classmethod
    def from_env(cls, index_name: str) -> "SearchConfig":
        connection_name = config.AZURE_AI_SEARCH_CONNECTION_NAME
        endpoint = config.AZURE_AI_SEARCH_ENDPOINT

        # Raise exception if any required environment variable is missing
        if not all([connection_name, index_name, endpoint]):
            raise ValueError(
                f"{cls.__name__} Missing required Azure Search environment variables"
            )

        return cls(
            connection_name=connection_name,
            endpoint=endpoint,
            index_name=index_name,
            search_query_type="simple",  # Use simple query type (keyword search)
            top_k=5
        )
