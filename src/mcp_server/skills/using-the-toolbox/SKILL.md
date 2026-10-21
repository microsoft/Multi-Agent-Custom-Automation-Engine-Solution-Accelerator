---
name: using-the-toolbox
description: >-
  How to discover and use the external capabilities exposed through the Tool
  Box: web search, GitHub, image generation and other registered MCP servers.
  Read this before claiming a task cannot be done for lack of tools.
---

# Using the Tool Box

The Tool Box exposes capabilities from external MCP servers (web search,
GitHub, image generation, and any other registered connectors). You reach them
through the inspector tools, not as direct local functions.

## Workflow

1. **See what is connected.** Call `list_connected_servers` to list the
   reachable servers and `discover_mcp_capabilities` to see their tools and
   resources.
2. **Find a tool by intent.** Call `discover_mcp_capabilities(server_name)` and
   choose the right tool from the returned tool names, descriptions, and
   schemas (for example to "search the web" or "create an image"). If a
   connected upstream server advertises its own search tool, invoke it through
   `call_external_tool`, not as a local function.
3. **Invoke it.** Call the external tool with `call_external_tool`, passing the
   server, tool name, and arguments.
4. **Read published skills/resources.** If a server advertises a skills
   resource (`skill://index.json` or `skill://<name>/SKILL.md`), read it with
   `read_external_resource` to learn its intended usage before calling tools.

## Guidance

- Prefer `discover_mcp_capabilities` over guessing tool names.
- Check for a `skill://` resource first; it documents the server's own
  recommended strategy.
- If a capability (web search, GitHub, image generation) might exist, discover
  before concluding it is unavailable.
