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
    [switch]$DeployOnly
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

function Resolve-Acr {
    Write-LogStep "Step 3: Resolving Container Registry"

    if ($Acr) {
        $input = $Acr -replace '\.azurecr\.io$', ''
        $script:AcrName = az acr show --name $input --query "name" -o tsv 2>$null
        if (-not $script:AcrName) {
            Write-LogError "ACR '$Acr' not found or not accessible."
            exit 1
        }
        $script:AcrLoginServer = az acr show --name $script:AcrName --query "loginServer" -o tsv
        $script:AcrId = az acr show --name $script:AcrName --query "id" -o tsv
        Write-LogSuccess "Using specified ACR: $script:AcrName ($script:AcrLoginServer)"
        return
    }

    # Discover in RG
    Write-LogInfo "Looking for ACR in resource group..."
    $script:AcrName = az acr list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null

    if ($script:AcrName) {
        $script:AcrLoginServer = az acr show --name $script:AcrName --query "loginServer" -o tsv
        $script:AcrId = az acr show --name $script:AcrName --query "id" -o tsv
        Write-LogSuccess "Found ACR in RG: $script:AcrName ($script:AcrLoginServer)"
        return
    }

    # Ask user
    Write-LogWarn "No ACR found in resource group '$ResourceGroup'."
    Write-Host ""
    $userAcr = Read-Host "Do you have an existing ACR? Enter its name (or press Enter to create one)"

    if ($userAcr) {
        $input = $userAcr -replace '\.azurecr\.io$', ''
        $script:AcrName = az acr show --name $input --query "name" -o tsv 2>$null
        if (-not $script:AcrName) {
            Write-LogError "ACR '$userAcr' not found."
            exit 1
        }
        $script:AcrLoginServer = az acr show --name $script:AcrName --query "loginServer" -o tsv
        $script:AcrId = az acr show --name $script:AcrName --query "id" -o tsv
        Write-LogSuccess "Using ACR: $script:AcrName ($script:AcrLoginServer)"
    } else {
        # Create new ACR
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
        $script:AcrLoginServer = az acr show --name $script:AcrName --query "loginServer" -o tsv
        $script:AcrId = az acr show --name $script:AcrName --query "id" -o tsv
        Write-LogSuccess "Created ACR: $script:AcrName ($script:AcrLoginServer)"

        Assign-AcrPullRoles
    }
}

# ==============================================================================
# ACR Pull Role Assignment
# ==============================================================================

