# ADR-002: Foundry IQ (FileSearchTool + Vector Stores) Over Azure AI Search

## Status

Accepted

## Date

2026-05-15

## Context

The solution accelerator uses Azure AI Search indexes to give agents access to domain-specific data (customer profiles, order data, contracts, RFP documents). This is implemented via `AzureAISearchTool` in a Toolbox, wired through `FoundryChatClient` and `Agent` (the Magentic-compatible path).

Nine search indexes exist across four agent teams:

| Team | Agent | Index |
|------|-------|-------|
| Retail | CustomerDataAgent | macae-retail-customer-index |
| Retail | OrderDataAgent | macae-retail-order-index |
| Content Gen | ResearchAgent | macae-content-gen-products-index |
| Contract Compliance | ContractSummaryAgent | contract-summary-doc-index |
| Contract Compliance | ContractRiskAgent | contract-risk-doc-index |
| Contract Compliance | ContractComplianceAgent | contract-compliance-doc-index |
| RFP | RfpSummaryAgent | macae-rfp-summary-index |
| RFP | RfpRiskAgent | macae-rfp-risk-index |
| RFP | RfpComplianceAgent | macae-rfp-compliance-index |

Azure AI Search requires:

- A separate Azure AI Search resource (with its own billing, connection, and API key)
- Index provisioning with a defined schema (fields, analyzers, etc.)
- `AZURE_AI_SEARCH_CONNECTION_NAME`, `AZURE_AI_SEARCH_ENDPOINT`, `AZURE_AI_SEARCH_API_KEY` configuration
- A Foundry project connection to the search resource

Foundry IQ (`FileSearchTool` + managed vector stores) offers a simpler alternative:

- Vector stores and file uploads are managed through the Foundry project client (no separate resource)
- `FileSearchTool` accepts `vector_store_ids` and performs semantic/vector search automatically
- No schema definition, index pipeline, or separate connection required
- Files are uploaded directly (CSV, JSON, Markdown, PDF, etc.) and chunked/embedded by the service

## Decision

We will **replace `AzureAISearchTool` with `FileSearchTool` (Foundry IQ)** for all agent team data access, starting with the retail scenario and rolling out to remaining teams.

## Validation

Before making this decision, we ran empirical validation tests (`localspec/validation-tests/`) that confirmed:

1. **Direct path works:** `FileSearchTool` → `FoundryChatClient` → `Agent` returns accurate answers from vector store data.
2. **Toolbox path works:** `FileSearchTool` → `Toolbox.create_version` → `chat_client.get_toolbox` → `Agent` round-trips correctly. The serialized form `{'vector_store_ids': [...], 'type': 'file_search'}` is preserved through the Toolbox.
3. **No architectural changes needed:** The existing Magentic orchestration, `FoundryChatClient` path, and Handoff pattern are fully compatible.

## Implementation

### Team JSON changes

Replace `use_rag` + `index_name` with `use_file_search` + `vector_store_name`:

```json
{
  "use_rag": false,
  "use_file_search": true,
  "vector_store_name": "macae-retail-customer-data"
}
```

### Code changes

- `mcp_config.py`: Add `VectorStoreConfig` dataclass with `vector_store_name` field
- `agent_factory.py`: Read `use_file_search` + `vector_store_name`, build `VectorStoreConfig`, pass to `AgentTemplate`
- `agent_template.py`: Resolve vector store name → ID at startup, use `FileSearchTool(vector_store_ids=[vs_id])` in `_build_tools()`

### Data provisioning

- New script `scripts/seed_vector_stores.py`: Creates vector stores from `data/datasets/` files, organized by team/agent
- Deterministic naming convention: `macae-{team}-{domain}-data` (e.g., `macae-retail-customer-data`)
- Script is idempotent: finds existing vector stores by name, skips re-creation

## Alternatives Considered

### Keep Azure AI Search, Add Vector Search Mode

- **Pros:** No migration; Azure AI Search supports vector and hybrid search
- **Cons:** Still requires separate resource provisioning, schema management, and connection setup. More operational overhead for a solution accelerator that ships sample data.

### Use Both (AzureAISearchTool for Some, FileSearchTool for Others)

- **Pros:** Incremental migration
- **Cons:** Two search paradigms to explain/maintain. Increases complexity for adopters who fork the accelerator.

### Use FileSearchTool with Server-Side FoundryAgent

- **Rejected:** `FoundryAgent` path blocks Magentic orchestration and Handoff (context ownership conflict). Our validation confirmed `FileSearchTool` works through the client-side `FoundryChatClient` path, so this is unnecessary.

## Consequences

- **Positive:** Eliminates Azure AI Search as a deployment dependency. Simplifies data ingestion (file upload vs. index pipeline). Reduces configuration surface (no search connection/endpoint/key). Vector search is automatic (no schema design needed).
- **Negative:** `FileSearchTool` chunking/embedding is a black box — less control over relevance tuning. Large-scale production workloads may still benefit from Azure AI Search's hybrid search, faceted filtering, and custom analyzers.
- **Mitigation:** `AzureAISearchTool` code path remains available (gated by `use_rag` flag) for teams that need advanced search features. The decision can be reversed per-agent.

## References

- [Foundry IQ Validation Tests](../../localspec/validation-tests/)
- [ADR-001: Retain Custom JSON Configuration](./001-retain-custom-json-declarative-config.md)
- [Azure AI Projects SDK 2.1.0](https://pypi.org/project/azure-ai-projects/)
- [Agent Framework Foundry 1.2.2](https://pypi.org/project/agent-framework-foundry/)
