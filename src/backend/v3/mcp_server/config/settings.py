"""
Configuration settings for the MCP server.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class MCPServerConfig(BaseSettings):
    """MCP Server configuration."""

    # Server settings
    host: str = Field(default="0.0.0.0", env="MCP_HOST")
    port: int = Field(default=9000, env="MCP_PORT")
    debug: bool = Field(default=False, env="MCP_DEBUG")

    # Authentication settings
    tenant_id: Optional[str] = Field(default=None, env="AZURE_TENANT_ID")
    client_id: Optional[str] = Field(default=None, env="AZURE_CLIENT_ID")
    jwks_uri: Optional[str] = Field(default=None, env="AZURE_JWKS_URI")
    issuer: Optional[str] = Field(default=None, env="AZURE_ISSUER")
    audience: Optional[str] = Field(default=None, env="AZURE_AUDIENCE")

    # MCP specific settings
    server_name: str = Field(default="MACAE MCP Server", env="MCP_SERVER_NAME")
    enable_auth: bool = Field(default=True, env="MCP_ENABLE_AUTH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global configuration instance
config = MCPServerConfig()


def get_auth_config():
    """Get authentication configuration for Azure."""
    if not config.enable_auth:
        return None

    return {
        "tenant_id": config.tenant_id,
        "client_id": config.client_id,
        "jwks_uri": config.jwks_uri,
        "issuer": config.issuer,
        "audience": config.audience,
    }


def get_server_config():
    """Get server configuration."""
    return {"host": config.host, "port": config.port, "debug": config.debug}
