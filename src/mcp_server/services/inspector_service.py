"""
MCP Inspector Service - External MCP server interaction tools.

Provides agents (e.g., TechnicalSupportAgent) with capabilities to:
- Connect to external MCP servers via streamable-http/SSE
- Connect to stdio-based MCP servers DIRECTLY (no proxy dependency)
- Discover tools, resources, and prompts on connected servers
- Execute tools on external servers
- Read resources from external servers
- List and manage connected server sessions

Architecture:
- ExternalMCPSession: direct JSON-RPC 2.0 over streamable-http (httpx)
- DirectStdioSession: spawns stdio MCP servers directly via the MCP SDK's
  stdio_client — no Inspector proxy needed.  This is the primary mode.
- ProxiedStdioSession: LEGACY — routes through Inspector proxy over SSE.
  Kept for backward compat but no longer the default.
- Session keys are (user_id, server_name) tuples for multi-tenant isolation.
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from typing import Any
from urllib.parse import quote

import httpx
from fastmcp.exceptions import ToolError
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from core.factory import Domain, MCPToolBase
from utils.formatters import format_error_response, format_success_response
from utils.tool_arguments import normalize_arguments, validate_arguments

logger = logging.getLogger(__name__)

# credential_resolver: ALWAYS this package's own module (the mcp_server root),
# never the backend's file of the same name. The backend module is a different
# interface (no resolve_valid_token) with backend-only imports; binding to it
# by path order produced three behaviors per environment: AttributeError-shaped
# 401s where it imported, silent None where it didn't, and "works" only in the
# container where the backend path doesn't exist. Import the local twin by its
# package location explicitly so every environment loads the same code.
credential_resolver = None
try:
    import importlib.util

    _resolver_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "credential_resolver.py"))
    _spec = importlib.util.spec_from_file_location("credential_resolver", _resolver_path)
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
        credential_resolver = _mod.credential_resolver
except Exception as e:
    logger.debug("credential_resolver not available: %s", e)


def _redact(headers: dict[str, str]) -> dict[str, str]:
    """Redact sensitive headers for logging."""
    _SENSITIVE = {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "proxy-authorization",
    }

    return {k: ("***REDACTED***" if k.lower() in _SENSITIVE else v) for k, v in headers.items()}


def _truncate(obj: Any, max_len: int) -> str:
    """Truncate object representation for logging."""
    s = str(obj)
    return s if len(s) <= max_len else s[:max_len] + "..."


class ToolSchemaCache:
    """Per-session cached ``tools/list`` index.

    ``call_external_tool`` conforms LLM-composed arguments to the target
    tool's declared ``inputSchema`` before the network round-trip; that needs
    the schema without paying a full ``tools/list`` (Higgsfield: 101 tools)
    on every call. The index is filled lazily and refreshed on a miss — a
    server may add tools at runtime — at most once per ``_REFRESH_INTERVAL``
    so an unlisted tool called in a loop does not re-list every time.
    """

    _REFRESH_INTERVAL = 60.0
    _tool_index: dict[str, dict[str, Any]] | None = None
    _tool_index_at: float = 0.0

    async def list_tools(self) -> list[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError

    async def tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """``inputSchema`` of *tool_name*, or ``None`` when the server does
        not list it (hidden member tools, pagination, list failure). ``None``
        means "unknown", never "invalid": the caller passes the call through
        unchanged and the remote stays the authority.
        """
        stale = self._tool_index is None or (
            tool_name not in self._tool_index and time.time() - self._tool_index_at > self._REFRESH_INTERVAL
        )
        if stale:
            try:
                tools = await self.list_tools()
            except Exception as exc:
                logger.debug("tools/list for schema lookup failed: %s", exc)
                return None
            self._tool_index = {t["name"]: t for t in tools if isinstance(t, dict) and t.get("name")}
            self._tool_index_at = time.time()
        entry = (self._tool_index or {}).get(tool_name)
        schema = entry.get("inputSchema") if entry else None
        return schema if isinstance(schema, dict) else None


class ExternalMCPSession(ToolSchemaCache):
    """Manages connections to an external MCP servers."""

    def __init__(self, server_url: str, server_name: str):
        self.server_url = server_url.rstrip("/")
        self.server_name = server_name
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_id: str | None = None
        self._initialized: bool = False
        self.server_info: dict[str, Any] = {}
        self.extra_headers: dict[str, str] = {}
        self.capabilities: dict[str, Any] = {}
        self.credential_source: str | None = None
        self.audience: str | None = None
        self.secret_ref: str = ""

        if "/toolboxes/" in self.server_url:
            self.extra_headers["Foundry-Features"] = "Toolboxes=V1Preview"
        self.connected_at: float = time.time()

    async def _refresh_auth(self) -> None:
        """Resolve a valid Authorization header for THIS call.

        No-op unless a credential_source is attached (registry-managed
        servers).
        """
        if not (self.credential_source and credential_resolver):
            return
        try:
            token = await credential_resolver.resolve_valid_token(
                credential_source=self.credential_source,
                audience=self.audience,
                secret_ref=self.secret_ref,
            )
        except Exception as exc:
            logger.warning("[%s] per-call token resolution failed: %s", self.server_name, exc)
            return
        if not token:
            return
        # Same scheme rule as the connect paths: a secret that already carries
        # its scheme ("App <key>") is forwarded verbatim.
        _known_schemes = ("bearer ", "app ", "basic ", "token ")
        self.extra_headers["Authorization"] = token if token.lower().startswith(_known_schemes) else f"Bearer {token}"

    async def initialize(self) -> dict[str, Any]:
        """Perform MCP handshake with the external server."""
        try:
            # Step 1: initialize
            init_result = await self._call_jsonrpc(
                "initialize",
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"roots": {"listChanged": False}},
                    "clientInfo": {
                        "name": "MACAE-Inspector-Bridge",
                        "version": "1.0.0",
                    },
                },
                skip_init_check=True,
            )

            self.server_info = init_result.get("serverInfo", {})
            self.capabilities = init_result.get("capabilities", {})
            self.registered_tools = init_result.get("registeredTools", [])

            # Step 2: Send initialized notification
            await self._send_notification("notifications/initialized")

            self._initialized = True
            logger.info(
                f"Connected to external MCP server: "
                f"{self.server_info.get('name', self.server_name)} "
                f"at {self.server_url}"
            )
            return self.server_info

        except Exception as e:
            logger.error(f"Failed to initialize connection to {self.server_url}: {e}")
            raise

    async def _send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send JSON-RPC 2.0 notification (no id, fire-and-forget)."""
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        if self.extra_headers:
            headers.update(self.extra_headers)

        try:
            async with self.client.stream("POST", self.server_url, json=payload, headers=headers) as response:
                response.raise_for_status()
                if "mcp-session-id" in response.headers:
                    self.session_id = response.headers["mcp-session-id"]
        except Exception as e:
            logger.warning(f"Notification {method} failed: {e}")

    async def _call_jsonrpc(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        skip_init_check: bool = False,
    ) -> dict[str, Any]:
        """Call JSON-RPC 2.0 method on the external server."""
        if not skip_init_check and not self._initialized:
            await self.initialize()

        await self._refresh_auth()

        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        if self.extra_headers:
            headers.update(self.extra_headers)

        try:
            async with self.client.stream("POST", self.server_url, json=payload, headers=headers) as response:
                # Read body BEFORE raise_for_status() to avoid stream closure
                body = await response.aread()

                if response.status_code >= 400:
                    logger.warning(
                        "[_call_jsonrpc] HTTP %s for %s method=%s\n"
                        "  request_headers=%s\n  request_body=%s\n"
                        "  response_headers=%s\n  response_body=%s",
                        response.status_code,
                        self.server_url,
                        method,
                        _redact(dict(response.request.headers)),
                        _truncate(payload, 2000),
                        _redact(dict(response.headers)),  # redacted to avoid leaking sensitive response headers
                        body.decode("utf-8", errors="replace")[:4000],
                    )
                    response.raise_for_status()

                if "mcp-session-id" in response.headers:
                    new_sid = response.headers["mcp-session-id"]
                    if new_sid != self.session_id:
                        self.session_id = new_sid

                result = self._parse_sse_response(body.decode("utf-8"))

                if "error" in result:
                    error = result["error"]
                    raise Exception(f"JSON-RPC error {error.get('code')}: {error.get('message')}")
                return result.get("result", {})

        except httpx.HTTPStatusError:
            raise  # Already logged above
        except Exception as e:
            logger.error(f"Error calling {method} on {self.server_url}: {e}")
            raise

    def _parse_sse_response(self, body: str) -> dict[str, Any]:
        """Parse JSON-RPC response from SSE body."""
        for event in body.split("\n\n"):
            data_lines: list[str] = []
            for line in event.splitlines():
                if line.startswith("data:"):
                    data_lines.append(line[5:].strip())
            if not data_lines:
                continue
            data = "\n".join(data_lines)
            if not data:
                continue
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and "jsonrpc" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

        # Fallback: try parsing the whole body as JSON
        try:
            parsed = json.loads(body.strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        raise ValueError("No valid JSON-RPC payload found in response")

    async def list_tools(self) -> list[dict[str, Any]]:
        """List tools available on the external server."""
        result = await self._call_jsonrpc("tools/list")
        return result.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the external server."""
        result = await self._call_jsonrpc("tools/call", {"name": tool_name, "arguments": arguments})
        return result

    async def list_resources(self) -> list[dict[str, Any]]:
        """List resources available on the external server."""
        result = await self._call_jsonrpc("resources/list")
        return result.get("resources", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource from the external server."""
        result = await self._call_jsonrpc("resources/read", {"uri": uri})
        return result

    async def list_prompts(self) -> list[dict[str, Any]]:
        """List prompts available on the external server."""
        result = await self._call_jsonrpc("prompts/list")
        return result.get("prompts", [])

    async def close(self):
        """Close the connection."""
        await self.client.aclose()
        self._initialized = False


class DirectStdioSession(ToolSchemaCache):
    """Manages a DIRECT connection to a stdio MCP server — no proxy needed.

    Uses the MCP SDK's ``stdio_client`` to spawn the command as a child
    process and communicates via stdin/stdout.  This is the PRIMARY mode
    for stdio servers (filesystem, github, etc.).

    IMPORTANT — cancel-scope isolation:
      ``stdio_client()`` creates an anyio TaskGroup internally.  If we
      enter that context inside a FastMCP request handler, the cancel
      scopes collide and crash the MCP server session.

      To avoid this, we run the entire stdio lifecycle in a **dedicated
      asyncio Task** (``_run_background``).  The background task owns
      the anyio cancel scopes; the FastMCP handler only talks to
      ``self._session`` which is safe to share across tasks.

    Exposes the same interface as ExternalMCPSession so callers can use
    either interchangeably.
    """

    def __init__(
        self,
        command: str,
        args: list[str],
        server_name: str,
        env: dict[str, str] | None = None,
    ):
        self.command = command
        self.args = args
        self.server_name = server_name
        self.env = env or {}
        self.server_url = f"stdio://{command}/{'+'.join(args)}"

        self.session_id: str | None = str(uuid.uuid4())
        self._initialized: bool = False
        self.server_info: dict[str, Any] = {}
        self.extra_headers: dict[str, str] = {}
        self.connected_at: float = time.time()
        self.capabilities: dict[str, Any] = {}

        # Lifecycle events — coordinate between background task and callers
        self._ready = asyncio.Event()
        self._shutdown = asyncio.Event()
        self._bg_task: asyncio.Task | None = None
        self._session: ClientSession | None = None
        self._init_error: Exception | None = None

    @property
    def is_alive(self) -> bool:
        """True if the background task is running and session is usable."""
        if not self._initialized or self._session is None:
            return False
        if self._bg_task and self._bg_task.done():
            return False
        return True

    async def _run_background(self, params: StdioServerParameters) -> None:
        """Background task that owns the stdio process and its cancel scopes.

        Runs in its own asyncio Task so anyio cancel scopes from
        stdio_client / ClientSession do NOT interfere with FastMCP's
        request handler scopes.
        """
        try:
            async with (
                stdio_client(params) as transport,
                ClientSession(
                    read_stream=transport[0],
                    write_stream=transport[1],
                ) as session,
            ):
                init_result = await session.initialize()

                # Extract server info
                si = getattr(init_result, "serverInfo", None)
                if si:
                    if isinstance(si, dict):
                        self.server_info = si
                    elif hasattr(si, "name"):
                        self.server_info = {
                            "name": si.name,
                            "version": getattr(si, "version", "unknown"),
                        }

                # Extract capabilities
                caps = getattr(init_result, "capabilities", None)
                if caps:
                    if isinstance(caps, dict):
                        self.capabilities = caps
                    else:
                        self.capabilities = {
                            attr: True
                            for attr in ["tools", "resources", "prompts"]
                            if getattr(caps, attr, None) is not None
                        }

                self._session = session
                self._initialized = True
                self._ready.set()

                logger.info(
                    "[DirectStdio] Connected to '%s' (%s %s) — caps=%s",
                    self.server_name,
                    self.server_info.get("name", "?"),
                    self.server_info.get("version", "?"),
                    list(self.capabilities.keys()),
                )

                # Keep alive until shutdown is requested
                await self._shutdown.wait()

        except Exception as e:
            self._init_error = e
            logger.error(
                "[DirectStdio] Background task failed for '%s': %s",
                self.server_name,
                e,
            )
        finally:
            self._initialized = False
            self._session = None
            self._ready.set()  # unblock initialize() if waiting

    async def initialize(self) -> dict[str, Any]:
        """Spawn the stdio process in a background task and wait for ready."""
        # Build process environment
        process_env = {**os.environ}
        for k, v in self.env.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env_key = v[2:-1]
                resolved = os.environ.get(env_key, "")
                if resolved:
                    process_env[k] = resolved
            else:
                process_env[k] = v

        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=process_env,
        )

        # Launch in a dedicated task — isolates cancel scopes from FastMCP
        self._bg_task = asyncio.create_task(
            self._run_background(params),
            name=f"stdio-{self.server_name}",
        )

        # Wait for the session to be ready (or for an error)
        await self._ready.wait()

        if self._init_error:
            raise self._init_error
        if not self._initialized:
            raise RuntimeError(f"DirectStdioSession '{self.server_name}' failed to initialize")

        return self.server_info

    async def list_tools(self) -> list[dict[str, Any]]:
        if not self._session:
            raise RuntimeError("Not connected")
        result = await self._session.list_tools()
        tools = []
        for t in result.tools:
            tools.append({
                "name": t.name,
                "description": t.description or "",
                "inputSchema": t.inputSchema if t.inputSchema else {},
            })
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self._session:
            raise RuntimeError("Not connected")
        result = await self._session.call_tool(tool_name, arguments=arguments)
        # Convert MCP SDK content items to dicts via model_dump()
        content = []
        for item in result.content:
            d = item.model_dump() if hasattr(item, "model_dump") else {"type": "unknown", "data": str(item)}
            content.append(d)
        # Same shape as the JSON-RPC sessions: isError is part of the MCP
        # tool-result contract and the caller decides success on it.
        return {"content": content, "isError": bool(getattr(result, "isError", False))}

    async def list_resources(self) -> list[dict[str, Any]]:
        if not self._session or "resources" not in self.capabilities:
            return []
        result = await self._session.list_resources()
        return [
            {
                "uri": str(r.uri),
                "name": r.name or "",
                "description": r.description or "",
                "mimeType": r.mimeType or "",
            }
            for r in result.resources
        ]

    async def read_resource(self, uri: str) -> dict[str, Any]:
        if not self._session:
            raise RuntimeError("Not connected")
        from pydantic import AnyUrl

        result = await self._session.read_resource(AnyUrl(uri))
        contents = []
        for item in result.contents:
            d = item.model_dump() if hasattr(item, "model_dump") else {}
            d.setdefault("uri", uri)
            d.setdefault("mimeType", "text/plain")
            contents.append(d)
        return {"contents": contents}

    async def list_prompts(self) -> list[dict[str, Any]]:
        if not self._session or "prompts" not in self.capabilities:
            return []
        result = await self._session.list_prompts()
        return [
            {
                "name": p.name or "",
                "description": p.description or "",
            }
            for p in result.prompts
        ]

    async def close(self) -> None:
        """Signal shutdown and wait for the background task to clean up."""
        self._shutdown.set()
        self._initialized = False
        if self._bg_task and not self._bg_task.done():
            try:
                await asyncio.wait_for(self._bg_task, timeout=5.0)
            except (TimeoutError, asyncio.CancelledError, Exception) as e:
                logger.debug(
                    "[DirectStdio] Background task cleanup for '%s': %s",
                    self.server_name,
                    e,
                )
                self._bg_task.cancel()
        self._session = None
        logger.info("[DirectStdio] Closed session '%s'", self.server_name)


