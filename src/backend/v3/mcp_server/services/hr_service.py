"""
Human Resources MCP tools service.
"""

from typing import Dict, Any
from core.factory import MCPToolBase, Domain
from utils.date_utils import format_date_for_user
from utils.formatters import format_success_response, format_error_response


class HRService(MCPToolBase):
    """Human Resources tools for employee onboarding and management."""

    def __init__(self):
        super().__init__(Domain.HR)

    def register_tools(self, mcp) -> None:
        """Register HR tools with the MCP server."""

        @mcp.tool(tags={self.domain.value})
        async def schedule_orientation_session(employee_name: str, date: str) -> str:
            """Schedule an orientation session for a new employee."""
            try:
                formatted_date = format_date_for_user(date)
                details = {
                    "employee_name": employee_name,
                    "date": formatted_date,
                    "status": "Scheduled",
                }
                summary = f"I scheduled the orientation session for {employee_name} on {formatted_date}, as part of their onboarding process."

                return format_success_response(
                    action="Orientation Session Scheduled",
                    details=details,
                    summary=summary,
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="scheduling orientation session"
                )

        @mcp.tool(tags={self.domain.value})
        async def assign_mentor(employee_name: str, mentor_name: str = "TBD") -> str:
            """Assign a mentor to a new employee."""
            try:
                details = {
                    "employee_name": employee_name,
                    "mentor_name": mentor_name,
                    "status": "Assigned",
                }
                summary = (
                    f"Successfully assigned mentor {mentor_name} to {employee_name}."
                )

                return format_success_response(
                    action="Mentor Assignment", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="assigning mentor"
                )

        @mcp.tool(tags={self.domain.value})
        async def register_for_benefits(
            employee_name: str, benefits_package: str = "Standard"
        ) -> str:
            """Register a new employee for benefits."""
            try:
                details = {
                    "employee_name": employee_name,
                    "benefits_package": benefits_package,
                    "status": "Registered",
                }
                summary = f"Successfully registered {employee_name} for {benefits_package} benefits package."

                return format_success_response(
                    action="Benefits Registration", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="registering for benefits"
                )

        @mcp.tool(tags={self.domain.value})
        async def provide_employee_handbook(employee_name: str) -> str:
            """Provide the employee handbook to a new employee."""
            try:
                details = {
                    "employee_name": employee_name,
                    "handbook_version": "2024.1",
                    "delivery_method": "Digital",
                    "status": "Delivered",
                }
                summary = f"Employee handbook has been provided to {employee_name}."

                return format_success_response(
                    action="Employee Handbook Provided",
                    details=details,
                    summary=summary,
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="providing employee handbook"
                )

        @mcp.tool(tags={self.domain.value})
        async def initiate_background_check(
            employee_name: str, check_type: str = "Standard"
        ) -> str:
            """Initiate a background check for a new employee."""
            try:
                details = {
                    "employee_name": employee_name,
                    "check_type": check_type,
                    "estimated_completion": "3-5 business days",
                    "status": "Initiated",
                }
                summary = f"Background check has been initiated for {employee_name}."

                return format_success_response(
                    action="Background Check Initiated",
                    details=details,
                    summary=summary,
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="initiating background check"
                )

        @mcp.tool(tags={self.domain.value})
        async def request_id_card(
            employee_name: str, department: str = "General"
        ) -> str:
            """Request an ID card for a new employee."""
            try:
                details = {
                    "employee_name": employee_name,
                    "department": department,
                    "processing_time": "3-5 business days",
                    "pickup_location": "Reception Desk",
                    "status": "Requested",
                }
                summary = f"ID card request submitted for {employee_name} in {department} department."

                return format_success_response(
                    action="ID Card Request", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="requesting ID card"
                )

        @mcp.tool(tags={self.domain.value})
        async def set_up_payroll(
            employee_name: str, salary: str = "As per contract"
        ) -> str:
            """Set up payroll for a new employee."""
            try:
                details = {
                    "employee_name": employee_name,
                    "salary": salary,
                    "pay_frequency": "Bi-weekly",
                    "next_pay_date": "Next pay cycle",
                    "status": "Setup Complete",
                }
                summary = f"Payroll has been successfully set up for {employee_name}."

                return format_success_response(
                    action="Payroll Setup", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="setting up payroll"
                )

    @property
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        return 7
