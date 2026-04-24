<#
.SYNOPSIS
    Pre-provision hook: Checks Bicep CLI version and offers to update if outdated.
.DESCRIPTION
    Automatically detects the installed Bicep CLI version via Azure CLI,
    compares against the minimum required version (0.33.0), and offers
    to install or upgrade if needed.
#>

$MIN_BICEP_VERSION = "0.33.0"

function Compare-SemVer {
    param(
        [string]$Current,
        [string]$Minimum
    )
    $currentParts = $Current.Split('.') | ForEach-Object { [int]$_ }
    $minimumParts = $Minimum.Split('.') | ForEach-Object { [int]$_ }

    for ($i = 0; $i -lt 3; $i++) {
        if ($currentParts[$i] -gt $minimumParts[$i]) { return 1 }
        if ($currentParts[$i] -lt $minimumParts[$i]) { return -1 }
    }
    return 0
}

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Yellow
Write-Host " BICEP VERSION CHECK" -ForegroundColor Green
Write-Host "===============================================================" -ForegroundColor Yellow
Write-Host ""

# Attempt to get Bicep version
$bicepInstalled = $true
$bicepVersionOutput = $null
try {
    $bicepVersionOutput = az bicep version 2>&1
    if ($LASTEXITCODE -ne 0) {
        $bicepInstalled = $false
    }
}
catch {
    $bicepInstalled = $false
}

if (-not $bicepInstalled -or [string]::IsNullOrWhiteSpace($bicepVersionOutput)) {
    Write-Host "Bicep CLI is not installed." -ForegroundColor Red
    Write-Host "This accelerator requires Bicep CLI version >= $MIN_BICEP_VERSION." -ForegroundColor White
    Write-Host ""

    while ($true) {
        $response = Read-Host "Would you like us to install Bicep CLI? (y/n)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            Write-Host ""
            Write-Host "Installing Bicep CLI..." -ForegroundColor Cyan
            az bicep install
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Failed to install Bicep CLI. Please install manually: az bicep install" -ForegroundColor Red
                exit 1
            }
            Write-Host "Bicep CLI installed successfully." -ForegroundColor Green
            exit 0
        }
        elseif ($response -eq 'n' -or $response -eq 'N') {
            Write-Host ""
            Write-Host "Bicep CLI >= $MIN_BICEP_VERSION is required. Deployment aborted." -ForegroundColor Red
            exit 1
        }
        else {
            Write-Host "Invalid input. Please enter 'y' or 'n'." -ForegroundColor Yellow
        }
    }
}

# Parse version from output like "Bicep CLI version 0.33.93 (1933ecab67)"
$versionMatch = [regex]::Match($bicepVersionOutput, '(\d+\.\d+\.\d+)')
if (-not $versionMatch.Success) {
    Write-Host "Could not parse Bicep version from output: $bicepVersionOutput" -ForegroundColor Red
    Write-Host "Please check your Bicep installation manually." -ForegroundColor Yellow
    exit 1
}

$currentVersion = $versionMatch.Groups[1].Value
$comparison = Compare-SemVer -Current $currentVersion -Minimum $MIN_BICEP_VERSION

if ($comparison -ge 0) {
    Write-Host "Bicep CLI version $currentVersion detected. Meets minimum requirement (>= $MIN_BICEP_VERSION)." -ForegroundColor Green
    Write-Host ""
    exit 0
}

# Version is below minimum
Write-Host "Bicep CLI version $currentVersion detected." -ForegroundColor Yellow
Write-Host "This accelerator requires Bicep CLI version >= $MIN_BICEP_VERSION." -ForegroundColor White
Write-Host ""

while ($true) {
    $response = Read-Host "Would you like us to upgrade Bicep CLI? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host ""
        Write-Host "Upgrading Bicep CLI..." -ForegroundColor Cyan
        az bicep upgrade
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to upgrade Bicep CLI. Please upgrade manually: az bicep upgrade" -ForegroundColor Red
            exit 1
        }
        Write-Host "Bicep CLI upgraded successfully." -ForegroundColor Green
        exit 0
    }
    elseif ($response -eq 'n' -or $response -eq 'N') {
        Write-Host ""
        Write-Host "Bicep CLI >= $MIN_BICEP_VERSION is required. Deployment aborted." -ForegroundColor Red
        exit 1
    }
    else {
        Write-Host "Invalid input. Please enter 'y' or 'n'." -ForegroundColor Yellow
    }
}
