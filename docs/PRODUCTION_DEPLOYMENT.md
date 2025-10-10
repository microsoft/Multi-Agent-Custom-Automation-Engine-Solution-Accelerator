# Production Deployment Guide

**Multi-Agent Custom Automation Engine Solution Accelerator**  
**Version:** 1.0  
**Last Updated:** October 10, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture Overview](#architecture-overview)
4. [Deployment Options](#deployment-options)
5. [Azure Deployment (Recommended)](#azure-deployment-recommended)
6. [Environment Configuration](#environment-configuration)
7. [Database Setup](#database-setup)
8. [Security Configuration](#security-configuration)
9. [Monitoring & Logging](#monitoring--logging)
10. [Scaling & Performance](#scaling--performance)
11. [Backup & Disaster Recovery](#backup--disaster-recovery)
12. [Troubleshooting](#troubleshooting)
13. [Post-Deployment Checklist](#post-deployment-checklist)

---

## Overview

This guide provides step-by-step instructions for deploying the Multi-Agent Custom Automation Engine to production environments. The platform consists of:

- **Backend API** (FastAPI, Python 3.11+)
- **Frontend Web App** (React/TypeScript, Vite)
- **MCP Server** (Model Context Protocol server for AI agents)
- **Data Storage** (Azure Cosmos DB, Azure Blob Storage)
- **AI Services** (Azure OpenAI, Azure AI Foundry)

**Deployment Time:** 2-3 hours (first-time), 30-45 minutes (subsequent deployments)

---

## Prerequisites

### Required Accounts & Subscriptions

✅ **Azure Subscription** with sufficient quota:
- Azure OpenAI (GPT-4, GPT-4 Turbo)
- Azure Cosmos DB
- Azure Blob Storage
- Azure Container Apps or App Service
- Azure Container Registry
- Azure Log Analytics
- Azure Application Insights

✅ **Developer Tools:**
- Azure CLI (`az`) version 2.50+
- Azure Developer CLI (`azd`) version 1.5.0+
- Docker Desktop (for local testing)
- Git
- Python 3.11+ (for local validation)
- Node.js 18+ (for frontend builds)

✅ **Access & Permissions:**
- Azure Subscription Owner or Contributor role
- Ability to create service principals
- Ability to register Azure AD applications

### Quota Requirements

Run the quota validation script before deployment:

```bash
# Check Azure OpenAI quota
bash infra/scripts/validate_model_deployment_quotas.sh
```

**Minimum Required Quotas:**
- **GPT-4**: 30K tokens/min
- **GPT-4 Turbo**: 50K tokens/min
- **GPT-3.5 Turbo**: 100K tokens/min
- **text-embedding-ada-002**: 150K tokens/min

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Azure Front Door                     │
│                    (Optional - CDN)                      │
└──────────────────────┬──────────────────────────────────┘
                       │
       ┌───────────────┴────────────────┐
       │                                 │
       ▼                                 ▼
┌────────────────┐              ┌──────────────────┐
│  Frontend App  │              │   Backend API    │
│  (App Service) │◄────────────►│  (Container App) │
└────────────────┘              └────────┬─────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
            ┌───────────────┐   ┌──────────────┐   ┌─────────────────┐
            │   MCP Server  │   │  Azure AI    │   │   Cosmos DB     │
            │ (Container    │   │  Foundry     │   │   (NoSQL)       │
            │     App)      │   │  + OpenAI    │   │                 │
            └───────────────┘   └──────────────┘   └─────────────────┘
                    │                    
                    ▼                    
            ┌───────────────┐   
            │  Blob Storage │   
            │  (Datasets)   │   
            └───────────────┘   
```

---

## Deployment Options

### Option 1: Azure Developer CLI (Recommended)

**Best for:** Quick production deployments with infrastructure-as-code

```bash
# Clone repository
git clone https://github.com/your-org/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator.git
cd Multi-Agent-Custom-Automation-Engine-Solution-Accelerator

# Login to Azure
az login
azd auth login

# Initialize azd environment
azd env new production

# Deploy everything
azd up
```

**Deployment includes:**
- ✅ Azure OpenAI models
- ✅ Cosmos DB with containers
- ✅ Blob Storage with containers
- ✅ Container Apps for backend/MCP
- ✅ App Service for frontend
- ✅ Application Insights
- ✅ Log Analytics workspace
- ✅ Key Vault for secrets
- ✅ Managed identities

---

### Option 2: Manual Azure Portal Deployment

**Best for:** Custom configurations or learning the architecture

See [Manual Azure Deployment Guide](ManualAzureDeployment.md) for detailed steps.

---

### Option 3: Azure DevOps Pipeline

**Best for:** CI/CD workflows and team deployments

```yaml
# .azdo/pipelines/azure-dev.yml already configured
# Trigger: Push to main branch or manual trigger

trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: AzureCLI@2
    inputs:
      azureSubscription: '$(AZURE_SUBSCRIPTION)'
      scriptType: 'bash'
      scriptLocation: 'inlineScript'
      inlineScript: |
        azd deploy --no-prompt
```

---

## Azure Deployment (Recommended)

### Step 1: Prepare Configuration

Create an environment file:

```bash
# Copy sample environment
cp .env.sample .env

# Edit with your settings
nano .env
```

**Required Environment Variables:**

```bash
# Azure Subscription
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_LOCATION=eastus

# Deployment Settings
AZURE_ENV_NAME=prod-macae
AZURE_RESOURCE_GROUP=rg-macae-prod

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# AI Foundry (optional)
AZURE_AI_PROJECT_NAME=your-ai-project
AZURE_AI_PROJECT_CONNECTION_STRING=your-connection-string

# Authentication
AZURE_AD_CLIENT_ID=your-app-registration-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret

# Storage
AZURE_COSMOS_DB_ENDPOINT=https://your-cosmos.documents.azure.com/
AZURE_COSMOS_DB_KEY=your-cosmos-key
AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount
AZURE_STORAGE_ACCOUNT_KEY=your-storage-key
```

---

### Step 2: Run Pre-Deployment Validation

```bash
# Validate Azure quota
bash infra/scripts/validate_model_deployment_quotas.sh

# Validate infrastructure templates
az deployment sub validate \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json

# Build and test containers locally
docker-compose up --build
```

---

### Step 3: Deploy Infrastructure

```bash
# Deploy using azd
azd up

# Or deploy using Azure CLI
az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json \
  --name macae-prod-deployment
```

**Deployment Duration:** ~15-20 minutes

**What gets deployed:**
1. Resource Group
2. Azure OpenAI service + models (GPT-4, embeddings)
3. Cosmos DB account + databases + containers
4. Storage Account + blob containers
5. Container Registry
6. Container Apps (backend + MCP server)
7. App Service (frontend)
8. Application Insights
9. Log Analytics Workspace
10. Key Vault
11. Managed Identities

---

### Step 4: Configure Azure AD Authentication

```bash
# Create app registration
bash infra/scripts/create_app_registration.sh

# Configure redirect URIs
az ad app update \
  --id $AZURE_AD_CLIENT_ID \
  --web-redirect-uris "https://your-frontend.azurewebsites.net/.auth/login/aad/callback"

# Assign API permissions
az ad app permission add \
  --id $AZURE_AD_CLIENT_ID \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

# Grant admin consent
az ad app permission admin-consent --id $AZURE_AD_CLIENT_ID
```

See [Azure App Service Auth Setup](azure_app_service_auth_setup.md) for detailed steps.

---

### Step 5: Upload Sample Data & Team Configurations

```bash
# Process and upload sample datasets
bash infra/scripts/process_sample_data.sh

# Upload agent team configurations
bash infra/scripts/upload_team_config.sh

# Verify uploads
az cosmosdb sql container query \
  --resource-group rg-macae-prod \
  --account-name your-cosmos-account \
  --database-name macae-db \
  --name datasets \
  --query-text "SELECT * FROM c"
```

---

### Step 6: Deploy Application Code

```bash
# Build and push backend container
cd src/backend
az acr build \
  --registry your-acr-name \
  --image macae-backend:latest \
  --file Dockerfile .

# Build and push MCP server container
cd ../mcp_server
az acr build \
  --registry your-acr-name \
  --image macae-mcp-server:latest \
  --file Dockerfile .

# Build and deploy frontend
cd ../frontend
npm ci
npm run build
az webapp deployment source config-zip \
  --resource-group rg-macae-prod \
  --name your-frontend-app \
  --src dist.zip
```

---

### Step 7: Configure Environment Variables

Set application settings in Azure:

```bash
# Backend Container App
az containerapp update \
  --name backend-container-app \
  --resource-group rg-macae-prod \
  --set-env-vars \
    AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \
    AZURE_OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=https://your-keyvault.vault.azure.net/secrets/openai-api-key) \
    COSMOS_DB_ENDPOINT=$AZURE_COSMOS_DB_ENDPOINT \
    COSMOS_DB_KEY=@Microsoft.KeyVault(SecretUri=https://your-keyvault.vault.azure.net/secrets/cosmos-db-key)

# Frontend App Service
az webapp config appsettings set \
  --resource-group rg-macae-prod \
  --name your-frontend-app \
  --settings \
    VITE_API_BASE_URL=https://your-backend.azurecontainerapps.io \
    VITE_MCP_SERVER_URL=https://your-mcp-server.azurecontainerapps.io
```

---

### Step 8: Enable Managed Identity Access

```bash
# Assign Cosmos DB access to backend
bash infra/scripts/assign_azure_ai_user_role.sh

# Grant backend access to Key Vault
az keyvault set-policy \
  --name your-keyvault \
  --object-id $BACKEND_MANAGED_IDENTITY_ID \
  --secret-permissions get list

# Grant MCP server access to Blob Storage
az role assignment create \
  --assignee $MCP_MANAGED_IDENTITY_ID \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/rg-macae-prod/providers/Microsoft.Storage/storageAccounts/your-storage-account
```

---

## Environment Configuration

### Production Environment Variables

Store in Azure Key Vault and reference in app settings:

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service URL | `https://your-openai.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | API key for OpenAI | (Stored in Key Vault) |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | GPT-4 deployment name | `gpt-4` |
| `COSMOS_DB_ENDPOINT` | Cosmos DB URL | `https://your-cosmos.documents.azure.com/` |
| `COSMOS_DB_KEY` | Cosmos DB primary key | (Stored in Key Vault) |
| `STORAGE_ACCOUNT_NAME` | Blob storage account | `macaestorage` |
| `STORAGE_ACCOUNT_KEY` | Storage access key | (Stored in Key Vault) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights conn string | Auto-injected by Azure |
| `ALLOWED_ORIGINS` | CORS origins | `https://your-frontend.azurewebsites.net` |

See [Environment Variables Reference](ENVIRONMENT_VARIABLES.md) for complete list.

---

## Database Setup

### Cosmos DB Configuration

**Database:** `macae-db`

**Containers:**

| Container | Partition Key | Throughput | Purpose |
|-----------|---------------|------------|---------|
| `datasets` | `/customerId` | 400 RU/s | Dataset storage |
| `plans` | `/userId` | 400 RU/s | Agent execution plans |
| `team_configs` | `/team_name` | 400 RU/s | Agent team configurations |
| `execution_logs` | `/planId` | 400 RU/s | Agent execution logs |

**Auto-created by deployment**, but can be created manually:

```bash
az cosmosdb sql database create \
  --account-name your-cosmos-account \
  --resource-group rg-macae-prod \
  --name macae-db

az cosmosdb sql container create \
  --account-name your-cosmos-account \
  --resource-group rg-macae-prod \
  --database-name macae-db \
  --name datasets \
  --partition-key-path "/customerId" \
  --throughput 400
```

---

## Security Configuration

### 1. Authentication & Authorization

**Azure AD Integration:**
- All users must authenticate via Azure AD
- Role-Based Access Control (RBAC) enforced
- API requires Bearer tokens

**Roles:**
- `MACAE.Admin` - Full access
- `MACAE.Analyst` - Read/execute analytics
- `MACAE.Viewer` - Read-only access

### 2. Network Security

**Recommended Configuration:**

```bash
# Enable private endpoints for Cosmos DB
az cosmosdb private-endpoint-connection create \
  --resource-group rg-macae-prod \
  --account-name your-cosmos-account \
  --name cosmos-private-endpoint \
  --vnet-name your-vnet \
  --subnet backend-subnet

# Restrict Storage Account to VNet
az storage account update \
  --name your-storage-account \
  --resource-group rg-macae-prod \
  --default-action Deny

az storage account network-rule add \
  --account-name your-storage-account \
  --resource-group rg-macae-prod \
  --vnet-name your-vnet \
  --subnet backend-subnet
```

### 3. Key Vault Secrets

Store all sensitive values in Key Vault:

```bash
# Store OpenAI API key
az keyvault secret set \
  --vault-name your-keyvault \
  --name openai-api-key \
  --value $AZURE_OPENAI_API_KEY

# Reference in app settings
az containerapp update \
  --name backend-container-app \
  --resource-group rg-macae-prod \
  --set-env-vars \
    AZURE_OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=https://your-keyvault.vault.azure.net/secrets/openai-api-key)
```

---

## Monitoring & Logging

### Application Insights

**Automatic Telemetry:**
- Request/response times
- Exception tracking
- Dependency tracking (Cosmos DB, OpenAI)
- Custom events for agent executions

**Key Metrics to Monitor:**

```kusto
// Average response time
requests
| where timestamp > ago(1h)
| summarize avg(duration) by bin(timestamp, 5m)

// Error rate
requests
| where timestamp > ago(1h)
| summarize total=count(), errors=countif(success == false) by bin(timestamp, 5m)
| extend error_rate = errors * 100.0 / total

// OpenAI token usage
dependencies
| where target contains "openai"
| extend tokens = toint(customDimensions["tokens"])
| summarize sum(tokens) by bin(timestamp, 1h)
```

### Log Analytics Queries

```kusto
// Container app logs
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "backend-container-app"
| where TimeGenerated > ago(1h)
| order by TimeGenerated desc

// Agent execution tracking
traces
| where message contains "Agent execution"
| extend plan_id = tostring(customDimensions["plan_id"])
| summarize count() by plan_id, bin(timestamp, 1h)
```

---

## Scaling & Performance

### Container Apps Auto-Scaling

```bash
# Configure auto-scaling for backend
az containerapp update \
  --name backend-container-app \
  --resource-group rg-macae-prod \
  --min-replicas 2 \
  --max-replicas 10 \
  --scale-rule-name http-rule \
  --scale-rule-type http \
  --scale-rule-http-concurrency 50
```

### Cosmos DB Performance

**Use autoscale throughput:**

```bash
az cosmosdb sql container throughput update \
  --account-name your-cosmos-account \
  --resource-group rg-macae-prod \
  --database-name macae-db \
  --name datasets \
  --max-throughput 4000
```

**Performance Tips:**
- Use partition keys effectively (`/customerId`, `/userId`)
- Enable indexing only on queried properties
- Use point reads with partition key when possible
- Monitor RU consumption in Application Insights

See [Performance Optimization Guide](PERFORMANCE_OPTIMIZATION.md) for detailed tuning.

---

## Backup & Disaster Recovery

### Cosmos DB Backup

**Automatic:** Continuous backup enabled by default (7-day retention)

**Point-in-time restore:**

```bash
az cosmosdb sql database restore \
  --account-name your-cosmos-account \
  --resource-group rg-macae-prod \
  --name macae-db \
  --restore-timestamp "2025-10-09T10:00:00Z"
```

### Blob Storage Backup

**Enable soft delete:**

```bash
az storage blob service-properties delete-policy update \
  --account-name your-storage-account \
  --enable true \
  --days-retained 30
```

### Application Code Backup

- **Source Control:** GitHub (primary backup)
- **Container Images:** Azure Container Registry (geo-replicated)
- **Configuration:** Infrastructure-as-code in Git

---

## Troubleshooting

### Common Issues

**1. Backend API returns 500 errors**

```bash
# Check logs
az containerapp logs show \
  --name backend-container-app \
  --resource-group rg-macae-prod \
  --follow

# Verify environment variables
az containerapp show \
  --name backend-container-app \
  --resource-group rg-macae-prod \
  --query properties.template.containers[0].env
```

**2. Frontend cannot connect to backend**

- Verify CORS settings in backend
- Check `VITE_API_BASE_URL` in frontend app settings
- Ensure backend is running (`az containerapp list`)

**3. OpenAI quota exceeded**

```bash
# Check current usage
az cognitiveservices account deployment list \
  --name your-openai-account \
  --resource-group rg-macae-prod

# Request quota increase
# https://aka.ms/oai/quotaincrease
```

**4. Cosmos DB throttling (429 errors)**

- Increase RU/s for affected container
- Review partition key distribution
- Enable autoscale throughput

See [Troubleshooting Guide](TroubleShootingSteps.md) for more solutions.

---

## Post-Deployment Checklist

### Validation Steps

- [ ] Backend API health check: `https://your-backend.azurecontainerapps.io/health`
- [ ] MCP server health check: `https://your-mcp-server.azurecontainerapps.io/health`
- [ ] Frontend loads successfully
- [ ] Azure AD authentication working
- [ ] Can upload a test dataset
- [ ] Can execute a test forecast
- [ ] Application Insights receiving telemetry
- [ ] Logs appearing in Log Analytics
- [ ] Alerts configured and tested
- [ ] Backup/restore tested

### Security Verification

- [ ] All secrets stored in Key Vault
- [ ] Managed identities configured
- [ ] Private endpoints enabled (if required)
- [ ] CORS configured correctly
- [ ] Network security groups configured
- [ ] Azure AD roles assigned
- [ ] Key Vault access policies set

### Performance Baseline

- [ ] Load test backend API (target: <500ms p95)
- [ ] Verify auto-scaling triggers
- [ ] Monitor Cosmos DB RU consumption
- [ ] Set up performance alerts
- [ ] Document baseline metrics

---

## Support & Maintenance

### Monitoring Recommendations

**Set up alerts for:**
- API error rate > 5%
- Average response time > 1 second
- OpenAI quota utilization > 80%
- Cosmos DB RU utilization > 80%
- Container app CPU > 80%
- Failed authentication attempts > 10/min

### Maintenance Schedule

**Weekly:**
- Review Application Insights dashboards
- Check for security updates
- Verify backup integrity

**Monthly:**
- Review and optimize Cosmos DB indexing
- Analyze cost optimization opportunities
- Update dependencies (security patches)

**Quarterly:**
- Conduct disaster recovery drill
- Review and update scaling policies
- Performance tuning based on usage patterns

---

**Deployment Guide Version:** 1.0  
**Last Updated:** October 10, 2025

For additional support:
- **Documentation:** [docs/](.)
- **Issues:** GitHub Issues
- **Email:** support@yourcompany.com



