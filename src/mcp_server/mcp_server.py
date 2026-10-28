"""
MACAE MCP Server - FastMCP server with organized tools and services.
"""

import argparse
import logging
from typing import Literal, cast

from fastmcp.server.auth.providers.jwt import JWTVerifier

###
from config.settings import config
from core.factory import MCPToolFactory
from services.data_tool_service import DataToolService
from services.general_service import GeneralService
from services.hr_service import HRService
from services.inspector_service import InspectorService
from services.marketing_service import MarketingService
from services.product_service import ProductService
from services.product_service_widgets import ProductServiceWithWidgets
from services.tech_support_service import TechSupportService
from services.workspace_service import WorkspaceToolService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global factory instance
factory = MCPToolFactory()

# Initialize services
factory.register_service(HRService())
factory.register_service(InspectorService())
factory.register_service(TechSupportService())
factory.register_service(MarketingService())
factory.register_service(ProductService())
factory.register_service(ProductServiceWithWidgets())
factory.register_service(GeneralService())
factory.register_service(DataToolService(config.dataset_path))
factory.register_service(WorkspaceToolService())


def create_fastmcp_server():
    """Create and configure FastMCP server."""
    try:
        # Create authentication provider if enabled
        auth = None
        if config.enable_auth:
            auth_config = {
                "jwks_uri": config.jwks_uri,
                "issuer": config.issuer,
                "audience": config.audience,
            }
            missing = [name.upper() for name, value in auth_config.items() if not value]
            if missing:
                # Fail at startup, not at the first request: an "Enabled" banner
                # over a server with no verifier is an open perimeter.
                raise RuntimeError(
                    "ENABLE_AUTH is true but "
                    + ", ".join(missing)
                    + " not configured; set them or set ENABLE_AUTH=false"
                )
            auth = JWTVerifier(
                jwks_uri=auth_config["jwks_uri"],
                issuer=auth_config["issuer"],
                algorithm="RS256",
                audience=auth_config["audience"],
            )

        # Create MCP server
        mcp_server = factory.create_mcp_server(name=config.server_name, auth=auth)

        logger.info("✅ FastMCP server created successfully")
        return mcp_server

    except ImportError:
        logger.warning("⚠️  FastMCP not available. Install with: pip install fastmcp")
        return None


# Create FastMCP server instance for fastmcp run command
mcp = create_fastmcp_server()


def log_server_info():
    """Log server initialization info."""
    if not mcp:
        logger.error("❌ FastMCP server not available")
        return

    summary = factory.get_tool_summary()
    logger.info(f"🚀 {config.server_name} initialized")
    logger.info(f"📊 Total services: {summary['total_services']}")
    logger.info(f"🔧 Total tools: {summary['total_tools']}")
    logger.info(f"🔐 Authentication: {'Enabled' if config.enable_auth else 'Disabled'}")

    for domain, info in summary["services"].items():
        logger.info(f"   📁 {domain}: {info['tool_count']} tools ({info['class_name']})")


Transport = Literal["stdio", "http", "streamable-http", "sse"]


def run_server(transport: str = "stdio", host: str = "127.0.0.1", port: int = 9000, **kwargs):
    """Run the FastMCP server with specified transport."""
    if not mcp:
        logger.error("❌ Cannot start FastMCP server - not available")
        return

    log_server_info()

    _transport = cast(Transport, transport)
    logger.info(f"🤖 Starting FastMCP server with {transport} transport")
    if transport in ["http", "streamable-http", "sse"]:
        logger.info(f"🌐 Server will be available at: http://{host}:{port}/mcp/")
        mcp.run(transport=_transport, host=host, port=port, json_response=True, **kwargs)
    else:
        # For STDIO transport, only pass kwargs that are supported
        stdio_kwargs = {k: v for k, v in kwargs.items() if k not in ["log_level"]}
        mcp.run(transport=_transport, **stdio_kwargs)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="MACAE MCP Server")
    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "http", "streamable-http", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to for HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=9000,
        help="Port to bind to for HTTP transport (default: 9000)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication")

    args = parser.parse_args()

    # Override config with command line arguments
    if args.debug:
        config.debug = True

    if args.no_auth:
        # The server object was built at import time; rebuild it so the flag
        # really removes the verifier instead of only changing the banner.
        config.enable_auth = False
        global mcp
        mcp = create_fastmcp_server()

    # Print startup info
    print("🚀 Starting MACAE MCP Server")
    print(f"📋 Transport: {args.transport.upper()}")
    print(f"🔧 Debug: {config.debug}")
    print(f"🔐 Auth: {'Enabled' if config.enable_auth else 'Disabled'}")
    if args.transport in ["http", "streamable-http", "sse"]:
        print(f"🌐 Host: {args.host}")
        print(f"🌐 Port: {args.port}")
    print("-" * 50)

    # Run the server
    run_server(
        transport=args.transport,
        host=args.host,
        port=args.port,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()
