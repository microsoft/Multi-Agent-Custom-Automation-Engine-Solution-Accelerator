# ADR-001: Retain Custom JSON Declarative Configuration Over MAF Declarative Package

## Status

Accepted

## Date

2026-04-23

## Context

This solution accelerator uses a custom JSON-based declarative configuration system (`data/agent_teams/*.json`) to define agent teams, individual agents, their capabilities, and orchestration parameters. Each JSON file specifies team metadata, agent names, deployment models, system messages, tool flags (`use_rag`, `use_mcp`, `use_bing`, `use_reasoning`, `coding_tools`), and RAG index references.

The Microsoft Agent Framework (MAF) introduced an `agent-framework-declarative` package that provides YAML-based declarative definitions for both agents and workflows. It offers `AgentFactory` and `WorkflowFactory` classes that can create agents and multi-step workflows from YAML files, including control flow (conditionals, loops), agent invocations, and human-in-the-loop patterns.

We evaluated whether to migrate from our custom JSON configuration to the MAF declarative package.

## Decision

We will **retain and continue evolving our custom JSON declarative configuration** rather than adopting the MAF `agent-framework-declarative` package.

## Rationale

### 1. Package Maturity and Stability Concerns

The `agent-framework-declarative` package is in preview (`pip install agent-framework-declarative --pre`). Its API surface, YAML schema, and supported action types are still evolving. Adopting a preview package as the foundation for configuration in a solution accelerator creates risk of breaking changes requiring rework.

### 2. Granularity Mismatch

Our JSON configuration captures **agent-level detail** that the MAF declarative schema does not directly model:

- Per-agent capability flags (`use_rag`, `use_mcp`, `use_bing`, `use_reasoning`, `coding_tools`)
- RAG index references (`index_name`, `index_foundry_name`, `index_endpoint`)
- MCP server bindings
- Team-level metadata (visibility, deployment defaults, team grouping)

The MAF declarative package focuses on workflow orchestration patterns (sequential, conditional, loop) and agent invocation, not on the detailed agent capability configuration our solution requires.

### 3. Orchestration Pattern Alignment

Our orchestration uses the Magentic pattern (`MagenticBuilder`) with custom plan approval (`HumanApprovalMagenticManager`). The MAF declarative package's YAML workflows define sequential/conditional/loop patterns but do not expose Magentic-specific features (dynamic LLM-driven planning, progress ledgers, stall detection, plan review). Adopting declarative YAML for workflow definition would still require code-level orchestration for Magentic, creating a split configuration model.

### 4. Solution Accelerator Goals

As a solution accelerator, this codebase is designed to be forked and customized. A self-contained JSON configuration with clear, domain-specific fields is easier for adopters to understand and modify than an external YAML schema with its own learning curve and version dependencies.

## Alternatives Considered

### Adopt MAF `agent-framework-declarative` for Everything

- **Pros:** Alignment with the SDK ecosystem; reduced custom code for workflow definition; potential future SDK improvements.
- **Cons:** Preview stability risk; granularity gap requiring hybrid config; Magentic features not available in YAML; additional dependency.

### Hybrid Approach (JSON for Agents, YAML for Workflows)

- **Pros:** Could leverage declarative workflows for simple sequential patterns.
- **Cons:** Two configuration formats to maintain; split mental model for contributors; Magentic orchestration still requires code.

### Convert JSON to YAML (Same Schema, Different Format)

- **Pros:** YAML is more readable for complex nested structures.
- **Cons:** No functional benefit; migration cost with no value; JSON is already well-understood by adopters.

## Consequences

- **Positive:** Full control over configuration schema evolution. No dependency on preview package stability. Single configuration format for adopters. Customization remains straightforward.
- **Negative:** We maintain custom loading and validation code. If the MAF declarative package matures and becomes the standard, migration effort increases the longer we wait.
- **Mitigation:** We will monitor the MAF declarative package's progression toward GA. If it stabilizes and adds support for the granularity we need, we will revisit this decision.

## References

- [MAF Declarative Package (Python)](https://github.com/microsoft/agent-framework/tree/main/python/packages/declarative)
- [MAF Declarative Workflow Samples](https://github.com/microsoft/agent-framework/tree/main/python/samples/03-workflows/declarative)
- [MAF Orchestrations Package (MagenticBuilder)](https://github.com/microsoft/agent-framework/tree/main/python/packages/orchestrations)
- Current JSON team configs: `data/agent_teams/*.json`
