<!-- markdownlint-disable-file -->
# Subagent Research: Origin of Reviewer's Draft FAQ / "VNet integration" Wording + Stage-2 Course Claim Fidelity

Status: Complete
Date: 2026-06-25
Repo: c:\workstation\Microsoft\github\MACAE_ME

## Research Questions

1. Where is the ORIGIN of the reviewer's quoted draft FAQ / architecture wording
   (anchor phrases: "VNet integration", "private networking", "Does this support",
   "Common technical questions", "Inspire and design", "Positioning in the deal
   cycle", "jumpbox", "EncryptionAtHost", "WAF production")?
2. Does ANY repo source contain "VNet integration" OUTSIDE bicep param descriptions
   / compiled AVM output?
3. Where, if anywhere, does FAQ-style "Does this support private networking" content
   live in the repo?
4. Stage-2 adjacent course claims — CONFIRMED / PARTIALLY CONFIRMED / NOT FOUND:
   - "approval state is persisted to Cosmos DB for audit"
   - "agents customizable through the Foundry Agent Service configuration and MCP tool bindings"
   - "GPT-4.1 for planning/general reasoning, o4-mini for deeper reasoning; model configuration is an azd parameter"

## Executive Summary

- The reviewer's anchor phrases ("Does this support private networking", "Common
  technical questions", "Inspire and design", "Positioning in the deal cycle")
  appear in the repo ONLY inside prior `.copilot-tracking` research notes that
  QUOTE the course — never in any shipped source/doc/KB file. The course's "source
  KB" for that FAQ phrasing does not exist in this repo.
- "VNet integration" exists in the repo ONLY in (a) bicep module parameter
  @descriptions, (b) compiled ARM JSON (infra/avm/main.json), and (c)
  `.copilot-tracking` research notes. ZERO occurrences in docs/, src/,
  content_packs/, README.md, or any FAQ. Confirmed by scoped greps below.
- The repo's own umbrella term for the mechanism is "private networking"
  (param `enablePrivateNetworking`), NOT "VNet integration." The most plausible
  origin of the course author's "VNet integration" phrase is the bicep parameter
  descriptions / compiled AVM text (the only place the literal phrase lives), plus
  the README WAF note + the README "Virtual Network" learn.microsoft.com link.
- Stage-2 model claim is CONFIRMED with strong direct evidence (ADR-003 + bicep
  params + azd parameter mapping). Cosmos approval persistence is CONFIRMED
  (handle_plan_approval persists approved status via Cosmos update_plan); "for
  audit" framing is loose (audit-like telemetry events, not a Cosmos audit log).
  Foundry Agent Service + MCP claim is PARTIALLY CONFIRMED (MCP tool bindings are
  fully real; the literal server-side "Foundry Agent Service" path is deprecated —
  agents run on Microsoft Agent Framework via FoundryChatClient).

## 1. docs/ADR/ — All Three ADRs (networking mentions: NONE)

Read in full. No ADR mentions VNet, private networking, jumpbox, or any networking
topic. They cover config format, search, and model selection.

- docs/ADR/001-retain-custom-json-declarative-config.md — retains custom JSON team
  config. Lists per-agent flags including `use_mcp` and "MCP server bindings" and
  "RAG index references" (lines ~13, ~37-41). NO networking content. This is a
  relevant origin for the "MCP tool bindings" course claim (see §6b).
- docs/ADR/002-foundry-iq-file-search-over-azure-ai-search.md — replaces
  `AzureAISearchTool` with Foundry IQ `FileSearchTool` + managed vector stores.
  NO networking content.
- docs/ADR/003-reasoning-model-for-orchestrator-manager.md — DIRECT origin of the
  Stage-2 model claim. Uses `o4-mini` (default) for the MagenticManager and
  `gpt-4.1` for participant agents. Key lines:
  - line 1 / title: "Reasoning Model (o4-mini) for Orchestrator Manager".
  - Context: participants use team `deployment_name` "(typically `gpt-4.1`)";
    manager uses reasoning model. Config `ORCHESTRATOR_MODEL_NAME` (default
    `o4-mini`) in `common/config/app_config.py`.
  - "Participant agents continue using the team's `deployment_name` (e.g.,
    `gpt-4.1`)." and fallback-to-team-model behavior.
  NO VNet / private networking content in any ADR.

## 2. Root + docs Files (next-steps, feature-changelog, README, TRANSPARENCY, SUPPORT)

