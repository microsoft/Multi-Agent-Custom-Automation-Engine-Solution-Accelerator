"""
General purpose MCP tools service.
"""

from core.factory import MCPToolBase, Domain
from utils.formatters import format_success_response, format_error_response
from utils.date_utils import get_current_timestamp


class GeneralService(MCPToolBase):
    """General purpose tools for common operations."""

    def __init__(self):
        super().__init__(Domain.GENERAL)

    def register_tools(self, mcp) -> None:
        """Register general tools with the MCP server."""

        @mcp.tool(tags={self.domain.value})
        def greet(name: str) -> str:
            """Greets the user with the provided name."""
            try:
                details = {
                    "name": name,
                    "greeting": f"Hello from MACAE MCP Server, {name}!",
                    "timestamp": get_current_timestamp(),
                }
                summary = f"Greeted user {name}."

                return format_success_response(
                    action="Greeting", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="greeting user"
                )

        @mcp.tool(tags={self.domain.value})
        async def get_server_status() -> str:
            """Get the current server status and information."""
            try:
                details = {
                    "server_name": "MACAE MCP Server",
                    "status": "Running",
                    "timestamp": get_current_timestamp(),
                    "version": "1.0.0",
                }
                summary = "Retrieved server status information."

                return format_success_response(
                    action="Server Status", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="getting server status"
                )

    @property
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        return 2
