"""
MCP authentication and plugin management for employee onboarding system.
Handles secure token-based authentication with Azure and MCP server integration.
"""

from azure.identity import InteractiveBrowserCredential
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin
from config.settings import TENANT_ID, CLIENT_ID, mcp_config

async def setup_mcp_authentication():
    """Set up MCP authentication and return token."""
    try:
        interactive_credential = InteractiveBrowserCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID
        )
        token = interactive_credential.get_token(f"api://{CLIENT_ID}/access_as_user")
        print("✅ Successfully obtained MCP authentication token")
        return token.token
    except Exception as e:
        print(f"❌ Failed to get MCP token: {e}")
        print("🔄 Continuing without MCP authentication...")
        return None

async def create_mcp_plugin(token=None):
    """Create and initialize MCP plugin for employee onboarding tools."""
    if not token:
        print("⚠️  No MCP token available, skipping MCP plugin creation")
        return None
    
    try:
        headers = mcp_config.get_headers(token)
        mcp_plugin = MCPStreamableHttpPlugin(
            name=mcp_config.name,
            description=mcp_config.description,
            url=mcp_config.url,
            headers=headers,
        )
        print("✅ MCP plugin created successfully for employee onboarding")
        return mcp_plugin
    except Exception as e:
        print(f"⚠️  Warning: Could not create MCP plugin: {e}")
        return None
