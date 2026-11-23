#!/usr/bin/env pwsh
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: MIT
#Requires -Version 7.0

<#
.SYNOPSIS
    Configures Microsoft Entra ID authentication for MACAE after deployment.

.DESCRIPTION
    Creates or reuses a single-tenant app registration, configures App Service
    Authentication (Easy Auth) on the frontend App Service, and enables API
    authentication on the backend Container App by setting AUTH_CLIENT_ID.

    Run this script AFTER post_deploy.ps1 has uploaded the team configurations,
    because in WAF deployments post_deploy calls the backend through the
    frontend URL, which requires sign-in once this script has run.

    Re-run it after every 'azd provision' / 'azd up': provisioning resets the
    backend environment variables and the frontend app settings.

    Values are resolved from the script parameters, then process environment
    variables, then the current azd environment. The app registration client ID
    is saved to the azd environment (AZURE_AUTH_CLIENT_ID) so reruns reuse it.

.PARAMETER ResourceGroup
    Resource group containing the deployment. Defaults to RESOURCE_GROUP_NAME.
.PARAMETER FrontendAppName
    Frontend App Service name. Defaults to FRONTEND_WEB_APP_NAME.
.PARAMETER BackendContainerAppName
    Backend Container App name. Defaults to BACKEND_CONTAINER_APP_NAME.
.PARAMETER ClientId
    Existing app registration client ID to reuse. Defaults to AZURE_AUTH_CLIENT_ID.
.PARAMETER AppDisplayName
    Display name used when creating a new app registration.

.EXAMPLE
    ./infra/scripts/post-provision/configure_auth.ps1
.EXAMPLE
    ./infra/scripts/post-provision/configure_auth.ps1 -ResourceGroup rg-macae -ClientId 00000000-0000-0000-0000-000000000000
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $false)]
    [string]$FrontendAppName,

    [Parameter(Mandatory = $false)]
    [string]$BackendContainerAppName,

    [Parameter(Mandatory = $false)]
    [string]$ClientId,

    [Parameter(Mandatory = $false)]
    [string]$AppDisplayName
)

$ErrorActionPreference = 'Stop'

$SecretSettingName = 'MICROSOFT_PROVIDER_AUTHENTICATION_SECRET'
$ScopeValue = 'user_impersonation'
# Pre-authorized so post-deployment scripts can run:
# az account get-access-token --resource api://<clientId>
$AzureCliAppId = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'

#region Functions

function Test-CommandAvailable {
    <#
    .SYNOPSIS
        Returns whether a command is available on the PATH.
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-AzdEnvValue {
    <#
    .SYNOPSIS
        Reads a value from the current azd environment, or returns $null.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $true)][string]$Key)
    if (-not (Test-CommandAvailable 'azd')) { return $null }
    $value = azd env get-value $Key 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($value)) { return $null }
    if ($value -match 'ERROR:' -or $value -match 'not found') { return $null }
    return ($value | Out-String).Trim()
}

function Resolve-Value {
    <#
    .SYNOPSIS
        Resolves a value from a parameter, process environment variable, or azd environment.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $false)][string]$Value,
        [Parameter(Mandatory = $true)][string[]]$EnvironmentKeys
    )
    if (-not [string]::IsNullOrWhiteSpace($Value)) { return $Value.Trim() }
    foreach ($key in $EnvironmentKeys) {
        $processValue = [Environment]::GetEnvironmentVariable($key)
        if (-not [string]::IsNullOrWhiteSpace($processValue)) { return $processValue.Trim() }
        $azdValue = Get-AzdEnvValue $key
        if ($azdValue) { return $azdValue }
    }
    return $null
}

function Invoke-Az {
    <#
    .SYNOPSIS
        Runs an Azure CLI command and throws when it fails.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = az @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI command failed: az $($Arguments[0..([Math]::Min(2, $Arguments.Count - 1))] -join ' ')"
    }
    return ($output | Out-String).Trim()
}

function Invoke-AzRestWithBody {
    <#
    .SYNOPSIS
        Sends a JSON body with 'az rest' using a temporary file.
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param(
        [Parameter(Mandatory = $true)][ValidateSet('put', 'patch')][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][hashtable]$Body
    )
    $tempFile = New-TemporaryFile
    try {
        Set-Content -LiteralPath $tempFile.FullName -Value ($Body | ConvertTo-Json -Depth 10 -Compress) -NoNewline
        Invoke-Az @('rest', '--method', $Method, '--uri', $Uri, '--headers', 'Content-Type=application/json', '--body', "@$($tempFile.FullName)", '--output', 'none') | Out-Null
    }
    finally {
        Remove-Item -LiteralPath $tempFile.FullName -Force -ErrorAction SilentlyContinue
    }
}

function Get-AppRegistration {
    <#
    .SYNOPSIS
        Returns the app registration for a client ID.
    #>
    [CmdletBinding()]
    [OutputType([psobject])]
    param([Parameter(Mandatory = $true)][string]$AppClientId)
    return Invoke-Az @('ad', 'app', 'show', '--id', $AppClientId, '--output', 'json') | ConvertFrom-Json
}

