# Upload Default Teams via Backend API
# This script uploads the default teams using the backend's REST API endpoint

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   Upload Default Teams via Backend API" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v3/analytics/health" -UseBasicParsing -TimeoutSec 2
    Write-Host "[OK] Backend is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Backend is not running!" -ForegroundColor Red
    Write-Host "Please start the backend first:" -ForegroundColor Yellow
    Write-Host "  cd src/backend" -ForegroundColor White
    Write-Host "  uvicorn app_kernel:app --reload --port 8000" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$teamsDir = Join-Path (Split-Path -Parent $scriptDir) "data\agent_teams"

# Define teams with their fixed IDs
$teams = @(
    @{File="hr.json"; ID="00000000-0000-0000-0000-000000000001"; Name="HR Team"},
    @{File="marketing.json"; ID="00000000-0000-0000-0000-000000000002"; Name="Marketing Team"},
    @{File="retail.json"; ID="00000000-0000-0000-0000-000000000003"; Name="Retail Team"},
    @{File="finance_forecasting.json"; ID="00000000-0000-0000-0000-000000000004"; Name="Finance Team"}
)

$uploaded = 0
$failed = 0

foreach ($team in $teams) {
    $filePath = Join-Path $teamsDir $team.File
    
    Write-Host "Uploading: $($team.Name) ($($team.File))" -ForegroundColor Cyan
    Write-Host "  Team ID: $($team.ID)" -ForegroundColor Gray
    
    if (-not (Test-Path $filePath)) {
        Write-Host "  [ERROR] File not found: $filePath" -ForegroundColor Red
        $failed++
        continue
    }
    
    try {
        # Read file content
        $fileContent = Get-Content $filePath -Raw
        $fileBytes = [System.Text.Encoding]::UTF8.GetBytes($fileContent)
        
        # Create multipart form data
        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        
        $bodyLines = @(
            "--$boundary",
            "Content-Disposition: form-data; name=`"file`"; filename=`"$($team.File)`"",
            "Content-Type: application/json$LF",
            $fileContent,
            "--$boundary--$LF"
        ) -join $LF
        
        # Upload
        $response = Invoke-WebRequest `
            -Uri "http://localhost:8000/api/v3/upload_team_config?team_id=$($team.ID)" `
            -Method POST `
            -ContentType "multipart/form-data; boundary=$boundary" `
            -Body $bodyLines `
            -UseBasicParsing
        
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] Successfully uploaded!" -ForegroundColor Green
            $uploaded++
        } else {
            Write-Host "  [WARN] Upload returned status: $($response.StatusCode)" -ForegroundColor Yellow
            $uploaded++
        }
    } catch {
        Write-Host "  [ERROR] Failed to upload: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
    
    Write-Host ""
}

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   Upload Summary" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  Uploaded: $uploaded" -ForegroundColor $(if ($uploaded -gt 0) { "Green" } else { "Gray" })
Write-Host "  Failed:   $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Gray" })
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

if ($uploaded -gt 0) {
    Write-Host "[OK] Teams uploaded successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Refresh your frontend at http://localhost:3001" -ForegroundColor White
    Write-Host "  2. The team initialization should now work" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "[WARN] No teams were uploaded." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Try using the Swagger UI instead:" -ForegroundColor Cyan
    Write-Host "  1. Open http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  2. Find /api/v3/upload_team_config endpoint" -ForegroundColor White
    Write-Host "  3. Click 'Try it out' and upload each file manually" -ForegroundColor White
    Write-Host ""
}

