# Azure CLI Helper Script
# Makes it easier to run Azure CLI commands without full path

# Check if az is in PATH
if (Get-Command az -ErrorAction SilentlyContinue) {
    Write-Host "✅ Azure CLI found in PATH" -ForegroundColor Green
    az --version
} else {
    Write-Host "⚠️  Azure CLI not in PATH, using full path..." -ForegroundColor Yellow
    
    # Common installation paths
    $azPaths = @(
        "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
        "C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
    )
    
    $azFound = $false
    foreach ($path in $azPaths) {
        if (Test-Path $path) {
            Write-Host "✅ Found Azure CLI at: $path" -ForegroundColor Green
            Set-Alias -Name az -Value $path -Scope Global
            $azFound = $true
            break
        }
    }
    
    if (-not $azFound) {
        Write-Host "❌ Azure CLI not found. Please install it:" -ForegroundColor Red
        Write-Host "   winget install Microsoft.AzureCLI" -ForegroundColor Yellow
        exit 1
    }
}

# Login to Azure
Write-Host "`n🔐 Logging in to Azure..." -ForegroundColor Cyan
az login

Write-Host "`n✅ Azure login complete!" -ForegroundColor Green
Write-Host "`nYou can now use 'az' commands in this PowerShell session." -ForegroundColor Yellow
Write-Host "Example: az account show" -ForegroundColor Gray

