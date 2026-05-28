#Requires -Version 7.0
<#
.SYNOPSIS
    Interactive post-deployment data seeding script.
    Seeds Cosmos DB (teams), uploads blob data, creates search indexes,
    creates vector stores, and provisions Foundry IQ knowledge bases.

.DESCRIPTION
    Run after 'azd up' completes. Pulls configuration from azd environment
    outputs. Presents an interactive menu to select which use cases to install.
    Writes teams directly to Cosmos DB (no running backend required).

.PARAMETER ResourceGroup
    Optional resource group name. If omitted, values come from azd env.

.EXAMPLE
    .\infra\scripts\post_deploy_data.ps1
    .\infra\scripts\post_deploy_data.ps1 -ResourceGroup rg-macae-dev
#>

param(
    [string]$ResourceGroup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$script:hasErrors = $false

# ──────────────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────────────

function Test-AzdInstalled {
    try { $null = Get-Command azd -ErrorAction Stop; return $true } catch { return $false }
}

function Get-AzdValue([string]$Key) {
    $val = $(azd env get-value $Key 2>$null)
    if (-not $val) {
        Write-Host "ERROR: Could not get '$Key' from azd env. Run 'azd up' first." -ForegroundColor Red
        exit 1
    }
    return $val.Trim()
}

function Deploy-ContentPack {
    param(
        [string]$PackPath,
        [string]$StorageAccountName,
        [string]$AiSearchName,
        [string]$PythonCmd
    )

    $packJsonPath = Join-Path $PackPath "pack.json"
    if (-not (Test-Path $packJsonPath)) {
        Write-Host "  No pack.json found at $packJsonPath - skipping data deployment."
        return $true
    }

    $pack = Get-Content $packJsonPath -Raw | ConvertFrom-Json
    Write-Host "  Deploying data for content pack: $($pack.name)"
    $hadFailure = $false

    # blob_indexes: upload + create search index
    if ($pack.PSObject.Properties['blob_indexes'] -and $pack.blob_indexes) {
        foreach ($entry in $pack.blob_indexes) {
            $container = $entry.container
            $sourcePath = Join-Path $PackPath $entry.source
            $pattern = if ($entry.pattern) { $entry.pattern } else { "*" }
            $indexName = $entry.index_name

            if (-not (Test-Path $sourcePath)) {
                Write-Host "  Warning: source directory not found: $sourcePath. Skipping."
                $hadFailure = $true
                continue
            }

            az storage container create --account-name $StorageAccountName --name $container --auth-mode login --output none 2>$null
            Write-Host "  Uploading blobs to container '$container'..."
            az storage blob upload-batch --account-name $StorageAccountName --destination $container --source $sourcePath --auth-mode login --pattern $pattern --overwrite --output none
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  Error: Failed to upload blobs to container '$container'."
                $hadFailure = $true
                continue
            }

            Write-Host "  Creating search index '$indexName' from container '$container'..."
            $process = Start-Process -FilePath $PythonCmd -ArgumentList "infra/scripts/index_datasets.py", $StorageAccountName, $container, $AiSearchName, $indexName -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Host "  Error: Indexing failed for '$indexName'."
                $hadFailure = $true
            }
        }
    }

    # blob_uploads: upload only
    if ($pack.PSObject.Properties['blob_uploads'] -and $pack.blob_uploads) {
        foreach ($entry in $pack.blob_uploads) {
            $container = $entry.container
            $sourcePath = Join-Path $PackPath $entry.source
            $pattern = if ($entry.pattern) { $entry.pattern } else { "*" }

            if (-not (Test-Path $sourcePath)) {
                Write-Host "  Warning: source directory not found: $sourcePath. Skipping."
                $hadFailure = $true
                continue
            }

            az storage container create --account-name $StorageAccountName --name $container --auth-mode login --output none 2>$null
            Write-Host "  Uploading blobs to container '$container'..."
            az storage blob upload-batch --account-name $StorageAccountName --destination $container --source $sourcePath --auth-mode login --pattern $pattern --overwrite --output none
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  Error: Failed to upload blobs to container '$container'."
                $hadFailure = $true
            }
        }
    }

    # search_indexes: create index from already-uploaded data
    if ($pack.PSObject.Properties['search_indexes'] -and $pack.search_indexes) {
        foreach ($entry in $pack.search_indexes) {
            $indexName = $entry.index_name
            $container = $null
            if ($pack.PSObject.Properties['blob_uploads'] -and $pack.blob_uploads.Count -gt 0) {
                $container = $pack.blob_uploads[0].container
            }
            if (-not $container) {
                Write-Host "  Warning: No blob container found for search_index '$indexName'. Skipping."
                continue
            }

            Write-Host "  Creating search index '$indexName' from container '$container'..."
            $process = Start-Process -FilePath $PythonCmd -ArgumentList "infra/scripts/index_datasets.py", $StorageAccountName, $container, $AiSearchName, $indexName -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0) {
                Write-Host "  Error: Indexing failed for '$indexName'."
                $hadFailure = $true
            }
        }
    }

    return (-not $hadFailure)
}

