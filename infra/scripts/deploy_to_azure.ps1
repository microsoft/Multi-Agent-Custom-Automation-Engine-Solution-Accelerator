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
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$BackendDir = Join-Path $RepoRoot "src\backend"
$McpDir = Join-Path $RepoRoot "src\mcp_server"
$FrontendDir = Join-Path $RepoRoot "src\App"

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
            Write-LogWarn "Azure operation in progress (attempt $attempt/4), retrying in 30s..."
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

    if (Get-Command az -ErrorAction SilentlyContinue) {
        Write-LogSuccess "Azure CLI found"
    } else {
        $missing += "azure-cli"
    }

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $dockerInfo = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-LogSuccess "Docker found and running"
        } else {
            Write-LogError "Docker found but daemon not running. Please start Docker Desktop."
            exit 1
        }
    } else {
        $missing += "docker"
    }

    if ($missing.Count -gt 0) {
        Write-LogError "Missing prerequisites: $($missing -join ', ')"
        Write-Host ""
        foreach ($tool in $missing) {
            switch ($tool) {
                "azure-cli" {
                    Write-Host "  ┌─ Azure CLI ───────────────────────────────────────────────────"
                    Write-Host "  │  Download: https://aka.ms/installazurecliwindows"
                    Write-Host "  │  Or: winget install Microsoft.AzureCLI"
                    Write-Host "  │  Verify: az --version"
                    Write-Host "  └──────────────────────────────────────────────────────────────"
                }
                "docker" {
                    Write-Host "  ┌─ Docker Desktop ──────────────────────────────────────────────"
                    Write-Host "  │  Download: https://www.docker.com/products/docker-desktop"
                    Write-Host "  │  Or: winget install Docker.DockerDesktop"
                    Write-Host "  │  Verify: docker --version"
                    Write-Host "  └──────────────────────────────────────────────────────────────"
                }
            }
        }
        exit 1
    }

    # Check Azure login
    $azAccount = az account show 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-LogWarn "Not logged into Azure CLI. Running 'az login'..."
        az login
    }
    Write-LogSuccess "Logged into Azure CLI"
}

# ==============================================================================
# Step 1b: Azure Role / Permission Check
# ==============================================================================
#
# Per docs/DeploymentGuide.md, the deploying account needs:
#   - Contributor (or Owner) on the subscription -- to update resources
#   - User Access Administrator OR Role Based Access Control Administrator
#     (or Owner) -- to assign the AcrPull role to managed identities
# This check is non-fatal: group-inherited roles may not always enumerate.
# ==============================================================================

