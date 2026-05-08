# ==============================================================================
# MACAE - Deploy Local Code to Azure
# ==============================================================================
#
# Usage:
#   .\deploy_to_azure.ps1 -ResourceGroup <name> [options]
#
# Examples:
#   .\deploy_to_azure.ps1 -ResourceGroup rg-macae-dev
#   .\deploy_to_azure.ps1 -ResourceGroup rg-macae-dev -Services "backend,mcp"
#   .\deploy_to_azure.ps1 -ResourceGroup rg-macae-dev -Acr myacr
#   .\deploy_to_azure.ps1 -ResourceGroup rg-macae-dev -DryRun
# ==============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    [string]$Acr = "",
    [string]$Services = "",
    [string]$Tag = "",
    [switch]$DryRun,
    [switch]$BuildOnly,
    [switch]$DeployOnly,
    [switch]$SkipRoleAssignment
)

$ErrorActionPreference = "Stop"

# ==============================================================================
# Configuration
# ==============================================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "src\backend"
$McpDir = Join-Path $ScriptDir "src\mcp_server"
$FrontendDir = Join-Path $ScriptDir "src\App"

$BackendImageName = "macaebackend"
$McpImageName = "macaemcp"
$FrontendImageName = "macaefrontend"

# ==============================================================================
# Logging
# ==============================================================================

function Write-LogInfo    { param([string]$msg) Write-Host "[i] $msg" -ForegroundColor Blue }
function Write-LogSuccess { param([string]$msg) Write-Host "[✓] $msg" -ForegroundColor Green }
function Write-LogWarn    { param([string]$msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-LogError   { param([string]$msg) Write-Host "[✗] $msg" -ForegroundColor Red }
function Write-LogStep    { param([string]$msg) Write-Host "`n━━━ $msg ━━━`n" -ForegroundColor Cyan }

# Retry az command up to 4 times on transient network/operation-in-progress errors
function Invoke-AzRetry {
    param([string[]]$AzArgs)
    $attempt = 1
    while ($attempt -le 4) {
        $out = az @AzArgs 2>&1
        if ($LASTEXITCODE -eq 0) { return $out }
        $outStr = $out -join "`n"
        if ($outStr -match 'OperationInProgress|ContainerAppOperation') {
            Write-LogWarn "Azure operation in progress (attempt $attempt/4), retrying in 30s..." -ForegroundColor Yellow
            Start-Sleep -Seconds 30; $attempt++
        } elseif ($outStr -match 'RemoteDisconnected|Connection aborted|timed out|ECONNRESET|HTTPSConnectionPool|Max retries exceeded|NewConnectionError|getaddrinfo|Failed to establish') {
            Write-LogWarn "Transient network error (attempt $attempt/4), retrying in 15s..."
            Start-Sleep -Seconds 15; $attempt++
        } else {
            return $out
        }
    }
    return $out
}

# ==============================================================================
# Step 1: Prerequisites
# ==============================================================================

function Check-Prerequisites {
    Write-LogStep "Step 1: Checking Prerequisites"

    $missing = @()

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-LogSuccess "Docker found: $(docker --version)"
    } else {
        $missing += "docker"
    }

    if (Get-Command az -ErrorAction SilentlyContinue) {
        Write-LogSuccess "Azure CLI found"
    } else {
        $missing += "azure-cli"
    }

    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-LogSuccess "Git found"
    } else {
        $missing += "git"
    }

    if ($missing.Count -gt 0) {
        Write-LogError "Missing prerequisites: $($missing -join ', ')"
        Write-Host ""
        foreach ($tool in $missing) {
            switch ($tool) {
                "docker" {
                    Write-Host "  ┌─ Docker ──────────────────────────────────────────────────────"
                    Write-Host "  │  Download: https://www.docker.com/products/docker-desktop"
                    Write-Host "  │  Or: winget install Docker.DockerDesktop"
                    Write-Host "  │  Verify: docker --version"
                    Write-Host "  └──────────────────────────────────────────────────────────────"
                }
                "azure-cli" {
                    Write-Host "  ┌─ Azure CLI ───────────────────────────────────────────────────"
                    Write-Host "  │  Download: https://aka.ms/installazurecliwindows"
                    Write-Host "  │  Or: winget install Microsoft.AzureCLI"
                    Write-Host "  │  Verify: az --version"
                    Write-Host "  └──────────────────────────────────────────────────────────────"
                }
                "git" {
                    Write-Host "  ┌─ Git ─────────────────────────────────────────────────────────"
                    Write-Host "  │  Download: https://git-scm.com/download/win"
                    Write-Host "  │  Or: winget install Git.Git"
                    Write-Host "  │  Verify: git --version"
                    Write-Host "  └──────────────────────────────────────────────────────────────"
                }
            }
        }
        exit 1
    }

    # Check Docker daemon
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-LogError "Docker daemon is not running. Please start Docker Desktop and retry."
        exit 1
    }
    Write-LogSuccess "Docker daemon is running"

    # Check Azure login
    $azAccount = az account show 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-LogWarn "Not logged into Azure CLI. Running 'az login'..."
        az login
    }
    Write-LogSuccess "Logged into Azure CLI"
}

