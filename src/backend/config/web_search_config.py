# Copyright (c) Microsoft. All rights reserved.
"""Resolve web-search access independently of domain MCP and Azure credentials."""

from dataclasses import dataclass, field
from typing import Sequence


PARALLEL_SEARCH_URL = "https://search.parallel.ai/mcp"
WEB_SEARCH_TOOLS = ("web_search", "web_fetch")
WEB_SEARCH_USER_AGENT = "macae/0.1.0 (+https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator)"


@dataclass(frozen=True, slots=True)
class WebSearchConfig:
    """A resolved Parallel connection; ``None`` from resolve means no access."""

    allowed_tools: tuple[str, ...] = WEB_SEARCH_TOOLS
    api_key: str | None = field(default=None, repr=False)

    @classmethod
    def resolve(
        cls,
        provider: str | None = None,
        allowed_tools: Sequence[str] | None = None,
        *,
        default_provider: str = "parallel",
        api_key: str | None = None,
    ) -> "WebSearchConfig | None":
        """Default to Parallel, respecting global denial and per-agent choices.

        Unknown providers/permissions are errors, never a reason to fall back.
        A global ``none`` is an operator restriction that agents cannot override.
        """
        if default_provider not in ("parallel", "none"):
            raise ValueError("WEB_SEARCH_PROVIDER must be 'parallel' or 'none'")
        if provider not in (None, "parallel", "none"):
            raise ValueError("web_search_provider must be 'parallel' or 'none'")
        tools = WEB_SEARCH_TOOLS if allowed_tools is None else tuple(allowed_tools)
        if any(name not in WEB_SEARCH_TOOLS for name in tools):
            raise ValueError("web_search_tools may contain only web_search and web_fetch")
        if default_provider == "none" or provider == "none" or not tools:
            return None
        return cls(tuple(dict.fromkeys(tools)), api_key=api_key or None)

    def get_headers(self) -> dict[str, str]:
        """Only dedicated Parallel credentials may leave on this connection."""
        headers = {"User-Agent": WEB_SEARCH_USER_AGENT}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
