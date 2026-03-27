# WAF Private Networking: Why We Built What We Built

**Document Purpose**: Explain the design decisions, mandatory requirements, and journey of implementing cross-subscription private networking for AI Foundry Agents in the MACAE Solution Accelerator.

**Audience**: Technical reviewers, architects, and developers working with this codebase.

---

## Table of Contents

1. [Background: The Two Deployment Modes](#1-background-the-two-deployment-modes)
2. [Why Two Subnets?](#2-why-two-subnets)
3. [Why Duplicate Private Endpoints?](#3-why-duplicate-private-endpoints)
4. [Is Cosmos DB Mandatory? Can We Skip It?](#4-is-cosmos-db-mandatory-can-we-skip-it)
5. [Is AI Search Mandatory? Can We Skip It?](#5-is-ai-search-mandatory-can-we-skip-it)
6. [Complete Resource Comparison: WAF vs WAF + Existing Foundry](#6-complete-resource-comparison-waf-vs-waf--existing-foundry)
7. [Our Journey: What We Tried and What Errors We Faced](#7-our-journey-what-we-tried-and-what-errors-we-faced)
8. [Extra Resources & Cost from Our Changes](#8-extra-resources--cost-from-our-changes)
9. [Official Microsoft Documentation References](#9-official-microsoft-documentation-references)

---

## 1. Background: The Two Deployment Modes

MACAE supports two deployment paths when WAF (private networking) is enabled:

| Mode | Description | When Used |
|------|-------------|-----------|
| **WAF (New Foundry)** | Deploys a brand-new AI Services account + project in the same subscription as Cosmos DB, Storage, and Search. Everything in one subscription. | User does NOT provide `existingAiFoundryAiProjectResourceId` |
| **WAF + EXP (Existing Foundry)** | Uses an already-existing AI Foundry project. The AI Services account may be in a **different subscription** than where Cosmos DB, Storage, and Search are deployed. | User provides `existingAiFoundryAiProjectResourceId` parameter |

The **WAF + EXP cross-subscription** scenario is the complex one that required all the custom modules we built.

---

## 2. Why Two Subnets?

### The Short Answer

Azure requires two subnets because the **agent compute subnet** has a mandatory delegation that **prevents it from hosting Private Endpoints**. So a second subnet is needed for PEs.

### The Detailed Explanation

#### Subnet 1: Agent Subnet (`172.16.0.0/24`)

This subnet is **delegated** to `Microsoft.App/environments`. 

**What does delegation mean?** It means this subnet is exclusively reserved for Azure Container Apps (which is what AI Foundry's agent compute runs on under the hood). When you delegate a subnet, Azure says: *"Only Container Apps can put their resources here — nothing else."*

**Why is delegation required?** From [Microsoft's official documentation](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/virtual-networks):

> *"Agent Service networking uses Azure Container Apps. When you deploy into your virtual network, you must use a dedicated subnet delegated to `Microsoft.App/environments`."*

And from the [FAQ](https://learn.microsoft.com/en-us/azure/foundry/agents/faq):

> *"The agent subnet can't be shared by multiple Foundry resources. Each Foundry resource must use a dedicated agent subnet."*

**Impact of delegation**: A delegated subnet **cannot host Private Endpoints**. Azure blocks this — you cannot create a PE in a subnet that is delegated to another service.

#### Subnet 2: Backend/PE Subnet (`172.16.1.0/24`)

This subnet has **no delegation** and has `privateEndpointNetworkPolicies: Disabled` — which is the setting that tells Azure *"allow Private Endpoints to be created in this subnet."*

This subnet hosts the 3 Private Endpoints that agent compute needs to reach Cosmos DB, Storage, and Search.

#### What Does Microsoft's Official Template Do?

The official [15-private-network-standard-agent-setup](https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/15-private-network-standard-agent-setup) template also creates exactly **two subnets**:

> *"Two subnets are needed:*  
> *- Agent Subnet (e.g., 192.168.0.0/24): Hosts Agent client for Agent workloads, delegated to Microsoft.App/environments.*  
> *- Private endpoint Subnet (e.g., 192.168.1.0/24): Hosts private endpoints"*

#### Summary: Why Two Subnets

| Reason | Detail |
|--------|--------|
| Azure requirement | Agent subnet MUST be delegated to `Microsoft.App/environments` |
| Delegation exclusivity | Delegated subnets CANNOT host Private Endpoints |
| PE needs undelegated subnet | Private Endpoints can only be placed in non-delegated subnets with PE policies disabled |
| Microsoft's own template does the same | Official Foundry samples use the identical 2-subnet pattern |

---

## 3. Why Duplicate Private Endpoints?

### The Short Answer

When AI agent compute runs in **Foundry VNet (Subscription A)** and tries to reach a Cosmos DB PE that lives in the **Deployment VNet (Subscription B)** through VNet peering, Cosmos DB rejects the traffic with a **403 error**: *"Traffic is not from an approved private endpoint."*

The fix: create **a second set of PEs in the Foundry VNet** so the traffic comes from a PE that is local to where the agent compute runs.

### The Detailed Explanation

#### How Private Endpoints Work

When you create a Private Endpoint for Cosmos DB, Azure:
1. Creates a **network interface (NIC)** in your subnet with a private IP
2. Registers that NIC as an **"approved" source** on the Cosmos DB service
3. Only traffic arriving **through that specific NIC** is considered "from an approved PE"

#### What Happens with VNet Peering Alone

```
Agent Compute (Foundry VNet, 172.16.x.x)
    │
    │ VNet Peering
    ▼
Cosmos DB PE NIC (Deployment VNet, 10.0.2.x)
    │
    ▼
Cosmos DB Service: "Is this traffic from MY PE NIC?" 
    → The traffic arrives from 172.16.x.x, routed through peering
    → Cosmos DB sees it as NOT from the PE NIC in 10.0.2.x
    → RESULT: 403 "Traffic is not from an approved private endpoint"
```

**Why does this happen?** The PE NIC lives at IP `10.0.2.x` in the deployment VNet. When agent compute at `172.16.0.x` sends traffic through VNet peering, the **source IP is still 172.16.0.x**, not 10.0.2.x. Cosmos DB checks "did this traffic come through my approved PE NIC?" — and the answer is no.

#### What Happens with Duplicate PEs

```
Agent Compute (Foundry VNet, 172.16.0.x)
    │
    │ Direct (same VNet)
    ▼
Cosmos DB PE NIC (Foundry VNet backend subnet, 172.16.1.x)
    │
    ▼
Cosmos DB Service: "Is this traffic from MY PE NIC?" 
    → Traffic arrives through the PE NIC at 172.16.1.x
    → This NIC IS an approved PE
    → RESULT: ✓ Access granted
```

By creating a PE in the Foundry VNet's backend subnet, the traffic goes directly to a **local PE NIC** instead of crossing the peering boundary. Cosmos DB sees it as coming from an approved PE.

#### Which Services Need Duplicate PEs?

All three BYO (Bring Your Own) resources that the capability host connects to:

| Service | PE Group ID | Why Needed |
|---------|-------------|------------|
| **Cosmos DB** | `Sql` | Stores agent threads, conversation history, agent definitions |
| **Azure Storage** | `blob` | Stores files uploaded by developers and end-users |
| **Azure AI Search** | `searchService` | Stores vector embeddings for file search |

#### What About the AI Services PE?

We do NOT create a duplicate PE for AI Services in the Foundry VNet because:
- AI Services already lives in the Foundry subscription — agent compute reaches it directly
- The AI Services PE in the deployment VNet is for the **deployment-side** resources (App Service, etc.) to reach AI Services

#### When Are Duplicate PEs NOT Needed?

- **Same-subscription**: If the Foundry and deployment resources are in the same subscription and same VNet, there is only one set of PEs — no duplicates needed
- **New Foundry (WAF mode)**: Everything is in one subscription and one VNet, so no cross-VNet PE issue exists

---

## 4. Is Cosmos DB Mandatory? Can We Skip It?

### Answer: YES, Cosmos DB is MANDATORY. You CANNOT skip it.

### Evidence from Microsoft Documentation

**From the [Capability Hosts documentation](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/capability-hosts):**

The project capability host requires THREE connections — all of them:

| Property | Purpose | Azure Resource | Required? |
|----------|---------|----------------|-----------|
| `threadStorageConnections` | Stores agent definitions, conversation history and chat threads | **Azure Cosmos DB** | **YES — REQUIRED** |
| `vectorStoreConnections` | Handles vector storage for retrieval and search | Azure AI Search | **YES — REQUIRED** |
| `storageConnections` | Manages file uploads and blob storage | Azure Storage Account | **YES — REQUIRED** |

**From the [Virtual Networks troubleshooting](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/virtual-networks#template-deployment-errors):**

> *"CreateCapabilityHostRequestDto is invalid: Agents CapabilityHost supports a single, non empty value for vectorStoreConnections property."*  
> *"Agents CapabilityHost supports a single, non empty value for storageConnections property."*  
> *"Agents CapabilityHost supports a single, non empty value for threadStorageConnections property."*  
>  
> **Solution**: *"Providing all connections to all Bring-your-Own (BYO) resources, requires connections to all BYO resources. **You can't create a secured standard agent in Foundry without all three resources provided.**"*

**From the [foundry-samples README](https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/15-private-network-standard-agent-setup):**

> *"The required Bring Your Own Resources include:*
> - *BYO File Storage: All files uploaded by developers or end-users are stored in the customer's Azure Storage account.*
> - *BYO Search: All vector stores created by the agent leverage the customer's Azure AI Search resource.*
> - *BYO Thread Storage: All customer messages and conversation history will be stored in the customer's own Azure Cosmos DB account."*

### What Does Cosmos DB Actually Store?

During capability host provisioning, **three Cosmos DB containers are automatically created** per project:

1. `<projectWorkspaceId>-thread-message-store` — All conversation messages
2. `<projectWorkspaceId>-system-thread-message-store` — System-level thread messages  
3. `<projectWorkspaceId>-agent-entity-store` — Agent definitions and configurations

### What Happens If You Try Without Cosmos DB?

The capability host creation will **fail** with the error:
> *"Agents CapabilityHost supports a single, non empty value for threadStorageConnections property."*

There is no way to create a standard agent setup without Cosmos DB. The API validates that all three connections (Cosmos DB, Storage, Search) are provided and non-empty.

### Cosmos DB Throughput Requirement

From the [Use Your Own Resources documentation](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/use-your-own-resources):

> *"Your existing Azure Cosmos DB for NoSQL account must have a total throughput limit of at least 3000 RU/s. Three containers will be provisioned, each requiring 1000 RU/s."*

> *"Insufficient RU/s capacity in the Cosmos DB account causes capability host provisioning failures during deployment."*

---

## 5. Is AI Search Mandatory? Can We Skip It?

### Answer: YES, AI Search is MANDATORY. You CANNOT skip it.

The same rule applies. The capability host API requires `vectorStoreConnections` to be non-empty. Even if your agents don't use the File Search tool, the capability host still needs the connection configured.

From the troubleshooting docs:
> *"Agents CapabilityHost supports a single, non empty value for vectorStoreConnections property."*

**All three — Cosmos DB, Storage, and AI Search — are mandatory for the standard (private networking) agent setup. None can be omitted.**

---

## 6. Complete Resource Comparison: WAF vs WAF + Existing Foundry

### Resources Created in WAF Mode (New Foundry, Same Subscription)

| Resource Category | Resource | Created By |
|------------------|----------|------------|
| **Networking** | | |
| | VNet (`vnet-{suffix}`) with ~6 subnets | `virtualNetwork.bicep` |
| | 7 Private DNS Zones | AVM `private-dns-zone` module |
| | Bastion Host + Public IP | AVM `bastion-host` module |
| | Virtual Machine (jumpbox) | AVM `virtual-machine` module |
| **AI Services** | | |
| | AI Services Account (`aif-{suffix}`) with `networkInjections` | AVM `cognitive-services/account` module |
| | AI Services PE (in deployment VNet) | AVM `private-endpoint` module |
| | AI Project | `ai-project.bicep` |
| | Model Deployment (GPT-4o) | Created within AI Services Account |
| **Data Services** | | |
| | Cosmos DB (NoSQL) + PE | AVM `document-db/database-account` |
| | Storage Account + PE | AVM `storage/storage-account` |
| | AI Search + PE | `Microsoft.Search/searchServices` |
| | Key Vault + PE | AVM `key-vault/vault` |
| **Compute** | | |
| | Container Apps Environment | AVM `app/managed-environment` |
| | Backend App Service | `Microsoft.Web/sites` |
| | Frontend App Service | `Microsoft.Web/sites` |
| **Agent Setup** | | |
| | Capability Host (project-level only) | `add-project-capability-host.bicep` |
| | Project Connections (Search, Storage, Cosmos) | `aifp-connections.bicep` |

**Total Private Endpoints in WAF mode: ~6** (AI Services, Cosmos DB, Storage, Search, Key Vault, plus any for Log Analytics if monitoring enabled)

### ADDITIONAL Resources Created in WAF + EXP Cross-Subscription Mode

Everything from WAF mode PLUS these additional resources:

| Resource Category | Resource | Created By | Why Needed |
|------------------|----------|------------|------------|
| **Cross-Sub Networking** | | | |
| | Foundry VNet (`vnet-agent-{suffix}`, 172.16.0.0/16) | `cross-subscription-vnet.bicep` | Agent subnet must be in same subscription as AI Services |
| | Agent Subnet (172.16.0.0/24, delegated) | `cross-subscription-vnet.bicep` | For agent compute injection |
| | Backend Subnet (172.16.1.0/24, undelegated) | `cross-subscription-vnet.bicep` | For hosting duplicate PEs |
| | Agent NSG (deny SSH/RDP outbound) | `cross-subscription-vnet.bicep` | WAF security requirement |
| | Backend NSG (deny SSH/RDP outbound) | `cross-subscription-vnet.bicep` | WAF security requirement |
| | VNet Peering: Foundry → Deployment | `cross-subscription-vnet.bicep` | Bidirectional connectivity |
| | VNet Peering: Deployment → Foundry | `main.bicep` (peeringToFoundryVNet) | Bidirectional connectivity |
| | DNS Zone links to Foundry VNet (x7) | `main.bicep` (union pattern in DNS module) | DNS resolution from Foundry VNet |
| **Duplicate PEs** | | | |
| | Cosmos DB PE in Foundry VNet | `foundry-vnet-private-endpoints.bicep` | 403 "not from approved PE" fix |
| | Storage PE in Foundry VNet | `foundry-vnet-private-endpoints.bicep` | 403 "not from approved PE" fix |
| | Search PE in Foundry VNet | `foundry-vnet-private-endpoints.bicep` | 403 "not from approved PE" fix |
| | 3x DNS Zone Groups for above PEs | `foundry-vnet-private-endpoints.bicep` | Register PE IPs in DNS |
| **AI Services Update** | | | |
| | existingAiServicesNetworking (PUT update) | `ai-services-account-networking.bicep` | Add networkInjections + disable public access |
| | AI Services PE in Deployment VNet | `main.bicep` (existingAiServicesPrivateEndpoint) | Deployment-side access to AI Services |
| | AI Services PE DNS Zone Group (3 zones) | `main.bicep` | DNS for AI Services PE |
| **Capability Host** | | | |
| | Account-Level Capability Host with `customerSubnet` | `add-project-capability-host.bicep` | Enable VNet injection for agent compute |

**Total ADDITIONAL Private Endpoints in WAF + EXP: 4** (3 duplicate PEs in Foundry VNet + 1 AI Services PE in deployment VNet)

### Side-by-Side Summary

| Aspect | WAF (New Foundry) | WAF + EXP (Existing Foundry, Cross-Sub) |
|--------|-------------------|----------------------------------------|
| VNets | 1 (deployment) | 2 (deployment + Foundry) |
| Subnets for agents | 1 (in deployment VNet) | 1 (in Foundry VNet) |
| Subnets for PEs | 1 (backend in deployment) | 2 (backend in both VNets) |
| VNet Peering | None | Bidirectional |
| DNS Zone VNet Links | 7 (one per zone) | 14 (two per zone — both VNets) |
| NSGs | From deployment VNet | Deployment VNet NSGs + 2 in Foundry VNet |
| Private Endpoints | ~6 (all in deployment VNet) | ~10 (6 in deployment + 4 cross-sub) |
| AI Services Account | Created new (AVM handles networking) | Existing — updated via PUT (preserve all properties) |
| Account Cap Host | Created by AVM module | Created explicitly by our module |
| Cosmos DB `networkAclBypass` | `None` | `AzureServices` (needed for cap host provisioning) |

---

## 7. Our Journey: What We Tried and What Errors We Faced

This section documents the iterative process of making WAF + Existing Foundry work, including every error encountered and how it was resolved.

### Phase 1: Initial Implementation — NetworkInjections in Same VNet

**Goal**: Add WAF networking to the `existingAiFoundryAiServices` path, matching what the AVM module does for new Foundry.

**What we tried**: Use the deployment VNet's agent subnet for `networkInjections` on the existing AI Services account.

**Error encountered**:
> `networkInjections` requires the subnet to be in the **same subscription** as the AI Services account.

Our deployment VNet was in Subscription B, but the AI Services account was in Subscription A. Azure's control plane requires the agent subnet to be in the same subscription as the Cognitive Services account — this is a hard platform constraint.

**Lesson learned**: Cross-subscription means we MUST create networking infrastructure in the Foundry's subscription.

---

### Phase 2: Cross-Subscription VNet — Address Space Overlap

**Goal**: Create a VNet in the Foundry subscription and peer it to the deployment VNet.

**What we tried**: Used `10.1.0.0/16` as the address space for the Foundry VNet.

**Error encountered**:
> **BCP120** — VNet address spaces overlap. `10.1.0.0/16` is inside `10.0.0.0/8` (the deployment VNet's address space).

Azure requires that peered VNets have **non-overlapping** address spaces. Since we used `10.0.0.0/8` (the entire Class A range) for the deployment VNet, any address starting with `10.x.x.x` would overlap.

**Solution**: Switched to `172.16.0.0/16` — a Class B private range from RFC 1918 that does not overlap with `10.0.0.0/8`.

**Lesson learned**: When choosing VNet address spaces for peering, always check for range containment, not just exact matches. `10.1.0.0/16` is a subset of `10.0.0.0/8`.

---

### Phase 3: BCP120 Error on Peering Resource

**Goal**: Create bidirectional VNet peering.

**What we tried**: Referenced the deployment VNet using a `module` output's `resourceId` for the parent of the peering resource.

**Error encountered**:
> **BCP120** — The peering resource requires a compile-time name for the parent VNet, but module outputs are runtime values.

**Solution**: Used an `existing` resource reference for the deployment VNet instead of relying on the module output. This gives Bicep a compile-time resource name to use as the parent:

```bicep
resource deploymentVNet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = if (...) {
  name: virtualNetworkResourceName  // compile-time string parameter
}
resource peeringToFoundryVNet '...' = if (...) {
  parent: deploymentVNet  // works because name is known at compile time
}
```

**Lesson learned**: Bicep peering resources need compile-time parent names. Use `existing` resource references, not module output resource IDs.

---

### Phase 4: Agent Compute Using Public IP Instead of VNet

**Goal**: Agent compute should run inside the VNet (private), not on public IPs.

**Symptom**: After deploying `networkInjections`, the agents were still making calls from public IPs. Services were rejecting traffic because it came from the internet, not from the private network.

**Root cause**: The `customerSubnet` property was missing from the **account-level capability host**. Without it, Azure defaults to Microsoft-managed networking (which uses public IPs).

**What we tried first**: Setting `customerSubnet` on the project-level capability host.

**Problem**: The Bicep type definition for `Microsoft.CognitiveServices/accounts/projects/capabilityHosts` does NOT expose the `customerSubnet` property. It only exists on the account-level `Microsoft.CognitiveServices/accounts/capabilityHosts`.

**Solution**: 
1. Set `createAccountCapabilityHost: true` for existing Foundry accounts
2. Pass the `customerSubnetResourceId` to the account-level capability host
3. The project-level host inherits the subnet setting from the account level

**Lesson learned**: `customerSubnet` MUST be set at the account level. It is NOT available at the project level. The AVM module handles this automatically for new accounts, but for existing accounts we must create the account-level host explicitly.

---

### Phase 5: 403 "Traffic is Not from an Approved Private Endpoint"

**Goal**: Agent compute in the Foundry VNet needs to reach Cosmos DB, Storage, and Search (which have PEs in the deployment VNet).

**Error encountered**:
> **HTTP 403**: *"Traffic is not from an approved private endpoint"*

**What we expected**: VNet peering allows network traffic between VNets, so agent compute should be able to reach PEs in the deployment VNet.

**What actually happened**: While VNet peering does carry the traffic, the **service-side validation** at Cosmos DB checks whether the traffic arrives through an **approved PE NIC**. The PE NIC lives in the deployment VNet (10.0.2.x). Traffic from the Foundry VNet (172.16.x.x) arrives through peering — Cosmos DB sees the source as the peered network, NOT as coming through its PE NIC. So it rejects it.

**Solution**: Create **duplicate Private Endpoints** in the Foundry VNet's backend subnet:
- `pep-cosmos-foundry-{suffix}` → Cosmos DB
- `pep-blob-foundry-{suffix}` → Storage Account  
- `pep-search-foundry-{suffix}` → AI Search

Each with DNS zone groups pointing to the central DNS zones (in the deployment subscription).

**Lesson learned**: VNet peering provides network reachability, but it does NOT satisfy the service-side "approved PE" check. Each VNet that needs to access a private service must have its OWN PE for that service.

---

### Phase 6: Capability Host Provisioning Fails — Cosmos DB Access

**Goal**: Capability host should provision successfully and create Cosmos DB containers.

**Error encountered**: Capability host creation failed with timeout/internal errors when trying to set up Cosmos DB containers.

**Root cause**: During capability host provisioning, Azure's internal control plane makes API calls to Cosmos DB to create the three containers. With `networkAclBypass: 'None'`, these internal calls were blocked.

**Solution**: Set `networkAclBypass: 'AzureServices'` on Cosmos DB **conditionally** — only when using an existing Foundry:

```bicep
networkAclBypass: useExistingAiFoundryAiProject ? 'AzureServices' : 'None'
```

For new Foundry deployments, the AVM module handles this internally, so `'None'` is fine there.

**From Microsoft's docs**:
> *"Timeout of 60000ms exceeded error when loading the Agent pages — The Foundry project has issues communicating with Azure Cosmos DB to create Agents. Verify connectivity to Azure Cosmos DB (Private Endpoint and DNS)."*

**Lesson learned**: When Azure's own services need to access your private Cosmos DB during provisioning, `AzureServices` bypass must be enabled. This is a known requirement for standard agent setup.

---

### Phase 7: Bicep PUT Overwrites Existing Properties

**Goal**: Update the existing AI Services account to add `networkInjections` and disable public access.

**Error encountered**: After deploying the networking update, the AI Services account lost its `customSubDomainName`, `identity` configuration, `tags`, etc.

**Root cause**: Bicep's `resource` declaration performs a full **PUT** (not PATCH). If you declare a resource and omit a writable property, Azure resets it to the default value. This means:
- If you omit `customSubDomainName` → it gets cleared (and once cleared, cannot be set again)
- If you omit `identity` → user-assigned identities are removed
- If you omit `tags` → all tags are removed
- If you omit `networkAcls` → network ACLs are reset

**Solution**: Created `ai-services-account-networking.bicep` that accepts EVERY writable property as a parameter, sourced from the `existing` resource reference in main.bicep:

```bicep
// Read ALL properties from the existing account and pass them through
params: {
  name: existingAiFoundryAiServices!.name
  location: existingAiFoundryAiServices!.location
  kind: existingAiFoundryAiServices!.kind
  skuName: existingAiFoundryAiServices!.sku.name
  customSubDomainName: existingAiFoundryAiServices!.properties.customSubDomainName
  identityType: existingAiFoundryAiServices!.identity.type
  userAssignedIdentityResourceIds: objectKeys(existingAiFoundryAiServices!.identity.?userAssignedIdentities ?? {})
  // ... all other properties preserved
}
```

**Lesson learned**: Always preserve ALL writable properties when doing a Bicep PUT update on an existing resource. Read them from the `existing` reference and pass them back.

---

### Summary: Error Timeline

| Phase | Error / Problem | Root Cause | Fix |
|-------|----------------|------------|-----|
| 1 | networkInjections fails cross-subscription | Subnet must be in same sub as AI Services | Create Foundry VNet in Foundry subscription |
| 2 | BCP120 address space overlap | `10.1.0.0/16` is inside `10.0.0.0/8` | Use `172.16.0.0/16` instead |
| 3 | BCP120 on peering parent | Module outputs are runtime values | Use `existing` resource reference |
| 4 | Agent compute uses public IPs | `customerSubnet` missing from account cap host | Set `customerSubnet` on account-level host |
| 5 | 403 "not from approved PE" | Cross-VNet PE traffic not recognized | Create duplicate PEs in Foundry VNet |
| 6 | Cap host provisioning fails | Cosmos DB blocks Azure internal calls | Set `networkAclBypass: AzureServices` |
| 7 | PUT wipes existing properties | Bicep resource PUT overwrites all | Preserve every property via existing reference |

---

## 8. Extra Resources & Cost from Our Changes

This section lists only the **new resources and configuration changes introduced by this branch** (`psl-pocprivatev4`) compared to `dev-v4`. These are the resources and modifications we added — not the ones that already existed for WAF or WAF + EXP.

> **Disclaimer**: Cost estimates are approximate, based on publicly available Azure Pay-As-You-Go pricing (East US 2 region, mid-2025). Actual costs vary by region, reserved instances, and enterprise agreements.

### 8.1 New Resources Added for WAF (both new and existing Foundry)

These resources were **not present in `dev-v4`** and are deployed for all WAF deployments (`enablePrivateNetworking = true`):

| # | New Resource | Module / File | Condition | Purpose | Est. Monthly Cost |
|---|-------------|---------------|-----------|---------|-------------------|
| 1 | **Agent Subnet** (`10.0.6.0/24`, delegated to `Microsoft.App/environments`) | `virtualNetwork.bicep` | `enablePrivateNetworking` | Dedicated subnet for AI Foundry agent compute (networkInjections) | Free (part of VNet) |
| 2 | **Agent Subnet NSG** (`nsg-agent`, deny SSH/RDP outbound) | `virtualNetwork.bicep` | `enablePrivateNetworking` | WAF security hardening for agent subnet | Free |
| 3 | **AI Search Private Endpoint** (`pep-search-{suffix}`) | `main.bicep` (searchServiceUpdate) | `enablePrivateNetworking` | Was commented out in dev-v4 due to connectivity issues — now fixed and enabled | **~$7.30/mo** |
| 4 | **AI Search `publicNetworkAccess: Disabled`** | `main.bicep` (searchServiceUpdate) | `enablePrivateNetworking` | Was forced `Enabled` in dev-v4 — now correctly disabled for WAF | Free (config) |
| 5 | **Storage Connection** to AI Project (`aifp-st-connection-{suffix}`) | `aifp-connections.bicep` | `enablePrivateNetworking` | Required for capability host — connects AI project to Storage Account | Free (config) |
| 6 | **Cosmos DB Connection** to AI Project (`aifp-cosmos-connection-{suffix}`) | `aifp-connections.bicep` | `enablePrivateNetworking` | Required for capability host — connects AI project to Cosmos DB | Free (config) |
| 7 | **Capability Host** (project-level + account-level) | `add-project-capability-host.bicep` | `enablePrivateNetworking` | Creates capability host with BYO resource connections for agent runtime | Free (config) |

### 8.2 New Resources Added for WAF + EXP (Existing Foundry Cross-Subscription)

These resources are deployed **only** when `existingAiFoundryAiProjectResourceId` points to AI Services in a **different subscription**:

| # | New Resource | Module / File | Deployed To | Purpose | Est. Monthly Cost |
|---|-------------|---------------|-------------|---------|-------------------|
| 1 | **Foundry VNet** (`vnet-agent-{suffix}`, 172.16.0.0/16) | `cross-subscription-vnet.bicep` | Foundry sub | Agent subnet must be in same sub as AI Services account | Free |
| 2 | **Agent Subnet** (172.16.0.0/24, delegated) | `cross-subscription-vnet.bicep` | Foundry sub | For agent compute networkInjections | Free |
| 3 | **Backend/PE Subnet** (172.16.1.0/24, undelegated) | `cross-subscription-vnet.bicep` | Foundry sub | Hosts duplicate PEs (delegated subnet can't have PEs) | Free |
| 4 | **2 NSGs** (Agent + Backend, deny SSH/RDP outbound) | `cross-subscription-vnet.bicep` | Foundry sub | WAF security hardening | Free |
| 5 | **VNet Peering: Foundry → Deployment** | `cross-subscription-vnet.bicep` | Foundry sub | Cross-subscription network connectivity | **~$0.01/GB** |
| 6 | **VNet Peering: Deployment → Foundry** | `main.bicep` (peeringToFoundryVNet) | Deployment sub | Reverse direction peering | **~$0.01/GB** |
| 7 | **7 DNS Zone Links to Foundry VNet** | `main.bicep` (union pattern in DNS module) | Deployment sub | DNS resolution from Foundry VNet for all private endpoints | Free |
| 8 | **AI Services Networking Update** (PUT) | `ai-services-account-networking.bicep` | Foundry sub | Adds `networkInjections` + `publicNetworkAccess: Disabled` to existing account | Free (config) |
| 9 | **AI Services PE** (`pep-{aiServicesName}`) | `main.bicep` (existingAiServicesPrivateEndpoint) | Deployment sub | Deployment-side private access to existing AI Services | **~$7.30/mo** |
| 10 | **AI Services PE DNS Zone Group** (3 zones: cognitiveservices, openai, ai.azure.com) | `main.bicep` (existingAiServicesPeDnsZoneGroup) | Deployment sub | DNS registration for AI Services PE | Free |
| 11 | **Cosmos DB PE in Foundry VNet** (`pep-cosmos-foundry-{suffix}`) | `foundry-vnet-private-endpoints.bicep` | Foundry sub | Duplicate PE — fixes 403 "not from approved PE" | **~$7.30/mo** |
| 12 | **Storage PE in Foundry VNet** (`pep-blob-foundry-{suffix}`) | `foundry-vnet-private-endpoints.bicep` | Foundry sub | Duplicate PE — fixes 403 "not from approved PE" | **~$7.30/mo** |
| 13 | **Search PE in Foundry VNet** (`pep-search-foundry-{suffix}`) | `foundry-vnet-private-endpoints.bicep` | Foundry sub | Duplicate PE — fixes 403 "not from approved PE" | **~$7.30/mo** |

### 8.3 Configuration Changes to Existing Resources

These are modifications to resources that already existed in `dev-v4`:

| Resource | What We Changed | Why |
|----------|----------------|-----|
| **Private DNS Zones** | Changed from excluding AI-related zones for existing Foundry → deploying ALL 7 zones always, with `union()` pattern to conditionally add Foundry VNet links | Existing Foundry also needs DNS zones; Foundry VNet needs links for PE resolution |
| **AI Search (searchServiceUpdate)** | Re-enabled `publicNetworkAccess: Disabled` + un-commented and enabled private endpoint | Was broken in dev-v4 (forced public, PEs commented out); we fixed the connectivity issue |
| **Cosmos DB** | Changed `networkAclBypass: 'None'` → `useExistingAiFoundryAiProject ? 'AzureServices' : 'None'` | Azure internal calls during capability host provisioning must reach Cosmos DB |
| **AI Project Connections** | Added Storage + Cosmos DB connections alongside existing Search connection | Capability host requires all 3 BYO resource connections |
| **AI Services (new Foundry path)** | Added `networkInjections` with agent subnet | Enables agent compute to run inside VNet instead of on public IPs |

### 8.4 Cost Summary of Our Changes

| Category | Items | Est. Monthly Cost |
|----------|-------|-------------------|
| **WAF (all deployments)** | | |
| AI Search PE (was missing) | 1 PE | **~$7.30/mo** |
| Agent subnet + NSG | Network config | Free |
| Connections + Capability Host | Config resources | Free |
| **WAF subtotal** | | **~$7.30/mo** |
| | | |
| **WAF + EXP additional (cross-subscription)** | | |
| Foundry VNet + 2 subnets + 2 NSGs | Network infra | Free |
| 2 VNet Peerings | Data transfer | **~$1–10/mo** (depends on traffic) |
| 7 DNS Zone Links | DNS config | Free |
| AI Services PE (deployment VNet) | 1 PE | **~$7.30/mo** |
| 3 Duplicate PEs in Foundry VNet (Cosmos, Storage, Search) | 3 PEs | **~$21.90/mo** |
| AI Services Networking Update + DNS Zone Group | Config resources | Free |
| **WAF + EXP subtotal** | | **~$30–40/mo** |
| | | |
| **Total cost of our changes** | | |
| WAF deployment | | **~$7/mo** |
| WAF + EXP deployment | | **~$37–47/mo** |

### 8.5 New Custom Modules Created

| Module | Purpose | Used By |
|--------|---------|---------|
| `cross-subscription-vnet.bicep` | Creates Foundry VNet (172.16.0.0/16) with 2 subnets, 2 NSGs, and peering to deployment VNet | WAF + EXP only |
| `ai-services-account-networking.bicep` | PUT update on existing AI Services to add `networkInjections` and disable public access, preserving all existing properties | WAF + EXP only |
| `add-project-capability-host.bicep` | Creates account-level and project-level capability hosts with BYO connections and `customerSubnet` | All WAF deployments |
| `foundry-vnet-private-endpoints.bicep` | Creates 3 duplicate PEs (Cosmos, Storage, Search) + DNS zone groups in Foundry VNet | WAF + EXP only |

### 8.6 Why VNet Peering? Why Not Use a Single Set of Private Endpoints?

#### Why We Need VNet Peering

In the cross-subscription scenario, we have two separate VNets in two different subscriptions:

- **Deployment VNet** (10.0.0.0/8) in Subscription B — where Cosmos DB, Storage, Search, Key Vault, and the frontend/backend apps live
- **Foundry VNet** (172.16.0.0/16) in Subscription A — where AI Foundry's agent compute runs (because the agent subnet must be in the same subscription as the AI Services account)

Without VNet peering, these two networks are completely isolated — they cannot communicate at all. VNet peering creates a **direct, low-latency, high-bandwidth link** between the two VNets across subscriptions.

**What VNet peering enables:**
- Agent compute (Foundry VNet) can reach the backend Container App (Deployment VNet)
- The backend app (Deployment VNet) can call AI Services endpoints that resolve to PEs in the Foundry VNet
- DNS queries flow through linked zones across both VNets
- Bidirectional traffic for runtime agent operations

**Without peering**, the only alternative would be routing traffic over the public internet — which defeats the purpose of private networking entirely.

#### Why We Can't Use Just the Deployment VNet's Private Endpoints

This is the key question: if we have VNet peering, and PEs for Cosmos DB, Storage, and Search already exist in the Deployment VNet, why not just let the Foundry VNet's agent compute reach those PEs through peering?

**The answer: Azure services reject cross-VNet PE traffic with a 403 error.**

Here's what happens step by step:

```
1. Agent compute (172.16.0.x in Foundry VNet) wants to reach Cosmos DB
2. DNS resolves cosmos-xxxxx.documents.azure.com → 10.0.2.x (PE NIC in Deployment VNet)
3. Traffic flows through VNet peering from 172.16.0.x → 10.0.2.x
4. The PE NIC at 10.0.2.x forwards the request to Cosmos DB service
5. Cosmos DB checks: "Did this traffic arrive through MY approved PE NIC?"
6. The traffic originated from 172.16.0.x, not from the PE NIC's own network interface
7. Cosmos DB says NO → 403 "Traffic is not from an approved private endpoint"
```

**Why does this happen?** When Azure creates a Private Endpoint, it registers the PE's NIC as an "approved source" on the service. The service validates that incoming traffic physically arrived **through that specific NIC**. Traffic arriving via VNet peering has a different source IP — the PE NIC sees it as forwarded traffic, not direct traffic, so the service rejects it.

**The fix: create duplicate PEs in the Foundry VNet**

```
1. Agent compute (172.16.0.x in Foundry VNet) wants to reach Cosmos DB
2. DNS resolves cosmos-xxxxx.documents.azure.com → 172.16.1.x (PE NIC in Foundry VNet)
3. Traffic goes directly to the LOCAL PE NIC at 172.16.1.x (same VNet, no peering)
4. Cosmos DB checks: "Did this traffic arrive through MY approved PE NIC?"
5. YES — it came through the PE NIC at 172.16.1.x which IS an approved PE
6. Access granted ✓
```

By creating PEs in the Foundry VNet's backend subnet (172.16.1.0/24), agent compute reaches a **local** PE NIC instead of crossing the peering boundary. This satisfies Azure's service-side validation.

#### So What Is VNet Peering Actually Used For?

If each VNet has its own PEs, you might ask: why do we still need peering? Peering is still essential for:

1. **DNS Zone Links** — The Private DNS Zones live in the Deployment subscription. The Foundry VNet needs VNet links to those zones so DNS queries from agent compute resolve to the correct PE IPs (the ones in the Foundry VNet)
2. **Backend-to-AI-Services traffic** — The backend Container App (Deployment VNet) needs to reach AI Services, which may have endpoints that resolve through the Foundry VNet
3. **Management plane** — Deployment-time operations that cross subscription boundaries during resource provisioning

#### Summary

| Question | Answer |
|----------|--------|
| Why VNet peering? | Two isolated VNets in different subscriptions need a network path for DNS, management, and cross-service communication |
| Why not use Deployment VNet PEs from Foundry VNet? | Azure rejects cross-VNet PE traffic with 403 — services validate traffic came through their own PE NIC |
| Why duplicate PEs in Foundry VNet? | Local PEs satisfy the "approved PE" check — agent compute reaches a PE NIC in its own VNet |
| What does peering provide after duplicate PEs? | DNS zone resolution, management-plane connectivity, and cross-VNet service communication |

---

## 9. Official Microsoft Documentation References

| Topic | URL | Key Takeaway |
|-------|-----|-------------|
| Private Networking for Agent Service | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/virtual-networks | Two subnets needed: agent (delegated) + PE (undelegated). All 3 BYO resources required. |
| Capability Hosts Concepts | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/capability-hosts | `threadStorageConnections` (Cosmos), `vectorStoreConnections` (Search), `storageConnections` (Storage) — ALL required |
| Use Your Own Resources | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/use-your-own-resources | Cosmos DB needs 3000 RU/s minimum. Three containers per project. |
| Agent Service FAQ | https://learn.microsoft.com/en-us/azure/foundry/agents/faq | VNet peering supported. Subnet dedicated per Foundry account. Same region required. |
| Official Bicep Template | https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/15-private-network-standard-agent-setup | Reference implementation. 2 subnets, PEs for all services, capability hosts, RBAC. |
| Troubleshooting Errors | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/virtual-networks#troubleshooting-guide | Error messages for missing connections, wrong subnet ranges, subnet delegation issues |

### Key Quotes from Microsoft Documentation

**On mandatory resources:**
> *"You can't create a secured standard agent in Foundry without all three resources provided."*
> — [Virtual Networks Troubleshooting](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/virtual-networks#template-deployment-errors)

**On two subnets:**
> *"Two subnets are needed: Agent Subnet — Hosts Agent client for Agent workloads, delegated to Microsoft.App/environments. Private endpoint Subnet — Hosts private endpoints."*
> — [foundry-samples README](https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/15-private-network-standard-agent-setup)

**On subnet exclusivity:**
> *"The agent subnet can't be shared by multiple Foundry resources. Each Foundry resource must use a dedicated agent subnet."*
> — [FAQ](https://learn.microsoft.com/en-us/azure/foundry/agents/faq)

**On BYO resources:**
> *"By bundling these BYO features (file storage, search, and thread storage), the standard setup guarantees that your deployment is secure by default."*
> — [foundry-samples README](https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/15-private-network-standard-agent-setup)

**On VNet peering:**
> *"Yes. The virtual network is in your subscription, and you should be able to peer with any virtual network."*
> — [FAQ](https://learn.microsoft.com/en-us/azure/foundry/agents/faq)