# ──────────────────────────────────────────────────────────────────────────────
# 1. Authenticate & resolve environment values
# ──────────────────────────────────────────────────────────────────────────────

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Post-Deployment Data Seeding" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Verify Azure CLI login
try {
    $null = az account show 2>$null
    Write-Host "Already authenticated with Azure."
} catch {
    Write-Host "Not authenticated. Logging in..."
    az login
}

if (-not (Test-AzdInstalled)) {
    Write-Host "ERROR: Azure Developer CLI (azd) is required. Install from https://aka.ms/azd" -ForegroundColor Red
    exit 1
}

$cosmosEndpoint  = Get-AzdValue "COSMOSDB_ENDPOINT"
$cosmosDatabase  = Get-AzdValue "COSMOSDB_DATABASE"
$cosmosContainer = Get-AzdValue "COSMOSDB_CONTAINER"
$storageAccount  = Get-AzdValue "AZURE_STORAGE_ACCOUNT_NAME"
$aiSearchName    = Get-AzdValue "AZURE_AI_SEARCH_NAME"
$searchEndpoint  = Get-AzdValue "AZURE_SEARCH_ENDPOINT"
$openaiEndpoint  = Get-AzdValue "AZURE_OPENAI_ENDPOINT"
$projectEndpoint = Get-AzdValue "AZURE_AI_PROJECT_ENDPOINT"

if (-not $ResourceGroup) {
    $ResourceGroup = $(azd env get-value AZURE_RESOURCE_GROUP 2>$null)
}

Write-Host ""
Write-Host "Cosmos DB:       $cosmosEndpoint"
Write-Host "Database:        $cosmosDatabase"
Write-Host "Storage:         $storageAccount"
Write-Host "AI Search:       $aiSearchName"
Write-Host "OpenAI:          $openaiEndpoint"
Write-Host "AI Project:      $projectEndpoint"
Write-Host "Resource Group:  $ResourceGroup"
Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# 2. Interactive use case selection
# ──────────────────────────────────────────────────────────────────────────────

Write-Host "==============================================="
Write-Host "Available Use Cases:"
Write-Host "==============================================="
Write-Host "1. RFP Evaluation"
Write-Host "2. Retail Customer Satisfaction"
Write-Host "3. HR Employee Onboarding"
Write-Host "4. Marketing Press Release"
Write-Host "5. Contract Compliance Review"
Write-Host "6. Content Generation"
Write-Host "7. All"
Write-Host "==============================================="
Write-Host ""

do {
    $useCaseSelection = Read-Host "Enter the number of the use case to install (1-7)"

    if ($useCaseSelection -eq "all" -or $useCaseSelection -eq "7") {
        $selectedUseCase = "All"
        $useCaseValid = $true
        Write-Host "Selected: All use cases will be installed."
    }
    elseif ($useCaseSelection -in @("1","2","3","4","5","6")) {
        $useCaseNames = @{
            "1" = "RFP Evaluation"
            "2" = "Retail Customer Satisfaction"
            "3" = "HR Employee Onboarding"
            "4" = "Marketing Press Release"
            "5" = "Contract Compliance Review"
            "6" = "Content Generation"
        }
        $selectedUseCase = $useCaseNames[$useCaseSelection]
        $useCaseValid = $true
        Write-Host "Selected: $selectedUseCase"
    }
    else {
        $useCaseValid = $false
        Write-Host "Invalid selection. Please enter a number from 1-7." -ForegroundColor Red
    }
} while (-not $useCaseValid)

Write-Host ""

# ──────────────────────────────────────────────────────────────────────────────
# 3. Set up Python environment
# ──────────────────────────────────────────────────────────────────────────────

$pythonCmd = $null
try { $v = (python --version 2>&1); if ($v -match "Python \d") { $pythonCmd = "python" } } catch {}
if (-not $pythonCmd) {
    try { $v = (python3 --version 2>&1); if ($v -match "Python \d") { $pythonCmd = "python3" } } catch {}
}
if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found. Install Python 3.10+ and add to PATH." -ForegroundColor Red
    exit 1
}

$venvPath = "infra/scripts/scriptenv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..."
    & $pythonCmd -m venv $venvPath
}

$activateScript = if (Test-Path "$venvPath/Scripts/Activate.ps1") { "$venvPath/Scripts/Activate.ps1" }
                  elseif (Test-Path "$venvPath/bin/Activate.ps1") { "$venvPath/bin/Activate.ps1" }
                  else { $null }
