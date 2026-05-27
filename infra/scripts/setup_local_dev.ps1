# ==============================================================================
# MACAE - Local Development Setup Script (Windows PowerShell)
# ==============================================================================
# Automates the entire local development setup for the Multi-Agent Custom
# Automation Engine Solution Accelerator on Windows.
#
# Usage:
#   .\setup_local_dev.ps1 [-ResourceGroup <name>] [-Subscription <id>] [-SkipVscode] [-SkipPrereqs]
#
# Examples:
#   .\setup_local_dev.ps1                                    # auto-detects config from .azure/ folder
#   .\setup_local_dev.ps1 -ResourceGroup "rg-macae-dev"      # fetch config from Azure deployment outputs
#   .\setup_local_dev.ps1 -ResourceGroup "rg-macae-dev" -SkipPrereqs
# ==============================================================================

param(
    [string]$ResourceGroup = "",
    [string]$Subscription = "",
    [switch]$SkipVscode,
    [switch]$SkipPrereqs
)

$ErrorActionPreference = "Stop"

# Resolve repo root (script lives in infra/scripts/)
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Get-Location }
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$BackendDir = Join-Path $RepoRoot "src\backend"
$McpDir = Join-Path $RepoRoot "src\mcp_server"
$FrontendDir = Join-Path $RepoRoot "src\App"

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

    if ($SkipPrereqs) {
        Write-LogInfo "Skipping prerequisite checks (-SkipPrereqs passed)."
        return
    }

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

    # Node.js (npm is bundled with Node — no separate check needed)
    if (Test-CommandExists "node") {
        Write-LogSuccess "Node.js found: $(node --version)"
    } else {
        $missing += "OpenJS.NodeJS.LTS"
    }

    # npm — only warn separately if Node is installed but npm somehow isn't
    if ((Test-CommandExists "node") -and -not (Test-CommandExists "npm")) {
        Write-LogWarn "npm not found despite Node.js being installed — try reinstalling Node.js"
        $missing += "OpenJS.NodeJS.LTS"
    } elseif (Test-CommandExists "npm") {
        Write-LogSuccess "npm found: $(npm --version)"
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

    # Build friendly display names for the error summary
    $friendlyNames = $missing | ForEach-Object {
        switch -Regex ($_) {
            "Python"    { "Python 3.12" }
            "NodeJS"    { "Node.js (LTS)" }
            "npm"       { "npm" }
            "uv"        { "uv (Python package manager)" }
            "AzureCLI"  { "Azure CLI" }
            "Git"       { "Git" }
            default     { $_ }
        }
    }
    Write-LogError "Missing prerequisites: $($friendlyNames -join ', ')"
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
                Write-Host "  │  Quick install options (recommended → fallback):"
                Write-Host "  │    Option 1 (recommended): winget install astral-sh.uv"
                Write-Host "  │    Option 2: irm https://astral.sh/uv/install.ps1 | iex"
                Write-Host "  │    Option 3 (if Python already installed): py -3.12 -m pip install uv"
                Write-Host "  │  Docs: https://docs.astral.sh/uv/getting-started/installation/"
                Write-Host "  │  Verify: uv --version"
                Write-Host "  │  Note: Restart your terminal after install so PATH updates take effect."
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
# Step 2b: Azure Role / Permission Check
# ==============================================================================
#
# This script assigns data-plane roles (Cosmos DB, AI services, AI Search,
# Storage Blob) to the signed-in user. That requires the user to have
# permission to write role assignments at subscription scope:
#   - User Access Administrator OR Role Based Access Control Administrator
#     (or Owner)
# Non-fatal warning: group-inherited roles may not always enumerate.
# ==============================================================================

function Check-AzureRoles {
    Write-LogStep "Step 2b: Checking Azure Roles & Permissions"

    $subId  = az account show --query id -o tsv 2>$null
    $userId = az ad signed-in-user show --query id -o tsv 2>$null
    if (-not $subId -or -not $userId) {
        Write-LogWarn "Could not determine subscription or user identity -- skipping role check."
        return
    }

    $scope = "/subscriptions/$subId"
    $rolesRaw = az role assignment list --assignee $userId --scope $scope `
        --include-inherited --include-groups --query "[].roleDefinitionName" -o tsv 2>$null
    if (-not $rolesRaw) {
        Write-LogWarn "Unable to enumerate role assignments at $scope."
        Write-LogWarn "Required: 'User Access Administrator' OR 'Role Based Access Control Administrator' (or 'Owner') to assign data-plane roles."
        return
    }

    $roles = ($rolesRaw -split "`r?`n" | Where-Object { $_ -ne "" })
    $hasRoleMgmt = ($roles -contains 'Owner') -or ($roles -contains 'User Access Administrator') -or ($roles -contains 'Role Based Access Control Administrator')

    if ($hasRoleMgmt) {
        Write-LogSuccess "Role-assignment permission found (Owner/UAA/RBAC Admin)"
    } else {
        Write-LogWarn "Missing 'User Access Administrator' / 'Role Based Access Control Administrator' (or 'Owner')."
        Write-LogWarn "The Cosmos DB / AI / Search / Storage Blob role assignments performed by this script may fail."
        Write-LogWarn "Ask an admin to pre-assign those roles, or grant the missing role on the subscription."
    }
}

# ==============================================================================
# Step 3: Fetch Configuration
# ==============================================================================

function Fetch-Configuration {
    Write-LogStep "Step 3: Fetching Azure Configuration"

    # PATH 1: Resource group explicitly provided — fetch from Azure deployment outputs
    if ($ResourceGroup) {
        Write-LogInfo "Resource group provided. Fetching config from Azure deployment outputs..."
        Fetch-FromResourceGroup
        return
    }

    # PATH 2: No RG given — look for .azure/<env>/.env written by 'azd up' / local deployment
    Write-LogInfo "No -ResourceGroup provided. Looking for existing config in .azure/ folder..."

    $azdDir = Join-Path $RepoRoot ".azure"
    $azdEnvFile = $null
    $detectedEnvName = ""

    # First try config.json defaultEnvironment (most reliable — set by last 'azd up')
    $configJson = Join-Path $azdDir "config.json"
    if (Test-Path $configJson) {
        try {
            $cfg = Get-Content $configJson -Raw | ConvertFrom-Json
            if ($cfg.defaultEnvironment) {
                $candidate = Join-Path $azdDir "$($cfg.defaultEnvironment)\.env"
                if (Test-Path $candidate) {
                    $azdEnvFile = $candidate
                    $detectedEnvName = $cfg.defaultEnvironment
                }
            }
        } catch {}
    }

    # Fallback: pick the most recently modified .env across all .azure/<env>/ folders
    if (-not $azdEnvFile) {
        $latest = Get-ChildItem -Path $azdDir -Filter ".env" -Recurse -ErrorAction SilentlyContinue |
                  Sort-Object LastWriteTime -Descending |
                  Select-Object -First 1
        if ($latest) {
            $azdEnvFile = $latest.FullName
            $detectedEnvName = $latest.Directory.Name
        }
    }

    if ($azdEnvFile) {
        Write-LogSuccess "Found deployment config '$detectedEnvName': $azdEnvFile"
        $azdFileValues = Get-Content $azdEnvFile -Raw

        # Extract resource group so RBAC step works
        if ($azdFileValues -match 'AZURE_RESOURCE_GROUP="?([^"\r\n]+)"?') {
            $script:ResourceGroup = $Matches[1]
            Write-LogInfo "  Resource Group : $($script:ResourceGroup)"
        }

        Generate-EnvFile $azdFileValues
        return
    }

    # PATH 3: No .env found — prompt user for RG name then fetch from Azure
    Write-Host ""
    Write-LogWarn "No .azure/ config found and no -ResourceGroup provided."
    Write-LogInfo "Please enter your Azure Resource Group name (created during deployment):"
    $script:ResourceGroup = Read-Host "Resource Group name"
    if (-not $script:ResourceGroup) {
        Write-LogError "Resource group name is required."
        Write-LogInfo "Usage: .\setup_local_dev.ps1 -ResourceGroup <name>"
        exit 1
    }
    Fetch-FromResourceGroup
}

function Fetch-FromResourceGroup {
    Write-LogInfo "Fetching configuration from Resource Group: $ResourceGroup"

    # Validate RG exists
    $rgExists = az group show --name $ResourceGroup 2>$null
    if (-not $rgExists) {
        Write-LogError "Resource group '$ResourceGroup' not found"
        exit 1
    }

    # --- Strategy 1: Deployment outputs (single call, exact values from main.bicep) ---
    $deploymentName = az group show --name $ResourceGroup --query "tags.DeploymentName" -o tsv 2>$null
    if ($deploymentName) {
        Write-LogInfo "Found deployment '$deploymentName' — reading outputs..."
        $outputsJson = az deployment group show `
            --resource-group $ResourceGroup `
            --name $deploymentName `
            --query "properties.outputs" -o json 2>$null

        if ($outputsJson) {
            $outputs = $outputsJson | ConvertFrom-Json
            $lines = @()
            foreach ($prop in $outputs.PSObject.Properties) {
                $key   = $prop.Name.ToUpper()   # bicep outputs are already UPPER_CASE
                $value = $prop.Value.value
                if ($key -and ($null -ne $value) -and $value -ne '') {
                    $lines += "$key=$value"
                }
            }
            if ($lines.Count -gt 0) {
                Write-LogSuccess "Read $($lines.Count) values from deployment outputs."
                Generate-EnvFile ($lines -join "`n")
                return
            }
        }
        Write-LogWarn "Deployment outputs empty or unreadable — falling back to resource queries."
    } else {
        Write-LogInfo "No DeploymentName tag on resource group — querying resources directly."
    }

    # --- Strategy 2: Query each resource type individually (fallback) ---
    Write-LogInfo "Querying Azure resources..."
    $subId    = az account show --query id -o tsv
    $tenantId = az account show --query tenantId -o tsv

    # CosmosDB
    $cosmosName = az cosmosdb list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    if ($cosmosName) { Write-LogSuccess "  CosmosDB        : $cosmosName" }
    else             { Write-LogWarn    "  CosmosDB        : not found" }

    # AI Services
    $aiServicesName = az cognitiveservices account list --resource-group $ResourceGroup `
        --query "[?kind=='AIServices' || kind=='CognitiveServices'].name | [0]" -o tsv 2>$null
    if ($aiServicesName) { Write-LogSuccess "  AI Services     : $aiServicesName" }
    else                 { Write-LogWarn    "  AI Services     : not found" }

    # AI Foundry Project
    $aiProjectName = az cognitiveservices account list --resource-group $ResourceGroup `
        --query "[?kind=='AIProject'].name | [0]" -o tsv 2>$null
    if ($aiProjectName) { Write-LogSuccess "  AI Project      : $aiProjectName" }
    else                { Write-LogWarn    "  AI Project      : not found (manual config needed)" }

    # Search Service
    $searchName = az search service list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    if ($searchName) { Write-LogSuccess "  Search Service  : $searchName" }
    else             { Write-LogWarn    "  Search Service  : not found" }

    # Application Insights
    $appInsightsKey  = az monitor app-insights component list --resource-group $ResourceGroup `
        --query "[0].instrumentationKey" -o tsv 2>$null
    $appInsightsConn = az monitor app-insights component list --resource-group $ResourceGroup `
        --query "[0].connectionString" -o tsv 2>$null
    if ($appInsightsKey) { Write-LogSuccess "  App Insights    : found" }
    else                 { Write-LogWarn    "  App Insights    : not found" }

    # Storage Account
    $storageName = az storage account list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    if ($storageName) { Write-LogSuccess "  Storage Account : $storageName" }
    else              { Write-LogWarn    "  Storage Account : not found" }

    # Build endpoint URLs
    $cosmosEndpoint  = if ($cosmosName)     { "https://$cosmosName.documents.azure.com:443/" } else { "" }
    $aiEndpoint      = if ($aiServicesName) { "https://$aiServicesName.openai.azure.com/" }    else { "" }
    $searchEndpoint  = if ($searchName)     { "https://$searchName.search.windows.net" }        else { "" }
    $storageUrl      = if ($storageName)    { "https://$storageName.blob.core.windows.net/" }   else { "" }
    $projectEndpoint = if ($aiServicesName -and $aiProjectName) {
        "https://$aiServicesName.services.ai.azure.com/api/projects/$aiProjectName"
    } else { "" }

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

# Tracks role assignments that failed so the final summary can surface them
$script:FailedRoleAssignments = @()

# Returns $true if the named role definition exists in the given subscription.
# Some Azure subscriptions (older tenants, sovereign clouds, or those where
# the AI Foundry RP is not registered) may be missing newer roles like
# 'Azure AI User' / 'Azure AI Developer'.
function Test-RoleDefinitionExists([string]$roleName, [string]$subId) {
    $def = az role definition list --name $roleName --subscription $subId --query "[0].id" -o tsv 2>$null
    return [bool]$def
}

function Record-RoleFailure([string]$role, [string]$assignee, [string]$scope, [string]$reason) {
    $script:FailedRoleAssignments += [pscustomobject]@{
        Role     = $role
        Assignee = $assignee
        Scope    = $scope
        Reason   = $reason
    }
}

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
            $cosmosScope = "/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.DocumentDB/databaseAccounts/$cosmosName"
            az cosmosdb sql role assignment create `
                --resource-group $ResourceGroup --account-name $cosmosName `
                --role-definition-name "Cosmos DB Built-in Data Contributor" `
                --principal-id $userObjectId `
                --scope $cosmosScope 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-LogSuccess "    Cosmos DB role assigned"
            } else {
                Write-LogWarn "    Cosmos DB role assignment failed (may need elevated permissions)"
                Record-RoleFailure "Cosmos DB Built-in Data Contributor" $userUpn $cosmosScope "AssignmentFailed"
            }
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
                continue
            }
            # Verify the role definition exists in this subscription before trying to assign.
            # Missing roles are common in older subscriptions or sovereign clouds.
            if (-not (Test-RoleDefinitionExists $role $subId)) {
                Write-LogWarn "  ${role}: role definition NOT FOUND in subscription '$subId'"
                Write-LogWarn "    Likely cause: Microsoft.CognitiveServices RP not registered, or AI Foundry role not yet available in this cloud."
                Record-RoleFailure $role $userUpn $scope "RoleDefinitionNotFound"
                continue
            }
            Write-LogInfo "  Assigning '$role'..."
            az role assignment create --assignee $userUpn --role $role --scope $scope 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-LogSuccess "    $role assigned"
            } else {
                Write-LogWarn "    $role assignment failed"
                Record-RoleFailure $role $userUpn $scope "AssignmentFailed"
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
            if ($LASTEXITCODE -eq 0) {
                Write-LogSuccess "    Search role assigned"
            } else {
                Write-LogWarn "    Search role assignment failed"
                Record-RoleFailure "Search Index Data Contributor" $userUpn $scope "AssignmentFailed"
            }
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
            if ($LASTEXITCODE -eq 0) {
                Write-LogSuccess "    Storage role assigned"
            } else {
                Write-LogWarn "    Storage role assignment failed"
                Record-RoleFailure "Storage Blob Data Contributor" $userUpn $scope "AssignmentFailed"
            }
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

    # Check for activate script, not just the directory (handles broken/incomplete venvs)
    if (-not (Test-Path ".venv\Scripts\activate")) {
        if (Test-Path ".venv") { Write-LogWarn "Existing .venv is incomplete (no activate script), recreating..." }
        Write-LogInfo "Creating virtual environment..."
        uv venv --seed .venv
    } else {
        Write-LogInfo "Virtual environment already exists"
    }

    Write-LogInfo "Installing dependencies..."
    uv sync --python 3.12 --extra dev
    if ($LASTEXITCODE -ne 0) {
        Write-LogWarn "uv sync failed; retrying with --refresh..."
        uv sync --python 3.12 --extra dev --refresh
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            throw "Backend 'uv sync' failed after retry. Check network/proxy and that Python 3.12 is on PATH, then re-run."
        }
    }

    Write-LogSuccess "Backend setup complete"
    Pop-Location
}

