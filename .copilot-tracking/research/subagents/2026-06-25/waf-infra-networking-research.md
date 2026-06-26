<!-- markdownlint-disable-file -->
# WAF Infra Private-Networking Research — MACAE

Date: 2026-06-25
Scope: Determine the EXACT Azure private-networking mechanism(s) used by the
WAF (Well-Architected Framework / production) deployment of the Multi-Agent
Custom Automation Engine (MACAE) accelerator, from bicep ground truth.

## Research Questions

1. Does the WAF config use App Service / Functions "VNet integration" specifically?
2. Does the WAF config use private endpoints (inbound private IPs + privatelink DNS)?
3. Does the WAF config use a jumpbox / bastion VM?
4. Which compute platform does MACAE actually run on (App Service vs Container Apps vs Functions)?
5. Single most accurate one-sentence description of how WAF provides private networking.

## Status

Complete. All five questions answered from IaC ground truth with file+line evidence.

---

## How the WAF path is selected (router)

infra/main.bicep is a deployment ROUTER, not the resource definition.

- infra/main.bicep:16-18 — `@allowed(['bicep', 'avm', 'avm-waf'])` param `deploymentFlavor`.
- infra/main.bicep:224 — `enableMonitoring = deploymentFlavor == 'avm-waf'`.
- infra/main.bicep:226-227 — `param enablePrivateNetworking bool = deploymentFlavor == 'avm-waf'` (private networking ON only for the WAF flavor).
- infra/main.bicep:230 — `enableScalability = deploymentFlavor == 'avm-waf'`.
- infra/main.bicep:233 — `enableRedundancy = deploymentFlavor == 'avm-waf'`.
- infra/main.bicep:251-252 — `var isAvm = deploymentFlavor == 'avm' || deploymentFlavor == 'avm-waf'`; `var isBicep = deploymentFlavor == 'bicep'`.
- infra/main.bicep:258 — `module avmDeployment './avm/main.bicep' = if (isAvm)` — both `avm` and `avm-waf` route to infra/avm/main.bicep; `enablePrivateNetworking` is forwarded (infra/main.bicep:298).
- infra/main.bicep:~318 — `module bicepDeployment './bicep/main.bicep' = if (isBicep)` — vanilla path.

WAF parameter file pins the flavor and forces private networking + the VM:

- infra/main.waf.parameters.json:5-7 — `"deploymentFlavor": { "value": "avm-waf" }`.
- infra/main.waf.parameters.json:72-74 — `"enableMonitoring": true`, `"enablePrivateNetworking": true`.
- infra/main.waf.parameters.json:75-78 — `"enableScalability": true`, `"enableRedundancy": false`.
- infra/main.waf.parameters.json:79-90 — `vmAdminUsername`, `vmAdminPassword`, `vmSize` (jumpbox VM creds), plus existing-LAW / existing-Foundry passthroughs and container registry hostnames + image tags.

Vanilla (non-WAF) bicep path explicitly has NO private networking:

- infra/bicep/main.bicep:4 — "This deployment intentionally excludes WAF features such as private networking, scale-out, redundancy, bastion, and VM resources...".
- grep of infra/bicep/** for `enablePrivateNetworking|privateEndpoint|virtualNetwork|bastion` returns ONLY that descriptive comment (no networking resources).

Conclusion: the WAF orchestrator is infra/avm/main.bicep with `enablePrivateNetworking = true`. Everything below is gated on that flag (`= if (enablePrivateNetworking)` or `enablePrivateNetworking ? ... : ...`).

- infra/avm/main.bicep:190 — `param enablePrivateNetworking bool = false` (default off; WAF sets true).

---

## Compute platform — MACAE runs on BOTH Container Apps AND App Service

MACAE is a multi-tier app. The WAF orchestrator deploys three application
workloads:

1. Backend API — Azure Container Apps.
   - infra/avm/main.bicep:349 — `var containerAppName = 'ca-${solutionSuffix}'`.
   - infra/avm/main.bicep:1066-1072 — `module containerApp './modules/compute/container-app.bicep'`, ingress external, target port 8000, on `containerAppEnvironment`.
   - infra/avm/main.bicep:1100 — image `${backendContainerRegistryHostname}/${backendContainerImageName}:${backendContainerImageTag}`.
2. MCP server — Azure Container Apps.
   - infra/avm/main.bicep:1236-1242 — `module containerAppMcp './modules/compute/container-app.bicep'`, on same `containerAppEnvironment`.
   - infra/avm/main.bicep:1263 — image `${MCPContainerRegistryHostname}/${MCPContainerImageName}:${MCPContainerImageTag}`.
3. Frontend web app — Azure App Service (Linux container Web App).
   - infra/avm/main.bicep:1339-1351 — `module webServerFarm './modules/compute/app-service-plan.bicep'` (App Service Plan, SKU `P1v4` when scalable/redundant else `B3`).
   - infra/avm/main.bicep:1353-1376 — `module webSite './modules/compute/app-service.bicep'`, `linuxFxVersion: 'DOCKER|${frontendContainerRegistryHostname}/...'`, `WEBSITES_PORT: '3000'`.

There are NO Azure Functions anywhere in the WAF path (the app-service AVM
wrapper enumerates `functionapp` kinds at infra/avm/modules/compute/app-service.bicep:46-58, but the frontend module is invoked with the default `kind = 'app,linux'`, i.e. a Web App, NOT a function app).

Container Registry is NOT deployed by this IaC. Hostnames default to the public
Microsoft sample registry and are overridden by env:

- infra/avm/main.bicep:150 — `param backendContainerRegistryHostname string = 'biabcontainerreg.azurecr.io'`.
- infra/avm/main.bicep:159 — frontend hostname default `biabcontainerreg.azurecr.io`.
- infra/avm/main.bicep:168 — MCP hostname default `biabcontainerreg.azurecr.io`.
- No `Microsoft.ContainerRegistry/registries` resource/module is declared (grep for `containerRegistry|registries|Microsoft.ContainerRegistry` finds only the image-hostname params and the container-app `registries` passthrough param). So there is NO ACR resource and therefore NO ACR private endpoint.

No Key Vault is deployed by MACAE. The privateDnsZones list (below) has no
`privatelink.vaultcore.azure.net`, and grep for `Microsoft.KeyVault` matches
only the compiled AVM library's optional `customerManagedKey` code paths inside
infra/avm/main.json (storage / cognitive-services CMK support), not a MACAE Key
Vault resource. So there is no Key Vault private endpoint.

---

## The VNet (WAF only)

- infra/avm/main.bicep:655-666 — `module virtualNetwork './modules/networking/virtual-network.bicep' = if (enablePrivateNetworking)`, address space `10.0.0.0/8`, subnets = `virtualNetworkSubnets`.

Subnets defined at infra/avm/main.bicep:373-540 (`var virtualNetworkSubnets`):

| Subnet | Prefix | Delegation | Purpose | Evidence |
| --- | --- | --- | --- | --- |
| `backend` | 10.0.0.0/27 | none | Holds the PRIVATE ENDPOINTS (storage, cosmos) | infra/avm/main.bicep:375-376 |
| `containers` | 10.0.2.0/23 | `Microsoft.App/environments` | Container Apps Environment VNet INJECTION | infra/avm/main.bicep:400-402 |
| `webserverfarm` | 10.0.4.0/27 | `Microsoft.Web/serverfarms` | App Service VNet INTEGRATION (frontend) | infra/avm/main.bicep:428-430 |
| `administration` | 10.0.0.32/27 | none | Jumpbox VM NIC | infra/avm/main.bicep:466 (block ~466-475) |
| `AzureBastionSubnet` | — | none | Azure Bastion | infra/avm/main.bicep:481-484 |

Authoritative subnet/delegation creation in the module:

- infra/avm/modules/networking/virtual-network.bicep:48 — `delegation: 'Microsoft.App/environments'` (containers).
- infra/avm/modules/networking/virtual-network.bicep:73 — `delegation: 'Microsoft.Web/serverfarms'` (webserverfarm).
- infra/avm/modules/networking/virtual-network.bicep:118-121 — `name: 'AzureBastionSubnet'` + `nsg-bastion`.
- infra/avm/modules/networking/virtual-network.bicep:225 — generic `delegation: subnet.?delegation` applied per subnet.
- Subnet resource-ID outputs: backend (267-268), containers (270-271), webserverfarm (273-274), administration (276-277), bastion (279-280).

---

## Mechanism 1 — App Service / Functions VNet INTEGRATION (outbound) — YES, for the frontend App Service only

The frontend Web App uses regional VNet integration into the delegated
`webserverfarm` subnet. This is the specific App Service "VNet integration"
(outbound) feature — NOT a private endpoint.

- infra/avm/main.bicep:1371 — `virtualNetworkSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.webserverfarmSubnetResourceId : ''` (the App Service is joined to the `webserverfarm` subnet, which is delegated to `Microsoft.Web/serverfarms`).
- infra/avm/main.bicep:1369 — `PROXY_API_REQUESTS: enablePrivateNetworking ? 'true' : 'false'` (in WAF mode the frontend proxies API calls to the backend Container App over the VNet).
- App Service module maps the subnet to the AVM regional-integration property:
  - infra/avm/modules/compute/app-service.bicep:66-67 — `param virtualNetworkSubnetId string = ''`.
  - infra/avm/modules/compute/app-service.bicep:137 — `virtualNetworkSubnetResourceId: !empty(virtualNetworkSubnetId) ? virtualNetworkSubnetId : null` (this is the AVM `avm/res/web/site` regional VNet-integration input; module ref at app-service.bicep:85 `avm/res/web/site:0.23.1`).
  - infra/avm/modules/compute/app-service.bicep:72-74 — `param vnetRouteAllEnabled bool = false` and it is wired at app-service.bicep:128 `vnetRouteAllEnabled: vnetRouteAllEnabled`. The WAF call (infra/avm/main.bicep:1353-1376) does NOT pass `vnetRouteAllEnabled`, so route-all stays FALSE (only private/RFC1918 destinations traverse the VNet; general egress is not forced through it).

Frontend App Service public access / inbound:

- infra/avm/main.bicep:1372 — `publicNetworkAccess: 'Enabled'` (the frontend stays publicly reachable; it is the user-facing entry point).
- infra/avm/modules/compute/app-service.bicep:80-82 — `param privateEndpoints ...` exists but is NOT passed by the WAF call, so the frontend App Service has NO inbound private endpoint. Its only VNet tie is the outbound VNet integration above.

---

## Mechanism 2 — Container Apps Environment VNet INJECTION (subnet delegation) — YES, for backend + MCP

The Container Apps Environment is injected into the delegated `containers`
subnet and made internal-only in WAF mode (this is NOT VNet integration and NOT
a classic private endpoint; it is VNet injection of the managed environment).

- infra/avm/main.bicep:669-670 — `containerSubnetIndex` / `containerSubnetResourceId` resolve the `containers` subnet.
- infra/avm/main.bicep:1011-1040 — `module containerAppEnvironment './modules/compute/container-app-environment.bicep'`, with `infrastructureSubnetId: enablePrivateNetworking ? containerSubnetResourceId : ''`.
- infra/avm/modules/compute/container-app-environment.bicep:62 — `publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'`.
- infra/avm/modules/compute/container-app-environment.bicep:63 — `internal: enablePrivateNetworking` (internal-only ingress, no public static IP).
- infra/avm/modules/compute/container-app-environment.bicep:64 — `infrastructureSubnetResourceId: !empty(infrastructureSubnetId) ? infrastructureSubnetId : null` (AVM `avm/res/app/managed-environment:0.13.3`, module ref at line 56).
- Private DNS for the internal CA env default domain:
  - infra/avm/main.bicep:1042-1064 — `module containerAppEnvDNSZone './modules/networking/private-dns-zone.bicep' = if (enablePrivateNetworking)`, creates a wildcard A record `*` → `containerAppEnvironment.outputs.staticIp` for `defaultDomain`, linked to the VNet.

So backend + MCP Container Apps are reachable only inside the VNet in WAF mode;
the frontend App Service reaches the backend over its VNet integration.

---

## Mechanism 3 — Private endpoints (inbound private IP + privatelink DNS) — YES, but only for Storage and Cosmos DB

Private DNS zones declared (WAF):

- infra/avm/main.bicep:351-358 — `var privateDnsZones`:
  - `privatelink.cognitiveservices.azure.com`
  - `privatelink.openai.azure.com`
  - `privatelink.services.ai.azure.com`
  - `privatelink.documents.azure.com`
  - `privatelink.blob.core.windows.net`
  - `privatelink.search.windows.net`
- infra/avm/main.bicep:359-366 — `dnsZoneIndex` map (cognitiveServices 0, openAI 1, aiServices 2, cosmosDb 3, blob 4, search 5).
- infra/avm/main.bicep:754-772 — `@batchSize(5) module privateDnsZoneDeployments ... = [for zone in privateDnsZones: if (enablePrivateNetworking && (!useExistingAIProject || !contains(aiRelatedDnsZoneIndices, i)))]` — the zones are created and VNet-linked.

Actual private endpoints created:

- Storage (blob) — YES.
  - infra/avm/main.bicep:949 — `publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'`.
  - infra/avm/main.bicep:964 — `enablePrivateNetworking: enablePrivateNetworking`.
  - infra/avm/main.bicep:965 — `privateEndpointSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.backendSubnetResourceId : ''` (PE lands in `backend` subnet).
  - infra/avm/main.bicep:966-968 — `privateDnsZoneResourceIds: [ privateDnsZoneDeployments[dnsZoneIndex.blob]!.outputs.resourceId ]`.
  - infra/avm/modules/data/storage-account.bicep:111-119 — `privateEndpoints: enablePrivateNetworking ? [{ subnetResourceId: privateEndpointSubnetId; service: 'blob'; privateDnsZoneGroup: ... }] : []` (creates `Microsoft.Network/privateEndpoints` via AVM storage module).
- Cosmos DB (Sql) — YES.
  - infra/avm/main.bicep:996 — `publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'`.
  - infra/avm/main.bicep:1001 — `privateEndpointSubnetId: enablePrivateNetworking ? virtualNetwork!.outputs.backendSubnetResourceId : ''`.
  - infra/avm/main.bicep:1002-1004 — `privateDnsZoneResourceIds: [ privateDnsZoneDeployments[dnsZoneIndex.cosmosDb]!.outputs.resourceId ]`.
  - infra/avm/modules/data/cosmos-db-nosql.bicep:94-102 — `privateEndpoints: enablePrivateNetworking ? [{ subnetResourceId: privateEndpointSubnetId; service: 'Sql'; privateDnsZoneGroup: ... }] : []`.

Services deliberately LEFT PUBLIC even in WAF mode (no private endpoint):

- Azure AI Foundry / AI Services — NO private endpoint.
  - infra/avm/main.bicep:803 — `publicNetworkAccess: 'Enabled' // Always enabled, as MCP KnowledgeBase Connections doesn't work [with] private endpoints`.
  - infra/avm/main.bicep:806-849 — the AI Foundry private-endpoint module is COMMENTED OUT (with the same MCP-KB rationale). The `cognitiveservices` / `openai` / `services.ai` privatelink zones are still created but not attached to a Foundry PE (and are skipped entirely when reusing an existing project: infra/avm/main.bicep:754 condition + `aiRelatedDnsZoneIndices` infra/avm/main.bicep:367-371).
- Azure AI Search — NO private endpoint.
  - infra/avm/main.bicep:877 — `publicNetworkAccess: 'Enabled'`.
  - infra/avm/main.bicep:913 — `privateEndpoints: []` (empty even in WAF). The `privatelink.search.windows.net` zone is declared but unused for a Search PE.
- Container Registry — not deployed (external public sample registry), so no PE.
- Key Vault — not deployed, so no PE.

Net: in WAF mode the only true PaaS private endpoints are Storage (blob) and
Cosmos DB (Sql), both terminating in the `backend` subnet.

---

## Mechanism 4 — Jumpbox VM + Azure Bastion — YES, WAF-only

- infra/avm/main.bicep:672-683 — `module bastionHost './modules/networking/bastion-host.bicep' = if (enablePrivateNetworking)` (Azure Bastion into `AzureBastionSubnet`).
- infra/avm/main.bicep:723-749 — `module virtualMachine './modules/compute/virtual-machine.bicep' = if (enablePrivateNetworking)`:
  - infra/avm/main.bicep:732 — `adminUsername: vmAdminUsername ?? 'JumpboxAdminUser'`.
  - infra/avm/main.bicep:733 — `adminPassword: vmAdminPassword ?? 'JumpboxAdminP@ssw0rd1234!'`.
  - infra/avm/main.bicep:734 — `subnetResourceId: virtualNetwork!.outputs.administrationSubnetResourceId` (VM NIC in `administration` subnet).
  - infra/avm/main.bicep:736 — `osType: 'Windows'`.
- Supporting WAF-only modules: maintenance config (infra/avm/main.bicep:685-696), VM data-collection rules (698-709), proximity placement group (711-721) — all `= if (enablePrivateNetworking)` / `if (enablePrivateNetworking && enableMonitoring)`.

The VM is a Windows jumpbox reached via Azure Bastion, gated strictly to the WAF
path (the vanilla bicep path excludes it per infra/bicep/main.bicep:4).

---

## Key Discoveries (summary)

- WAF = `deploymentFlavor: avm-waf` → infra/avm/main.bicep with `enablePrivateNetworking = true` (infra/main.bicep:226-227; infra/main.waf.parameters.json:5-7,73).
- MACAE compute = Container Apps (backend + MCP) + App Service (frontend Web App). No Azure Functions.
- Three distinct private-networking mechanisms are combined:
  1. App Service VNet INTEGRATION (outbound) for the frontend into the `Microsoft.Web/serverfarms`-delegated `webserverfarm` subnet (infra/avm/main.bicep:1371; app-service.bicep:137).
  2. Container Apps Environment VNet INJECTION (internal=true) into the `Microsoft.App/environments`-delegated `containers` subnet (container-app-environment.bicep:62-64).
  3. Private ENDPOINTS for Storage (blob) and Cosmos DB (Sql) into the `backend` subnet with privatelink DNS (storage-account.bicep:111-119; cosmos-db-nosql.bicep:94-102).
- Plus a Windows jumpbox VM + Azure Bastion, WAF-only (infra/avm/main.bicep:672-749).
- AI Foundry / AI Services and AI Search are intentionally left public even in WAF (private endpoints commented out / empty) because MCP KnowledgeBase connections don't work over private endpoints (infra/avm/main.bicep:803-849, 877, 913).

## Direct Answers

- (a) App Service "VNet integration" specifically? YES — frontend Web App only, regional VNet integration into the serverfarms-delegated `webserverfarm` subnet (infra/avm/main.bicep:1371; infra/avm/modules/compute/app-service.bicep:137). No Functions are used.
- (b) Private endpoints? YES — but only Storage (blob) and Cosmos DB (Sql) into the `backend` subnet (infra/avm/main.bicep:965-968, 1001-1004; storage-account.bicep:111-119; cosmos-db-nosql.bicep:94-102). AI Foundry, AI Search, ACR, Key Vault have none.
- (c) Jumpbox VM? YES — Windows jumpbox + Azure Bastion, gated to WAF only (infra/avm/main.bicep:672-749).
- (d) Compute platform? Container Apps for backend + MCP (infra/avm/main.bicep:1066, 1236) AND App Service Web App for the frontend (infra/avm/main.bicep:1353); no Azure Functions.
- (e) One-sentence description: In the `avm-waf` configuration, MACAE provides private networking by deploying a hub VNet whose backend Container Apps Environment is VNet-injected into a delegated subnet (internal-only), whose frontend App Service uses regional VNet integration into a `Microsoft.Web/serverfarms`-delegated subnet, and whose Storage and Cosmos DB are reached via private endpoints with privatelink DNS, all administered through a Bastion-fronted Windows jumpbox — while AI Foundry and AI Search are intentionally left on public endpoints (infra/avm/main.bicep:655-749, 965-1004, 1011-1040, 1371; infra/avm/modules/compute/app-service.bicep:137; infra/avm/modules/compute/container-app-environment.bicep:62-64).

## Recommended Next Research (not done this session)

- [ ] Confirm whether the `administration` subnet NSG and the `deny-hop-outbound` rules materially restrict the jumpbox (read infra/avm/main.bicep:466-540 NSG blocks in full).
- [ ] Trace post-provision scripts (infra/scripts/post-provision/) to see if any networking is reconfigured at deploy time (e.g., seed_kb_connections.py, post_deploy.*).
- [ ] Verify the `re-use-foundry-project` / existing-LAW reuse paths don't add or remove any private endpoints.

## Clarifying Questions

None — the IaC is unambiguous on all five questions.
