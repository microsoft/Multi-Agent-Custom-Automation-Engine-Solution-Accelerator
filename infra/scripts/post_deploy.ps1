#Requires -Version 7.0
<#
.SYNOPSIS
    Interactive post-deployment data seeding script (azd postdeploy hook).
    Uploads team configurations via the backend REST API, uploads sample
    blob data, creates AI Search indexes, vector stores, Foundry IQ knowledge
    bases, and KB MCP connections.

.DESCRIPTION
    Mirrors the structure of infra/scripts/Selecting-Team-Config-And-Data.ps1.
    Configuration values are resolved using a 3-tier fallback strategy:
      1. azd env  -> 2. ARM deployment outputs  -> 3. resource naming convention
    Handles WAF deployments by temporarily enabling public network access on
    Storage Account and AI Search Service for the duration of the data
    seeding, then restoring the original setting in a finally block.

.PARAMETER ResourceGroup
    Optional resource group name. If omitted, values come from azd env.

.EXAMPLE
    .\infra\scripts\post_deploy.ps1
    .\infra\scripts\post_deploy.ps1 -ResourceGroup rg-macae-dev
#>

param(
    [string]$ResourceGroup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Variables (script scope so helpers can populate them)
$script:backendUrl                 = ""
$script:storageAccount             = ""
$script:aiSearch                   = ""
$script:aiSearchEndpoint           = ""
$script:openaiEndpoint             = ""
$script:projectEndpoint            = ""
$script:azSubscriptionId           = ""
$script:stIsPublicAccessDisabled   = $false
$script:srchIsPublicAccessDisabled = $false
$script:aiFoundryIsPublicAccessDisabled = $false
$script:aiFoundryAccountName      = ""
$script:aiFoundryResourceGroup    = ""
$script:hasErrors                  = $false

# ──────────────────────────────────────────────────────────────────────────────
# WAF helpers — temporarily enable / restore public network access
# ──────────────────────────────────────────────────────────────────────────────

function Restore-NetworkAccess {
    if (-not $script:ResourceGroup -or -not $script:storageAccount -or -not $script:aiSearch) {
        return
    }

    $rgTypeTag = (az group show --name $script:ResourceGroup --query "tags.Type" -o tsv 2>$null)
    if ($rgTypeTag -ne "WAF") {
        return
    }

    if ($script:stIsPublicAccessDisabled -or $script:srchIsPublicAccessDisabled) {
        Write-Host ""
        Write-Host "=== Restoring network access settings ==="
    }

    if ($script:stIsPublicAccessDisabled) {
        $currentAccess = (az storage account show --name $script:storageAccount --resource-group $script:ResourceGroup --query "publicNetworkAccess" -o tsv 2>$null)
        if ($currentAccess -eq "Enabled") {
            Write-Host "Disabling public access for Storage Account: $($script:storageAccount)"
            az storage account update --name $script:storageAccount --resource-group $script:ResourceGroup --public-network-access disabled --default-action Deny --output none 2>$null
            Write-Host "✓ Storage Account public access disabled"
        } else {
            Write-Host "✓ Storage Account access unchanged (already at desired state)"
        }
    }

    if ($script:srchIsPublicAccessDisabled) {
        $currentAccess = (az search service show --name $script:aiSearch --resource-group $script:ResourceGroup --query "publicNetworkAccess" -o tsv 2>$null)
        if ($currentAccess -eq "Enabled") {
            Write-Host "Disabling public access for AI Search Service: $($script:aiSearch)"
            az search service update --name $script:aiSearch --resource-group $script:ResourceGroup --public-network-access disabled --output none 2>$null
            Write-Host "✓ AI Search Service public access disabled"
        } else {
            Write-Host "✓ AI Search Service access unchanged (already at desired state)"
        }
    }

    if ($script:aiFoundryIsPublicAccessDisabled -and $script:aiFoundryAccountName -and $script:aiFoundryResourceGroup) {
        $currentAccess = (az cognitiveservices account show --name $script:aiFoundryAccountName --resource-group $script:aiFoundryResourceGroup --query "properties.publicNetworkAccess" -o tsv 2>$null)
        if ($currentAccess -eq "Enabled") {
            Write-Host "Disabling public access for AI Foundry: $($script:aiFoundryAccountName)"
            az resource update --resource-group $script:aiFoundryResourceGroup --name $script:aiFoundryAccountName --resource-type "Microsoft.CognitiveServices/accounts" --set properties.publicNetworkAccess=Disabled --output none 2>$null
            Write-Host "✓ AI Foundry public access disabled"
        } else {
            Write-Host "✓ AI Foundry access unchanged (already at desired state)"
        }
    }

    if ($script:stIsPublicAccessDisabled -or $script:srchIsPublicAccessDisabled -or $script:aiFoundryIsPublicAccessDisabled) {
        Write-Host "=========================================="
    }
}

function Enable-PublicAccessIfWaf {
    if (-not $script:ResourceGroup) { return }
    $rgTypeTag = (az group show --name $script:ResourceGroup --query "tags.Type" -o tsv 2>$null)
    if ($rgTypeTag -ne "WAF") { return }

    Write-Host ""
    Write-Host "=== WAF deployment detected — temporarily enabling public network access ==="

    # Storage Account
    $stPublicAccess = (az storage account show --name $script:storageAccount --resource-group $script:ResourceGroup --query "publicNetworkAccess" -o tsv 2>$null)
    if ($stPublicAccess -eq "Disabled") {
        $script:stIsPublicAccessDisabled = $true
        Write-Host "Enabling public access for Storage Account: $($script:storageAccount)"
        az storage account update --name $script:storageAccount --resource-group $script:ResourceGroup --public-network-access enabled --default-action Allow --output none
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: Failed to enable public access for storage account." -ForegroundColor Red
            throw "Failed to enable storage public access"
        }

        Write-Host "Waiting 30 seconds for public access to propagate..."
        Start-Sleep -Seconds 30

        $maxRetries = 10
        for ($i = 0; $i -lt $maxRetries; $i++) {
            $currentAccess = (az storage account show --name $script:storageAccount --resource-group $script:ResourceGroup --query "publicNetworkAccess" -o tsv 2>$null)
            if ($currentAccess -eq "Enabled") {
                Write-Host "✓ Storage Account public access enabled successfully"
                break
            }
            Write-Host "Public access not yet enabled (attempt $($i + 1)/$maxRetries). Waiting 5 seconds..."
            Start-Sleep -Seconds 5
        }
    } else {
        Write-Host "✓ Storage Account public access already enabled"
    }

    # AI Search Service
    $srchPublicAccess = (az search service show --name $script:aiSearch --resource-group $script:ResourceGroup --query "publicNetworkAccess" -o tsv 2>$null)
    if ($srchPublicAccess -eq "Disabled") {
        $script:srchIsPublicAccessDisabled = $true
        Write-Host "Enabling public access for AI Search Service: $($script:aiSearch)"
        az search service update --name $script:aiSearch --resource-group $script:ResourceGroup --public-network-access enabled --output none
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: Failed to enable public access for search service." -ForegroundColor Red
            throw "Failed to enable search public access"
        }

        Write-Host "Waiting 30 seconds for public access to propagate..."
        Start-Sleep -Seconds 30

        $maxRetries = 10
        for ($i = 0; $i -lt $maxRetries; $i++) {
            $currentAccess = (az search service show --name $script:aiSearch --resource-group $script:ResourceGroup --query "publicNetworkAccess" -o tsv 2>$null)
            if ($currentAccess -eq "Enabled") {
                Write-Host "✓ AI Search Service public access enabled successfully"
                break
            }
            Write-Host "Public access not yet enabled (attempt $($i + 1)/$maxRetries). Waiting 5 seconds..."
            Start-Sleep -Seconds 5
        }
    } else {
        Write-Host "✓ AI Search Service public access already enabled"
    }

    # AI Foundry (Cognitive Services account) — name parsed from AZURE_OPENAI_ENDPOINT,
    # RG parsed from AZURE_EXISTING_AI_PROJECT_RESOURCE_ID if set (existing foundry may live in a different RG).
    if ($script:openaiEndpoint -and $script:openaiEndpoint -match '^https?://([^.]+)\.') {
        $script:aiFoundryAccountName = $Matches[1]
    }
    $existingFoundryId = $(azd env get-value AZURE_EXISTING_AI_PROJECT_RESOURCE_ID 2>$null)
    if ($existingFoundryId -and $existingFoundryId -match '/resourceGroups/([^/]+)/') {
        $script:aiFoundryResourceGroup = $Matches[1]
    } else {
        $script:aiFoundryResourceGroup = $script:ResourceGroup
    }

    if ($script:aiFoundryAccountName -and $script:aiFoundryResourceGroup) {
        $foundryPublicAccess = (az cognitiveservices account show --name $script:aiFoundryAccountName --resource-group $script:aiFoundryResourceGroup --query "properties.publicNetworkAccess" -o tsv 2>$null)
        if ($foundryPublicAccess -eq "Disabled") {
            $script:aiFoundryIsPublicAccessDisabled = $true
            Write-Host "Enabling public access for AI Foundry: $($script:aiFoundryAccountName) (RG: $($script:aiFoundryResourceGroup))"
            az resource update --resource-group $script:aiFoundryResourceGroup --name $script:aiFoundryAccountName --resource-type "Microsoft.CognitiveServices/accounts" --set properties.publicNetworkAccess=Enabled --output none
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Error: Failed to enable public access for AI Foundry." -ForegroundColor Red
                throw "Failed to enable AI Foundry public access"
            }

            Write-Host "Waiting 30 seconds for public access to propagate..."
            Start-Sleep -Seconds 30

            $maxRetries = 10
            for ($i = 0; $i -lt $maxRetries; $i++) {
                $currentAccess = (az cognitiveservices account show --name $script:aiFoundryAccountName --resource-group $script:aiFoundryResourceGroup --query "properties.publicNetworkAccess" -o tsv 2>$null)
                if ($currentAccess -eq "Enabled") {
                    Write-Host "✓ AI Foundry public access enabled successfully"
                    break
                }
                Write-Host "Public access not yet enabled (attempt $($i + 1)/$maxRetries). Waiting 5 seconds..."
                Start-Sleep -Seconds 5
            }
        } else {
            Write-Host "✓ AI Foundry public access already enabled"
        }
    } else {
        Write-Host "⚠ Could not determine AI Foundry account name/RG — skipping Foundry public-access toggle."
    }

    Write-Host "==========================================================="
    Write-Host ""
}