function Setup-McpServer {
    Write-LogStep "Step 6: Setting up MCP Server (src\mcp_server)"

    Push-Location $McpDir

    # Check for activate script, not just the directory (handles broken/incomplete venvs)
    if (-not (Test-Path ".venv\Scripts\activate")) {
        if (Test-Path ".venv") { Write-LogWarn "Existing .venv is incomplete (no activate script), recreating..." }
        Write-LogInfo "Creating virtual environment..."
        uv venv --seed .venv
    } else {
        Write-LogInfo "Virtual environment already exists"
    }

    Write-LogInfo "Installing dependencies..."
    uv sync --python 3.12
    if ($LASTEXITCODE -ne 0) {
        Write-LogWarn "uv sync failed; retrying with --refresh..."
        uv sync --python 3.12 --refresh
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            throw "MCP Server 'uv sync' failed after retry. Check network/proxy and that Python 3.12 is on PATH, then re-run."
        }
    }

    Write-LogSuccess "MCP Server setup complete"
    Pop-Location
}

function Setup-Frontend {
    Write-LogStep "Step 7: Setting up Frontend (src\App)"

    Push-Location $FrontendDir

    # Check for activate script, not just the directory (handles broken/incomplete venvs)
    if (-not (Test-Path ".venv\Scripts\activate")) {
        if (Test-Path ".venv") { Write-LogWarn "Existing .venv is incomplete (no activate script), recreating..." }
        Write-LogInfo "Creating Python virtual environment..."
        python -m venv --clear .venv
    } else {
        Write-LogInfo "Python virtual environment already exists"
    }

    Write-LogInfo "Installing Python dependencies..."
    & ".venv\Scripts\pip.exe" install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "Frontend 'pip install' failed. Check network/proxy and the Python venv, then re-run."
    }

    Write-LogInfo "Installing npm dependencies..."
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-LogWarn "npm install failed; retrying with --legacy-peer-deps..."
        npm install --legacy-peer-deps
        if ($LASTEXITCODE -ne 0) {
            Pop-Location
            throw "Frontend 'npm install' failed after retry. Check Node.js version (>=18) and your npm registry, then re-run."
        }
    }

    Write-LogInfo "Building frontend..."
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "Frontend 'npm run build' failed. Review the build output above and re-run."
    }

    Write-LogSuccess "Frontend setup complete"
    Pop-Location
}

