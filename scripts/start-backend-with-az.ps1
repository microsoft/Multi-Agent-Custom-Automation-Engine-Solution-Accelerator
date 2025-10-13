# Start Backend Server with Azure CLI in PATH
# This script ensures Azure CLI is available to the Python backend

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Starting Multi-Agent Backend Server (with Azure CLI)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Add Azure CLI to PATH for this session
$azCliPath = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin"
if (Test-Path $azCliPath) {
    $env:Path = "$azCliPath;$env:Path"
    Write-Host "Added Azure CLI to PATH" -ForegroundColor Green
} else {
    Write-Host "WARNING: Azure CLI not found at: $azCliPath" -ForegroundColor Yellow
    Write-Host "Azure authentication may fail!" -ForegroundColor Yellow
}

# Navigate to backend directory
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "src\backend"
Write-Host "Navigating to: $backendDir" -ForegroundColor Yellow

if (-not (Test-Path $backendDir)) {
    Write-Host "ERROR: Backend directory not found!" -ForegroundColor Red
    Write-Host "Looking for: $backendDir" -ForegroundColor Red
    exit 1
}

Set-Location $backendDir

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Backend may not start correctly without environment variables." -ForegroundColor Yellow
    Write-Host ""
}

# Verify Azure CLI is accessible
Write-Host ""
Write-Host "Verifying Azure CLI..." -ForegroundColor Yellow
try {
    $azVersion = az --version 2>&1 | Select-Object -First 1
    Write-Host "  $azVersion" -ForegroundColor Green
    
    $account = az account show 2>&1 | ConvertFrom-Json
    Write-Host "  Logged in as: $($account.user.name)" -ForegroundColor Green
    Write-Host "  Subscription: $($account.name)" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Azure CLI not working or not logged in!" -ForegroundColor Red
    Write-Host "  Run: az login" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting uvicorn server..." -ForegroundColor Green
Write-Host "  URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the server (PATH is inherited by uvicorn process)
try {
    uvicorn app_kernel:app --reload --port 8000
}
catch {
    Write-Host ""
    Write-Host "ERROR: Failed to start backend server!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure uvicorn is installed:" -ForegroundColor Yellow
    Write-Host "  pip install uvicorn" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