# ==============================================================================
# Step 2: Discover Azure Resources
# ==============================================================================

function Discover-Resources {
    Write-LogStep "Step 2: Discovering Azure Resources"

    $rgCheck = az group show --name $ResourceGroup 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-LogError "Resource group '$ResourceGroup' not found."
        exit 1
    }
    Write-LogSuccess "Resource group: $ResourceGroup"

    # Discover container apps
    $caList = az containerapp list --resource-group $ResourceGroup --query "[].name" -o tsv 2>$null

    $script:BackendCA = ""
    $script:McpCA = ""

    if ($caList) {
        foreach ($app in ($caList -split "`n")) {
            $app = $app.Trim()
            if ($app -like "ca-mcp-*") {
                $script:McpCA = $app
            } elseif ($app -like "ca-*") {
                $script:BackendCA = $app
            }
        }
    }

    if ($script:BackendCA) { Write-LogSuccess "Backend Container App: $script:BackendCA" }
    else { Write-LogWarn "Backend Container App: not found in RG" }

    if ($script:McpCA) { Write-LogSuccess "MCP Container App: $script:McpCA" }
    else { Write-LogWarn "MCP Container App: not found in RG" }

    # Discover frontend web app
    $script:FrontendApp = az webapp list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    if ($script:FrontendApp) { Write-LogSuccess "Frontend Web App: $script:FrontendApp" }
    else { Write-LogWarn "Frontend Web App: not found in RG" }

    # Capture current images for rollback
    $script:OldBackendImage = ""
    $script:OldMcpImage = ""
    $script:OldFrontendImage = ""

    if ($script:BackendCA) {
        $script:OldBackendImage = az containerapp show --name $script:BackendCA --resource-group $ResourceGroup `
            --query "properties.template.containers[0].image" -o tsv 2>$null
        Write-LogInfo "Current backend image: $script:OldBackendImage"
    }
    if ($script:McpCA) {
        $script:OldMcpImage = az containerapp show --name $script:McpCA --resource-group $ResourceGroup `
            --query "properties.template.containers[0].image" -o tsv 2>$null
        Write-LogInfo "Current MCP image: $script:OldMcpImage"
    }
    if ($script:FrontendApp) {
        $script:OldFrontendImage = az webapp config show --name $script:FrontendApp --resource-group $ResourceGroup `
            --query "linuxFxVersion" -o tsv 2>$null
        Write-LogInfo "Current frontend image: $script:OldFrontendImage"
    }
}

# ==============================================================================
# Step 3: Resolve ACR
# ==============================================================================

# Resolve ACR resource ID reliably:
# 1. Try with -ResourceGroup (fastest, most reliable for RG-scoped ACRs)
# 2. Try global lookup (for ACRs in a different RG)
# 3. Build from known parts as fallback (handles post-create propagation delay)
function Get-AcrResourceId([string]$acrName, [string]$rg = $ResourceGroup) {
    $id = az acr show --name $acrName --resource-group $rg --query "id" -o tsv 2>$null
    if (-not $id) {
        $id = az acr show --name $acrName --query "id" -o tsv 2>$null
    }
    if (-not $id) {
        $subId = az account show --query id -o tsv 2>$null
        $id = "/subscriptions/$subId/resourceGroups/$rg/providers/Microsoft.ContainerRegistry/registries/$acrName"
    }
    return $id
}

function Resolve-Acr {
    Write-LogStep "Step 3: Resolving Container Registry"

    if ($Acr) {
        # User provided ACR via -Acr flag — try RG-scoped lookup first, then global
        $input = $Acr -replace '\.azurecr\.io$', ''
        $script:AcrName = az acr list --resource-group $ResourceGroup --query "[?name=='$input'].name | [0]" -o tsv 2>$null
        if (-not $script:AcrName) {
            $script:AcrName = az acr show --name $input --query "name" -o tsv 2>$null
        }
        if (-not $script:AcrName) {
            Write-LogError "ACR '$Acr' not found or not accessible."
            exit 1
        }
        $script:AcrLoginServer = az acr show --name $script:AcrName --query "loginServer" -o tsv 2>$null
        if (-not $script:AcrLoginServer) { $script:AcrLoginServer = az acr show --name $script:AcrName --resource-group $ResourceGroup --query "loginServer" -o tsv 2>$null }
        $script:AcrId = Get-AcrResourceId $script:AcrName
        Write-LogSuccess "Using specified ACR: $script:AcrName ($script:AcrLoginServer)"
        Assign-AcrPullRoles
        return
    }

    # Always ask first — no pre-discovery
    Write-Host ""
    $userAcr = Read-Host "Enter ACR name to use (or press Enter to see available ACRs / create new)"

    if ($userAcr) {
        $input = $userAcr -replace '\.azurecr\.io$', ''
        $script:AcrName = az acr show --name $input --query "name" -o tsv 2>$null
        if (-not $script:AcrName) {
            Write-LogError "ACR '$userAcr' not found or not accessible."
            exit 1
        }
        $script:AcrLoginServer = az acr show --name $script:AcrName --resource-group $ResourceGroup --query "loginServer" -o tsv 2>$null
        if (-not $script:AcrLoginServer) { $script:AcrLoginServer = az acr show --name $script:AcrName --query "loginServer" -o tsv 2>$null }
        $script:AcrId = Get-AcrResourceId $script:AcrName
        Write-LogSuccess "Using ACR: $script:AcrName ($script:AcrLoginServer)"
        Assign-AcrPullRoles
        return
    }

    # Empty input — discover what's in the RG and auto-select or auto-create
    Write-LogInfo "Looking for ACR(s) in resource group '$ResourceGroup'..."
    $foundAcrs = @(az acr list --resource-group $ResourceGroup --query "[].name" -o tsv 2>$null | Where-Object { $_ })

    if ($foundAcrs.Count -gt 0) {
        $script:AcrName = $foundAcrs[0]
        $script:AcrLoginServer = az acr show --name $script:AcrName --resource-group $ResourceGroup --query "loginServer" -o tsv
        $script:AcrId = Get-AcrResourceId $script:AcrName
        Write-LogSuccess "Found and using ACR: $script:AcrName ($script:AcrLoginServer)"
        Assign-AcrPullRoles
    } else {
        # Create new ACR in the same RG
        $suffix = ($ResourceGroup -replace '[^a-zA-Z0-9]', '').Substring(0, [Math]::Min(15, ($ResourceGroup -replace '[^a-zA-Z0-9]', '').Length))
        $ts = (Get-Date).ToString("HHmmss")
        $newAcrName = ("acr$suffix$ts").ToLower().Substring(0, [Math]::Min(50, ("acr$suffix$ts").Length))

        Write-LogInfo "Creating ACR: $newAcrName in $ResourceGroup..."
        az acr create `
            --resource-group $ResourceGroup `
            --name $newAcrName `
            --sku Basic `
            --admin-enabled false `
            --output none

        $script:AcrName = $newAcrName
        $script:AcrLoginServer = az acr show --name $script:AcrName --resource-group $ResourceGroup --query "loginServer" -o tsv
        $script:AcrId = Get-AcrResourceId $script:AcrName
        Write-LogSuccess "Created ACR: $script:AcrName ($script:AcrLoginServer)"
        Assign-AcrPullRoles
    }
}