# ==============================================================================
# Step 8: VS Code
# ==============================================================================

function Setup-VSCode {
    if ($SkipVscode) { return }

    Write-LogStep "Step 8: Configuring VS Code"

    $vscodeDir = Join-Path $RepoRoot ".vscode"
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

    Write-Host ""
    Write-Host "All services have been configured successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  HOW TO START THE APPLICATION" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Open 3 separate terminals and start services in this order:" -ForegroundColor White
    Write-Host ""

    Write-Host "  Terminal 1 - Backend (port 8000):" -ForegroundColor Yellow
    Write-Host "    cd src\backend"
    Write-Host "    Activate virtual environment:"
    Write-Host "      PowerShell : .\.venv\Scripts\Activate.ps1"
    Write-Host "      Git Bash   : source .venv/Scripts/activate"
    Write-Host "      Linux/macOS: source .venv/bin/activate"
    Write-Host "    python app.py"
    Write-Host ""

    Write-Host "  Terminal 2 - MCP Server (port 9000):" -ForegroundColor Yellow
    Write-Host "    cd src\mcp_server"
    Write-Host "    Activate virtual environment:"
    Write-Host "      PowerShell : .\.venv\Scripts\Activate.ps1"
    Write-Host "      Git Bash   : source .venv/Scripts/activate"
    Write-Host "      Linux/macOS: source .venv/bin/activate"
    Write-Host "    python mcp_server.py --transport streamable-http --host 0.0.0.0 --port 9000"
    Write-Host ""

    Write-Host "  Terminal 3 - Frontend (port 3000):" -ForegroundColor Yellow
    Write-Host "    cd src\App"
    Write-Host "    Activate virtual environment:"
    Write-Host "      PowerShell : .\.venv\Scripts\Activate.ps1"
    Write-Host "      Git Bash   : source .venv/Scripts/activate"
    Write-Host "      Linux/macOS: source .venv/bin/activate"
    Write-Host "    python frontend_server.py"
    Write-Host ""

    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  SERVICE URLs" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  Application UI:  http://localhost:3000" -ForegroundColor Green
    Write-Host "  Backend API:     http://localhost:8000" -ForegroundColor Green
    Write-Host "  API Docs:        http://localhost:8000/docs" -ForegroundColor Green
    Write-Host "  MCP Server:      http://localhost:9000" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
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
if (-not (Test-Path (Join-Path $RepoRoot "src\backend\app.py"))) {
    Write-LogError "This script must be run from the repository root directory"
    exit 1
}

# Ensure execution policy allows running scripts
$policy = Get-ExecutionPolicy -Scope CurrentUser
if ($policy -eq "Restricted") {
    Write-LogWarn "Execution policy is Restricted. Setting to RemoteSigned..."
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
}

function Report-FailedRoleAssignments {
    if (-not $script:FailedRoleAssignments -or $script:FailedRoleAssignments.Count -eq 0) { return }

    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host " ⚠  Setup completed, but $($script:FailedRoleAssignments.Count) required role assignment(s) FAILED" -ForegroundColor Red
    Write-Host "    The application will get 403 errors at runtime without these." -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    foreach ($f in $script:FailedRoleAssignments) {
        Write-Host "  • $($f.Role)" -ForegroundColor Yellow
        Write-Host "      Reason : $($f.Reason)"
        Write-Host "      Scope  : $($f.Scope)"
        if ($f.Reason -eq "RoleDefinitionNotFound") {
            Write-Host "      Fix    : Register the resource provider, or have an admin run:"
            Write-Host "               az provider register -n Microsoft.CognitiveServices --wait"
        } else {
            Write-Host "      Fix    : Ask an admin with 'User Access Administrator' (or 'Owner') to run:"
            Write-Host "               az role assignment create --assignee `"$($f.Assignee)`" ``"
            Write-Host "                 --role `"$($f.Role)`" --scope `"$($f.Scope)`""
        }
        Write-Host ""
    }
    Write-Host "Re-run this script once the roles are in place, or pass --resource-group to retry." -ForegroundColor Yellow
    Write-Host ""
    exit 2
}

Check-Prerequisites
Check-AzureAuth
Check-AzureRoles
Fetch-Configuration
Assign-RbacRoles
Setup-Backend
Setup-McpServer
Setup-Frontend
Setup-VSCode
Print-Summary
Report-FailedRoleAssignments
