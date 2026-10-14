"""
Human Resources MCP tools service.
"""


from core.factory import Domain, MCPToolBase
from utils.date_utils import format_date_for_user
from utils.formatters import format_error_response, format_success_response

# ---------------------------------------------------------------------------
# Workflow blueprints — lightweight markdown descriptions
# The agent should use the tool descriptions/signatures to determine exact
# parameters. This just tells it what steps exist and what order to follow.
# ---------------------------------------------------------------------------

_HR_BLUEPRINTS = {
    "employee_onboarding": """\
## Employee Onboarding Workflow

### Required Steps (in order)
1. Initiate background check
2. Schedule orientation session (after background check)
3. Provide employee handbook
4. Register for benefits
5. Set up payroll

### Optional Steps — present these to the user and ask if they want them
- Assign a mentor (if yes, ask for the mentor's name)
- Request an ID card (after background check)

### Information you need from the user before starting
- Employee full name
- Department
- Start date
- Manager name
- Orientation date/time preference
- Salary (for payroll)
- Would they like to assign a mentor? If yes, who?
- Would they like to request an ID card?

### Defaults — present these to the user and ask if they want to change them
- Background check type: Standard (options: Standard, Enhanced)
- Benefits package: Standard (options: Standard, Premium, Executive)

### Important
- Ask about ALL of the above in a single request — required info, optional steps, AND defaults.
- Look at each tool's required parameters to know exactly what to pass.
- Do NOT fabricate any information — ask the user for anything you don't have.
""",
}


# --- Commented out: original JSON blueprint structure ---
# _HR_BLUEPRINTS_JSON = {
#     "employee_onboarding": {
#         "version": "2.0",
#         "workflow": "employee_onboarding",
#         "description": "Full HR onboarding workflow for a new employee.",
#         "steps": [
#             {"id": "bg_check", "action": "Initiate background check", "tool": "initiate_background_check", "required": True, ...},
#             {"id": "orientation", "action": "Schedule orientation session", "tool": "schedule_orientation_session", "required": True, "depends_on": ["bg_check"], ...},
#             {"id": "handbook", "action": "Provide employee handbook", "tool": "provide_employee_handbook", "required": True, ...},
#             {"id": "mentor", "action": "Assign a mentor", "tool": "assign_mentor", "required": False, ...},
#             {"id": "benefits", "action": "Register for benefits", "tool": "register_for_benefits", "required": True, ...},
#             {"id": "payroll", "action": "Set up payroll", "tool": "set_up_payroll", "required": True, ...},
#             {"id": "id_card", "action": "Request ID card", "tool": "request_id_card", "required": False, "depends_on": ["bg_check"], ...},
#         ],
#     },
# }


class HRService(MCPToolBase):
    """Human Resources tools for employee onboarding and management."""

    def __init__(self):
        super().__init__(Domain.HR)

    def register_tools(self, mcp) -> None:
        """Register HR tools with the MCP server."""

        @mcp.tool(tags={self.domain.value})
        async def get_workflow_blueprint(workflow: str) -> str:
            """Get the workflow blueprint for an HR process.

            Returns a description of steps to follow, information needed from the
            user, and optional steps. Use this when you need to understand what an
            HR workflow involves before executing it.

            Args:
                workflow: The workflow identifier. Supported: "employee_onboarding"

            Returns:
                A markdown description of the workflow, or an error message.
            """
            blueprint = _HR_BLUEPRINTS.get(workflow)
            if blueprint:
                return blueprint
            available = ", ".join(_HR_BLUEPRINTS.keys())
            return f"Unknown workflow: '{workflow}'. Available workflows: {available}"
        @mcp.tool(tags={self.domain.value})
        async def schedule_orientation_session(employee_name: str, date: str) -> str:
            """Schedule an orientation session for a new employee.

            Args:
                employee_name: Full name of the employee (required).
                date: The orientation date/time as provided by the user (required).
            """
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
        async def assign_mentor(employee_name: str, mentor_name: str) -> str:
            """Assign a mentor to a new employee.

            Args:
                employee_name: Full name of the employee (required).
                mentor_name: Name of the mentor to assign (required — ask the user).
            """
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
            employee_name: str, department: str
        ) -> str:
            """Request an ID card for a new employee.

            Args:
                employee_name: Full name of the employee (required).
                department: Employee's department (required — ask the user).
            """
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
            employee_name: str, salary: str
        ) -> str:
            """Set up payroll for a new employee.

            Args:
                employee_name: Full name of the employee (required).
                salary: Annual salary amount or 'per contract' (required — ask the user).
            """
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
        return 8
