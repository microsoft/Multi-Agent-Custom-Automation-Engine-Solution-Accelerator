# Feature Changelog — feature/TAS27

High-level feature list for this release. Tracks new capabilities at the user/architecture level
(not individual commits).

## Feature Status Legend

| Status | Meaning |
|--------|---------|
| ✅ Done | Implemented and validated |
| 🔧 In Progress | Partially complete or needs finishing |
| 📋 Planned | Designed but not yet started |

---

## Features

### 1. Agent V2 Implementation (MAF 1.0 Stable)

**Status:** ✅ Done

Replaced `AzureAIAgentClient` / server-side agent pattern with MAF 1.0 stable:
- Get-or-create portal agents (`project_client.agents.get_agent`)
- `FoundryChatClient` for runtime (in-process state ownership)
- Single code path — `FoundryAgent` server-side pattern eliminated
- Portal edits (model, instructions) persist across restarts
- Flattened `v4/` directory structure

### 2. Foundry IQ Knowledge Base Integration

**Status:** ✅ Done

Migrated from `AzureAISearchTool` (server-side, serialization issues) to
`AzureAISearchContextProvider` (client-side, `mode="agentic"`):
- Per-agent knowledge bases (`macae-{domain}-kb` naming)
- Portal MCPTool sync — stale-KB detection and auto-update
- Retail, Contract Compliance, and RFP teams fully migrated
- Content Generation team defined (pending index creation in env)
- `seed_knowledge_bases.py` provisions KBs from index definitions

### 3. Toolboxes for MCP Assets

**Status:** ✅ Done

Per-agent Toolboxes created on first load (get-or-create pattern):
- Non-destructive — portal edits preserved across restarts
- MCP tools, Code Interpreter, and KB references stored as first-class Toolbox members
- `project_connection_id` for auth resolved server-side by Responses API

### 4. MCP Tool Filtering

**Status:** 📋 Planned

Filter MCP tools exposed to each agent based on team JSON configuration:
- Agents should only see tools relevant to their domain
- Reduces token overhead and prevents cross-domain tool hallucination
- Filtering criteria TBD (allowlist per agent, category tags, or regex patterns)

### 5. Prompt–Agent Sync

**Status:** ✅ Done

Agent system prompts defined in team JSON are synced to portal definitions:
- On agent load, compares local prompt vs portal `instructions`
- Updates portal if local definition has changed
- Portal remains editable for quick iteration (next restart re-syncs from JSON)

### 6. Magentic Orchestration (New)

**Status:** ✅ Done

Replaced custom orchestration with `MagenticBuilder` from agent-framework:
- `StatelessMagenticManager` — `session=None` prevents history confusion
- Progress ledger prompt with premature satisfaction guard
- Blocked-agent detection routes to ProxyAgent for human input
- Intermediate streaming outputs surfaced per-agent

### 7. Built-in Plan Approval

**Status:** ✅ Done

Native plan review via `MagenticBuilder(enable_plan_review=True)`:
- `MagenticPlanReviewRequest` events emitted to frontend via WebSocket
- Human approve/reject/edit flow with `wait_for_plan_approval()` gate
- Plan converted to structured `MPlan` for frontend display

### 8. Clarification Implementation (New)

**Status:** ✅ Done

ProxyAgent-based human-in-the-loop clarification:
- Agents report missing info → orchestrator routes to ProxyAgent
- ProxyAgent sends `UserClarificationRequest` via WebSocket
- Human responds → answer injected back into workflow
- Three-layer routing fix: StatelessMagenticManager + prompt guards + agent instructions

### 9. GitHub Copilot Customization Agent

**Status:** 📋 Planned

Custom `.agent.md` / instructions for using MACAE with GitHub Copilot:
- Agent definitions for common workflows (team creation, debugging, deployment)
- Skill files for domain-specific knowledge
- Integration with VS Code Copilot Chat for assisted development

---

## Deployment Lifecycle (Reference)

| Phase | What gets created |
|-------|-------------------|
| 1. Bicep deploy (`azd up`) | AI Search service, Storage, Cosmos, Foundry project, MCP server, index names defined |
| 2. Post-deploy script | Data uploaded, indexes created + populated, **KBs created** (pending integration), teams seeded to Cosmos |
| 3. Agent creation (runtime) | KBs linked as context providers, toolboxes created in Foundry |
