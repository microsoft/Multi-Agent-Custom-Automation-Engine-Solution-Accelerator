"""Service abstractions for v3.

Exports:
- BaseAPIService: minimal async HTTP wrapper using endpoints from AppConfig
- MCPService: service targeting a local/remote MCP server
- FoundryService: helper around Azure AI Foundry (AIProjectClient)
"""

from .base_api_service import BaseAPIService
from .mcp_service import MCPService
from .foundry_service import FoundryService

__all__ = [
    "BaseAPIService",
    "MCPService",
    "FoundryService",
]
