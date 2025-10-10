# Frontend Development Server Launcher
# Sprint 4 - Analytics Dashboard

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Frontend Development Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to frontend directory
Set-Location -Path "src\frontend"

Write-Host "Installing dependencies (if needed)..." -ForegroundColor Yellow
npm install

Write-Host ""
Write-Host "Starting Vite development server..." -ForegroundColor Green
Write-Host ""
Write-Host "Once started, visit:" -ForegroundColor Yellow
Write-Host "  - Home: http://localhost:5173/" -ForegroundColor White
Write-Host "  - Analytics Dashboard: http://localhost:5173/analytics" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Start Vite dev server
npm run dev

