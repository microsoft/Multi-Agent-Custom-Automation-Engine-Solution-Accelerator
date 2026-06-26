<!-- markdownlint-disable-file -->
# Task Research: MACAE WAF Private-Networking Mechanism — "VNet Integration" Accuracy

Investigate whether the Multi-Agent Custom Automation Engine (MACAE) WAF
(production) configuration delivers private networking specifically via
"VNet integration," or via a different mechanism (private endpoints, VNet
injection / subnet delegation, VM jumpbox). Goal: confirm or refute the
Rise course wording under accuracy review before Gold sign-off.

## Task Implementation Requests

* Explain the reviewer's question in one paragraph.
* Determine the ACTUAL private-networking mechanism(s) used by the WAF
  production configuration from the infra-as-code (bicep) ground truth.
* Determine whether "via VNet integration" is technically accurate,
  partially accurate, or incorrect for MACAE.
* Recommend source-accurate wording for the course answer.

## Scope and Success Criteria

* Scope: `infra/` bicep + parameters (WAF path), README + docs FAQ /
  architecture sections, AVM/bicep networking modules. Excludes runtime
  behavior testing.
* Assumptions: The course "source KB" maps to repo README + docs.
* Success Criteria:
  * Identify exact Azure networking constructs the WAF config deploys
    (VNet, subnets, private endpoints, private DNS zones, App Service /
    Functions VNet integration, Container Apps VNet, jumpbox VM).
  * State whether "VNet integration" is the correct term.
  * Provide recommended corrected wording with evidence citations.

## Reviewer Question Summary

A course-accuracy reviewer is auditing the Rise course "Multi-Agent Custom
Automation Engine - Technical Implementation," Lesson 7 (Positioning in the
deal cycle), Stage 2 ("Inspire and design"). Under "Common technical
questions at this stage," the course answers "Does this support private
networking?" with "Yes, the WAF production configuration supports private
networking **via VNet integration**." The reviewer flags that the phrase
"via VNet integration" does not appear in the source KB — the source
attributes private networking to the WAF (production) configuration
(`main.waf.parameters.json` with `EncryptionAtHost` registered) and to a
VM jumpbox, never to "VNet integration." The reviewer asks whether the WAF
production configuration delivers private networking specifically via VNet
integration (keep + feed back to source if yes; correct the wording if no
or different, e.g. private endpoints / jumpbox-only).

## Verdict

"Via VNet integration" is **imprecise / partially incorrect** as a
standalone description. It is a minor but legitimate accuracy issue.

* VNet integration IS present, but it applies ONLY to the frontend App
  Service web app — not to the solution as a whole.
* The WAF config delivers private networking through a COMBINATION of
  four distinct mechanisms (see below). Singling out "VNet integration"
  mischaracterizes one sub-mechanism as the whole and omits the most
  security-relevant pieces (private endpoints, VNet injection, jumpbox).
* The source's own umbrella term is "private networking" (the bicep
  parameter is literally `enablePrivateNetworking`). That is the
  source-accurate phrasing.

## Infra Ground Truth (WAF = `avm-waf` flavor)

WAF path is `deploymentFlavor: avm-waf` (infra/main.waf.parameters.json:5-7),
which sets `enablePrivateNetworking = true` (infra/main.bicep:226-227;
infra/main.waf.parameters.json:73) and routes to infra/avm/main.bicep:258.
The vanilla `bicep` flavor "intentionally excludes ... private networking,
scale-out, redundancy, bastion, and VM resources" (infra/bicep/main.bicep:4).

The WAF config combines four distinct private-networking mechanisms; the
IaC keeps them separate:

| Mechanism | Applies to | Evidence |
|-----------|-----------|----------|
| App Service **regional VNet integration** (delegated `Microsoft.Web/serverfarms` subnet, `vnetRouteAllEnabled` false) | Frontend web app ONLY | infra/avm/main.bicep:1371; infra/avm/modules/compute/app-service.bicep:137,72-74,128 |
| **VNet injection** (internal Container Apps Environment in a delegated `Microsoft.App/environments` subnet, `internal: true`) | Backend API + MCP server (Container Apps) | infra/avm/main.bicep:1066,1236; infra/avm/modules/compute/container-app-environment.bicep:62-64 |
| **Private endpoints** + privatelink Private DNS zones | Storage (blob) + Cosmos DB (Sql) ONLY | infra/avm/main.bicep:965-968,1001-1004; infra/avm/modules/data/storage-account.bicep:111-119; infra/avm/modules/data/cosmos-db-nosql.bicep:94-102 |
| **Windows jumpbox VM + Azure Bastion** (gated `if (enablePrivateNetworking)`) | Private admin access | infra/avm/main.bicep:672-683,723-749 |

Intentionally LEFT PUBLIC in the WAF config:

* AI Foundry / AI Services — private endpoint deliberately commented out
  ("MCP KnowledgeBase Connections doesn't work [with] private endpoints",
  infra/avm/main.bicep:803-849).