# ==============================================================================
# ACR Pull Role Assignment
# ==============================================================================

function Assign-AcrPullRoles {
    if ($SkipRoleAssignment) {
        Write-LogInfo "Skipping AcrPull role assignment (-SkipRoleAssignment set)."
        return
    }

    Write-LogInfo "Assigning AcrPull role to service identities..."

    if (-not $script:AcrId) {
        Write-LogError "ACR resource ID is empty — cannot assign roles. Aborting."
        exit 1
    }

    $acrPullRole = "7f951dda-4ed3-4680-a7ca-43fe172d538d"
    $anyFailed = $false

    # Helper: resolve principal ID from a Container App (system-assigned first, then user-assigned)
    function Get-CAPrincipalId([string]$caName) {
        $id = az containerapp show --name $caName --resource-group $ResourceGroup `
            --query "identity.principalId" -o tsv 2>$null
        if (-not $id -or $id -eq "null") {
            $id = az containerapp show --name $caName --resource-group $ResourceGroup `
                --query "identity.userAssignedIdentities.*.principalId | [0]" -o tsv 2>$null
        }
        return $id
    }

    function Assign-Role([string]$identity, [string]$label) {
        $existing = az role assignment list --assignee $identity --role $acrPullRole --scope $script:AcrId --query "[0].id" -o tsv 2>$null
        if (-not $existing) {
            $createOutput = az role assignment create --assignee $identity --role $acrPullRole --scope $script:AcrId --output none 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-LogError "  Failed to assign AcrPull to $label identity"
                Write-LogError "  Azure: $createOutput"
                $script:RoleFailed = $true
            } else {
                Write-LogSuccess "  AcrPull assigned to $label identity"
            }
        } else {
            Write-LogInfo "  AcrPull already assigned to $label identity ✓"
        }
    }

    $script:RoleFailed = $false

    # Backend
    if ($script:BackendCA) {
        $identity = Get-CAPrincipalId $script:BackendCA
        if ($identity -and $identity -ne "null") {
            Assign-Role $identity "backend"
        } else {
            Write-LogWarn "  No identity found on backend Container App — cannot assign AcrPull"
            $script:RoleFailed = $true
        }
    }

    # MCP
    if ($script:McpCA) {
        $identity = Get-CAPrincipalId $script:McpCA
        if ($identity -and $identity -ne "null") {
            Assign-Role $identity "MCP"
        } else {
            Write-LogWarn "  No identity found on MCP Container App — cannot assign AcrPull"
            $script:RoleFailed = $true
        }
    }

    # Frontend
    if ($script:FrontendApp) {
        $identity = az webapp show --name $script:FrontendApp --resource-group $ResourceGroup `
            --query "identity.principalId" -o tsv 2>$null
        if (-not $identity -or $identity -eq "null") {
            $identity = az webapp show --name $script:FrontendApp --resource-group $ResourceGroup `
                --query "identity.userAssignedIdentities.*.principalId | [0]" -o tsv 2>$null
        }
        if ($identity -and $identity -ne "null") {
            Assign-Role $identity "frontend"
        } else {
            Write-LogWarn "  No identity found on frontend Web App — cannot assign AcrPull"
            $script:RoleFailed = $true
        }
    }

    if ($script:RoleFailed) {
        Write-Host ""
        Write-LogError "One or more AcrPull role assignments failed."
        Write-LogError "The container(s) will NOT be able to pull images from $($script:AcrLoginServer)."
        Write-LogError ""
        Write-LogError "This usually means your account lacks 'Microsoft.Authorization/roleAssignments/write'."
        Write-LogError "Ask your subscription Owner to grant you 'User Access Administrator' on the RG,"
        Write-LogError "or run:  az role assignment create --assignee <your-object-id> --role 'Owner' --scope /subscriptions/<sub-id>"
        Write-LogError ""
        Write-LogError "If AcrPull roles are already assigned, re-run with: -SkipRoleAssignment"
        exit 1
    }
}

