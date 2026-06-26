<!-- markdownlint-disable-file -->
# WAF Network Isolation Posture Research (MACAE `avm-waf`)

## Research Topics / Questions

1. VNet + subnet definitions: every subnet, address space, delegation, line ranges.
2. NSG definitions/rules — `deny-hop-outbound` and bastion rules; quote name/direction/access/priority and explain how tightly the jumpbox/subnets are constrained (internet reach? subnet-to-subnet?).
3. Private endpoints for Storage (blob) + Cosmos DB: subnet, privatelink Private DNS zone names, whether `publicNetworkAccess` is Disabled.
4. Bastion host config (SKU, subnet) + jumpbox VM config (OS, size, admin user handling, public IP?).
5. Which services KEEP public access in WAF (AI Foundry/AI Services, AI Search) and whether `publicNetworkAccess` is explicitly Enabled.

Status: Complete.

## Primary Sources

- infra/avm/main.bicep (orchestrator; all subnet/NSG/PE/public-access wiring)
- infra/avm/modules/networking/virtual-network.bicep (VNet + per-subnet NSG AVM wrapper; mirrors defaults)
- infra/avm/modules/networking/bastion-host.bicep (Bastion AVM wrapper)
- infra/avm/modules/compute/virtual-machine.bicep (jumpbox AVM wrapper)
- infra/avm/modules/compute/container-app-environment.bicep (internal env flag)

All private-networking behavior is gated by the `enablePrivateNetworking` flag (true under the WAF/`avm-waf` parameter set).

---

## 1. VNet + Subnets

VNet created in infra/avm/main.bicep lines 643-657 via module `virtualNetwork` (only when `enablePrivateNetworking`):
- addressPrefixes: `['10.0.0.0/8']` (infra/avm/main.bicep line 649)
- subnets: passed as `virtualNetworkSubnets` var (infra/avm/main.bicep line 650)

Subnet array `virtualNetworkSubnets` defined infra/avm/main.bicep lines 373-548. The same shapes are the module-default `subnets` param in infra/avm/modules/networking/virtual-network.bicep lines 22-178.

| # | Subnet name | Address prefix | Delegation | PE/PLS network policies | NSG | main.bicep lines |
|---|-------------|----------------|------------|-------------------------|-----|------------------|
| 1 | `backend` | `10.0.0.0/27` | none | (defaults) | `nsg-backend` | 374-399 |
| 2 | `containers` | `10.0.2.0/23` | `Microsoft.App/environments` | privateEndpointNetworkPolicies `Enabled`, privateLinkServiceNetworkPolicies `Enabled` | `nsg-containers` | 400-427 |
| 3 | `webserverfarm` | `10.0.4.0/27` | `Microsoft.Web/serverfarms` | privateEndpointNetworkPolicies `Enabled`, privateLinkServiceNetworkPolicies `Enabled` | `nsg-webserverfarm` | 428-455 |
| 4 | `administration` | `10.0.0.32/27` | none | (defaults) | `nsg-administration` | 456-477 |
| 5 | `AzureBastionSubnet` | `10.0.0.64/26` | none | (defaults) | `nsg-bastion` | 478-547 |

Subnet → resource mapping (which workload lands where):
- `backend` (10.0.0.0/27): private endpoints for Storage blob (infra/avm/main.bicep line 973) and Cosmos DB (infra/avm/main.bicep line 1000). Was also the intended (commented-out) AI Foundry PE subnet (infra/avm/main.bicep line 814).
- `containers` (10.0.2.0/23): Container Apps Environment infrastructure subnet — `infrastructureSubnetId: containerSubnetResourceId` (infra/avm/main.bicep line 1019; `containerSubnetResourceId` resolved at lines 669-670). Backend + MCP container apps run here.
- `webserverfarm` (10.0.4.0/27): frontend App Service regional VNet integration — `virtualNetworkSubnetId: webserverfarmSubnetResourceId` (infra/avm/main.bicep line 1371).
- `administration` (10.0.0.32/27): jumpbox VM NIC — `subnetResourceId: virtualNetwork!.outputs.administrationSubnetResourceId` (infra/avm/main.bicep line 734).
- `AzureBastionSubnet` (10.0.0.64/26): Azure Bastion host (via VNet resource id, infra/avm/modules/networking/bastion-host.bicep).

---

## 2. NSG Rules

### Workload subnets — single anti-pivot rule `deny-hop-outbound`

`backend`, `containers`, `webserverfarm`, and `administration` each carry exactly ONE explicit custom NSG rule, named `deny-hop-outbound`. Definitions:
- `nsg-backend` / `deny-hop-outbound`: infra/avm/main.bicep lines 380-396
- `nsg-containers` / `deny-hop-outbound`: infra/avm/main.bicep lines 408-424
- `nsg-webserverfarm` / `deny-hop-outbound`: infra/avm/main.bicep lines 436-452
- `nsg-administration` / `deny-hop-outbound`: infra/avm/main.bicep lines 460-476