function Get-ExistingFrontendSecret {
    <#
    .SYNOPSIS
        Returns the frontend's Easy Auth secret if it is already configured for this client ID.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)][string]$AuthSettingsUri,
        [Parameter(Mandatory = $true)][string]$ExpectedClientId
    )
    $configuredClientId = az rest --method get --uri $AuthSettingsUri --query 'properties.identityProviders.azureActiveDirectory.registration.clientId' -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or ($configuredClientId | Out-String).Trim() -ne $ExpectedClientId) { return $null }
    $secret = az webapp config appsettings list --resource-group $script:ResourceGroup --name $script:FrontendAppName --query "[?name=='$SecretSettingName'].value | [0]" -o tsv 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($secret)) { return $null }
    return ($secret | Out-String).Trim()
}

#endregion Functions

#region Main Execution

function Invoke-Main {
    <#
    .SYNOPSIS
        Configures the app registration, frontend Easy Auth, and backend API authentication.
    #>
    [CmdletBinding()]
    [OutputType([void])]
    param()

    if (-not (Test-CommandAvailable 'az')) { throw "Azure CLI ('az') is required." }

    $account = Invoke-Az @('account', 'show', '--output', 'json') | ConvertFrom-Json
    $tenantId = $account.tenantId
    $subscriptionId = $account.id

    $script:ResourceGroup = Resolve-Value $ResourceGroup @('RESOURCE_GROUP_NAME', 'AZURE_RESOURCE_GROUP')
    $script:FrontendAppName = Resolve-Value $FrontendAppName @('FRONTEND_WEB_APP_NAME')
    $script:BackendContainerAppName = Resolve-Value $BackendContainerAppName @('BACKEND_CONTAINER_APP_NAME')
    $resolvedClientId = Resolve-Value $ClientId @('AZURE_AUTH_CLIENT_ID')

    $requiredValues = [ordered]@{
        ResourceGroup           = $script:ResourceGroup
        FrontendAppName         = $script:FrontendAppName
        BackendContainerAppName = $script:BackendContainerAppName
    }
    foreach ($required in $requiredValues.GetEnumerator()) {
        if ([string]::IsNullOrWhiteSpace($required.Value)) {
            throw "Missing $($required.Key). Pass -$($required.Key) or run from the azd environment used for the deployment."
        }
    }

    # The backend validates the token issuer against its AZURE_TENANT_ID (set by Bicep).
    $backendTenantId = az containerapp show --name $script:BackendContainerAppName --resource-group $script:ResourceGroup --query "properties.template.containers[0].env[?name=='AZURE_TENANT_ID'].value | [0]" -o tsv 2>$null
    $backendTenantId = ($backendTenantId | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Backend Container App '$($script:BackendContainerAppName)' was not found in '$($script:ResourceGroup)'." }
    if ($backendTenantId -and $backendTenantId -ne $tenantId) {
        throw "Signed-in tenant '$tenantId' differs from the backend AZURE_TENANT_ID '$backendTenantId'. Run 'az login --tenant $backendTenantId' and retry."
    }

    $frontendHostName = Invoke-Az @('webapp', 'show', '--resource-group', $script:ResourceGroup, '--name', $script:FrontendAppName, '--query', 'defaultHostName', '--output', 'tsv')
    $redirectUri = "https://$frontendHostName/.auth/login/aad/callback"

    Write-Host ""
    Write-Host "Resource group:   $($script:ResourceGroup)"
    Write-Host "Frontend:         $($script:FrontendAppName) (https://$frontendHostName)"
    Write-Host "Backend:          $($script:BackendContainerAppName)"
    Write-Host "Tenant:           $tenantId"
    Write-Host ""

    # --- App registration ---------------------------------------------------
    if ($resolvedClientId) {
        $application = Get-AppRegistration $resolvedClientId
        Write-Host "Reusing app registration '$($application.displayName)' ($resolvedClientId)."
    }
    else {
        if ([string]::IsNullOrWhiteSpace($AppDisplayName)) {
            $environmentName = Get-AzdEnvValue 'AZURE_ENV_NAME'
            $AppDisplayName = if ($environmentName) { "$environmentName-macae-auth" } else { "$($script:FrontendAppName)-auth" }
        }
        Write-Host "Creating app registration '$AppDisplayName'."
        $application = Invoke-Az @('ad', 'app', 'create', '--display-name', $AppDisplayName, '--sign-in-audience', 'AzureADMyOrg', '--enable-id-token-issuance', 'true', '--web-redirect-uris', $redirectUri, '--output', 'json') | ConvertFrom-Json
        $resolvedClientId = $application.appId
    }

    $redirectUris = @(@($application.web.redirectUris) + $redirectUri | Where-Object { $_ } | Sort-Object -Unique)
    Invoke-Az (@('ad', 'app', 'update', '--id', $resolvedClientId, '--enable-id-token-issuance', 'true', '--web-redirect-uris') + $redirectUris + @('--output', 'none')) | Out-Null

    $identifierUris = @(@($application.identifierUris) + "api://$resolvedClientId" | Where-Object { $_ } | Sort-Object -Unique)
    Invoke-Az (@('ad', 'app', 'update', '--id', $resolvedClientId, '--identifier-uris') + $identifierUris + @('--output', 'none')) | Out-Null

    # Expose api://<clientId>/user_impersonation (v2 access tokens)
    $graphUri = "https://graph.microsoft.com/v1.0/applications/$($application.id)"
    $scopes = @($application.api.oauth2PermissionScopes | Where-Object { $_ })
    $scope = $scopes | Where-Object { $_.value -eq $ScopeValue } | Select-Object -First 1
    if (-not $scope) {
        $scope = [pscustomobject]@{
            adminConsentDescription = 'Access the MACAE API on behalf of the signed-in user.'
            adminConsentDisplayName = 'Access the MACAE API'
            id                      = [guid]::NewGuid().ToString()
            isEnabled               = $true
            type                    = 'User'
            userConsentDescription  = 'Allow this application to access the MACAE API on your behalf.'
            userConsentDisplayName  = 'Access the MACAE API'
            value                   = $ScopeValue
        }
        $scopes += $scope
    }
    Invoke-AzRestWithBody -Method 'patch' -Uri $graphUri -Body @{
        api = @{ oauth2PermissionScopes = $scopes; requestedAccessTokenVersion = 2 }
    }

    # A pre-authorization can only reference a scope that already exists, so it is a separate update.
    $preAuthorized = @($application.api.preAuthorizedApplications | Where-Object { $_ -and $_.appId -ne $AzureCliAppId })
    $preAuthorized += [pscustomobject]@{ appId = $AzureCliAppId; delegatedPermissionIds = @($scope.id) }
    Invoke-AzRestWithBody -Method 'patch' -Uri $graphUri -Body @{
        api = @{ preAuthorizedApplications = $preAuthorized }
    }
    Write-Host "✅ App registration configured (client ID: $resolvedClientId)." -ForegroundColor Green

    # --- Frontend App Service Authentication --------------------------------
    $authSettingsUri = "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/$($script:ResourceGroup)/providers/Microsoft.Web/sites/$($script:FrontendAppName)/config/authsettingsV2?api-version=2022-09-01"
    $clientSecret = Get-ExistingFrontendSecret -AuthSettingsUri $authSettingsUri -ExpectedClientId $resolvedClientId
    if (-not $clientSecret) {
        Write-Host "Creating a client secret for App Service Authentication."
        $clientSecret = Invoke-Az @('ad', 'app', 'credential', 'reset', '--id', $resolvedClientId, '--append', '--display-name', 'MACAE App Service Authentication', '--years', '2', '--query', 'password', '--output', 'tsv')
    }

    Write-Host "Configuring App Service Authentication on '$($script:FrontendAppName)'."
    Invoke-Az @('webapp', 'config', 'appsettings', 'set', '--resource-group', $script:ResourceGroup, '--name', $script:FrontendAppName, '--settings', "$SecretSettingName=$clientSecret", '--output', 'none') | Out-Null

    # The MACAE frontend does not redirect anonymous users itself, so the platform must.
    Invoke-AzRestWithBody -Method 'put' -Uri $authSettingsUri -Body @{
        properties = @{
            platform          = @{ enabled = $true; runtimeVersion = '~1' }
            globalValidation  = @{ requireAuthentication = $true; unauthenticatedClientAction = 'RedirectToLoginPage'; redirectToProvider = 'azureactivedirectory' }
            httpSettings      = @{ requireHttps = $true }
            identityProviders = @{
                azureActiveDirectory = @{
                    enabled      = $true
                    registration = @{
                        clientId                = $resolvedClientId
                        clientSecretSettingName = $SecretSettingName
                        openIdIssuer            = "https://login.microsoftonline.com/$tenantId/v2.0"
                    }
                    login        = @{ loginParameters = @("scope=openid profile email offline_access api://$resolvedClientId/$ScopeValue") }
                    validation   = @{ allowedAudiences = @($resolvedClientId, "api://$resolvedClientId") }
                }
            }
            login             = @{ tokenStore = @{ enabled = $true } }
        }
    }
    Write-Host "✅ App Service Authentication configured." -ForegroundColor Green

    if (Test-CommandAvailable 'azd') {
        azd env set AZURE_AUTH_CLIENT_ID $resolvedClientId 2>$null | Out-Null
    }

    # --- Backend API authentication -----------------------------------------
    Write-Host "Enabling API authentication on '$($script:BackendContainerAppName)'."
    Invoke-Az @('containerapp', 'update', '--name', $script:BackendContainerAppName, '--resource-group', $script:ResourceGroup, '--set-env-vars', "AUTH_CLIENT_ID=$resolvedClientId", '--output', 'none') | Out-Null
    Write-Host "✅ Backend AUTH_CLIENT_ID set to $resolvedClientId." -ForegroundColor Green

    Write-Host ""
    Write-Host "Authentication configured. Allow a few minutes for the changes to take effect, then sign in at https://$frontendHostName" -ForegroundColor Green
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        Invoke-Main
        exit 0
    }
    catch {
        Write-Error -ErrorAction Continue "configure_auth failed: $($_.Exception.Message)"
        exit 1
    }
}

#endregion Main Execution