# ==============================================================================
# Step 4: Determine Services
# ==============================================================================

function Get-ChangedServices {
    # Only detect uncommitted changes (staged + unstaged vs last commit).
    # We intentionally skip 'commits ahead of origin/main' to avoid false positives
    # from other work on the feature branch that the user hasn't actively changed.
    $changed = git diff --name-only HEAD 2>$null
    if (-not $changed) { return @() }

    $services = @()
    if ($changed -match '^src/backend/')    { $services += "backend" }
    if ($changed -match '^src/mcp_server/') { $services += "mcp" }
    if ($changed -match '^src/App/')        { $services += "frontend" }
    return $services
}

function Determine-Services {
    Write-LogStep "Step 4: Determining Services to Deploy"

    $script:DeployBackend = $false
    $script:DeployMcp = $false
    $script:DeployFrontend = $false

    if ($Services) {
        foreach ($svc in ($Services -split ',')) {
            $svc = $svc.Trim().ToLower()
            switch ($svc) {
                "backend"  { $script:DeployBackend = $true }
                "mcp"      { $script:DeployMcp = $true }
                "frontend" { $script:DeployFrontend = $true }
                default    { Write-LogWarn "Unknown service: $svc (valid: backend, mcp, frontend)" }
            }
        }
    } else {
        # Auto-detect changed services from git
        Write-LogInfo "No -Services specified — detecting changed services via git..."
        $detected = Get-ChangedServices

        if ($detected.Count -gt 0) {
            Write-LogInfo "Git detected changes in: $($detected -join ', ')"
            foreach ($svc in $detected) {
                switch ($svc) {
                    "backend"  { $script:DeployBackend = $true }
                    "mcp"      { $script:DeployMcp = $true }
                    "frontend" { $script:DeployFrontend = $true }
                }
            }
        } else {
            Write-LogWarn "No service-specific changes detected (no git diff vs HEAD or origin/main)."
            Write-Host ""
            $confirm = Read-Host "No changes detected. Deploy all services anyway? [y/N]"
            if ($confirm -match '^[Yy](es)?$') {
                $script:DeployBackend = $true
                $script:DeployMcp = $true
                $script:DeployFrontend = $true
            } else {
                Write-LogInfo "Nothing to deploy. Exiting."
                exit 0
            }
        }
    }

    Write-Host "  Services to deploy:"
    if ($script:DeployBackend)  { Write-Host "    ✓ Backend" } else { Write-Host "    ○ Backend (skipped)" }
    if ($script:DeployMcp)      { Write-Host "    ✓ MCP Server" } else { Write-Host "    ○ MCP Server (skipped)" }
    if ($script:DeployFrontend) { Write-Host "    ✓ Frontend" } else { Write-Host "    ○ Frontend (skipped)" }
}