Rule properties (identical across all four):
- name: `deny-hop-outbound`
- access: `Deny`
- direction: `Outbound`
- priority: `200`
- protocol: `Tcp`
- sourceAddressPrefix: `VirtualNetwork`
- sourcePortRange: `*`
- destinationAddressPrefix: `*`
- destinationPortRanges: `22`, `3389` (SSH, RDP)

Plain language: This rule blocks **outbound SSH (22) and RDP (3389)** from any host in those four subnets to **any** destination. It is an anti-lateral-movement / anti-pivot control: a compromised host (including the jumpbox in `administration`) cannot initiate SSH/RDP "hops" to other machines inside the VNet or out to the internet. It does NOT block general egress — only ports 22/3389/Tcp are denied. All other outbound (e.g., HTTPS 443) falls through to the platform default rules.

Default NSG rules still apply (Azure platform defaults, not overridden here):
- `AllowVnetInBound` / `AllowVnetOutBound` (priority 65000): subnets CAN still talk to each other within the VNet over non-22/3389 ports.
- `AllowInternetOutBound` (priority 65001): subnets CAN still reach the internet on ports other than 22/3389.
- `DenyAllInBound` (priority 65500): no unsolicited inbound from the internet.

So the posture is: **east-west and outbound traffic is generally permitted, but the management/remote-desktop "hop" protocols (22/3389) are explicitly denied outbound everywhere** to prevent pivoting. The jumpbox is reachable (inbound RDP from Bastion is allowed by the default VNet-inbound rule), but cannot itself RDP/SSH outward.

### `AzureBastionSubnet` — `nsg-bastion` (infra/avm/main.bicep lines 481-546)

| Rule name | Direction | Access | Priority | Protocol | Dest port | Source → Dest prefix |
|-----------|-----------|--------|----------|----------|-----------|----------------------|
| `AllowGatewayManager` | Inbound | Allow | 2702 | `*` | 443 | `GatewayManager` → `*` |
| `AllowHttpsInBound` | Inbound | Allow | 2703 | `*` | 443 | `Internet` → `*` |
| `AllowSshRdpOutbound` | Outbound | Allow | 100 | `*` | 22, 3389 | `*` → `VirtualNetwork` |
| `AllowAzureCloudOutbound` | Outbound | Allow | 110 | `Tcp` | 443 | `*` → `AzureCloud` |

Plain language: Bastion accepts inbound HTTPS (443) from the internet (`AllowHttpsInBound`) — this is how an operator reaches the Bastion portal — and from `GatewayManager`. Bastion is explicitly allowed to reach VMs over 22/3389 (`AllowSshRdpOutbound` → `VirtualNetwork`) and to reach Azure control plane over 443 (`AllowAzureCloudOutbound`). Because the `deny-hop-outbound` rule lives on the workload subnets (not on `AzureBastionSubnet`), Bastion is exempt and can broker RDP into the jumpbox; the jumpbox's own NSG only blocks it from RDP/SSH-ing back out.

Net effect for the jumpbox: **reachable only through Bastion (no public IP, see §4), and unable to pivot outward over SSH/RDP.**

---

## 3. Private Endpoints — Storage (blob) + Cosmos DB

Private DNS zones list (infra/avm/main.bicep lines 351-358):
- `privatelink.cognitiveservices.azure.com`
- `privatelink.openai.azure.com`
- `privatelink.services.ai.azure.com`
- `privatelink.documents.azure.com` (Cosmos DB)
- `privatelink.blob.core.windows.net` (Storage blob)
- `privatelink.search.windows.net`

Zones deployed via `privateDnsZoneDeployments` loop (infra/avm/main.bicep lines 753-767), each linked to the VNet. AI-related zones (cognitiveservices/openai/services.ai, indices 0-2) are skipped when reusing an existing AI project (infra/avm/main.bicep lines 367-371, 753).

### Storage account (infra/avm/main.bicep lines 945-978)
- `publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'` (line 952) → **Disabled under WAF**.
- `privateEndpointSubnetId: virtualNetwork!.outputs.backendSubnetResourceId` (line 973) → PE lands in `backend` subnet (10.0.0.0/27).
- `privateDnsZoneResourceIds`: `privatelink.blob.core.windows.net` zone (line 974-976, `dnsZoneIndex.blob`).
- Blob container `default` has `publicAccess: 'None'` (lines 956-959).

