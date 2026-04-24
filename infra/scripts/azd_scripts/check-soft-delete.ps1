<#
.SYNOPSIS
    Pre-provision hook: Informs users how to check for and purge soft-deleted
    Key Vault and Cognitive Services resources before deployment.
.DESCRIPTION
    Explains that if redeploying in the same environment, deployment can fail if
    resources with the same name exist in a soft-deleted state. Shows the user
    commands to check and purge, then prompts to proceed or abort.
#>

# Sanitize AZURE_ENV_NAME to match Bicep solutionSuffix logic:
# toLower, strip: - _ . / space *
function Get-SanitizedEnvName {
    param([string]$EnvName)
    $sanitized = $EnvName -replace '[-_./\s*]', ''
    return $sanitized.ToLower()
}

$envName = $env:AZURE_ENV_NAME
if ([string]::IsNullOrWhiteSpace($envName)) {
    Write-Host "WARNING: AZURE_ENV_NAME is not set. Cannot determine resource name patterns." -ForegroundColor Red
    Write-Host "Please ensure you are running this via 'azd provision' or 'azd up'." -ForegroundColor Yellow
    exit 1
}

$sanitizedName = Get-SanitizedEnvName -EnvName $envName

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Yellow
Write-Host " SOFT-DELETE RESOURCE CHECK" -ForegroundColor Green
Write-Host "===============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "If you are redeploying in the same environment, deployment can fail" -ForegroundColor White
Write-Host "if Key Vault or Cognitive Services accounts with the same name" -ForegroundColor White
Write-Host "exist in a soft-deleted state." -ForegroundColor White
Write-Host ""
Write-Host "Expected resource name patterns (based on AZURE_ENV_NAME='$envName'):" -ForegroundColor Cyan
Write-Host "  Key Vault:          kv-$sanitizedName*" -ForegroundColor White
Write-Host "  Cognitive Services: aif-$sanitizedName*" -ForegroundColor White
Write-Host ""
Write-Host "Please open a SEPARATE terminal to check and purge any soft-deleted resources," -ForegroundColor Yellow
Write-Host "then come back to THIS terminal to continue the deployment." -ForegroundColor Yellow
Write-Host ""
Write-Host "Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Check for soft-deleted Key Vaults:" -ForegroundColor White
Write-Host "       az keyvault list-deleted --query `"[?starts_with(name, 'kv-$sanitizedName')].[name, properties.location, properties.deletionDate]`" -o table" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Check for soft-deleted Cognitive Services accounts:" -ForegroundColor White
Write-Host "       az cognitiveservices account list-deleted --query `"[?starts_with(name, 'aif-$sanitizedName')].[name, location, resourceGroup, deletionDate]`" -o table" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. If soft-deleted Key Vaults are found, purge them:" -ForegroundColor White
Write-Host "       az keyvault purge --name <name> --location <location>" -ForegroundColor Cyan
Write-Host ""
Write-Host "  4. If soft-deleted Cognitive Services accounts are found, purge them:" -ForegroundColor White
Write-Host "       az cognitiveservices account purge --name <name> --location <location> --resource-group <resource-group>" -ForegroundColor Cyan
Write-Host ""
Write-Host "  If not purged, deployment may fail with 'FlagMustBeSetForRestore' or" -ForegroundColor Yellow
Write-Host "  'CustomDomainInUse' errors." -ForegroundColor Yellow
Write-Host ""
Write-Host "===============================================================" -ForegroundColor Yellow
Write-Host ""

while ($true) {
    $response = Read-Host "Do you want to proceed with deployment? (y/n)"

    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host ""
        Write-Host "Proceeding with deployment..." -ForegroundColor Green
        exit 0
    }
    elseif ($response -eq 'n' -or $response -eq 'N') {
        Write-Host ""
        Write-Host "Deployment aborted by user." -ForegroundColor Red
        exit 1
    }
    else {
        Write-Host "Invalid input. Please enter 'y' or 'n'." -ForegroundColor Yellow
    }
}