# ==============================================================================
# Step 5: Generate Tag
# ==============================================================================

function Generate-Tag {
    Write-LogStep "Step 5: Generating Image Tag"

    if ($Tag) {
        $script:ImageTag = $Tag
    } else {
        $timestamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
        $gitSha = git rev-parse --short=7 HEAD 2>$null
        if (-not $gitSha) { $gitSha = "unknown" }
        $script:ImageTag = "$timestamp-$gitSha"
    }

    Write-LogSuccess "Image tag: $script:ImageTag"
}

# ==============================================================================
# Step 6: Build & Push
# ==============================================================================

function Build-AndPush {
    Write-LogStep "Step 6: Building & Pushing Docker Images"

    if ($DeployOnly) {
        Write-LogInfo "Skipping build (--DeployOnly mode)"
        return
    }

    # Login to ACR
    Write-LogInfo "Logging into ACR: $script:AcrName..."
    az acr login --name $script:AcrName
    Write-LogSuccess "ACR login successful"

    $env:DOCKER_BUILDKIT = "1"

    if ($script:DeployBackend) {
        $fullImage = "$($script:AcrLoginServer)/$BackendImageName`:$($script:ImageTag)"
        Write-LogInfo "Building backend image: $fullImage"
        if ($DryRun) {
            Write-LogInfo "[DRY RUN] Would build: docker build -t $fullImage $BackendDir"
        } else {
            docker build -t $fullImage $BackendDir
            if ($LASTEXITCODE -ne 0) { Write-LogError "Backend image build FAILED"; exit 1 }
            Write-LogSuccess "Backend image built"
            docker push $fullImage
            if ($LASTEXITCODE -ne 0) { Write-LogError "Backend image push FAILED"; exit 1 }
            Write-LogSuccess "Backend image pushed: $fullImage"
        }
    }

    if ($script:DeployMcp) {
        $fullImage = "$($script:AcrLoginServer)/$McpImageName`:$($script:ImageTag)"
        Write-LogInfo "Building MCP image: $fullImage"
        if ($DryRun) {
            Write-LogInfo "[DRY RUN] Would build: docker build -t $fullImage $McpDir"
        } else {
            docker build -t $fullImage $McpDir
            if ($LASTEXITCODE -ne 0) { Write-LogError "MCP image build FAILED"; exit 1 }
            Write-LogSuccess "MCP image built"
            docker push $fullImage
            if ($LASTEXITCODE -ne 0) { Write-LogError "MCP image push FAILED"; exit 1 }
            Write-LogSuccess "MCP image pushed: $fullImage"
        }
    }

    if ($script:DeployFrontend) {
        $fullImage = "$($script:AcrLoginServer)/$FrontendImageName`:$($script:ImageTag)"
        Write-LogInfo "Building frontend image: $fullImage"
        if ($DryRun) {
            Write-LogInfo "[DRY RUN] Would build: docker build -t $fullImage $FrontendDir"
        } else {
            docker build -t $fullImage $FrontendDir
            if ($LASTEXITCODE -ne 0) { Write-LogError "Frontend image build FAILED"; exit 1 }
            Write-LogSuccess "Frontend image built"
            docker push $fullImage
            if ($LASTEXITCODE -ne 0) { Write-LogError "Frontend image push FAILED"; exit 1 }
            Write-LogSuccess "Frontend image pushed: $fullImage"
        }
    }

    if ($BuildOnly) {
        Write-LogSuccess "Build & push complete (-BuildOnly mode, skipping Azure update)"
    }
}

