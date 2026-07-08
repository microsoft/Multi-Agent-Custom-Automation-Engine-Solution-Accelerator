<#
.SYNOPSIS
    Builds the backend, frontend and MCP container images and pushes them to the
    Azure Container Registry (ACR) provisioned by the solution, then updates the
    Container Apps and the frontend Web App to use the freshly pushed images.

.DESCRIPTION
    This script is designed to run as an `azd` postprovision hook. It reads
    provisioning outputs from the current `azd` environment (`azd env get-values`)
    and does the following:

      1. Reads: ACR name/endpoint, resource group, container app/web app names.
      2. Builds each image either:
           - Remotely with `az acr build` (default; no local Docker required), or
           - Locally with `docker build` + `docker push` (when BUILD_MODE=local).
      3. Updates:
           - the backend Container App image
           - the MCP Container App image
           - the frontend Web App container image and DOCKER_REGISTRY_SERVER_URL

.PARAMETER BuildMode
    Optional. `remote` (default) or `local`. Overrides the AZURE_ENV_BUILD_MODE
    environment variable when provided.

.PARAMETER ImageTag
    Optional. Tag applied to all built images. Overrides AZURE_ENV_IMAGE_TAG
    when provided. Defaults to `latest`.

.PARAMETER Skip
    Optional switch. When set the script prints a message and exits 0. Also
    honored via AZURE_ENV_SKIP_IMAGE_BUILD=true.

.EXAMPLE
    # Remote build (no Docker needed on the client machine)
    ./infra/scripts/Build-And-Push-Images.ps1

.EXAMPLE
    # Local build using Docker Desktop
    ./infra/scripts/Build-And-Push-Images.ps1 -BuildMode local -ImageTag dev
#>
[CmdletBinding()]
param(
    [ValidateSet('local', 'remote')]
    [string]$BuildMode,

    [string]$ImageTag,

    [switch]$Skip
)

$ErrorActionPreference = 'Stop'

function Write-Section {
    param([string]$Message)
    Write-Host ''
    Write-Host ('=' * 70) -ForegroundColor DarkCyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host ('=' * 70) -ForegroundColor DarkCyan
}

function Get-AzdEnvValues {
    # Returns a hashtable of the current azd environment's key/value pairs.
    $values = @{}
    $raw = & azd env get-values 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $raw) {
        return $values
    }
    foreach ($line in $raw) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"?(.*?)"?\s*$') {
            $values[$matches[1]] = $matches[2]
        }
    }
    return $values
}

function Get-EnvOrAzd {
    param(
        [Parameter(Mandatory)][string]$Name,
        [hashtable]$AzdEnv,
        [string]$Default
    )
    $val = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($val)) { return $val }
    if ($AzdEnv.ContainsKey($Name) -and -not [string]::IsNullOrWhiteSpace($AzdEnv[$Name])) {
        return $AzdEnv[$Name]
    }
    return $Default
}

# --- Skip switch handling ---------------------------------------------------
if ($Skip -or ([Environment]::GetEnvironmentVariable('AZURE_ENV_SKIP_IMAGE_BUILD') -eq 'true')) {
    Write-Host 'AZURE_ENV_SKIP_IMAGE_BUILD=true or -Skip specified. Skipping container image build & push.' -ForegroundColor Yellow
    exit 0
}

# --- Read configuration -----------------------------------------------------
Write-Section 'Reading azd environment values'
$azdEnv = Get-AzdEnvValues

$acrName        = Get-EnvOrAzd -Name 'AZURE_CONTAINER_REGISTRY_NAME'     -AzdEnv $azdEnv
$acrEndpoint    = Get-EnvOrAzd -Name 'AZURE_CONTAINER_REGISTRY_ENDPOINT' -AzdEnv $azdEnv
$resourceGroup  = Get-EnvOrAzd -Name 'AZURE_RESOURCE_GROUP'              -AzdEnv $azdEnv
$backendCa      = Get-EnvOrAzd -Name 'BACKEND_CONTAINER_APP_NAME'        -AzdEnv $azdEnv
$mcpCa          = Get-EnvOrAzd -Name 'MCP_CONTAINER_APP_NAME'            -AzdEnv $azdEnv
$frontendApp    = Get-EnvOrAzd -Name 'FRONTEND_WEB_APP_NAME'             -AzdEnv $azdEnv
$backendImage   = Get-EnvOrAzd -Name 'BACKEND_IMAGE_NAME'                -AzdEnv $azdEnv -Default 'macaebackend'
$frontendImage  = Get-EnvOrAzd -Name 'FRONTEND_IMAGE_NAME'               -AzdEnv $azdEnv -Default 'macaefrontend'
$mcpImage       = Get-EnvOrAzd -Name 'MCP_IMAGE_NAME'                    -AzdEnv $azdEnv -Default 'macaemcp'
$frontendPort   = Get-EnvOrAzd -Name 'FRONTEND_WEBSITES_PORT'            -AzdEnv $azdEnv -Default '3000'

