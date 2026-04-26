# =============================================================================
# Deployment Pre-Check Script (PowerShell)
# =============================================================================
# This script runs as a preprovision hook during 'azd up' to validate that
# all prerequisites are met before provisioning begins.
#
# It checks:
#   1. Environment detection (Local, Codespace, Dev Container)
#   2. Required CLI tools and versions (azd, az, bicep, python, npm, node)
#   3. Azure authentication (logged in, subscription accessible)
#   4. azd environment variables (AZURE_LOCATION, AZURE_ENV_OPENAI_LOCATION)
#   5. Allowed Azure region validation
#   6. Hook script existence (prepackage, postdeploy scripts)
#   7. Azure OpenAI model quota availability
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed (details printed)
# =============================================================================

$ErrorActionPreference = "Continue"

# ── State ────────────────────────────────────────────────────────────────────
$script:Errors = [System.Collections.ArrayList]::new()
$script:Warnings = [System.Collections.ArrayList]::new()
$script:Environment = "Local"

# ── Allowed regions (from main.bicep) ────────────────────────────────────────
$AllowedLocations = @("australiaeast", "centralus", "eastasia", "eastus2", "japaneast", "northeurope", "southeastasia", "uksouth")
$AllowedAILocations = @("australiaeast", "eastus2", "francecentral", "japaneast", "norwayeast", "swedencentral", "uksouth", "westus")

# ── Helper functions ─────────────────────────────────────────────────────────

function Add-CheckError {
    param([string]$Message)
    [void]$script:Errors.Add($Message)
}

function Add-CheckWarning {
    param([string]$Message)
    [void]$script:Warnings.Add($Message)
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Yellow
    Write-Host " $Title" -ForegroundColor Green
    Write-Host "===============================================================" -ForegroundColor Yellow
    Write-Host ""
}

function Write-Section {
    param([string]$Title)
    Write-Host "── $Title ──" -ForegroundColor Cyan
}

function Write-OK {
    param([string]$Message)
    Write-Host "  ✅ $Message" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Message)
    Write-Host "  ❌ $Message" -ForegroundColor Red
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  ⚠️  $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "  ℹ️  $Message" -ForegroundColor Blue
}

function Test-VersionGte {
    param(
        [string]$Current,
        [string]$Required
    )
    try {
        $currentVersion = [System.Version]::new($Current)
        $requiredVersion = [System.Version]::new($Required)
        return $currentVersion -ge $requiredVersion
    }
    catch {
        return $false
    }
}

