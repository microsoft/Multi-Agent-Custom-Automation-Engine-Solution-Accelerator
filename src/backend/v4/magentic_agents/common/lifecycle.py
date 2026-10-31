from __future__ import annotations

import inspect
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, cast

from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework_azure_ai import AzureAIClient, AzureAIProjectAgentOptions
from azure.ai.agents.aio import AgentsClient
from azure.ai.projects.models import (
    BingCustomSearchConfiguration,
    BingCustomSearchPreviewTool,
    BingCustomSearchToolParameters,
    BingGroundingSearchConfiguration,
    BingGroundingSearchToolParameters,
    BingGroundingTool,
    BrowserAutomationPreviewTool,
    BrowserAutomationToolConnectionParameters,
    BrowserAutomationToolParameters,
    CodeInterpreterTool,
    FabricDataAgentToolParameters,
    FileSearchTool,
    ImageGenTool,
    MCPTool,
    MicrosoftFabricPreviewTool,
    PromptAgentDefinition,
    SharepointGroundingToolParameters,
    SharepointPreviewTool,
    Tool,
    ToolProjectConnection,
    WebSearchTool,
)

from common.config.app_config import config
from common.database.database_base import DatabaseBase
from common.models.messages_af import TeamConfiguration
from common.utils.utils_agents import generate_assistant_id
from v4.common.mcp_tool import ReconnectingMCPTool
from v4.common.services.team_service import TeamService
from v4.config.agent_registry import agent_registry
from v4.magentic_agents.models.agent_models import MCPConfig

# Cache Foundry registrations per process so ephemeral runtime agents do not
# recreate the same persisted agent on every request.
_FOUNDRY_REGISTERED_AGENT_NAMES: set[str] = set()

# name -> fingerprint of the definition this process last published/verified.
# Composed agents are REUSED BY NAME across requests but their Router-written
# instructions/tools vary per request: reuse must be decided by comparing
# definitions, not by name alone (name-only reuse froze the FIRST published
# toolset forever; force-publish minted a version per run — both wrong).
_FOUNDRY_PUBLISHED_FINGERPRINTS: dict[str, str] = {}


def _definition_fingerprint(model: str, instructions: str, tools) -> str:
    """Canonical identity of an agent definition for publish-on-diff.

    A tool reduces to its ``type`` plus its EXECUTION IDENTITY: the minimal
    set of values that decide WHICH resource the tool works against. Tools
    with no resource behind them (code_interpreter, web_search, image_gen)
    reduce to the bare type — they cannot drift.

    Both shapes must yield the SAME string: locally built SDK models
    (attributes) and definitions read back from Foundry (dict-like). An
    extractor that only understands one shape makes published_fp differ from
    desired_fp forever, publishing a version on every single run.
    """

    def _get(obj: Any, key: str) -> Any:
        """Read one field from either shape."""
        if obj is None:
            return None
        if hasattr(obj, "get"):
            return obj.get(key)
        return getattr(obj, key, None)

    def _ids(seq: Any, key: str = "project_connection_id") -> list[str]:
        """Connection ids from a list whose items may be objects, dicts or
        plain strings. Sorted: order is not part of the identity."""
        out: list[str] = []
        for item in seq or []:
            if isinstance(item, str):
                out.append(item)
                continue
            val = _get(item, key)
            if val:
                out.append(str(val))
        return sorted(out)

    def _identity(tool: Any, tool_type: str) -> list[str]:
        """The values that decide which resource this tool talks to."""
        if tool_type == "mcp":
            # allowed_tools narrows what the server may run: same URL with a
            # different subset is a different agent.
            return [
                str(_get(tool, "server_url") or ""),
                *sorted(str(a) for a in (_get(tool, "allowed_tools") or [])),
                str(_get(tool, "project_connection_id") or ""),
            ]
        if tool_type == "file_search":
            return sorted(str(v) for v in (_get(tool, "vector_store_ids") or []))
        if tool_type == "azure_ai_search":
            res = _get(tool, "azure_ai_search")
            vals: list[str] = []
            for idx in _get(res, "indexes") or []:
                vals.append(
                    ":".join(
                        str(_get(idx, k) or "")
                        for k in (
                            "project_connection_id",
                            "index_name",
                            "query_type",
                            "top_k",
                        )
                    )
                )
            return sorted(vals)
        if tool_type == "bing_grounding":
            params = _get(tool, "bing_grounding")
            return _ids(_get(params, "search_configurations"))
        if tool_type == "bing_custom_search_preview":
            params = _get(tool, "bing_custom_search_preview")
            vals = []
            for cfg in _get(params, "search_configurations") or []:
                vals.append(
                    f"{_get(cfg, 'project_connection_id') or ''}"
                    f":{_get(cfg, 'instance_name') or ''}"
                )
            return sorted(vals)
        if tool_type == "sharepoint_grounding_preview":
            params = _get(tool, "sharepoint_grounding_preview")
            return _ids(_get(params, "project_connections"))
        if tool_type == "fabric_dataagent_preview":
            params = _get(tool, "fabric_dataagent_preview")
            return _ids(_get(params, "project_connections"))
        if tool_type == "browser_automation_preview":
            params = _get(tool, "browser_automation_preview")
            conn = _get(params, "connection")
            return [str(_get(conn, "project_connection_id") or "")]
        # code_interpreter, web_search, image_generation, ...: no resource.
        return []

    parts: list[str] = []
    for tool in tools or []:
        tool_type = str(_get(tool, "type") or "")
        identity = [v for v in _identity(tool, tool_type) if v]
        parts.append(f"{tool_type}:{'|'.join(identity)}" if identity else tool_type)

    return f"{model}\n{instructions}\n" + "|".join(sorted(parts))