if (-not $BuildMode) {
    $BuildMode = Get-EnvOrAzd -Name 'AZURE_ENV_BUILD_MODE' -AzdEnv $azdEnv -Default 'remote'
}
if (-not $ImageTag) {
    $ImageTag = Get-EnvOrAzd -Name 'AZURE_ENV_IMAGE_TAG' -AzdEnv $azdEnv -Default 'latest'
}

foreach ($pair in @(
    @('AZURE_CONTAINER_REGISTRY_NAME',     $acrName),
    @('AZURE_CONTAINER_REGISTRY_ENDPOINT', $acrEndpoint),
    @('AZURE_RESOURCE_GROUP',              $resourceGroup),
    @('BACKEND_CONTAINER_APP_NAME',        $backendCa),
    @('MCP_CONTAINER_APP_NAME',            $mcpCa),
    @('FRONTEND_WEB_APP_NAME',             $frontendApp)
)) {
    if ([string]::IsNullOrWhiteSpace($pair[1])) {
        throw "Required value '$($pair[0])' is missing. Ensure provisioning finished successfully and the outputs are present in the azd environment."
    }
}

Write-Host "ACR:                $acrName ($acrEndpoint)"
Write-Host "Resource group:     $resourceGroup"
Write-Host "Backend CA:         $backendCa   -> $backendImage`:$ImageTag"
Write-Host "MCP CA:             $mcpCa       -> $mcpImage`:$ImageTag"
Write-Host "Frontend Web App:   $frontendApp -> $frontendImage`:$ImageTag"
Write-Host "Build mode:         $BuildMode"

# --- Resolve source paths ---------------------------------------------------
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$srcRoot  = Join-Path $repoRoot 'src'

$images = @(
    [pscustomobject]@{ Name = $backendImage;  Context = (Join-Path $srcRoot 'backend');    Dockerfile = 'Dockerfile' },
    [pscustomobject]@{ Name = $frontendImage; Context = (Join-Path $srcRoot 'App');        Dockerfile = 'Dockerfile' },
    [pscustomobject]@{ Name = $mcpImage;      Context = (Join-Path $srcRoot 'mcp_server'); Dockerfile = 'Dockerfile' }
)

foreach ($img in $images) {
    $dockerfilePath = Join-Path $img.Context $img.Dockerfile
    if (-not (Test-Path $dockerfilePath)) {
        throw "Dockerfile not found at '$dockerfilePath'."
    }
}

# --- WAF: temporarily relax ACR restrictions for build/push, restored in finally ---
$deploymentType = & az group show --name $resourceGroup --query "tags.Type" -o tsv 2>$null

if ($deploymentType -eq 'WAF') {
    Write-Section 'WAF deployment detected - temporarily relaxing ACR restrictions'
    & az acr update --name $acrName --resource-group $resourceGroup --allow-exports true --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to enable ACR exports." }
    & az acr update --name $acrName --resource-group $resourceGroup --public-network-enabled true --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to enable ACR public network access." }
    & az acr update --name $acrName --resource-group $resourceGroup --default-action Allow --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to set ACR default action to Allow." }
    Write-Host 'ACR restrictions temporarily relaxed.'
}

