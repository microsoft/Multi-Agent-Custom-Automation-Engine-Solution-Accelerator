"""
Core MCP server components and factory patterns.
"""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider


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
    INSPECTOR = "inspector"
    WORKSPACE = "workspace"


class MCPToolBase(ABC):
    """Base class for MCP tool services."""

    def __init__(self, domain: Domain):
        self.domain = domain
        self.tools: list = []

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
        self._services: dict[Domain, MCPToolBase] = {}
        self._mcp_server: FastMCP | None = None

    def register_service(self, service: MCPToolBase) -> None:
        """Register a tool service with the factory."""
        self._services[service.domain] = service

    def create_mcp_server(self, name: str = "MACAE MCP Server", auth=None) -> FastMCP:
        """Create and configure the MCP server with all registered services."""
        self._mcp_server = FastMCP(name, auth=auth)

        # Register all tools from all services
        for service in self._services.values():
            service.register_tools(self._mcp_server)

        # Register skills directory provider.
        # factory.py lives at <mcp_server>/core/factory.py, so parents[1] is the
        # mcp_server root: src/mcp_server/skills locally and /app/skills in the
        # container (Dockerfile does `COPY . /app`). One source of truth, no env var.
        skills_root = Path(__file__).resolve().parents[1] / "skills"
        self._mcp_server.add_provider(SkillsDirectoryProvider(roots=skills_root))

        return self._mcp_server

    def get_services_by_domain(self, domain: Domain) -> MCPToolBase | None:
        """Get service by domain."""
        return self._services.get(domain)

    def get_all_services(self) -> dict[Domain, MCPToolBase]:
        """Get all registered services."""
        return self._services.copy()

    def get_tool_summary(self) -> dict[str, Any]:
        """Get a summary of all tools and services."""
        services: dict[str, Any] = {}
        summary: dict[str, Any] = {
            "total_services": len(self._services),
            "total_tools": sum(service.tool_count for service in self._services.values()),
            "services": services,
        }

        for domain, service in self._services.items():
            services[domain.value] = {
                "tool_count": service.tool_count,
                "class_name": service.__class__.__name__,
            }

        return summary
