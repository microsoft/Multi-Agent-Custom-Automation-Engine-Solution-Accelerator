<!-- markdownlint-disable-file -->
# Subagent Research: Source-KB Networking Claims (Private Networking / WAF / Jumpbox / "VNet integration")

Status: Complete

Workspace root: c:\workstation\Microsoft\github\MACAE_ME

## Research Questions

1. Where do the docs / "source KB" describe private networking, the WAF (production) configuration, and the VM jumpbox?
2. Capture EXACT verbatim quotes for:
   - FAQ answer: "Does MACAE support private networking?" (reviewer's claimed quote: "Yes... use the WAF (production) configuration (main.waf.parameters.json) with EncryptionAtHost registered.")
   - Architecture/resource description: "Virtual Machine / jumpbox — Deployed only for the WAF (production) configuration to support private networking."
   - Any parameter doc describing `enablePrivateNetworking` or similar.
3. Case-insensitive whole-repo grep for the exact phrases: `VNet integration`, `vnet integration`, `virtual network integration`, `private endpoint`, `EncryptionAtHost`, `enablePrivateNetworking`. Determine whether "VNet integration" / "virtual network integration" appears ANYWHERE.

---

## HEADLINE FINDINGS

1. The reviewer's two claimed quotes DO NOT EXIST verbatim anywhere in the repo.
   - There is NO FAQ section in README.md (or any doc) titled or containing "Does MACAE support private networking?".
   - There is NO architecture text line "Virtual Machine / jumpbox — Deployed only for the WAF (production) configuration to support private networking." The README "Solution architecture" section is an IMAGE only (architecture.png), with no per-resource text descriptions.
   - Zero matches for the anchor strings: "Does MACAE support", "support private networking", "to support private networking", "Deployed only for".

2. "VNet integration" (the exact phrase) DOES appear in the repo — but ONLY in Bicep/ARM source parameter descriptions, NEVER in README.md or any docs/*.md file.

3. "virtual network integration" (the exact phrase) appears NOWHERE in the repo (zero matches). The compiled ARM JSON uses the capitalized variant "Regional VNET Integration" inside vendored AVM module descriptions only.

4. The term the source actually uses for the mechanism is "private networking" (parameter `enablePrivateNetworking`). The implementation is a MIX: VNet + subnets + Azure Bastion + a jumpbox VM + private DNS zones + private endpoints for data services (Cosmos, Storage), while App Service / Container App Environment use subnet "VNet integration".

---

## 1. README.md — Private Networking / WAF / Jumpbox

The README has NO FAQ section and NO per-resource architecture text. Section headings present:
Solution overview, Solution architecture (image only), Agentic architecture (image only), Additional resources, Key features, Quick deploy, Prerequisites and Costs, Business Scenario, Business value, Use Case, Supporting documentation, Security guidelines, Cross references.

Only two networking-relevant lines exist in README.md:

- README.md line 28 — architecture is an image, not text:
  > `|![image](./docs/images/readme/architecture.png)|`

- README.md line 85 — the only "use WAF for private networking" steer (a Note, NOT a FAQ, and does NOT mention main.waf.parameters.json or EncryptionAtHost):
  > "**Note**: Some tenants may have additional security restrictions that run periodically and could impact the application (e.g., blocking public network access). If you experience issues or the application stops working, check if these restrictions are the cause. In such cases, consider deploying the WAF-supported version to ensure compliance. To configure, [Click here](./docs/DeploymentGuide.md#31-choose-deployment-type-optional)."

- README.md line 188 — Security guidelines, generic firewall/VNet suggestion (links to external Learn docs, NOT the jumpbox/WAF config):
  > "Protecting the Azure Container Apps instance with a [firewall](https://learn.microsoft.com/azure/container-apps/waf-app-gateway) and/or [Virtual Network](https://learn.microsoft.com/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli)."

CONCLUSION: The reviewer's quoted FAQ answer and jumpbox architecture line are NOT present in README.md. They are not paraphrases of existing README text either — there is no FAQ and no architecture resource list in the README at all.

---

## 2. docs/ — Where WAF / private networking / jumpbox ARE actually documented

### docs/DeploymentGuide.md

- DeploymentGuide.md line 9 — WAF steer note (mirrors README line 85):
  > "**Note**: Some tenants may have additional security restrictions ... consider deploying the WAF-supported version to ensure compliance. To configure, [Click here](#31-choose-deployment-type-optional)."

- DeploymentGuide.md line 188 (Section "3.1 Choose Deployment Type") — the WAF config-file mechanism:
  > "| **Configuration File** | `main.parameters.json` (sandbox) | Copy `main.waf.parameters.json` to `main.parameters.json` |"

- DeploymentGuide.md line 192:
  > "| **Framework** | Basic configuration | [Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/) |"

- DeploymentGuide.md line 197 — the EncryptionAtHost prerequisite, tied to WAF/production VMs:
  > "**Prerequisite** — Enable the Microsoft.Compute/EncryptionAtHost feature for every subscription (and region, if required) where you plan to deploy VMs or VM scale sets with `encryptionAtHost: true`. Repeat the registration steps below for each target subscription (and for each region when applicable). This step is required for **WAF-aligned** (production) deployments."

- DeploymentGuide.md line 204:
  > "Run: `az feature register --name EncryptionAtHost --namespace Microsoft.Compute`"

- DeploymentGuide.md line 206:
  > "Run: `az feature show --name EncryptionAtHost --namespace Microsoft.Compute --query properties.state -o tsv`"

- DeploymentGuide.md lines 216-218 — copy steps for the WAF parameters file.

- DeploymentGuide.md Section "3.2 Set VM Credentials (Optional - Production Deployment Only)":
  > "**Note:** This section only applies if you selected **Production** deployment type in section 3.1. VMs are not deployed in the default Development/Testing configuration."

NOTE: This is the CLOSEST the docs come to the reviewer's claimed FAQ. It conveys the same FACTS (WAF/production = copy main.waf.parameters.json + register EncryptionAtHost + VMs only in production), but it is a deployment-guide table/prose, NOT a README FAQ, and it never uses the sentence the reviewer quoted.

### docs/CustomizingAzdParameters.md — the `enablePrivateNetworking`-adjacent parameter docs

There is NO doc row literally named `enablePrivateNetworking`. The user-facing knobs are the VM parameters (only relevant under private networking):

- CustomizingAzdParameters.md line ~30:
  > "| `AZURE_ENV_VM_ADMIN_USERNAME`  | string | `take(newGuid(), 20)`               | The administrator username for the virtual machine.         |"
- CustomizingAzdParameters.md line ~31:
  > "| `AZURE_ENV_VM_ADMIN_PASSWORD`  | string | `newGuid()`               | The administrator password for the virtual machine.         |"
- CustomizingAzdParameters.md line 32 — explicitly ties the VM to private networking:
  > "| `AZURE_ENV_VM_SIZE`  | string | `Standard_D2s_v5`               | The size of the virtual machine deployed with private networking.         |"

### docs/TroubleShootingSteps.md — jumpbox + Bastion specifics

- TroubleShootingSteps.md line 64 — names the VM a "jumpbox":
  > "**In this deployment**, the jumpbox VM defaults to `Standard_D2s_v5`. ..."
- TroubleShootingSteps.md line 122 — VNet/Bastion subnet sizing (`AzureBastionSubnet` must be /27).
- TroubleShootingSteps.md line 125 — reproduces with `enablePrivateNetworking=true` creating `AzureBastionSubnet` + NSG; Azure Bastion deploy failure.
- TroubleShootingSteps.md line 126 — `AzureBastionSubnet` route-table restriction.

### docs/feature-changelog.md

No matches for VNet / private networking / jumpbox / WAF / Bastion / virtual network. (Changelog covers Agent V2, Foundry IQ KB, etc. — not networking.)

### Other docs checked (AVMPostDeploymentGuide.md, ManualAzureDeployment.md, quota_check.md)

No additional private-networking FAQ or jumpbox architecture prose surfaced beyond the above. No doc anywhere contains the reviewer's quoted sentences.

---

## 3. infra/ — networking source (where the mechanism is actually defined)

- infra/main.bicep line 226:
  > "@description('Optional. Enable private networking for applicable resources. Defaults to true when deploymentFlavor is avm-waf.')"
- infra/main.bicep line 227:
  > "param enablePrivateNetworking bool = deploymentFlavor == 'avm-waf'"

- infra/avm/main.bicep line 189-190:
  > "@description('Optional. Enable private networking for applicable resources, aligned with the Well Architected Framework recommendations. Defaults to false.')"
  > "param enablePrivateNetworking bool = false"
- infra/avm/main.bicep — conditional WAF-only resources gated on `enablePrivateNetworking`: virtualNetwork (655), bastionHost (672), maintenanceConfiguration (685), windowsVmDataCollectionRules (698), proximityPlacementGroup (711), virtualMachine/jumpbox (723), privateDnsZoneDeployments (754).
- infra/avm/main.bicep lines 802 & 806-807 — explicit note that AI Foundry / MCP KnowledgeBase stays public because private endpoints don't work for it (the private-endpoint module is COMMENTED OUT):
  > "publicNetworkAccess: 'Enabled' // Always enabled, as MCP KnowledgeBase Connections doesn't work private endpoints"
  > "// Commented Private Endpoints as MCP KnowledgeBase Connections doesn't work private endpoints"

- infra/avm/modules/compute/virtual-machine.bicep line 2:
  > "// Module: Virtual Machine (Jumpbox)"
- infra/avm/modules/compute/virtual-machine.bicep line 101:
  > "encryptionAtHost: true"

- infra/bicep/main.bicep line 4 (the NON-WAF vanilla orchestrator, explicitly excludes these):
  > "metadata description = 'Vanilla Bicep orchestrator ... This deployment intentionally excludes WAF features such as private networking, scale-out, redundancy, bastion, and VM resources while keeping router-compatible outputs.'"

- Data services use private ENDPOINTS (not "VNet integration"):
  - infra/avm/modules/data/storage-account.bicep line 54: "// --- WAF: Private Networking ---"; line 67: "@description('Subnet resource ID for the private endpoint.')"
  - infra/avm/modules/data/cosmos-db-nosql.bicep line 38: "// --- WAF: Private Networking ---"; line 45: "@description('Subnet resource ID for the private endpoint.')"

No infra/-level README describes networking (only infra/vscode_web/README.md exists, unrelated).

---

## 4. WHOLE-REPO CASE-INSENSITIVE GREP RESULTS

### "VNet integration" — APPEARS, but only in Bicep/ARM source (NOT docs/README)

| File (workspace-relative) | Line | Verbatim |
|---|---|---|
| infra/avm/modules/compute/container-app-environment.bicep | 21 | "@description('Subnet resource ID for VNet integration (required when enablePrivateNetworking is true).')" |
| infra/avm/modules/compute/app-service.bicep | 66 | "@description('Subnet resource ID for VNet integration.')" |
| infra/avm/main.json | 45996 | "description": "Subnet resource ID for VNet integration (required when enablePrivateNetworking is true)." |
| infra/avm/main.json | 56108 | "description": "Subnet resource ID for VNet integration." |
| infra/avm/main.json | 55255 | "...resource ID of the subnet to integrate the App Service Plan with for VNet integration." |
| infra/avm/main.json | 56531 / 61198 / 66659 | "...joined by Regional VNET Integration..." (vendored AVM module text) |
| .copilot-tracking/research/2026-06-25/macae-waf-private-networking-research.md | 2,6,15,29,37 | A RESEARCH TRACKING artifact (this agent's own prior research), NOT docs/source-KB |

ANSWER: "VNet integration" appears in the repo, but ONLY in (a) Bicep module parameter descriptions, (b) the compiled ARM JSON, and (c) a `.copilot-tracking` research note. It appears in ZERO README/docs content.

### "virtual network integration" — ZERO matches anywhere.

### "private endpoint" — present (Cosmos/Storage modules, commented AI Foundry PE, main.bicep comments). Multiple matches across infra/avm.

### "EncryptionAtHost" — present:
- docs/DeploymentGuide.md lines 197, 204, 206, 211 (prereq + az commands).
- infra/avm/modules/compute/virtual-machine.bicep line 101 ("encryptionAtHost: true").
- infra/avm/main.json lines 12478, 14725, 14729, 15464 (vendored VM module).

### "enablePrivateNetworking" — present in infra/main.bicep (226-227, 296), infra/avm/main.bicep (190, 265, 591-593, 655, 669-670, 672, 685, 698, 711, 723, 754, 952...), data modules, and docs/TroubleShootingSteps.md (125). No README/docs FAQ row literally named this param.

---

## ANSWERS TO THE FOUR REQUIRED QUESTIONS

(a) Exact FAQ wording about private networking:
   NONE EXISTS. There is no FAQ in README.md or any doc. The reviewer's quote ("Yes... use the WAF (production) configuration (main.waf.parameters.json) with EncryptionAtHost registered.") is NOT present verbatim anywhere (zero matches for "Does MACAE support" / "support private networking"). The closest real text is README.md line 85 (steer to "WAF-supported version") and docs/DeploymentGuide.md §3.1 lines 188/197 (copy main.waf.parameters.json + register EncryptionAtHost), which convey the same facts but are not a README FAQ.

(b) Exact architecture wording about the jumpbox:
   NONE EXISTS in README. The README "Solution architecture" is an image only (README.md line 28). The reviewer's line "Virtual Machine / jumpbox — Deployed only for the WAF (production) configuration to support private networking." is NOT present verbatim (zero matches for "Deployed only for"). The term "jumpbox" appears in docs/TroubleShootingSteps.md line 64 ("the jumpbox VM defaults to Standard_D2s_v5") and infra/avm/modules/compute/virtual-machine.bicep line 2 ("// Module: Virtual Machine (Jumpbox)"). The "VMs only in production/WAF" fact is stated in docs/DeploymentGuide.md §3.2 ("VMs are not deployed in the default Development/Testing configuration").

(c) Term(s) the source uses for the networking mechanism:
   Primary term = "private networking" (parameter `enablePrivateNetworking`, defaulting on for the avm-waf flavor). The mechanism is a MIX: VNet + subnets, Azure Bastion, a jumpbox VM, private DNS zones, and private ENDPOINTS for data services (Cosmos/Storage). App Service and Container App Environment subnet wiring is labeled "VNet integration" ONLY in their Bicep parameter @descriptions — not in docs.

(d) Does "VNet integration" appear anywhere in the repo?
   YES — but ONLY in Bicep/ARM source + a `.copilot-tracking` research note, NEVER in README/docs:
   - infra/avm/modules/compute/container-app-environment.bicep line 21
   - infra/avm/modules/compute/app-service.bicep line 66
   - infra/avm/main.json lines 45996, 55255, 56108, 56531, 61198, 66659 (compiled output; 55255/56531/61198/66659 are "Regional VNET Integration")
   - .copilot-tracking/research/2026-06-25/macae-waf-private-networking-research.md (prior research artifact)
   "virtual network integration" = ZERO matches.

---

## Clarifying Questions / Caveats

- The reviewer appears to be quoting a DRAFT/proposed README FAQ + architecture-resource section that is NOT YET in the repo (or was removed). If the intent is to ADD such an FAQ, note it would be NEW content, not a correction of existing text.
- If a future FAQ/architecture entry uses "via VNet integration" as the headline mechanism, that would be technically imprecise: data services use private endpoints, and a jumpbox+Bastion are involved — "private networking" (the param name) is the accurate umbrella term.

## Recommended Next Research (not done here)

- [ ] Confirm whether a separate ADR or PR description (outside docs/) introduced the reviewer's exact FAQ/architecture wording.
- [ ] If adding the FAQ, decide the canonical mechanism phrase ("private networking" vs "VNet integration") for consistency with infra parameter naming.