function Test-CommandExists {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# ── Detect environment ───────────────────────────────────────────────────────

function Test-Environment {
    Write-Section "Environment Detection"

    if ($env:CODESPACES -or $env:CLOUDENV_ENVIRONMENT_ID) {
        $script:Environment = "Codespace"
        Write-OK "Running in GitHub Codespaces"
    }
    elseif ($env:REMOTE_CONTAINERS -or $env:DEVCONTAINER -or (Test-Path "/.dockerenv" -ErrorAction SilentlyContinue)) {
        $script:Environment = "DevContainer"
        Write-OK "Running in Dev Container"
    }
    else {
        $script:Environment = "Local"
        Write-OK "Running in Local environment"
    }
    Write-Host ""
}

# ── Check CLI tools ──────────────────────────────────────────────────────────

function Test-Azd {
    Write-Section "Azure Developer CLI (azd)"

    if (-not (Test-CommandExists "azd")) {
        Add-CheckError "Azure Developer CLI (azd) is not installed. Install: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd"
        Write-Fail "azd is not installed"
        Write-Host ""
        return
    }

    try {
        $azdVersionOutput = azd version 2>&1 | Out-String
        $azdVersion = [regex]::Match($azdVersionOutput, '\d+\.\d+\.\d+').Value

        if ($azdVersion) {
            if (Test-VersionGte $azdVersion "1.18.0") {
                Write-OK "azd version $azdVersion (>= 1.18.0 required)"
            }
            else {
                Add-CheckError "azd version $azdVersion is too old. Version >= 1.18.0 is required. Update: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd"
                Write-Fail "azd version $azdVersion is below the minimum required 1.18.0"
            }
        }
        else {
            Add-CheckWarning "Could not determine azd version. Ensure >= 1.18.0."
            Write-Warn "Could not determine azd version"
        }
    }
    catch {
        Add-CheckWarning "Could not determine azd version. Ensure >= 1.18.0."
        Write-Warn "Could not determine azd version"
    }
    Write-Host ""
}

function Test-AzureCLI {
    Write-Section "Azure CLI (az)"

    if (-not (Test-CommandExists "az")) {
        Add-CheckError "Azure CLI (az) is not installed. Install: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
        Write-Fail "Azure CLI (az) is not installed"
        Write-Host ""
        return
    }

    try {
        $azVersionJson = az version --output json 2>$null | ConvertFrom-Json
        $azVersion = $azVersionJson.'azure-cli'
        if ($azVersion) {
            Write-OK "Azure CLI version $azVersion"
        }
    }
    catch {
        Write-Warn "Could not determine Azure CLI version"
    }

    # Check login status
    try {
        $accountInfo = az account show --output json 2>$null | ConvertFrom-Json
        if ($accountInfo) {
            Write-OK "Logged in to Azure (subscription: $($accountInfo.name))"
        }
        else {
            Add-CheckError "Not logged in to Azure CLI. Run 'az login' to authenticate."
            Write-Fail "Not logged in to Azure CLI"
        }
    }
    catch {
        Add-CheckError "Not logged in to Azure CLI. Run 'az login' to authenticate."
        Write-Fail "Not logged in to Azure CLI"
    }
    Write-Host ""
}

function Test-Bicep {
    Write-Section "Bicep CLI"

    try {
        $bicepOutput = az bicep version 2>&1 | Out-String
        $bicepVersion = [regex]::Match($bicepOutput, '\d+\.\d+\.\d+').Value

        if ($bicepVersion) {
            if (Test-VersionGte $bicepVersion "0.33.0") {
                Write-OK "Bicep version $bicepVersion (>= 0.33.0 required)"
            }
            else {
                Add-CheckError "Bicep version $bicepVersion is too old. Version >= 0.33.0 is required. Run 'az bicep upgrade' to update."
                Write-Fail "Bicep version $bicepVersion is below the minimum required 0.33.0"
            }
        }
        else {
            Write-Warn "Bicep not found. Attempting install..."
            az bicep install 2>$null
            $bicepOutput = az bicep version 2>&1 | Out-String
            $bicepVersion = [regex]::Match($bicepOutput, '\d+\.\d+\.\d+').Value
            if ($bicepVersion) {
                Write-OK "Bicep installed: version $bicepVersion"
            }
            else {
                Add-CheckError "Bicep CLI is not installed. Run 'az bicep install' to install it."
                Write-Fail "Bicep CLI is not available"
            }
        }
    }
    catch {
        Add-CheckError "Bicep CLI is not installed. Run 'az bicep install' to install it."
        Write-Fail "Bicep CLI check failed"
    }
    Write-Host ""
}

function Test-Python {
    Write-Section "Python"

    $pythonCmd = $null
    if (Test-CommandExists "python3") {
        $pythonCmd = "python3"
    }
    elseif (Test-CommandExists "python") {
        $pythonCmd = "python"
    }

    if ($pythonCmd) {
        try {
            $pyVersion = & $pythonCmd --version 2>&1 | Out-String
            $pyVersionNumber = [regex]::Match($pyVersion, '\d+\.\d+\.\d+').Value
            Write-OK "Python $pyVersionNumber ($pythonCmd)"
        }
        catch {
            Write-OK "Python is available ($pythonCmd)"
        }
    }
    else {
        Add-CheckError "Python is not installed. Python 3.x is required for backend and frontend services."
        Write-Fail "Python is not installed"
    }

    # Check pip
    if ((Test-CommandExists "pip") -or (Test-CommandExists "pip3")) {
        Write-OK "pip is available"
    }
    else {
        Add-CheckWarning "pip is not available. It may be needed for frontend packaging."
        Write-Warn "pip is not available"
    }
    Write-Host ""
}

function Test-Node {
    Write-Section "Node.js & npm"

    if (Test-CommandExists "node") {
        try {
            $nodeVersion = node --version 2>&1 | Out-String
            Write-OK "Node.js $($nodeVersion.Trim())"
        }
        catch {
            Write-OK "Node.js is available"
        }
    }
    else {
        Add-CheckError "Node.js is not installed. It is required for frontend packaging."
        Write-Fail "Node.js is not installed"
    }

    if (Test-CommandExists "npm") {
        try {
            $npmVersion = npm --version 2>&1 | Out-String
            Write-OK "npm $($npmVersion.Trim())"
        }
        catch {
            Write-OK "npm is available"
        }
    }
    else {
        Add-CheckError "npm is not installed. It is required for frontend packaging."
        Write-Fail "npm is not installed"
    }
    Write-Host ""
}

function Test-Docker {
    Write-Section "Docker"

    if ($script:Environment -eq "Local") {
        if (Test-CommandExists "docker") {
            try {
                $dockerInfo = docker info 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-OK "Docker is running"
                }
                else {
                    Add-CheckWarning "Docker is installed but the daemon is not running. It may be needed for container builds."
                    Write-Warn "Docker daemon is not running"
                }
            }
            catch {
                Add-CheckWarning "Docker is installed but could not verify daemon status."
                Write-Warn "Docker daemon status unknown"
            }
        }
        else {
            Add-CheckWarning "Docker is not installed. It may be needed for container builds."
            Write-Warn "Docker is not installed (optional)"
        }
    }
    else {
        if (Test-CommandExists "docker") {
            Write-OK "Docker is available (managed by $($script:Environment))"
        }
        else {
            Write-Info "Docker check skipped ($($script:Environment) environment)"
        }
    }
    Write-Host ""
}

