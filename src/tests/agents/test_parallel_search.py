# Copyright (c) Microsoft. All rights reserved.
"""Real Agent Framework/MCP dispatch with a scripted model and HTTP fixtures.

Run separately from backend unit tests, whose module stubs replace the framework:
    PYTHONPATH=src/backend pytest src/tests/agents/test_parallel_search.py -q
No Azure, model, or Parallel credentials/network access are needed.
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from agent_framework import BaseChatClient, ChatResponseUpdate, Content
from agent_framework._tools import FunctionInvocationLayer


SEARCH_URL = "https://example.org/source"
TOOLS = [
    {
        "name": "web_search",
        "description": "Search the public web",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "search_queries": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["objective", "search_queries"],
        },
    },
    {
        "name": "web_fetch",
        "description": "Read a public URL",
        "inputSchema": {
            "type": "object",
            "properties": {"urls": {"type": "array", "items": {"type": "string"}}},
            "required": ["urls"],
        },
    },
    {"name": "unrelated_tool", "inputSchema": {"type": "object"}},
]


class ScriptedResearchClient(FunctionInvocationLayer, BaseChatClient):
    """Deterministic tool requests; proves dispatch, not model research quality."""

    def __init__(self, calls=None):
        super().__init__()
        self.calls = calls if calls is not None else [
            ("web_search", {"objective": "Find a source", "search_queries": ["public source information"]}),
            ("web_fetch", {"urls": [SEARCH_URL]}),
        ]
        self.round = 0
        self.consumed = []
        self.offered = []

    def _inner_get_response(self, *, messages, stream, options, **kwargs):
        assert stream

        async def updates():
            self.offered.append([t.name for t in options.get("tools", [])])
            results = [c for m in messages for c in m.contents if c.type == "function_result"]
            if results:
                self.consumed.append(str(results[-1].result))
            index = self.round
            self.round += 1
            if index < len(self.calls):
                name, arguments = self.calls[index]
                yield ChatResponseUpdate(
                    role="assistant", message_id=f"round-{index}",
                    contents=[Content.from_function_call(f"call-{index}", f"parallel_{name}", arguments=arguments)],
                )
            else:
                text = "Research complete: " + (self.consumed[-1] if self.consumed else "no web tools")
                yield ChatResponseUpdate(role="assistant", message_id="final", contents=[Content.from_text(text)])

        return self._build_response_stream(updates())


@pytest.fixture
def runtime(monkeypatch):
    """Import the real application with inert Azure settings and no search key."""
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda **kw: None)
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_AI_AGENT_ENDPOINT"):
        monkeypatch.setenv(key, "https://unused.example")
    for key in ("AZURE_AI_SUBSCRIPTION_ID", "AZURE_AI_RESOURCE_GROUP", "AZURE_AI_PROJECT_NAME"):
        monkeypatch.setenv(key, "unused")
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    monkeypatch.delenv("WEB_SEARCH_PROVIDER", raising=False)

    from agents import agent_factory, agent_template
    from common.config.app_config import AppConfig
    from common.models.messages import TeamAgent
    from config.web_search_config import WebSearchConfig
    from services.team_service import TeamService

    # Avoid loading a developer .env when checking the fresh environment default.
    settings = AppConfig()
    assert settings.WEB_SEARCH_PROVIDER == "parallel"
    assert not settings.PARALLEL_API_KEY
    settings.SUPPORTED_MODELS = '["test-model"]'
    settings.AZURE_AI_PROJECT_ENDPOINT = "https://unused.example/project"
    monkeypatch.setattr(agent_factory, "config", settings)

    credential = AsyncMock()
    credential.__aenter__.return_value = credential
    monkeypatch.setattr(agent_template, "AzureCliCredential", lambda: credential)
    monkeypatch.setattr(agent_template, "ManagedIdentityCredential", lambda **kw: credential)

    from azure.ai.projects.models import PromptAgentDefinition
    definition = PromptAgentDefinition(model="test-model", instructions="Research public information.")
    project = AsyncMock()
    project.__aenter__.return_value = project
    project.agents.get.return_value = SimpleNamespace(
        versions=SimpleNamespace(latest=SimpleNamespace(definition=definition))
    )
    monkeypatch.setattr(agent_template, "AIProjectClient", lambda **kw: project)

    requests = []
    clients = []
    started = asyncio.Event()
    failure = {"kind": None}

    async def respond(request):
        if request.method != "POST":
            return httpx.Response(405)
        body = json.loads(request.content)
        requests.append((request, body))
        method = body["method"]
        if "id" not in body:
            return httpx.Response(202)
        if method == "initialize":
            if failure["kind"] == "discovery_error":
                return httpx.Response(503)
            if failure["kind"] == "discovery_wait":
                started.set()
                await asyncio.Event().wait()
            result = {"protocolVersion": body["params"]["protocolVersion"], "capabilities": {"tools": {}},
                      "serverInfo": {"name": "fixture", "version": "1"}}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "ping":
            result = {}
        elif method == "tools/call":
            started.set()
            if failure["kind"] == "timeout":
                raise httpx.ReadTimeout("fixture read timeout", request=request)
            if failure["kind"] == "wait":
                await asyncio.Event().wait()
            if failure["kind"] == "error":
                result = {"isError": True, "content": [{"type": "text", "text": "Search unavailable"}]}
            else:
                text = (json.dumps({"results": [{"url": SEARCH_URL, "excerpts": ["Useful search excerpt"]}]})
                        if body["params"]["name"] == "web_search" else "Fetched source detail: " + SEARCH_URL)
                result = {"content": [{"type": "text", "text": text}]}
        else:
            pytest.fail(f"Unexpected MCP method: {method}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    def http_client(**kwargs):
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(agent_template, "AsyncClient", http_client)
    real_mcp_tool = agent_template.MCPStreamableHTTPTool

    def mcp_tool(**kwargs):
        # Keep production's bounded timeout assertion, but make fixture timeouts fast.
        assert kwargs["request_timeout"] == 60
        kwargs["request_timeout"] = 0.1
        return real_mcp_tool(**kwargs)

    monkeypatch.setattr(agent_template, "MCPStreamableHTTPTool", mcp_tool)

    async def make(overrides=None, calls=None):
        raw = {"input_key": "research", "type": "", "name": "ResearchAgent",
               "deployment_name": "test-model", "system_message": definition.instructions, **(overrides or {})}
        # Use the upload parser, then the same serialization used for saved teams.
        parsed = TeamService._validate_and_parse_agent(TeamService.__new__(TeamService), raw)
        saved = TeamAgent.model_validate_json(parsed.model_dump_json())
        model = ScriptedResearchClient(calls)
        monkeypatch.setattr(agent_template, "FoundryChatClient", lambda **kw: model)
        agent = await agent_factory.AgentFactory().create_agent_from_config("user", saved, None, None)
        return agent, model

    return SimpleNamespace(make=make, settings=settings, requests=requests, clients=clients,
                           failure=failure, started=started, config_cls=WebSearchConfig,
                           template_module=agent_template, project=project, credential=credential)


@pytest.mark.asyncio
async def test_default_dispatch_search_fetch_and_consume(runtime):
    from config.web_search_config import PARALLEL_SEARCH_URL, WEB_SEARCH_USER_AGENT

    agent, model = await runtime.make()
    try:
        updates = [u async for u in agent.invoke("Research a public source and read it.")]
        assert SEARCH_URL in "".join(u.text for u in updates)
        assert "Useful search excerpt" in model.consumed[0]
        assert "Fetched source detail" in model.consumed[1]
        assert set(model.offered[0]) == {"parallel_web_search", "parallel_web_fetch"}
        calls = [body for _, body in runtime.requests if body["method"] == "tools/call"]
        assert [b["params"]["name"] for b in calls] == ["web_search", "web_fetch"]
        assert calls[1]["params"]["arguments"]["urls"] == [SEARCH_URL]
        assert {b["method"] for _, b in runtime.requests} >= {"initialize", "tools/list", "tools/call"}
        for request, _ in runtime.requests:
            assert str(request.url) == PARALLEL_SEARCH_URL
            assert request.headers["User-Agent"] == WEB_SEARCH_USER_AGENT
            assert "Authorization" not in request.headers
    finally:
        await agent.close()
    assert all(c.is_closed for c in runtime.clients)
    assert agent._agent is None
    runtime.credential.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("overrides,global_provider", [
    ({"web_search_provider": "none"}, "parallel"),
    ({"web_search_tools": []}, "parallel"),
    ({"web_search_provider": "parallel"}, "none"),
])
@pytest.mark.asyncio
async def test_saved_disables_and_global_deny_make_no_requests(runtime, overrides, global_provider):
    runtime.settings.WEB_SEARCH_PROVIDER = global_provider
    agent, model = await runtime.make(overrides, calls=[])
    try:
        assert [u async for u in agent.invoke("Do an offline task.")]
        assert not runtime.requests
        assert not runtime.clients
        assert model.offered == [[]]
    finally:
        await agent.close()


@pytest.mark.asyncio
async def test_saved_selection_permissions_and_dedicated_credentials(runtime):
    runtime.settings.PARALLEL_API_KEY = "dedicated-test-key"
    runtime.settings.AZURE_CLIENT_SECRET = "never-forward-this"
    agent, model = await runtime.make({"web_search_provider": "parallel", "web_search_tools": ["web_search"]},
                                    calls=[("web_search", {"objective": "Source", "search_queries": ["public source information"]})])
    try:
        assert [u async for u in agent.invoke("Find a source.")]
        assert model.offered[0] == ["parallel_web_search"]
        for request, _ in runtime.requests:
            assert request.headers["Authorization"] == "Bearer dedicated-test-key"
            assert "never-forward-this" not in str(request.headers)
        assert "dedicated-test-key" not in repr(agent.web_search_config)
    finally:
        await agent.close()


@pytest.mark.asyncio
async def test_model_cannot_dispatch_disallowed_fetch(runtime):
    agent, model = await runtime.make({"web_search_tools": ["web_search"]},
                                    calls=[("web_fetch", {"urls": [SEARCH_URL]})])
    try:
        assert [u async for u in agent.invoke("Read a source.")]
        assert not [b for _, b in runtime.requests if b["method"] == "tools/call"]
        assert model.consumed
    finally:
        await agent.close()


@pytest.mark.parametrize("kind", ["error", "timeout"])
@pytest.mark.asyncio
async def test_errors_reach_model_without_provider_fallback(runtime, kind):
    runtime.failure["kind"] = kind
    agent, model = await runtime.make(calls=[("web_search", {"objective": "Source", "search_queries": ["public source information"]})])
    try:
        assert [u async for u in agent.invoke("Find a source.")]
        assert model.consumed
        calls = [b for _, b in runtime.requests if b["method"] == "tools/call"]
        assert len(calls) == 1
        assert "Useful search excerpt" not in model.consumed[0]
    finally:
        await agent.close()
    assert all(c.is_closed for c in runtime.clients)


@pytest.mark.asyncio
async def test_cancel_releases_transport(runtime):
    runtime.failure["kind"] = "wait"
    agent, model = await runtime.make()

    async def consume():
        return [u async for u in agent.invoke("Find a source.")]

    task = asyncio.create_task(consume())
    try:
        await asyncio.wait_for(runtime.started.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not model.consumed
    finally:
        await agent.close()
    assert all(c.is_closed for c in runtime.clients)


def test_unknown_provider_and_permission_do_not_fall_back(runtime):
    with pytest.raises(ValueError, match="web_search_provider"):
        runtime.config_cls.resolve("unconfigured-provider")
    with pytest.raises(ValueError, match="WEB_SEARCH_PROVIDER"):
        runtime.config_cls.resolve(default_provider="unconfigured-provider")
    with pytest.raises(ValueError, match="web_search_tools"):
        runtime.config_cls.resolve(allowed_tools=["unrelated_tool"])


@pytest.mark.asyncio
async def test_factory_preserves_domain_knowledge_and_other_tool_choices(runtime, monkeypatch):
    from agents import agent_factory
    from config import mcp_config

    settings = runtime.settings
    settings.MCP_SERVER_ENDPOINT = "https://domain.example/mcp"
    settings.MCP_SERVER_NAME = "domain-tools"
    settings.MCP_SERVER_DESCRIPTION = "Existing domain tools"
    settings.AZURE_TENANT_ID = "existing-tenant"
    settings.AZURE_CLIENT_ID = "existing-client"
    settings.MCP_SERVER_CONNECTION_ID = "existing-domain-connection"
    settings.AZURE_AI_SEARCH_ENDPOINT = "https://knowledge.example"
    settings.AZURE_AI_SEARCH_CONNECTION_NAME = "existing-knowledge-connection"
    monkeypatch.setattr(mcp_config, "config", settings)
    captured = {}

    def template(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(open=AsyncMock())

    monkeypatch.setattr(agent_factory, "AgentTemplate", template)
    await runtime.make({"use_toolbox": True, "toolbox_filter": "hr", "use_file_search": True,
                        "vector_store_name": "existing-files", "use_knowledge_base": True,
                        "knowledge_base_name": "existing-knowledge", "coding_tools": True,
                        "user_responses": True})
    assert captured["mcp_config"].url == "https://domain.example/hr/mcp"
    assert captured["mcp_config"].connection_id == "existing-domain-connection"
    assert captured["mcp_config"].allowed_tools == mcp_config.DOMAIN_ALLOWED_TOOLS["hr"]
    assert captured["kb_config"].search_connection_name == "existing-knowledge-connection"
    assert captured["vector_store_config"].vector_store_name == "existing-files"
    assert captured["enable_code_interpreter"] is True
    assert captured["extra_tools"]
    assert captured["web_search_config"] is not None
    assert captured["web_search_config"].get_headers().get("Authorization") is None


@pytest.mark.asyncio
async def test_failed_discovery_closes_clients_and_lifecycle_tasks(runtime):
    runtime.failure["kind"] = "discovery_error"
    with pytest.raises(ExceptionGroup) as error:
        await runtime.make()
    assert "503" in str(error.value.exceptions[0])
    assert all(c.is_closed for c in runtime.clients)
    assert not [t for t in asyncio.all_tasks() if t.get_name() == "mcp-lifecycle:parallel_search"]
    runtime.credential.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancelled_discovery_closes_clients_and_lifecycle_tasks(runtime):
    runtime.failure["kind"] = "discovery_wait"
    task = asyncio.create_task(runtime.make())
    await asyncio.wait_for(runtime.started.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert all(c.is_closed for c in runtime.clients)
    assert not [t for t in asyncio.all_tasks() if t.get_name() == "mcp-lifecycle:parallel_search"]
    runtime.credential.__aexit__.assert_awaited_once()
