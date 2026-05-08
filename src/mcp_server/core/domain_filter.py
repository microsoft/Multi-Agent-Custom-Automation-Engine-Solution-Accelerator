"""Middleware to filter MCP tools by domain (tag) using HTTP query string.

Agents pass `?domains=image,marketing` on the MCP URL. This middleware:
- Filters list_tools responses to tools whose tags intersect the requested domains.
- Blocks call_tool for tools outside the requested domains.

If `domains` is missing/empty, no filtering is applied (backward compatible).
"""
from __future__ import annotations

import logging
from typing import Iterable

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


def _requested_domains() -> set[str]:
    """Read the `domains` query parameter from the current HTTP request.

    Returns an empty set if there is no HTTP request (e.g., stdio transport)
    or if the parameter is absent.
    """
    try:
        request = get_http_request()
    except RuntimeError:
        return set()
    raw = request.query_params.get("domains") if request is not None else None
    if not raw:
        return set()
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


class DomainFilterMiddleware(Middleware):
    """Restrict tool visibility/execution to a caller-supplied domain allowlist."""

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        domains = _requested_domains()
        if not domains:
            return tools
        filtered = [t for t in tools if _tags(t) & domains]
        logger.info(
            "DomainFilter: domains=%s, %d/%d tools allowed",
            sorted(domains),
            len(filtered),
            len(tools),
        )
        return filtered

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        domains = _requested_domains()
        if domains and context.fastmcp_context:
            try:
                tool = await context.fastmcp_context.fastmcp.get_tool(
                    context.message.name
                )
            except Exception:  # noqa: BLE001 - fall through to handler if missing
                tool = None
            if tool is not None and not (_tags(tool) & domains):
                raise ToolError(
                    f"Tool '{context.message.name}' is not available for "
                    f"domains={sorted(domains)}"
                )
        return await call_next(context)


def _tags(tool) -> set[str]:
    raw: Iterable[str] | None = getattr(tool, "tags", None)
    if not raw:
        return set()
    return {str(t).lower() for t in raw}