# ── Check azd environment variables ─────────────────────────────────────────

function Test-AzdEnvironment {
    Write-Section "azd Environment Variables"

    $hasEnv = $false

    try {
        $envListOutput = azd env list --output json 2>$null | ConvertFrom-Json
        if ($envListOutput -and $envListOutput.Count -gt 0) {
            Write-OK "azd environment is configured"
            $hasEnv = $true
        }
    }
    catch {}

    if (-not $hasEnv) {
        Add-CheckWarning "No azd environment detected. 'azd up' will prompt you to create one."
        Write-Warn "No azd environment detected (will be created during 'azd up')"
        Write-Host ""
        return
    }

    # Validate AZURE_LOCATION
    try {
        $azureLocation = (azd env get-value AZURE_LOCATION 2>$null)
        if ($azureLocation) {
            $locationLower = $azureLocation.ToLower().Trim()
            if ($AllowedLocations -contains $locationLower) {
                Write-OK "AZURE_LOCATION=$azureLocation (valid)"
            }
            else {
                Add-CheckError "AZURE_LOCATION='$azureLocation' is not a supported region. Allowed: $($AllowedLocations -join ', '). Fix: azd env set AZURE_LOCATION '<valid_region>'"
                Write-Fail "AZURE_LOCATION='$azureLocation' is not in the allowed list"
            }
        }
        else {
            Write-Info "AZURE_LOCATION is not set (will be prompted during 'azd up')"
        }
    }
    catch {
        Write-Info "AZURE_LOCATION is not set (will be prompted during 'azd up')"
    }

    # Validate AZURE_ENV_OPENAI_LOCATION
    try {
        $openaiLocation = (azd env get-value AZURE_ENV_OPENAI_LOCATION 2>$null)
        if ($openaiLocation) {
            $aiLocLower = $openaiLocation.ToLower().Trim()
            if ($AllowedAILocations -contains $aiLocLower) {
                Write-OK "AZURE_ENV_OPENAI_LOCATION=$openaiLocation (valid)"
            }
            else {
                Add-CheckError "AZURE_ENV_OPENAI_LOCATION='$openaiLocation' is not a supported Azure AI region. Allowed: $($AllowedAILocations -join ', '). Fix: azd env set AZURE_ENV_OPENAI_LOCATION '<valid_region>'"
                Write-Fail "AZURE_ENV_OPENAI_LOCATION='$openaiLocation' is not in the allowed list"
            }
        }
        else {
            Write-Info "AZURE_ENV_OPENAI_LOCATION is not set (will use default or be prompted)"
        }
    }
    catch {
        Write-Info "AZURE_ENV_OPENAI_LOCATION is not set (will use default or be prompted)"
    }

    # Check deployment type env vars
    $deploymentTypeVars = @(
        @{Name = "AZURE_ENV_MODEL_DEPLOYMENT_TYPE"; Label = "GPT model" }
        @{Name = "AZURE_ENV_MODEL_4_1_DEPLOYMENT_TYPE"; Label = "GPT-4.1 model" }
        @{Name = "AZURE_ENV_REASONING_MODEL_DEPLOYMENT_TYPE"; Label = "Reasoning model" }
    )

    foreach ($dtVar in $deploymentTypeVars) {
        try {
            $dtValue = (azd env get-value $dtVar.Name 2>$null)
            if ($dtValue) {
                $dtValueTrimmed = $dtValue.Trim()
                if ($dtValueTrimmed -eq "Standard" -or $dtValueTrimmed -eq "GlobalStandard") {
                    Write-OK "$($dtVar.Name)=$dtValueTrimmed (valid)"
                }
                else {
                    Add-CheckError "$($dtVar.Name)='$dtValueTrimmed' is invalid. Must be 'Standard' or 'GlobalStandard'. Fix: azd env set $($dtVar.Name) 'GlobalStandard'"
                    Write-Fail "$($dtVar.Name)='$dtValueTrimmed' is not valid"
                }
            }
        }
        catch {}
    }
    Write-Host ""
}

