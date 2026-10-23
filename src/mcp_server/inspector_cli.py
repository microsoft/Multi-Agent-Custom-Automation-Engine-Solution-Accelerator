#!/usr/bin/env python3
"""
MACAE MCP Inspector CLI — Programmatic interaction with MCP servers.

A command-line tool for automating MCP server testing, validation,
and compatibility checks. Designed for CI/CD pipelines, scripted
workflows, and rapid feedback during tool/widget development.

Usage examples:

  # List tools on a server
  python inspector_cli.py --url http://localhost:9000/mcp tools/list

  # List tools with JSON output (for scripting)
  python inspector_cli.py --url http://localhost:9000/mcp --json tools/list

  # Call a specific tool with arguments
  python inspector_cli.py --url http://localhost:9000/mcp tools/call \\
      --tool-name get_product_info

  # Call a tool with arguments
  python inspector_cli.py --url http://localhost:9000/mcp tools/call \\
      --tool-name schedule_orientation_session \\
      --tool-arg employee_name=John --tool-arg date=2026-04-15

  # Discover all capabilities (tools + resources + prompts)
  python inspector_cli.py --url http://localhost:9000/mcp capabilities

  # List resources
  python inspector_cli.py --url http://localhost:9000/mcp resources/list

  # Read a specific resource
  python inspector_cli.py --url http://localhost:9000/mcp resources/read \\
      --uri "ui://inspector-widget"

  # List prompts
  python inspector_cli.py --url http://localhost:9000/mcp prompts/list

  # Ping the server
  python inspector_cli.py --url http://localhost:9000/mcp ping

  # Connect with custom headers (auth)
  python inspector_cli.py --url https://remote.example.com/mcp \\
      --header "Authorization=Bearer tok123" \\
      --header "X-Api-Key=secret" tools/list

  # Run full compatibility check
  python inspector_cli.py --url http://localhost:9000/mcp validate

  # Specify transport (default: streamable-http)
  python inspector_cli.py --url http://localhost:9000/mcp \\
      --transport sse tools/list
"""

import argparse
import asyncio
import json
import logging
import sys
import time
import uuid
from typing import Any

import httpx

# ─── Colors for terminal output ──────────────────────────────────────
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"
CHECK = f"{GREEN}✔{RESET}"
CROSS = f"{RED}✘{RESET}"
ARROW = f"{CYAN}→{RESET}"
WARN = f"{YELLOW}⚠{RESET}"


def _no_color():
    """Disable color codes (for --no-color or piped output)."""
    global BOLD, DIM, GREEN, YELLOW, RED, CYAN, MAGENTA, BLUE, RESET
    global CHECK, CROSS, ARROW, WARN
    BOLD = DIM = GREEN = YELLOW = RED = CYAN = MAGENTA = BLUE = RESET = ""
    CHECK = "[OK]"
    CROSS = "[FAIL]"
    ARROW = "->"
    WARN = "[WARN]"


# ─── Low-level MCP JSON-RPC client ──────────────────────────────────