* AI Search — `privateEndpoints: []` (infra/avm/main.bicep:913).
* ACR and Key Vault — not deployed at all (no PE possible).

Compute platform: Backend API (port 8000) and MCP server run on **Azure
Container Apps** (VNet-injected); the **frontend** runs on **Azure App
Service** (Linux Docker Web App). There are **no Azure Functions** anywhere.

## Source KB Claims (README / docs)

The reviewer's two quoted strings do NOT exist verbatim in the repo:

* README.md has no FAQ section; the "Solution architecture" block is an
  image only (README.md:28). Zero matches for `Does MACAE support`,
  `support private networking`, `to support private networking`, or
  `Deployed only for`.
* Closest real text: README.md:85 steers users to "the WAF-supported
  version to ensure compliance" (a Note, not a FAQ).
* docs/DeploymentGuide.md:188 — "Copy `main.waf.parameters.json` to
  `main.parameters.json`"; docs/DeploymentGuide.md:197 — "Enable the
  Microsoft.Compute/EncryptionAtHost feature ... required for
  WAF-aligned (production) deployments."
* "jumpbox" term: docs/TroubleShootingSteps.md:64; comment at
  infra/avm/modules/compute/virtual-machine.bicep:2 ("Module: Virtual
  Machine (Jumpbox)"); "VMs not deployed in default Development/Testing
  configuration" in docs/DeploymentGuide.md §3.2.

Where "VNet integration" actually appears (NEVER in README/docs — only in
bicep parameter descriptions and compiled AVM output):

* infra/avm/modules/compute/container-app-environment.bicep:21
* infra/avm/modules/compute/app-service.bicep:66
* infra/avm/main.json (lines 45996, 56108; "Regional VNET Integration" at
  55255, 56531, 61198, 66659 — compiled AVM output)

`virtual network integration` = zero matches anywhere.

Implication: the reviewer appears to be auditing draft/proposed FAQ +
architecture text that is not actually in the repo source. Either way,
"via VNet integration" is not the source's umbrella term — "private
networking" is.

## Draft-Wording Origin

The reviewer's exact FAQ/architecture strings exist nowhere in shipped
repo source. The phrases "Does this support private networking", "Common
technical questions", "Inspire and design", and "Positioning in the deal
cycle" appear ONLY inside the `.copilot-tracking` research note that
quotes the course — not in any repo KB. README/docs have no FAQ section.

The literal phrase "VNet integration" exists only in:

* bicep parameter `@description`s — infra/avm/modules/compute/container-app-environment.bicep:21;
  infra/avm/modules/compute/app-service.bicep:66.
* compiled ARM JSON — infra/avm/main.json.

Most likely origin: the course author lifted "VNet integration" from the
bicep/AVM parameter descriptions (the only literal source), and/or
generalized from README.md:85 (WAF private-networking note) plus the
"Virtual Network" learn.microsoft.com link label (README.md:188). The
only other private-networking text is in gitignored dev runbooks under
data/sample_code/docs/ (00-overview-and-plan.md:30; 01-deployment-runbook.md:10),
both of which state private networking is "Disabled" and use neither
"VNet integration" nor FAQ phrasing. Conclusion: the reviewer is correct
that the phrase is not in the source KB.

## Adjacent Stage-2 Course Claims — Fidelity Check

While auditing the same Stage-2 panel, the other course answers were
corroborated against the repo (useful context for Gold sign-off):

| Course claim | Verdict | Evidence |
|--------------|---------|----------|
| "approval state is persisted to Cosmos DB for audit" | CONFIRMED (persistence); "for audit" is loose | plan_service.py:118 `handle_plan_approval` → `memory_store.update_plan`; cosmosdb.py:185-187 → `upsert_item` (124). "Audit" signal is telemetry (`track_event_if_configured("PlanApproved")`), not a dedicated audit container. |
| "customize agents through the Foundry Agent Service configuration and MCP tool bindings" | PARTIALLY CONFIRMED | MCP bindings are real (mcp_config.py; agent_factory.py:146; agent_template.py:20-138 declarative `use_mcp`/`use_toolbox`/`use_knowledge_base`). But the server-side "Foundry Agent Service" path (`FoundryAgent`/`AzureAIAgentClient`) is deprecated (agent_factory.py:6); agents run on Microsoft Agent Framework via client-side `FoundryChatClient`. |
| "GPT-4.1 for planning/general reasoning, o4-mini for deeper reasoning; model config is an azd parameter" | CONFIRMED | ADR-003; infra/main.bicep:88 (`gpt4_1ModelName='gpt-4.1'`), :107 (`gptReasoningModelName='o4-mini'`); infra/main.parameters.json:32 ← `AZURE_ENV_MODEL_4_1_NAME`, :45 ← `AZURE_ENV_REASONING_MODEL_NAME`. |

## Network Isolation Posture (WAF)

Subnets in the WAF VNet (`10.0.0.0/8`, infra/avm/main.bicep:373-548):

| Subnet | Prefix | Delegation | Hosts |
|--------|--------|------------|-------|
| `backend` | `10.0.0.0/27` | none | Storage + Cosmos private endpoints |
| `containers` | `10.0.2.0/23` | `Microsoft.App/environments` | internal Container Apps env (backend + MCP) |
| `webserverfarm` | `10.0.4.0/27` | `Microsoft.Web/serverfarms` | frontend App Service VNet integration |
| `administration` | `10.0.0.32/27` | none | jumpbox VM NIC (no public IP) |
| `AzureBastionSubnet` | `10.0.0.64/26` | none | Azure Bastion (Standard SKU) |

Isolation facts:

* Every workload subnet carries a `deny-hop-outbound` NSG rule (Deny /
  Outbound / priority 200 / TCP 22+3389 / source `VirtualNetwork`),
  infra/avm/main.bicep:380-476 — an anti-pivot block: hosts (incl. the
  jumpbox) cannot initiate SSH/RDP outbound. Other ports and intra-VNet
  traffic still flow per platform defaults.
* Cosmos DB + Storage: `publicNetworkAccess` Disabled under WAF
  (infra/avm/main.bicep:952,994), private endpoints in `backend` subnet
  (973,1000), privatelink DNS zones (351-358).
* AI Foundry + AI Search: `publicNetworkAccess: 'Enabled'`
  (infra/avm/main.bicep:802,878) — intentionally public; Foundry PE
  commented out (805-846), Search `privateEndpoints: []` (913). AI Search
  compensates with `disableLocalAuth: true` (Entra-only).
* Jumpbox: Windows DSVM (`dsvm-win-2022`), `Standard_D2s_v5`, no public
  IP, Entra-ID join; reachable only via Bastion
  (infra/avm/modules/compute/virtual-machine.bicep:41-137).

Aside security note (factual, not part of the course question): a
hardcoded fallback local-admin password is present at
infra/avm/main.bicep:733 (`JumpboxAdminP@ssw0rd1234!`). It is unusable
for interactive login because the VM uses Entra-ID join, but it is a
literal credential default in tracked IaC — worth a separate hardening
follow-up independent of the course review.

## Recommended Corrected Wording

Source-accurate replacement for the Stage 2 answer:

> "Does this support private networking?" — "Yes. The WAF (production)
> configuration (`main.waf.parameters.json`, with the
> `Microsoft.Compute/EncryptionAtHost` feature registered) deploys the
> solution into a private virtual network. The frontend App Service uses
> regional VNet integration, the backend and MCP server run on an
> internal (VNet-injected) Container Apps environment, and data services
> (Cosmos DB and Storage) are reached over private endpoints with private
> DNS. A Bastion-fronted jumpbox VM provides private administrative
> access. The default Development/Testing configuration does not enable
> private networking or deploy the VM."

Minimal-change alternative (if a short answer is required): replace
"via VNet integration" with "by deploying into a private virtual network
(VNet integration for the frontend, VNet injection for the backend, and
private endpoints for data services), with a jumpbox for admin access."

## Potential Next Research

* RESOLVED — Draft-wording origin traced: phrase exists only in bicep
  param descriptions / compiled output; no FAQ in repo source. See
  Draft-Wording Origin section.
* RESOLVED — NSG `deny-hop-outbound` characterized (anti-pivot SSH/RDP
  egress block on all workload subnets). See Network Isolation Posture.
* OPEN — Decide whether to author a real repo FAQ entry using the
  accurate umbrella term "private networking" so future course content
  has a citable source.
  * Reasoning: the course's "source KB" has no FAQ; adding one closes the
    gap and prevents recurrence.
* OPEN — Separate hardening follow-up for the hardcoded jumpbox admin
  password fallback at infra/avm/main.bicep:733.
  * Reasoning: credential default in tracked IaC; unrelated to the course
    review but surfaced during it.

## Research Executed

### Subagent Research Documents

* .copilot-tracking/research/subagents/2026-06-25/waf-infra-networking-research.md
  * Infra/bicep ground truth — mechanisms, file+line evidence.
* .copilot-tracking/research/subagents/2026-06-25/source-kb-networking-claims-research.md
  * README/docs claims, verbatim-quote verification, term search.
* .copilot-tracking/research/subagents/2026-06-25/draft-wording-origin-research.md
  * Origin of "VNet integration" phrasing; adjacent Stage-2 claim fidelity.
* .copilot-tracking/research/subagents/2026-06-25/waf-network-isolation-posture-research.md
  * Subnet/NSG/private-endpoint/Bastion/jumpbox isolation detail.

### Project Conventions

* WAF/production gating via `deploymentFlavor: avm-waf` and
  `enablePrivateNetworking` parameter.
