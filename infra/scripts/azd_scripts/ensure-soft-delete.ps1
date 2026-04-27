<#
.SYNOPSIS
    Pre-provision hook: Detects and purges soft-deleted Key Vault and
    Cognitive Services resources that would conflict with deployment.
.DESCRIPTION
    Automatically lists soft-deleted resources matching the expected naming
    pattern, displays them, and offers to purge all, selected ones, or abort.
#>

# Sanitize AZURE_ENV_NAME to match Bicep solutionSuffix logic:
# toLower, strip: - _ . / space *
function Get-SanitizedEnvName {
    param([string]$EnvName)
    $sanitized = $EnvName -replace '[-_./\s*]', ''
    return $sanitized.ToLower()
}

$envName = $env:AZURE_ENV_NAME
if ([string]::IsNullOrWhiteSpace($envName)) {
    Write-Host "WARNING: AZURE_ENV_NAME is not set. Cannot determine resource names." -ForegroundColor Red
    Write-Host "Please ensure you are running this via 'azd provision' or 'azd up'." -ForegroundColor Yellow
    exit 1
}

$sanitizedName = Get-SanitizedEnvName -EnvName $envName

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Yellow
Write-Host " SOFT-DELETE RESOURCE CHECK" -ForegroundColor Green
Write-Host "===============================================================" -ForegroundColor Yellow
Write-Host ""

# Check if user is logged in to Azure CLI
az account show 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "You are not logged in to Azure CLI." -ForegroundColor Red
    Write-Host "Please run 'az login' before deploying." -ForegroundColor Yellow
    exit 1
}

Write-Host "Checking for soft-deleted resources that may conflict with deployment..." -ForegroundColor Cyan
Write-Host ""

# Collect soft-deleted resources into a unified list
$resources = @()

# Check soft-deleted Key Vaults
Write-Host "Checking soft-deleted Key Vaults..." -ForegroundColor White
$kvJson = az keyvault list-deleted --query "[?starts_with(name, 'kv-$sanitizedName')].{name:name, location:properties.location, deletionDate:properties.deletionDate}" -o json 2>&1
if ($LASTEXITCODE -eq 0 -and $kvJson -ne '[]' -and -not [string]::IsNullOrWhiteSpace($kvJson)) {
    $kvList = $kvJson | ConvertFrom-Json
    foreach ($kv in $kvList) {
        $resources += [PSCustomObject]@{
            Index        = 0
            Type         = "Key Vault"
            Name         = $kv.name
            Location     = $kv.location
            ResourceGroup = "-"
            DeletionDate = $kv.deletionDate
        }
    }
}

# Check soft-deleted Cognitive Services accounts
Write-Host "Checking soft-deleted Cognitive Services accounts..." -ForegroundColor White
$csJson = az cognitiveservices account list-deleted --query "[?starts_with(name, 'aif-$sanitizedName')].{name:name, location:location, id:id, deletionDate:properties.deletionDate}" -o json 2>&1
if ($LASTEXITCODE -eq 0 -and $csJson -ne '[]' -and -not [string]::IsNullOrWhiteSpace($csJson)) {
    $csList = $csJson | ConvertFrom-Json
    foreach ($cs in $csList) {
        # Extract resourceGroup from the id path: .../resourceGroups/<RG>/deletedAccounts/...
        $rgName = ""
        if ($cs.id -match '/resourceGroups/([^/]+)/') {
            $rgName = $Matches[1]
        }
        $resources += [PSCustomObject]@{
            Index        = 0
            Type         = "Cognitive Services"
            Name         = $cs.name
            Location     = $cs.location
            ResourceGroup = $rgName
            DeletionDate = $cs.deletionDate
        }
    }
}

Write-Host ""

# No soft-deleted resources found
if ($resources.Count -eq 0) {
    Write-Host "No soft-deleted resources found matching pattern. Proceeding with deployment." -ForegroundColor Green
    Write-Host ""
    exit 0
}

