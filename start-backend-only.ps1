# Multi-Agent Automation Engine - Backend Only Startup
# Quick script to start just the backend for testing

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   Starting Backend API Only" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check .env file
if (Test-Path "$scriptDir\src\backend\.env") {
    Write-Host "[OK] Environment configured" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Backend .env file missing!" -ForegroundColor Red
    Write-Host "   Run: python scripts/test_env.py" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting Backend API on port 8000..." -ForegroundColor Cyan
Write-Host ""
Write-Host "URLs:" -ForegroundColor Yellow
Write-Host "   API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Health Check: http://localhost:8000/api/v3/analytics/health" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Change to backend directory and start
Set-Location "$scriptDir\src\backend"
uvicorn app_kernel:app --reload --port 8000
