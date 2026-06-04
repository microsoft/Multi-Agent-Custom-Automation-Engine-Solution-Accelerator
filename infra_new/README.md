# Infrastructure Modules — Accelerator Toolkit Core

The **baseline repository** for modular Bicep infrastructure used across all GSA Solution Accelerators.

## Overview

This is the **baseline repo** that all GSAs should reference when building or updating their infrastructure. Modules here represent the standardized, tested patterns — individual accelerators copy what they need and wire them together in their own `main.bicep` orchestrator.

Two flavors are available:

| Flavor | Path | Description |
|--------|------|-------------|
| **AVM** | `avm/` | Modules wrapping [Azure Verified Modules](https://aka.ms/avm) for WAF-aligned, enterprise-grade deployments |
| **Vanilla Bicep** | `bicep/` | Lightweight modules using native Bicep resources directly |

Both flavors follow the same folder structure and naming conventions, so switching between them requires minimal changes to your orchestrator.

---

## Folder Structure

```
infra/
├── avm/
│   ├── main.bicep                    # Orchestrator (reference implementation)
│   └── modules/
│       ├── ai/                       # AI Services, Foundry, Search
│       ├── compute/                  # App Service, VMs
│       ├── data/                     # SQL, Cosmos DB, Storage
│       ├── fabric/                   # Microsoft Fabric
│       ├── identity/                 # RBAC, Managed Identities
│       ├── monitoring/               # Log Analytics, App Insights
│       └── networking/               # VNet, Private Endpoints, Bastion
├── bicep/
│   ├── main.bicep                    # Orchestrator (reference implementation)
│   └── modules/                      # Same domain folders as AVM
├── main.bicep                        # Router (selects avm/ or bicep/ based on param)
├── main.parameters.json              # Default parameters
└── main.waf.parameters.json          # WAF-aligned parameters (VNet, PE, etc.)
```

Modules are organized by **service domain** (ai, compute, data, etc.). Browse the folders to see what's available — new modules are added continuously as accelerators contribute back.

---

## How to Use

### 1. Copy modules to your accelerator

Copy the modules you need into your accelerator's `infra/` folder, preserving the folder structure:

```bash
# Copy entire structure (recommended for new accelerators)
cp -r infra/avm/modules/ <your-repo>/infra/avm/modules/
cp -r infra/bicep/modules/ <your-repo>/infra/bicep/modules/

# Or copy only the domain folders you need
cp -r infra/avm/modules/ai/ <your-repo>/infra/avm/modules/ai/
cp -r infra/avm/modules/data/ <your-repo>/infra/avm/modules/data/
```

### 2. Create your orchestrator (`main.bicep`)

Your `main.bicep` acts as the **orchestrator only** — it declares parameters, calls modules, and wires outputs together. All resource naming and configuration logic lives inside the modules.

```bicep
// main.bicep — Orchestrator example
targetScope = 'resourceGroup'

// ========== Parameters ========== //
param solutionName string
param location string = resourceGroup().location

// ========== Modules ========== //

module my_service './modules/<domain>/<service>.bicep' = {
  name: 'module.<service>.${solutionName}'
  params: {
    solutionName: solutionName
    location: location
  }
}

// ========== Outputs ========== //
output serviceEndpoint string = my_service.outputs.endpoint
```

### 3. Wire outputs between modules

Modules output their key properties (name, id, endpoint, principalId). Use these to connect modules together:

```bicep
module service_a './modules/domain-a/service-a.bicep' = { ... }

module service_b './modules/domain-b/service-b.bicep' = {
  params: {
    dependencyEndpoint: service_a.outputs.endpoint
    dependencyResourceId: service_a.outputs.resourceId
  }
}
```

### 4. Use the router for dual-mode support (optional)

The root `main.bicep` acts as a router — it selects between `avm/main.bicep` and `bicep/main.bicep` based on a parameter, allowing the same deployment command to target either flavor.

---

## Role Assignments

All role assignments are centralized in `identity/role-assignments.bicep` for auditability. Individual modules do **not** create their own RBAC — the orchestrator wires principal IDs and resource IDs into the single role-assignments module.

> **Note:** The `role-assignments.bicep` file in this toolkit is a **reference template**. Each GSA should customize it based on their specific service-to-service and deployer-to-resource RBAC requirements. Add or remove role assignments as needed for your accelerator's services — only the structure and pattern should remain consistent across GSAs.

---

## Contributing New Modules

When adding a new module to the toolkit:

1. Place it in the appropriate domain folder (`ai/`, `compute/`, `data/`, etc.)
2. Accept `solutionName` as a parameter and derive the resource name internally
3. Use descriptive `@description()` decorators on all parameters
4. Output the resource's key properties (name, id, endpoint, principalId, etc.)
5. Keep it generic — no app-specific or accelerator-specific logic
6. Add it to both `avm/` and `bicep/` flavors where applicable
7. Test with `az bicep build` before committing