# ==============================================================================
# Step 7: Configure ACR on Resources (if changed)
# ==============================================================================

function Set-CaRegistry([string]$caName, [string]$label) {
    # Skip if registry + identity already correctly configured
    $currentServer = az containerapp show --name $caName --resource-group $ResourceGroup `
        --query "properties.configuration.registries[0].server" -o tsv 2>$null
    $currentIdentity = az containerapp show --name $caName --resource-group $ResourceGroup `
        --query "properties.configuration.registries[0].identity" -o tsv 2>$null
    if ($currentServer -eq $script:AcrLoginServer -and $currentIdentity -and $currentIdentity -ne "null") {
        Write-LogSuccess "$label`: ACR registry already configured — skipping"
        return
    }
    $identityId = az containerapp show --name $caName --resource-group $ResourceGroup `
        --query "identity.userAssignedIdentities | keys(@) | [0]" -o tsv 2>$null
    $identityArg = if ($identityId -and $identityId -ne "null") { $identityId } else { "system" }
    Write-LogInfo "Configuring $label registry → $($script:AcrLoginServer)..."
    $regOut = az containerapp registry set --name $caName --resource-group $ResourceGroup `
        --server $script:AcrLoginServer --identity $identityArg --output none 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-LogSuccess "$label registry configured"
    } elseif ($regOut -match 'Operation expired|OperationInProgress|ContainerAppOperation|HTTPSConnectionPool|Max retries exceeded|NewConnectionError|getaddrinfo|Failed to establish|RemoteDisconnected|Connection aborted') {
        Write-LogWarn "$label registry config accepted but status polling failed (network/timeout). The app will pull correctly once the revision is ready."
    } else {
        Write-LogError "$label registry set FAILED — $regOut"
        throw "$label registry set failed"
    }
}

