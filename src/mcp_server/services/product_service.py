"""
Product MCP tools service.
"""


from core.factory import Domain, MCPToolBase
from utils.formatters import format_success_response


class ProductService(MCPToolBase):
    """Product tools for employee onboarding and management."""

    def __init__(self):
        super().__init__(Domain.PRODUCT)

    def register_tools(self, mcp) -> None:
        """Register Product tools with the MCP server."""

        @mcp.tool(tags={self.domain.value})
        async def get_product_info() -> str:
            """Get information about the different products and phone plans available, including roaming services."""
            product_info = """

            # Simulated Phone Plans

            ## Plan A: Basic Saver
            - **Monthly Cost**: $25
            - **Data**: 5GB
            - **Calls**: Unlimited local calls
            - **Texts**: Unlimited local texts

            ## Plan B: Standard Plus
            - **Monthly Cost**: $45
            - **Data**: 15GB
            - **Calls**: Unlimited local and national calls
            - **Texts**: Unlimited local and national texts

            ## Plan C: Premium Unlimited
            - **Monthly Cost**: $70
            - **Data**: Unlimited
            - **Calls**: Unlimited local, national, and international calls
            - **Texts**: Unlimited local, national, and international texts

            # Roaming Extras Add-On Pack
            - **Cost**: $15/month
            - **Data**: 1GB
            - **Calls**: 200 minutes
            - **Texts**: 200 texts

            """
            return f"Here is information to relay back to the user. Repeat back all the relevant sections that the user asked for: {product_info}."


    @property
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        return 1