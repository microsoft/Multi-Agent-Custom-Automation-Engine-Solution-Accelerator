# Multi-Agent Automation Engine - Full Stack Startup Script
# This script opens 3 terminals and starts all services in the correct order

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   Starting Multi-Agent Automation Engine" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Project directory: $scriptDir" -ForegroundColor Yellow
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  [OK] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python not found! Please install Python 3.13+" -ForegroundColor Red
    exit 1
}

# Check Node
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  [OK] Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Node.js not found (optional for backend-only)" -ForegroundColor Yellow
}

# Check .env files
if (Test-Path "$scriptDir\src\backend\.env") {
    Write-Host "  [OK] Backend .env file found" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Backend .env file missing!" -ForegroundColor Red
    Write-Host "     Run: python scripts/test_env.py" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   Opening terminals for each service..." -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend in new terminal
Write-Host "[1/3] Starting Backend API (Port 8000)..." -ForegroundColor Cyan
$backendCmd = "cd '$scriptDir\src\backend'; Write-Host 'Starting Backend API...' -ForegroundColor Cyan; uvicorn app_kernel:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Sleep -Seconds 3

# Start MCP Server in new terminal
Write-Host "[2/3] Starting MCP Server (Port 8001)..." -ForegroundColor Cyan
$mcpCmd = "cd '$scriptDir\src\mcp_server'; Write-Host 'Starting MCP Server...' -ForegroundColor Cyan; python -m mcp_server"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $mcpCmd
Start-Sleep -Seconds 2

# Start Frontend in new terminal (if Node is installed)
if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "[3/3] Starting Frontend Dashboard (Port 3001)..." -ForegroundColor Cyan
    $frontendCmd = "cd '$scriptDir\src\frontend'; Write-Host 'Starting Frontend...' -ForegroundColor Cyan; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
    Start-Sleep -Seconds 2
} else {
    Write-Host "[3/3] Skipping Frontend (Node.js not installed)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "   All services starting in separate terminals!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Yellow
Write-Host "   Backend API:     http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs:        http://localhost:8000/docs" -ForegroundColor White
Write-Host "   MCP Server:      http://localhost:8001" -ForegroundColor White
if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "   Frontend:        http://localhost:3001" -ForegroundColor White
    Write-Host "   Dashboard:       http://localhost:3001/analytics" -ForegroundColor White
}
Write-Host ""
Write-Host "Wait ~30 seconds for all services to start..." -ForegroundColor Yellow
Write-Host ""
Write-Host "To verify everything is working:" -ForegroundColor Cyan
Write-Host "   python scripts/testing/test_analytics_api.py" -ForegroundColor White
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Cyan
Write-Host "   Press Ctrl+C in each terminal window" -ForegroundColor White
Write-Host ""
Write-Host "For more info, see: START_EVERYTHING.md" -ForegroundColor Cyan
Write-Host ""

# Wait a bit, then open browser
Start-Sleep -Seconds 8
Write-Host "Opening API documentation in browser..." -ForegroundColor Green
Start-Process "http://localhost:8000/docs"

Write-Host ""
Write-Host "Startup complete! Check the opened terminal windows." -ForegroundColor Green
Write-Host ""