class MCPEnabledBase:
    """
    Base that owns an AsyncExitStack and (optionally) prepares an MCP tool
    for subclasses to attach to ChatOptions (agent_framework style).
    Subclasses must implement _after_open() and assign self._agent.
    """

    def __init__(
        self,
        mcp: MCPConfig | None = None,
        team_service: TeamService | None = None,
        team_config: TeamConfiguration | None = None,
        project_endpoint: str | None = None,
        memory_store: DatabaseBase | None = None,
        agent_name: str | None = None,
        agent_description: str | None = None,
        agent_instructions: str | None = None,
        model_deployment_name: str | None = None,
        project_client=None,
        user_access_token: str | None = None,
    ) -> None:
        self._stack: AsyncExitStack | None = None
        self.mcp_cfg: MCPConfig | None = mcp
        self.mcp_tool: MCPStreamableHTTPTool | None = None
        self._agent: Agent | None = None
        self.team_service: TeamService | None = team_service
        self.team_config: TeamConfiguration | None = team_config
        self.client: AgentsClient | None = None
        self.project_endpoint = project_endpoint
        self.creds = None
        # True only when self.creds is a per-user (OBO/passthrough) credential this
        # agent created and must close. The process-scoped Managed Identity
        # credential is borrowed (owned by config) and must NOT be closed here.
        self._owns_creds = False
        self.memory_store: DatabaseBase | None = memory_store
        self.agent_name: str | None = agent_name
        self.agent_description: str | None = agent_description
        self.agent_instructions: str | None = agent_instructions
        self.model_deployment_name: str | None = model_deployment_name
        self.project_client = project_client
        self.user_access_token = user_access_token
        self.logger = logging.getLogger(__name__)

    async def open(self) -> MCPEnabledBase:
        if self._stack is not None:
            return self
        self._stack = AsyncExitStack()

        # Use the end-user credential when a token is available so Foundry's ARA
        # can perform its OBO exchange to user-delegated tool connections
        # (e.g. agent365/WorkIQ). With ENABLE_OBO this is a real
        # OnBehalfOfCredential; otherwise it forwards the EasyAuth token verbatim.
        # Falls back to Managed Identity in local/dev (no user token present).
        if self.user_access_token and config.APP_ENV != "dev":
            # Per-user credential: this agent owns it and closes it on close().
            new_creds = config.build_user_credential(self.user_access_token)
            self.creds = new_creds
            self._owns_creds = True
            if self._stack:
                await self._stack.enter_async_context(new_creds)
        else:
            # In local dev the device-code/EasyAuth user token is NOT audienced for
            # the Foundry data plane (https://ai.azure.com), so forwarding it verbatim
            # is rejected ("audience is incorrect"). Use the shared az/Managed Identity
            # credential for the data plane — it mints a correctly-audienced token. The
            # raw user token is still forwarded to MCP in _prepare_mcp_tool (unaffected).
            # Borrow the process-scoped Managed Identity credential. It is NOT
            # entered into this agent's stack and is NOT closed by close(), so
            # closing/rebuilding this agent can never tear down the transport that
            # other in-flight tasks (e.g. a background orchestration run) share.
            new_creds = config.get_shared_async_credential()
            self.creds = new_creds
            self._owns_creds = False
        # Create AgentsClient with a custom aiohttp connector to avoid
        # 'SSL shutdown timed out' errors on long-running Foundry calls.
        # The default aiohttp ssl_shutdown_timeout is 5s which is too short
        # when the server closes the connection after a long response.
        import aiohttp

        _connector = aiohttp.TCPConnector(
            ssl_shutdown_timeout=30.0,
            enable_cleanup_closed=True,
        )
        self.client = AgentsClient(
            endpoint=self.project_endpoint or "",
            credential=new_creds,
            connection=_connector,
        )
        if self._stack:
            await self._stack.enter_async_context(self.client)
        # Prepare MCP
        await self._prepare_mcp_tool()

        # Let subclass build agent client
        await self._after_open()

        # Register agent (best effort)
        try:
            agent_registry.register_agent(self)
        except Exception as exc:
            # Best-effort registration; log and continue without failing open()
            self.logger.warning(
                "Failed to register agent %s in agent_registry: %s",
                type(self).__name__,
                exc,
                exc_info=True,
            )

        return self

    async def close(self) -> None:
        if self._stack is None and self.mcp_tool is None:
            return
        try:
            # 1. Close the underlying AzureAIClient / ResponsesClient
            _agent_close = getattr(self._agent, "close", None) if self._agent else None
            if callable(_agent_close):
                try:
                    result = _agent_close()
                    if inspect.isawaitable(result):
                        await result
                except Exception as exc:
                    self.logger.warning(
                        "Error closing AzureAIClient for agent %s: %s",
                        self.agent_name,
                        exc,
                    )

            # 2. Close AgentsClient
            if self.client and hasattr(self.client, "close"):
                try:
                    await self.client.close()
                except Exception as exc:
                    self.logger.debug(
                        "AgentsClient close error (non-critical): %s", exc
                    )

            # 3. Close MCPStreamableHTTPTool directly (NOT via stack).
            # anyio cancel scopes must be exited from the same task that entered
            # them. We swallow RuntimeError from cross-task teardown — the HTTP
            # DELETE /mcp is still sent by the SDK before the error fires, so the
            # server-side session is cleaned up regardless.
            if self.mcp_tool is not None:
                try:
                    await self.mcp_tool.__aexit__(None, None, None)
                except RuntimeError as exc:
                    if (
                        "cancel scope" in str(exc).lower()
                        or "different task" in str(exc).lower()
                    ):
                        self.logger.debug(
                            "MCP tool cross-task teardown (expected on force-rebuild): %s",
                            exc,
                        )
                    else:
                        self.logger.warning("MCP tool close error: %s", exc)
                except Exception as exc:
                    self.logger.debug("MCP tool close error (non-critical): %s", exc)

            # 4. Release the AsyncExitStack (http_client and other non-MCP contexts).
            if self._stack:
                try:
                    await self._stack.aclose()
                except Exception as exc:
                    self.logger.debug(
                        "Stack release notice for agent '%s': %s",
                        self.agent_name,
                        exc,
                    )

            # 5. Close credential — ONLY if this agent owns it.
            if self._owns_creds and self.creds and hasattr(self.creds, "close"):
                try:
                    await self.creds.close()
                except Exception as exc:
                    self.logger.debug("Credential close error (non-critical): %s", exc)

        finally:
            try:
                agent_registry.unregister_agent(self)
            except Exception as exc:
                self.logger.debug(
                    "Agent unregister error (non-critical) for '%s': %s",
                    self.agent_name,
                    exc,
                )
            self._stack = None
            self.mcp_tool = None
            self._agent = None
            self.client = None
            self.creds = None
            self._owns_creds = False

    # Context manager
    async def __aenter__(self) -> MCPEnabledBase:
        return await self.open()

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        await self.close()

    # Delegate to underlying agent
    def __getattr__(self, name: str) -> Any:
        if self._agent is not None:
            return getattr(self._agent, name)
        raise AttributeError(f"{type(self).__name__} has no attribute '{name}'")

    async def _after_open(self) -> None:
        """Subclasses must build self._agent here."""
        raise NotImplementedError

    def get_chat_client(self) -> AzureAIClient[AzureAIProjectAgentOptions]:
        """Return AzureAIClient for agents WITHOUT runtime tools (e.g. Azure Search path).

        Uses agent_name with use_latest_version=True to get the latest agent version.
        Agent reuse is handled automatically by the SDK via agent_name.

        WARNING: AzureAIClient does NOT support runtime tools (MCP, dynamic functions).
        For agents with runtime tools, use get_responses_client() instead.
        """
        if self._agent and self._agent.client:
            return cast("AzureAIClient[AzureAIProjectAgentOptions]", self._agent.client)
        # Build from the SHARED project_client, not project_endpoint+credential:
        # AzureAIClient derives its OpenAI client from project_client.get_openai_client(),
        # and the shared client (config.get_ai_project_client) injects the
        # image-generation deployment header on every call. Passing
        # project_endpoint+credential instead makes AzureAIClient create its OWN
        # headerless project_client — the cause of the 400 "imagegen deployment
        # must be provided through header" for any agent offering image generation.
        chat_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=self.agent_name,
            model_deployment_name=self.model_deployment_name,
            use_latest_version=True,
        )
        self.logger.info(
            "Created new AzureAIClient (agent_name=%s, use_latest_version=True)",
            self.agent_name,
        )
        return chat_client

    def get_responses_client(self) -> AzureOpenAIResponsesClient:
        """Return AzureOpenAIResponsesClient for agents WITH runtime tools.

        This client supports dynamic tools (MCP, functions) passed at runtime
        via Agent(tools=[...]).  Uses the Foundry project_endpoint so the
        execution goes through the same Azure AI project.

        Agents using this client are NOT automatically persisted in Foundry.
        Call _register_in_foundry() separately to make them visible in the
        Azure AI Foundry portal and extension.
        """
        responses_client = AzureOpenAIResponsesClient(
            project_endpoint=self.project_endpoint,
            deployment_name=self.model_deployment_name,
            credential=self.creds,
        )
        self.logger.info(
            "Created AzureOpenAIResponsesClient (deployment=%s, project_endpoint=%s)",
            self.model_deployment_name,
            self.project_endpoint,
        )
        return responses_client

    async def _register_in_foundry(self) -> None:
        """Persist agent definition in Azure AI Foundry via create_version.

        Assembles the tool list from the agent’s own config so the published
        definition carries exactly the tools the factory declared:

          * ``enable_code_interpreter`` → ``CodeInterpreterTool()``
          * ``mcp_cfg`` (has url + name)  → ``MCPTool(server_label, server_url)``
          * ``use_bing`` + ``AZURE_BING_CONNECTION_NAME`` → ``BingGroundingTool``
          * ``enable_file_search`` + ``AZURE_FILE_SEARCH_VECTOR_STORE_IDS``
            → ``FileSearchTool``
          * ``enable_web_search`` → ``WebSearchTool()``
          * ``enable_image_generation`` → ``ImageGenTool()``
          * ``enable_azure_functions`` → no-op (requires a full
            ``AzureFunctionDefinition``; logs a warning and skips)
          * ``enable_sharepoint`` + ``AZURE_SHAREPOINT_CONNECTION_NAME``
            → ``SharepointPreviewTool``
          * ``enable_browser_automation`` +
            ``AZURE_BROWSER_AUTOMATION_CONNECTION_NAME``
            → ``BrowserAutomationPreviewTool``
          * ``enable_fabric`` + ``AZURE_FABRIC_CONNECTION_NAME``
            → ``MicrosoftFabricPreviewTool``
          * ``enable_bing_custom_search`` +
            ``AZURE_BING_CUSTOM_SEARCH_CONNECTION_NAME`` /
            ``AZURE_BING_CUSTOM_SEARCH_INSTANCE_NAME``
            → ``BingCustomSearchTool``

        Azure AI Search already has its own create path
        (``_create_azure_search_enabled_client``); it is not duplicated here.

        Behavior:
          - Default: if the agent already exists in Foundry, reuse it (skip
            publish). Prevents version bloat on every backend restart.
          - ``MACAE_FORCE_AGENT_PUBLISH=1``: always publish a new version.
            Use after editing ``data/agent_teams/*.json`` system_messages.
            Unset after one successful run.
        """
        if not self.project_client or not self.agent_name:
            return

        force_republish = os.getenv("MACAE_FORCE_AGENT_PUBLISH", "").lower() in (
            "1",
            "true",
            "yes",
        )

        # ── Desired definition (tools + fingerprint) ────────────────────────
        # Assembled BEFORE any reuse decision: composed agents share names
        # across requests while the Router varies instructions/tools per
        # request, so "already exists" alone can never justify reuse.
        tools_to_publish: list[Tool] = []
        if getattr(self, "enable_code_interpreter", False):
            tools_to_publish.append(CodeInterpreterTool())
        _mcp = getattr(self, "mcp_cfg", None)
        if _mcp and getattr(_mcp, "url", ""):
            tools_to_publish.append(
                MCPTool(
                    server_label=getattr(_mcp, "name", "mcp") or "mcp",
                    # The published tool executes in FOUNDRY's runtime, not on
                    # this host: it must carry the publicly reachable endpoint
                    # (dev localhost is unreachable from Azure — same rule as
                    # the chat lane's direct attach). Client-side runtime MCP
                    # keeps using the local URL.
                    server_url=config.MACAE_MCP_PUBLIC_ENDPOINT or _mcp.url,
                    # No allowed_tools filter: these are exact-name lists (a
                    # literal "*" matches nothing); omitting the field allows
                    # every tool the server exposes. Magentic runs have no
                    # human channel for per-call tool approvals — anything but
                    # "never" hangs the run.
                    require_approval="never",
                )
            )
        if getattr(self, "enable_bing", False):
            _bing_conn = getattr(config, "AZURE_BING_CONNECTION_NAME", "") or ""
            if _bing_conn:
                tools_to_publish.append(
                    BingGroundingTool(
                        bing_grounding=BingGroundingSearchToolParameters(
                            search_configurations=[
                                BingGroundingSearchConfiguration(
                                    project_connection_id=_bing_conn
                                )
                            ]
                        )
                    )
                )
            else:
                self.logger.warning(
                    "Agent '%s' requested Bing grounding but "
                    "AZURE_BING_CONNECTION_NAME is not configured — "
                    "publishing without web search.",
                    self.agent_name,
                )

        if getattr(self, "enable_file_search", False):
            _vs_ids_raw = (
                getattr(config, "AZURE_FILE_SEARCH_VECTOR_STORE_IDS", "") or ""
            )
            _vs_ids = [v.strip() for v in _vs_ids_raw.split(",") if v.strip()]
            if _vs_ids:
                tools_to_publish.append(FileSearchTool(vector_store_ids=_vs_ids))
            else:
                self.logger.warning(
                    "Agent '%s' requested FileSearch but "
                    "AZURE_FILE_SEARCH_VECTOR_STORE_IDS is not configured — "
                    "publishing without file search.",
                    self.agent_name,
                )
        if getattr(self, "enable_web_search", False):
            tools_to_publish.append(WebSearchTool())
        if getattr(self, "enable_image_generation", False):
            tools_to_publish.append(ImageGenTool())
        if getattr(self, "enable_azure_functions", False):
            self.logger.warning(
                "Agent '%s' requested AzureFunctionTool but runtime "
                "construction requires a full AzureFunctionDefinition "
                "(function + bindings). Set 'use_azure_functions' in the "
                "agent definition JSON with the function spec — skipping.",
                self.agent_name,
            )
        if getattr(self, "enable_sharepoint", False):
            _sp_conn = getattr(config, "AZURE_SHAREPOINT_CONNECTION_NAME", "") or ""
            if _sp_conn:
                tools_to_publish.append(
                    SharepointPreviewTool(
                        sharepoint_grounding_preview=SharepointGroundingToolParameters(
                            project_connections=[
                                ToolProjectConnection(project_connection_id=_sp_conn)
                            ]
                        )
                    )
                )
            else:
                self.logger.warning(
                    "Agent '%s' requested SharePoint grounding but "
                    "AZURE_SHAREPOINT_CONNECTION_NAME is not configured — "
                    "publishing without SharePoint.",
                    self.agent_name,
                )
        if getattr(self, "enable_browser_automation", False):
            _ba_conn = (
                getattr(config, "AZURE_BROWSER_AUTOMATION_CONNECTION_NAME", "") or ""
            )
            if _ba_conn:
                tools_to_publish.append(
                    BrowserAutomationPreviewTool(
                        browser_automation_preview=BrowserAutomationToolParameters(
                            connection=BrowserAutomationToolConnectionParameters(
                                project_connection_id=_ba_conn
                            )
                        )
                    )
                )
            else:
                self.logger.warning(
                    "Agent '%s' requested BrowserAutomation but "
                    "AZURE_BROWSER_AUTOMATION_CONNECTION_NAME is not configured — "
                    "publishing without browser automation.",
                    self.agent_name,
                )
        if getattr(self, "enable_fabric", False):
            _fab_conn = getattr(config, "AZURE_FABRIC_CONNECTION_NAME", "") or ""
            if _fab_conn:
                tools_to_publish.append(
                    MicrosoftFabricPreviewTool(
                        fabric_dataagent_preview=FabricDataAgentToolParameters(
                            project_connections=[
                                ToolProjectConnection(project_connection_id=_fab_conn)
                            ]
                        )
                    )
                )
            else:
                self.logger.warning(
                    "Agent '%s' requested Microsoft Fabric but "
                    "AZURE_FABRIC_CONNECTION_NAME is not configured — "
                    "publishing without Fabric.",
                    self.agent_name,
                )
        if getattr(self, "enable_bing_custom_search", False):
            _bcs_conn = (
                getattr(config, "AZURE_BING_CUSTOM_SEARCH_CONNECTION_NAME", "") or ""
            )
            _bcs_instance = (
                getattr(config, "AZURE_BING_CUSTOM_SEARCH_INSTANCE_NAME", "") or ""
            )
            if _bcs_conn and _bcs_instance:
                tools_to_publish.append(
                    BingCustomSearchPreviewTool(
                        bing_custom_search_preview=BingCustomSearchToolParameters(
                            search_configurations=[
                                BingCustomSearchConfiguration(
                                    project_connection_id=_bcs_conn,
                                    instance_name=_bcs_instance,
                                )
                            ]
                        )
                    )
                )
            else:
                self.logger.warning(
                    "Agent '%s' requested BingCustomSearch but "
                    "AZURE_BING_CUSTOM_SEARCH_CONNECTION_NAME and/or "
                    "AZURE_BING_CUSTOM_SEARCH_INSTANCE_NAME are not configured — "
                    "publishing without Bing custom search.",
                    self.agent_name,
                )

        desired_fp = _definition_fingerprint(
            self.model_deployment_name or "",
            self.agent_instructions or "",
            tools_to_publish,
        )

        if (
            not force_republish
            and _FOUNDRY_PUBLISHED_FINGERPRINTS.get(self.agent_name) == desired_fp
        ):
            self.logger.info(
                "✅ Agent '%s' already published with this exact definition "
                "(process cache). NO new version.",
                self.agent_name,
            )
            return

        try:
            existing_agent = None
            if not force_republish:
                self.logger.info(
                    "🔍 Checking if agent '%s' already exists in Foundry to avoid creating new version...",
                    self.agent_name,
                )
                async for agent in self.project_client.agents.list():
                    if getattr(agent, "name", None) == self.agent_name:
                        existing_agent = agent
                        break

            if existing_agent is not None and not force_republish:
                _versions = getattr(existing_agent, "versions", None)
                _latest = (
                    getattr(_versions, "latest", None)
                    if _versions is not None
                    else None
                )
                _version_str = (
                    getattr(_latest, "version", "unknown")
                    if _latest is not None
                    else "unknown"
                )
                _version_id = (
                    getattr(_latest, "id", "unknown")
                    if _latest is not None
                    else "unknown"
                )

                # ── Publish-on-diff ─────────────────────────────────────────
                # Reuse ONLY when the published definition matches what THIS
                # composition needs; a changed definition publishes a new
                # version so the Router's current instructions/tools actually
                # apply (name-only reuse silently kept stale definitions).
                published_def = getattr(_latest, "definition", None)
                if published_def is None and _latest is not None:
                    try:
                        _ver = await self.project_client.agents.get_version(
                            self.agent_name, str(_version_str)
                        )
                        published_def = getattr(_ver, "definition", None)
                    except Exception as ver_exc:
                        self.logger.debug(
                            "Could not fetch version definition for '%s': %s",
                            self.agent_name,
                            ver_exc,
                        )
                if published_def is None:
                    # Unreadable published definition: reuse conservatively —
                    # publishing blind here would mint a version on every
                    # restart, the exact sprawl this path exists to prevent.
                    _FOUNDRY_REGISTERED_AGENT_NAMES.add(self.agent_name)
                    self.logger.warning(
                        "⚠️ Agent '%s' exists (version=%s) but its definition "
                        "could not be read for comparison — REUSING as-is.",
                        self.agent_name,
                        _version_str,
                    )
                    return

                published_fp = _definition_fingerprint(
                    str(getattr(published_def, "model", "") or ""),
                    str(getattr(published_def, "instructions", "") or ""),
                    getattr(published_def, "tools", None) or [],
                )
                if published_fp == desired_fp:
                    _FOUNDRY_REGISTERED_AGENT_NAMES.add(self.agent_name)
                    _FOUNDRY_PUBLISHED_FINGERPRINTS[self.agent_name] = desired_fp
                    self.logger.info(
                        "✅ Agent '%s' ALREADY EXISTS in Foundry with an IDENTICAL "
                        "definition (id=%s, latest_version=%s, version_id=%s). "
                        "REUSING - NO NEW VERSION CREATED.",
                        self.agent_name,
                        getattr(existing_agent, "id", "unknown"),
                        _version_str,
                        _version_id,
                    )
                    return
                self.logger.info(
                    "♻️ Agent '%s' exists (version=%s) but the definition CHANGED "
                    "(instructions/tools/model) — publishing a new version so this "
                    "composition's definition actually applies.",
                    self.agent_name,
                    _version_str,
                )

            tool_names = (
                ", ".join(
                    str(t.get("type", "?")) if hasattr(t, "get") else str(t)
                    for t in tools_to_publish
                )
                or "none"
            )
            self.logger.warning(
                "⚠️ Publishing agent '%s' (new name, changed definition, or "
                "force_republish). Creating NEW version (tools=%s)...",
                self.agent_name,
                tool_names,
            )
            agent_def = await self.project_client.agents.create_version(
                agent_name=self.agent_name,
                description=self.agent_description or "",
                definition=PromptAgentDefinition(
                    model=self.model_deployment_name or "",
                    instructions=self.agent_instructions or "",
                    tools=tools_to_publish or None,
                ),
            )
            self.logger.info(
                "🆕 CREATED NEW agent version '%s' in Foundry (id=%s, version=%s, tools=%s)",
                self.agent_name,
                agent_def.id,
                agent_def.version,
                tool_names,
            )
            _FOUNDRY_REGISTERED_AGENT_NAMES.add(self.agent_name)
            _FOUNDRY_PUBLISHED_FINGERPRINTS[self.agent_name] = desired_fp
        except Exception as exc:
            self.logger.warning(
                "Could not register agent '%s' in Foundry: %s",
                self.agent_name,
                exc,
            )

    def get_agent_id(self) -> str:
        """Generate a local agent ID for the ChatAgent wrapper.

        The new AzureAIClient identifies agents by name (not ID) on the server side.
        This ID is only used locally for the ChatAgent wrapper instance.
        """
        id = generate_assistant_id()
        self.logger.debug(
            "Generated local wrapper ID: %s (not a new Azure Foundry agent)", id
        )
        return id

    async def _prepare_mcp_tool(self) -> None:
        """Translate MCPConfig to a MCPStreamableHTTPTool and connect it.

        The tool is intentionally NOT entered into the AsyncExitStack.
        anyio cancel scopes (used internally by streamable_http_client) must be
        exited from the SAME task that entered them. Since close() can be called
        from a different task (e.g. force-rebuild in a background task), putting
        the MCP tool in the stack causes:
            RuntimeError: Attempted to exit cancel scope in a different task
        Instead we open/close the tool directly and swallow cross-task teardown
        errors — the HTTP DELETE /mcp is still sent (confirmed in logs), so the
        server-side session is cleaned up regardless.
        """
        if not self.mcp_cfg:
            return
        try:
            http_client = None
            if self.user_access_token:
                import httpx

                # Match the MCP SDK's own client timeouts (create_mcp_http_client):
                # 30s for regular ops, 300s read for the long-lived streamable-http
                # GET stream. A bare httpx.AsyncClient() defaults to read=5s, which
                # kills that GET stream on any idle >5s (approval pause / gaps
                # between agent turns) → "MCP connection closed unexpectedly.
                # Reconnecting" churn → cross-task cancel-scope teardown → the run
                # truncates. Passing our own client made us responsible for this.
                http_client = httpx.AsyncClient(
                    headers={
                        "Authorization": f"Bearer: x-ms-client-obo-token {self.user_access_token}"
                    },
                    verify=getattr(config, "HTTPS_VERIFY", True),
                    timeout=httpx.Timeout(30.0, read=300.0),
                )
                self.logger.info(
                    "Forwarding user OBO token to MCP server via Authorization header"
                )
                # http_client IS entered into the stack — it has no anyio cancel
                # scope and closes cleanly from any task.
                if self._stack:
                    await self._stack.enter_async_context(http_client)

            mcp_tool = ReconnectingMCPTool(
                name=self.mcp_cfg.name,
                description=self.mcp_cfg.description,
                url=self.mcp_cfg.url,
                http_client=http_client,
                # Lectura sin aprobación; el resto pide aprobación humana según
                # lo que el servidor declara (readOnlyHint).
                approval_from_annotations=True,
            )
            # Open the tool directly (not via stack) to avoid cross-task
            # cancel-scope violations on close.
            await mcp_tool.__aenter__()
            self.mcp_tool = mcp_tool
        except Exception as exc:
            self.logger.warning("MCP tool setup failed: %s", exc)
            self.mcp_tool = None


