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


# @dataclass(slots=True)
# class BingConfig:
#     """Configuration for connecting to Bing Search."""
#     connection_name: str = "Bing"

#     @classmethod
#     def from_env(cls) -> "BingConfig":
#         connection_name = config.BING_CONNECTION_NAME

#         # Raise exception if required environment variable is missing
#         if not connection_name:
#             raise ValueError(f"{cls.__name__} Missing required environment variables")

#         return cls(
#             connection_name=connection_name,
#         )


@dataclass(slots=True)
class SearchConfig:
    """Configuration for connecting to Azure AI Search."""

    connection_name: str | None = None
    endpoint: str | None = None
    index_name: str | None = None
    api_key: str | None = None  # API key for Azure AI Search

    @classmethod
    def from_env(cls) -> "SearchConfig":
        connection_name = config.AZURE_AI_SEARCH_CONNECTION_NAME
        index_name = config.AZURE_AI_SEARCH_INDEX_NAME
        endpoint = config.AZURE_AI_SEARCH_ENDPOINT
        api_key = config.AZURE_AI_SEARCH_API_KEY

        # Raise exception if any required environment variable is missing
        if not all([connection_name, index_name, endpoint]):
            raise ValueError(
                f"{cls.__name__} Missing required Azure Search environment variables"
            )

        return cls(
            connection_name=connection_name,
            index_name=index_name,
            endpoint=endpoint,
            api_key=api_key,
        )