# Assign indices
for ($i = 0; $i -lt $resources.Count; $i++) {
    $resources[$i].Index = $i + 1
}

# Display found resources
Write-Host "Found $($resources.Count) soft-deleted resource(s) that may conflict with deployment:" -ForegroundColor Yellow
Write-Host ""
Write-Host ("{0,-5} {1,-22} {2,-30} {3,-18} {4,-20} {5}" -f "#", "Type", "Name", "Location", "Resource Group", "Deletion Date") -ForegroundColor Cyan
Write-Host ("{0,-5} {1,-22} {2,-30} {3,-18} {4,-20} {5}" -f "---", "----", "----", "--------", "--------------", "-------------")
foreach ($r in $resources) {
    Write-Host ("{0,-5} {1,-22} {2,-30} {3,-18} {4,-20} {5}" -f $r.Index, $r.Type, $r.Name, $r.Location, $r.ResourceGroup, $r.DeletionDate)
}
Write-Host ""
Write-Host "If not purged, deployment may fail with 'FlagMustBeSetForRestore' or" -ForegroundColor Yellow
Write-Host "'CustomDomainInUse' errors." -ForegroundColor Yellow
Write-Host ""

# Prompt user
while ($true) {
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  a             - Purge ALL listed resources" -ForegroundColor White
    Write-Host "  1,2,3,...     - Purge specific resources (comma-separated numbers)" -ForegroundColor White
    Write-Host "  n             - Abort deployment" -ForegroundColor White
    Write-Host ""
    $response = Read-Host "Enter your choice"

    if ($response -eq 'a' -or $response -eq 'A') {
        $selectedResources = $resources
        break
    }
    elseif ($response -eq 'n' -or $response -eq 'N') {
        Write-Host ""
        Write-Host "Deployment aborted. Please purge the soft-deleted resources manually before redeploying." -ForegroundColor Red
        exit 1
    }
    else {
        # Try to parse comma-separated numbers
        $indices = @()
        $valid = $true
        foreach ($part in ($response -split ',')) {
            $trimmed = $part.Trim()
            $num = 0
            if ([int]::TryParse($trimmed, [ref]$num) -and $num -ge 1 -and $num -le $resources.Count) {
                $indices += $num
            }
            else {
                $valid = $false
                break
            }
        }
        if ($valid -and $indices.Count -gt 0) {
            $selectedResources = $resources | Where-Object { $indices -contains $_.Index }
            break
        }
        else {
            Write-Host "Invalid input. Please enter 'a', 'n', or comma-separated numbers (e.g., 1,3)." -ForegroundColor Yellow
        }
    }
}

# Purge selected resources
Write-Host ""
$failed = $false
foreach ($r in $selectedResources) {
    Write-Host "Purging $($r.Type): $($r.Name) (location: $($r.Location))..." -ForegroundColor Cyan

    if ($r.Type -eq "Key Vault") {
        $purgeOutput = az keyvault purge --name $r.Name --location $r.Location 2>&1
    }
    elseif ($r.Type -eq "Cognitive Services") {
        $purgeOutput = az cognitiveservices account purge --name $r.Name --location $r.Location --resource-group $r.ResourceGroup 2>&1
    }

    if ($LASTEXITCODE -ne 0) {
        $outputStr = "$purgeOutput"
        if ($outputStr -match "not allowed|purge protection") {
            Write-Host "  Purge protection is enabled on '$($r.Name)'. Cannot purge." -ForegroundColor Red
            Write-Host "  You must wait for the retention period to expire, or use a different AZURE_ENV_NAME." -ForegroundColor Yellow
        }
        else {
            Write-Host "  Failed to purge $($r.Name). Error: $outputStr" -ForegroundColor Red
        }
        $failed = $true
    }
    else {
        Write-Host "  Successfully purged $($r.Name)." -ForegroundColor Green
    }
}

if ($failed) {
    Write-Host ""
    Write-Host "One or more resources failed to purge. Deployment aborted." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "All selected resources purged successfully. Proceeding with deployment." -ForegroundColor Green
exit 0