if ($activateScript) { . $activateScript }

Write-Host "Installing Python dependencies..."
pip install --quiet -r infra/scripts/requirements.txt
pip install --quiet azure-cosmos httpx aiohttp

# ──────────────────────────────────────────────────────────────────────────────
# 4. Ensure src/backend/.env has required values for seed scripts
# ──────────────────────────────────────────────────────────────────────────────

$envFile = "src/backend/.env"
$envPairs = @{
    "COSMOSDB_ENDPOINT"        = $cosmosEndpoint
    "COSMOSDB_DATABASE"        = $cosmosDatabase
    "COSMOSDB_CONTAINER"       = $cosmosContainer
    "AZURE_STORAGE_ACCOUNT_NAME" = $storageAccount
    "AZURE_AI_SEARCH_ENDPOINT" = $searchEndpoint
    "AZURE_OPENAI_ENDPOINT"    = $openaiEndpoint
    "AZURE_AI_PROJECT_ENDPOINT" = $projectEndpoint
}

if (Test-Path $envFile) {
    $existing = Get-Content $envFile -Raw
    foreach ($key in $envPairs.Keys) {
        if ($existing -notmatch "(?m)^$key=") {
            Add-Content -Path $envFile -Value "$key=$($envPairs[$key])"
        }
    }
} else {
    $lines = $envPairs.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
    Set-Content -Path $envFile -Value ($lines -join "`n")
}

# ──────────────────────────────────────────────────────────────────────────────
# 5. Seed Cosmos DB with team configs (direct write — no backend needed)
# ──────────────────────────────────────────────────────────────────────────────

# Map use case selections to content pack team directories
$teamPackMap = @{
    "1" = @("content_packs/rfp_evaluation/agent_teams")
    "2" = @("content_packs/retail_customer/agent_teams")
    "3" = @("content_packs/hr_onboarding/agent_teams")
    "4" = @("content_packs/marketing_press_release/agent_teams")
    "5" = @("content_packs/contract_compliance/agent_teams")
    "6" = @("content_packs/content_gen/agent_teams")
    "7" = @(
        "content_packs/rfp_evaluation/agent_teams",
        "content_packs/retail_customer/agent_teams",
        "content_packs/hr_onboarding/agent_teams",
        "content_packs/marketing_press_release/agent_teams",
        "content_packs/contract_compliance/agent_teams",
        "content_packs/content_gen/agent_teams"
    )
}

$selectedTeamDirs = $teamPackMap[$useCaseSelection]

Write-Host "`n── Step 1: Seeding Cosmos DB with team configs ──" -ForegroundColor Green

$teamDirsJson = ($selectedTeamDirs | ConvertTo-Json -Compress)

$seedTeamsScript = @"
import asyncio, json, uuid, sys, os
from datetime import datetime, timezone
from pathlib import Path
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

ENDPOINT = os.environ["COSMOSDB_ENDPOINT"]
DATABASE = os.environ["COSMOSDB_DATABASE"]
CONTAINER = os.environ["COSMOSDB_CONTAINER"]
TEAM_DIRS = json.loads(r'''$teamDirsJson''')

async def seed():
    cred = DefaultAzureCredential()
    client = CosmosClient(ENDPOINT, credential=cred)
    db = client.get_database_client(DATABASE)
    container = db.get_container_client(CONTAINER)
    count = 0

    for team_dir in TEAM_DIRS:
        team_path = Path(team_dir)
        if not team_path.exists():
            print(f"  Warning: {team_dir} not found, skipping.")
            continue
        for filepath in sorted(team_path.glob("*.json")):
            with open(filepath, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            unique_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            doc = {
                "id": unique_id,
                "team_id": unique_id,
                "session_id": session_id,
                "data_type": "team_config",
                "name": json_data.get("name", ""),
                "status": json_data.get("status", "active"),
                "created": now,
                "created_by": "system",
                "deployment_name": json_data.get("deployment_name", ""),
                "agents": json_data.get("agents", []),
                "description": json_data.get("description", ""),
                "logo": json_data.get("logo", ""),
                "plan": json_data.get("plan", ""),
                "starting_tasks": json_data.get("starting_tasks", []),
                "user_id": "system",
            }

            query = "SELECT * FROM c WHERE c.data_type = 'team_config' AND c.name = @name"
            params = [{"name": "@name", "value": json_data.get("name", "")}]
            existing = [item async for item in container.query_items(query, parameters=params)]
            if existing:
                doc["id"] = existing[0]["id"]
                doc["team_id"] = existing[0]["team_id"]
                doc["session_id"] = existing[0]["session_id"]

            try:
                await container.upsert_item(body=doc)
                verb = "Updated" if existing else "Created"
                print(f"  {verb}: {json_data.get('name')} ({filepath.name})")
                count += 1
            except Exception as e:
                print(f"  FAILED: {json_data.get('name')}: {str(e)[:120]}")

    await cred.close()
    await client.close()
    print(f"  Done — {count} team(s) seeded.")

asyncio.run(seed())
"@

$env:COSMOSDB_ENDPOINT = $cosmosEndpoint
$env:COSMOSDB_DATABASE = $cosmosDatabase
$env:COSMOSDB_CONTAINER = $cosmosContainer

$seedTeamsScript | & $pythonCmd -
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Team config seeding had errors." -ForegroundColor Red
    $script:hasErrors = $true
}