class MCPClient:
    """Minimal MCP JSON-RPC 2.0 client for CLI use."""

    def __init__(
        self,
        server_url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        transport: str = "streamable-http",
    ):
        self.server_url = server_url.rstrip("/")
        self.transport = transport
        self.timeout = timeout
        self.extra_headers = headers or {}
        self.client = httpx.AsyncClient(timeout=timeout)
        self.session_id: str | None = None
        self.server_info: dict[str, Any] = {}
        self.protocol_version: str = ""
        self._initialized = False

    async def initialize(self) -> dict[str, Any]:
        """Perform MCP initialize + initialized handshake."""
        result = await self._call(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {"roots": {"listChanged": False}},
                "clientInfo": {
                    "name": "macae-inspector-cli",
                    "version": "1.0.0",
                },
            },
            skip_init_check=True,
        )
        self.server_info = result.get("serverInfo", {})
        self.protocol_version = result.get("protocolVersion", "unknown")

        # Send initialized notification
        await self._notify("notifications/initialized")
        self._initialized = True
        return result

    async def _notify(self, method: str, params: dict | None = None) -> None:
        """Send JSON-RPC notification (no id, no response expected)."""
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        headers = self._build_headers()
        try:
            async with self.client.stream("POST", self.server_url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                if "mcp-session-id" in resp.headers:
                    self.session_id = resp.headers["mcp-session-id"]
        except Exception:
            pass

    async def _call(
        self,
        method: str,
        params: dict | None = None,
        skip_init_check: bool = False,
    ) -> dict[str, Any]:
        """Call a JSON-RPC method and return the result."""
        if not skip_init_check and not self._initialized:
            await self.initialize()

        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        headers = self._build_headers()

        async with self.client.stream("POST", self.server_url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            if "mcp-session-id" in resp.headers:
                self.session_id = resp.headers["mcp-session-id"]
            body = await resp.aread()
            result = self._parse_response(body.decode("utf-8"))

        if "error" in result:
            err = result["error"]
            raise RuntimeError(f"JSON-RPC error {err.get('code', '?')}: {err.get('message', '?')}")
        return result.get("result", {})

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        headers.update(self.extra_headers)
        return headers

    @staticmethod
    def _parse_response(body: str) -> dict[str, Any]:
        """Parse SSE-wrapped or plain JSON-RPC response."""
        for event in body.split("\n\n"):
            data_lines = []
            for line in event.splitlines():
                if line.startswith("data:"):
                    data_lines.append(line[5:].strip())
            if data_lines:
                data = "\n".join(data_lines)
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict) and "jsonrpc" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue
        # Fallback: plain JSON
        try:
            parsed = json.loads(body.strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        raise ValueError("No valid JSON-RPC payload in response")

    async def ping(self) -> float:
        """Send ping and return round-trip time in ms."""
        t0 = time.monotonic()
        await self._call("ping")
        return (time.monotonic() - t0) * 1000

    async def list_tools(self) -> list[dict]:
        result = await self._call("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> dict:
        return await self._call("tools/call", {"name": name, "arguments": arguments})

    async def list_resources(self) -> list[dict]:
        result = await self._call("resources/list")
        return result.get("resources", [])

    async def read_resource(self, uri: str) -> dict:
        return await self._call("resources/read", {"uri": uri})

    async def list_prompts(self) -> list[dict]:
        result = await self._call("prompts/list")
        return result.get("prompts", [])

    async def close(self):
        await self.client.aclose()


# ─── CLI command handlers ────────────────────────────────────────────


async def cmd_tools_list(client: MCPClient, args) -> int:
    """List all tools on the server."""
    tools = await client.list_tools()

    if args.json:
        print(json.dumps(tools, indent=2))
        return 0

    if not tools:
        print(f"\n  {DIM}No tools available on this server.{RESET}")
        return 0

    print(f"\n  {BOLD}Tools ({len(tools)}){RESET}")
    print(f"  {'─' * 56}")

    for t in sorted(tools, key=lambda x: x.get("name", "")):
        name = t.get("name", "?")
        desc = t.get("description", "").split("\n")[0][:60]
        schema = t.get("inputSchema", {})
        required = schema.get("required", [])
        props = list(schema.get("properties", {}).keys())

        print(f"  {CYAN}{name}{RESET}")
        if desc:
            print(f"    {DIM}{desc}{RESET}")
        if props:
            param_strs = []
            for p in props:
                marker = f"{BOLD}*{RESET}" if p in required else ""
                param_strs.append(f"{p}{marker}")
            print(f"    {DIM}params: {', '.join(param_strs)}{RESET}")
        print()

    print(f"  {DIM}* = required  |  {len(tools)} tool(s) total{RESET}\n")
    return 0


async def cmd_tools_call(client: MCPClient, args) -> int:
    """Call a specific tool with arguments."""
    tool_name = args.tool_name
    if not tool_name:
        print(f"{CROSS} --tool-name is required for tools/call", file=sys.stderr)
        return 1

    # Parse --tool-arg key=value pairs
    arguments = {}
    for arg_str in args.tool_arg or []:
        if "=" not in arg_str:
            print(
                f"{CROSS} Invalid --tool-arg '{arg_str}'. Use key=value format.",
                file=sys.stderr,
            )
            return 1
        key, _, value = arg_str.partition("=")
        # Try to parse as JSON for complex types
        try:
            arguments[key] = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            arguments[key] = value

    # Also accept --tool-args as a JSON string
    if args.tool_args:
        try:
            extra = json.loads(args.tool_args)
            arguments.update(extra)
        except json.JSONDecodeError as e:
            print(f"{CROSS} Invalid JSON in --tool-args: {e}", file=sys.stderr)
            return 1

    if not args.json:
        param_str = ", ".join(f"{k}={v!r}" for k, v in arguments.items()) or "none"
        print(f"\n  {ARROW} Calling {CYAN}{tool_name}{RESET}({DIM}{param_str}{RESET})")

    t0 = time.monotonic()
    try:
        result = await client.call_tool(tool_name, arguments)
        elapsed = (time.monotonic() - t0) * 1000
    except RuntimeError as e:
        elapsed = (time.monotonic() - t0) * 1000
        if args.json:
            print(json.dumps({"error": str(e), "elapsed_ms": round(elapsed, 1)}))
        else:
            print(f"  {CROSS} {RED}{e}{RESET} ({elapsed:.0f}ms)\n")
        return 1

    if args.json:
        result["_elapsed_ms"] = round(elapsed, 1)
        print(json.dumps(result, indent=2, default=str))
        return 0

    is_error = result.get("isError", False)
    content = result.get("content", [])

    status = f"{CROSS} Error" if is_error else f"{CHECK} Success"
    print(f"  {status} ({elapsed:.0f}ms)\n")

    for part in content:
        if part.get("type") == "text":
            text = part.get("text", "")
            # Indent output for readability
            for line in text.split("\n"):
                print(f"    {line}")
    print()
    return 1 if is_error else 0


async def cmd_resources_list(client: MCPClient, args) -> int:
    """List all resources on the server."""
    resources = await client.list_resources()

    if args.json:
        print(json.dumps(resources, indent=2))
        return 0

    if not resources:
        print(f"\n  {DIM}No resources available.{RESET}\n")
        return 0

    print(f"\n  {BOLD}Resources ({len(resources)}){RESET}")
    print(f"  {'─' * 56}")
    for r in resources:
        uri = r.get("uri", "?")
        name = r.get("name", "")
        mime = r.get("mimeType", "")
        print(f"  {MAGENTA}{uri}{RESET}")
        if name:
            print(f"    {name}")
        if mime:
            print(f"    {DIM}type: {mime}{RESET}")
        print()
    return 0


async def cmd_resources_read(client: MCPClient, args) -> int:
    """Read a specific resource."""
    uri = args.uri
    if not uri:
        print(f"{CROSS} --uri is required for resources/read", file=sys.stderr)
        return 1

    result = await client.read_resource(uri)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0

    contents = result.get("contents", [])
    for c in contents:
        mime = c.get("mimeType", "text/plain")
        text = c.get("text", c.get("blob", ""))
        print(f"\n  {BOLD}Resource:{RESET} {uri}")
        print(f"  {DIM}Type: {mime}  |  {len(text)} bytes{RESET}\n")
        for line in text.split("\n"):
            print(f"    {line}")
    print()
    return 0


async def cmd_prompts_list(client: MCPClient, args) -> int:
    """List all prompts."""
    prompts = await client.list_prompts()

    if args.json:
        print(json.dumps(prompts, indent=2))
        return 0

    if not prompts:
        print(f"\n  {DIM}No prompts available.{RESET}\n")
        return 0

    print(f"\n  {BOLD}Prompts ({len(prompts)}){RESET}")
    print(f"  {'─' * 56}")
    for p in prompts:
        name = p.get("name", "?")
        desc = p.get("description", "")
        print(f"  {BLUE}{name}{RESET}")
        if desc:
            print(f"    {DIM}{desc}{RESET}")
        print()
    return 0


async def cmd_ping(client: MCPClient, args) -> int:
    """Ping the server."""
    latency = await client.ping()
    if args.json:
        print(json.dumps({"latency_ms": round(latency, 2)}))
    else:
        color = GREEN if latency < 100 else YELLOW if latency < 500 else RED
        print(f"  {CHECK} Pong — {color}{latency:.1f}ms{RESET}")
    return 0


async def cmd_capabilities(client: MCPClient, args) -> int:
    """Discover all capabilities (tools + resources + prompts)."""
    tools = await client.list_tools()
    resources = []
    prompts = []

    try:
        resources = await client.list_resources()
    except Exception:
        pass
    try:
        prompts = await client.list_prompts()
    except Exception:
        pass

    if args.json:
        print(
            json.dumps(
                {
                    "server_info": client.server_info,
                    "protocol_version": client.protocol_version,
                    "tools": tools,
                    "resources": resources,
                    "prompts": prompts,
                    "summary": {
                        "total_tools": len(tools),
                        "total_resources": len(resources),
                        "total_prompts": len(prompts),
                    },
                },
                indent=2,
            )
        )
        return 0

    srv = client.server_info
    print(f"\n  {BOLD}Server:{RESET} {srv.get('name', '?')} v{srv.get('version', '?')}")
    print(f"  {BOLD}Protocol:{RESET} {client.protocol_version}")
    print(f"  {BOLD}Endpoint:{RESET} {client.server_url}")
    print(f"  {'─' * 56}")
    print(f"  {CYAN}Tools:{RESET}     {len(tools)}")
    print(f"  {MAGENTA}Resources:{RESET} {len(resources)}")
    print(f"  {BLUE}Prompts:{RESET}   {len(prompts)}")
    print()

    if tools:
        print(f"  {BOLD}Tool Names:{RESET}")
        for t in sorted(tools, key=lambda x: x.get("name", "")):
            print(f"    {CYAN}•{RESET} {t.get('name', '?')}")
        print()

    if resources:
        print(f"  {BOLD}Resource URIs:{RESET}")
        for r in resources:
            print(f"    {MAGENTA}•{RESET} {r.get('uri', '?')}")
        print()

    if prompts:
        print(f"  {BOLD}Prompt Names:{RESET}")
        for p in prompts:
            print(f"    {BLUE}•{RESET} {p.get('name', '?')}")
        print()

    return 0


async def cmd_validate(client: MCPClient, args) -> int:
    """Run full compatibility validation against a server."""
    checks: list[tuple[str, bool, str]] = []
    t_start = time.monotonic()

    if not args.json:
        srv = client.server_info
        print(f"\n  {BOLD}Validating:{RESET} {srv.get('name', '?')} v{srv.get('version', '?')}")
        print(f"  {BOLD}Endpoint:{RESET}   {client.server_url}")
        print(f"  {'─' * 56}")

    # 1. Ping
    try:
        latency = await client.ping()
        checks.append(("ping", True, f"{latency:.1f}ms"))
    except Exception as e:
        checks.append(("ping", False, str(e)))

    # 2. tools/list
    tools = []
    try:
        tools = await client.list_tools()
        checks.append(("tools/list", True, f"{len(tools)} tools"))
    except Exception as e:
        checks.append(("tools/list", False, str(e)))

    # 3. resources/list
    resources = []
    try:
        resources = await client.list_resources()
        checks.append(("resources/list", True, f"{len(resources)} resources"))
    except Exception as e:
        checks.append(("resources/list", False, str(e)))

    # 4. prompts/list
    prompts = []
    try:
        prompts = await client.list_prompts()
        checks.append(("prompts/list", True, f"{len(prompts)} prompts"))
    except Exception as e:
        checks.append(("prompts/list", False, str(e)))

    # 5. Validate tool schemas
    schema_errors = 0
    for t in tools:
        schema = t.get("inputSchema", {})
        if not isinstance(schema, dict):
            schema_errors += 1
        elif schema and "type" not in schema:
            schema_errors += 1
    if tools:
        if schema_errors == 0:
            checks.append(("tool schemas", True, f"all {len(tools)} valid"))
        else:
            checks.append(("tool schemas", False, f"{schema_errors}/{len(tools)} invalid"))

    # 6. Call first tool with empty args (validation test)
    if tools:
        first_tool = tools[0]
        tool_name = first_tool.get("name", "")
        schema = first_tool.get("inputSchema", {})
        required = schema.get("required", [])

        if not required:
            try:
                result = await client.call_tool(tool_name, {})
                is_err = result.get("isError", False)
                checks.append((
                    f"call {tool_name} (no args)",
                    not is_err,
                    "error response" if is_err else "success",
                ))
            except Exception as e:
                checks.append((f"call {tool_name}", False, str(e)[:60]))
        else:
            checks.append((
                f"call {tool_name} (skipped)",
                True,
                f"requires: {', '.join(required)}",
            ))

    total_time = (time.monotonic() - t_start) * 1000

    if args.json:
        print(
            json.dumps(
                {
                    "server_info": client.server_info,
                    "url": client.server_url,
                    "protocol_version": client.protocol_version,
                    "checks": [{"name": c[0], "passed": c[1], "detail": c[2]} for c in checks],
                    "summary": {
                        "total": len(checks),
                        "passed": sum(1 for c in checks if c[1]),
                        "failed": sum(1 for c in checks if not c[1]),
                    },
                    "elapsed_ms": round(total_time, 1),
                },
                indent=2,
            )
        )
    else:
        for name, passed, detail in checks:
            icon = CHECK if passed else CROSS
            color = GREEN if passed else RED
            print(f"  {icon} {name}: {color}{detail}{RESET}")

        passed = sum(1 for c in checks if c[1])
        failed = sum(1 for c in checks if not c[1])
        print(f"\n  {'─' * 56}")
        status = f"{GREEN}ALL PASSED{RESET}" if failed == 0 else f"{RED}{failed} FAILED{RESET}"
        print(f"  {BOLD}{passed}/{len(checks)} checks passed{RESET} — {status} ({total_time:.0f}ms)\n")

    return 1 if any(not c[1] for c in checks) else 0


# ─── Main ────────────────────────────────────────────────────────────

COMMANDS = {
    "tools/list": cmd_tools_list,
    "tools/call": cmd_tools_call,
    "resources/list": cmd_resources_list,
    "resources/read": cmd_resources_read,
    "prompts/list": cmd_prompts_list,
    "ping": cmd_ping,
    "capabilities": cmd_capabilities,
    "validate": cmd_validate,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inspector-cli",
        description="MACAE MCP Inspector CLI — Programmatic MCP server interaction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s --url http://localhost:9000/mcp tools/list
  %(prog)s --url http://localhost:9000/mcp tools/call --tool-name get_product_info
  %(prog)s --url http://localhost:9000/mcp tools/call \\
      --tool-name schedule_orientation_session \\
      --tool-arg employee_name=John --tool-arg date=2026-04-15
  %(prog)s --url http://localhost:9000/mcp capabilities
  %(prog)s --url http://localhost:9000/mcp validate
  %(prog)s --url http://localhost:9000/mcp --json tools/list | jq '.[].name'
  %(prog)s --url https://remote.example.com/mcp \\
      --header "Authorization=Bearer token123" validate
""",
    )

    # Connection options
    parser.add_argument(
        "--url",
        required=True,
        help="MCP server URL (e.g., http://localhost:9000/mcp)",
    )
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "sse", "http"],
        default="streamable-http",
        help="Transport protocol (default: streamable-http)",
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Custom HTTP header (repeatable). Example: --header 'Authorization=Bearer token'",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30)",
    )

    # Output options
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format (for piping / scripting)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # Command
    parser.add_argument(
        "command",
        choices=list(COMMANDS.keys()),
        help="MCP method to execute",
    )

    # Tool-specific options
    parser.add_argument(
        "--tool-name",
        help="Tool name (for tools/call)",
    )
    parser.add_argument(
        "--tool-arg",
        action="append",
        metavar="KEY=VALUE",
        help="Tool argument as key=value (repeatable, for tools/call)",
    )
    parser.add_argument(
        "--tool-args",
        metavar="JSON",
        help='Tool arguments as JSON string (for tools/call). Example: \'{"name":"John"}\'',
    )

    # Resource-specific options
    parser.add_argument(
        "--uri",
        help="Resource URI (for resources/read)",
    )

    return parser


async def run(args) -> int:
    """Execute the CLI command."""
    if args.no_color or not sys.stdout.isatty():
        _no_color()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Parse custom headers
    headers = {}
    for h in args.header:
        if "=" not in h:
            print(f"{CROSS} Invalid header '{h}'. Use KEY=VALUE.", file=sys.stderr)
            return 1
        key, _, value = h.partition("=")
        headers[key.strip()] = value.strip()

    # Create client and connect
    client = MCPClient(
        server_url=args.url,
        headers=headers,
        timeout=args.timeout,
        transport=args.transport,
    )

    try:
        if not args.json:
            print(f"\n  {DIM}Connecting to {args.url}...{RESET}", end="", flush=True)

        t0 = time.monotonic()
        await client.initialize()
        connect_ms = (time.monotonic() - t0) * 1000

        if not args.json:
            srv = client.server_info
            print(
                f"\r  {CHECK} Connected to {BOLD}{srv.get('name', '?')}{RESET}"
                f" v{srv.get('version', '?')}"
                f" {DIM}({connect_ms:.0f}ms, protocol {client.protocol_version}){RESET}"
            )

        # Dispatch command
        handler = COMMANDS[args.command]
        return await handler(client, args)

    except httpx.ConnectError:
        if args.json:
            print(json.dumps({"error": f"Connection refused: {args.url}"}))
        else:
            print(f"\r  {CROSS} {RED}Connection refused:{RESET} {args.url}")
            print(f"    {DIM}Is the MCP server running?{RESET}\n")
        return 1
    except httpx.TimeoutException:
        if args.json:
            print(json.dumps({"error": f"Timeout after {args.timeout}s"}))
        else:
            print(f"\r  {CROSS} {RED}Timeout{RESET} after {args.timeout}s connecting to {args.url}\n")
        return 1
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"\r  {CROSS} {RED}Error:{RESET} {e}\n")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1
    finally:
        await client.close()


def main():
    parser = build_parser()
    args = parser.parse_args()
    exit_code = asyncio.run(run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
