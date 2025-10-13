# Windows Setup Quick Fix Guide

## Issue: "az is not recognized"

Azure CLI is installed but PowerShell can't find it. Here are your options:

---

## ✅ Solution 1: Restart PowerShell (EASIEST)

```powershell
# 1. Close this PowerShell window
# 2. Open a NEW PowerShell window
# 3. Test it works:
az --version
az login
```

This works because the installer updated your PATH, but your current session doesn't have the update yet.

---

## ✅ Solution 2: Use the Helper Script (QUICK)

I created a helper script for you:

```powershell
# Run this once per PowerShell session
.\scripts\az-login.ps1

# Now az commands will work:
az account show
az account list
```

---

## ✅ Solution 3: Add to PATH Permanently

```powershell
# Run PowerShell as Administrator, then:
$azPath = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$azPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$azPath", "Machine")
    Write-Host "✅ Added Azure CLI to PATH permanently"
}

# Restart PowerShell, then test:
az --version
```

---

## ✅ Solution 4: Use Full Path (TEMPORARY)

For this session only:

```powershell
# Create an alias
Set-Alias -Name az -Value "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

# Now use az normally:
az login
az account show
```

---

## 🚀 What to Do Next

### Step 1: Login to Azure

After fixing the PATH issue:

```powershell
# Login (opens browser)
az login

# Verify you're logged in
az account show

# List subscriptions
az account list --output table
```

### Step 2: Get Your Azure Credentials

Now that you're logged in, get the missing credentials:

#### Get Azure OpenAI API Key

```powershell
# List your OpenAI resources
az cognitiveservices account list --resource-group Agents --output table

# Get the key for your resource
az cognitiveservices account keys list `
  --name aif-ngxbol6k `
  --resource-group Agents `
  --output table
```

Copy `Key1` → This is your `AZURE_OPENAI_API_KEY`

#### Get Cosmos DB Credentials

```powershell
# List Cosmos DB accounts
az cosmosdb list --resource-group Agents --output table

# Get keys (replace <cosmos-account-name> with actual name)
az cosmosdb keys list `
  --name <cosmos-account-name> `
  --resource-group Agents `
  --output table
```

Copy:
- `documentEndpoint` → `COSMOS_DB_ENDPOINT`
- `primaryMasterKey` → `COSMOS_DB_KEY`

#### Get Client Secret

```powershell
# List app registrations
az ad app list --display-name "your-app-name" --output table

# Create new secret (if needed)
az ad app credential reset `
  --id efd2b969-bf42-4a11-9aca-57e2716d044a `
  --append
```

Copy the secret value → `AZURE_CLIENT_SECRET`

---

## 📋 Create Your .env File

Once you have all credentials:

```powershell
# Navigate to backend
cd src/backend

# Create .env file
@"
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://aif-ngxbol6k.cognitiveservices.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_API_KEY=<paste-key-here>

# Azure Auth
AZURE_TENANT_ID=2da40318-46be-402c-ba75-cfb1f656567d
AZURE_CLIENT_ID=efd2b969-bf42-4a11-9aca-57e2716d044a
AZURE_CLIENT_SECRET=<paste-secret-here>

# Cosmos DB
COSMOS_DB_ENDPOINT=<paste-endpoint-here>
COSMOS_DB_KEY=<paste-key-here>
COSMOS_DB_DATABASE_NAME=multi-agent-db
COSMOS_DB_CONTAINER_NAME=agents-container

# OR for testing without Cosmos DB:
# USE_IN_MEMORY_DB=true

# Project Config
AZURE_AI_SUBSCRIPTION_ID=efd2b969-bf42-4a11-9aca-57e2716d044a
AZURE_AI_RESOURCE_GROUP=Agents
AZURE_AI_PROJECT_NAME=proj-ngxbol6k
AZURE_AI_AGENT_ENDPOINT=https://aif-ngxbol6k.services.ai.azure.com/

# Application
APP_ENV=NGX
LOG_LEVEL=INFO
MCP_SERVER_ENDPOINT=http://localhost:8001
FRONTEND_SITE_NAME=http://127.0.0.1:3001
SUPPORTED_MODELS=["gpt-4o","gpt-4.1-mini","gpt-4","o1-preview","o3-mini","o3"]
"@ | Out-File -FilePath .env -Encoding utf8
```

---

## 🧪 Test Your Setup

```powershell
# Start the backend
cd src/backend
uvicorn app_kernel:app --reload --port 8000

# In another terminal, test the API
curl http://localhost:8000/api/v3/analytics/health
```

---

## 💡 Alternative: Skip Azure Setup for Now

Want to test the analytics features without all the Azure setup?

```powershell
# Option 1: Run unit tests (no Azure needed)
python scripts/testing/run_sprint1_tests.py
python scripts/testing/run_sprint2_tests.py
python scripts/testing/run_sprint3_tests.py

# Option 2: Use Jupyter notebooks (no backend needed)
pip install jupyter matplotlib seaborn
jupyter notebook examples/notebooks/01_revenue_forecasting.ipynb

# Option 3: Test analytics API with mock data
python scripts/testing/test_analytics_api.py
```

These work **immediately** without any Azure credentials!

---

## 🆘 Still Having Issues?

### PowerShell Execution Policy Error?

```powershell
# Run this as Administrator:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Can't Find Azure Resources?

```powershell
# Make sure you're using the right subscription
az account set --subscription efd2b969-bf42-4a11-9aca-57e2716d044a

# List all resources in the resource group
az resource list --resource-group Agents --output table
```

### Need to Create Resources?

If you don't have Cosmos DB or other resources yet, you can deploy using:

```powershell
# Install Azure Developer CLI
winget install microsoft.azd

# Deploy everything
azd up
```

See `docs/FULL_AZURE_DEPLOYMENT.md` for complete deployment guide.

---

## 📚 Summary

**Immediate fix:**
1. Close and reopen PowerShell OR run `.\scripts\az-login.ps1`
2. Run `az login`
3. Get credentials with the Azure CLI commands above
4. Create `.env` file
5. Start backend: `uvicorn app_kernel:app --reload --port 8000`

**Or skip Azure for now:**
1. Run `python scripts/testing/run_sprint1_tests.py`
2. Run `jupyter notebook examples/notebooks/`
3. Test analytics without backend

Let me know which path you choose! 🚀

