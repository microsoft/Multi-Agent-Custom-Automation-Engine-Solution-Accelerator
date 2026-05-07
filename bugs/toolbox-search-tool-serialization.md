# Bug: AzureAISearchTool from toolbox not JSON-serializable in Responses API path

## Summary

When a Foundry toolbox contains an `AzureAISearchTool`, the tool object passes
through `_sanitize_foundry_response_tool` in `agent_framework_foundry` and is
shallow-copied via `dict(mapping)`. The nested `AzureAISearchToolResource` and
`AISearchIndexResource` SDK models survive as live objects rather than plain
dicts, causing `json.dumps` to fail when the OpenAI client serializes the
request body.

## Versions

```text
agent-framework==1.2.2
agent-framework-openai==1.2.2
agent-framework-foundry==1.2.2
azure-ai-projects==2.1.0
```

## Repro (minimal)

```python
import json
from azure.ai.projects.models import (
    AzureAISearchTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
)

tool = AzureAISearchTool(
    azure_ai_search=AzureAISearchToolResource(
        indexes=[
            AISearchIndexResource(
                project_connection_id="my-connection",
                index_name="my-index",
            )
        ]
    )
)

# dict() shallow-copies — nested SDK models are NOT plain dicts
shallow = dict(tool)
json.dumps(shallow)  # TypeError: Object of type AzureAISearchToolResource is not JSON serializable

# as_dict() deep-converts — this works
json.dumps(tool.as_dict())  # OK
```

## Root cause

`_sanitize_foundry_response_tool` in
`agent_framework_foundry/_chat_client.py` converts hosted-tool `Mapping`
objects with `sanitized = dict(mapping)`. For `azure-ai-projects` SDK models
that implement `MutableMapping`, `dict()` performs a shallow copy — the
top-level keys become plain `str` keys, but the values remain live SDK model
instances (`AzureAISearchToolResource`, `AISearchIndexResource`). When the
resulting dict reaches `openai._utils._json.openapi_dumps`, those nested SDK
models are not JSON-serializable.

The same issue does **not** affect `MCPTool` or `CodeInterpreterTool` because
their values are plain strings/dicts, so `dict()` produces a fully
JSON-safe payload.

## Suggested fix

In `_sanitize_foundry_response_tool`, after the `sanitized = dict(mapping)`
line, call `.as_dict()` on any value that has it (all `azure-ai-projects` SDK
models do), or replace `dict(mapping)` with a deep-conversion helper:

```python
def _to_plain_dict(obj):
    """Deep-convert azure-ai-projects SDK model to plain dict."""
    if hasattr(obj, "as_dict"):
        return obj.as_dict()
    return dict(obj) if isinstance(obj, Mapping) else obj

# In _sanitize_foundry_response_tool:
sanitized = _to_plain_dict(tool_item)   # instead of dict(mapping)
```

## Traceback

```
TypeError: Object of type AzureAISearchToolResource is not JSON serializable

  File "agent_framework_openai/_chat_client.py", line 634, in _stream
    async for chunk in await client.responses.create(stream=True, **run_options):
  ...
  File "openai/_utils/_json.py", line 35, in default
    return super().default(o)
  File "json/encoder.py", line 180, in default
    raise TypeError(...)
```
