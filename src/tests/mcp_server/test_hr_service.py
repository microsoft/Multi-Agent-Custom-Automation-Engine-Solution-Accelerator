"""
Tests for HR service.
"""

import pytest
from src.mcp_server.services.hr_service import HRService
from src.mcp_server.core.factory import Domain


class TestHRService:
    """Test cases for HR service."""

    def test_service_initialization(self, hr_service):
        """Test HR service initialization."""
        assert hr_service.domain == Domain.HR
        assert hr_service.tool_count == 7

    def test_register_tools(self, hr_service, mock_mcp_server):
        """Test tool registration."""
        hr_service.register_tools(mock_mcp_server)

        # Check that tools were registered
        assert len(mock_mcp_server.tools) == hr_service.tool_count

        # Check that all tools have HR tags
        for tool in mock_mcp_server.tools:
            assert Domain.HR.value in tool["tags"]

    @pytest.mark.asyncio
    async def test_schedule_orientation_session(self, hr_service, mock_mcp_server):
        """Test orientation session scheduling."""
        hr_service.register_tools(mock_mcp_server)

        # Find the schedule_orientation_session tool
        schedule_tool = None
        for tool in mock_mcp_server.tools:
            if tool["func"].__name__ == "schedule_orientation_session":
                schedule_tool = tool["func"]
                break

        assert schedule_tool is not None

        # Test the tool
        result = await schedule_tool("John Doe", "2024-12-25")
        assert "John Doe" in result
        assert "Orientation Session Scheduled" in result
        assert "AGENT SUMMARY" in result

    @pytest.mark.asyncio
    async def test_assign_mentor(self, hr_service, mock_mcp_server):
        """Test mentor assignment."""
        hr_service.register_tools(mock_mcp_server)

        # Find the assign_mentor tool
        assign_tool = None
        for tool in mock_mcp_server.tools:
            if tool["func"].__name__ == "assign_mentor":
                assign_tool = tool["func"]
                break

        assert assign_tool is not None

        # Test the tool
        result = await assign_tool("John Doe", "Jane Smith")
        assert "John Doe" in result
        assert "Jane Smith" in result
        assert "Mentor Assignment" in result
        assert "AGENT SUMMARY" in result

    @pytest.mark.asyncio
    async def test_register_for_benefits(self, hr_service, mock_mcp_server):
        """Test benefits registration."""
        hr_service.register_tools(mock_mcp_server)

        # Find the register_for_benefits tool
        benefits_tool = None
        for tool in mock_mcp_server.tools:
            if tool["func"].__name__ == "register_for_benefits":
                benefits_tool = tool["func"]
                break

        assert benefits_tool is not None

        # Test the tool
        result = await benefits_tool("John Doe", "Premium")
        assert "John Doe" in result
        assert "Premium" in result
        assert "Benefits Registration" in result
        assert "AGENT SUMMARY" in result

    @pytest.mark.asyncio
    async def test_provide_employee_handbook(self, hr_service, mock_mcp_server):
        """Test employee handbook provision."""
        hr_service.register_tools(mock_mcp_server)

        # Find the provide_employee_handbook tool
        handbook_tool = None
        for tool in mock_mcp_server.tools:
            if tool["func"].__name__ == "provide_employee_handbook":
                handbook_tool = tool["func"]
                break

        assert handbook_tool is not None

        # Test the tool
        result = await handbook_tool("John Doe")
        assert "John Doe" in result
        assert "Employee Handbook Provided" in result
        assert "AGENT SUMMARY" in result

    @pytest.mark.asyncio
    async def test_initiate_background_check(self, hr_service, mock_mcp_server):
        """Test background check initiation."""
        hr_service.register_tools(mock_mcp_server)

        # Find the initiate_background_check tool
        check_tool = None
        for tool in mock_mcp_server.tools:
            if tool["func"].__name__ == "initiate_background_check":
                check_tool = tool["func"]
                break

        assert check_tool is not None

        # Test the tool
        result = await check_tool("John Doe", "Enhanced")
        assert "John Doe" in result
        assert "Enhanced" in result
        assert "Background Check Initiated" in result
        assert "AGENT SUMMARY" in result

    @pytest.mark.asyncio
    async def test_request_id_card(self, hr_service, mock_mcp_server):
        """Test ID card request."""
        hr_service.register_tools(mock_mcp_server)

        # Find the request_id_card tool
        id_tool = None
        for tool in mock_mcp_server.tools:
            if tool["func"].__name__ == "request_id_card":
                id_tool = tool["func"]
                break

        assert id_tool is not None

        # Test the tool
        result = await id_tool("John Doe", "Engineering")
        assert "John Doe" in result
        assert "Engineering" in result
        assert "ID Card Request" in result
        assert "AGENT SUMMARY" in result

    @pytest.mark.asyncio
    async def test_set_up_payroll(self, hr_service, mock_mcp_server):
        """Test payroll setup."""
        hr_service.register_tools(mock_mcp_server)

        # Find the set_up_payroll tool
        payroll_tool = None
        for tool in mock_mcp_server.tools:
            if tool["func"].__name__ == "set_up_payroll":
                payroll_tool = tool["func"]
                break

        assert payroll_tool is not None

        # Test the tool
        result = await payroll_tool("John Doe", "$75,000")
        assert "John Doe" in result
        assert "$75,000" in result
        assert "Payroll Setup" in result
        assert "AGENT SUMMARY" in result
