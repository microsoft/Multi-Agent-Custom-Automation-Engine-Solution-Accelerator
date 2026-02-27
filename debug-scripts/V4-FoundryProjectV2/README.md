# Debug Scripts — Local Development Guide

Standalone debug scripts for running multi-agent workflows locally **without** the full backend/frontend/MCP server stack. These scripts use the Azure AI Agent Framework v2 (Foundry Agents) to orchestrate multiple specialized agents with Azure AI Search (RAG) integration.

## Scripts

| Script | Description | Agents | Search Indexes |
|---|---|---|---|
| `contractagent.py` | NDA / Contract Compliance analysis | ContractSummaryAgent, ContractRiskAgent, ContractComplianceAgent | `contract-summary-doc-index`, `contract-risk-doc-index`, `contract-compliance-doc-index` |
| `rfpagent.py` | RFP (Request for Proposal) analysis | RfpSummaryAgent, RfpRiskAgent, RfpComplianceAgent | `macae-rfp-summary-index`, `macae-rfp-risk-index`, `macae-rfp-compliance-index` |

Both scripts share a common utility module (`agent_utils.py`) that handles agent creation, orchestration, streaming, and cleanup.

## Prerequisites

### 1. Required Tools

- **Python 3.12+**
- **Azure CLI** (`az`) — authenticated with your subscription
- **Git**

Install on Windows (PowerShell):

```powershell
winget install Python.Python.3.12
winget install Git.Git
winget install Microsoft.AzureCLI
```

Install on Linux (Ubuntu/Debian):

```bash
sudo apt update && sudo apt install python3.12 python3.12-venv git curl -y
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### 2. Azure Deployment

The solution accelerator must be deployed to Azure first. The deployment creates:

- **Azure AI Foundry Project** with model deployments (e.g., `gpt-4.1-mini`)
- **Azure AI Search** service with search indexes populated with your data
- **Azure AI Search connection** configured in the Foundry project

> If you haven't deployed yet, follow the [Deployment Guide](../docs/DeploymentGuide.md).

### 3. Azure RBAC Permissions

Your Azure account needs the following role assignments on the deployed resources:

| Resource | Role |
|---|---|
| AI Foundry Project | `Azure AI User`, `Azure AI Developer`, `Cognitive Services OpenAI User` |
| Azure AI Search | `Search Index Data Contributor` |

See [Local Development Setup — Azure RBAC Permissions](../docs/LocalDevelopmentSetup.md#required-azure-rbac-permissions) for detailed `az role assignment` commands.

### 4. Azure Authentication

```bash
az login
az account set --subscription "<your-subscription-id>"
az account show  # Verify correct subscription
```

## Setup

### Step 1: Navigate to the debug-scripts directory

```bash
cd debug-scripts
```

### Step 2: Create and activate a Python virtual environment

**Windows (PowerShell):**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / WSL2:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Create the `.env` file

Copy the sample environment file:

**Windows (PowerShell):**

```powershell
Copy-Item env.sample .env
```

**Linux / WSL2:**

```bash
cp env.sample .env
```

### Step 5: Configure the `.env` file

Open `.env` in your editor and fill in the values:

```ini
# Azure AI Project Configuration
AZURE_AI_PROJECT_ENDPOINT=<your-foundry-project-endpoint>

# Model Deployment
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=<your-model-deployment-name>

# Azure AI Search Configuration
AZURE_AI_SEARCH_CONNECTION_NAME=<your-search-connection-name>
```

#### How to find each value

| Variable | Where to find it |
|---|---|
| `AZURE_AI_PROJECT_ENDPOINT` | Azure Portal → Resource Group → AI Foundry Project → **Overview** → **Project endpoint** |
| `AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME` | Azure AI Foundry portal → your project → **Models + endpoints** → deployment name (e.g., `gpt-4.1-mini`) |
| `AZURE_AI_SEARCH_CONNECTION_NAME` | Azure AI Foundry portal → your project → **Connected resources** → name of the Azure AI Search connection |
| `AZURE_AI_SEARCH_INDEX_NAME_RFP_RISK` | Azure Portal → Azure AI Search service → **Indexes** → the RFP risk index name (e.g., `macae-rfp-risk-index`) |

> **Tip:** If the solution was deployed via `azd`, you can also find these values in the Backend Container App's environment variables: Azure Portal → Resource Group → Backend Container App → **Environment variables**.

## Running the Scripts

### Contract Compliance Analysis

```bash
python contractagent.py
```

This will:
1. Create three contract analysis agents with Azure AI Search tools
2. Build a Magentic orchestration workflow
3. Present the proposed plan and wait for your approval (type `yes` or `y`)
4. Stream agent responses as they execute
5. Print the consolidated final output
6. Clean up all created agents

### RFP Analysis

```bash
python rfpagent.py
```

This will:
1. Create three RFP analysis agents with Azure AI Search tools
2. Build a Magentic orchestration workflow
3. Present the proposed plan and wait for your approval (type `yes` or `y`)
4. Stream agent responses as they execute
5. Print the consolidated final output
6. Clean up all created agents

## File Structure

```
debug-scripts/
├── README.md              ← This file
├── env.sample             ← Environment variable template
├── .env                   ← Your local config (git-ignored)
├── requirements.txt       ← Python dependencies
├── agent_utils.py         ← Shared utilities (agent creation, orchestration, streaming)
├── contractagent.py       ← Contract compliance analysis script
└── rfpagent.py            ← RFP analysis script
```

## Troubleshooting

### `ValueError: Azure AI Search connection name is required`

Your `.env` file is missing or `AZURE_AI_SEARCH_CONNECTION_NAME` is not set. See [Step 5](#step-5-configure-the-env-file) above.

### `ValueError: AZURE_AI_PROJECT_ENDPOINT environment variable is required`

Your `.env` file is missing or `AZURE_AI_PROJECT_ENDPOINT` is not set. See [Step 5](#step-5-configure-the-env-file) above.

### `azure.core.exceptions.HttpResponseError: (AuthorizationFailed)`

Your Azure account is missing required RBAC roles. See [Prerequisites — Azure RBAC Permissions](#3-azure-rbac-permissions).

### `ModuleNotFoundError: No module named '...'`

Ensure your virtual environment is activated and dependencies are installed:

```bash
# Activate venv (if not already)
.\.venv\Scripts\Activate.ps1   # Windows
source .venv/bin/activate       # Linux

# Install dependencies
pip install -r requirements.txt
```

### Plan rejected / `Plan execution cancelled by user`

Both scripts use human approval. When the orchestrator presents a plan, type `yes` or `y` to approve. Type `no` or `n` to cancel.
