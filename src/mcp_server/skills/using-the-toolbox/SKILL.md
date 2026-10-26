---
name: using-the-toolbox
description: Discover and run external capabilities through the Foundry Toolbox (web search, GitHub, the Foundry MCP server, knowledge bases and other registered MCP servers). Read this before concluding that a capability is unavailable.
---

# Using the Tool Box

The Tool Box is one MCP endpoint that aggregates several upstream servers. You
reach it through MacaeMcpServer's inspector tools; never as local functions.
Identity travels with the session: do not invent a `user_id`, pass the one you
received or none.

## Workflow

1. **Connect once.** `connect_from_registry(server_name="tool-boxv")`. If it is
   already connected the call says so; that is not an error.
2. **Discover.** `discover_mcp_capabilities("tool-boxv")` returns the two
   meta-tools (`tool_search`, `call_tool`), any pinned tools, and the resource
   `skill://index.json`. Read `skill://<name>/SKILL.md` for any skill listed
   there with `read_external_resource` before calling tools.
3. **Search by intent, then call by exact name.**
   `call_external_tool("tool-boxv", "tool_search", {"query": "<capability>"})`
   returns matching tools when the index has entries. **An empty result is not
   proof that the capability is missing**: the index can be empty while the
   tools still run. In that case go straight to step 4 with the known names
   below.
4. **Run the tool.** Tool names have the shape `Source___tool` and are
   case-sensitive. Either form works:
   - `call_external_tool("tool-boxv", "call_tool", {"name": "<Source___tool>", "arguments": {...}})`
   - `call_external_tool("tool-boxv", "<Source___tool>", {...})`
   Arguments must match the tool's own schema; a validation error names the
   missing field (for example `web_search___search` requires `search_query`).
5. **Report only what the tool returned.** On an error (auth, consent,
   validation, not found) quote it and say what is missing. Do not simulate a
   result.

## Known members and verified calls

| Need | Tool | Arguments |
|---|---|---|
| Latest commits of a GitHub repo | `GitHub___list_commits` | `{"owner": "...", "repo": "...", "perPage": 1, "page": 1}` |
| Live public web information | `web_search___search` | `{"search_query": "..."}` |
| Agents of the Foundry project | `FoundryMCPServerpreview___agent_get` | `{"projectEndpoint": "<project endpoint>"}` |
| Knowledge base retrieval | `kb-knowledgebase550-lrm9b___knowledge_base_retrieve` | per schema |

Other members: `MicrosoftLearnMCPserver`, `arm`, `AzureDevOpsMCPServerpreview`,
`azure_ai_search`, `code_interpreter`, `WorkIQTeams1`, `MacaeMcpServer`.

## Rules

- **Read-only first.** Confirm access with a list/get/search call before any
  mutating one.
- **One failing upstream does not mean the Tool Box is down.** Try the other
  member that covers the need.
- **Do not reach the Foundry MCP server by a separate registry entry**; it is a
  member of the Tool Box and is called through it.
- **Do not loop on reads.** Read a skill or resource once per turn; if it does
  not answer the question, say so instead of reading it again.