# ──────────────────────────────────────────────────────────────────────────────
# Configuration retrieval — 3-tier fallback
# ──────────────────────────────────────────────────────────────────────────────

function Test-AzdInstalled {
    try { $null = Get-Command azd -ErrorAction Stop; return $true } catch { return $false }
}

function Get-DeploymentValue {
    param(
        [object]$DeploymentOutputs,
        [string]$PrimaryKey,
        [string]$FallbackKey
    )
    $value = $null
    if ($DeploymentOutputs.PSObject.Properties[$PrimaryKey]) {
        $value = $DeploymentOutputs.$PrimaryKey.value
    }
    if (-not $value -and $DeploymentOutputs.PSObject.Properties[$FallbackKey]) {
        $value = $DeploymentOutputs.$FallbackKey.value
    }
    return $value
}

function Get-ValuesFromAzdEnv {
    if (-not (Test-AzdInstalled)) {
        Write-Host "Error: Azure Developer CLI (azd) is not installed."
        return $false
    }

    Write-Host "Getting values from azd environment..."

    $script:backendUrl       = $(azd env get-value BACKEND_URL 2>$null)
    $script:storageAccount   = $(azd env get-value AZURE_STORAGE_ACCOUNT_NAME 2>$null)
    $script:aiSearch         = $(azd env get-value AZURE_AI_SEARCH_NAME 2>$null)
    $script:aiSearchEndpoint = $(azd env get-value AZURE_SEARCH_ENDPOINT 2>$null)
    $script:openaiEndpoint   = $(azd env get-value AZURE_OPENAI_ENDPOINT 2>$null)
    $script:projectEndpoint  = $(azd env get-value AZURE_AI_PROJECT_ENDPOINT 2>$null)
    $script:ResourceGroup    = $(azd env get-value AZURE_RESOURCE_GROUP 2>$null)

    if (-not $script:backendUrl -or -not $script:storageAccount -or -not $script:aiSearch -or -not $script:ResourceGroup) {
        Write-Host "Error: Could not retrieve all required values from azd environment."
        return $false
    }

    Write-Host "Successfully retrieved values from azd environment."
    return $true
}

