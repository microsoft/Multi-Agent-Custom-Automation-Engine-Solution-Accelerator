"""
Marketing MCP tools service.
"""


from core.factory import Domain, MCPToolBase

class MarketingService(MCPToolBase):
    """Marketing tools for employee onboarding and management."""

    def __init__(self):
        super().__init__(Domain.MARKETING)

    def register_tools(self, mcp) -> None:
        """Register Marketing tools with the MCP server."""

        @mcp.tool(tags={self.domain.value})
        async def generate_press_release(key_information_for_press_release: str) -> str:
            """Draft a press release. Call this tool EXACTLY ONCE per request.

            The tool returns a directive plus a DONE sentinel. After calling it, you
            (the agent) must write the press release in your reply using the directive
            and the conversation context. Do NOT call this tool again for the same
            request — doing so will waste tokens and the orchestration will rate-limit.
            """

            return (
                "PRESS_RELEASE_TASK_ACCEPTED\n"
                f"Key information: {key_information_for_press_release}\n\n"
                "INSTRUCTIONS FOR YOU (the calling agent):\n"
                "1. Write the press release in your NEXT reply (approximately 2 paragraphs).\n"
                "2. Use the key information above plus relevant context from the conversation history.\n"
                "3. Do NOT call generate_press_release again. The task is accepted; deliver the prose directly.\n"
                "STATUS: DONE — proceed to compose the release in your reply."
            )

        @mcp.tool(tags={self.domain.value})
        async def handle_influencer_collaboration(influencer_name: str, campaign_name: str) -> str:
            """Handle collaboration with an influencer."""

            return f"Collaboration with influencer '{influencer_name}' for campaign '{campaign_name}' handled."

    @property
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        return 2
