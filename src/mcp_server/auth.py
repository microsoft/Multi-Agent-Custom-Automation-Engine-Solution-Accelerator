"""
MCP authentication and plugin (tool) management for employee onboarding system.

"""

from azure.identity import InteractiveBrowserCredential
from agent_framework import HostedMCPTool  # agent_framework substitute
from config.settings import TENANT_ID, CLIENT_ID, mcp_config


async def setup_mcp_authentication():
    """
    Set up MCP authentication and return an access token string for downstream header use.
    Returns:
        str | None: Access token (bearer) or None if authentication fails.
    """
    try:
        interactive_credential = InteractiveBrowserCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
        )
        token = interactive_credential.get_token(f"api://{CLIENT_ID}/access_as_user")
        print("✅ Successfully obtained MCP authentication token")
        return token.token
    except Exception as e:  # noqa: BLE001
        print(f"❌ Failed to get MCP token: {e}")
        print("🔄 Continuing without MCP authentication...")
        return None


async def create_mcp_plugin(token: str | None = None):
    """
    Create and initialize an MCP tool (agent_framework HostedMCPTool) for onboarding tools.

    Parameters:
        token: Optional bearer token string for authenticated MCP requests.

    Returns:
        HostedMCPTool | None
    """
    if not token:
        print("⚠️  No MCP token available, skipping MCP tool creation")
        return None

    try:
        headers = mcp_config.get_headers(token)
        # HostedMCPTool currently doesn’t require headers directly in its constructor in some builds;
        # if your version supports passing headers, include them. We store them on the instance for later use.
        mcp_tool = HostedMCPTool(
            name=mcp_config.name,
            description=mcp_config.description,
            server_label=mcp_config.name.replace(" ", "_"),
            url=mcp_config.url,
        )
        # Optionally attach headers for downstream custom transport layers
        try:
            setattr(mcp_tool, "headers", headers)
        except Exception:
            pass

        print("✅ MCP tool (HostedMCPTool) created successfully for employee onboarding")
        return mcp_tool
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  Warning: Could not create MCP tool: {e}")
        return None