function Check-AzureRoles {
    Write-LogStep "Step 1b: Checking Azure Roles & Permissions"

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
        Write-LogWarn "Required: Contributor + (User Access Administrator OR Role Based Access Control Administrator), or Owner."
        return
    }

    $roles = ($rolesRaw -split "`r?`n" | Where-Object { $_ -ne "" })
    $hasResMgmt  = ($roles -contains 'Owner') -or ($roles -contains 'Contributor')
    $hasRoleMgmt = ($roles -contains 'Owner') -or ($roles -contains 'User Access Administrator') -or ($roles -contains 'Role Based Access Control Administrator')

    if ($hasResMgmt) { Write-LogSuccess "Resource management role found (Owner/Contributor)" }
    else { Write-LogWarn "Missing 'Contributor' (or 'Owner') at subscription scope -- Azure resource updates may fail." }

    if ($hasRoleMgmt) { Write-LogSuccess "Role-assignment permission found (Owner/UAA/RBAC Admin)" }
    else { Write-LogWarn "Missing 'User Access Administrator' / 'Role Based Access Control Administrator' (or 'Owner') -- AcrPull role assignment may fail. Pass -SkipRoleAssignment if roles are already in place." }
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
        Write-LogInfo "No -Services specified — deploying all services"
        $script:DeployBackend = $true
        $script:DeployMcp = $true
        $script:DeployFrontend = $true
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
        $script:ImageTag = $timestamp
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

    Write-LogInfo "Logging into ACR: $script:AcrName..."
    az acr login --name $script:AcrName
    if ($LASTEXITCODE -ne 0) {
        Write-LogError "ACR login failed for '$script:AcrName'."
        Write-LogError "  Likely causes:"
        Write-LogError "    - Your account lacks 'AcrPush' / 'Contributor' on the registry."
        Write-LogError "    - Docker daemon not running."
        Write-LogError "    - Tenant blocks docker-credential helpers (try: az acr login -n $script:AcrName --expose-token)."
        exit 1
    }
    Write-LogSuccess "ACR login successful"

    $env:DOCKER_BUILDKIT = "1"

    # Track per-service success so a partial failure does not strand the others
    $script:BuildResults = [ordered]@{}

    if ($script:DeployBackend) {
        $fullImage = "$($script:AcrLoginServer)/$BackendImageName`:$($script:ImageTag)"
        Write-LogInfo "Building backend image: $fullImage"
        if ($DryRun) {
            Write-LogInfo "[DRY RUN] Would build: docker build -t $fullImage $BackendDir"
            $script:BuildResults["backend"] = "dry-run"
        } else {
            docker build -t $fullImage $BackendDir
            if ($LASTEXITCODE -ne 0) {
                Write-LogError "Backend image build FAILED -- continuing with other services"
                $script:BuildResults["backend"] = "build-failed"
                $script:DeployBackend = $false
            } else {
                Write-LogSuccess "Backend image built"
                docker push $fullImage
                if ($LASTEXITCODE -ne 0) {
                    Write-LogError "Backend image push FAILED -- continuing with other services"
                    $script:BuildResults["backend"] = "push-failed"
                    $script:DeployBackend = $false
                } else {
                    Write-LogSuccess "Backend image pushed: $fullImage"
                    $script:BuildResults["backend"] = "ok"
                }
            }
        }
    }

    if ($script:DeployMcp) {
        $fullImage = "$($script:AcrLoginServer)/$McpImageName`:$($script:ImageTag)"
        Write-LogInfo "Building MCP image: $fullImage"
        if ($DryRun) {
            Write-LogInfo "[DRY RUN] Would build: docker build -t $fullImage $McpDir"
            $script:BuildResults["mcp"] = "dry-run"
        } else {
            docker build -t $fullImage $McpDir
            if ($LASTEXITCODE -ne 0) {
                Write-LogError "MCP image build FAILED -- continuing with other services"
                $script:BuildResults["mcp"] = "build-failed"
                $script:DeployMcp = $false
            } else {
                Write-LogSuccess "MCP image built"
                docker push $fullImage
                if ($LASTEXITCODE -ne 0) {
                    Write-LogError "MCP image push FAILED -- continuing with other services"
                    $script:BuildResults["mcp"] = "push-failed"
                    $script:DeployMcp = $false
                } else {
                    Write-LogSuccess "MCP image pushed: $fullImage"
                    $script:BuildResults["mcp"] = "ok"
                }
            }
        }
    }

    if ($script:DeployFrontend) {
        $fullImage = "$($script:AcrLoginServer)/$FrontendImageName`:$($script:ImageTag)"
        Write-LogInfo "Building frontend image: $fullImage"
        if ($DryRun) {
            Write-LogInfo "[DRY RUN] Would build: docker build -t $fullImage $FrontendDir"
            $script:BuildResults["frontend"] = "dry-run"
        } else {
            docker build -t $fullImage $FrontendDir
            if ($LASTEXITCODE -ne 0) {
                Write-LogError "Frontend image build FAILED -- continuing with other services"
                $script:BuildResults["frontend"] = "build-failed"
                $script:DeployFrontend = $false
            } else {
                Write-LogSuccess "Frontend image built"
                docker push $fullImage
                if ($LASTEXITCODE -ne 0) {
                    Write-LogError "Frontend image push FAILED -- continuing with other services"
                    $script:BuildResults["frontend"] = "push-failed"
                    $script:DeployFrontend = $false
                } else {
                    Write-LogSuccess "Frontend image pushed: $fullImage"
                    $script:BuildResults["frontend"] = "ok"
                }
            }
        }
    }

    # If all selected services failed to build/push, bail before touching Azure resources
    $okCount = ($script:BuildResults.Values | Where-Object { $_ -eq "ok" -or $_ -eq "dry-run" }).Count
    if ($okCount -eq 0 -and $script:BuildResults.Count -gt 0) {
        Write-LogError "All image builds/pushes failed -- aborting before touching Azure resources."
        exit 1
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
            # Capture exit codes from BOTH commands — without this, a failure in the
            # first call (DOCKER_REGISTRY_SERVER_URL) would be masked if the second
            # call succeeds, leaving the Web App with a half-configured registry.
            az webapp config appsettings set --name $script:FrontendApp --resource-group $ResourceGroup `
                --settings DOCKER_REGISTRY_SERVER_URL="https://$($script:AcrLoginServer)" --output none
            $appsettingsRc = $LASTEXITCODE
            az webapp config set --name $script:FrontendApp --resource-group $ResourceGroup `
                --generic-configurations '{\"acrUseManagedIdentityCreds\": true}' --output none
            $configRc = $LASTEXITCODE
            if ($appsettingsRc -ne 0 -or $configRc -ne 0) {
                Write-LogError "Frontend registry config FAILED (appsettings rc=$appsettingsRc, config rc=$configRc) — image pull may fail."
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

    if ($script:BuildResults -and $script:BuildResults.Count -gt 0) {
        Write-Host "  Build results:"
        foreach ($k in $script:BuildResults.Keys) {
            $v = $script:BuildResults[$k]
            $glyph = if ($v -eq "ok" -or $v -eq "dry-run") { "[OK]" } else { "[FAIL]" }
            Write-Host ("    {0,-6} {1,-9} {2}" -f $glyph, $k, $v)
        }
        Write-Host ""
    }

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
    Write-Host "  │  NOTE: When rolling back to images from a different registry"
    Write-Host "  │  (e.g. biabcontainerreg.azurecr.io public defaults), the Web App"
    Write-Host "  │  also needs acrUseManagedIdentityCreds disabled and the"
    Write-Host "  │  DOCKER_REGISTRY_SERVER_URL updated, otherwise the pull will"
    Write-Host "  │  fail with ACRTokenRetrievalFailure. Container Apps fall back"
    Write-Host "  │  to anonymous pull automatically for public registries."
    Write-Host "  └──────────────────────────────────────────────────────────────"
    Write-Host ""
    Write-Host "  Copy/paste the commands below (one per line):"
    Write-Host ""

    if ($script:DeployBackend -and $script:BackendCA -and $script:OldBackendImage) {
        Write-Host "  # Backend rollback"
        Write-Host "  az containerapp update --name $($script:BackendCA) --resource-group $ResourceGroup --image $($script:OldBackendImage)"
        Write-Host ""
    }
    if ($script:DeployMcp -and $script:McpCA -and $script:OldMcpImage) {
        Write-Host "  # MCP rollback"
        Write-Host "  az containerapp update --name $($script:McpCA) --resource-group $ResourceGroup --image $($script:OldMcpImage)"
        Write-Host ""
    }
    if ($script:DeployFrontend -and $script:FrontendApp -and $script:OldFrontendImage) {
        $oldImg = $script:OldFrontendImage -replace '^DOCKER\|', ''
        $oldRegistry = ($oldImg -split '/')[0]
        Write-Host "  # Frontend rollback (run all 4 lines)"
        Write-Host "  az webapp config set --name $($script:FrontendApp) --resource-group $ResourceGroup --generic-configurations '{\""acrUseManagedIdentityCreds\"": false}'"
        Write-Host "  az webapp config appsettings set --name $($script:FrontendApp) --resource-group $ResourceGroup --settings DOCKER_REGISTRY_SERVER_URL=https://$oldRegistry"
        Write-Host "  az webapp config container set --name $($script:FrontendApp) --resource-group $ResourceGroup --container-image-name $oldImg"
        Write-Host "  az webapp restart --name $($script:FrontendApp) --resource-group $ResourceGroup"
        Write-Host ""
    }

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
Check-AzureRoles
Discover-Resources
Resolve-Acr
Determine-Services
Generate-Tag
Build-AndPush
Update-AzureResources
Print-Summary