### Cosmos DB (NoSQL) (infra/avm/main.bicep lines 980-1004)
- `publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'` (line 994) → **Disabled under WAF**.
- `privateEndpointSubnetId: virtualNetwork!.outputs.backendSubnetResourceId` (line 1000) → PE lands in `backend` subnet (10.0.0.0/27).
- `privateDnsZoneResourceIds`: `privatelink.documents.azure.com` zone (lines 1001-1003, `dnsZoneIndex.cosmosDb`).

Conclusion: Under WAF, **both Storage and Cosmos DB have public network access Disabled and are reachable only via private endpoints in the `backend` subnet**, resolved through their privatelink DNS zones.

---

## 4. Bastion + Jumpbox VM

### Azure Bastion (infra/avm/modules/networking/bastion-host.bicep; wired at infra/avm/main.bicep lines 672-682)
- AVM module `br/public:avm/res/network/bastion-host:0.8.2` (module line 52).
- `skuName` default `'Standard'` (module line 28).
- `scaleUnits` = 4 (module line 31).
- Hardening: `disableCopyPaste: true` (line 34), `enableFileCopy: false` (line 37), `enableIpConnect: false` (line 40), `enableShareableLink: false` (line 43).
- Public IP `pip-bas-<suffix>` created by the module (lines 60-64) — the public IP is on Bastion, NOT on the VM.
- Subnet: implicit `AzureBastionSubnet` via `virtualNetworkResourceId` (module line 60).

### Jumpbox VM (infra/avm/modules/compute/virtual-machine.bicep; wired at infra/avm/main.bicep lines 723-751)
- AVM module `br/public:avm/res/compute/virtual-machine:0.22.0` (module line 85).
- `osType: 'Windows'` (infra/avm/main.bicep line 736).
- `vmSize` default `'Standard_D2s_v5'` (infra/avm/main.bicep line 201; passed line 731).
- Image: Data Science VM, `microsoft-dsvm` / `dsvm-win-2022` / `winserver-2022` / `latest` (module lines 41-46).
- OS disk: Premium_LRS, 128 GB, `encryptionAtHost: true` (module lines 100, 106-114).
- NIC: single ipConfiguration with **only** `subnetResourceId` (the `administration` subnet) — **no public IP / no `pipConfiguration`** on the NIC (module lines 116-131). The VM is private; access is solely via Bastion.
- Admin user handling:
  - `adminUsername: vmAdminUsername ?? 'JumpboxAdminUser'` and `adminPassword: vmAdminPassword ?? 'JumpboxAdminP@ssw0rd1234!'` (infra/avm/main.bicep lines 732-733). Both are `@secure()` params in the module (module lines 24-29) with hardcoded fallback defaults in the orchestrator.
  - **Entra ID join enabled** — `extensionAadJoinConfig.enabled: true` (module lines 132-137). With Entra ID auth, the local admin account cannot be used for login; the deploying user is granted the `Virtual Machine Administrator Login` role (`1c0163c0-47e6-4577-8991-ea5c82e286e4`, module lines 73-80) so they can sign in via Bastion + Entra ID. The hardcoded local password is therefore a provisioning-time requirement, not a usable login credential — but it is still a hardcoded default in IaC worth noting.
- `availabilityZone: 1`, `patchMode: 'AutomaticByPlatform'`, anti-malware extension enabled.

---

## 5. Services that KEEP public access under WAF

### AI Foundry / AI Services account (`ai_foundry_project`, infra/avm/main.bicep lines 795-803)
- `publicNetworkAccess: 'Enabled'` — **explicitly and unconditionally Enabled** (line 802), with inline comment: `// Always enabled, as MCP KnowledgeBase Connections doesn't work private endpoints`.
- The AI Foundry private endpoint module is **fully commented out** (infra/avm/main.bicep lines 805-846), with the same rationale. So AI Foundry/AI Services has NO private endpoint and remains publicly reachable even in WAF.

### AI Search (`ai_search`, infra/avm/main.bicep lines 868-919)
- `publicNetworkAccess: 'Enabled'` — **explicitly Enabled** (line 878), not gated on `enablePrivateNetworking`.
- `privateEndpoints: []` — **no private endpoints** (line 913).
- `disableLocalAuth: true` (line 877) — AAD/Entra-only auth (no admin keys), which is the compensating control for the public surface.

### Frontend App Service (infra/avm/main.bicep ~lines 1355-1374)
- `virtualNetworkSubnetId: webserverfarmSubnetResourceId` — regional VNet integration for outbound to the private backend (line 1371).
- `publicNetworkAccess: 'Enabled'` (line 1372) — frontend stays publicly reachable (it is the public entry point; `PROXY_API_REQUESTS: 'true'` under WAF so it proxies to the internal backend).