function Get-ValuesFromAzDeployment {
    Write-Host "Getting values from Azure deployment outputs..."

    $deploymentName = az group show --name $script:ResourceGroup --query "tags.DeploymentName" -o tsv 2>$null
    if (-not $deploymentName) {
        Write-Host "Error: Could not find deployment name in resource group tags."
        return $false
    }

    Write-Host "Fetching deployment outputs for deployment: $deploymentName"
    $deploymentOutputs = az deployment group show --resource-group $script:ResourceGroup --name $deploymentName --query "properties.outputs" -o json 2>$null | ConvertFrom-Json
    if (-not $deploymentOutputs) {
        Write-Host "Error: Could not fetch deployment outputs."
        return $false
    }

    $script:storageAccount   = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_STORAGE_ACCOUNT_NAME" -FallbackKey "azureStorageAccountName"
    $script:aiSearch         = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_SEARCH_NAME"       -FallbackKey "azureAiSearchName"
    $script:backendUrl       = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "backenD_URL"                -FallbackKey "backendUrl"
    $script:aiSearchEndpoint = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_SEARCH_ENDPOINT"      -FallbackKey "azureSearchEndpoint"
    $script:openaiEndpoint   = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_OPENAI_ENDPOINT"      -FallbackKey "azureOpenaiEndpoint"
    $script:projectEndpoint  = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azurE_AI_PROJECT_ENDPOINT"  -FallbackKey "azureAiProjectEndpoint"

    if (-not $script:storageAccount -or -not $script:aiSearch -or -not $script:backendUrl) {
        Write-Host "Error: Could not extract all required values from deployment outputs."
        return $false
    }

    Write-Host "Successfully retrieved values from deployment outputs."
    return $true
}