# ── Check Azure subscription ────────────────────────────────────────────────

function Test-AzureSubscription {
    Write-Section "Azure Subscription"

    try {
        $accountInfo = az account show --output json 2>$null | ConvertFrom-Json
        if (-not $accountInfo) {
            Write-Fail "Cannot validate subscription (not logged in)"
            Write-Host ""
            return
        }

        if ($accountInfo.state -eq "Enabled") {
            Write-OK "Subscription is active (state: Enabled)"
        }
        else {
            Add-CheckError "Azure subscription state is '$($accountInfo.state)'. An active (Enabled) subscription is required."
            Write-Fail "Subscription state: $($accountInfo.state) (expected: Enabled)"
        }

        Write-OK "Subscription ID: $($accountInfo.id)"
    }
    catch {
        Write-Fail "Cannot validate subscription (not logged in)"
    }
    Write-Host ""
}

# ── Check hook scripts exist ────────────────────────────────────────────────

function Test-HookScripts {
    Write-Section "Deployment Hook Scripts"

    $scriptsToCheck = @(
        @{Path = "infra/scripts/package_frontend.sh"; Desc = "Frontend prepackage hook (bash)" }
        @{Path = "infra/scripts/package_frontend.ps1"; Desc = "Frontend prepackage hook (PowerShell)" }
        @{Path = "infra/scripts/selecting_team_config_and_data.sh"; Desc = "Post-deploy team config script (bash)" }
        @{Path = "infra/scripts/Selecting-Team-Config-And-Data.ps1"; Desc = "Post-deploy team config script (PowerShell)" }
        @{Path = "infra/scripts/validate_model_quota.sh"; Desc = "Model quota validation (bash)" }
        @{Path = "infra/scripts/validate_model_quota.ps1"; Desc = "Model quota validation (PowerShell)" }
        @{Path = "infra/scripts/validate_model_deployment_quota.sh"; Desc = "Model deployment quota validation (bash)" }
        @{Path = "infra/scripts/validate_model_deployment_quotas.ps1"; Desc = "Model deployment quota validation (PowerShell)" }
    )

    foreach ($script in $scriptsToCheck) {
        if (Test-Path $script.Path) {
            Write-OK "$($script.Desc) exists ($($script.Path))"
        }
        else {
            Add-CheckWarning "$($script.Desc) not found at $($script.Path)"
            Write-Warn "$($script.Desc) not found ($($script.Path))"
        }
    }
    Write-Host ""
}

# ── Check model quota ───────────────────────────────────────────────────────