try {
# --- Build & push -----------------------------------------------------------
Write-Section "Building and pushing images ($BuildMode)"

foreach ($img in $images) {
    $imageRef = "$acrEndpoint/$($img.Name):$ImageTag"
    Write-Host ''
    Write-Host ">>> $($img.Name)" -ForegroundColor Green

    if ($BuildMode -eq 'local') {
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            throw "BUILD_MODE=local but 'docker' is not on PATH. Install Docker Desktop or switch to remote mode."
        }
        Write-Host "docker build -t $imageRef -f $($img.Dockerfile) $($img.Context)"
        Push-Location $img.Context
        try {
            & docker build -t $imageRef -f $img.Dockerfile .
            if ($LASTEXITCODE -ne 0) { throw "docker build failed for $($img.Name) (exit $LASTEXITCODE)." }
        }
        finally {
            Pop-Location
        }

        Write-Host "az acr login --name $acrName"
        & az acr login --name $acrName
        if ($LASTEXITCODE -ne 0) { throw "az acr login failed (exit $LASTEXITCODE)." }

        Write-Host "docker push $imageRef"
        & docker push $imageRef
        if ($LASTEXITCODE -ne 0) { throw "docker push failed for $imageRef (exit $LASTEXITCODE)." }
    }
    else {
        # Remote build via ACR Tasks
        Push-Location $img.Context
        try {
            Write-Host "az acr build --registry $acrName --image $($img.Name):$ImageTag --file $($img.Dockerfile) ."
            & az acr build --registry $acrName --image "$($img.Name):$ImageTag" --file $img.Dockerfile .
            if ($LASTEXITCODE -ne 0) { throw "az acr build failed for $($img.Name) (exit $LASTEXITCODE)." }
        }
        finally {
            Pop-Location
        }
    }
}

# --- Update Container Apps and Web App --------------------------------------
Write-Section 'Updating Container Apps and Web App to use new images'

$backendRef  = "$acrEndpoint/$backendImage`:$ImageTag"
$mcpRef      = "$acrEndpoint/$mcpImage`:$ImageTag"
$frontendRef = "$acrEndpoint/$frontendImage`:$ImageTag"

Write-Host "Updating backend Container App -> $backendRef"
& az containerapp update --name $backendCa --resource-group $resourceGroup --image $backendRef --output none
if ($LASTEXITCODE -ne 0) { throw "Failed to update backend Container App '$backendCa'." }

Write-Host "Updating MCP Container App -> $mcpRef"
& az containerapp update --name $mcpCa --resource-group $resourceGroup --image $mcpRef --output none
if ($LASTEXITCODE -ne 0) { throw "Failed to update MCP Container App '$mcpCa'." }

Write-Host "Updating Frontend Web App -> $frontendRef"
& az webapp config container set `
    --name $frontendApp `
    --resource-group $resourceGroup `
    --container-image-name $frontendRef `
    --container-registry-url "https://$acrEndpoint" `
    --output none
if ($LASTEXITCODE -ne 0) { throw "Failed to set container image on Web App '$frontendApp'." }

Write-Host "Ensuring WEBSITES_PORT=$frontendPort on Web App"
& az webapp config appsettings set `
    --name $frontendApp `
    --resource-group $resourceGroup `
    --settings "WEBSITES_PORT=$frontendPort" "DOCKER_REGISTRY_SERVER_URL=https://$acrEndpoint" `
    --output none
if ($LASTEXITCODE -ne 0) { throw "Failed to update app settings on Web App '$frontendApp'." }

Write-Host "Restarting Web App '$frontendApp'"
& az webapp restart --name $frontendApp --resource-group $resourceGroup --output none
if ($LASTEXITCODE -ne 0) { throw "Failed to restart Web App '$frontendApp'." }

Write-Section 'Image build & push complete'
Write-Host "All images built, pushed to '$acrEndpoint' with tag '$ImageTag', and services updated." -ForegroundColor Green

Write-Section 'Next step: Upload Team Configurations and index sample data'
Write-Host "Run the following command from the project root to upload the team" -ForegroundColor White
Write-Host "configurations and index the sample data:" -ForegroundColor White
Write-Host ""
Write-Host "   infra\scripts\Selecting-Team-Config-And-Data.ps1" -ForegroundColor Cyan
Write-Host ""
}
finally {
    if ($deploymentType -eq 'WAF') {
        Write-Section 'Restoring WAF ACR configuration'
        & az acr update --name $acrName --resource-group $resourceGroup --default-action Deny --output none
        & az acr update --name $acrName --resource-group $resourceGroup --public-network-enabled false --output none
        & az acr update --name $acrName --resource-group $resourceGroup --allow-exports false --output none
        Write-Host 'ACR configuration restored.'
    }
}