### Contrast — services LOCKED DOWN under WAF
- Log Analytics: `publicNetworkAccessForIngestion`/`...ForQuery` = `Disabled` when private (infra/avm/main.bicep lines 591-592).
- Container Apps Environment: `internal: enablePrivateNetworking` and `publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'` (infra/avm/modules/compute/container-app-environment.bicep lines 64-66) → internal-only ingress in WAF.
- Storage + Cosmos: `publicNetworkAccess` Disabled (see §3).

---

## Plain-Language Posture Summary

- **Data plane is sealed:** Cosmos DB and Storage (blob) have public access Disabled and are reached only via private endpoints in the `backend` subnet, through `privatelink.documents.azure.com` and `privatelink.blob.core.windows.net` zones. The backend/MCP container apps run in an **internal** Container Apps environment (no public ingress).
- **Management plane is bastioned and anti-pivot:** The Windows DSVM jumpbox has **no public IP** and is reachable only through Azure Bastion (Standard SKU, copy/paste + file copy + shareable-link disabled) using Entra ID login. Every workload subnet (including the jumpbox's) carries a `deny-hop-outbound` rule blocking outbound SSH/RDP (22/3389) to anywhere, so a compromised host cannot pivot laterally over the remote-management protocols. General east-west and HTTPS egress remain on platform defaults.
- **Deliberate public exceptions (AI plane):** AI Foundry/AI Services and AI Search are **intentionally left publicly reachable** (`publicNetworkAccess: 'Enabled'`, no private endpoints) because MCP KnowledgeBase connections don't work over private endpoints; AI Search compensates with `disableLocalAuth: true` (Entra-only). The frontend App Service is also public by design (the entry point), with VNet integration so it can proxy to the private backend.

### Answers to required final-reply items

(a) **Subnets + delegations:** `backend` 10.0.0.0/27 (no delegation), `containers` 10.0.2.0/23 (Microsoft.App/environments), `webserverfarm` 10.0.4.0/27 (Microsoft.Web/serverfarms), `administration` 10.0.0.32/27 (no delegation), `AzureBastionSubnet` 10.0.0.64/26 (no delegation). [infra/avm/main.bicep lines 373-548]

(b) **NSG posture:** Four workload subnets each Deny outbound TCP 22/3389 to `*` (priority 200, `deny-hop-outbound`) — an anti-pivot block; default rules still allow VNet-internal traffic and non-22/3389 internet egress. Jumpbox can be RDP'd INTO via Bastion but cannot SSH/RDP OUT. Bastion subnet allows inbound 443 from Internet/GatewayManager and outbound 22/3389 to VirtualNetwork + 443 to AzureCloud. [infra/avm/main.bicep lines 380-546]

(c) **Cosmos + Storage public access:** Both `Disabled` under WAF (`publicNetworkAccess: enablePrivateNetworking ? 'Disabled' : 'Enabled'`). [infra/avm/main.bicep lines 952, 994]

(d) **AI Foundry + AI Search:** Both remain **publicly reachable** — `publicNetworkAccess: 'Enabled'` explicitly (AI Foundry line 802, AI Search line 878), AI Foundry PE commented out (lines 805-846), AI Search `privateEndpoints: []` (line 913). [infra/avm/main.bicep]

(e) **Sales-engineer one-liner:** "The WAF deployment private-locks the data and backend tiers — Cosmos DB, Storage, and the backend/MCP Container Apps environment are private-endpoint-only with public access disabled — and exposes management solely through Entra-ID Azure Bastion to a no-public-IP jumpbox whose subnet (like all workload subnets) denies outbound RDP/SSH to stop lateral movement; the AI Foundry and AI Search services are intentionally kept on public endpoints (Entra-only auth) because MCP KnowledgeBase connections don't support private endpoints, and the frontend App Service stays public as the VNet-integrated entry point."

---

## Clarifying Questions / Caveats

- The jumpbox local admin password `JumpboxAdminP@ssw0rd1234!` is a hardcoded fallback default in infra/avm/main.bicep line 733. It is unusable for login (Entra ID join makes local accounts non-login), but it is still a literal credential in tracked IaC — flagging factually; no action requested.
- This research covers the AVM orchestrator (infra/avm/main.bicep). The legacy infra/main.bicep and infra/bicep/main.bicep were not re-read this session; the AVM path is the one wired by `azure_custom.yaml`/`avm-waf`. If the legacy templates must match, that is follow-on.

## Recommended Next Research (not done this session)

- [ ] Confirm legacy infra/main.bicep / infra/bicep parity for the same subnet/NSG/PE posture (only if a non-AVM deploy path is in scope).
- [ ] Verify the WAF parameter file (main.waf.parameters.json) actually sets `enablePrivateNetworking: true` and any subnet/address overrides.
- [ ] Trace how the frontend (public) → backend (internal Container App) call path resolves DNS for the internal CA env (`containerAppEnvDNSZone`, infra/avm/main.bicep lines ~1042+).
