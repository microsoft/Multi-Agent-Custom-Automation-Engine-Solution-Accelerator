# Cross-Subscription Private Networking for AI Foundry Agents

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Problem Statement](#problem-statement)
4. [Design Constraints & Decisions](#design-constraints--decisions)
5. [Module Reference](#module-reference)
   - [cross-subscription-vnet.bicep](#1-cross-subscription-vnetbicep)
   - [foundry-vnet-private-endpoints.bicep](#2-foundry-vnet-private-endpointsbicep)
   - [ai-services-account-networking.bicep](#3-ai-services-account-networkingbicep)
   - [add-project-capability-host.bicep](#4-add-project-capability-hostbicep)
6. [Main Template Integration (main.bicep)](#main-template-integration-mainbicep)
   - [DNS Zones](#dns-zones)
   - [Cross-Subscription Detection](#cross-subscription-detection)
   - [VNet & Peering](#vnet--peering)
   - [AI Services Networking Update](#ai-services-networking-update)
   - [AI Services Private Endpoint](#ai-services-private-endpoint)
   - [Cosmos DB networkAclBypass](#cosmos-db-networkaclbypass)
   - [Capability Host](#capability-host)
   - [Foundry VNet Private Endpoints](#foundry-vnet-private-endpoints)
7. [Network Topology & IP Address Allocation](#network-topology--ip-address-allocation)
8. [DNS Resolution Flow](#dns-resolution-flow)
9. [Security Controls (WAF Alignment)](#security-controls-waf-alignment)
10. [Deployment Dependencies](#deployment-dependencies)
11. [Prerequisites & Permissions](#prerequisites--permissions)
12. [Conditional Deployment Logic](#conditional-deployment-logic)
13. [Troubleshooting](#troubleshooting)

---

## Overview

This document describes the private networking infrastructure that enables AI Foundry Agents to operate securely when the AI Foundry project (AI Services account) resides in a **different Azure subscription** from the deployment resources (Cosmos DB, Storage, Search).

The solution implements **WAF (Well-Architected Framework) aligned** network security:
- All public internet access is disabled on every service
- All service-to-service communication occurs through Private Endpoints
- VNet injection is used for agent compute via `networkInjections`
- Network Security Groups enforce lateral movement prevention
- Private DNS Zones ensure correct name resolution across both subscriptions

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `infra/modules/cross-subscription-vnet.bicep` | Creates Foundry VNet, subnets, NSGs, and peering to deployment VNet | ~154 |
| `infra/modules/foundry-vnet-private-endpoints.bicep` | Creates local Private Endpoints in Foundry VNet for Cosmos DB, Storage, Search | ~161 |
| `infra/modules/ai-services-account-networking.bicep` | PUT update on existing AI Services account for networkInjections + disabled public access | ~98 |
| `infra/modules/add-project-capability-host.bicep` | Creates account + project capability hosts with `customerSubnet` for VNet injection | ~53 |
| `infra/main.bicep` | Orchestrates all modules with conditional deployment logic | Modified sections across file |

---

## Architecture Diagram

```
 ┌─────────────────────────────────────────────────────────────────────┐
 │                    FOUNDRY SUBSCRIPTION                             │
 │                    (AI Services + AI Project)                       │
 │                                                                     │
 │  ┌─── VNet: vnet-agent-{suffix} (172.16.0.0/16) ───────────────┐  │
 │  │                                                               │  │
 │  │  ┌── agent subnet (172.16.0.0/24) ─────────────────┐        │  │
 │  │  │  Delegation: Microsoft.App/environments          │        │  │
 │  │  │  NSG: deny SSH(22) + RDP(3389) outbound          │        │  │
 │  │  │                                                   │        │  │
 │  │  │  ┌──────────────────┐                            │        │  │
 │  │  │  │  Agent Compute   │ (injected via              │        │  │
 │  │  │  │  (Cap Host)      │  networkInjections)        │        │  │
 │  │  │  └──────────────────┘                            │        │  │
 │  │  └───────────────────────────────────────────────────┘        │  │
 │  │                                                               │  │
 │  │  ┌── backend subnet (172.16.1.0/24) ────────────────┐        │  │
 │  │  │  privateEndpointNetworkPolicies: Disabled         │        │  │
 │  │  │  NSG: deny SSH(22) + RDP(3389) outbound           │        │  │
 │  │  │                                                   │        │  │
 │  │  │  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │        │  │
 │  │  │  │ PE: Cosmos  │ │ PE: Storage │ │ PE: Search │ │        │  │
 │  │  │  │ (Sql)       │ │ (blob)      │ │ (search)   │ │        │  │
 │  │  │  └──────┬──────┘ └──────┬──────┘ └─────┬──────┘ │        │  │
 │  │  └─────────┼───────────────┼───────────────┼────────┘        │  │
 │  │            │               │               │                  │  │
 │  └────────────┼───────────────┼───────────────┼──────────────────┘  │
 │               │               │               │                     │
 │  ┌────────────┴───────────────┴───────────────┴──────────────────┐  │
 │  │  AI Services Account (aif-{suffix})                            │  │
 │  │  - networkInjections: [{ scenario: 'agent', subnetArmId: ... }]│  │
 │  │  - publicNetworkAccess: Disabled                               │  │
 │  │  - Capability Host (account-level): customerSubnet set         │  │
 │  │  - Capability Host (project-level): connections wired          │  │
 │  └────────────────────────────────────────────────────────────────┘  │
 │                                                                     │
 └──────────────────────────────┬──────────────────────────────────────┘
                                │
                    VNet Peering (bidirectional)
                    ┌───────────┴───────────┐
                    │  peer-to-deployment   │ (Foundry → Deployment)
                    │  peer-to-foundry-vnet │ (Deployment → Foundry)
                    └───────────┬───────────┘
                                │
 ┌──────────────────────────────┴──────────────────────────────────────┐
 │                    DEPLOYMENT SUBSCRIPTION                          │
 │                    (App, Databases, Storage, Search)                 │
 │                                                                     │
 │  ┌─── VNet: vnet-{suffix} (10.0.0.0/8) ────────────────────────┐  │
 │  │                                                               │  │
 │  │  ┌─ backend subnet (10.0.2.0/24) ────────────────────┐      │  │
 │  │  │  Private Endpoints:                                │      │  │
 │  │  │  - PE: AI Services (account)                       │      │  │
 │  │  │  - PE: Cosmos DB (Sql)                             │      │  │
 │  │  │  - PE: Storage (blob)                              │      │  │
 │  │  │  - PE: Search (searchService)                      │      │  │
 │  │  │  - PE: Key Vault (vault)                           │      │  │
 │  │  └────────────────────────────────────────────────────┘      │  │
 │  │                                                               │  │
 │  │  ┌─ agent subnet (10.0.6.0/24) ──────────────────────┐      │  │
 │  │  │  Delegation: Microsoft.App/environments            │      │  │
 │  │  │  (Used for same-subscription scenarios only)       │      │  │
 │  │  └────────────────────────────────────────────────────┘      │  │
 │  │                                                               │  │
 │  └───────────────────────────────────────────────────────────────┘  │
 │                                                                     │
 │  ┌─ Services ───────────────────────────────────────────────────┐  │
 │  │  Cosmos DB    │ networkAclBypass: AzureServices              │  │
 │  │  Storage      │ publicNetworkAccess: Disabled                │  │
 │  │  AI Search    │ publicNetworkAccess: Disabled                │  │
 │  │  Key Vault    │ publicNetworkAccess: Disabled                │  │
 │  └──────────────────────────────────────────────────────────────┘  │
 │                                                                     │
 │  ┌─ Private DNS Zones (linked to BOTH VNets) ──────────────────┐  │
 │  │  privatelink.cognitiveservices.azure.com                     │  │
 │  │  privatelink.openai.azure.com                                │  │
 │  │  privatelink.services.ai.azure.com                           │  │
 │  │  privatelink.documents.azure.com                             │  │
 │  │  privatelink.blob.core.windows.net                           │  │
 │  │  privatelink.search.windows.net                              │  │
 │  │  privatelink.vaultcore.azure.net                             │  │
 │  └──────────────────────────────────────────────────────────────┘  │
 │                                                                     │
 └─────────────────────────────────────────────────────────────────────┘
```

---

## Problem Statement

### Scenario
An organization has:
- An **existing AI Foundry project** (AI Services account + project) in **Subscription A**
- A MACAE deployment (Cosmos DB, Storage Account, AI Search, App Service) in **Subscription B**
- A requirement for **WAF-aligned private networking** (no public internet exposure)

### Constraints Discovered During Implementation

| # | Constraint | Impact | Solution |
|---|-----------|--------|----------|
| 1 | `networkInjections` requires the agent subnet to be in the **same subscription** as the AI Services account | Cannot use deployment VNet's agent subnet for cross-subscription | Create a VNet with agent subnet in the Foundry's subscription |
| 2 | VNet address spaces must **not overlap** for peering | Initial attempt with `10.1.0.0/16` failed because it overlaps `10.0.0.0/8` | Use RFC 1918 range `172.16.0.0/16` which does not overlap |
| 3 | Services validate that traffic comes from an **approved Private Endpoint** | Agent compute in Foundry VNet, accessing PEs in deployment VNet through peering, was rejected with 403 "Traffic not from approved PE" | Create duplicate PEs in the Foundry VNet (backend subnet) |
| 4 | `customerSubnet` must be set on the **account-level** capability host | Without it, agent compute uses public IPs instead of VNet injection | Explicitly create account-level capability host with `customerSubnet` parameter |
| 5 | Cosmos DB requires `networkAclBypass: AzureServices` for existing Foundry | Capability host provisioning makes internal Azure API calls that need bypass | Conditionally set when `useExistingAiFoundryAiProject` is true |
| 6 | Bicep `resource` PUT overwrites **all writable properties** | A networking update PUT on AI Services without preserving existing properties wipes them | Read all properties from existing resource reference and pass them through as params |

---

## Design Constraints & Decisions

### Why 172.16.0.0/16?
RFC 1918 defines three private IP ranges: `10.0.0.0/8`, `172.16.0.0/12`, and `192.168.0.0/16`. The deployment VNet uses `10.0.0.0/8`. To avoid overlap (which prevents peering), the Foundry VNet uses `172.16.0.0/16`.

### Why Two Subnets in the Foundry VNet?
- **agent** (`172.16.0.0/24`): Delegated to `Microsoft.App/environments` for agent compute injection. Delegation prevents hosting Private Endpoints.
- **backend** (`172.16.1.0/24`): No delegation, `privateEndpointNetworkPolicies: Disabled` — hosts the local Private Endpoints.

### Why Duplicate Private Endpoints?
Azure services (Cosmos DB, Storage, Search) validate that incoming traffic originates from an approved Private Endpoint on their service. When agent compute in the Foundry VNet accesses a PE in the deployment VNet via peering, the service sees the traffic as "not from an approved PE" because the PE NIC lives in a different VNet. Creating PEs in both VNets ensures both locations have approved PE NICs.

### Why `privateLinkServiceConnections` (not `manualPrivateLinkServiceConnections`)?
`privateLinkServiceConnections` allows auto-approval of PE connections — even cross-subscription — when the deploying identity has the required permissions on the target resource. `manualPrivateLinkServiceConnections` would require manual approval, adding an unnecessary operational step.

### Why `networkAclBypass: AzureServices` on Cosmos DB?
When using an existing Foundry, the capability host setup involves Azure-internal API calls (control plane operations) that need to reach Cosmos DB. Without the bypass, these calls fail. For new Foundry deployments, the AVM module handles this internally, so `None` is sufficient.

---

## Module Reference

### 1. cross-subscription-vnet.bicep

**Location**: `infra/modules/cross-subscription-vnet.bicep`
**Scope**: Deploys to the Foundry subscription's resource group
**Condition**: `isExistingFoundryCrossSubscription && enablePrivateNetworking`

#### Purpose
Creates a complete VNet infrastructure in the Foundry's subscription for agent network injection.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | VNet name (e.g., `vnet-agent-{suffix}`) |
| `location` | string | Azure region (matches AI Services region) |
| `addressPrefixes` | array | VNet CIDR blocks (e.g., `['172.16.0.0/16']`) |
| `agentSubnetAddressPrefix` | string | Agent subnet CIDR (e.g., `172.16.0.0/24`) |
| `backendSubnetAddressPrefix` | string | Backend subnet CIDR (e.g., `172.16.1.0/24`) |
| `remoteVirtualNetworkId` | string | Resource ID of the deployment VNet for peering |
| `tags` | object | Resource tags |

#### Resources Created

| Resource | Type | Details |
|----------|------|---------|
| `agentNsg` | Network Security Group | Attached to agent subnet. Rule: deny TCP outbound on ports 22, 3389 |
| `backendNsg` | Network Security Group | Attached to backend subnet. Same deny rule |
| `vnet` | Virtual Network | Address space `172.16.0.0/16` with two subnets |
| `vnet/subnets[0]` (agent) | Subnet | `172.16.0.0/24`, delegated to `Microsoft.App/environments` |
| `vnet/subnets[1]` (backend) | Subnet | `172.16.1.0/24`, `privateEndpointNetworkPolicies: Disabled` |
| `peeringToDeployment` | VNet Peering | Foundry VNet → Deployment VNet, allows virtual network access + forwarded traffic |

#### Outputs

| Output | Description |
|--------|-------------|
| `resourceId` | VNet resource ID (used for DNS zone linking + reverse peering) |
| `name` | VNet name |
| `agentSubnetResourceId` | Agent subnet ID (used by `networkInjections` and `customerSubnet`) |
| `backendSubnetResourceId` | Backend subnet ID (used by `foundry-vnet-private-endpoints.bicep`) |

#### NSG Rule Explanation

```bicep
{
  name: 'deny-hop-outbound'
  properties: {
    access: 'Deny'
    destinationAddressPrefix: '*'
    destinationPortRanges: ['22', '3389']
    direction: 'Outbound'
    priority: 200
    protocol: 'Tcp'
    sourceAddressPrefix: 'VirtualNetwork'
    sourcePortRange: '*'
  }
}
```

This rule prevents **lateral movement** — if an attacker compromises a workload in the subnet, they cannot SSH or RDP to other VMs in the network. This is a **WAF security baseline** requirement.

#### Subnet Delegation

The agent subnet delegation to `Microsoft.App/environments` is required because Azure AI Foundry's agent compute uses Azure Container Apps infrastructure under the hood. The delegation gives Azure Container Apps permission to inject compute instances into this subnet.

---

### 2. foundry-vnet-private-endpoints.bicep

**Location**: `infra/modules/foundry-vnet-private-endpoints.bicep`
**Scope**: Deploys to the Foundry subscription's resource group
**Condition**: `isExistingFoundryCrossSubscription && enablePrivateNetworking`

#### Purpose
Creates Private Endpoints in the Foundry VNet's backend subnet for cross-subscription resources. This solves the "Traffic is not from an approved private endpoint" 403 error.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `location` | string | Azure region for PE resources |
| `tags` | object | Resource tags |
| `solutionSuffix` | string | Naming suffix |
| `backendSubnetResourceId` | string | Backend subnet in Foundry VNet (from `cross-subscription-vnet` output) |
| `cosmosDbAccountResourceId` | string | Target Cosmos DB resource ID (in deployment subscription) |
| `storageAccountResourceId` | string | Target Storage Account resource ID (in deployment subscription) |
| `searchServiceResourceId` | string | Target Search Service resource ID (in deployment subscription) |
| `cosmosDbDnsZoneId` | string | Private DNS Zone ID for `privatelink.documents.azure.com` |
| `blobDnsZoneId` | string | Private DNS Zone ID for `privatelink.blob.core.windows.net` |
| `searchDnsZoneId` | string | Private DNS Zone ID for `privatelink.search.windows.net` |

#### Resources Created (3 PE + 3 DNS Zone Groups)

| Resource | PE Name | Group ID | Target Service |
|----------|---------|----------|----------------|
| `cosmosDbPe` | `pep-cosmos-foundry-{suffix}` | `Sql` | Cosmos DB (NoSQL API) |
| `storageBlobPe` | `pep-blob-foundry-{suffix}` | `blob` | Storage Account (Blob) |
| `searchPe` | `pep-search-foundry-{suffix}` | `searchService` | Azure AI Search |

Each PE has:
- A `privateLinkServiceConnections` block (auto-approved cross-subscription)
- A `customNetworkInterfaceName` (e.g., `nic-cosmos-foundry-{suffix}`)
- A DNS zone group pointing to the central Private DNS Zone in the deployment subscription

#### DNS Zone Group Detail
```bicep
resource cosmosDbPeDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: cosmosDbPe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [{
      name: 'cosmos-dns-zone'
      properties: {
        privateDnsZoneId: cosmosDbDnsZoneId  // Zone lives in deployment subscription
      }
    }]
  }
}
```

The DNS zone group automatically registers the PE's private IP address as an A record in the DNS zone. Since the DNS zones are linked to both VNets, both the deployment VNet and Foundry VNet can resolve the private IP addresses of PEs in either VNet.

---

### 3. ai-services-account-networking.bicep

**Location**: `infra/modules/ai-services-account-networking.bicep`
**Scope**: Deploys to the Foundry subscription's resource group
**Condition**: `useExistingAiFoundryAiProject && enablePrivateNetworking`

#### Purpose
Performs a full PUT on the existing AI Services account to add `networkInjections` and disable `publicNetworkAccess`, while meticulously preserving all existing writable properties.

#### Critical Design: Property Preservation

Bicep's `resource` declaration performs a PUT (not PATCH). If writable properties are omitted, Azure resets them to defaults. The module accepts every writable property as a parameter, sourced from the `existing` resource reference in main.bicep:

```bicep
// In main.bicep — reading existing account properties
params: {
  name: existingAiFoundryAiServices!.name
  location: existingAiFoundryAiServices!.location
  kind: existingAiFoundryAiServices!.kind
  skuName: existingAiFoundryAiServices!.sku.name
  customSubDomainName: existingAiFoundryAiServices!.properties.customSubDomainName
  disableLocalAuth: existingAiFoundryAiServices!.properties.disableLocalAuth
  allowProjectManagement: existingAiFoundryAiServices!.properties.allowProjectManagement
  networkAcls: existingAiFoundryAiServices!.properties.networkAcls
  identityType: existingAiFoundryAiServices!.identity.type
  userAssignedIdentityResourceIds: objectKeys(existingAiFoundryAiServices!.identity.?userAssignedIdentities ?? {})
  tags: existingAiFoundryAiServices!.tags ?? {}
  agentSubnetResourceId: agentSubnetResourceIdForNetworkInjections
  publicNetworkAccess: 'Disabled'
}
```

#### Identity Dictionary Construction

User-assigned identity IDs must be formatted as a dictionary `{ "/subscriptions/.../id1": {}, "/subscriptions/.../id2": {} }`. The module converts the input array using reduce+map+union:

```bicep
var formattedUserAssignedIdentities = reduce(
  map(userAssignedIdentityResourceIds, (id) => { '${id}': {} }),
  {},
  (cur, next) => union(cur, next)
)
```

**Step-by-step**:
1. `map()` transforms `['/sub/id1', '/sub/id2']` → `[{ '/sub/id1': {} }, { '/sub/id2': {} }]`
2. `reduce()` with `union()` merges them → `{ '/sub/id1': {}, '/sub/id2': {} }`

#### networkInjections Property

```bicep
networkInjections: [
  {
    scenario: 'agent'
    subnetArmId: agentSubnetResourceId
    useMicrosoftManagedNetwork: false
  }
]
```

| Field | Value | Explanation |
|-------|-------|-------------|
| `scenario` | `'agent'` | Specifies this injection is for the Agents capability |
| `subnetArmId` | Resource ID of agent subnet | Must be in the same subscription as the AI Services account |
| `useMicrosoftManagedNetwork` | `false` | Customer-managed VNet injection instead of Microsoft-managed |

> **Note**: This property generates a BCP036 warning in Bicep because `networkInjections` is not present in the published type schema. It is a valid REST API property that works at deployment time.

---

### 4. add-project-capability-host.bicep

**Location**: `infra/modules/add-project-capability-host.bicep`
**Scope**: Deploys to the Foundry subscription's resource group
**Condition**: `enablePrivateNetworking`

#### Purpose
Creates the account-level and project-level capability hosts that enable the **Agents** feature with VNet-injected compute.

#### Account-Level Capability Host

```bicep
resource accountCapabilityHost 'Microsoft.CognitiveServices/accounts/capabilityHosts@2025-04-01-preview' = if (createAccountCapabilityHost) {
  name: accountCapHost  // 'default'
  parent: account
  properties: {
    capabilityHostKind: 'Agents'
    customerSubnet: !empty(customerSubnetResourceId) ? customerSubnetResourceId : null
  }
}
```

- **`createAccountCapabilityHost`**: Only `true` when using an existing Foundry account. For new accounts, the AVM module creates this automatically.
- **`customerSubnet`**: The agent subnet resource ID. Without this, Azure uses Microsoft-managed networking (public IPs), defeating the purpose of VNet injection.
- **`name: 'default'`**: The account-level capability host must be named `default`.

#### Project-Level Capability Host

```bicep
resource projectCapabilityHost 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview' = {
  name: projectCapHost  // 'default' for existing, 'proj-cap-host-{suffix}' for new
  parent: project
  properties: {
    capabilityHostKind: 'Agents'
    vectorStoreConnections: vectorStoreConnections    // AI Search connection
    storageConnections: storageConnections              // Storage Account connection
    threadStorageConnections: threadConnections          // Cosmos DB connection
  }
  dependsOn: [accountCapabilityHost]
}
```

- Wires the three service connections that Agents needs: AI Search (vector store), Storage (file storage), Cosmos DB (thread/conversation persistence)
- `dependsOn` ensures account-level host exists first (required by the API)
- Does **not** have `customerSubnet` — the Bicep type definition for project-level hosts doesn't expose this property; the account-level setting is inherited

---

## Main Template Integration (main.bicep)

### DNS Zones

**Location**: ~Lines 700-757

```bicep
var privateDnsZones = [
  'privatelink.cognitiveservices.azure.com'
  'privatelink.openai.azure.com'
  'privatelink.services.ai.azure.com'
  'privatelink.documents.azure.com'
  'privatelink.blob.core.windows.net'
  'privatelink.search.windows.net'
  keyVaultPrivateDNSZone
]
```

Seven Private DNS Zones are deployed, each linked to:
1. The deployment VNet (always)
2. The Foundry VNet (only when `isExistingFoundryCrossSubscription` is true)

The linking is done via the `union()` pattern:

```bicep
virtualNetworkLinks: union(
  [{ name: '...', virtualNetworkResourceId: virtualNetwork!.outputs.resourceId }],
  isExistingFoundryCrossSubscription
    ? [{ name: '...', virtualNetworkResourceId: foundryVNet!.outputs.resourceId }]
    : []
)
```

This ensures DNS resolution works from both VNets — any workload in either VNet can resolve any Private Endpoint's private IP address.

### Cross-Subscription Detection

**Location**: ~Line 773

```bicep
var isExistingFoundryCrossSubscription = useExistingAiFoundryAiProject
  && (aiFoundryAiServicesSubscriptionId != subscription().subscriptionId)
```

Compares the subscription ID extracted from the existing AI Foundry project resource ID against the current deployment subscription. When true, triggers all cross-subscription infrastructure (VNet, peering, DNS linking, Foundry VNet PEs).

### VNet & Peering

**Location**: ~Lines 778-812

**Foundry VNet** deploys to Foundry subscription scope:
```bicep
module foundryVNet 'modules/cross-subscription-vnet.bicep' = if (isExistingFoundryCrossSubscription && enablePrivateNetworking) {
  scope: resourceGroup(aiFoundryAiServicesSubscriptionId, aiFoundryAiServicesResourceGroupName)
  ...
}
```

**Reverse peering** (Deployment → Foundry) uses an `existing` resource reference:
```bicep
resource deploymentVNet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = if (...) {
  name: virtualNetworkResourceName
}
resource peeringToFoundryVNet 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-05-01' = if (...) {
  parent: deploymentVNet
  name: 'peer-to-foundry-vnet'
  ...
}
```

Both peering directions set `allowVirtualNetworkAccess: true` and `allowForwardedTraffic: true` to enable full bidirectional connectivity.

### Agent Subnet Abstraction

**Location**: ~Lines 814-817

```bicep
var agentSubnetResourceIdForNetworkInjections = isExistingFoundryCrossSubscription
  ? foundryVNet!.outputs.agentSubnetResourceId
  : virtualNetwork!.outputs.agentSubnetResourceId
```

This variable abstracts the subnet selection, allowing downstream modules (`ai-services-account-networking`, `add-project-capability-host`) to use the same parameter regardless of whether it's cross-subscription or same-subscription.

### AI Services Networking Update

**Location**: ~Lines 928-957

Calls `ai-services-account-networking.bicep` with all existing properties preserved. Dependencies:
- `existingAiFoundryAiServicesDeployments` — model deployments must complete first
- `peeringToFoundryVNet` — peering must exist before networking update

### AI Services Private Endpoint

**Location**: ~Lines 960-1012

Creates a PE for the AI Services account in the **deployment VNet** (backend subnet). This allows the deployment-side resources (App Service, etc.) to reach AI Services privately. The PE has DNS zone group registrations for all three AI Services DNS zones:
- `privatelink.cognitiveservices.azure.com`
- `privatelink.openai.azure.com`
- `privatelink.services.ai.azure.com`

### Cosmos DB networkAclBypass

**Location**: ~Line 1222

```bicep
networkAclBypass: useExistingAiFoundryAiProject ? 'AzureServices' : 'None'
```

When using an existing Foundry, Azure's control plane needs to perform internal calls to Cosmos DB during capability host setup. The `AzureServices` bypass permits these calls. For new Foundry projects, this is handled by the AVM module internally.

### Capability Host

**Location**: ~Lines 1917-1940

Calls `add-project-capability-host.bicep` with:
- `createAccountCapabilityHost: useExistingAiFoundryAiProject` — only creates account-level host for existing Foundry
- `customerSubnetResourceId: agentSubnetResourceIdForNetworkInjections` — passes the correct subnet (cross or same subscription)

Dependencies are extensive to ensure all network infrastructure is ready:
- `searchServiceUpdate`, `virtualNetwork`, `avmPrivateDnsZones`, `aiProjectConnections`, `existingAiServicesNetworking`, `existingAiServicesPrivateEndpoint`

### Foundry VNet Private Endpoints

**Location**: ~Lines 1942-1968

Calls `foundry-vnet-private-endpoints.bicep` — only for cross-subscription scenarios. Passes:
- `backendSubnetResourceId` from the Foundry VNet's backend subnet
- Resource IDs of Cosmos DB, Storage, and Search (in deployment subscription)
- DNS Zone IDs (in deployment subscription)

Dependencies: `peeringToFoundryVNet`, `addProjectCapabilityHost`

---

## Network Topology & IP Address Allocation

| VNet | Subscription | Address Space | Purpose |
|------|-------------|---------------|---------|
| `vnet-{suffix}` | Deployment | `10.0.0.0/8` | Hosts all deployment resources + PEs |
| `vnet-agent-{suffix}` | Foundry | `172.16.0.0/16` | Hosts agent compute + cross-sub PEs |

### Subnet Allocation (Foundry VNet)

| Subnet | CIDR | Delegation | PE Policies | Purpose |
|--------|------|-----------|-------------|---------|
| `agent` | `172.16.0.0/24` | `Microsoft.App/environments` | N/A | Agent compute injection |
| `backend` | `172.16.1.0/24` | None | Disabled | Private Endpoints |

### Subnet Allocation (Deployment VNet)

| Subnet | CIDR | Delegation | Purpose |
|--------|------|-----------|---------|
| `backend` | `10.0.2.0/24` | None | PEs for all services |
| `agent` | `10.0.6.0/24` | `Microsoft.App/environments` | Agent compute (same-sub only) |
| (other subnets) | Various | Various | App Service, Container Apps, etc. |

---

## DNS Resolution Flow

### Same-Subscription Flow
```
Agent in deployment VNet → queries mydb.documents.azure.com
  → Private DNS Zone (privatelink.documents.azure.com)
  → Returns private IP of PE in deployment VNet backend subnet
  → Traffic stays within VNet
```

### Cross-Subscription Flow
```
Agent in Foundry VNet → queries mydb.documents.azure.com
  → Private DNS Zone (linked to Foundry VNet)
  → Returns private IPs of PEs in BOTH VNets
  → Agent's NIC resolves to Foundry VNet PE IP (local)
  → Traffic goes directly to local PE NIC
  → Cosmos DB recognizes traffic from approved PE ✓
```

Without the Foundry VNet PEs, the agent would:
```
Agent in Foundry VNet → queries mydb.documents.azure.com
  → DNS returns deployment VNet PE IP
  → Traffic routes through VNet peering to deployment VNet PE NIC
  → Cosmos DB sees traffic NOT from an approved PE ✗
  → 403 "Traffic is not from an approved private endpoint"
```

---

## Security Controls (WAF Alignment)

| Control | Implementation | Resources Affected |
|---------|---------------|-------------------|
| Public access disabled | `publicNetworkAccess: 'Disabled'` | AI Services, Cosmos DB, Storage, Search, Key Vault |
| Private Endpoints only | PEs in both VNets with DNS zone groups | All services |
| Lateral movement prevention | NSG rules deny SSH(22) + RDP(3389) outbound | All subnets |
| VNet injection | `networkInjections` + `customerSubnet` | AI agent compute |
| No Microsoft-managed networking | `useMicrosoftManagedNetwork: false` | Agent capability host |
| DNS isolation | Private DNS Zones with VNet links only | All name resolution |
| Minimal network exposure | Per-subnet delegation where required | Agent subnets only |

---

## Deployment Dependencies

```
virtualNetwork
  ├── foundryVNet (cross-sub only)
  │     ├── peeringToFoundryVNet (reverse direction)
  │     └── foundryVNetPrivateEndpoints
  ├── avmPrivateDnsZones (linked to both VNets)
  ├── existingAiServicesNetworking
  │     ├── depends: existingAiFoundryAiServicesDeployments
  │     └── depends: peeringToFoundryVNet
  ├── existingAiServicesPrivateEndpoint
  │     └── depends: existingAiServicesNetworking
  ├── cosmosDb
  │     └── networkAclBypass: AzureServices (existing Foundry)
  ├── searchServiceUpdate
  └── addProjectCapabilityHost
        ├── depends: searchServiceUpdate
        ├── depends: virtualNetwork
        ├── depends: avmPrivateDnsZones
        ├── depends: aiProjectConnections
        ├── depends: existingAiServicesNetworking
        └── depends: existingAiServicesPrivateEndpoint
```

---

## Prerequisites & Permissions

### Required RBAC Roles

| Role | Scope | Purpose |
|------|-------|---------|
| Cognitive Services Contributor | AI Services account | Modify networking, create capability hosts |
| Network Contributor | Foundry subscription resource group | Create VNet, subnets, NSGs, peering |
| Private DNS Zone Contributor | Deployment subscription DNS zones | Link DNS zones to Foundry VNet |
| Reader | Deployment VNet | Reference for peering |

### Cross-Subscription Requirements
- The deploying identity (service principal or user) must have permissions in **both** subscriptions
- `azd` must be configured with credentials that can deploy to both subscriptions
- The Foundry resource group must already exist

---

## Conditional Deployment Logic

All cross-subscription resources are gated by conditions:

| Variable | Logic | Used By |
|----------|-------|---------|
| `useExistingAiFoundryAiProject` | `!empty(existingAiFoundryAiProjectResourceId)` | All existing Foundry modules |
| `isExistingFoundryCrossSubscription` | `useExistingAiFoundryAiProject && (subscriptionId != current)` | VNet, peering, DNS linking, Foundry PEs |
| `enablePrivateNetworking` | User parameter | All networking resources |

**Deployment matrix**:

| Scenario | VNet Created | Peering | Foundry PEs | Networking Update | AI Services PE | Cap Host |
|----------|-------------|---------|-------------|-------------------|---------------|----------|
| New Foundry + Private | No (AVM handles) | No | No | No | No | Yes (AVM) |
| Existing Foundry, same-sub + Private | No | No | No | Yes | Yes | Yes (explicit) |
| Existing Foundry, cross-sub + Private | Yes | Yes | Yes | Yes | Yes | Yes (explicit) |
| Any + No Private Networking | No | No | No | No | No | No |

---

## Troubleshooting

### Error: "Traffic is not from an approved private endpoint" (403)

**Cause**: Agent compute in the Foundry VNet is reaching services through peering to the deployment VNet's PEs, but the service doesn't recognize cross-VNet PE traffic as "approved."

**Solution**: Ensure `foundryVNetPrivateEndpoints` module is deployed, creating PEs in the Foundry VNet's backend subnet.

### Error: BCP120 — VNet overlap

**Cause**: The Foundry VNet address space overlaps with the deployment VNet.

**Solution**: Use non-overlapping RFC 1918 ranges. Deployment VNet uses `10.0.0.0/8`; Foundry VNet must use `172.16.0.0/16` or `192.168.0.0/16`.

### Warning: BCP036 on networkInjections

**Cause**: The `networkInjections` property is not in the published Bicep type schema for `Microsoft.CognitiveServices/accounts`.

**Impact**: None — this is a compile-time warning only. The property is accepted by the REST API at deployment time.

### Error: Capability host fails to create

**Cause**: Missing dependencies — networking, PEs, DNS zones, or connections not yet deployed.

**Solution**: Check that all dependency modules have completed successfully. The capability host has the most dependencies of any resource.

### Error: Agent uses public IP instead of VNet

**Cause**: `customerSubnet` not set on the account-level capability host.

**Solution**: Ensure `customerSubnetResourceId` is passed to `add-project-capability-host.bicep` and `createAccountCapabilityHost` is `true` for existing Foundry accounts.
