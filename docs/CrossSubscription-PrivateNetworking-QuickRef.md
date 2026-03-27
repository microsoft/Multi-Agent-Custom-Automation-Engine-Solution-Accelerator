# Cross-Subscription Private Networking for AI Foundry Agents — Quick Reference

## Overview

When AI Foundry (AI Services account + project) lives in **Subscription A** and your data resources (Cosmos DB, Storage, AI Search) live in **Subscription B**, you need cross-subscription private networking to connect them securely.

---

## Architecture at a Glance

```
 Subscription A (Foundry)              Subscription B (Deployment)
┌─────────────────────────┐           ┌──────────────────────────────┐
│  AI Services Account    │           │  Cosmos DB                   │
│  AI Foundry Project     │           │  Storage Account             │
│                         │           │  AI Search                   │
│  Foundry VNet           │  Peering  │  Key Vault                   │
│  ├─ Agent Subnet        │◄────────►│                              │
│  │  (delegated)         │           │  Deployment VNet             │
│  └─ PE Subnet           │           │  ├─ Backend Subnet           │
│     ├─ Cosmos PE        │           │  │  ├─ Cosmos PE             │
│     ├─ Storage PE       │           │  │  ├─ Storage PE            │
│     └─ Search PE        │           │  │  ├─ Search PE             │
│                         │           │  │  ├─ Key Vault PE          │
│                         │           │  │  └─ AI Services PE        │
│                         │           │  ├─ Agent Subnet (delegated) │
│                         │           │  └─ Other subnets...         │
│                         │           │                              │
│                         │           │  7 Private DNS Zones         │
│                         │           │  (linked to both VNets)      │
└─────────────────────────┘           └──────────────────────────────┘
```

---

## Why Two VNets?

Azure requires the **agent subnet** (used in `networkInjections`) to be in the **same subscription** as the AI Services account. If your AI Services is in Subscription A but your data resources are in Subscription B, you must create a VNet in Subscription A for the agent subnet.

## Why VNet Peering?

The two VNets are in different subscriptions and completely isolated by default. **Bidirectional VNet peering** provides:
- Network path for DNS resolution across both VNets
- Management-plane connectivity during resource provisioning
- Cross-VNet service communication for runtime operations

## Why Two Subnets Per VNet?

| Subnet | Delegation | Purpose |
|--------|-----------|---------|
| **Agent Subnet** | `Microsoft.App/environments` (required) | AI Foundry agent compute runs here |
| **PE/Backend Subnet** | None | Hosts Private Endpoints — delegated subnets **cannot** host PEs |

Azure enforces this: a subnet delegated to `Microsoft.App/environments` is exclusively reserved for Container Apps. Private Endpoints are blocked in delegated subnets.

## Why Duplicate Private Endpoints?

PEs for Cosmos DB, Storage, and Search already exist in the Deployment VNet. Why can't agent compute in the Foundry VNet use them through peering?

**Because Azure rejects cross-VNet PE traffic:**

```
Agent (172.16.0.x) → peering → PE NIC (10.0.2.x) → Cosmos DB
                                                     ↓
                                          403: "Not from approved PE"
```

The service-side validation checks that traffic arrived **through the specific PE NIC**. Traffic routed via peering has a different source — the service rejects it.

**Fix:** Create duplicate PEs in the Foundry VNet so agent compute hits a **local** PE NIC:

```
Agent (172.16.0.x) → local PE NIC (172.16.1.x) → Cosmos DB
                                                   ↓
                                          ✓ Access granted
```

## Mandatory BYO Resources

The capability host **requires all three** — none can be skipped:

| Connection | Azure Resource | What It Stores |
|-----------|----------------|----------------|
| `threadStorageConnections` | **Cosmos DB** | Agent threads, conversation history |
| `vectorStoreConnections` | **AI Search** | Vector embeddings for file search |
| `storageConnections` | **Storage Account** | File uploads from users/developers |

Missing any one → capability host creation fails with: *"Agents CapabilityHost supports a single, non empty value for [connection] property."*

---

## What We Added (vs existing WAF baseline)

### For All WAF Deployments

| Resource | Purpose | Cost |
|----------|---------|------|
| Agent Subnet + NSG | Dedicated subnet for agent compute `networkInjections` | Free |
| AI Search PE | Was missing — now enabled with `publicNetworkAccess: Disabled` | ~$7/mo |
| Storage + Cosmos DB connections | Required for capability host (only Search existed before) | Free |
| Capability Host module | Creates account + project capability hosts with BYO connections | Free |

### For Cross-Subscription (WAF + Existing Foundry)

| Resource | Purpose | Cost |
|----------|---------|------|
| Foundry VNet (172.16.0.0/16) + 2 subnets + 2 NSGs | Agent subnet in Foundry's subscription | Free |
| 2 VNet Peerings (bidirectional) | Cross-subscription connectivity | ~$0.01/GB |
| 7 DNS Zone Links to Foundry VNet | PE DNS resolution from Foundry VNet | Free |
| AI Services Networking Update (PUT) | Adds `networkInjections` + disables public access | Free |
| AI Services PE + DNS Zone Group (3 zones) | Deployment-side private access to AI Services | ~$7/mo |
| 3 Duplicate PEs (Cosmos, Storage, Search) in Foundry VNet | Fixes 403 "not from approved PE" | ~$22/mo |
| Cosmos DB `networkAclBypass: AzureServices` | Allows Azure internal calls during provisioning | Free |

**Total added cost: ~$7/mo (WAF) or ~$37–47/mo (WAF + cross-subscription)**

---

## New Modules

| Module | When Used | What It Does |
|--------|-----------|-------------|
| `cross-subscription-vnet.bicep` | Cross-sub only | Foundry VNet, 2 subnets, 2 NSGs, peering |
| `ai-services-account-networking.bicep` | Cross-sub only | PUT update preserving all existing properties |
| `add-project-capability-host.bicep` | All WAF | Account + project capability hosts with `customerSubnet` |
| `foundry-vnet-private-endpoints.bicep` | Cross-sub only | 3 duplicate PEs + DNS zone groups |

---

## Key Lessons

1. **`networkInjections` subnet must be in the same subscription** as the AI Services account — no exceptions
2. **VNet peering ≠ PE access** — peered traffic is rejected by service-side PE validation
3. **Bicep resource PUT overwrites everything** — always read and pass back all properties when updating existing resources
4. **`customerSubnet` must be set at the account level** — project-level capability host does not expose this property
5. **Cosmos DB needs `networkAclBypass: AzureServices`** for existing Foundry — otherwise capability host provisioning fails
6. **All 3 BYO resources are mandatory** — Cosmos DB, Storage, and AI Search cannot be skipped

---

## References

| Topic | Link |
|-------|------|
| Private Networking for Agents | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/virtual-networks |
| Capability Hosts | https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/capability-hosts |
| Use Your Own Resources | https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/use-your-own-resources |
| Agent Service FAQ | https://learn.microsoft.com/en-us/azure/foundry/agents/faq |
| Official Bicep Template | https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/15-private-network-standard-agent-setup |
