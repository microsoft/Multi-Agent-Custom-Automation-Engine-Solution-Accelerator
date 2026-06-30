"""
Tech Support MCP tools service.
"""

from core.factory import MCPToolBase, Domain
from utils.formatters import format_success_response, format_error_response


class TechSupportService(MCPToolBase):
    """Tech Support tools for IT setup and system configuration."""

    def __init__(self):
        super().__init__(Domain.TECH_SUPPORT)

    def register_tools(self, mcp) -> None:
        """Register tech support tools with the MCP server."""

        @mcp.tool(tags={self.domain.value})
        async def send_welcome_email(employee_name: str, email_address: str) -> str:
            """Send a welcome email to a new employee as part of onboarding."""
            try:
                details = {
                    "employee_name": employee_name,
                    "email_address": email_address,
                    "email_type": "Welcome Email",
                    "status": "Sent",
                }
                summary = f"Welcome email has been successfully sent to {employee_name} at {email_address}."

                return format_success_response(
                    action="Welcome Email Sent", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="sending welcome email"
                )

        @mcp.tool(tags={self.domain.value})
        async def set_up_office_365_account(
            employee_name: str, email_address: str, department: str = "General"
        ) -> str:
            """Set up an Office 365 account for an employee."""
            try:
                details = {
                    "employee_name": employee_name,
                    "email_address": email_address,
                    "department": department,
                    "licenses": "Office 365 Business Premium",
                    "status": "Account Created",
                }
                summary = f"Office 365 account has been successfully set up for {employee_name} at {email_address}."

                return format_success_response(
                    action="Office 365 Account Setup", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="setting up Office 365 account"
                )

        @mcp.tool(tags={self.domain.value})
        async def configure_laptop(
            employee_name: str, laptop_model: str, operating_system: str = "Windows 11"
        ) -> str:
            """Configure a laptop for a new employee."""
            try:
                details = {
                    "employee_name": employee_name,
                    "laptop_model": laptop_model,
                    "operating_system": operating_system,
                    "software_installed": "Standard Business Package",
                    "security_setup": "Corporate Security Profile",
                    "status": "Configured",
                }
                summary = f"The laptop {laptop_model} has been successfully configured for {employee_name}."

                return format_success_response(
                    action="Laptop Configuration", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="configuring laptop"
                )

        @mcp.tool(tags={self.domain.value})
        async def setup_vpn_access(
            employee_name: str, access_level: str = "Standard"
        ) -> str:
            """Set up VPN access for an employee."""
            try:
                details = {
                    "employee_name": employee_name,
                    "access_level": access_level,
                    "vpn_profile": "Corporate VPN",
                    "credentials_sent": "Via secure email",
                    "status": "Access Granted",
                }
                summary = f"VPN access has been configured for {employee_name} with {access_level} access level."

                return format_success_response(
                    action="VPN Access Setup", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="setting up VPN access"
                )

        @mcp.tool(tags={self.domain.value})
        async def create_system_accounts(
            employee_name: str, systems: str = "Standard business systems"
        ) -> str:
            """Create system accounts for a new employee."""
            try:
                details = {
                    "employee_name": employee_name,
                    "systems": systems,
                    "active_directory": "Account created",
                    "access_permissions": "Role-based access",
                    "status": "Accounts Created",
                }
                summary = f"System accounts have been created for {employee_name} across {systems}."

                return format_success_response(
                    action="System Accounts Created", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="creating system accounts"
                )

    @property
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        return 5
