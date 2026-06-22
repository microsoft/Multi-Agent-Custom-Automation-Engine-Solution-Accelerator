"""
MACAE MCP Server - FastMCP server with per-domain path routing.

Each registered service domain gets its own FastMCP instance mounted at
``/<domain>/mcp`` under a single FastAPI application.  A catch-all server
with **all** tools is also mounted at ``/mcp`` for backward compatibility.

Example endpoints (default port 9000):
    http://localhost:9000/hr/mcp           -> HR tools only
    http://localhost:9000/tech_support/mcp -> Tech-support tools only
    http://localhost:9000/mcp              -> all tools (legacy)
"""

import argparse
import logging
from contextlib import asynccontextmanager

import uvicorn
from config.settings import config
from core.factory import MCPToolFactory
from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from services.ask_user_service import AskUserService
from services.hr_service import HRService
from services.image_service import ImageService
from services.marketing_service import MarketingService
from services.product_service import ProductService
from services.tech_support_service import TechSupportService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global factory instance
factory = MCPToolFactory()

# Initialize services
factory.register_service(HRService())
factory.register_service(TechSupportService())
factory.register_service(MarketingService())
factory.register_service(ProductService())
factory.register_service(ImageService())

# Shared services — registered on every domain server
factory.register_shared_service(AskUserService())


def _create_user_responses_server(auth=None) -> FastMCP:
    """Create a minimal MCP server that exposes only the ask_user shared tool.

    Agents with ``user_responses: true`` but no domain tools connect here.
    """
    server = FastMCP("MACAE-user_responses", auth=auth)
    for svc in factory._shared_services:
        svc.register_tools(server)
    return server


def _build_auth():
    """Return a JWTVerifier when auth is enabled, else None."""
    if not config.enable_auth:
        return None
    auth_config = {
        "jwks_uri": config.jwks_uri,
        "issuer": config.issuer,
        "audience": config.audience,
    }
    if not all(auth_config.values()):
        return None
    return JWTVerifier(
        jwks_uri=auth_config["jwks_uri"],
        issuer=auth_config["issuer"],
        algorithm="RS256",
        audience=auth_config["audience"],
    )


def create_app() -> FastAPI:
    """Build a FastAPI application with per-domain MCP mounts."""
    auth = _build_auth()

    # One FastMCP server per domain + one catch-all with every tool
    domain_servers: dict[str, FastMCP] = factory.create_all_domain_servers(auth=auth)
    all_server: FastMCP = factory.create_mcp_server(name=config.server_name, auth=auth)

    # Minimal server for agents that only need ask_user (user_responses domain)
    user_responses_server: FastMCP = _create_user_responses_server(auth=auth)
    domain_servers["user_responses"] = user_responses_server

    # Convert each FastMCP to a mountable ASGI sub-app
    domain_apps = {
        domain: server.http_app(path="/mcp")
        for domain, server in domain_servers.items()
    }
    all_app = all_server.http_app(path="/mcp")

    # Chain lifespans so every sub-app starts/stops cleanly
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        apps = list(domain_apps.values()) + [all_app]
        # Enter all lifespans (nested)
        async def _enter(remaining):
            if not remaining:
                yield
                return
            head, *tail = remaining
            async with head.lifespan(_app):
                async for _ in _enter(tail):
                    yield
        async for _ in _enter(apps):
            yield

    app = FastAPI(lifespan=lifespan)

    # Mount domain-scoped endpoints: /<domain>/mcp
    for domain, sub_app in domain_apps.items():
        app.mount(f"/{domain}", sub_app)
        logger.info("  Mounted /%s/mcp", domain)

    # Mount catch-all: /mcp (all tools, backward compat)
    app.mount("", all_app)
    logger.info("  Mounted /mcp (all tools)")

    return app


# Module-level app for ``uvicorn mcp_server:app``
app = create_app()

# Keep a reference to the legacy single-server for ``fastmcp run`` compat
mcp = factory.create_mcp_server(name=config.server_name, auth=_build_auth())


def log_server_info():
    """Log server initialization info."""
    summary = factory.get_tool_summary()
    logger.info(" %s initialized with per-domain routing", config.server_name)
    logger.info(" Total services: %s", summary["total_services"])
    logger.info(" Total tools: %s", summary["total_tools"])
    logger.info(" Authentication: %s", "Enabled" if config.enable_auth else "Disabled")

    for domain, info in summary["services"].items():
        logger.info(
            "    /%s/mcp: %s tools (%s)",
            domain,
            info["tool_count"],
            info["class_name"],
        )


def run_server(
    transport: str = "stdio", host: str = "127.0.0.1", port: int = 9000, **kwargs
):
    """Run the server."""
    log_server_info()

    if transport in ("http", "streamable-http", "sse"):
        logger.info("🤖 Starting server on http://%s:%s", host, port)
        uvicorn.run(app, host=host, port=port)
    else:
        # STDIO transport — fall back to the single catch-all server
        stdio_kwargs = {k: v for k, v in kwargs.items() if k not in ["log_level"]}
        mcp.run(transport=transport, **stdio_kwargs)


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
        import os

        os.environ["MCP_DEBUG"] = "true"
        config.debug = True

    if args.no_auth:
        import os

        os.environ["MCP_ENABLE_AUTH"] = "false"
        config.enable_auth = False

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
