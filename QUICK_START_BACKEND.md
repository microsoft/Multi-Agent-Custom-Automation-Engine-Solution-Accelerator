# 🚀 Quick Start: Backend Server

**Last Updated:** October 13, 2025

---

## Prerequisites

✅ Python 3.10+ installed  
✅ Azure CLI installed and logged in (`az login`)  
✅ Environment variables configured in `src/backend/.env`

---

## Option 1: Automated Startup (Easiest)

### PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-backend.ps1
```

### Windows Command Prompt
```cmd
scripts\start-backend.bat
```

---

## Option 2: Manual Startup

### Step 1: Navigate to Backend Directory
```powershell
cd src\backend
```

### Step 2: Start the Server
```powershell
uvicorn app_kernel:app --reload --port 8000
```

### Step 3: Wait for Startup Message
```
INFO:     Application startup complete.
```

---

## Verify Backend is Running

### Check Health Endpoint
Open in browser or use curl:
```
http://localhost:8000/api/v3/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-13T15:30:00Z"
}
```

### Open API Documentation
```
http://localhost:8000/docs
```

You should see the interactive Swagger UI with all API endpoints.

---

## Common Startup Errors

### Error: "uvicorn: command not found"

**Solution:** Install uvicorn
```powershell
pip install uvicorn
```

### Error: "No module named 'fastapi'"

**Solution:** Install dependencies
```powershell
cd src\backend
pip install -r requirements.txt
```

### Error: "Environment variable APPLICATIONINSIGHTS_CONNECTION_STRING not found"

**Solution:** Create `.env` file in `src/backend/` with required variables:
```bash
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=00000000-0000-0000-0000-000000000000
AZURE_OPENAI_ENDPOINT=https://aif-ngxbol6k.cognitiveservices.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
# ... (see src/backend/.env for full config)
```

### Error: "Port 8000 is already in use"

**Solution:** Kill existing process on port 8000
```powershell
# Find process
netstat -ano | findstr :8000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

Or use a different port:
```powershell
uvicorn app_kernel:app --reload --port 8001
```

### Error: "Unable to acquire Azure credentials"

**Solution:** Login to Azure CLI
```powershell
az login
az account set --subscription efd2b969-bf42-4a11-9aca-57e2716d044a
```

---

## After Backend Starts

### 1. Upload Agent Teams

Run the automated upload script:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/upload_all_teams.ps1
```

**Expected Output:**
```
Uploading: Marketing Team... SUCCESS
Uploading: Retail Team... SUCCESS
Uploading: Finance Forecasting Team... SUCCESS
...
```

### 2. Start Frontend

In a **new terminal**:
```powershell
cd src\frontend
npm run dev
```

Access at: http://localhost:3001

### 3. Start MCP Server (Optional)

In another **new terminal**:
```powershell
cd src\mcp_server
python -m mcp_server
```

---

## Backend URLs Quick Reference

| Service | URL | Purpose |
|---------|-----|---------|
| Health Check | http://localhost:8000/api/v3/health | Verify backend is running |
| API Docs (Swagger) | http://localhost:8000/docs | Interactive API documentation |
| ReDoc | http://localhost:8000/redoc | Alternative API docs |
| Upload Team Config | http://localhost:8000/api/v3/upload_team_config | Upload agent team configurations |
| Analytics KPIs | http://localhost:8000/api/v3/analytics/kpis | Get KPI dashboard data |
| Dataset Upload | http://localhost:8000/api/v3/datasets/upload | Upload CSV/Excel datasets |

---

## Stopping the Backend

**In the terminal running uvicorn:**
1. Press `Ctrl+C`
2. Wait for "Shutting down" message
3. Terminal will return to prompt

---

## Development Tips

### Auto-Reload
The `--reload` flag automatically restarts the server when you edit Python files.

### Logs
Backend logs appear in the terminal. Look for:
- `INFO` - Normal operations
- `WARNING` - Potential issues
- `ERROR` - Actual errors (investigate these!)

### Debugging
To enable more verbose logging, edit `src/backend/.env`:
```bash
LOG_LEVEL=DEBUG
```

Then restart the backend.

---

## Full Platform Startup Order

For the complete platform, start services in this order:

1. **Backend** (port 8000) - Core API server
2. **Upload Teams** - Load agent configurations
3. **MCP Server** (port 8001) - MCP tools [Optional]
4. **Frontend** (port 3001) - User interface

---

## Next Steps After Backend is Running

1. ✅ Upload agent teams (see above)
2. ✅ Verify at http://localhost:8000/docs
3. ✅ Start frontend server
4. ✅ Open http://localhost:3001 and test!

---

**Need Help?**
- Check backend terminal logs for errors
- Verify `.env` file exists and has correct values
- Ensure Azure CLI is logged in (`az account show`)
- Check `RAI_CONFIGURATION_COMPLETE.md` for RAI setup details

