# Start MCP Server
# This script starts the MCP (Model Context Protocol) server

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Starting MCP Server" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to MCP server directory
$repoRoot = Split-Path -Parent $PSScriptRoot
$mcpDir = Join-Path $repoRoot "src\mcp_server"
Write-Host "Navigating to: $mcpDir" -ForegroundColor Yellow

if (-not (Test-Path $mcpDir)) {
    Write-Host "ERROR: MCP server directory not found!" -ForegroundColor Red
    Write-Host "Looking for: $mcpDir" -ForegroundColor Red
    exit 1
}

Set-Location $mcpDir

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "MCP server may not start correctly without environment variables." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ""
Write-Host "Starting MCP server..." -ForegroundColor Green
Write-Host "  URL: http://localhost:8001" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the MCP server with streamable-http transport on port 8001
try {
    python mcp_server.py --transport streamable-http --port 8001 --no-auth
}
catch {
    Write-Host ""
    Write-Host "ERROR: Failed to start MCP server!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure Python is installed and mcp_server module exists" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

