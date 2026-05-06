# ==============================================================================
# MACAE - Local Development Setup Script (Windows PowerShell)
# ==============================================================================
# Automates the entire local development setup for the Multi-Agent Custom
# Automation Engine Solution Accelerator on Windows.
#
# Usage:
#   .\setup_local_dev.ps1 [-ResourceGroup <name>] [-Subscription <id>] [-AzdEnvName <name>] [-AssignRbac] [-SkipVscode]
#
# Examples:
#   .\setup_local_dev.ps1 -ResourceGroup "my-resource-group"
#   .\setup_local_dev.ps1 -AzdEnvName "my-azd-env"
#   .\setup_local_dev.ps1 -ResourceGroup "rg-macae-dev" -AssignRbac
# ==============================================================================

param(
    [string]$ResourceGroup = "",
    [string]$Subscription = "",
    [string]$AzdEnvName = "",
    [switch]$AssignRbac,
    [switch]$SkipVscode
)

$ErrorActionPreference = "Stop"

# Script directory (repo root)
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Get-Location }
$BackendDir = Join-Path $ScriptDir "src\backend"
$McpDir = Join-Path $ScriptDir "src\mcp_server"
$FrontendDir = Join-Path $ScriptDir "src\App"

# ==============================================================================
# Helper Functions
# ==============================================================================