- README.md:85 — the ONLY doc-level "use WAF for private networking" steer; it is a
  Note, not a FAQ, and does not mention `main.waf.parameters.json`, EncryptionAtHost,
  or "VNet integration": "...consider deploying the WAF-supported version to ensure
  compliance. To configure, [Click here](./docs/DeploymentGuide.md#31-...)".
- README.md:188 — "Protecting the Azure Container Apps instance with a [firewall](...)
  and/or [Virtual Network](https://learn.microsoft.com/azure/container-apps/networking...)".
  This is the only README "Virtual Network" phrasing — an external link label, NOT
  "VNet integration", NOT a FAQ.
- next-steps.md, docs/feature-changelog.md, TRANSPARENCY_FAQS.md,
  docs/TRANSPARENCY_FAQ.md, SUPPORT.md — ZERO matches for VNet / private networking /
  jumpbox / EncryptionAtHost / WAF / "Does this support" / "Common technical".
- No FAQ section titled or containing "Does this support private networking?" exists
  in README.md or any docs/*.md (confirmed by anchor-phrase greps returning matches
  only inside `.copilot-tracking`).

## 3. content_packs/ (private networking / WAF / VNet / FAQ: NONE; MCP: YES)

- Scoped grep for `VNet|private networking|private endpoint|jumpbox|EncryptionAtHost|WAF`
  across content_packs/** → NO matches. No pack.json, README, agent_teams JSON, or
  dataset mentions private networking or VNet.
- content_packs DO heavily document MCP tool bindings (corroborates §6b), e.g.:
  - content_packs/example_pack/README.md:14, 37, 44, 47, 158, 233, 237 — Foundry IQ
    KB "(MCP endpoint)" / "exposes it as an MCP tool endpoint" / `use_knowledge_base`
    "Connects a Foundry IQ KB as an MCP search tool" / `use_toolbox` "Connects MCP
    toolbox tools".
  - content_packs/README.md:110, 220 — "Knowledge Base (MCP) ──► Agent";
    `use_knowledge_base` "Connects a Foundry IQ KB as an MCP search tool".
  - content_packs/content_gen/agent_teams/content_gen.json:87-88, 122 — agents call
    the MCP tool `generate_marketing_image`.

## 4. data/sample_code/ (FAQ-style "Does this support...": NONE; private networking: only "Disabled" runbook lines)

`data/sample_code/` is a gitignored sample/scratch tree (searched with ignored files
included). It contains internal dev runbooks, NOT a published FAQ KB.

- data/sample_code/docs/00-overview-and-plan.md:30 — locked-decisions table row:
  "| Private networking | Disabled, so public endpoints let the local services
  connect |". (Internal bug-fix working plan, ms.date 2026-06-11.)
- data/sample_code/docs/01-deployment-runbook.md:10 — "Private networking stays
  disabled so the local services can reach the resources later."
- data/sample_code/agent-framework-main/TRANSPARENCY_FAQ.md:1 — "Responsible AI
  Transparency FAQs" (vendored upstream agent-framework file; unrelated to
  networking; no "Does this support private networking").
- Zero matches in data/sample_code/** for "VNet integration", "Does this support",
  or "Common technical questions". The sample_code docs are NOT the course's FAQ
  source and do not use "VNet integration".

## 5. Whole-repo Anchor-phrase Grep Results (case-insensitive)

- "VNet integration" — matches ONLY in:
  - infra/avm/modules/compute/container-app-environment.bicep:21
    ("Subnet resource ID for VNet integration (required when enablePrivateNetworking is true).")
  - infra/avm/modules/compute/app-service.bicep:66 ("Subnet resource ID for VNet integration.")
  - infra/avm/main.json (compiled ARM; lines ~45996, ~56108, plus "Regional VNET
    Integration" vendored AVM text).
  - .copilot-tracking/research/**/*.md (prior research notes only).
  - SCOPED CONFIRMATION: grep "VNet integration" across {src/**, docs/**,
    content_packs/**, README.md, next-steps.md, SUPPORT.md, TRANSPARENCY_FAQS.md}
    → NO matches. grep across docs/** → NO matches.
- "private networking" — README.md:85 (WAF note); data/sample_code runbooks
  (Disabled); bicep param `enablePrivateNetworking`; many `.copilot-tracking` notes.
- "Does this support", "Common technical questions", "Inspire and design",
  "Positioning in the deal cycle" — matches ONLY in
  .copilot-tracking/research/2026-06-25/macae-waf-private-networking-research.md
  (lines ~36-38, ~131), which is a research note QUOTING the COURSE. These phrases
  do NOT exist in any shipped repo source.
- "jumpbox" / "EncryptionAtHost" / "WAF" — appear in infra bicep
  (enablePrivateNetworking VM/jumpbox path) and `.copilot-tracking` notes; NOT in a
  user-facing FAQ.

## 6. Stage-2 Adjacent Course Claims — Fidelity

### 6a. "approval state is persisted to Cosmos DB for audit" — CONFIRMED (persistence); "for audit" is loose framing

- src/backend/services/plan_service.py:118 — `PlanService.handle_plan_approval(...)`.
- plan_service.py (~lines 145-152) — on approval: `plan.overall_status =
  PlanStatus.approved`, `plan.m_plan = mplan.model_dump()`, then
  `await memory_store.update_plan(plan)`. On reject:
  `await memory_store.delete_plan_by_plan_id(...)`.
- memory_store is the Cosmos store: src/backend/common/database/cosmosdb.py:185-187
  `update_plan(plan)` → `update_item(plan)`; cosmosdb.py:114-124 `update_item` →
  `self.container.upsert_item(body=document)`.
- Cosmos config: src/backend/.env.sample:1-3 (COSMOSDB_ENDPOINT/DATABASE=macae/
  CONTAINER=memory); src/backend/app.py:89-90 (Cosmos logging suppression).
- API entry: src/backend/api/router.py:428-430 `POST /plan_approval`.
- "For audit": the explicit audit-like signal is telemetry, not a Cosmos audit log —
  plan_service.py emits `track_event_if_configured("PlanApproved", {...})` /
  `"PlanRejected"` (App Insights). The approval STATE itself IS persisted to Cosmos
  (approved status on the plan record). VERDICT: persistence to Cosmos = CONFIRMED;
  "for audit" = loosely supported (persisted record + telemetry events, no dedicated
  Cosmos audit container).

### 6b. "agents customizable through the Foundry Agent Service configuration and MCP tool bindings" — PARTIALLY CONFIRMED

- MCP tool bindings — CONFIRMED:
  - src/backend/config/mcp_config.py — `MCPConfig`/`VectorStoreConfig`/
    `KnowledgeBaseConfig`.
  - src/backend/agents/agent_factory.py:18, 146 — `MCPConfig.from_env(domain=...)`,
    passed to the agent template; line 6 notes `FoundryAgentTemplate (AzureAIAgentClient
    + ChatAgent, deprecated)`.
  - src/backend/agents/agent_template.py:20, 25, 33, 52, 66, 133-138 — `MCPTool`,
    `MCPStreamableHTTPTool`, `mcp_config`, KB MCP URL built into a Toolbox.
  - Declarative `use_mcp`/`use_toolbox`/`use_knowledge_base` flags in team JSON
    (ADR-001; content_packs README §3) bind MCP tools per agent.
  - src/backend/.env:28-33 — `MCP_SERVER_ENDPOINT`, `MCP_SERVER_NAME`,
    `MCP_SERVER_CONNECTION_ID`.
- "Foundry Agent Service configuration" — IMPRECISE: agents are configured via the
  custom JSON team configs + a client-side `FoundryChatClient` against an Azure AI
  Foundry project (ADR-003 implementation block). The literal server-side Foundry
  Agent Service path (`FoundryAgent` / `AzureAIAgentClient`) is explicitly
  DEPRECATED and "never used so Magentic / Handoff" work (agent_factory.py:6,
  agent_template.py:9). So "MCP tool bindings" is fully accurate; "Foundry Agent
  Service configuration" overstates — it is Microsoft Agent Framework + Foundry
  project model/connection config, not the server-side Agent Service.

### 6c. "GPT-4.1 for planning/general reasoning, o4-mini for deeper reasoning; model configuration is an azd parameter" — CONFIRMED

- Model names + roles (ADR-003, §1): participants/general use `gpt-4.1`; orchestrator
  deeper-reasoning uses `o4-mini` via `ORCHESTRATOR_MODEL_NAME` (default `o4-mini`).
- Bicep params (defaults):
  - infra/main.bicep:71 `param gptModelName = 'gpt-4.1-mini'`; :88
    `param gpt4_1ModelName = 'gpt-4.1'`; :107 `param gptReasoningModelName = 'o4-mini'`;
    :442 `output ORCHESTRATOR_MODEL_NAME = ... gptReasoningModelName ...`.
  - infra/avm/main.bicep:72/79/86 (same three params); :314/321/328
    deploymentName wiring; :1175 env var `ORCHESTRATOR_MODEL_NAME`; :1479
    `output ORCHESTRATOR_MODEL_NAME = gptReasoningModelName`; quota line :61
    `'OpenAI.GlobalStandard.o4-mini, 50'`.
  - infra/bicep/main.bicep:49/66/83 (same params); :619 env var `ORCHESTRATOR_MODEL_NAME`.
- azd parameter mapping (these ARE azd/bicep parameters driven by azd env vars):
  - infra/main.parameters.json:20 `gptModelName` ← `${AZURE_ENV_GPT_MODEL_NAME}`.
  - infra/main.parameters.json:32 `gpt4_1ModelName` ← `${AZURE_ENV_MODEL_4_1_NAME}`.
  - infra/main.parameters.json:45 `gptReasoningModelName` ← `${AZURE_ENV_REASONING_MODEL_NAME}`.
  - Plus matching deployment-type/version/capacity params, all azd-env-var driven.
- VERDICT: model names, role split (gpt-4.1 general vs o4-mini deeper reasoning),
  and "azd parameter" configurability are ALL confirmed in source.

## Most Likely Origin of the Course Author's "VNet integration"

The phrase "VNet integration" exists in the repo ONLY in bicep parameter
@descriptions (container-app-environment.bicep:21, app-service.bicep:66) and the
compiled ARM JSON (infra/avm/main.json), plus prior `.copilot-tracking` notes. The
repo's user-facing/umbrella term is "private networking" (`enablePrivateNetworking`).
The course author most plausibly:

1. Lifted "VNet integration" from the bicep/AVM parameter descriptions or compiled
   output (the only literal source of the phrase), and/or
2. Generalized from README.md:85 (WAF private-networking note) + README.md:188
   ("Virtual Network" learn.microsoft.com link),

then phrased it as a FAQ. There is NO shipped FAQ/KB in the repo containing "Does
this support private networking" or "Yes, the WAF production configuration supports
private networking via VNet integration" — so the reviewer is correct that the exact
phrase is not in the source KB. The technically accurate repo term is "private
networking", and the WAF mechanism is a MIX (VNet + subnets + Bastion + jumpbox VM +
private DNS + private endpoints for Cosmos/Storage), with "VNet integration"
strictly applying to the App Service / Container App Environment subnet wiring.

## Files Examined (plain-text paths)

- docs/ADR/001-retain-custom-json-declarative-config.md
- docs/ADR/002-foundry-iq-file-search-over-azure-ai-search.md
- docs/ADR/003-reasoning-model-for-orchestrator-manager.md
- README.md (lines 85, 188)
- data/sample_code/docs/00-overview-and-plan.md (line 30)
- data/sample_code/docs/01-deployment-runbook.md (line 10)
- data/sample_code/agent-framework-main/TRANSPARENCY_FAQ.md
- content_packs/example_pack/README.md, content_packs/README.md,
  content_packs/content_gen/agent_teams/content_gen.json
- infra/main.bicep, infra/avm/main.bicep, infra/bicep/main.bicep,
  infra/main.parameters.json
- infra/avm/modules/compute/container-app-environment.bicep (line 21),
  infra/avm/modules/compute/app-service.bicep (line 66)
- src/backend/services/plan_service.py (line 118+)
- src/backend/common/database/cosmosdb.py (lines 114-124, 181-187)
- src/backend/api/router.py (lines 315, 428-430)
- src/backend/agents/agent_factory.py (lines 6, 18, 146),
  src/backend/agents/agent_template.py (lines 9, 20-66, 133-138)
- src/backend/.env.sample, src/backend/.env (Cosmos + MCP env)

## Recommended Next Research (not done this session)

- [ ] Read docs/feature-changelog.md and next-steps.md in full (only grepped) to be
      100% sure no narrative FAQ paragraph was missed (greps returned zero on the
      anchor terms, so low risk).
- [ ] Confirm common/config/app_config.py exposes `ORCHESTRATOR_MODEL_NAME` /
      `gpt-4.1` deployment names exactly as ADR-003 states (ADR text asserts it;
      not re-read this session).
- [ ] If the course intends a "source KB" link, decide whether to ADD a real FAQ
      entry to README/docs using the accurate term "private networking" (and note
      VNet integration applies only to App Service / ACA subnet wiring).

## Clarifying Questions

- None blocking. (Open product question for the course owner, not answerable from
  the repo: did the course author intend an external/curated "source KB" outside
  this git repo? If so, that artifact — not this repo — is where the FAQ wording
  originated; this repo contains no such FAQ.)