function Assign-AcrPullRoles {
    Write-LogInfo "Assigning AcrPull role to service identities..."

    $acrPullRole = "7f951dda-4ed3-4680-a7ca-43fe172d538d"

    # Backend
    if ($script:BackendCA) {
        $identity = az containerapp show --name $script:BackendCA --resource-group $ResourceGroup `
            --query "identity.principalId" -o tsv 2>$null
        if ($identity -and $identity -ne "null") {
            $existing = az role assignment list --assignee $identity --role $acrPullRole --scope $script:AcrId --query "[0].id" -o tsv 2>$null
            if (-not $existing) {
                az role assignment create --assignee $identity --role $acrPullRole --scope $script:AcrId --output none 2>$null
                Write-LogSuccess "  AcrPull assigned to backend identity"
            } else {
                Write-LogInfo "  AcrPull already assigned to backend identity ✓"
            }
        }
    }

    # MCP
    if ($script:McpCA) {
        $identity = az containerapp show --name $script:McpCA --resource-group $ResourceGroup `
            --query "identity.principalId" -o tsv 2>$null
        if ($identity -and $identity -ne "null") {
            $existing = az role assignment list --assignee $identity --role $acrPullRole --scope $script:AcrId --query "[0].id" -o tsv 2>$null
            if (-not $existing) {
                az role assignment create --assignee $identity --role $acrPullRole --scope $script:AcrId --output none 2>$null
                Write-LogSuccess "  AcrPull assigned to MCP identity"
            } else {
                Write-LogInfo "  AcrPull already assigned to MCP identity ✓"
            }
        }
    }

    # Frontend
    if ($script:FrontendApp) {
        $identity = az webapp show --name $script:FrontendApp --resource-group $ResourceGroup `
            --query "identity.principalId" -o tsv 2>$null
        if ($identity -and $identity -ne "null") {
            $existing = az role assignment list --assignee $identity --role $acrPullRole --scope $script:AcrId --query "[0].id" -o tsv 2>$null
            if (-not $existing) {
                az role assignment create --assignee $identity --role $acrPullRole --scope $script:AcrId --output none 2>$null
                Write-LogSuccess "  AcrPull assigned to frontend identity"
            } else {
                Write-LogInfo "  AcrPull already assigned to frontend identity ✓"
            }
        }
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
            Write-LogSuccess "Backend image built"
            docker push $fullImage
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
            Write-LogSuccess "MCP image built"
            docker push $fullImage
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
            Write-LogSuccess "Frontend image built"
            docker push $fullImage
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

function Configure-AcrOnResources {
    if ($script:DeployBackend -and $script:BackendCA) {
        $currentRegistry = az containerapp show --name $script:BackendCA --resource-group $ResourceGroup `
            --query "properties.configuration.registries[0].server" -o tsv 2>$null
        if ($currentRegistry -and $currentRegistry -ne $script:AcrLoginServer) {
            Write-LogInfo "Updating backend Container App registry to $($script:AcrLoginServer)..."
            if (-not $DryRun) {
                $identityId = az containerapp show --name $script:BackendCA --resource-group $ResourceGroup `
                    --query "identity.userAssignedIdentities | keys(@) | [0]" -o tsv 2>$null
                if ($identityId -and $identityId -ne "null") {
                    az containerapp registry set --name $script:BackendCA --resource-group $ResourceGroup `
                        --server $script:AcrLoginServer --identity $identityId --output none 2>$null
                } else {
                    az containerapp registry set --name $script:BackendCA --resource-group $ResourceGroup `
                        --server $script:AcrLoginServer --identity system --output none 2>$null
                }
                Write-LogSuccess "Backend registry updated"
            }
        }
    }

    if ($script:DeployMcp -and $script:McpCA) {
        $currentRegistry = az containerapp show --name $script:McpCA --resource-group $ResourceGroup `
            --query "properties.configuration.registries[0].server" -o tsv 2>$null
        if ($currentRegistry -and $currentRegistry -ne $script:AcrLoginServer) {
            Write-LogInfo "Updating MCP Container App registry to $($script:AcrLoginServer)..."
            if (-not $DryRun) {
                $identityId = az containerapp show --name $script:McpCA --resource-group $ResourceGroup `
                    --query "identity.userAssignedIdentities | keys(@) | [0]" -o tsv 2>$null
                if ($identityId -and $identityId -ne "null") {
                    az containerapp registry set --name $script:McpCA --resource-group $ResourceGroup `
                        --server $script:AcrLoginServer --identity $identityId --output none 2>$null
                } else {
                    az containerapp registry set --name $script:McpCA --resource-group $ResourceGroup `
                        --server $script:AcrLoginServer --identity system --output none 2>$null
                }
                Write-LogSuccess "MCP registry updated"
            }
        }
    }

    if ($script:DeployFrontend -and $script:FrontendApp) {
        Write-LogInfo "Updating frontend App Service registry config..."
        if (-not $DryRun) {
            az webapp config appsettings set --name $script:FrontendApp --resource-group $ResourceGroup `
                --settings DOCKER_REGISTRY_SERVER_URL="https://$($script:AcrLoginServer)" --output none 2>$null
            az webapp config set --name $script:FrontendApp --resource-group $ResourceGroup `
                --generic-configurations '{\"acrUseManagedIdentityCreds\": true}' --output none 2>$null
            Write-LogSuccess "Frontend registry config updated"
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
                az containerapp update --name $script:BackendCA --resource-group $ResourceGroup --image $fullImage --output none
                Write-LogSuccess "Backend updated successfully"
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
                az containerapp update --name $script:McpCA --resource-group $ResourceGroup --image $fullImage --output none
                Write-LogSuccess "MCP updated successfully"
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
