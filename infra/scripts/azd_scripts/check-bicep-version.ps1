<#
.SYNOPSIS
    Pre-provision hook: Informs users about the minimum Bicep CLI version requirement.
.DESCRIPTION
    Displays the minimum Bicep version needed (>= 0.33.0) and provides steps
    to check, install, or upgrade Bicep via Azure CLI. Prompts the user to
    confirm before proceeding with deployment.
#>

$MIN_BICEP_VERSION = "0.33.0"

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Yellow
Write-Host " BICEP VERSION CHECK" -ForegroundColor Green
Write-Host "===============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "This accelerator requires Bicep CLI version >= $MIN_BICEP_VERSION." -ForegroundColor White
Write-Host ""
Write-Host "Please open a SEPARATE terminal to check and update your Bicep version," -ForegroundColor Yellow
Write-Host "then come back to THIS terminal to continue the deployment." -ForegroundColor Yellow
Write-Host ""
Write-Host "Steps:" -ForegroundColor Cyan
Write-Host "  1. Check your current Bicep version:" -ForegroundColor White
Write-Host "       az bicep version" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. If Bicep is not installed, install it:" -ForegroundColor White
Write-Host "       az bicep install" -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. If Bicep is installed but version is below $MIN_BICEP_VERSION, upgrade it:" -ForegroundColor White
Write-Host "       az bicep upgrade" -ForegroundColor Cyan
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