function Get-ValuesUsingSolutionSuffix {
    Write-Host "Getting values from resource naming convention using solution suffix..."

    $solutionSuffix = az group show --name $script:ResourceGroup --query "tags.SolutionSuffix" -o tsv 2>$null
    if (-not $solutionSuffix) {
        Write-Host "Error: Could not find SolutionSuffix tag in resource group."
        return $false
    }

    Write-Host "Found solution suffix: $solutionSuffix"

    $script:storageAccount = ("st$solutionSuffix") -replace '-', ''
    $script:aiSearch       = "srch-$solutionSuffix"
    $containerAppName      = "ca-$solutionSuffix"

    Write-Host "Querying backend URL from Container App..."
    $backendFqdn = az containerapp show --name $containerAppName --resource-group $script:ResourceGroup --query "properties.configuration.ingress.fqdn" -o tsv 2>$null
    if (-not $backendFqdn) {
        Write-Host "Error: Could not get Container App FQDN. Container App may not be deployed yet."
        return $false
    }
    $script:backendUrl = "https://$backendFqdn"

    # Endpoints (best-effort reconstruction; seed scripts will fail loudly if missing)
    $script:aiSearchEndpoint = "https://$($script:aiSearch).search.windows.net"

    if (-not $script:storageAccount -or -not $script:aiSearch -or -not $script:backendUrl) {
        Write-Host "Error: Failed to reconstruct all required resource names."
        return $false
    }

    Write-Host "Successfully reconstructed values from resource naming convention."
    return $true
}

# ──────────────────────────────────────────────────────────────────────────────
# Content pack deployment (blob upload + index creation)
# ──────────────────────────────────────────────────────────────────────────────

function Deploy-ContentPack {
    param(
        [string]$PackPath,
        [string]$StorageAccountName,
        [string]$AiSearchName,
        [string]$PythonCmd
    )

    $packJsonPath = Join-Path $PackPath "pack.json"
    if (-not (Test-Path $packJsonPath)) {
        Write-Host "  No pack.json found at $packJsonPath - skipping data deployment."
        return $true
    }

    $pack = Get-Content $packJsonPath -Raw | ConvertFrom-Json
    Write-Host "  Deploying data for content pack: $($pack.name)"
    $hadFailure = $false

    if ($pack.PSObject.Properties['blob_indexes'] -and $pack.blob_indexes) {
        foreach ($entry in $pack.blob_indexes) {
            $container = $entry.container
            $sourcePath = Join-Path $PackPath $entry.source
            $pattern = if ($entry.pattern) { $entry.pattern } else { "*" }
            $indexName = $entry.index_name

            if (-not (Test-Path $sourcePath)) {
                Write-Host "  Warning: source directory not found: $sourcePath. Skipping."
                $hadFailure = $true
                continue
            }

            az storage container create --account-name $StorageAccountName --name $container --auth-mode login --output none 2>$null
            Write-Host "  Uploading blobs to container '$container'..."
            az storage blob upload-batch --account-name $StorageAccountName --destination $container --source $sourcePath --auth-mode login --pattern $pattern --overwrite --output none
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  Error: Failed to upload blobs to container '$container'."
                $hadFailure = $true
                continue
            }

            Write-Host "  Creating search index '$indexName' from container '$container'..."
            $process = Start-Process -FilePath $PythonCmd -ArgumentList "infra/scripts/index_datasets.py", $StorageAccountName, $container, $AiSearchName, $indexName -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Host "  Error: Indexing failed for '$indexName'."
                $hadFailure = $true
            }
        }
    }

    if ($pack.PSObject.Properties['blob_uploads'] -and $pack.blob_uploads) {
        foreach ($entry in $pack.blob_uploads) {
            $container = $entry.container
            $sourcePath = Join-Path $PackPath $entry.source
            $pattern = if ($entry.pattern) { $entry.pattern } else { "*" }

            if (-not (Test-Path $sourcePath)) {
                Write-Host "  Warning: source directory not found: $sourcePath. Skipping."
                $hadFailure = $true
                continue
            }

            az storage container create --account-name $StorageAccountName --name $container --auth-mode login --output none 2>$null
            Write-Host "  Uploading blobs to container '$container'..."
            az storage blob upload-batch --account-name $StorageAccountName --destination $container --source $sourcePath --auth-mode login --pattern $pattern --overwrite --output none
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  Error: Failed to upload blobs to container '$container'."
                $hadFailure = $true
            }
        }
    }

    if ($pack.PSObject.Properties['search_indexes'] -and $pack.search_indexes) {
        foreach ($entry in $pack.search_indexes) {
            $indexName = $entry.index_name
            $container = $null
            if ($pack.PSObject.Properties['blob_uploads'] -and $pack.blob_uploads.Count -gt 0) {
                $container = $pack.blob_uploads[0].container
            }
            if (-not $container) {
                Write-Host "  Warning: No blob container found for search_index '$indexName'. Skipping."
                continue
            }

            Write-Host "  Creating search index '$indexName' from container '$container'..."
            $process = Start-Process -FilePath $PythonCmd -ArgumentList "infra/scripts/index_datasets.py", $StorageAccountName, $container, $AiSearchName, $indexName -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Host "  Error: Indexing failed for '$indexName'."
                $hadFailure = $true
            }
        }
    }

    return (-not $hadFailure)
}