# ──────────────────────────────────────────────────────────────────────────────
# 6. Deploy blob data and create search indexes
# ──────────────────────────────────────────────────────────────────────────────

# Map use cases to content packs that have data (blob/index operations)
$dataPackMap = @{
    "1" = @("content_packs/rfp_evaluation")
    "2" = @("content_packs/retail_customer")
    "3" = @()  # HR has no datasets
    "4" = @()  # Marketing has no datasets
    "5" = @("content_packs/contract_compliance")
    "6" = @("content_packs/content_gen")
    "7" = @(
        "content_packs/rfp_evaluation",
        "content_packs/retail_customer",
        "content_packs/contract_compliance",
        "content_packs/content_gen"
    )
}

$selectedDataPacks = $dataPackMap[$useCaseSelection]

if ($selectedDataPacks.Count -gt 0) {
    Write-Host "`n── Step 2: Uploading blob data and creating search indexes ──" -ForegroundColor Green

    $isSampleDataFailed = $false
    foreach ($packPath in $selectedDataPacks) {
        $result = Deploy-ContentPack -PackPath $packPath -StorageAccountName $storageAccount -AiSearchName $aiSearchName -PythonCmd $pythonCmd
        if (-not $result) {
            $isSampleDataFailed = $true
            $script:hasErrors = $true
            Write-Host "  Error in data deployment for $packPath" -ForegroundColor Red
        }
    }

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Create vector stores (Foundry file search)
    # ──────────────────────────────────────────────────────────────────────────

    Write-Host "`n── Step 3: Creating vector stores ──" -ForegroundColor Green

    $env:AZURE_AI_PROJECT_ENDPOINT = $projectEndpoint
    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/seed_vector_stores.py" -Wait -NoNewWindow -PassThru
    if ($process.ExitCode -ne 0) {
        Write-Host "  ERROR: Vector store creation failed. Run 'python infra/scripts/seed_vector_stores.py' manually." -ForegroundColor Red
        $script:hasErrors = $true
    } else {
        Write-Host "  Vector stores created successfully."
    }

    # ──────────────────────────────────────────────────────────────────────────
    # 8. Create Foundry IQ Knowledge Bases
    # ──────────────────────────────────────────────────────────────────────────

    Write-Host "`n── Step 4: Seeding Foundry IQ Knowledge Bases ──" -ForegroundColor Green

    $env:AZURE_AI_SEARCH_ENDPOINT = $searchEndpoint
    $env:AZURE_OPENAI_ENDPOINT = $openaiEndpoint
    $process = Start-Process -FilePath $pythonCmd -ArgumentList "infra/scripts/seed_knowledge_bases.py" -Wait -NoNewWindow -PassThru
    if ($process.ExitCode -ne 0) {
        Write-Host "  ERROR: Knowledge base seeding failed. Run 'python infra/scripts/seed_knowledge_bases.py' manually." -ForegroundColor Red
        $script:hasErrors = $true
    } else {
        Write-Host "  Knowledge bases seeded successfully."
    }
} else {
    Write-Host "`n  Selected use case has no datasets to deploy — skipping blob/index/KB steps."
}

# ──────────────────────────────────────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────────────────────────────────────

if ($script:hasErrors) {
    Write-Host "`n========================================" -ForegroundColor Red
    Write-Host " Post-deployment seeding completed with ERRORS" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "`nOne or more steps failed. Review the output above and re-run the failed steps manually." -ForegroundColor Yellow
    $frontendHost = $(azd env get-value webSiteDefaultHostname 2>$null)
    if ($frontendHost) {
        Write-Host "Frontend: https://$frontendHost"
    }
    Write-Host ""
    exit 1
} else {
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host " Post-deployment data seeding complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "`nThe application is ready to use."
    $frontendHost = $(azd env get-value webSiteDefaultHostname 2>$null)
    if ($frontendHost) {
        Write-Host "Frontend: https://$frontendHost"
    }
    Write-Host ""
}
