"""
Core MCP server components and factory patterns.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from fastmcp import FastMCP


class Domain(Enum):
    """Service domains for organizing MCP tools."""

    HR = "hr"
    MARKETING = "marketing"
    PROCUREMENT = "procurement"
    PRODUCT = "product"
    TECH_SUPPORT = "tech_support"
    RETAIL = "retail"
    GENERAL = "general"
    DATA = "data"
    IMAGE = "image"
    USER_RESPONSES = "user_responses"


class MCPToolBase(ABC):
    """Base class for MCP tool services."""

    def __init__(self, domain: Domain):
        self.domain = domain
        self.tools = []

    @abstractmethod
    def register_tools(self, mcp: FastMCP) -> None:
        """Register tools with the MCP server."""
        pass

    @property
    @abstractmethod
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        pass


class MCPToolFactory:
    """Factory for creating and managing MCP tools."""

    def __init__(self):
        self._services: Dict[Domain, MCPToolBase] = {}
        self._shared_services: list[MCPToolBase] = []
        self._mcp_server: Optional[FastMCP] = None

    def register_service(self, service: MCPToolBase) -> None:
        """Register a tool service with the factory."""
        self._services[service.domain] = service

    def register_shared_service(self, service: MCPToolBase) -> None:
        """Register a service whose tools are added to every domain server."""
        self._shared_services.append(service)

    def create_mcp_server(self, name: str = "MACAE MCP Server", auth=None) -> FastMCP:
        """Create and configure the MCP server with all registered services."""
        self._mcp_server = FastMCP(name, auth=auth)

        # Register all tools from all services
        for service in self._services.values():
            service.register_tools(self._mcp_server)
        for service in self._shared_services:
            service.register_tools(self._mcp_server)

        return self._mcp_server

    def create_domain_server(
        self, domain: Domain, name: str | None = None, auth=None
    ) -> FastMCP | None:
        """Create a FastMCP server scoped to a single domain's tools."""
        service = self._services.get(domain)
        if not service:
            return None
        server_name = name or f"MACAE-{domain.value}"
        server = FastMCP(server_name, auth=auth)
        service.register_tools(server)
        for shared in self._shared_services:
            shared.register_tools(server)
        return server

    def create_all_domain_servers(self, auth=None) -> Dict[str, FastMCP]:
        """Create one FastMCP server per registered domain. Returns {domain_value: server}."""
        servers: Dict[str, FastMCP] = {}
        for domain in self._services:
            server = self.create_domain_server(domain, auth=auth)
            if server:
                servers[domain.value] = server
        return servers

    def get_services_by_domain(self, domain: Domain) -> Optional[MCPToolBase]:
        """Get service by domain."""
        return self._services.get(domain)

    def get_all_services(self) -> Dict[Domain, MCPToolBase]:
        """Get all registered services."""
        return self._services.copy()

    def get_tool_summary(self) -> Dict[str, Any]:
        """Get a summary of all tools and services."""
        summary = {
            "total_services": len(self._services),
            "total_tools": sum(
                service.tool_count for service in self._services.values()
            ),
            "services": {},
        }

        for domain, service in self._services.items():
            summary["services"][domain.value] = {
                "tool_count": service.tool_count,
                "class_name": service.__class__.__name__,
            }

        return summary
