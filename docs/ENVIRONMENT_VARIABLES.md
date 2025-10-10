# Environment Variables Reference

**Multi-Agent Custom Automation Engine Solution Accelerator**  
**Version:** 1.0  
**Last Updated:** October 10, 2025

---

## Overview

This document provides a comprehensive reference for all environment variables used across the Multi-Agent Custom Automation Engine platform.

**Components:**
- Backend API
- Frontend Web App
- MCP Server
- Deployment Scripts

---

## Table of Contents

1. [Azure Core Services](#azure-core-services)
2. [Azure OpenAI](#azure-openai)
3. [Azure AI Foundry](#azure-ai-foundry)
4. [Database & Storage](#database--storage)
5. [Authentication](#authentication)
6. [Application Configuration](#application-configuration)
7. [Monitoring & Logging](#monitoring--logging)
8. [Development & Testing](#development--testing)
9. [Optional Features](#optional-features)
10. [Environment-Specific Values](#environment-specific-values)

---

## Azure Core Services

### `AZURE_SUBSCRIPTION_ID`
- **Required:** Yes
- **Used by:** Deployment scripts, backend
- **Description:** Azure subscription ID for resource deployment
- **Example:** `12345678-1234-1234-1234-123456789abc`
- **How to obtain:** `az account show --query id -o tsv`

### `AZURE_TENANT_ID`
- **Required:** Yes
- **Used by:** Authentication, deployment
- **Description:** Azure AD tenant ID
- **Example:** `87654321-4321-4321-4321-cba987654321`
- **How to obtain:** `az account show --query tenantId -o tsv`

### `AZURE_LOCATION`
- **Required:** Yes
- **Used by:** Deployment scripts
- **Description:** Azure region for resource deployment
- **Example:** `eastus`, `westus2`, `northeurope`
- **Recommended:** `eastus` (best OpenAI model availability)

### `AZURE_RESOURCE_GROUP`
- **Required:** Yes
- **Used by:** All components
- **Description:** Resource group name for all Azure resources
- **Example:** `rg-macae-prod`
- **Naming convention:** `rg-{project}-{environment}`

### `AZURE_ENV_NAME`
- **Required:** Yes (for azd)
- **Used by:** Azure Developer CLI
- **Description:** Environment name for azd deployments
- **Example:** `prod-macae`, `dev-macae`, `staging-macae`
- **Max length:** 64 characters

---

## Azure OpenAI

### `AZURE_OPENAI_ENDPOINT`
- **Required:** Yes
- **Used by:** Backend, MCP server
- **Description:** Azure OpenAI service endpoint URL
- **Example:** `https://your-openai-eastus.openai.azure.com/`
- **Format:** Must end with `/`
- **How to obtain:**
  ```bash
  az cognitiveservices account show \
    --name your-openai-account \
    --resource-group rg-macae-prod \
    --query properties.endpoint -o tsv
  ```

### `AZURE_OPENAI_API_KEY`
- **Required:** Yes
- **Used by:** Backend, MCP server
- **Description:** API key for Azure OpenAI service
- **Example:** (64-character hex string)
- **Security:** Store in Azure Key Vault, reference via `@Microsoft.KeyVault(...)`
- **How to obtain:**
  ```bash
  az cognitiveservices account keys list \
    --name your-openai-account \
    --resource-group rg-macae-prod \
    --query key1 -o tsv
  ```

### `AZURE_OPENAI_DEPLOYMENT_NAME`
- **Required:** Yes
- **Used by:** Backend, MCP server
- **Description:** Name of GPT-4 deployment
- **Example:** `gpt-4`, `gpt-4-turbo`
- **Default:** `gpt-4`

### `AZURE_OPENAI_API_VERSION`
- **Required:** No
- **Used by:** Backend, MCP server
- **Description:** Azure OpenAI API version
- **Example:** `2024-02-15-preview`
- **Default:** `2024-02-15-preview`

### `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- **Required:** No (for advanced features)
- **Used by:** MCP server
- **Description:** Text embedding model deployment name
- **Example:** `text-embedding-ada-002`
- **Default:** `text-embedding-ada-002`

---

## Azure AI Foundry

### `AZURE_AI_PROJECT_NAME`
- **Required:** No (recommended for production)
- **Used by:** Backend
- **Description:** AI Foundry project name
- **Example:** `macae-ai-project`

### `AZURE_AI_PROJECT_CONNECTION_STRING`
- **Required:** No
- **Used by:** Backend
- **Description:** Connection string for AI Foundry project
- **Example:** `Endpoint=https://...;ApiKey=...`
- **Security:** Store in Key Vault

### `AZURE_AI_HUB_NAME`
- **Required:** No
- **Used by:** Deployment scripts
- **Description:** AI Foundry hub name
- **Example:** `macae-ai-hub`

---

## Database & Storage

### Cosmos DB

#### `COSMOS_DB_ENDPOINT`
- **Required:** Yes
- **Used by:** Backend
- **Description:** Cosmos DB account endpoint URL
- **Example:** `https://your-cosmos-account.documents.azure.com:443/`
- **How to obtain:**
  ```bash
  az cosmosdb show \
    --name your-cosmos-account \
    --resource-group rg-macae-prod \
    --query documentEndpoint -o tsv
  ```

#### `COSMOS_DB_KEY`
- **Required:** Yes (if not using managed identity)
- **Used by:** Backend
- **Description:** Cosmos DB primary key
- **Example:** (88-character base64 string)
- **Security:** Store in Key Vault
- **Alternative:** Use managed identity (recommended for production)
- **How to obtain:**
  ```bash
  az cosmosdb keys list \
    --name your-cosmos-account \
    --resource-group rg-macae-prod \
    --query primaryMasterKey -o tsv
  ```

#### `COSMOS_DB_DATABASE_NAME`
- **Required:** No
- **Used by:** Backend
- **Description:** Cosmos DB database name
- **Example:** `macae-db`
- **Default:** `macae-db`

#### `COSMOS_DB_CONTAINER_DATASETS`
- **Required:** No
- **Used by:** Backend
- **Description:** Container name for datasets
- **Default:** `datasets`

#### `COSMOS_DB_CONTAINER_PLANS`
- **Required:** No
- **Used by:** Backend
- **Description:** Container name for execution plans
- **Default:** `plans`

#### `COSMOS_DB_CONTAINER_TEAMS`
- **Required:** No
- **Used by:** Backend
- **Description:** Container name for team configurations
- **Default:** `team_configs`

### Blob Storage

#### `AZURE_STORAGE_ACCOUNT_NAME`
- **Required:** Yes
- **Used by:** Backend, MCP server
- **Description:** Storage account name for dataset files
- **Example:** `macaestorageprod`
- **Constraints:** 3-24 lowercase alphanumeric characters

#### `AZURE_STORAGE_ACCOUNT_KEY`
- **Required:** Yes (if not using managed identity)
- **Used by:** Backend, MCP server
- **Description:** Storage account access key
- **Security:** Store in Key Vault
- **Alternative:** Use managed identity
- **How to obtain:**
  ```bash
  az storage account keys list \
    --account-name macaestorageprod \
    --resource-group rg-macae-prod \
    --query [0].value -o tsv
  ```

#### `AZURE_STORAGE_CONNECTION_STRING`
- **Required:** No (alternative to separate name/key)
- **Used by:** Backend, MCP server
- **Description:** Full connection string for storage account
- **Example:** `DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net`

#### `AZURE_STORAGE_CONTAINER_DATASETS`
- **Required:** No
- **Used by:** Backend, MCP server
- **Description:** Blob container name for datasets
- **Default:** `datasets`

---

## Authentication

### `AZURE_AD_CLIENT_ID`
- **Required:** Yes
- **Used by:** Frontend, backend
- **Description:** Azure AD app registration client ID
- **Example:** `abcdef12-3456-7890-abcd-ef1234567890`
- **How to obtain:** See [App Registration Guide](create_new_app_registration.md)

### `AZURE_AD_CLIENT_SECRET`
- **Required:** Yes (backend only)
- **Used by:** Backend
- **Description:** Azure AD app registration client secret
- **Security:** Store in Key Vault, rotate every 90 days
- **How to obtain:**
  ```bash
  az ad app credential reset \
    --id $AZURE_AD_CLIENT_ID \
    --query password -o tsv
  ```

### `AZURE_AD_AUTHORITY`
- **Required:** No
- **Used by:** Backend, frontend
- **Description:** Azure AD authority URL
- **Example:** `https://login.microsoftonline.com/{tenant_id}`
- **Default:** Constructed from `AZURE_TENANT_ID`

### `AZURE_AD_REDIRECT_URI`
- **Required:** Yes (frontend)
- **Used by:** Frontend
- **Description:** OAuth redirect URI after authentication
- **Example:** `https://your-frontend.azurewebsites.net/.auth/login/aad/callback`
- **Must match:** App registration redirect URIs

---

## Application Configuration

### Backend

#### `BACKEND_PORT`
- **Required:** No
- **Used by:** Backend
- **Description:** Port for backend API server
- **Example:** `8000`
- **Default:** `8000`

#### `ALLOWED_ORIGINS`
- **Required:** Yes (production)
- **Used by:** Backend
- **Description:** Comma-separated list of allowed CORS origins
- **Example:** `https://your-frontend.azurewebsites.net,https://custom-domain.com`
- **Default (dev):** `http://localhost:5173,http://localhost:3000`

#### `API_BASE_PATH`
- **Required:** No
- **Used by:** Backend
- **Description:** Base path for API endpoints
- **Example:** `/api/v3`
- **Default:** `/api/v3`

#### `MAX_UPLOAD_SIZE_MB`
- **Required:** No
- **Used by:** Backend
- **Description:** Maximum dataset upload size in MB
- **Example:** `50`
- **Default:** `50`

#### `ENABLE_SWAGGER_UI`
- **Required:** No
- **Used by:** Backend
- **Description:** Enable Swagger/OpenAPI documentation UI
- **Example:** `true`, `false`
- **Default:** `true` (dev), `false` (prod)

### Frontend

#### `VITE_API_BASE_URL`
- **Required:** Yes
- **Used by:** Frontend
- **Description:** Backend API base URL
- **Example:** `https://your-backend.azurecontainerapps.io`
- **Default (dev):** `http://localhost:8000`

#### `VITE_MCP_SERVER_URL`
- **Required:** No
- **Used by:** Frontend
- **Description:** MCP server URL (if accessed directly from browser)
- **Example:** `https://your-mcp-server.azurecontainerapps.io`
- **Default:** Same as backend (proxied)

#### `VITE_APP_TITLE`
- **Required:** No
- **Used by:** Frontend
- **Description:** Application title displayed in UI
- **Example:** `MACAE - Production`
- **Default:** `Multi-Agent Custom Automation Engine`

#### `VITE_ENABLE_ANALYTICS`
- **Required:** No
- **Used by:** Frontend
- **Description:** Enable Application Insights in frontend
- **Example:** `true`, `false`
- **Default:** `true` (prod), `false` (dev)

### MCP Server

#### `MCP_SERVER_PORT`
- **Required:** No
- **Used by:** MCP server
- **Description:** Port for MCP server
- **Example:** `8001`
- **Default:** `8001`

#### `MCP_TOOL_TIMEOUT_SECONDS`
- **Required:** No
- **Used by:** MCP server
- **Description:** Timeout for MCP tool executions
- **Example:** `300`
- **Default:** `300` (5 minutes)

#### `MCP_MAX_CONCURRENT_TOOLS`
- **Required:** No
- **Used by:** MCP server
- **Description:** Maximum concurrent tool executions
- **Example:** `10`
- **Default:** `10`

---

## Monitoring & Logging

### `APPLICATIONINSIGHTS_CONNECTION_STRING`
- **Required:** Yes (production)
- **Used by:** All components
- **Description:** Application Insights connection string
- **Example:** `InstrumentationKey=...;IngestionEndpoint=https://...`
- **Auto-injected:** By Azure when using Container Apps/App Service
- **How to obtain:**
  ```bash
  az monitor app-insights component show \
    --app your-app-insights \
    --resource-group rg-macae-prod \
    --query connectionString -o tsv
  ```

### `LOG_LEVEL`
- **Required:** No
- **Used by:** All components
- **Description:** Logging level
- **Options:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Default:** `INFO` (prod), `DEBUG` (dev)

### `ENABLE_TELEMETRY`
- **Required:** No
- **Used by:** All components
- **Description:** Enable detailed telemetry and tracing
- **Example:** `true`, `false`
- **Default:** `true`

---

## Development & Testing

### `ENVIRONMENT`
- **Required:** No
- **Used by:** All components
- **Description:** Environment name
- **Options:** `development`, `staging`, `production`
- **Default:** `development`

### `DEBUG`
- **Required:** No
- **Used by:** Backend
- **Description:** Enable debug mode
- **Example:** `true`, `false`
- **Default:** `false`
- **Warning:** Never enable in production

### `PYTEST_CURRENT_TEST`
- **Required:** No (set by pytest)
- **Used by:** Test suite
- **Description:** Indicates test environment
- **Auto-set:** By pytest when running tests

---

## Optional Features

### `ENABLE_BING_SEARCH`
- **Required:** No
- **Used by:** MCP server
- **Description:** Enable Bing search grounding
- **Example:** `true`, `false`
- **Default:** `false`
- **Requires:** `BING_SEARCH_API_KEY`

### `BING_SEARCH_API_KEY`
- **Required:** If Bing search enabled
- **Used by:** MCP server
- **Description:** Bing Search API key
- **How to obtain:** See [Bing Search Setup](SetUpGroundingWithBingSearch.md)

### `ENABLE_RATE_LIMITING`
- **Required:** No
- **Used by:** Backend
- **Description:** Enable API rate limiting
- **Example:** `true`, `false`
- **Default:** `true` (prod), `false` (dev)

### `RATE_LIMIT_PER_MINUTE`
- **Required:** No
- **Used by:** Backend
- **Description:** Requests per minute per user
- **Example:** `100`
- **Default:** `100`

---

## Environment-Specific Values

### Development

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
ENABLE_SWAGGER_UI=true
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
VITE_API_BASE_URL=http://localhost:8000
AZURE_LOCATION=eastus

# Use local emulators
COSMOS_DB_ENDPOINT=https://localhost:8081/
COSMOS_DB_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true
```

### Staging

```bash
# .env.staging
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
ENABLE_SWAGGER_UI=true
ALLOWED_ORIGINS=https://staging-frontend.azurewebsites.net
VITE_API_BASE_URL=https://staging-backend.azurecontainerapps.io
AZURE_LOCATION=eastus
AZURE_RESOURCE_GROUP=rg-macae-staging
```

### Production

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
ENABLE_SWAGGER_UI=false
ALLOWED_ORIGINS=https://macae.yourcompany.com
VITE_API_BASE_URL=https://api.macae.yourcompany.com
AZURE_LOCATION=eastus
AZURE_RESOURCE_GROUP=rg-macae-prod
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=100

# All secrets stored in Key Vault
AZURE_OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=https://macae-kv.vault.azure.net/secrets/openai-api-key)
COSMOS_DB_KEY=@Microsoft.KeyVault(SecretUri=https://macae-kv.vault.azure.net/secrets/cosmos-db-key)
```

---

## Quick Reference Table

| Variable | Required | Stored in Key Vault? | Default |
|----------|----------|---------------------|---------|
| `AZURE_SUBSCRIPTION_ID` | ✅ | ❌ | - |
| `AZURE_OPENAI_API_KEY` | ✅ | ✅ | - |
| `COSMOS_DB_KEY` | ✅* | ✅ | - |
| `AZURE_STORAGE_ACCOUNT_KEY` | ✅* | ✅ | - |
| `AZURE_AD_CLIENT_SECRET` | ✅ | ✅ | - |
| `ALLOWED_ORIGINS` | ✅ | ❌ | `*` (dev) |
| `LOG_LEVEL` | ❌ | ❌ | `INFO` |
| `BACKEND_PORT` | ❌ | ❌ | `8000` |

\* Not required if using managed identity

---

## Validation Script

Validate your environment configuration:

```bash
#!/bin/bash
# validate_env.sh

required_vars=(
    "AZURE_SUBSCRIPTION_ID"
    "AZURE_OPENAI_ENDPOINT"
    "AZURE_OPENAI_API_KEY"
    "COSMOS_DB_ENDPOINT"
    "AZURE_STORAGE_ACCOUNT_NAME"
)

missing=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing+=("$var")
    fi
done

if [ ${#missing[@]} -eq 0 ]; then
    echo "✅ All required environment variables are set"
else
    echo "❌ Missing required variables:"
    printf '  - %s\n' "${missing[@]}"
    exit 1
fi
```

---

**Document Version:** 1.0  
**Last Updated:** October 10, 2025

For questions: support@yourcompany.com