function Test-ModelQuota {
    Write-Section "Azure OpenAI Model Quota (Optional)"

    # Check prerequisites
    try {
        $accountInfo = az account show --output json 2>$null | ConvertFrom-Json
        if (-not $accountInfo) {
            Write-Info "Skipping quota check (not logged in to Azure)"
            Write-Host ""
            return
        }
    }
    catch {
        Write-Info "Skipping quota check (not logged in to Azure)"
        Write-Host ""
        return
    }

    try {
        $openaiLocation = (azd env get-value AZURE_ENV_OPENAI_LOCATION 2>$null)
        if (-not $openaiLocation) {
            Write-Info "Skipping quota check (AZURE_ENV_OPENAI_LOCATION not set)"
            Write-Host ""
            return
        }
        $openaiLocation = $openaiLocation.Trim()
    }
    catch {
        Write-Info "Skipping quota check (AZURE_ENV_OPENAI_LOCATION not set)"
        Write-Host ""
        return
    }

    $subId = $accountInfo.id

    Write-Info "Checking Azure OpenAI model quota in '$openaiLocation'..."
    Write-Info "This may take a moment..."

    # Default models: gpt-4.1-mini (50), gpt-4.1 (150), o4-mini (50)
    $models = @(
        @{Name = "gpt-4.1-mini"; Capacity = 50; Type = "GlobalStandard" }
        @{Name = "gpt-4.1"; Capacity = 150; Type = "GlobalStandard" }
        @{Name = "o4-mini"; Capacity = 50; Type = "GlobalStandard" }
    )

    $quotaErrors = @()

    foreach ($model in $models) {
        $modelType = "OpenAI.$($model.Type).$($model.Name)"
        try {
            $modelData = az cognitiveservices usage list --location $openaiLocation --query "[?name.value=='$modelType']" --output json 2>$null | ConvertFrom-Json

            if ($modelData -and $modelData.Count -gt 0) {
                $currentValue = [int]($modelData[0].currentValue)
                $limit = [int]($modelData[0].limit)
                $available = $limit - $currentValue

                if ($available -ge $model.Capacity) {
                    Write-OK "$($model.Name): $available available (need $($model.Capacity)) in $openaiLocation"
                }
                else {
                    $quotaErrors += "$($model.Name): only $available available but $($model.Capacity) required in $openaiLocation"
                    Write-Fail "$($model.Name): insufficient quota ($available available, $($model.Capacity) required)"
                }
            }
            else {
                Write-Warn "$($model.Name): could not retrieve quota info for $openaiLocation"
            }
        }
        catch {
            Write-Warn "$($model.Name): error checking quota - $($_.Exception.Message)"
        }
    }

    if ($quotaErrors.Count -gt 0) {
        Add-CheckError "Insufficient Azure OpenAI model quota. Details:"
        foreach ($qe in $quotaErrors) {
            Add-CheckError "  - $qe"
        }
        Add-CheckError "Request quota increase: https://aka.ms/oai/stuquotarequest or try a different region: azd env set AZURE_ENV_OPENAI_LOCATION '<region>'"
    }
    Write-Host ""
}

# ── Main ─────────────────────────────────────────────────────────────────────

function Main {
    Write-Header "DEPLOYMENT PRE-CHECK RUNNER"
    Write-Host "Running deployment pre-checks to ensure a smooth deployment..." -ForegroundColor White
    Write-Host ""

    Test-Environment
    Test-Azd
    Test-AzureCLI
    Test-Bicep
    Test-Python
    Test-Node
    Test-Docker
    Test-AzureSubscription
    Test-AzdEnvironment
    Test-HookScripts
    Test-ModelQuota

    # ── Summary ──────────────────────────────────────────────────────────────

    Write-Host ""
    Write-Header "PRE-CHECK SUMMARY"

    Write-Host "  Environment: $($script:Environment)" -ForegroundColor White
    Write-Host ""

    if ($script:Warnings.Count -gt 0) {
        Write-Host "  Warnings ($($script:Warnings.Count)):" -ForegroundColor Yellow
        foreach ($warning in $script:Warnings) {
            Write-Host "    ⚠️  $warning" -ForegroundColor Yellow
        }
        Write-Host ""
    }

    if ($script:Errors.Count -gt 0) {
        Write-Host "  Errors ($($script:Errors.Count)):" -ForegroundColor Red
        Write-Host "  The following issues must be resolved before deployment can proceed:" -ForegroundColor Red
        Write-Host ""
        $idx = 1
        foreach ($err in $script:Errors) {
            Write-Host "    $idx. $err" -ForegroundColor Red
            $idx++
        }
        Write-Host ""
        Write-Host "  ❌ Pre-checks FAILED. Please fix the above errors and retry 'azd up'." -ForegroundColor Red
        Write-Host ""
        exit 1
    }
    else {
        Write-Host "  ✅ All pre-checks PASSED. Deployment can proceed." -ForegroundColor Green
        Write-Host ""
        exit 0
    }
}

Main
