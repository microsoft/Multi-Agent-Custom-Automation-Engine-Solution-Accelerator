## Execute backend API Service

```shell
uv run uvicorn app:app --port 8000
```

## Public web research

Agents now receive `parallel_web_search` and `parallel_web_fetch` from
[Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp) when
web search is unconfigured. Anonymous search uses Fast mode and needs no Parallel
account or API key. The application's Azure model/project setup is still required.
Existing team configurations without web-search settings also receive these tools.

Search objectives, queries, and fetched URLs are sent to Parallel. Use public
information in these requests. To keep a deployment offline from this service,
set `WEB_SEARCH_PROVIDER=none` in the backend environment before starting it.
This operator restriction denies access for every agent, even one explicitly
configured with `web_search_provider: "parallel"`.

Team JSON supports these **per-agent** fields; they are retained on upload and
when a saved team is loaded:

| Field | Default when omitted | Behavior |
|-------|----------------------|----------|
| `web_search_provider` | `null` | Inherit `WEB_SEARCH_PROVIDER` (`parallel` by default). Use `"none"` to disable web access for this agent or `"parallel"` to select Parallel explicitly. |
| `web_search_tools` | `["web_search", "web_fetch"]` | Limit the tools exposed to this agent. Use `["web_search"]` for search only, `["web_fetch"]` for page fetching only, or `[]` to deny both. |

For example, an agent restricted to internal documents can include:

```json
"web_search_provider": "none"
```

These settings are independent of `use_toolbox`, its domain filter and Azure
credentials, Foundry IQ, and Code Interpreter. Web tools run through the same
client-side Agent Framework tool dispatcher as other MCP tools. They do not add
tools to the Foundry portal definition. Existing domain/knowledge-base choices
and credentials keep their own connections.
The `parallel_` prefix keeps model-facing function names distinct from domain
tools; the permission list uses the server's `web_search` and `web_fetch` names.

Optionally set `PARALLEL_API_KEY` to a dedicated Parallel key for higher limits.
Only this key is sent as a Bearer token to `https://search.parallel.ai/mcp`;
Azure credentials are never reused for web research. Without the key, the
connection is anonymous. Free access has service limits; it is not unlimited.
Connection or tool errors are reported through the existing agent error path,
without switching providers. MCP requests have a 60-second timeout (10 seconds
to connect), and agent cleanup closes the MCP session and its HTTP client.

With the backend dependencies installed, run the deterministic dispatcher tests
from the repository root:

```shell
PYTHONPATH=src/backend python -m pytest src/tests/agents/test_parallel_search.py -q
```

These tests use a scripted model, the real Agent Framework/MCP client, and HTTP
fixtures. They need no Azure, model, or Parallel credentials and make no external
requests. Run them separately from the backend unit suite, which replaces the
framework with module stubs.