function Upload-TeamConfig {
    param(
        [string]$Label,
        [string]$TeamConfigDir,
        [string]$TeamId,
        [string]$PythonCmd
    )

    Write-Host ""
    Write-Host "Uploading Team Configuration for $Label..."
    try {
        $process = Start-Process -FilePath $PythonCmd `
            -ArgumentList "infra/scripts/upload_team_config.py", $script:backendUrl, $TeamConfigDir, $script:userPrincipalId, $TeamId `
            -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -ne 0) {
            Write-Host "Error: Team configuration for $Label upload failed." -ForegroundColor Red
            $script:hasErrors = $true
            return $false
        }
    } catch {
        Write-Host "Error: Uploading team configuration failed: $_" -ForegroundColor Red
        $script:hasErrors = $true
        return $false
    }
    Write-Host "Uploaded Team Configuration for $Label."
    return $true
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Post-Deployment Data Seeding" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {

    # ── Authenticate ──────────────────────────────────────────────────────────
    try {
        $null = az account show 2>$null
        Write-Host "Already authenticated with Azure."
    } catch {
        Write-Host "Not authenticated. Logging in..."
        az login
    }

    # ── Resolve subscription (allow user to switch if mismatched) ────────────
    if (Test-AzdInstalled) {
        try {
            $script:azSubscriptionId = $(azd env get-value AZURE_SUBSCRIPTION_ID 2>$null)
            if (-not $script:azSubscriptionId) { $script:azSubscriptionId = $env:AZURE_SUBSCRIPTION_ID }
        } catch { $script:azSubscriptionId = "" }
    }

    $currentSubscriptionId   = az account show --query id   -o tsv
    $currentSubscriptionName = az account show --query name -o tsv

    if ($script:azSubscriptionId -and $currentSubscriptionId -ne $script:azSubscriptionId) {
        Write-Host "Current subscription is $currentSubscriptionName ( $currentSubscriptionId )."
        $confirmation = Read-Host "Do you want to continue with this subscription? (y/n)"
        if ($confirmation -notin @("y", "Y")) {
            $availableSubscriptions = az account list --query "[?state=='Enabled'].[name,id]" --output tsv
            $subscriptions = $availableSubscriptions -split "`n" | ForEach-Object { $_.Split("`t") }

            do {
                Write-Host ""
                Write-Host "Available Subscriptions:"
                Write-Host "========================"
                for ($i = 0; $i -lt $subscriptions.Count; $i += 2) {
                    $index = ($i / 2) + 1
                    Write-Host "$index. $($subscriptions[$i]) ( $($subscriptions[$i + 1]) )"
                }
                Write-Host "========================"

                $subscriptionIndex = Read-Host "Enter the number of the subscription (1-$([int]($subscriptions.Count / 2)))"

                if ($subscriptionIndex -match '^\d+$' -and [int]$subscriptionIndex -ge 1 -and [int]$subscriptionIndex -le ($subscriptions.Count / 2)) {
                    $selectedIndex = ([int]$subscriptionIndex - 1) * 2
                    $selectedSubscriptionName = $subscriptions[$selectedIndex]
                    $selectedSubscriptionId   = $subscriptions[$selectedIndex + 1]
                    az account set --subscription $selectedSubscriptionId
                    Write-Host "Switched to subscription: $selectedSubscriptionName ( $selectedSubscriptionId )"
                    $script:azSubscriptionId = $selectedSubscriptionId
                    break
                } else {
                    Write-Host "Invalid selection. Please try again." -ForegroundColor Red
                }
            } while ($true)
        } else {
            az account set --subscription $currentSubscriptionId
            $script:azSubscriptionId = $currentSubscriptionId
        }
    } else {
        Write-Host "Proceeding with subscription: $currentSubscriptionName ( $currentSubscriptionId )"
        az account set --subscription $currentSubscriptionId
        $script:azSubscriptionId = $currentSubscriptionId
    }

    # ── Resolve config values (3-tier fallback) ───────────────────────────────
    if (-not $ResourceGroup) {
        if (-not (Get-ValuesFromAzdEnv)) {
            Write-Host "Failed to get values from azd environment."
            Write-Host "If you want to use deployment outputs instead, pass -ResourceGroup <name>."
            exit 1
        }
    } else {
        $script:ResourceGroup = $ResourceGroup
        Write-Host "Resource group provided: $ResourceGroup"

        if (-not (Get-ValuesFromAzDeployment)) {
            Write-Host "Warning: Could not retrieve values from deployment outputs. Falling back to naming convention..." -ForegroundColor Yellow
            if (-not (Get-ValuesUsingSolutionSuffix)) {
                Write-Host "Error: Both fallback methods failed." -ForegroundColor Red
                exit 1
            }
        }
    }

    # ── Use case selection ────────────────────────────────────────────────────
    Write-Host ""
    Write-Host "==============================================="
    Write-Host "Available Use Cases:"
    Write-Host "==============================================="
    Write-Host "1. RFP Evaluation"
    Write-Host "2. Retail Customer Satisfaction"
    Write-Host "3. HR Employee Onboarding"
    Write-Host "4. Marketing Press Release"
    Write-Host "5. Contract Compliance Review"
    Write-Host "6. Content Generation"
    Write-Host "7. All"
    Write-Host "==============================================="
    Write-Host ""

    do {
        $useCaseSelection = Read-Host "Please enter the number of the use case you would like to install (1-7)"
        switch ($useCaseSelection) {
            "1" { $selectedUseCase = "RFP Evaluation";              $useCaseValid = $true }
            "2" { $selectedUseCase = "Retail Customer Satisfaction"; $useCaseValid = $true }
            "3" { $selectedUseCase = "HR Employee Onboarding";       $useCaseValid = $true }
            "4" { $selectedUseCase = "Marketing Press Release";      $useCaseValid = $true }
            "5" { $selectedUseCase = "Contract Compliance Review";   $useCaseValid = $true }
            "6" { $selectedUseCase = "Content Generation";           $useCaseValid = $true }
            "7" { $selectedUseCase = "All";                          $useCaseValid = $true }
            "all" { $useCaseSelection = "7"; $selectedUseCase = "All"; $useCaseValid = $true }
            default {
                $useCaseValid = $false
                Write-Host "Invalid selection. Please enter a number from 1-7." -ForegroundColor Red
            }
        }
    } while (-not $useCaseValid)

    Write-Host ""
    Write-Host "==============================================="
    Write-Host "Values to be used:"
    Write-Host "==============================================="
    Write-Host "Selected Use Case: $selectedUseCase"
    Write-Host "Resource Group:    $($script:ResourceGroup)"
    Write-Host "Backend URL:       $($script:backendUrl)"
    Write-Host "Storage Account:   $($script:storageAccount)"
    Write-Host "AI Search:         $($script:aiSearch)"
    Write-Host "AI Project:        $($script:projectEndpoint)"
    Write-Host "Subscription ID:   $($script:azSubscriptionId)"
    Write-Host "==============================================="
    Write-Host ""

    # ── Signed-in user principal id (for backend API auth header) ─────────────
    $script:userPrincipalId = az ad signed-in-user show --query id -o tsv
    if (-not $script:userPrincipalId) {
        Write-Host "Error: Could not retrieve signed-in user principal id." -ForegroundColor Red
        exit 1
    }

    # ── Python environment ────────────────────────────────────────────────────
    $pythonCmd = $null
    try { $v = (python --version 2>&1);  if ($v -match "Python \d") { $pythonCmd = "python" } } catch {}
    if (-not $pythonCmd) {
        try { $v = (python3 --version 2>&1); if ($v -match "Python \d") { $pythonCmd = "python3" } } catch {}
    }
    if (-not $pythonCmd) {
        Write-Host "ERROR: Python not found. Install Python 3.10+ and add it to PATH." -ForegroundColor Red
        exit 1
    }

    $venvPath = "infra/scripts/scriptenv"
    if (-not (Test-Path $venvPath)) {
        Write-Host "Creating virtual environment..."
        & $pythonCmd -m venv $venvPath
    } else {
        Write-Host "Virtual environment already exists. Skipping creation."
    }

    $activateScript = if (Test-Path "$venvPath/Scripts/Activate.ps1") { "$venvPath/Scripts/Activate.ps1" }
                      elseif (Test-Path "$venvPath/bin/Activate.ps1") { "$venvPath/bin/Activate.ps1" }
                      else { $null }
    if ($activateScript) { . $activateScript }

    Write-Host "Installing Python dependencies..."
    pip install --quiet -r infra/scripts/requirements.txt

    # ── Export endpoints as process env vars for seed scripts ────────────────
    # Seed scripts read these via os.environ; we set them here so we don't
    # need to write src/backend/.env.
    if ($script:projectEndpoint)  { $env:AZURE_AI_PROJECT_ENDPOINT = $script:projectEndpoint }
    if ($script:aiSearchEndpoint) { $env:AZURE_AI_SEARCH_ENDPOINT  = $script:aiSearchEndpoint }
    if ($script:openaiEndpoint)   { $env:AZURE_OPENAI_ENDPOINT     = $script:openaiEndpoint }

    # ── WAF: temporarily enable public access for use cases that need data ──
    $usesData = $useCaseSelection -in @("1","2","5","6","7")
    if ($usesData) {
        Enable-PublicAccessIfWaf
    }

    $isTeamConfigFailed = $false
    $isSampleDataFailed = $false

    # ── Use Case 3: HR Onboarding (team config only, no data) ─────────────────
    if ($useCaseSelection -in @("3","7")) {
        if (-not (Upload-TeamConfig -Label "HR Employee Onboarding" `
                    -TeamConfigDir "content_packs/hr_onboarding/agent_teams" `
                    -TeamId "00000000-0000-0000-0000-000000000001" `
                    -PythonCmd $pythonCmd)) {
            $isTeamConfigFailed = $true
        }
    }

    # ── Use Case 4: Marketing Press Release (team config only, no data) ──────
    if ($useCaseSelection -in @("4","7")) {
        if (-not (Upload-TeamConfig -Label "Marketing Press Release" `
                    -TeamConfigDir "content_packs/marketing_press_release/agent_teams" `
                    -TeamId "00000000-0000-0000-0000-000000000002" `
                    -PythonCmd $pythonCmd)) {
            $isTeamConfigFailed = $true
        }
    }

    # ── Use Case 1: RFP Evaluation ────────────────────────────────────────────
    if ($useCaseSelection -in @("1","7")) {
        if (-not (Upload-TeamConfig -Label "RFP Evaluation" `
                    -TeamConfigDir "content_packs/rfp_evaluation/agent_teams" `
                    -TeamId "00000000-0000-0000-0000-000000000004" `
                    -PythonCmd $pythonCmd)) {
            $isTeamConfigFailed = $true
        }

        Write-Host "Deploying data for RFP Evaluation content pack..."
        if (-not (Deploy-ContentPack -PackPath "content_packs/rfp_evaluation" -StorageAccountName $script:storageAccount -AiSearchName $script:aiSearch -PythonCmd $pythonCmd)) {
            Write-Host "Error: Data deployment for RFP Evaluation failed." -ForegroundColor Red
            $isSampleDataFailed = $true
        }
    }

    # ── Use Case 5: Contract Compliance ───────────────────────────────────────
    if ($useCaseSelection -in @("5","7")) {
        if (-not (Upload-TeamConfig -Label "Contract Compliance Review" `
                    -TeamConfigDir "content_packs/contract_compliance/agent_teams" `
                    -TeamId "00000000-0000-0000-0000-000000000005" `
                    -PythonCmd $pythonCmd)) {
            $isTeamConfigFailed = $true
        }

        Write-Host "Deploying data for Contract Compliance content pack..."
        if (-not (Deploy-ContentPack -PackPath "content_packs/contract_compliance" -StorageAccountName $script:storageAccount -AiSearchName $script:aiSearch -PythonCmd $pythonCmd)) {
            Write-Host "Error: Data deployment for Contract Compliance failed." -ForegroundColor Red
            $isSampleDataFailed = $true
        }
    }

    # ── Use Case 2: Retail Customer Satisfaction ──────────────────────────────
    if ($useCaseSelection -in @("2","7")) {
        if (-not (Upload-TeamConfig -Label "Retail Customer Satisfaction" `
                    -TeamConfigDir "content_packs/retail_customer/agent_teams" `
                    -TeamId "00000000-0000-0000-0000-000000000003" `
                    -PythonCmd $pythonCmd)) {
            $isTeamConfigFailed = $true
        }

        Write-Host "Deploying data for Retail Customer content pack..."
        if (-not (Deploy-ContentPack -PackPath "content_packs/retail_customer" -StorageAccountName $script:storageAccount -AiSearchName $script:aiSearch -PythonCmd $pythonCmd)) {
            Write-Host "Error: Data deployment for Retail Customer Satisfaction failed." -ForegroundColor Red
            $isSampleDataFailed = $true
        }
    }

    # ── Use Case 6: Content Generation ────────────────────────────────────────
    if ($useCaseSelection -in @("6","7")) {
        if (-not (Upload-TeamConfig -Label "Content Generation" `
                    -TeamConfigDir "content_packs/content_gen/agent_teams" `
                    -TeamId "00000000-0000-0000-0000-000000000007" `
                    -PythonCmd $pythonCmd)) {
            $isTeamConfigFailed = $true
        }

        Write-Host "Deploying data for Content Generation content pack..."
        if (-not (Deploy-ContentPack -PackPath "content_packs/content_gen" -StorageAccountName $script:storageAccount -AiSearchName $script:aiSearch -PythonCmd $pythonCmd)) {
            Write-Host "Error: Data deployment for Content Generation failed." -ForegroundColor Red
            $isSampleDataFailed = $true
        }
    }

    if ($isTeamConfigFailed -or $isSampleDataFailed) {
        $script:hasErrors = $true
        Write-Host ""
        Write-Host "One or more tasks failed. Please review the messages above." -ForegroundColor Yellow
    }

    # ── Vector stores / Foundry IQ KB / KB MCP connections ──────────────────
    # Scoped to the selected use case via --only filter.
    if ($usesData -and -not $isSampleDataFailed) {

        # Map use case → vector store names (only Retail has vector stores today)
        $vectorStoreMap = @{
            "1" = @()
            "2" = @("macae-retail-customer-data", "macae-retail-order-data")
            "5" = @()
            "6" = @()
            "7" = @("macae-retail-customer-data", "macae-retail-order-data")
        }

        # Map use case → KB names (used for both seed_knowledge_bases and seed_kb_connections)
        $kbMap = @{
            "1" = @("macae-rfp-summary-kb", "macae-rfp-risk-kb", "macae-rfp-compliance-kb")
            "2" = @("macae-retail-customer-kb", "macae-retail-orders-kb")
            "5" = @("macae-contract-summary-kb", "macae-contract-risk-kb", "macae-contract-compliance-kb")
            "6" = @("macae-content-gen-products-kb")
            "7" = @(
                "macae-retail-customer-kb", "macae-retail-orders-kb",
                "macae-content-gen-products-kb",
                "macae-contract-summary-kb", "macae-contract-risk-kb", "macae-contract-compliance-kb",
                "macae-rfp-summary-kb", "macae-rfp-risk-kb", "macae-rfp-compliance-kb"
            )
        }

        $selectedVectorStores = $vectorStoreMap[$useCaseSelection]
        $selectedKbs          = $kbMap[$useCaseSelection]

        # Vector stores — skip entirely if none for this use case
        if ($selectedVectorStores.Count -gt 0) {
            Write-Host ""
            Write-Host "── Creating vector stores ──" -ForegroundColor Green
            $vsFilter = ($selectedVectorStores -join ",")
            $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/seed_vector_stores.py", "--only", $vsFilter -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Host "  ERROR: Vector store creation failed. Run 'python infra/scripts/seed_vector_stores.py --only $vsFilter' manually." -ForegroundColor Red
                $script:hasErrors = $true
            } else {
                Write-Host "  Vector stores created successfully."
            }
        }

        # Knowledge bases + MCP connections
        if ($selectedKbs.Count -gt 0) {
            $kbFilter = ($selectedKbs -join ",")

            Write-Host ""
            Write-Host "── Seeding Foundry IQ Knowledge Bases ──" -ForegroundColor Green
            $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/seed_knowledge_bases.py", "--only", $kbFilter -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Host "  ERROR: Knowledge base seeding failed. Run 'python infra/scripts/seed_knowledge_bases.py --only $kbFilter' manually." -ForegroundColor Red
                $script:hasErrors = $true
            } else {
                Write-Host "  Knowledge bases seeded successfully."
            }

            Write-Host ""
            Write-Host "── Creating KB MCP RemoteTool connections ──" -ForegroundColor Green
            $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/seed_kb_connections.py", "--only", $kbFilter -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Host "  ERROR: KB connection provisioning failed. Run 'python infra/scripts/seed_kb_connections.py --only $kbFilter' manually." -ForegroundColor Red
                $script:hasErrors = $true
            } else {
                Write-Host "  KB MCP connections created successfully."
            }
        }
    }

} finally {
    Write-Host ""
    Restore-NetworkAccess
}

# ──────────────────────────────────────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────────────────────────────────────

if ($script:hasErrors) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " Post-deployment seeding completed with ERRORS" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    $frontendHost = $(azd env get-value webSiteDefaultHostname 2>$null)
    if ($frontendHost) { Write-Host "Frontend: https://$frontendHost" }
    Write-Host ""
    exit 1
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " Post-deployment data seeding complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    $frontendHost = $(azd env get-value webSiteDefaultHostname 2>$null)
    if ($frontendHost) { Write-Host "Frontend: https://$frontendHost" }
    Write-Host ""
}
