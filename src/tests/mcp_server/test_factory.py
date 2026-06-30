"""
Tests for the MCP tool factory.
"""

import pytest
from src.mcp_server.core.factory import MCPToolFactory, Domain, MCPToolBase


class TestMCPToolFactory:
    """Test cases for MCPToolFactory."""

    def test_factory_initialization(self, mcp_factory):
        """Test factory can be initialized."""
        assert isinstance(mcp_factory, MCPToolFactory)
        assert len(mcp_factory.get_all_services()) == 0

    def test_register_service(self, mcp_factory, hr_service):
        """Test service registration."""
        mcp_factory.register_service(hr_service)

        services = mcp_factory.get_all_services()
        assert len(services) == 1
        assert Domain.HR in services
        assert services[Domain.HR] == hr_service

    def test_get_services_by_domain(self, mcp_factory, hr_service):
        """Test getting service by domain."""
        mcp_factory.register_service(hr_service)

        retrieved_service = mcp_factory.get_services_by_domain(Domain.HR)
        assert retrieved_service == hr_service

        # Test non-existent domain
        assert mcp_factory.get_services_by_domain(Domain.MARKETING) is None

    def test_get_tool_summary(self, mcp_factory, hr_service, tech_support_service):
        """Test tool summary generation."""
        mcp_factory.register_service(hr_service)
        mcp_factory.register_service(tech_support_service)

        summary = mcp_factory.get_tool_summary()

        assert summary["total_services"] == 2
        assert (
            summary["total_tools"]
            == hr_service.tool_count + tech_support_service.tool_count
        )
        assert "services" in summary
        assert Domain.HR.value in summary["services"]
        assert Domain.TECH_SUPPORT.value in summary["services"]

    def test_create_mcp_server(self, mcp_factory, hr_service):
        """Test MCP server creation."""
        mcp_factory.register_service(hr_service)

        # This would normally create a FastMCP server, but we'll test the structure
        try:
            server = mcp_factory.create_mcp_server(name="Test Server")
            # If fastmcp is available, this should work
            assert server is not None
        except ImportError:
            # If fastmcp is not available, we expect an import error
            pass


class TestDomain:
    """Test cases for Domain enum."""

    def test_domain_values(self):
        """Test domain enum values."""
        assert Domain.HR.value == "hr"
        assert Domain.MARKETING.value == "marketing"
        assert Domain.PROCUREMENT.value == "procurement"
        assert Domain.PRODUCT.value == "product"
        assert Domain.TECH_SUPPORT.value == "tech_support"
        assert Domain.RETAIL.value == "retail"
        assert Domain.GENERAL.value == "general"


class TestMCPToolBase:
    """Test cases for MCPToolBase abstract class."""

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that MCPToolBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MCPToolBase(Domain.GENERAL)

    def test_service_properties(self, hr_service):
        """Test service properties."""
        assert hr_service.domain == Domain.HR
        assert isinstance(hr_service.tool_count, int)
        assert hr_service.tool_count > 0