class ProxiedStdioSession(ToolSchemaCache):
    """LEGACY: Manages a connection to a stdio MCP server via the Inspector proxy.

    NOTE: This class is kept for backward compatibility but is no longer the
    default.  Use DirectStdioSession instead — it spawns stdio processes
    directly without depending on the Inspector proxy.

    The MCP Inspector proxy can spawn stdio-based MCP servers (e.g.,
    @modelcontextprotocol/server-github) and bridge them over SSE.

    Protocol:
    1. GET /stdio?transportType=stdio&command=...&args=... → SSE stream
       First SSE event (type=endpoint) gives: /message?sessionId=<uuid>
    2. POST /message?sessionId=<uuid> → sends JSON-RPC requests (returns 202)
    3. Responses come back via the SSE stream as event=message data=<json>

    This class keeps the SSE stream alive in a background task and
    exposes the same interface as ExternalMCPSession.
    """

    def __init__(
        self,
        proxy_url: str,
        command: str,
        args: list[str],
        server_name: str,
        env: dict[str, str] | None = None,
        proxy_auth_token: str | None = None,
    ):
        self.proxy_url = proxy_url.rstrip("/")
        self.command = command
        self.args = args
        self.server_name = server_name
        self.env = env or {}
        self.proxy_auth_token = proxy_auth_token
        self.server_url = f"stdio://{command}/{'+'.join(args)}"

        self.client = httpx.AsyncClient(timeout=60.0)
        self.session_id: str | None = None
        self._initialized: bool = False
        self.server_info: dict[str, Any] = {}
        self.extra_headers: dict[str, str] = {}
        self.connected_at: float = time.time()
        self.capabilities: dict[str, Any] = {}  # server capabilities from initialize

        # SSE reader state
        self._msg_endpoint: str | None = None
        self._msg_url: str | None = None
        self._sse_task: asyncio.Task | None = None
        self._response_queues: dict[Any, asyncio.Queue] = {}
        self._sse_connected = asyncio.Event()
        self._sse_dead = asyncio.Event()  # set when SSE stream closes unexpectedly
        self._sse_stream: Any = None
        self._request_id_counter = 0
        self._closing = False  # True when close() is called intentionally

    @property
    def is_alive(self) -> bool:
        """True if SSE stream is still running and session is usable."""
        if not self._initialized:
            return False
        if self._sse_dead.is_set():
            return False
        if self._sse_task and self._sse_task.done():
            return False
        return True

    def _next_id(self) -> int:
        self._request_id_counter += 1
        return self._request_id_counter

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.proxy_auth_token:
            headers["x-mcp-proxy-auth"] = f"Bearer {self.proxy_auth_token}"
        headers.update(self.extra_headers)
        return headers

    async def _start_sse_reader(self) -> None:
        """Open the SSE stream to the proxy's /stdio endpoint."""
        # Build query string
        args_encoded = quote(" ".join(self.args))
        sse_url = f"{self.proxy_url}/stdio?transportType=stdio&command={quote(self.command)}&args={args_encoded}"

        # Add env vars as query params
        for k, v in self.env.items():
            resolved = os.environ.get(k, v) if v.startswith("${") else v
            sse_url += f"&env.{quote(k)}={quote(resolved)}"

        headers = self._build_headers()
        headers["Accept"] = "text/event-stream"

        logger.info(f"[ProxiedStdio] Opening SSE to {sse_url}")

        self._sse_stream = self.client.stream("GET", sse_url, headers=headers)
        response = await self._sse_stream.__aenter__()

        # Start background reader
        self._sse_task = asyncio.create_task(self._read_sse(response), name=f"sse-{self.server_name}")

        # Wait for the endpoint event
        try:
            await asyncio.wait_for(self._sse_connected.wait(), timeout=30.0)
        except TimeoutError as err:
            raise TimeoutError(f"Timed out waiting for stdio server '{self.server_name}' to start via proxy") from err

    async def _read_sse(self, response) -> None:
        """Background task: read SSE events and dispatch responses."""
        event_type = None
        try:
            async for raw_line in response.aiter_lines():
                line = raw_line.strip()

                if line.startswith("event:"):
                    event_type = line[6:].strip()
                    continue

                if not line.startswith("data:"):
                    continue

                data = line[5:].strip()
                if not data:
                    continue

                if event_type == "endpoint":
                    self._msg_endpoint = data
                    self._msg_url = f"{self.proxy_url}{data}"
                    self.session_id = data.split("sessionId=")[-1]
                    logger.info(f"[ProxiedStdio] Session: {self.session_id}")
                    self._sse_connected.set()
                    event_type = None
                    continue

                if event_type == "message":
                    try:
                        parsed = json.loads(data)
                    except json.JSONDecodeError:
                        logger.warning(f"[ProxiedStdio] Unparseable: {data[:100]}")
                        event_type = None
                        continue

                    # Response to a request we sent
                    msg_id = parsed.get("id")
                    if msg_id is not None and msg_id in self._response_queues:
                        await self._response_queues[msg_id].put(parsed)
                    # Notifications — log and ignore
                    elif "method" in parsed and "id" not in parsed:
                        logger.debug(f"[ProxiedStdio] Notification: {parsed.get('method')}")

                event_type = None

        except (httpx.RemoteProtocolError, httpx.ReadError, asyncio.CancelledError):
            return  # normal stream close or intentional cancel — don't mark dead
        except Exception as e:
            if not e or not str(e).strip():  # empty exception = stream closed normally
                return
            logger.error(f"[ProxiedStdio] SSE reader error: {e}")
            if not self._closing:
                self._sse_dead.set()
                self._initialized = False
                for q in list(self._response_queues.values()):
                    await q.put({"error": {"code": -1, "message": "SSE connection lost"}})
                logger.info(f"[ProxiedStdio] Session {self.server_name} marked dead")

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        request_id: int | None = None,
    ) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for the response via SSE."""
        needs_reconnect = not self._msg_url or self._sse_dead.is_set() or (self._sse_task and self._sse_task.done())
        if needs_reconnect:
            logger.info(f"[ProxiedStdio] '{self.server_name}' reconnecting...")
            # Close stale stream and recreate client to avoid reuse of closed connections
            if self._sse_stream:
                try:
                    await self._sse_stream.__aexit__(None, None, None)
                except Exception:
                    pass
                self._sse_stream = None
            if not self.client.is_closed:
                await self.client.aclose()
            self.client = httpx.AsyncClient(timeout=60.0)
            self._sse_dead.clear()
            self._initialized = False
            self._sse_connected = asyncio.Event()
            self._msg_url = None
            self._response_queues.clear()
            await self.initialize()

        rid = request_id or self._next_id()
        q: asyncio.Queue = asyncio.Queue()
        self._response_queues[rid] = q

        payload = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params or {},
        }
        headers = self._build_headers()
        headers["Content-Type"] = "application/json"

        if not self._msg_url:
            raise RuntimeError("Not connected - message URL not available")

        try:
            resp = await self.client.post(self._msg_url, json=payload, headers=headers)
            if resp.status_code not in (200, 202):
                raise RuntimeError(f"POST {method} returned {resp.status_code}")

            # Wait for response on SSE stream
            result = await asyncio.wait_for(q.get(), timeout=30.0)

            if "error" in result:
                error = result["error"]
                raise Exception(f"JSON-RPC error {error.get('code')}: {error.get('message')}")
            return result.get("result", {})

        finally:
            self._response_queues.pop(rid, None)

    async def _send_notification(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        if not self._msg_url:
            raise RuntimeError("Not connected")

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        headers = self._build_headers()
        headers["Content-Type"] = "application/json"

        await self.client.post(self._msg_url, json=payload, headers=headers)

    async def initialize(self) -> dict[str, Any]:
        """Spawn the stdio server via proxy and complete MCP handshake."""
        try:
            # Start the SSE connection and wait for sessionId
            await self._start_sse_reader()

            # initialize
            init_result = await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"roots": {"listChanged": False}},
                    "clientInfo": {
                        "name": "MACAE-Inspector-Bridge",
                        "version": "1.0.0",
                    },
                },
            )

            self.server_info = init_result.get("serverInfo", {})
            self.capabilities = init_result.get("capabilities", {})

            # initialized notification
            await self._send_notification("notifications/initialized")

            self._initialized = True
            logger.info(
                f"[ProxiedStdio] Connected to "
                f"{self.server_info.get('name', self.server_name)} "
                f"via Inspector proxy (caps={list(self.capabilities.keys())})"
            )
            return self.server_info

        except Exception as e:
            logger.error(f"[ProxiedStdio] Failed to initialize {self.server_name}: {e}")
            raise

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._send_request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self._send_request("tools/call", {"name": tool_name, "arguments": arguments})

    async def list_resources(self) -> list[dict[str, Any]]:
        if "resources" not in self.capabilities:
            return []
        result = await self._send_request("resources/list")
        return result.get("resources", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        return await self._send_request("resources/read", {"uri": uri})

    async def list_prompts(self) -> list[dict[str, Any]]:
        if "prompts" not in self.capabilities:
            return []
        result = await self._send_request("prompts/list")
        return result.get("prompts", [])

    async def close(self) -> None:
        """Shut down the SSE reader and HTTP client."""
        self._closing = True
        self._sse_dead.set()
        self._initialized = False
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            try:
                await self._sse_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._sse_stream:
            try:
                await self._sse_stream.__aexit__(None, None, None)
            except Exception:
                pass
        try:
            await self.client.aclose()
        except Exception:
            pass
        logger.info(f"[ProxiedStdio] Closed session '{self.server_name}'")


def _load_inspector_config() -> dict[str, Any]:
    """Load the mcp-inspector-config.json file if it exists."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "mcp-inspector-config.json")
    config_path = os.path.normpath(config_path)
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"Could not load inspector config: {e}")
        return {}


