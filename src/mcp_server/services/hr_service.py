"""
Human Resources MCP tools service.
"""


from core.factory import Domain, MCPToolBase
from utils.date_utils import format_date_for_user
from utils.formatters import format_error_response, format_success_response


class HRService(MCPToolBase):
    """Human Resources tools for employee onboarding and management."""

    def __init__(self):
        super().__init__(Domain.HR)

    def register_tools(self, mcp) -> None:
        """Register HR tools with the MCP server."""

        @mcp.tool(tags={self.domain.value})
        async def employee_onboarding_blueprint_flat(
            employee_name: str | None = None,
            start_date: str | None = None,
            role: str | None = None
        ) -> dict:
            """
            Ultra-minimal onboarding blueprint (flat list).
            Agent usage:
            1. Call this first when onboarding intent detected.
            2. Filter steps to its own domain.
            3. Execute in listed order while honoring depends_on.
            """
            return {
                "version": "1.0",
                "intent": "employee_onboarding",
                "employee": {
                    "name": employee_name,
                    "start_date": start_date,
                    "role": role
                },
                "steps": [
                    # Pre-boarding
                    {
                        "id": "bg_check",
                        "domain": "HR",
                        "action": "Initiate background check",
                        "tool": "initiate_background_check",
                        "required": True,
                        "params": ["employee_name", "check_type?"]
                    },
                    {
                        "id": "configure_laptop",
                        "domain": "TECH_SUPPORT",
                        "action": "Provision and configure laptop",
                        "tool": "configure_laptop",
                        "required": True
                    },
                    {
                        "id": "create_accounts",
                        "domain": "TECH_SUPPORT",
                        "action": "Create system accounts",
                        "tool": "create_system_accounts",
                        "required": True
                    },

                    # Day 1
                    {
                        "id": "orientation",
                        "domain": "HR",
                        "action": "Schedule orientation session",
                        "tool": "schedule_orientation_session",
                        "required": True,
                        "depends_on": ["bg_check"],
                        "params": ["employee_name", "date"]
                    },
                    {
                        "id": "handbook",
                        "domain": "HR",
                        "action": "Provide employee handbook",
                        "tool": "provide_employee_handbook",
                        "required": True,
                        "params": ["employee_name"]
                    },
                    {
                        "id": "welcome_email",
                        "domain": "TECH_SUPPORT",
                        "action": "Send welcome email",
                        "tool": "send_welcome_email",
                        "required": False,
                        "depends_on": ["create_accounts"]
                    },

                    # Week 1
                    {
                        "id": "mentor",
                        "domain": "HR",
                        "action": "Assign mentor",
                        "tool": "assign_mentor",
                        "required": False,
                        "params": ["employee_name", "mentor_name?"]
                    },
                    {
                        "id": "vpn",
                        "domain": "TECH_SUPPORT",
                        "action": "Set up VPN access",
                        "tool": "setup_vpn_access",
                        "required": False,
                        "depends_on": ["create_accounts"]
                    },
                    {
                        "id": "benefits",
                        "domain": "HR",
                        "action": "Register employee for benefits",
                        "tool": "register_for_benefits",
                        "required": True,
                        "params": ["employee_name", "benefits_package?"]
                    },
                    {
                        "id": "payroll",
                        "domain": "HR",
                        "action": "Set up payroll",
                        "tool": "set_up_payroll",
                        "required": True,
                        "params": ["employee_name", "salary?"]
                    },
                    {
                        "id": "id_card",
                        "domain": "HR",
                        "action": "Request ID card",
                        "tool": "request_id_card",
                        "required": False,
                        "depends_on": ["bg_check"],
                        "params": ["employee_name", "department?"]
                    }
                ]
            }
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
