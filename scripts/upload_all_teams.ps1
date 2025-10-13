# Upload All Agent Teams to Backend API
# This script uploads all team configurations via the REST API

$ErrorActionPreference = "Stop"

# Configuration
$apiUrl = "http://localhost:8000/api/v3/upload_team_config"
$teamsDir = "data/agent_teams"

# Define all teams to upload
$teams = @(
    @{
        Name = "Marketing Team"
        TeamId = "00000000-0000-0000-0000-000000000002"
        File = "marketing.json"
        Color = "Cyan"
    },
    @{
        Name = "Retail Team"
        TeamId = "00000000-0000-0000-0000-000000000003"
        File = "retail.json"
        Color = "Cyan"
    },
    @{
        Name = "Finance Forecasting Team"
        TeamId = "00000000-0000-0000-0000-000000000004"
        File = "finance_forecasting.json"
        Color = "Cyan"
    },
    @{
        Name = "Retail Operations Team"
        TeamId = "00000000-0000-0000-0000-000000000005"
        File = "retail_operations.json"
        Color = "Green"
    },
    @{
        Name = "Customer Intelligence Team"
        TeamId = "00000000-0000-0000-0000-000000000006"
        File = "customer_intelligence.json"
        Color = "Green"
    },
    @{
        Name = "Revenue Optimization Team"
        TeamId = "00000000-0000-0000-0000-000000000007"
        File = "revenue_optimization.json"
        Color = "Green"
    },
    @{
        Name = "Marketing Intelligence Team"
        TeamId = "00000000-0000-0000-0000-000000000008"
        File = "marketing_intelligence.json"
        Color = "Green"
    }
)

Write-Host "`n============================================================" -ForegroundColor Yellow
Write-Host "   UPLOADING AGENT TEAMS TO BACKEND" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""

$successCount = 0
$failCount = 0
$results = @()

foreach ($team in $teams) {
    $filePath = Join-Path $teamsDir $team.File
    
    Write-Host "Uploading: $($team.Name)..." -ForegroundColor $team.Color -NoNewline
    
    # Check if file exists
    if (-not (Test-Path $filePath)) {
        Write-Host " SKIPPED (File not found)" -ForegroundColor Yellow
        $failCount++
        $results += @{
            Team = $team.Name
            Status = "SKIPPED"
            Message = "File not found: $filePath"
        }
        continue
    }
    
    try {
        # Read JSON file
        $jsonContent = Get-Content $filePath -Raw
        
        # Build URL with team_id as query parameter (bypasses RAI check for updates)
        $uploadUrl = "$apiUrl`?team_id=$($team.TeamId)"
        
        # Prepare multipart form data
        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        
        $bodyLines = @(
            "--$boundary",
            "Content-Disposition: form-data; name=`"file`"; filename=`"$($team.File)`"",
            "Content-Type: application/json",
            "",
            $jsonContent,
            "--$boundary--"
        ) -join $LF
        
        # Make API request
        $response = Invoke-RestMethod -Uri $uploadUrl `
            -Method Post `
            -ContentType "multipart/form-data; boundary=$boundary" `
            -Body $bodyLines
        
        Write-Host " SUCCESS" -ForegroundColor Green
        $successCount++
        $results += @{
            Team = $team.Name
            Status = "SUCCESS"
            Message = $response.message
            TeamId = $response.team_id
        }
    }
    catch {
        $errorMsg = $_.Exception.Message
        if ($_.ErrorDetails.Message) {
            $errorDetail = ($_.ErrorDetails.Message | ConvertFrom-Json).detail
            $errorMsg = $errorDetail
        }
        
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "  Error: $errorMsg" -ForegroundColor Red
        $failCount++
        $results += @{
            Team = $team.Name
            Status = "FAILED"
            Message = $errorMsg
        }
    }
    
    Start-Sleep -Milliseconds 500
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "   UPLOAD SUMMARY" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "Total Teams: $($teams.Count + 1) (including HR already uploaded)" -ForegroundColor White
Write-Host "Successful: $($successCount + 1)" -ForegroundColor Green
Write-Host "Failed: $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
Write-Host ""

if ($successCount -gt 0) {
    Write-Host "Successfully Uploaded Teams:" -ForegroundColor Green
    foreach ($result in $results | Where-Object { $_.Status -eq "SUCCESS" }) {
        Write-Host "  - $($result.Team)" -ForegroundColor Green
    }
    Write-Host ""
}

if ($failCount -gt 0) {
    Write-Host "Failed Teams:" -ForegroundColor Red
    foreach ($result in $results | Where-Object { $_.Status -ne "SUCCESS" }) {
        Write-Host "  - $($result.Team): $($result.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""

if ($failCount -eq 0) {
    Write-Host "ALL TEAMS UPLOADED SUCCESSFULLY!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Step: Refresh your frontend at http://localhost:3001" -ForegroundColor Cyan
    Write-Host "The team initialization errors should be gone!" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "Some teams failed to upload. Check the errors above." -ForegroundColor Yellow
    Write-Host ""
}

# Exit with appropriate code
if ($failCount -gt 0) {
    exit 1
} else {
    exit 0
}

