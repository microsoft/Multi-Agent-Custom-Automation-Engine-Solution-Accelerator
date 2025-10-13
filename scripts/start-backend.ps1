# Start Backend Server
# This script starts the FastAPI backend server on port 8000

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Starting Multi-Agent Backend Server" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to backend directory
$backendDir = Join-Path $PSScriptRoot ".." "src" "backend"
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
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Aborted." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Starting uvicorn server..." -ForegroundColor Green
Write-Host "  URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the server
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