function Configure-AcrOnResources {
    if ($script:DeployBackend -and $script:BackendCA) {
        if ($DryRun) { Write-LogInfo "[DRY RUN] Would configure backend registry" }
        else { Set-CaRegistry $script:BackendCA "Backend" }
    }
    if ($script:DeployMcp -and $script:McpCA) {
        if ($DryRun) { Write-LogInfo "[DRY RUN] Would configure MCP registry" }
        else { Set-CaRegistry $script:McpCA "MCP" }
    }
    if ($script:DeployFrontend -and $script:FrontendApp) {
        if ($DryRun) { Write-LogInfo "[DRY RUN] Would update frontend App Service registry config" }
        else {
            Write-LogInfo "Updating frontend App Service registry config..."
            az webapp config appsettings set --name $script:FrontendApp --resource-group $ResourceGroup `
                --settings DOCKER_REGISTRY_SERVER_URL="https://$($script:AcrLoginServer)" --output none
            az webapp config set --name $script:FrontendApp --resource-group $ResourceGroup `
                --generic-configurations '{\"acrUseManagedIdentityCreds\": true}' --output none
            if ($LASTEXITCODE -ne 0) {
                Write-LogError "Frontend registry config FAILED — image pull may fail."
            } else {
                Write-LogSuccess "Frontend registry config updated"
            }
        }
    }
}

# ==============================================================================
# Step 8: Update Azure Resources
# ==============================================================================