def _detect_inspector_token() -> str:
    """Auto-detect the Inspector proxy auth token from .inspector.log.

    The Inspector writes a line like:
        MCP_PROXY_AUTH_TOKEN=<hex>
    into .inspector.log each time it starts.  We read the last
    occurrence so the token stays current after restarts.
    """
    import re

    log_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".inspector.log")
    log_path = os.path.normpath(log_path)
    try:
        with open(log_path) as f:
            content = f.read()
        matches = re.findall(r"MCP_PROXY_AUTH_TOKEN=([a-f0-9]{64})", content)
        if matches:
            token = matches[-1]
            logger.info(f"[Inspector] Auto-detected proxy token: {token[:12]}...")
            return token
    except Exception as e:
        logger.debug(f"Could not read inspector log for token: {e}")
    return ""


class RegistryBridge:
    """HTTP bridge to MCPConnectionsService via backend API.

    Allows the MCP server's InspectorService to look up servers
    registered in the Cosmos DB catalog, check user authorization,
    and initiate connections — all via REST calls to the backend.
    """

    def __init__(self):
        backend_url = os.environ.get("MACAE_BACKEND_URL", "http://localhost:8000").rstrip("/")
        self.base = f"{backend_url}/api/v4/mcp/connections"
        self._client = httpx.AsyncClient(timeout=10.0)

    def _user_headers(self, user_id: str, bearer_token: str | None = None) -> dict[str, str]:
        """Build auth headers for requests on behalf of a user.

        Always forwards a Bearer: the one passed explicitly, else the one on
        the inbound MCP request. Locally (no EasyAuth) the principal headers
        alone suffice; in the Container App only the bearer counts — EasyAuth
        strips client-supplied x-ms-client-principal-* and re-injects them only
        after validating the bearer. Without it the hop is anonymous.
        """
        headers: dict[str, str] = {
            "x-ms-client-principal-id": user_id,
            "x-ms-client-principal-name": user_id,
        }
        token = bearer_token or _caller_identity()[1]
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def lookup_server(self, server_name: str) -> dict[str, Any] | None:
        """Look up a server in the catalog by name."""
        try:
            resp = await self._client.get(f"{self.base}/servers")
            resp.raise_for_status()
            for s in resp.json().get("servers", []):
                if s.get("server_name") == server_name:
                    return s
            return None
        except Exception as e:
            logger.warning(f"Registry lookup failed: {e}")
            return None

    async def list_catalog(self) -> list[dict[str, Any]]:
        """List all enabled servers in the catalog."""
        try:
            resp = await self._client.get(f"{self.base}/servers")
            resp.raise_for_status()
            return resp.json().get("servers", [])
        except Exception as e:
            logger.warning(f"Registry catalog fetch failed: {e}")
            return []

    async def get_user_connection(self, user_id: str, server_name: str) -> dict[str, Any] | None:
        """Get a user's connection status for a specific server."""
        try:
            resp = await self._client.get(
                f"{self.base}/user/{server_name}",
                headers=self._user_headers(user_id),
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"User connection check failed: {e}")
            return None

    async def initiate_connection(
        self,
        user_id: str,
        server_name: str,
        bearer_token: str | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Initiate / create a user connection to a cataloged server.

        ``body`` may carry ``{"oauth_discovery": true, "resource_metadata": ...}``
        after the remote answered 401: the backend then discovers the AS
        (RFC 9728/8414), registers a client (RFC 7591) and returns ``oauth_url``.
        """
        try:
            resp = await self._client.post(
                f"{self.base}/user/{server_name}/connect",
                headers=self._user_headers(user_id, bearer_token),
                json=body or {},
            )
            if resp.status_code in (400, 422):
                # Backend explains why OAuth cannot be set up (no metadata, no DCR).
                try:
                    detail = resp.json().get("detail", resp.text)
                except ValueError:
                    detail = resp.text
                return {"error": detail}
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Connection initiation failed: {e}")
            return None

    async def register_server(
        self, user_id: str, entry: dict[str, Any], bearer_token: str | None = None
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Persist a NEW catalog entry (POST {base}/servers).

        Same identity hop as ``initiate_connection``: the backend endpoint
        requires an EasyAuth principal, so the user's bearer is forwarded and
        the backend records ``added_by`` from it. Returns ``(result, error)``
        so the caller can surface a 409 (duplicate) distinctly.
        """
        try:
            resp = await self._client.post(
                f"{self.base}/servers",
                headers=self._user_headers(user_id, bearer_token),
                json=entry,
            )
            if resp.status_code == 409:
                return None, resp.json().get("detail", "already exists")
            resp.raise_for_status()
            return resp.json(), None
        except Exception as e:
            logger.warning(f"Server registration failed: {e}")
            return None, str(e)

    async def activate_connection(self, user_id: str, server_name: str, secret_ref: str = "") -> dict[str, Any] | None:
        """Mark a user connection as active (after OAuth callback)."""
        try:
            body = {}
            if secret_ref:
                body["secret_ref"] = secret_ref
            resp = await self._client.patch(
                f"{self.base}/user/{server_name}/activate",
                headers=self._user_headers(user_id),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Connection activation failed: {e}")
            return None

    async def disconnect_user_connection(self, user_id: str, server_name: str, bearer_token: str | None = None) -> bool:
        """Delete the user's connection record (DELETE {base}/user/{name}).

        Discards the stored credential (e.g. an OAuth token) so the next
        connect starts a fresh sign-in — required when the user authenticated
        with the wrong account. Same identity hop as ``initiate_connection``.
        Returns True when a record was removed; False when there was none.
        """
        try:
            resp = await self._client.delete(
                f"{self.base}/user/{server_name}",
                headers=self._user_headers(user_id, bearer_token),
            )
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.warning(
                "User connection delete failed (status=%s): %s",
                e.response.status_code,
                e,
            )
            raise
        except httpx.HTTPError as e:
            logger.warning(f"User connection delete failed: {e}")
            raise

    async def get_user_servers(self, user_id: str) -> list[dict[str, Any]]:
        """Get all servers with the user's connection status."""
        try:
            resp = await self._client.get(
                f"{self.base}/user",
                headers=self._user_headers(user_id),
            )
            resp.raise_for_status()
            return resp.json().get("connections", [])
        except Exception as e:
            logger.warning(f"User servers fetch failed: {e}")
            return []

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


def _pending_auth_response(
    server_name: str,
    endpoint: str,
    auth_type: str,
    user_id: str,
    server: dict[str, Any],
    conn_result: dict[str, Any],
) -> str:
    """Uniform "Authentication Required" result for connect_from_registry.

    Carries ``oauth_url`` when the backend produced one (pre-configured OAuth or
    the discovery lane after a 401). The router turns that field into an
    ``oauth_consent_request`` SSE event so the composer opens the SAME popup the
    Applications UI uses; on close the message is re-sent and the retry connects
    with the fresh token. Without a URL the user must supply a static token.
    """
    oauth_url = conn_result.get("oauth_url")
    details: dict[str, Any] = {
        "server_name": server_name,
        "endpoint": endpoint,
        "auth_type": auth_type,
        "status": "pending_auth",
        "user_id": user_id,
        "oauth_scopes": server.get("oauth_scopes", []),
    }
    if oauth_url:
        details["oauth_url"] = oauth_url
        details["instructions"] = (
            f"Server '{server_name}' requires the user to sign in. The sign-in "
            f"window opens automatically; tell the user to complete it. Then call "
            f"connect_from_registry('{server_name}') again. Do NOT paste the URL "
            f"as text unless the user asks for it."
        )
        summary = (
            f"Server '{server_name}' requires {auth_type} sign-in. Authorization "
            f"window opened for the user; retry connect_from_registry after they "
            f"finish."
        )
    else:
        details["instructions"] = (
            f"Server '{server_name}' requires {auth_type} authentication and no "
            f"OAuth flow is available. The user must add a token in Applications, "
            f"then call connect_from_registry again."
        )
        summary = f"Server '{server_name}' requires {auth_type} auth. User must authorize first, then retry."
    return format_success_response(action="Authentication Required", details=details, summary=summary)


async def _oauth_discovery_pivot(
    registry,
    user_id: str,
    server_name: str,
    endpoint: str,
    bearer_token: str | None,
    www_authenticate: str,
    ensure_registered_url: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Turn a 401 from an external MCP server into the OAuth sign-in flow.

    Shared by BOTH connect paths so neither dead-ends on a raw 401 asking the
    user for a token. Reads the RFC 9728 ``resource_metadata`` hint from the
    ``WWW-Authenticate`` header, then asks the backend to run discovery
    (RFC 9728 -> 8414 -> 7591 + PKCE) and return an authorize URL. For the
    direct-URL path the server may not be catalogued yet — discovery needs a
    catalog entry — so it is registered first (best-effort; 409 = already there).
    Returns ``(discovery_result, None)`` on success or ``(None, error)``.
    """
    _rm = None
    _m = re.search(r'resource_metadata="([^"]+)"', www_authenticate or "")
    if _m:
        _rm = _m.group(1)
    if ensure_registered_url:
        try:
            await registry.register_server(
                user_id,
                {
                    "server_name": server_name,
                    "display_name": server_name,
                    "endpoint": ensure_registered_url,
                    "transport": "streamable-http",
                },
                bearer_token=bearer_token,
            )
        except Exception as exc:  # best-effort; discovery still needs the entry
            logger.debug("[oauth pivot] register '%s' best-effort: %s", server_name, exc)
    logger.info(
        "[oauth pivot] 401 from %s; requesting OAuth discovery (resource_metadata=%s)",
        endpoint,
        _rm,
    )
    disc = await registry.initiate_connection(
        user_id,
        server_name,
        bearer_token=bearer_token,
        body={"oauth_discovery": True, "resource_metadata": _rm},
    )
    if not disc or disc.get("error") or not disc.get("oauth_url"):
        return None, str((disc or {}).get("error", "no metadata"))
    return disc, None


def _principal_from_bearer(bearer: str | None) -> str | None:
    """The ``oid`` (AAD object id) carried in a Bearer JWT, or ``None``.

    The backend forwards the user's OBO token but NOT the
    ``x-ms-client-principal-id`` header (``lifecycle.py`` sets only
    ``Authorization``). The principal the backend expects IS that token's
    ``oid`` claim — the same GUID EasyAuth would put in the header — so the
    identity already travels with the token. No signature check here: the
    token was minted by AAD's OBO exchange upstream and the backend trusts the
    principal header it is echoed into; this only reads the claim already
    present. ``sub`` is a last resort (pairwise, per-app — not the directory
    object id).
    """
    if not bearer or bearer.count(".") < 2:
        return None
    try:
        import base64

        payload_b64 = bearer.split(".", 2)[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        return claims.get("oid") or None
    except Exception:
        return None


def _caller_identity() -> tuple[str | None, str | None]:
    """(principal_id, bearer) of the MCP request being served, or (None, None).

    The backend attaches ca-mcp with the user's EasyAuth
    ``Authorization: Bearer`` (proof the backend validates on the hop back).
    The ``x-ms-client-principal-id`` header is the preferred source of *who*,
    but the backend→MCP forward does not send it — so when it is absent the
    principal is recovered from the Bearer's ``oid`` claim (the identical GUID
    the backend expects). Never trust ``user_id`` args from the model when a
    principal is present.
    """
    try:
        from fastmcp.server.dependencies import get_http_headers

        headers = get_http_headers(include={"x-ms-client-principal-id", "authorization"})
        principal = headers.get("x-ms-client-principal-id") or None
        auth = headers.get("authorization", "").strip()
        if auth.lower().startswith("bearer "):
            bearer = auth[7:].strip() or None
        else:
            # Tolerate a scheme-less token value (a caller that passed only the
            # token). Downstream always re-attaches the "Bearer " prefix.
            bearer = auth or None
        # The hop from the backend carries the token but not the principal
        # header; recover the authoritative principal from the token itself.
        if not principal:
            principal = _principal_from_bearer(bearer)
        return principal, bearer
    except Exception:
        return None, None


class InspectorService(MCPToolBase):
    """
    MCP Inspector tools for connecting to and interacting
    with external MCP servers.

    Enables TechnicalSupportAgent and other agents to:
    - Discover external MCP servers and their capabilities
    - Execute tools across server boundaries
    - Read resources from any connected MCP server
    - Look up servers from the Cosmos DB registry catalog
    - Check user authorization before connecting
    """

    def __init__(self):
        super().__init__(Domain.INSPECTOR)
        # Keyed by (user_id, server_name) for per-user session isolation.
        # user_id="" is the anonymous/shared namespace (dev / backward-compat).
        self._sessions: dict[tuple[str, str], ExternalMCPSession] = {}
        self._proxied_sessions: dict[tuple[str, str], ProxiedStdioSession | DirectStdioSession] = {}
        self._registry = RegistryBridge()
        self._inspector_config = _load_inspector_config()
        self._proxy_url = os.environ.get("MCP_INSPECTOR_PROXY_URL", "http://localhost:16277")
        # Token is resolved dynamically — see _get_proxy_token()
        self._cached_proxy_token: str = ""

    def _get_proxy_token(self) -> str:
        """Return the current Inspector proxy auth token.

        Resolution order:
        1. MCP_INSPECTOR_AUTH_TOKEN env-var (explicit override)
        2. Auto-detect from .inspector.log (survives Inspector restarts)
        3. Cached value from last successful detection
        """
        env_token = os.environ.get("MCP_INSPECTOR_AUTH_TOKEN", "")
        if env_token:
            return env_token
        detected = _detect_inspector_token()
        if detected:
            self._cached_proxy_token = detected
            return detected
        return self._cached_proxy_token

    def register_tools(self, mcp) -> None:
        """Register inspector tools with the MCP server."""

        # Keep references in closure
        sessions = self._sessions
        proxied_sessions = self._proxied_sessions
        registry = self._registry
        inspector_config = self._inspector_config

        def _all_sessions(user_id: str = "") -> dict[str, Any]:
            """Return the CALLER's sessions, keyed by server_name.

            Identity is the authenticated principal of the request, NOT the
            ``user_id`` the model passes: the model calls with an empty or
            guessed value, and an empty value used to return EVERY user's
            sessions — one identity's live session leaking into another's
            view. The principal on the request is the single source of truth;
            the model-supplied ``user_id`` is only a last resort when no
            principal is present (anonymous/dev with no auth header at all).
            """
            _principal, _ = _caller_identity()
            scope = _principal or user_id
            merged: dict[str, Any] = {}
            for (uid, sname), sess in sessions.items():
                if not scope or uid == scope:
                    merged[sname] = sess
            for (uid, sname), psess in proxied_sessions.items():
                if not scope or uid == scope:
                    merged[sname] = psess
            return merged

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        async def connect_mcp_server(
            server_url: str = "",
            server_name: str = "",
            user_id: str = "",
            access_token: str = "",
        ) -> str:
            """
            Connect to an external MCP server.

            Establishes a JSON-RPC session with the target server,
            performing the full MCP handshake (initialize + initialized).

            Supports two modes:
            - **Direct URL**: provide ``server_url`` (and optionally
              ``server_name``).
            - **Registry lookup**: provide ``server_name`` only; the
              endpoint URL is resolved from the Cosmos DB catalog.

            Args:
                server_url: Full URL of the MCP server endpoint
                           (e.g., "http://host:port/mcp").
                           Leave empty to look up by server_name.
                server_name: Friendly name for the server.
                             Auto-generated from URL if not provided.
                access_token: Optional OAuth bearer token. When provided,
                              sent as ``Authorization: Bearer <token>`` on
                              every request to the server (required for
                              OBO-protected servers such as Agent365).

            Returns:
                Connection status with server info and capabilities.
            """
            try:
                # Identity of the MCP request (principal + forwarded bearer),
                # resolved ONCE here and reused below — one source of truth.
                _principal, _inbound_bearer = _caller_identity()
                if _principal:
                    user_id = _principal
                    logger.info(f"[connect_mcp_server] Auto-detected user_id: {user_id}")

                logger.info(
                    "[connect_mcp_server] called: server_url=%s, server_name=%s, user_id=%s, has_token=%s",
                    server_url,
                    server_name,
                    user_id,
                    bool(access_token),
                )
                # --- Registry lookup when no URL provided ---
                if not server_url and server_name:
                    catalog_entry = await registry.lookup_server(server_name)
                    if not catalog_entry:
                        return format_error_response(
                            error_message=(
                                f"Server '{server_name}' not found "
                                f"in registry. Provide a server_url "
                                f"for direct connection, or register "
                                f"the server first."
                            ),
                            context="registry lookup",
                        )
                    server_url = catalog_entry.get("endpoint", "")
                    if not server_url:
                        return format_error_response(
                            error_message=(f"Server '{server_name}' found in registry but has no endpoint."),
                            context="registry lookup",
                        )
                    logger.info(f"Resolved '{server_name}' from registry -> {server_url}")

                if not server_url:
                    return format_error_response(
                        error_message=(
                            "Either server_url or server_name is "
                            "required. Provide a URL for direct "
                            "connection or a server_name for "
                            "registry lookup."
                        ),
                        context="connecting to MCP server",
                    )

                if not server_name:
                    from urllib.parse import urlparse

                    parsed = urlparse(server_url)
                    server_name = f"{parsed.hostname}:{parsed.port or 80}"

                # Check if already connected
                _key = (user_id, server_name)
                if _key in sessions:
                    existing = sessions[_key]
                    if existing._initialized:
                        return format_success_response(
                            action="Server Already Connected",
                            details={
                                "server_name": server_name,
                                "server_url": existing.server_url,
                                "server_info": existing.server_info,
                                "connected_at": existing.connected_at,
                            },
                            summary=(
                                f"Already connected to '{server_name}'. Use discover_mcp_capabilities to explore."
                            ),
                        )

                # Create and initialize new session
                session = ExternalMCPSession(server_url, server_name)

                # Determine the server's credential_source from the catalog FIRST.
                # A registry-managed source OWNS the token — for managed_identity the
                # platform mints it and it MUST win over any access_token the caller
                # passed (the agent helpfully sends a stale/wrong token, which 401s).
                # An explicit access_token is honored only for direct/manual
                # connections (raw URL or servers with no managed source).
                _cred_source = "static_secret"
                _audience = None
                if server_name:
                    try:
                        _entry = await registry.lookup_server(server_name)
                        if _entry:
                            _cred_source = _entry.get("credential_source") or "static_secret"
                            _audience = _entry.get("audience") or ((_entry.get("oauth_scopes") or [None])[0])
                    except Exception as e:
                        logger.debug(
                            "[connect_mcp_server] catalog lookup failed for '%s': %s",
                            server_name,
                            e,
                        )

                bearer = None
                if _cred_source == "managed_identity" and credential_resolver:
                    # Platform-minted token WINS over anything the caller passed.
                    # Attach the SOURCE too: the session re-resolves per call,
                    # so the minted token's ~1h lifetime never strands it.
                    session.credential_source = _cred_source
                    session.audience = _audience

                    try:
                        bearer = await credential_resolver.resolve_valid_token(
                            credential_source=_cred_source,
                            audience=_audience,
                        )
                        if bearer:
                            logger.info(
                                "[connect_mcp_server] Resolved managed-identity token for '%s' (audience=%s)",
                                server_name,
                                _audience,
                            )
                    except Exception as mi_err:
                        logger.error(
                            "[connect_mcp_server] managed-identity mint failed for '%s': %s",
                            server_name,
                            mi_err,
                        )

                # Caller-provided token — honored only for direct/manual connections
                # (non-managed_identity servers).
                if not bearer:
                    bearer = access_token

                if not bearer and _inbound_bearer:
                    bearer = _inbound_bearer
                    logger.info(
                        "[connect_mcp_server] Forwarding inbound Authorization header to upstream '%s'",
                        server_name,
                    )

                # If still no token, resolve the registered connection's secret from
                # the registry/Key Vault. The lookup MUST key on the AUTHENTICATED user
                # (x-ms-client-principal-id header) — NOT the user_id the agent passed.
                # The model guesses that value (e.g. "current_user" / a display name),
                # which never matches how the connection was registered, so the lookup
                # silently missed and forced passing a token by hand. Prefer the header;
                # fall back to the passed user_id only when the header is absent.
                lookup_user_id = _principal or user_id

                if not bearer and lookup_user_id and server_name:
                    try:
                        conn = await registry.get_user_connection(lookup_user_id, server_name)
                        if conn and conn.get("status") == "active":
                            secret_ref = conn.get("secret_ref", "")
                            if secret_ref and credential_resolver:
                                bearer = await credential_resolver.resolve_valid_token(
                                    credential_source=_cred_source,
                                    secret_ref=secret_ref,
                                )
                                if bearer:
                                    # oauth_refresh rotates near expiry; give
                                    # the session the source so later calls
                                    # keep resolving instead of freezing this
                                    # token.
                                    session.credential_source = _cred_source
                                    session.audience = _audience
                                    session.secret_ref = secret_ref
                                    logger.info(
                                        f"[connect_mcp_server] Resolved token for "
                                        f"'{server_name}' from Key Vault "
                                        f"(source={_cred_source}, user={lookup_user_id})"
                                    )
                    except Exception as kv_err:
                        logger.debug(f"[connect_mcp_server] Could not resolve token from registry: {kv_err}")

                if bearer:
                    # Standard servers take "Bearer <token>". Some (Infobip:
                    # "App <key>") use a custom scheme — if the resolved secret
                    # already carries one, forward it verbatim instead of
                    # double-wrapping ("Bearer App <key>" → 401).
                    _known_schemes = ("bearer ", "app ", "basic ", "token ")
                    session.extra_headers["Authorization"] = (
                        bearer if bearer.lower().startswith(_known_schemes) else f"Bearer {bearer}"
                    )

                try:
                    server_info = await session.initialize()
                except httpx.HTTPStatusError as http_err:
                    if http_err.response.status_code != 401:
                        raise
                    # Same as connect_from_registry: a direct-URL 401 must NOT
                    # dead-end asking for a token. Register the URL (discovery
                    # needs a catalog entry) and pivot to the OAuth sign-in flow.
                    disc, err = await _oauth_discovery_pivot(
                        registry,
                        user_id,
                        server_name,
                        server_url,
                        _inbound_bearer,
                        http_err.response.headers.get("www-authenticate", ""),
                        ensure_registered_url=server_url,
                    )
                    if not disc:
                        await session.close()
                        return format_error_response(
                            error_message=(
                                f"'{server_url}' returned 401 and OAuth could not "
                                f"be set up automatically: {err}. Register it in the "
                                "Applications UI or provide a token."
                            ),
                            context=f"connecting to MCP server at {server_url}",
                        )
                    await session.close()
                    return _pending_auth_response(server_name, server_url, "oauth2", user_id, {}, disc)

                sessions[_key] = session

                return format_success_response(
                    action="MCP Server Connected",
                    details={
                        "server_name": server_name,
                        "server_url": server_url,
                        "server_info": server_info,
                        "protocol_version": "2025-11-25",
                    },
                    summary=(
                        f"Successfully connected to MCP server "
                        f"'{server_info.get('name', server_name)}' "
                        f"at {server_url}. "
                        f"Use discover_mcp_capabilities("
                        f"'{server_name}') to see available tools "
                        f"and resources."
                    ),
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e),
                    context=(f"connecting to MCP server at {server_url}"),
                )

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        async def discover_mcp_capabilities(server_name: str, user_id: str = "") -> str:
            """
            Discover all capabilities (tools, resources, prompts) on a
            connected external MCP server.

            Args:
                server_name: Name of a previously connected server.

            Returns:
                Complete capability listing including tools with
                descriptions, resources, and prompts.
            """
            try:
                all_sess = _all_sessions(user_id)
                if server_name not in all_sess:
                    available = list(all_sess.keys())
                    return format_error_response(
                        error_message=(
                            f"Server '{server_name}' not connected. "
                            f"Available servers: {available or 'none'}. "
                            f"Use connect_mcp_server first."
                        ),
                        context="discovering capabilities",
                    )

                session = all_sess[server_name]

                # Discover all capabilities in parallel
                tools = []
                resources = []
                prompts = []
                # Track per-capability failures so a list error is reported to
                # the model instead of masquerading as "0 tools" — a silent
                # empty list is indistinguishable from a real failure.
                errors: dict[str, str] = {}

                try:
                    tools = await session.list_tools()
                except Exception as e:
                    logger.warning(f"Failed to list tools from {server_name}: {e}")
                    errors["tools"] = str(e)

                try:
                    resources = await session.list_resources()
                except Exception as e:
                    logger.warning(f"Failed to list resources from {server_name}: {e}")
                    errors["resources"] = str(e)

                try:
                    prompts = await session.list_prompts()
                except Exception as e:
                    logger.warning(f"Failed to list prompts from {server_name}: {e}")
                    errors["prompts"] = str(e)

                capabilities = {
                    "server_name": server_name,
                    "server_url": session.server_url,
                    "server_info": session.server_info,
                    "tools": [
                        {
                            "name": t.get("name"),
                            "description": t.get("description", ""),
                            "inputSchema": t.get("inputSchema", {}),
                        }
                        for t in tools
                    ],
                    "resources": [
                        {
                            "uri": r.get("uri"),
                            "name": r.get("name", ""),
                            "description": r.get("description", ""),
                            "mimeType": r.get("mimeType", ""),
                        }
                        for r in resources
                    ],
                    "prompts": [
                        {
                            "name": p.get("name"),
                            "description": p.get("description", ""),
                        }
                        for p in prompts
                    ],
                    "summary": {
                        "total_tools": len(tools),
                        "total_resources": len(resources),
                        "total_prompts": len(prompts),
                    },
                }
                if errors:
                    capabilities["errors"] = errors

                error_note = f" (errores al listar: {', '.join(errors)})" if errors else ""
                return format_success_response(
                    action="Capabilities Discovered",
                    details=capabilities,
                    summary=(
                        f"Server '{server_name}' has "
                        f"{len(tools)} tools, "
                        f"{len(resources)} resources, "
                        f"{len(prompts)} prompts. "
                        f"Use call_external_tool or read_external_resource "
                        f"to interact.{error_note}"
                    ),
                )

            except Exception as e:
                return format_error_response(
                    error_message=str(e),
                    context=f"discovering capabilities on '{server_name}'",
                )

        @mcp.tool(tags={self.domain.value})
        async def call_external_tool(
            server_name: str,
            target_tool: str,
            arguments: dict[str, Any] | None = None,
            user_id: str = "",
        ) -> str:
            """
            Execute a tool on a connected external MCP server.

            Args:
                server_name: Name of a previously connected server.
                target_tool: Name of the tool to execute on that server.
                arguments: Tool arguments as a JSON object
                          (e.g., {"query": "hello"}).

            Returns:
                Tool execution result from the external server.
            """
            try:
                all_sess = _all_sessions(user_id)
                session = all_sess.get(server_name)
                if session is None:
                    available = list(all_sess.keys())
                    # ToolError (not a formatted string): a returned string is
                    # reported by FastMCP as "call_external_tool succeeded",
                    # masking the failure. Raising marks the result isError=true
                    # and propagates the message to the model.
                    raise ToolError(f"Server '{server_name}' not connected. Available: {available or 'none'}.")

                # Parse arguments — accept dict (normal), string (legacy), or None
                if isinstance(arguments, dict):
                    args = arguments
                elif isinstance(arguments, str):
                    try:
                        args = json.loads(arguments) if arguments else {}
                    except json.JSONDecodeError as e:
                        raise ToolError(f"Invalid JSON arguments: {e}") from e
                else:
                    args = {}

                # Pre-flight against the tool's declared inputSchema, BEFORE
                # any network round-trip: the model writes property names in
                # its own convention (job_id) while the server declares
                # another (jobId). Conform the names deterministically when
                # the match is unambiguous, and reject here — with the schema
                # in hand for a one-step retry — what the server would reject
                # anyway. Unknown schema (unlisted tool, list failure) → pass
                # through untouched; the remote stays the authority.
                schema = await session.tool_schema(target_tool)
                renamed: dict[str, str] = {}
                if schema is not None:
                    conformed = normalize_arguments(args, schema)
                    args, renamed = conformed.arguments, conformed.renamed
                    if renamed:
                        logger.info(
                            "[call_external_tool] %s/%s: arguments conformed to inputSchema: %s",
                            server_name,
                            target_tool,
                            renamed,
                        )
                    check = validate_arguments(args, schema)
                    if not check.ok:
                        problems = []
                        if check.missing_required:
                            problems.append(f"missing required {check.missing_required}")
                        if check.unknown:
                            problems.append(f"unknown {check.unknown} (schema declares additionalProperties: false)")
                        raise ToolError(
                            f"Arguments for '{target_tool}' on '{server_name}' "
                            f"do not match its inputSchema: "
                            f"{'; '.join(problems)}. The call was NOT sent. "
                            f"Retry using exactly these properties: "
                            f"{_truncate(json.dumps(schema, ensure_ascii=False), 4000)}"
                        )

                # Call the tool
                result = await session.call_tool(target_tool, args)

                # Extract content from MCP tool result
                content_parts = result.get("content", [])
                text_content = ""
                for part in content_parts:
                    if part.get("type") == "text":
                        text_content += part.get("text", "")
                    elif part.get("type") == "resource":
                        res = part.get("resource") or {}
                        text_content += res.get("text", "") or res.get("blob", "")

                # MCP tool-result contract: isError=true is a FAILED call even
                # though the transport succeeded. Reporting it as SUCCESS hid
                # the failure from the model.
                if result.get("isError"):
                    schema_hint = (
                        f" inputSchema: {_truncate(json.dumps(schema, ensure_ascii=False), 2000)}"
                        if schema is not None
                        else ""
                    )
                    message = text_content or f"'{target_tool}' returned isError with no message."
                    raise ToolError(
                        f"{message} "
                        f"('{target_tool}' on '{server_name}' reported an error "
                        f"for arguments {_truncate(json.dumps(args), 1000)}."
                        f"{schema_hint})"
                    )

                return format_success_response(
                    action="TOOL SUCCESS - External Tool Executed",
                    details={
                        "server_name": server_name,
                        "target_tool": target_tool,
                        "arguments": args,
                        "renamed_arguments": renamed,
                        "result": text_content or result,
                        "is_error": False,
                        "status": "SUCCESS",
                    },
                    summary=(
                        f"✅ SUCCESS: Tool '{target_tool}' executed successfully on '{server_name}'. "
                        f"Result: {text_content[:200] if text_content else 'See details.'}"
                    ),
                )

            except ToolError:
                # Already a typed tool failure — let FastMCP mark isError=true.
                raise
            except Exception as e:
                # Any other failure must also surface as a real error, not a
                # formatted "success" string the framework would log as OK.
                raise ToolError(f"Error executing '{target_tool}' on '{server_name}': {e}") from e

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        async def read_external_resource(server_name: str, resource_uri: str, user_id: str = "") -> str:
            """
            Read a resource from a connected external MCP server.

            Args:
                server_name: Name of a previously connected server.
                resource_uri: URI of the resource to read
                             (e.g., "file:///path" or "ui://widget").

            Returns:
                Resource content with MIME type.
            """
            try:
                all_sess = _all_sessions(user_id)
                if server_name not in all_sess:
                    available = list(all_sess.keys())
                    return format_error_response(
                        error_message=(f"Server '{server_name}' not connected. Available: {available or 'none'}."),
                        context="reading external resource",
                    )

                session = all_sess[server_name]
                result = await session.read_resource(resource_uri)

                contents = result.get("contents", [])
                if not contents:
                    return format_error_response(
                        error_message=f"No content returned for {resource_uri}",
                        context="reading external resource",
                    )

                first = contents[0]
                content_text = first.get("text") or first.get("blob", "")
                mime_type = first.get("mimeType", "text/plain")

                return format_success_response(
                    action="External Resource Read",
                    details={
                        "server_name": server_name,
                        "resource_uri": resource_uri,
                        "mimeType": mime_type,
                        "content": (content_text[:500] if len(content_text) > 500 else content_text),
                        "content_length": len(content_text),
                    },
                    summary=(
                        f"Resource '{resource_uri}' from '{server_name}' ({mime_type}, {len(content_text)} bytes)."
                    ),
                )

            except Exception as e:
                return format_error_response(
                    error_message=str(e),
                    context=f"reading '{resource_uri}' from '{server_name}'",
                )

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        async def list_connected_servers(user_id: str = "") -> str:
            """
            List active sessions and registry catalog servers.

            Shows both in-memory connected sessions and servers
            registered in the Cosmos DB catalog (best-effort).

            Returns:
                Active sessions, registry catalog entries, and
                summary counts.
            """
            try:
                # Identity is the authenticated principal of the request, NOT
                # the model-supplied user_id (empty/guessed). An empty user_id
                # used to list EVERY user's sessions — one identity's live
                # session leaking into another's view.
                _principal, _ = _caller_identity()
                user_id = _principal or user_id

                # --- Active RAM sessions (direct HTTP) ---
                active = []
                for (uid, name), session in sessions.items():
                    if user_id and uid != user_id:
                        continue
                    active.append({
                        "server_name": name,
                        "user_id": uid,
                        "server_url": session.server_url,
                        "server_info": session.server_info,
                        "initialized": session._initialized,
                        "connected_at": session.connected_at,
                        "session_id": session.session_id,
                        "transport": "streamable-http",
                        "source": "ram_session",
                    })

                # --- Active proxied stdio sessions ---
                for (uid, name), psession in proxied_sessions.items():
                    if user_id and uid != user_id:
                        continue
                    active.append({
                        "server_name": name,
                        "user_id": uid,
                        "server_url": psession.server_url,
                        "server_info": psession.server_info,
                        "initialized": psession._initialized,
                        "connected_at": psession.connected_at,
                        "session_id": psession.session_id,
                        "transport": "stdio-via-proxy",
                        "source": "proxied_session",
                    })

                # --- Inspector config servers (best-effort) ---
                inspector_servers = []
                cfg_servers = inspector_config.get("mcpServers", {})
                # Build set of connected server names for the current user scope
                all_connected = {sname for (uid, sname) in sessions.keys() if not user_id or uid == user_id} | {
                    sname for (uid, sname) in proxied_sessions.keys() if not user_id or uid == user_id
                }
                for sname, sdef in cfg_servers.items():
                    transport = "streamable-http" if sdef.get("url") else "stdio"
                    inspector_servers.append({
                        "server_name": sname,
                        "transport": transport,
                        "is_connected": sname in all_connected,
                        "source": "inspector_config",
                    })

                # --- Registry catalog (best-effort) ---
                catalog = []
                try:
                    catalog_entries = await registry.list_catalog()
                    for entry in catalog_entries:
                        sname = entry.get("server_name", "")
                        catalog.append({
                            "server_name": sname,
                            "endpoint": entry.get("endpoint", ""),
                            "auth_type": entry.get("auth_type", "none"),
                            "display_name": entry.get("display_name", sname),
                            "description": entry.get("description", ""),
                            "is_connected": sname in all_connected,
                            "source": "registry",
                        })
                except Exception as e:
                    logger.debug(f"Registry catalog unavailable: {e}")

                total_active = len(active)
                total_catalog = len(catalog)
                total_inspector = len(inspector_servers)

                if not active and not catalog and not inspector_servers:
                    return format_success_response(
                        action="Connected Servers",
                        details={
                            "active_sessions": [],
                            "inspector_config_servers": [],
                            "registry_catalog": [],
                            "total_active": 0,
                            "total_inspector": 0,
                            "total_catalog": 0,
                        },
                        summary=(
                            "No active sessions, no inspector config, "
                            "and registry is empty or unavailable. "
                            "Use connect_mcp_server, "
                            "connect_stdio_server, or "
                            "connect_from_registry."
                        ),
                    )

                parts = []
                if total_active:
                    all_names = [sname for (uid, sname) in sessions.keys() if not user_id or uid == user_id] + [
                        sname for (uid, sname) in proxied_sessions.keys() if not user_id or uid == user_id
                    ]
                    parts.append(f"{total_active} active session(s): {', '.join(all_names)}")
                not_connected = [s["server_name"] for s in inspector_servers if not s["is_connected"]]
                if not_connected:
                    parts.append(
                        f"{len(not_connected)} available in inspector "
                        f"config (not connected): "
                        f"{', '.join(not_connected)}. "
                        f"Use connect_stdio_server to connect."
                    )
                if total_catalog:
                    parts.append(f"{total_catalog} server(s) in registry")

                return format_success_response(
                    action="Connected Servers",
                    details={
                        "active_sessions": active,
                        "inspector_config_servers": inspector_servers,
                        "registry_catalog": catalog,
                        "total_active": total_active,
                        "total_inspector": total_inspector,
                        "total_catalog": total_catalog,
                    },
                    summary=". ".join(parts) + ".",
                )

            except Exception as e:
                return format_error_response(
                    error_message=str(e),
                    context="listing connected servers",
                )

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        async def register_mcp_server(
            server_url: str,
            server_name: str,
            display_name: str = "",
            description: str = "",
            auth_type: str = "",
            credential_source: str = "",
            audience: str = "",
            transport: str = "streamable-http",
            user_id: str = "",
        ) -> str:
            """
            Persist an MCP server URL in the Cosmos registry so it becomes a
            reusable catalog entry (visible in the UI and to
            connect_from_registry) instead of an ephemeral in-memory session.

            This is the WRITE half of the Cosmos lane; connect_mcp_server is
            ephemeral (dies with the replica). Use this for arbitrary /
            self-hosted / third-party servers where the platform can hold the
            credential. First-party servers (Graph, Teams, WorkIQ) are NOT for
            this lane: they are bound server-side to the published Foundry
            agent and reject third-party OBO.

            You normally only need server_url + server_name. Leave auth_type /
            credential_source / audience EMPTY unless the user stated them: the
            backend derives the working credential strategy from the endpoint
            (Azure data planes such as *.search.windows.net, *.grafana.azure.com,
            *.services.ai.azure.com, management.azure.com → managed_identity
            with the right audience; oauth2 → oauth_refresh; api_key →
            static_secret). Sending explicit values DISABLES that derivation.

            Args:
                server_url: Full MCP endpoint, e.g. https://host/mcp.
                server_name: Unique slug key, e.g. "grafana-prod".
                display_name: UI label; defaults to server_name.
                description: Optional free text.
                auth_type: Optional override: none | api_key | oauth2 | bearer_token
                           | managed_identity (what the wire sees).
                credential_source: Optional override: static_secret | oauth_refresh
                           | managed_identity (how the platform OBTAINS the token).
                audience: Optional AAD scope for managed_identity, e.g. "<appId>/.default".
                transport: streamable-http | sse.
                user_id: Optional; the authenticated caller identity on the
                         request always wins (accepted so callers that pass it
                         are not rejected).

            Returns:
                The persisted catalog entry (with the derived auth_type /
                credential_source / audience), or an error (409 if the name exists).
                Next step on success: connect_from_registry(server_name). If the
                server then answers 401, connect_from_registry returns an
                oauth_url the user must open (OAuth is discovered automatically).
            """
            try:
                _principal, _bearer_token = _caller_identity()
                user_id = _principal or user_id
                if not user_id:
                    return format_error_response(
                        error_message="No authenticated caller identity on the request.",
                        context="register_mcp_server",
                    )

                url = (server_url or "").strip()
                if not url.lower().startswith(("http://", "https://")):
                    return format_error_response(
                        error_message=f"server_url must be http(s): {url!r}",
                        context="register_mcp_server",
                    )
                name = (server_name or "").strip()
                if not name:
                    return format_error_response(
                        error_message="server_name is required.",
                        context="register_mcp_server",
                    )

                # Send ONLY what the caller stated. MCPServerEntry's
                # _derive_credential_source runs `if not credential_source`,
                # so a default here would silently disable it and an Azure
                # endpoint would be stored none/static_secret → no Authorization
                # → 401. Same body shape the UI sends.
                entry: dict[str, Any] = {
                    "server_name": name,
                    "display_name": (display_name or name).strip(),
                    "description": description or "",
                    "endpoint": url,
                    "transport": transport or "streamable-http",
                }
                if auth_type:
                    # Normalize what models actually send ("oauth", "bearer",
                    # "api-key") to the catalog enum; anything still unknown is
                    # dropped so the backend derives it instead of answering 422.
                    _alias = {
                        "oauth": "oauth2",
                        "oauth2": "oauth2",
                        "bearer": "bearer_token",
                        "bearer_token": "bearer_token",
                        "apikey": "api_key",
                        "api-key": "api_key",
                        "api_key": "api_key",
                        "none": "none",
                        "managed_identity": "managed_identity",
                    }
                    _norm = _alias.get(auth_type.strip().lower())
                    if _norm:
                        entry["auth_type"] = _norm
                    else:
                        logger.info(
                            "[register_mcp_server] ignoring unknown auth_type=%r; backend will derive it",
                            auth_type,
                        )
                if credential_source:
                    entry["credential_source"] = credential_source
                if audience:
                    entry["audience"] = audience

                result, err = await registry.register_server(user_id, entry, bearer_token=_bearer_token)
                if result is None:
                    return format_error_response(
                        error_message=(
                            f"Failed to register '{name}': {err}. If it already exists, call connect_from_registry."
                        ),
                        context="register_mcp_server",
                    )

                server = result.get("server", {})
                # Report what the backend actually persisted (derived values),
                # not what we sent.
                eff_auth = server.get("auth_type", "?")
                eff_src = server.get("credential_source", "?")
                eff_aud = server.get("audience") or "-"
                return format_success_response(
                    action="MCP Server Registered",
                    details={
                        "server": server,
                        "next_step": f"connect_from_registry('{name}')",
                    },
                    summary=(
                        f"Registered '{name}' → {url} (auth_type={eff_auth}, "
                        f"credential_source={eff_src}, audience={eff_aud}). "
                        f"Persisted in the catalog; now call "
                        f"connect_from_registry('{name}')."
                    ),
                )
            except Exception as e:
                return format_error_response(error_message=str(e), context="register_mcp_server")

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        async def connect_from_registry(server_name: str, user_id: str = "") -> str:
            """
            Connect to an MCP server from the registry with
            user authorization check.

            Looks up the server in the Cosmos DB catalog, verifies
            user authorization, and connects if allowed.  For
            servers requiring authentication (OAuth2, API key, etc.)
            the tool initiates the auth flow and returns
            instructions.

            Args:
                server_name: Name of the server in the registry
                             (e.g., "youtube-api").
                user_id: User ID for authorization check.
                         Defaults to "sample_user" in dev.

            Returns:
                Connection result or auth instructions.
            """
            try:
                _principal, _bearer_token = _caller_identity()
                if _principal:
                    user_id = _principal

                # 1. Lookup server in catalog
                server = await registry.lookup_server(server_name)
                if not server:
                    catalog = await registry.list_catalog()
                    available = [s.get("server_name") for s in catalog]
                    return format_error_response(
                        error_message=(
                            f"Server '{server_name}' not found in registry. Available: {available or 'none'}."
                        ),
                        context="registry lookup",
                    )

                endpoint = server.get("endpoint", "")
                auth_type = server.get("auth_type", "none")

                # 2. Initiate / check user connection — forward the caller's
                # Bearer token so the backend resolves the real user identity
                # instead of falling back to sample_user.
                conn_result = await registry.initiate_connection(user_id, server_name, bearer_token=_bearer_token)
                if not conn_result:
                    return format_error_response(
                        error_message=(
                            f"Failed to initiate connection for "
                            f"user '{user_id}' to "
                            f"'{server_name}'. Backend API may "
                            f"be unavailable."
                        ),
                        context="connection initiation",
                    )

                if conn_result.get("error"):
                    return format_error_response(
                        error_message=str(conn_result["error"]),
                        context="connection initiation",
                    )

                connection = conn_result.get("connection", {})
                status = connection.get("status", "unknown")

                # 3. Handle pending auth
                if status == "pending_auth":
                    return _pending_auth_response(server_name, endpoint, auth_type, user_id, server, conn_result)

                # 4. Active — connect to endpoint
                if not endpoint:
                    return format_error_response(
                        error_message=(f"Server '{server_name}' has no endpoint in the registry."),
                        context="endpoint resolution",
                    )

                # Build extra headers by resolving a VALID token per the server's
                # credential_source (managed_identity mints fresh from the platform MI;
                # static_secret / oauth_refresh come from the user's Key Vault blob).
                # auth_type stays = what the wire sees (a Bearer); HOW we get it lives
                # in the resolver.
                extra_headers: dict[str, str] = {}
                _cred_source: str | None = None
                _audience: str | None = None
                _secret_ref: str = ""
                if auth_type != "none" and status == "active" and credential_resolver:
                    _cred_source = server.get("credential_source") or "static_secret"
                    _audience = server.get("audience") or ((server.get("oauth_scopes") or [None])[0])
                    _secret_ref = connection.get("secret_ref", "")
                    try:
                        bearer_token = await credential_resolver.resolve_valid_token(
                            credential_source=_cred_source,
                            audience=_audience,
                            secret_ref=_secret_ref,
                        )
                        if bearer_token:
                            # Same scheme rule as connect_mcp_server: a secret
                            # that already carries its scheme ("App <key>" for
                            # Infobip) is forwarded verbatim — double-wrapping
                            # ("Bearer App <key>") gets a 401.
                            _known_schemes = ("bearer ", "app ", "basic ", "token ")
                            extra_headers["Authorization"] = (
                                bearer_token
                                if bearer_token.lower().startswith(_known_schemes)
                                else f"Bearer {bearer_token}"
                            )
                            logger.info(
                                f"[connect_from_registry] Resolved token for '{server_name}' (source={_cred_source})"
                            )
                        else:
                            logger.warning(
                                f"[connect_from_registry] No token resolved for '{server_name}' (source={_cred_source})"
                            )
                    except Exception as kv_err:
                        logger.error(f"[connect_from_registry] Token resolution failed for '{server_name}': {kv_err}")

                # Already connected?
                _reg_key = (user_id, server_name)
                if _reg_key in sessions:
                    existing = sessions[_reg_key]
                    if existing._initialized:
                        # Reused sessions adopt the credential SOURCE so their
                        # calls resolve tokens per call from now on — a session
                        # created before this code carries only the frozen
                        # (long-expired) header.
                        if _cred_source:
                            existing.credential_source = _cred_source
                            existing.audience = _audience
                            existing.secret_ref = _secret_ref
                        return format_success_response(
                            action="Already Connected (Registry)",
                            details={
                                "server_name": server_name,
                                "server_url": existing.server_url,
                                "server_info": existing.server_info,
                                "auth_type": auth_type,
                                "user_id": user_id,
                                "registry_status": status,
                            },
                            summary=(f"Already connected to '{server_name}' (auth={auth_type}, status={status})."),
                        )

                # Create session with optional auth headers
                session = ExternalMCPSession(endpoint, server_name)
                if extra_headers:
                    session.extra_headers = extra_headers
                if _cred_source:
                    session.credential_source = _cred_source
                    session.audience = _audience
                    session.secret_ref = _secret_ref

                try:
                    server_info = await session.initialize()
                except httpx.HTTPStatusError as http_err:
                    if http_err.response.status_code != 401:
                        raise
                    # The remote demands auth we don't hold. Do NOT dead-end on a
                    # raw 401 — pivot to the OAuth sign-in flow (shared helper).
                    disc, err = await _oauth_discovery_pivot(
                        registry,
                        user_id,
                        server_name,
                        endpoint,
                        _bearer_token,
                        http_err.response.headers.get("www-authenticate", ""),
                    )
                    if not disc:
                        return format_error_response(
                            error_message=(
                                f"'{server_name}' returned 401 and OAuth could not "
                                f"be set up automatically: {err}. "
                                "Provide a static token via the Applications UI."
                            ),
                            context=f"connecting to '{server_name}' from registry",
                        )
                    return _pending_auth_response(server_name, endpoint, "oauth2", user_id, server, disc)
                sessions[_reg_key] = session

                return format_success_response(
                    action="Connected from Registry",
                    details={
                        "server_name": server_name,
                        "endpoint": endpoint,
                        "server_info": server_info,
                        "auth_type": auth_type,
                        "user_id": user_id,
                        "registry_status": status,
                        "protocol_version": "2025-11-25",
                    },
                    summary=(
                        f"Connected to '{server_name}' via "
                        f"registry (auth={auth_type}, "
                        f"status={status}). Use "
                        f"discover_mcp_capabilities("
                        f"'{server_name}') to explore."
                    ),
                )

            except Exception as e:
                return format_error_response(
                    error_message=str(e),
                    context=(f"connecting to '{server_name}' from registry"),
                )

        @mcp.tool(tags={self.domain.value}, annotations={"readOnlyHint": True})
        async def connect_stdio_server(server_name: str, user_id: str = "") -> str:
            """
            Connect to a stdio-based MCP server DIRECTLY (no proxy needed).

            Spawns the server command as a child process and communicates
            via stdin/stdout using the MCP SDK's stdio_client.

            Looks up the server definition in mcp-inspector-config.json
            for the command, args, and env vars.

            Use this for servers that run as local CLI processes
            (e.g., GitHub, filesystem, server-everything).

            Use ``list_connected_servers`` to see available server names
            from the inspector config.

            Args:
                server_name: Name of the server as defined in
                             mcp-inspector-config.json (e.g., "github",
                             "filesystem").
                user_id: User ID for session isolation (default: shared).

            Returns:
                Connection status with server info and tool count.
            """
            try:
                # Identity is the authenticated principal, NOT the model-supplied
                # ``user_id`` — same rule as connect_mcp_server and the reader
                # (_my_sessions): the principal is the single source of truth and
                # the model-supplied value is only a fallback when anonymous.
                _principal, _ = _caller_identity()
                user_id = _principal or user_id
                # Already connected?
                _stdio_key = (user_id, server_name)
                if _stdio_key in proxied_sessions:
                    existing = proxied_sessions[_stdio_key]
                    if existing.is_alive:
                        return format_success_response(
                            action="Already Connected (stdio)",
                            details={
                                "server_name": server_name,
                                "server_info": existing.server_info,
                                "transport": "stdio-direct",
                            },
                            summary=(
                                f"Already connected to "
                                f"'{server_name}' via direct stdio. "
                                f"Use discover_mcp_capabilities to "
                                f"explore."
                            ),
                        )
                    # Dead session — clean up and reconnect
                    logger.info(f"[connect_stdio_server] Stale session '{server_name}' — reconnecting")
                    try:
                        await existing.close()
                    except Exception:
                        pass
                    del proxied_sessions[_stdio_key]

                # Look up in inspector config
                cfg_servers = inspector_config.get("mcpServers", {})
                if server_name not in cfg_servers:
                    available = [
                        n
                        for n, d in cfg_servers.items()
                        if d.get("command")  # stdio servers only
                    ]
                    return format_error_response(
                        error_message=(
                            f"Server '{server_name}' not found in "
                            f"inspector config. Available stdio "
                            f"servers: {available or 'none'}."
                        ),
                        context="connecting stdio server",
                    )

                server_def = cfg_servers[server_name]
                command = server_def.get("command")
                if not command:
                    return format_error_response(
                        error_message=(
                            f"Server '{server_name}' is not a stdio "
                            f"server (no 'command' field). Use "
                            f"connect_mcp_server for URL-based servers."
                        ),
                        context="connecting stdio server",
                    )

                args = server_def.get("args", [])
                env = server_def.get("env", {})

                # Resolve env var placeholders — os.environ first, then Key Vault
                resolved_env = {}
                for k, v in env.items():
                    if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                        env_key = v[2:-1]
                        resolved = os.environ.get(env_key, "")

                        if not resolved:
                            # Attempt Key Vault resolution using secret name = env_key
                            # normalized to lowercase-hyphen (e.g. GITHUB_PERSONAL_ACCESS_TOKEN
                            # → github-personal-access-token)
                            if credential_resolver:
                                try:
                                    secret_name = env_key.lower().replace("_", "-")
                                    creds = await credential_resolver.resolve_by_secret_ref(secret_name)
                                    if creds:
                                        resolved = (
                                            creds.get("token")
                                            or creds.get("api_key")
                                            or creds.get("access_token")
                                            or creds.get(env_key)
                                            or next(iter(creds.values()), "")
                                        )
                                        if resolved:
                                            logger.info(
                                                f"[connect_stdio_server] Resolved credential "
                                                f"for '{server_name}' from Key Vault"
                                            )
                                except Exception as kv_err:
                                    logger.debug(f"[connect_stdio_server] KV lookup failed for '{env_key}': {kv_err}")

                        if not resolved:
                            return format_error_response(
                                error_message=(
                                    f"Credential '{env_key}' required by "
                                    f"'{server_name}' not found in environment "
                                    f"or Key Vault (secret: "
                                    f"'{env_key.lower().replace('_', '-')}')."
                                ),
                                context="resolving server credentials",
                            )
                        resolved_env[k] = resolved
                    else:
                        resolved_env[k] = v

                # Create DIRECT stdio session — no proxy dependency
                dsession = DirectStdioSession(
                    command=command,
                    args=args,
                    server_name=server_name,
                    env=resolved_env,
                )

                server_info = await dsession.initialize()
                proxied_sessions[_stdio_key] = dsession

                # Get tool count for summary
                try:
                    tools = await dsession.list_tools()
                    tool_count = len(tools)
                except Exception:
                    tool_count = -1

                return format_success_response(
                    action="Stdio Server Connected",
                    details={
                        "server_name": server_name,
                        "server_info": server_info,
                        "command": command,
                        "args": args,
                        "transport": "stdio-direct",
                        "tool_count": tool_count,
                    },
                    summary=(
                        f"Connected to stdio server "
                        f"'{server_info.get('name', server_name)}' "
                        f"directly ({tool_count} tools). "
                        f"Use discover_mcp_capabilities('"
                        f"{server_name}') to explore."
                    ),
                )

            except Exception as e:
                return format_error_response(
                    error_message=str(e),
                    context=(f"connecting to stdio server '{server_name}'"),
                )

    @property
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        return len(self._registered_tools)
