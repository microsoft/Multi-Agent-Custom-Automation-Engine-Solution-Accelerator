# =============================================================================
# Deployment Pre-Check Script (PowerShell)
# =============================================================================
# Standalone diagnostic that validates everything required for a successful
# 'azd up' run. This script is NOT registered as an azd hook — operators run
# it manually before invoking 'azd up'.
#
# Checks performed (in order):
#    1. Environment detection (Local, Codespace, Dev Container)
#    2. azd CLI presence and version
#    3. Azure CLI presence and version
#    4. Bicep CLI presence and version
#    5. Python presence and version
#    6. Node + npm presence and versions
#    7. Docker presence (skipped on Local; required in Codespace/Dev Container)
#    8. Azure authentication (logged in, subscription accessible)
#    9. Tenant match (cross-tenant subscription / Guest user detection)
#   10. Azure RBAC roles (Contributor + UAA/RBAC Admin, or Owner)
#   11. App registration permission (directory role or tenant default policy)
#   12. Required Azure resource providers registered
#   13. azd environment variables (AZURE_LOCATION, AZURE_ENV_OPENAI_LOCATION,
#       deployment-type flags) and allowed-region validation
#   14. Deployment hook scripts exist (prepackage, postdeploy, quota helpers)
#   15. Azure OpenAI model quota report (delegates to
#       infra/scripts/quota_check_params.ps1)
#
# Exit codes:
#   0 - All critical checks passed (warnings allowed)
#   1 - One or more critical checks failed (details printed)
#
# See docs/DeploymentPreChecks.md for the full reference.
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

    # Docker is required in Codespace/DevContainer environments where containers
    # back the dev workflow. On Local (host) machines we skip the check because
    # Docker is not needed for 'azd up' itself.
    if ($script:Environment -eq "Local") {
        Write-Info "Docker check skipped (Local environment)"
    }
    else {
        if (Test-CommandExists "docker") {
            try {
                $dockerInfo = docker info 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-OK "Docker is running (managed by $($script:Environment))"
                }
                else {
                    Add-CheckWarning "Docker is installed but the daemon is not running in $($script:Environment). It may be needed for container builds."
                    Write-Warn "Docker daemon is not running"
                }
            }
            catch {
                Add-CheckWarning "Docker is installed but could not verify daemon status in $($script:Environment)."
                Write-Warn "Docker daemon status unknown"
            }
        }
        else {
            Add-CheckWarning "Docker is not installed in $($script:Environment). It may be needed for container builds."
            Write-Warn "Docker is not installed"
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

# ── Check tenant match (TroubleShootingSteps: CrossTenantDeploymentNotPermitted)
# Catches two foot-guns:
#   1. The subscription is from a different tenant than the one it currently
#      lives in (homeTenantId != tenantId). Cross-tenant subscriptions can
#      block deployment with `CrossTenantDeploymentNotPermitted`.
#   2. The signed-in user is a Guest in the subscription's tenant. Guest
#      identities frequently lack the directory permissions needed for
#      role assignments and app-registration creation done by `azd up`.
function Test-TenantMatch {
    Write-Section "Azure Tenant Match"

    try {
        $accountInfo = az account show --output json 2>$null | ConvertFrom-Json
    }
    catch {
        $accountInfo = $null
    }
    if (-not $accountInfo) {
        Write-Info "Skipping tenant match check (not logged in to Azure)"
        Write-Host ""
        return
    }

    $tenantId = $accountInfo.tenantId
    $homeTenantId = $accountInfo.homeTenantId

    if ($tenantId -and $homeTenantId -and ($tenantId -ne $homeTenantId)) {
        Write-Warn "Subscription tenant ($tenantId) differs from its home tenant ($homeTenantId)."
        Write-Info  "  This is a cross-tenant subscription and may trigger 'CrossTenantDeploymentNotPermitted'."
        Add-CheckWarning "Subscription is cross-tenant (tenantId != homeTenantId). Deployment may fail with CrossTenantDeploymentNotPermitted."
    }
    else {
        Write-OK "Subscription tenant matches its home tenant ($tenantId)"
    }

    # Detect Guest user in the subscription's tenant
    $userType = $null
    try {
        $userType = (az ad signed-in-user show --query userType -o tsv 2>$null)
        if ($LASTEXITCODE -ne 0) { $userType = $null }
    }
    catch { $userType = $null }

    # Graph returns userType=null for many native Member accounts; only an
    # explicit "Guest" string indicates an external/guest identity.
    if ($userType -eq "Guest") {
        $upn = $accountInfo.user.name
        Write-Warn "Signed-in user '$upn' is a Guest in tenant $tenantId."
        Write-Info  "  Guest accounts often lack directory permissions required by 'azd up' (role assignments, app registrations)."
        Add-CheckWarning "Signed-in user is a Guest in the subscription's tenant; deployment may fail on role assignment or app-registration steps."
    }
    else {
        Write-OK "Signed-in user is a Member of tenant $tenantId"
    }

    Write-Host ""
}

# ── Check subscription role assignments (DeploymentGuide §1.1) ──────────────

# Roles required to deploy this solution end-to-end. Owner satisfies all of
# these. The check is informational (warning, not hard error) because the
# caller may rely on inherited Management Group assignments that are not
# returned by `az role assignment list` without elevated permissions.
$RequiredRoles = @(
    @{ Name = "Contributor"; Purpose = "Create and manage Azure resources" }
    @{ Name = "User Access Administrator"; Purpose = "Manage role assignments (RBAC)" }
    @{ Name = "Role Based Access Control Administrator"; Purpose = "Configure RBAC permissions" }
)

function Test-AzureRoles {
    Write-Section "Azure RBAC Roles (DeploymentGuide §1.1)"

    try {
        $accountInfo = az account show --output json 2>$null | ConvertFrom-Json
    }
    catch {
        $accountInfo = $null
    }
    if (-not $accountInfo) {
        Write-Info "Skipping role check (not logged in to Azure)"
        Write-Host ""
        return
    }

    # Resolve the caller's object id (works for users, SPNs, and managed identities)
    $callerOid = $null
    try {
        $callerOid = (az ad signed-in-user show --query id -o tsv 2>$null)
        if ($LASTEXITCODE -ne 0) { $callerOid = $null }
    }
    catch { $callerOid = $null }

    if (-not $callerOid) {
        # Service principal / managed identity path
        try {
            $callerOid = (az account show --query "user.name" -o tsv 2>$null)
        }
        catch { $callerOid = $null }
    }

    if (-not $callerOid) {
        Write-Warn "Could not determine signed-in identity object id; skipping role enumeration."
        Add-CheckWarning "Unable to verify subscription RBAC roles (could not resolve signed-in identity)."
        Write-Host ""
        return
    }

    $scope = "/subscriptions/$($accountInfo.id)"
    $assignments = $null
    try {
        $assignments = az role assignment list --assignee $callerOid --scope $scope --include-inherited --include-groups --output json 2>$null | ConvertFrom-Json
    }
    catch {
        $assignments = $null
    }

    if (-not $assignments) {
        Write-Warn "Could not list role assignments for the signed-in identity at subscription scope."
        Write-Info "If 'azd up' fails with authorization errors, request 'Contributor' + 'User Access Administrator' (or 'Owner') on subscription $($accountInfo.id)."
        Add-CheckWarning "Unable to verify subscription RBAC roles (insufficient permission to read role assignments)."
        Write-Host ""
        return
    }

    $roleNames = @($assignments | ForEach-Object { $_.roleDefinitionName })
    $hasOwner = $roleNames -contains "Owner"

    if ($hasOwner) {
        Write-OK "'Owner' role assigned (covers all required permissions)"
    }
    else {
        $missing = @()
        foreach ($r in $RequiredRoles) {
            if ($roleNames -contains $r.Name) {
                Write-OK "'$($r.Name)' assigned ($($r.Purpose))"
            }
            else {
                $missing += $r.Name
                Write-Warn "'$($r.Name)' not found ($($r.Purpose))"
            }
        }

        # User Access Administrator and RBAC Admin are interchangeable for our needs
        $hasAccessAdmin = ($roleNames -contains "User Access Administrator") -or ($roleNames -contains "Role Based Access Control Administrator")
        $hasContributor = $roleNames -contains "Contributor"

        if (-not $hasContributor -or -not $hasAccessAdmin) {
            Add-CheckWarning "Signed-in identity is missing one or more required roles at subscription scope ($($accountInfo.id)). Required: 'Contributor' + ('User Access Administrator' or 'Role Based Access Control Administrator'), or 'Owner'. Missing: $($missing -join ', ')."
            Write-Info "Request the missing roles or have an Owner run 'azd up'. See DeploymentGuide §1.1."
        }
    }
    Write-Host ""
}

# ── Check resource providers are registered (DeploymentGuide §1.2) ──────────

# Providers that this solution uses. Unregistered providers will cause
# 'azd up' to fail with cryptic 'NoRegisteredProviderFound' errors.
$RequiredProviders = @(
    "Microsoft.CognitiveServices",
    "Microsoft.Search",
    "Microsoft.App",
    "Microsoft.ContainerRegistry",
    "Microsoft.DocumentDB",
    "Microsoft.KeyVault",
    "Microsoft.Storage",
    "Microsoft.Web",
    "Microsoft.OperationalInsights",
    "Microsoft.Insights",
    "Microsoft.ManagedIdentity"
)

function Test-ResourceProviders {
    Write-Section "Azure Resource Providers (DeploymentGuide §1.2)"

    try {
        $accountInfo = az account show --output json 2>$null | ConvertFrom-Json
    }
    catch {
        $accountInfo = $null
    }
    if (-not $accountInfo) {
        Write-Info "Skipping provider check (not logged in to Azure)"
        Write-Host ""
        return
    }

    $unregistered = @()
    foreach ($ns in $RequiredProviders) {
        $state = $null
        try {
            $state = (az provider show --namespace $ns --query "registrationState" -o tsv 2>$null)
            if ($LASTEXITCODE -ne 0) { $state = $null }
        }
        catch { $state = $null }

        if ($state -eq "Registered") {
            Write-OK "$ns is Registered"
        }
        elseif ($state) {
            Write-Warn "$ns is '$state' (expected 'Registered')"
            $unregistered += $ns
        }
        else {
            Write-Warn "${ns}: could not determine registration state"
            $unregistered += $ns
        }
    }

    if ($unregistered.Count -gt 0) {
        Add-CheckWarning "The following resource providers are not 'Registered' on subscription $($accountInfo.id): $($unregistered -join ', '). Register with: az provider register --namespace <Namespace>"
        Write-Info "To register all at once: $($unregistered | ForEach-Object { 'az provider register --namespace ' + $_ } | Out-String)"
    }
    Write-Host ""
}

# ── Check App Registration creation permission (DeploymentGuide §1.1) ──────

# Directory roles that grant app registration creation rights.
$AppCreatorRoles = @(
    "Global Administrator",
    "Application Administrator",
    "Application Developer",
    "Cloud Application Administrator"
)

function Test-AppRegistrationPermission {
    Write-Section "App Registration Permission (DeploymentGuide §1.1)"

    try {
        $accountInfo = az account show --output json 2>$null | ConvertFrom-Json
    }
    catch {
        $accountInfo = $null
    }
    if (-not $accountInfo) {
        Write-Info "Skipping app registration check (not logged in to Azure)"
        Write-Host ""
        return
    }

    # Skip for service principals / managed identities — their app-creation
    # rights come from Graph API permissions, which can't be reliably probed.
    $userType = $accountInfo.user.type
    if ($userType -and $userType -ne "user") {
        Write-Info "Signed in as '$userType'; skipping interactive app registration check."
        Write-Host ""
        return
    }

    $userName = $accountInfo.user.name

    # Path 1: Caller holds a directory role that explicitly grants app creation.
    $rolesGranting = @()
    $memberOfReadable = $false
    try {
        $memberOf = az rest --method GET --url "https://graph.microsoft.com/v1.0/me/memberOf?`$select=id,displayName,@odata.type" --output json 2>$null | ConvertFrom-Json
        if ($memberOf -and $memberOf.value) {
            $memberOfReadable = $true
            foreach ($entry in $memberOf.value) {
                $type = $entry.'@odata.type'
                if ($type -eq "#microsoft.graph.directoryRole" -and ($AppCreatorRoles -contains $entry.displayName)) {
                    $rolesGranting += $entry.displayName
                }
            }
        }
    }
    catch { }

    if ($rolesGranting.Count -gt 0) {
        Write-OK "$userName can create app registrations via directory role: $($rolesGranting -join ', ')"
        Write-Host ""
        return
    }

    # Path 2: Tenant default permission lets every user create app registrations.
    $allowedToCreateApps = $null
    try {
        $policy = az rest --method GET --url "https://graph.microsoft.com/v1.0/policies/authorizationPolicy" --output json 2>$null | ConvertFrom-Json
        if ($policy) {
            $allowedToCreateApps = $policy.defaultUserRolePermissions.allowedToCreateApps
        }
    }
    catch { $allowedToCreateApps = $null }

    if ($allowedToCreateApps -eq $true) {
        Write-OK "$userName can create app registrations (granted by tenant default user permissions)"
        Write-Host ""
        return
    }

    if ($allowedToCreateApps -eq $false) {
        Write-Warn "$userName cannot create app registrations: tenant restricts creation to privileged roles and you do not hold any of: $($AppCreatorRoles -join ', ')."
        Add-CheckWarning "App registration creation may be blocked for $userName. If 'azd up' fails creating an Entra ID app, request 'Application Developer' (or higher) in the tenant. See DeploymentGuide §1.1."
    }
    else {
        # Tenant policy unreadable. Decide based on whether we could even read directory roles.
        if ($memberOfReadable) {
            Write-Warn "Could not verify app registration permission for $userName (no granting directory role assigned and tenant default policy is not readable from this account)."
        }
        else {
            Write-Warn "Could not verify app registration permission for $userName (insufficient Graph permission to inspect directory roles or tenant policy)."
        }
        Add-CheckWarning "Unable to verify app registration creation permission for $userName. If 'azd up' fails creating an Entra ID app, request 'Application Developer' (or higher) in the tenant. See DeploymentGuide §1.1."
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

# ── Recommended OpenAI regions (from docs/DeploymentGuide.md) ───────────────
$RecommendedOpenAIRegions = @("eastus", "eastus2", "australiaeast", "japaneast", "uksouth", "francecentral")

# Path to the canonical PowerShell quota check script (sibling of the bash version)
$QuotaCheckScript = "infra/scripts/quota_check_params.ps1"

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

    if (-not (Test-Path $QuotaCheckScript)) {
        Write-Warn "Quota check script not found at '$QuotaCheckScript'. Skipping."
        Write-Host ""
        return
    }

    # If the user has selected a specific region, pass it through; otherwise use
    # the script's defaults (8 recommended regions, 3 default models).
    $regionsArg = $null
    if ($env:AZURE_ENV_OPENAI_LOCATION) {
        $regionsArg = $env:AZURE_ENV_OPENAI_LOCATION.Trim()
    }
    else {
        $azdValue = & azd env get-value AZURE_ENV_OPENAI_LOCATION 2>$null
        if ($LASTEXITCODE -eq 0 -and $azdValue) {
            $candidate = $azdValue.ToString().Trim()
            if ($candidate -and ($candidate -notmatch '^\s*ERROR')) {
                $regionsArg = $candidate
            }
        }
    }

    Write-Info "Running '$QuotaCheckScript' (DeploymentGuide §1.3)..."
    if ($regionsArg) {
        Write-Info "Targeting selected region: $regionsArg"
    }
    else {
        Write-Info "No region selected. Using script defaults (8 regions, 3 models)."
    }
    Write-Host ""

    # Pre-set AZURE_SUBSCRIPTION_ID so the script never prompts when multiple
    # subscriptions are enabled.
    $previousSubId = $env:AZURE_SUBSCRIPTION_ID
    $env:AZURE_SUBSCRIPTION_ID = $accountInfo.id
    try {
        if ($regionsArg) {
            & pwsh -NoProfile -File $QuotaCheckScript -Regions $regionsArg
            if (-not $?) {
                & powershell -NoProfile -File $QuotaCheckScript -Regions $regionsArg
            }
        }
        else {
            & pwsh -NoProfile -File $QuotaCheckScript
            if (-not $?) {
                & powershell -NoProfile -File $QuotaCheckScript
            }
        }
    }
    finally {
        if ($null -eq $previousSubId) {
            Remove-Item Env:\AZURE_SUBSCRIPTION_ID -ErrorAction SilentlyContinue
        }
        else {
            $env:AZURE_SUBSCRIPTION_ID = $previousSubId
        }
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
    Test-TenantMatch
    Test-AzureRoles
    Test-AppRegistrationPermission
    Test-ResourceProviders
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