function Write-LogInfo { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Blue }
function Write-LogSuccess { param([string]$Message) Write-Host "[✓] $Message" -ForegroundColor Green }
function Write-LogWarn { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-LogError { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-LogStep { 
    param([string]$Message) 
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
}

function Test-CommandExists {
    param([string]$Command)
    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

# ==============================================================================
# Step 1: Prerequisites
# ==============================================================================

function Check-Prerequisites {
    Write-LogStep "Step 1: Checking Prerequisites"

    $missing = @()

    # Python 3.12+
    if (Test-CommandExists "py") {
        $pyVersion = & py -3.12 --version 2>$null
        if ($pyVersion) {
            Write-LogSuccess "Python 3.12 found: $pyVersion"
        } else {
            $missing += "Python.Python.3.12"
        }
    } elseif (Test-CommandExists "python") {
        $pyVersion = & python --version 2>$null
        if ($pyVersion -match "3\.1[2-9]") {
            Write-LogSuccess "Python found: $pyVersion"
        } else {
            $missing += "Python.Python.3.12"
        }
    } else {
        $missing += "Python.Python.3.12"
    }

    # Node.js
    if (Test-CommandExists "node") {
        Write-LogSuccess "Node.js found: $(node --version)"
    } else {
        $missing += "OpenJS.NodeJS.LTS"
    }

    # npm
    if (Test-CommandExists "npm") {
        Write-LogSuccess "npm found: $(npm --version)"
    } else {
        $missing += "npm (install Node.js)"
    }

    # uv
    if (Test-CommandExists "uv") {
        Write-LogSuccess "uv found: $(uv --version)"
    } else {
        $missing += "uv"
    }

    # Azure CLI
    if (Test-CommandExists "az") {
        Write-LogSuccess "Azure CLI found"
    } else {
        $missing += "Microsoft.AzureCLI"
    }

    # Git
    if (Test-CommandExists "git") {
        Write-LogSuccess "Git found: $(git --version)"
    } else {
        $missing += "Git.Git"
    }

    if ($missing.Count -eq 0) {
        Write-LogSuccess "All prerequisites installed!"
        return
    }

    Write-LogError "Missing prerequisites: $($missing -join ', ')"
    Write-Host ""
    Write-LogWarn "Please install the following before proceeding:"
    Write-Host ""
    foreach ($tool in $missing) {
        switch -Regex ($tool) {
            "Python" {
                Write-Host "  ┌─ Python 3.12 ─────────────────────────────────────────────────"
                Write-Host "  │  Download: https://www.python.org/downloads/"
                Write-Host "  │  Quick install (Windows):"
                Write-Host "  │    winget install Python.Python.3.12"
                Write-Host "  │  Verify: python --version  (should show 3.12.x)"
                Write-Host "  │  Note: During install, CHECK 'Add Python to PATH'"
                Write-Host "  └──────────────────────────────────────────────────────────────"
            }
            "npm|Node" {
                Write-Host "  ┌─ Node.js & npm ───────────────────────────────────────────────"
                Write-Host "  │  Download: https://nodejs.org/ (LTS version)"
                Write-Host "  │  Quick install (Windows):"
                Write-Host "  │    winget install OpenJS.NodeJS.LTS"
                Write-Host "  │  Verify: node --version && npm --version"
                Write-Host "  └──────────────────────────────────────────────────────────────"
            }
            "uv" {
                Write-Host "  ┌─ uv (Python package manager) ─────────────────────────────────"
                Write-Host "  │  Quick install options:"
                Write-Host "  │    Option 1: py -3.12 -m pip install uv"
                Write-Host "  │    Option 2: winget install astral-sh.uv"
                Write-Host "  │    Option 3: irm https://astral.sh/uv/install.ps1 | iex"
                Write-Host "  │  Docs: https://docs.astral.sh/uv/getting-started/installation/"
                Write-Host "  │  Verify: uv --version"
                Write-Host "  └──────────────────────────────────────────────────────────────"
            }
            "AzureCLI" {
                Write-Host "  ┌─ Azure CLI ───────────────────────────────────────────────────"
                Write-Host "  │  Download: https://aka.ms/installazurecliwindows"
                Write-Host "  │  Quick install (Windows):"
                Write-Host "  │    winget install Microsoft.AzureCLI"
                Write-Host "  │  Docs: https://learn.microsoft.com/cli/azure/install-azure-cli"
                Write-Host "  │  Verify: az --version"
                Write-Host "  │  After install: az login"
                Write-Host "  └──────────────────────────────────────────────────────────────"
            }
            "Git" {
                Write-Host "  ┌─ Git ─────────────────────────────────────────────────────────"
                Write-Host "  │  Download: https://git-scm.com/download/win"
                Write-Host "  │  Quick install (Windows):"
                Write-Host "  │    winget install Git.Git"
                Write-Host "  │  Verify: git --version"
                Write-Host "  └──────────────────────────────────────────────────────────────"
            }
        }
    }
    Write-Host ""
    Write-Host "  For detailed step-by-step instructions, see:"
    Write-Host "  https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator/blob/main/docs/LocalDevelopmentSetup.md#step-1-prerequisites---install-required-tools"
    Write-Host ""
    Write-Host "  Also see: docs/NON_DEVCONTAINER_SETUP.md for VS Code extension recommendations."
    Write-Host ""
    Write-LogInfo "After installing, restart your terminal and re-run this script."
    exit 1
}

# ==============================================================================
# Step 2: Azure Authentication
# ==============================================================================

function Check-AzureAuth {
    Write-LogStep "Step 2: Azure Authentication"

    $accountInfo = $null
    try {
        $accountInfo = az account show --output json 2>$null | ConvertFrom-Json
    } catch {}

    if (-not $accountInfo) {
        Write-LogWarn "Not logged into Azure CLI"
        Write-LogInfo "Running 'az login'..."
        az login
        $accountInfo = az account show --output json | ConvertFrom-Json
    }

    if ($Subscription) {
        Write-LogInfo "Setting subscription to: $Subscription"
        az account set --subscription $Subscription
        $accountInfo = az account show --output json | ConvertFrom-Json
    }

    $script:Subscription = $accountInfo.id
    Write-LogSuccess "Logged in to Azure"
    Write-LogInfo "  Subscription: $($accountInfo.name) ($($accountInfo.id))"

    $response = Read-Host "Is this the correct subscription? [Y/n]"
    if ($response -match "^[Nn]") {
        az account list --output table --query "[].{Name:name, Id:id, State:state}"
        $script:Subscription = Read-Host "Enter subscription ID"
        az account set --subscription $script:Subscription
    }
}

# ==============================================================================
# Step 3: Fetch Configuration
# ==============================================================================

function Fetch-Configuration {
    Write-LogStep "Step 3: Fetching Azure Configuration"

    $configSource = ""

    # Priority 1: Resource group provided via parameter
    if ($ResourceGroup) {
        $configSource = "rg"
    }
    # Priority 2: azd env provided
    elseif ($AzdEnvName) {
        $configSource = "azd"
    }
    # Priority 3: Existing .env with valid values - use silently
    elseif (Test-Path (Join-Path $BackendDir ".env")) {
        $envContent = Get-Content (Join-Path $BackendDir ".env") -Raw -ErrorAction SilentlyContinue
        if ($envContent -match "COSMOSDB_ENDPOINT=https://") {
            Write-LogInfo "Existing .env file found with valid configuration. Using it."
            $configSource = "existing"
        }
    }

    # If still not determined, ask for RG name
    if (-not $configSource) {
        Write-Host ""
        Write-LogInfo "No resource group provided and no existing .env found."
        Write-LogInfo "Please provide your Azure Resource Group name (from your deployment)."
        $script:ResourceGroup = Read-Host "Resource Group name"
        if (-not $script:ResourceGroup) {
            Write-LogError "Resource group name is required."
            Write-LogInfo "Usage: .\setup_local_dev.ps1 -ResourceGroup <name>"
            exit 1
        }
        $configSource = "rg"
    }

    switch ($configSource) {
        "azd" { Fetch-FromAzd }
        "rg" { Fetch-FromResourceGroup }
        "existing" {
            if (Test-Path (Join-Path $BackendDir ".env")) {
                Write-LogSuccess "Using existing .env file"
            } else {
                Copy-Item (Join-Path $BackendDir ".env.sample") (Join-Path $BackendDir ".env")
                Write-LogWarn "Created .env from template. Please fill in values and re-run."
                exit 0
            }
        }
    }
}

function Fetch-FromAzd {
    Write-LogInfo "Fetching from azd environment: $AzdEnvName"

    if (-not (Test-CommandExists "azd")) {
        Write-LogError "azd CLI not found. Install from https://aka.ms/azd"
        exit 1
    }

    $azdValues = azd env get-values --environment $AzdEnvName 2>$null
    if (-not $azdValues) {
        Write-LogError "Failed to get values from azd environment '$AzdEnvName'"
        exit 1
    }

    Generate-EnvFile ($azdValues -join "`n")
}

function Fetch-FromResourceGroup {
    Write-LogInfo "Fetching from Resource Group: $ResourceGroup"

    # Validate RG
    $rgExists = az group show --name $ResourceGroup 2>$null
    if (-not $rgExists) {
        Write-LogError "Resource group '$ResourceGroup' not found"
        exit 1
    }

    # Find backend container app
    $containerApps = az containerapp list --resource-group $ResourceGroup --query "[].name" -o tsv 2>$null
    $backendApp = ""

    if ($containerApps) {
        foreach ($app in ($containerApps -split "`n")) {
            $app = $app.Trim()
            if ($app -like "ca-mcp-*") { continue }
            $hasCosmos = az containerapp show --name $app --resource-group $ResourceGroup `
                --query "properties.template.containers[0].env[?name=='COSMOSDB_ENDPOINT'].value" -o tsv 2>$null
            if ($hasCosmos) {
                $backendApp = $app
                break
            }
        }
    }

    if ($backendApp) {
        Write-LogSuccess "Found backend container app: $backendApp"
        $envJson = az containerapp show --name $backendApp --resource-group $ResourceGroup `
            --query "properties.template.containers[0].env" -o json 2>$null

        $envVars = $envJson | ConvertFrom-Json
        $lines = @()
        foreach ($e in $envVars) {
            if ($e.name -and $e.value) {
                $lines += "$($e.name)=$($e.value)"
            }
        }
        Generate-EnvFile ($lines -join "`n")
    } else {
        Write-LogWarn "No backend container app found. Discovering resources..."
        Fetch-FromResources
    }
}

function Fetch-FromResources {
    $subId = az account show --query id -o tsv
    $tenantId = az account show --query tenantId -o tsv

    $cosmosName = az cosmosdb list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    $aiServicesName = az cognitiveservices account list --resource-group $ResourceGroup `
        --query "[?kind=='AIServices' || kind=='CognitiveServices'].name | [0]" -o tsv 2>$null
    $aiProjectName = az cognitiveservices account list --resource-group $ResourceGroup `
        --query "[?kind=='AIProject'].name | [0]" -o tsv 2>$null
    $searchName = az search service list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    $appInsightsKey = az monitor app-insights component list --resource-group $ResourceGroup `
        --query "[0].instrumentationKey" -o tsv 2>$null
    $appInsightsConn = az monitor app-insights component list --resource-group $ResourceGroup `
        --query "[0].connectionString" -o tsv 2>$null
    $storageName = az storage account list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null

    $cosmosEndpoint = if ($cosmosName) { "https://$cosmosName.documents.azure.com:443/" } else { "" }
    $aiEndpoint = if ($aiServicesName) { "https://$aiServicesName.openai.azure.com/" } else { "" }
    $searchEndpoint = if ($searchName) { "https://$searchName.search.windows.net" } else { "" }
    $storageUrl = if ($storageName) { "https://$storageName.blob.core.windows.net/" } else { "" }
    $projectEndpoint = if ($aiServicesName -and $aiProjectName) { "https://$aiServicesName.services.ai.azure.com/api/projects/$aiProjectName" } else { "" }

    $envLines = @"
COSMOSDB_ENDPOINT=$cosmosEndpoint
COSMOSDB_DATABASE=macae
COSMOSDB_CONTAINER=memory
AZURE_OPENAI_ENDPOINT=$aiEndpoint
AZURE_OPENAI_MODEL_NAME=gpt-4.1-mini
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_OPENAI_RAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-12-01-preview
APPLICATIONINSIGHTS_INSTRUMENTATION_KEY=$appInsightsKey
APPLICATIONINSIGHTS_CONNECTION_STRING=$appInsightsConn
AZURE_AI_SUBSCRIPTION_ID=$subId
AZURE_AI_RESOURCE_GROUP=$ResourceGroup
AZURE_AI_PROJECT_NAME=$aiProjectName
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_AI_SEARCH_CONNECTION_NAME=macae-search-connection
AZURE_AI_SEARCH_ENDPOINT=$searchEndpoint
AZURE_TENANT_ID=$tenantId
AZURE_STORAGE_BLOB_URL=$storageUrl
AZURE_AI_PROJECT_ENDPOINT=$projectEndpoint
AZURE_AI_AGENT_ENDPOINT=$projectEndpoint
REASONING_MODEL_NAME=o4-mini
"@

    Generate-EnvFile $envLines
}

function Generate-EnvFile {
    param([string]$RawValues)

    $envFile = Join-Path $BackendDir ".env"
    Write-LogInfo "Generating .env file at: $envFile"

    # Parse into hashtable
    $envVars = @{}
    foreach ($line in ($RawValues -split "`n")) {
        $line = $line.Trim()
        if (-not $line -or $line.StartsWith("#")) { continue }
        $eqIdx = $line.IndexOf("=")
        if ($eqIdx -gt 0) {
            $key = $line.Substring(0, $eqIdx)
            $value = $line.Substring($eqIdx + 1).Trim('"').Trim("'")
            $envVars[$key] = $value
        }
    }

    # Local overrides
    $envVars["APP_ENV"] = "dev"
    $envVars["BACKEND_API_URL"] = "http://localhost:8000"
    $envVars["FRONTEND_SITE_NAME"] = "*"
    $envVars["MCP_SERVER_ENDPOINT"] = "http://localhost:9000/mcp"
    $envVars["MCP_SERVER_NAME"] = "MacaeMcpServer"
    $envVars["MCP_SERVER_DESCRIPTION"] = "MCP server with greeting, HR, and planning tools"

    # Write file
    $content = @"
# ===================================================================
# MACAE Local Development Configuration
# Generated by setup_local_dev.ps1 on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# ===================================================================

# --- Local Development Settings (DO NOT CHANGE) ---
APP_ENV=dev
BACKEND_API_URL=http://localhost:8000
FRONTEND_SITE_NAME=*
MCP_SERVER_ENDPOINT=http://localhost:9000/mcp
MCP_SERVER_NAME=MacaeMcpServer
MCP_SERVER_DESCRIPTION="MCP server with greeting, HR, and planning tools"

# --- Azure Authentication ---
AZURE_TENANT_ID=$($envVars["AZURE_TENANT_ID"])
AZURE_CLIENT_ID=$($envVars["AZURE_CLIENT_ID"])

# --- CosmosDB ---
COSMOSDB_ENDPOINT=$($envVars["COSMOSDB_ENDPOINT"])
COSMOSDB_DATABASE=$($envVars["COSMOSDB_DATABASE"] ?? "macae")
COSMOSDB_CONTAINER=$($envVars["COSMOSDB_CONTAINER"] ?? "memory")

# --- Azure OpenAI ---
AZURE_OPENAI_ENDPOINT=$($envVars["AZURE_OPENAI_ENDPOINT"])
AZURE_OPENAI_MODEL_NAME=$($envVars["AZURE_OPENAI_MODEL_NAME"] ?? "gpt-4.1-mini")
AZURE_OPENAI_DEPLOYMENT_NAME=$($envVars["AZURE_OPENAI_DEPLOYMENT_NAME"] ?? "gpt-4.1-mini")
AZURE_OPENAI_RAI_DEPLOYMENT_NAME=$($envVars["AZURE_OPENAI_RAI_DEPLOYMENT_NAME"] ?? "gpt-4.1")
AZURE_OPENAI_API_VERSION=$($envVars["AZURE_OPENAI_API_VERSION"] ?? "2024-12-01-preview")
REASONING_MODEL_NAME=$($envVars["REASONING_MODEL_NAME"] ?? "o4-mini")
SUPPORTED_MODELS=$($envVars["SUPPORTED_MODELS"] ?? '["o3","o4-mini","gpt-4.1","gpt-4.1-mini"]')

# --- Azure AI Foundry ---
AZURE_AI_SUBSCRIPTION_ID=$($envVars["AZURE_AI_SUBSCRIPTION_ID"])
AZURE_AI_RESOURCE_GROUP=$($envVars["AZURE_AI_RESOURCE_GROUP"])
AZURE_AI_PROJECT_NAME=$($envVars["AZURE_AI_PROJECT_NAME"])
AZURE_AI_PROJECT_ENDPOINT=$($envVars["AZURE_AI_PROJECT_ENDPOINT"])
AZURE_AI_AGENT_ENDPOINT=$($envVars["AZURE_AI_AGENT_ENDPOINT"])
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=$($envVars["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"] ?? "gpt-4.1-mini")
AZURE_AI_AGENT_API_VERSION=$($envVars["AZURE_AI_AGENT_API_VERSION"] ?? "2025-05-01-preview")
AZURE_AI_AGENT_PROJECT_CONNECTION_STRING=$($envVars["AZURE_AI_AGENT_PROJECT_CONNECTION_STRING"])
AZURE_COGNITIVE_SERVICES=$($envVars["AZURE_COGNITIVE_SERVICES"] ?? "https://cognitiveservices.azure.com/.default")

# --- Azure AI Search ---
AZURE_AI_SEARCH_CONNECTION_NAME=$($envVars["AZURE_AI_SEARCH_CONNECTION_NAME"])
AZURE_AI_SEARCH_ENDPOINT=$($envVars["AZURE_AI_SEARCH_ENDPOINT"])

# --- Application Insights ---
APPLICATIONINSIGHTS_INSTRUMENTATION_KEY=$($envVars["APPLICATIONINSIGHTS_INSTRUMENTATION_KEY"])
APPLICATIONINSIGHTS_CONNECTION_STRING=$($envVars["APPLICATIONINSIGHTS_CONNECTION_STRING"])

# --- Storage ---
AZURE_STORAGE_BLOB_URL=$($envVars["AZURE_STORAGE_BLOB_URL"])

# --- Bing ---
AZURE_BING_CONNECTION_NAME=$($envVars["AZURE_BING_CONNECTION_NAME"] ?? "binggrnd")
BING_CONNECTION_NAME=$($envVars["BING_CONNECTION_NAME"] ?? "binggrnd")

# --- Logging ---
AZURE_BASIC_LOGGING_LEVEL=$($envVars["AZURE_BASIC_LOGGING_LEVEL"] ?? "INFO")
AZURE_PACKAGE_LOGGING_LEVEL=$($envVars["AZURE_PACKAGE_LOGGING_LEVEL"] ?? "WARNING")
AZURE_LOGGING_PACKAGES=$($envVars["AZURE_LOGGING_PACKAGES"])
"@

    $content | Out-File -FilePath $envFile -Encoding utf8NoBOM
    Write-LogSuccess ".env file generated successfully"

    # Validate required keys
    $requiredKeys = @("COSMOSDB_ENDPOINT", "AZURE_OPENAI_ENDPOINT", "AZURE_AI_SUBSCRIPTION_ID", "AZURE_AI_RESOURCE_GROUP", "AZURE_AI_PROJECT_NAME", "AZURE_AI_AGENT_ENDPOINT")
    $missingKeys = @()
    foreach ($key in $requiredKeys) {
        if (-not $envVars[$key]) { $missingKeys += $key }
    }
    if ($missingKeys.Count -gt 0) {
        Write-LogWarn "The following required values are empty (edit .env manually):"
        foreach ($k in $missingKeys) { Write-LogWarn "  - $k" }
    }
}

# ==============================================================================
# Step 4: RBAC (Optional)
# ==============================================================================

function Assign-RbacRoles {
    # Always assign RBAC when resource group is known (needed for local dev access)
    if (-not $ResourceGroup) { 
        Write-LogInfo "No resource group specified, skipping RBAC assignment."
        return 
    }

    Write-LogStep "Step 4: Assigning RBAC Roles"

    $userObjectId = az ad signed-in-user show --query id -o tsv 2>$null
    $userUpn = az ad signed-in-user show --query userPrincipalName -o tsv 2>$null

    if (-not $userObjectId) {
        Write-LogError "Could not get user info. Skipping RBAC."
        return
    }

    Write-LogInfo "Assigning roles for: $userUpn ($userObjectId)"
    $subId = az account show --query id -o tsv

    # Cosmos DB (uses its own role system, not ARM RBAC)
    $cosmosName = az cosmosdb list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    if ($cosmosName) {
        # Check if Cosmos role already assigned
        $existingCosmos = az cosmosdb sql role assignment list `
            --resource-group $ResourceGroup --account-name $cosmosName `
            --query "[?principalId=='$userObjectId']" -o tsv 2>$null
        if ($existingCosmos) {
            Write-LogSuccess "  Cosmos DB Data Contributor: already assigned ✓"
        } else {
            Write-LogInfo "  Assigning Cosmos DB Data Contributor..."
            az cosmosdb sql role assignment create `
                --resource-group $ResourceGroup --account-name $cosmosName `
                --role-definition-name "Cosmos DB Built-in Data Contributor" `
                --principal-id $userObjectId `
                --scope "/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.DocumentDB/databaseAccounts/$cosmosName" 2>$null
            if ($LASTEXITCODE -eq 0) { Write-LogSuccess "    Cosmos DB role assigned" }
            else { Write-LogWarn "    Cosmos DB role assignment failed (may need elevated permissions)" }
        }
    }

    # AI Foundry roles
    $aiServicesName = az cognitiveservices account list --resource-group $ResourceGroup `
        --query "[?kind=='AIServices'].name | [0]" -o tsv 2>$null
    $aiProjectName = az cognitiveservices account list --resource-group $ResourceGroup `
        --query "[?kind=='AIProject'].name | [0]" -o tsv 2>$null

    if ($aiServicesName -and $aiProjectName) {
        $scope = "/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$aiServicesName/projects/$aiProjectName"
        foreach ($role in @("Azure AI User", "Azure AI Developer", "Cognitive Services OpenAI User")) {
            $existing = az role assignment list --assignee $userObjectId --role $role --scope $scope --query "[0].id" -o tsv 2>$null
            if ($existing) {
                Write-LogSuccess "  ${role}: already assigned ✓"
            } else {
                Write-LogInfo "  Assigning '$role'..."
                az role assignment create --assignee $userUpn --role $role --scope $scope 2>$null
                if ($LASTEXITCODE -eq 0) { Write-LogSuccess "    $role assigned" }
                else { Write-LogWarn "    $role assignment failed" }
            }
        }
    }

    # Search
    $searchName = az search service list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    if ($searchName) {
        $scope = "/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.Search/searchServices/$searchName"
        $existing = az role assignment list --assignee $userObjectId --role "Search Index Data Contributor" --scope $scope --query "[0].id" -o tsv 2>$null
        if ($existing) {
            Write-LogSuccess "  Search Index Data Contributor: already assigned ✓"
        } else {
            Write-LogInfo "  Assigning Search Index Data Contributor..."
            az role assignment create --assignee $userUpn --role "Search Index Data Contributor" --scope $scope 2>$null
            if ($LASTEXITCODE -eq 0) { Write-LogSuccess "    Search role assigned" }
            else { Write-LogWarn "    Search role assignment failed" }
        }
    }

    # Storage
    $storageName = az storage account list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    if ($storageName) {
        $scope = "/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.Storage/storageAccounts/$storageName"
        $existing = az role assignment list --assignee $userObjectId --role "Storage Blob Data Contributor" --scope $scope --query "[0].id" -o tsv 2>$null
        if ($existing) {
            Write-LogSuccess "  Storage Blob Data Contributor: already assigned ✓"
        } else {
            Write-LogInfo "  Assigning Storage Blob Data Contributor..."
            az role assignment create --assignee $userUpn --role "Storage Blob Data Contributor" --scope $scope 2>$null
            if ($LASTEXITCODE -eq 0) { Write-LogSuccess "    Storage role assigned" }
            else { Write-LogWarn "    Storage role assignment failed" }
        }
    }

    Write-LogWarn "RBAC changes may take 5-10 minutes to propagate"
}

# ==============================================================================
# Step 5-7: Service Setup
# ==============================================================================

function Setup-Backend {
    Write-LogStep "Step 5: Setting up Backend (src\backend)"

    Push-Location $BackendDir

    # Handle existing .venv that may be locked by VS Code or other processes
    if (Test-Path ".venv") {
        Write-LogInfo "Existing .venv found. Checking accessibility..."
        $venvLocked = $false
        try {
            $testFile = ".venv\.uv-lock-test"
            New-Item -Path $testFile -ItemType File -Force -ErrorAction Stop | Out-Null
            Remove-Item $testFile -Force -ErrorAction SilentlyContinue
        } catch {
            $venvLocked = $true
        }

        if ($venvLocked) {
            Write-LogWarn ".venv is locked by another process (likely VS Code Python extension)."
            Write-LogInfo "Attempting to auto-fix by killing locking Python processes..."

            # Find python processes running from this .venv
            $venvFullPath = (Resolve-Path ".venv").Path
            $lockingProcs = Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
                try {
                    $_.Path -and $_.Path.StartsWith($venvFullPath, [System.StringComparison]::OrdinalIgnoreCase)
                } catch { $false }
            }

            if ($lockingProcs) {
                foreach ($proc in $lockingProcs) {
                    Write-LogInfo "  Killing PID $($proc.Id) ($($proc.Path))"
                    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                }
                Start-Sleep -Seconds 2
            }

            # Retry deletion after killing processes
            try {
                Remove-Item -Recurse -Force ".venv" -ErrorAction Stop
                Write-LogInfo "Removed locked .venv successfully."
            } catch {
                Write-LogWarn "Still cannot remove .venv after killing processes."
                Write-LogWarn "Please close VS Code completely and re-run the script."
                Pop-Location
                throw "Cannot modify .venv - files still locked. Close VS Code and retry."
            }
        }
    }

    if (-not (Test-Path ".venv")) {
        Write-LogInfo "Creating virtual environment..."
        uv venv .venv
    }

    Write-LogInfo "Installing dependencies..."
    # Use --no-cache to avoid stale lock issues on Windows
    uv sync --python 3.12 --extra dev

    Write-LogSuccess "Backend setup complete"
    Pop-Location
}

function Setup-McpServer {
    Write-LogStep "Step 6: Setting up MCP Server (src\mcp_server)"

    Push-Location $McpDir

    if (-not (Test-Path ".venv")) {
        Write-LogInfo "Creating virtual environment..."
        uv venv .venv
    }

    Write-LogInfo "Installing dependencies..."
    uv sync --python 3.12

    Write-LogSuccess "MCP Server setup complete"
    Pop-Location
}

function Setup-Frontend {
    Write-LogStep "Step 7: Setting up Frontend (src\App)"

    Push-Location $FrontendDir

    if (-not (Test-Path ".venv")) {
        Write-LogInfo "Creating Python virtual environment..."
        python -m venv .venv
    }

    Write-LogInfo "Installing Python dependencies..."
    & ".\.venv\Scripts\pip.exe" install -q -r requirements.txt

    Write-LogInfo "Installing npm dependencies..."
    npm install

    Write-LogInfo "Building frontend..."
    npm run build

    Write-LogSuccess "Frontend setup complete"
    Pop-Location
}

# ==============================================================================
# Step 8: VS Code
# ==============================================================================

function Setup-VSCode {
    if ($SkipVscode) { return }

    Write-LogStep "Step 8: Configuring VS Code"

    $vscodeDir = Join-Path $ScriptDir ".vscode"
    if (-not (Test-Path $vscodeDir)) { New-Item -ItemType Directory -Path $vscodeDir | Out-Null }

    $extensionsFile = Join-Path $vscodeDir "extensions.json"
    if (-not (Test-Path $extensionsFile)) {
        @'
{
    "recommendations": [
        "ms-python.python",
        "ms-python.pylint",
        "ms-python.black-formatter",
        "ms-python.isort",
        "ms-vscode-remote.remote-wsl",
        "ms-vscode-remote.remote-containers",
        "redhat.vscode-yaml",
        "ms-vscode.azure-account",
        "ms-python.mypy-type-checker"
    ]
}
'@ | Out-File -FilePath $extensionsFile -Encoding utf8NoBOM
        Write-LogSuccess "Created .vscode\extensions.json"
    }

    $settingsFile = Join-Path $vscodeDir "settings.json"
    if (-not (Test-Path $settingsFile)) {
        @'
{
    "python.defaultInterpreterPath": "${workspaceFolder}/src/backend/.venv/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.formatting.provider": "black",
    "python.debugging.logLevel": "Debug",
    "debug.inlineValues": "on",
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    },
    "python.analysis.extraPaths": [
        "${workspaceFolder}/src/backend",
        "${workspaceFolder}/src/mcp_server"
    ]
}
'@ | Out-File -FilePath $settingsFile -Encoding utf8NoBOM
        Write-LogSuccess "Created .vscode\settings.json"
    }
}

# ==============================================================================
# Summary
# ==============================================================================

function Print-Summary {
    Write-LogStep "Setup Complete! 🎉"

    Write-Host "All services have been set up successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "To start the application, open 3 separate PowerShell windows:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Terminal 1 - Backend (port 8000):" -ForegroundColor Yellow
    Write-Host "    cd src\backend"
    Write-Host "    .\.venv\Scripts\Activate.ps1"
    Write-Host "    python app.py"
    Write-Host ""
    Write-Host "  Terminal 2 - MCP Server (port 9000):" -ForegroundColor Yellow
    Write-Host "    cd src\mcp_server"
    Write-Host "    .\.venv\Scripts\Activate.ps1"
    Write-Host "    python mcp_server.py --transport streamable-http --host 0.0.0.0 --port 9000"
    Write-Host ""
    Write-Host "  Terminal 3 - Frontend (port 3000):" -ForegroundColor Yellow
    Write-Host "    cd src\App"
    Write-Host "    .\.venv\Scripts\Activate.ps1"
    Write-Host "    python frontend_server.py"
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  Application URL: http://localhost:3000" -ForegroundColor Green
    Write-Host "  Backend API:     http://localhost:8000" -ForegroundColor Green
    Write-Host "  API Docs:        http://localhost:8000/docs" -ForegroundColor Green
    Write-Host "  MCP Server:      http://localhost:9000" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
}

# ==============================================================================
# Main
# ==============================================================================

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     MACAE - Local Development Setup (Windows)               ║" -ForegroundColor Cyan
Write-Host "║     Multi-Agent Custom Automation Engine                     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Verify repo root
if (-not (Test-Path (Join-Path $ScriptDir "src\backend\app.py"))) {
    Write-LogError "This script must be run from the repository root directory"
    exit 1
}

# Ensure execution policy allows running scripts
$policy = Get-ExecutionPolicy -Scope CurrentUser
if ($policy -eq "Restricted") {
    Write-LogWarn "Execution policy is Restricted. Setting to RemoteSigned..."
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
}

Check-Prerequisites
Check-AzureAuth
Fetch-Configuration
Assign-RbacRoles
Setup-Backend
Setup-McpServer
Setup-Frontend
Setup-VSCode
Print-Summary