class AzureAgentBase(MCPEnabledBase):
    """
    Extends MCPEnabledBase with Azure credential + AzureAIClient contexts.
    Subclasses:
      - create or attach an Azure AI Agent definition
      - instantiate an AzureAIClient and assign to self._agent
      - optionally register themselves via agent_registry
    """

    def __init__(
        self,
        mcp: MCPConfig | None = None,
        model_deployment_name: str | None = None,
        project_endpoint: str | None = None,
        team_service: TeamService | None = None,
        team_config: TeamConfiguration | None = None,
        memory_store: DatabaseBase | None = None,
        agent_name: str | None = None,
        agent_description: str | None = None,
        agent_instructions: str | None = None,
        project_client=None,
        user_access_token: str | None = None,
    ) -> None:
        super().__init__(
            mcp=mcp,
            team_service=team_service,
            team_config=team_config,
            project_endpoint=project_endpoint,
            memory_store=memory_store,
            agent_name=agent_name,
            agent_description=agent_description,
            agent_instructions=agent_instructions,
            model_deployment_name=model_deployment_name,
            project_client=project_client,
            user_access_token=user_access_token,
        )

        self._created_ephemeral: bool = (
            False  # reserved if you add ephemeral agent cleanup
        )

    # async def open(self) -> "AzureAgentBase":
    #     if self._stack is not None:
    #         return self
    #     self._stack = AsyncExitStack()

    #     # Acquire credential
    #     self.creds = DefaultAzureCredential()
    #     if self._stack:
    #         await self._stack.enter_async_context(self.creds)
    #     # Create AgentsClient
    #     self.client = AgentsClient(
    #         endpoint=self.project_endpoint,
    #         credential=self.creds,
    #     )
    #     if self._stack:
    #         await self._stack.enter_async_context(self.client)
    #     # Prepare MCP
    #     await self._prepare_mcp_tool()

    #     # Let subclass build agent client
    #     await self._after_open()

    #     # Register agent (best effort)
    #     try:
    #         agent_registry.register_agent(self)
    #     except Exception:
    #         pass

    #     return self

    async def close(self) -> None:
        """
        Close agent client and Azure resources.
        If you implement ephemeral agent creation in subclasses, you can
        optionally delete the agent definition here.
        """
        try:
            # Close underlying client via base close
            _agent_close = getattr(self._agent, "close", None) if self._agent else None
            if callable(_agent_close):
                try:
                    result = _agent_close()
                    if inspect.isawaitable(result):
                        await result
                except Exception as exc:
                    logging.warning(
                        "Failed to close underlying agent %r: %s",
                        self._agent,
                        exc,
                        exc_info=True,
                    )

            # Unregister from registry
            try:
                agent_registry.unregister_agent(self)
            except Exception as exc:
                logging.warning(
                    "Failed to unregister agent %r from registry: %s",
                    self,
                    exc,
                    exc_info=True,
                )

            # Close the per-agent AgentsClient only. The credential is NOT
            # closed here: without a user token self.creds is the process-shared
            # Managed Identity credential (borrowed from config), and closing it
            # kills token minting for the whole process — blob store, Foundry
            # file uploads and download-file all fail with "HTTP transport has
            # already been closed" once their cached tokens expire. The guarded
            # close in super().close() handles the per-user (owned) credential.
            if self.client:
                try:
                    await self.client.close()
                except Exception as exc:
                    logging.warning(
                        "Failed to close Azure AgentsClient %r: %s",
                        self.client,
                        exc,
                        exc_info=True,
                    )

        finally:
            await super().close()
            self.client = None
            self.project_endpoint = None
