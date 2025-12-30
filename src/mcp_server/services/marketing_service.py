"""
Marketing MCP tools service.
"""


from core.factory import Domain, MCPToolBase
from utils.formatters import format_success_response


class MarketingService(MCPToolBase):
    """Marketing tools for employee onboarding and management."""

    def __init__(self):
        super().__init__(Domain.MARKETING)

    def register_tools(self, mcp) -> None:
        """Register Marketing tools with the MCP server."""

        @mcp.tool(tags={self.domain.value})
        async def generate_press_release(key_information_for_press_release: str) -> str:
            """This is a function to draft / write a press release. You must call the function by passing the key information that you want to be included in the press release."""

            return f"Look through the conversation history. Identify the content. Now you must generate a press release based on this content {key_information_for_press_release}. Make it approximately 2 paragraphs."

        @mcp.tool(tags={self.domain.value})
        async def handle_influencer_collaboration(influencer_name: str, campaign_name: str) -> str:
            """Handle collaboration with an influencer."""

            return f"Collaboration with influencer '{influencer_name}' for campaign '{campaign_name}' handled."

    @property
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        return 2