function Update-AzureResources {
    Write-LogStep "Step 7: Updating Azure Resources"

    if ($BuildOnly) { return }

    Configure-AcrOnResources

    # Backend
    if ($script:DeployBackend) {
        if (-not $script:BackendCA) {
            Write-LogWarn "No backend Container App found — skipping backend deployment"
        } else {
            $fullImage = "$($script:AcrLoginServer)/$BackendImageName`:$($script:ImageTag)"
            Write-LogInfo "Updating backend: $($script:BackendCA) → $fullImage"
            if ($DryRun) {
                Write-LogInfo "[DRY RUN] Would run: az containerapp update --name $($script:BackendCA) --image $fullImage"
            } else {
                $updOut = Invoke-AzRetry @('containerapp','update','--name',$script:BackendCA,'--resource-group',$ResourceGroup,'--image',$fullImage,'--output','none')
                if ($LASTEXITCODE -eq 0) {
                    Write-LogSuccess "Backend updated successfully"
                } elseif ($updOut -match 'Operation expired|OperationInProgress|ContainerAppOperation|HTTPSConnectionPool|Max retries exceeded|NewConnectionError|getaddrinfo|Failed to establish|RemoteDisconnected|Connection aborted') {
                    Write-LogWarn "Backend image update accepted but status polling failed (network/timeout). Azure will complete provisioning shortly."
                } else {
                    Write-LogError "Backend update failed: $updOut"; throw "Backend update failed"
                }
            }
        }
    }

    # MCP
    if ($script:DeployMcp) {
        if (-not $script:McpCA) {
            Write-LogWarn "No MCP Container App found — skipping MCP deployment"
        } else {
            $fullImage = "$($script:AcrLoginServer)/$McpImageName`:$($script:ImageTag)"
            Write-LogInfo "Updating MCP: $($script:McpCA) → $fullImage"
            if ($DryRun) {
                Write-LogInfo "[DRY RUN] Would run: az containerapp update --name $($script:McpCA) --image $fullImage"
            } else {
                $updOut = Invoke-AzRetry @('containerapp','update','--name',$script:McpCA,'--resource-group',$ResourceGroup,'--image',$fullImage,'--output','none')
                if ($LASTEXITCODE -eq 0) {
                    Write-LogSuccess "MCP updated successfully"
                } elseif ($updOut -match 'Operation expired|OperationInProgress|ContainerAppOperation|HTTPSConnectionPool|Max retries exceeded|NewConnectionError|getaddrinfo|Failed to establish|RemoteDisconnected|Connection aborted') {
                    Write-LogWarn "MCP image update accepted but status polling failed (network/timeout). Azure will complete provisioning shortly."
                } else {
                    Write-LogError "MCP update failed: $updOut"; throw "MCP update failed"
                }
            }
        }
    }

    # Frontend
    if ($script:DeployFrontend) {
        if (-not $script:FrontendApp) {
            Write-LogWarn "No Frontend Web App found — skipping frontend deployment"
        } else {
            $fullImage = "$($script:AcrLoginServer)/$FrontendImageName`:$($script:ImageTag)"
            Write-LogInfo "Updating frontend: $($script:FrontendApp) → $fullImage"
            if ($DryRun) {
                Write-LogInfo "[DRY RUN] Would run: az webapp config container set + restart"
            } else {
                az webapp config container set `
                    --name $script:FrontendApp `
                    --resource-group $ResourceGroup `
                    --container-image-name $fullImage `
                    --container-registry-url "https://$($script:AcrLoginServer)" `
                    --output none

                Write-LogInfo "Restarting frontend App Service..."
                az webapp restart --name $script:FrontendApp --resource-group $ResourceGroup --output none
                Write-LogSuccess "Frontend updated and restarted"
            }
        }
    }
}

# ==============================================================================
# Summary
# ==============================================================================

function Print-Summary {
    Write-LogStep "Deployment Summary"

    Write-Host "  Resource Group:  $ResourceGroup"
    Write-Host "  ACR:             $($script:AcrLoginServer)"
    Write-Host "  Image Tag:       $($script:ImageTag)"
    Write-Host ""

    if ($script:DeployBackend -and $script:BackendCA) {
        Write-Host "  Backend:         $($script:AcrLoginServer)/$BackendImageName`:$($script:ImageTag)"
    }
    if ($script:DeployMcp -and $script:McpCA) {
        Write-Host "  MCP:             $($script:AcrLoginServer)/$McpImageName`:$($script:ImageTag)"
    }
    if ($script:DeployFrontend -and $script:FrontendApp) {
        Write-Host "  Frontend:        $($script:AcrLoginServer)/$FrontendImageName`:$($script:ImageTag)"
    }

    Write-Host ""
    Write-Host "  ┌─ Rollback Commands (if needed) ───────────────────────────────"

    if ($script:DeployBackend -and $script:BackendCA -and $script:OldBackendImage) {
        Write-Host "  │  Backend:  az containerapp update --name $($script:BackendCA) --resource-group $ResourceGroup --image $($script:OldBackendImage)"
    }
    if ($script:DeployMcp -and $script:McpCA -and $script:OldMcpImage) {
        Write-Host "  │  MCP:      az containerapp update --name $($script:McpCA) --resource-group $ResourceGroup --image $($script:OldMcpImage)"
    }
    if ($script:DeployFrontend -and $script:FrontendApp -and $script:OldFrontendImage) {
        $oldImg = $script:OldFrontendImage -replace '^DOCKER\|', ''
        Write-Host "  │  Frontend: az webapp config container set --name $($script:FrontendApp) --resource-group $ResourceGroup --container-image-name $oldImg"
    }
    Write-Host "  └──────────────────────────────────────────────────────────────"

    if ($DryRun) {
        Write-Host ""
        Write-LogWarn "This was a DRY RUN — no changes were made."
    } else {
        Write-Host ""
        Write-LogSuccess "Deployment complete!"
    }
}

# ==============================================================================
# Main
# ==============================================================================

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        MACAE - Deploy Local Code to Azure                   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Check-Prerequisites
Discover-Resources
Resolve-Acr
Determine-Services
Generate-Tag
Build-AndPush
Update-AzureResources
Print-Summary
