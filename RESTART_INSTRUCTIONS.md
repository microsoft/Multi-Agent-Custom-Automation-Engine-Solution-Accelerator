# 🔄 Restart Instructions - MCP Connection Fix

## ✅ **What Was Fixed**

1. **MCP Configuration**: Made `AZURE_TENANT_ID` and `AZURE_CLIENT_ID` optional in `MCPConfig`
2. **Better Logging**: Added detailed logs to track MCP plugin initialization
3. **Error Handling**: Improved error messages when MCP connection fails

---

## 🚀 **How to Restart Everything**

### **Step 1: Stop All Services**

In each terminal window, press `Ctrl+C` to stop:
- ✋ Backend server
- ✋ MCP server  
- ✋ Frontend server (if needed)

### **Step 2: Start MCP Server FIRST**

```powershell
# Terminal 1: MCP Server
powershell -ExecutionPolicy Bypass -File scripts/start-mcp-server.ps1
```

**Wait for**: `✓ Server running on http://localhost:8001`

### **Step 3: Start Backend Server**

```powershell
# Terminal 2: Backend
powershell -ExecutionPolicy Bypass -File scripts/start-backend-with-az.ps1
```

**Look for these log messages**:
```
✅ GOOD SIGNS:
INFO:mcp_init:Initializing MCP plugin: name=MACAE MCP Server, url=http://localhost:8001
INFO:mcp_init:✅ MCP plugin initialized successfully: MACAE MCP Server
INFO:FoundryAgentTemplate:✅ Agent 'FinancialStrategistAgent' has MCP plugin: MACAE MCP Server
INFO:FoundryAgentTemplate:✅ Agent 'FinancialStrategistAgent' initialized with MCP tools enabled

❌ BAD SIGNS:
ERROR:mcp_init:❌ Failed to initialize MCP plugin: ...
WARNING:FoundryAgentTemplate:⚠️ Agent 'FinancialStrategistAgent' has NO MCP plugin
```

### **Step 4: Refresh Frontend**

```powershell
# If frontend is running, just refresh browser
# Press: Ctrl+Shift+R

# If frontend is NOT running:
cd src/frontend
npm run dev
```

---

## 🧪 **Test the Fix**

### **Quick Test**

1. Go to `http://localhost:3001`
2. Select **"Financial Forecasting Team"**
3. Enter: **"Use our latest sales dataset to project revenue for the next quarter"**
4. Click **"Create Plan"**

### **Expected Behavior** ✅

**Agent Response Timeline:**
1. **0-5 seconds**: Plan approval request
2. **5-10 seconds**: Agent starts working (NO clarification about dataset location)
3. **10-30 seconds**: Agent returns forecast with confidence intervals

**Backend Logs Should Show:**
```
INFO: MCP tool called: list_finance_datasets
INFO: MCP tool result: {"datasets": [{"dataset_id": "b89604c5-7994-463e-ac00-39c79c33ca20", ...}]}
INFO: MCP tool called: summarize_financial_dataset
INFO: MCP tool called: generate_financial_forecast
```

### **Bad Behavior** ❌

If you see:
- Agent asks: "Please provide access to the sales dataset..."
- Agent asks: "Which dataset should I use?"
- Agent asks: "Please retrieve the dataset and provide its contents..."
- **NO MCP tool logs** in backend

**Then**: MCP connection failed. See troubleshooting below.

---

## 🔍 **Troubleshooting**

### **Problem**: Backend logs show "❌ Failed to initialize MCP plugin"

**Diagnosis**:
```powershell
# Test MCP server health
curl http://localhost:8001/health
```

**If this fails**:
- MCP server is not running
- MCP server is on wrong port
- Firewall is blocking connection

**Solution**:
1. Verify MCP server is running: Check Terminal 1
2. Check MCP server logs for errors
3. Restart MCP server: `powershell -ExecutionPolicy Bypass -File scripts/start-mcp-server.ps1`

### **Problem**: Backend logs show "⚠️ Agent has NO MCP plugin"

**Diagnosis**:
```powershell
# Check MCP environment variables
Get-Content src\backend\.env | Select-String -Pattern "MCP_SERVER"
```

**Expected Output**:
```
MCP_SERVER_ENDPOINT=http://localhost:8001
MCP_SERVER_NAME=MACAE MCP Server
MCP_SERVER_DESCRIPTION=Multi-Agent Custom Automation Engine MCP Tools
```

**If any are missing**:
1. Add them to `src/backend/.env`
2. Restart backend

### **Problem**: Agents still ask for clarification

**Check**: Do backend logs show MCP tool calls?

**If NO**:
1. Verify `use_mcp: true` in team JSON files
2. Re-upload team configurations via frontend
3. Refresh frontend with `Ctrl+Shift+R`
4. Try creating a **new** plan (old plans may be cached)

**If YES** (MCP tools are being called):
- This is expected! Some clarification is normal (e.g., fiscal calendar)
- As long as agents DON'T ask about "dataset location" or "provide the dataset", they're working correctly

---

## 📊 **Verify MCP Tools Are Available**

### **Method 1: Check Uploaded Datasets**

```powershell
python scripts/list_uploaded_datasets.py
```

**Expected**: List of uploaded datasets with their IDs

### **Method 2: Check Backend Logs**

Look for these patterns when agent executes:

```
✅ WORKING:
INFO:mcp_init:✅ MCP plugin initialized successfully
INFO:FoundryAgentTemplate:✅ Agent 'FinancialStrategistAgent' has MCP plugin
INFO:semantic_kernel:MCP tool called: list_finance_datasets
INFO:semantic_kernel:MCP tool result: {"datasets": [...]}

❌ NOT WORKING:
WARNING:FoundryAgentTemplate:⚠️ Agent has NO MCP plugin
(No MCP tool logs appear)
```

### **Method 3: Test MCP Server Directly**

```powershell
# List available MCP tools
curl http://localhost:8001/tools | ConvertFrom-Json | Select-Object -ExpandProperty tools | Select-Object name, description
```

**Expected Output**: List of 15+ tools including:
- `list_finance_datasets`
- `summarize_financial_dataset`
- `generate_financial_forecast`
- `analyze_customer_churn`
- `forecast_delivery_performance`
- etc.

---

## ✅ **Success Criteria**

After restart, you should have:

1. ✅ MCP server running on port 8001
2. ✅ Backend logs show "✅ MCP plugin initialized successfully"
3. ✅ Agent logs show "✅ Agent initialized with MCP tools enabled"
4. ✅ When testing, agents call MCP tools (visible in logs)
5. ✅ Agents DON'T ask about "dataset location" or "provide dataset contents"
6. ✅ Agents may ask about fiscal calendar (this is OK!)

---

## 📝 **Summary of Changes**

| File | Change | Reason |
|------|--------|--------|
| `src/backend/v3/magentic_agents/models/agent_models.py` | Made `tenant_id` and `client_id` optional in `MCPConfig` | Allow MCP to work without Azure AD auth |
| `src/backend/v3/magentic_agents/common/lifecycle.py` | Added detailed logging for MCP initialization | Better debugging of connection issues |
| `src/backend/v3/magentic_agents/foundry_agent.py` | Added logging when agents get MCP plugin | Verify agents have access to MCP tools |

---

## 🎯 **Quick Reference**

```powershell
# 1. Start MCP Server
powershell -ExecutionPolicy Bypass -File scripts/start-mcp-server.ps1

# 2. Start Backend
powershell -ExecutionPolicy Bypass -File scripts/start-backend-with-az.ps1

# 3. Verify MCP Connection
curl http://localhost:8001/health

# 4. Check Datasets
python scripts/list_uploaded_datasets.py

# 5. Test Frontend
# Go to http://localhost:3001
# Select "Financial Forecasting Team"
# Enter: "Use our latest sales dataset to project revenue"
```

---

**Last Updated**: 2025-10-13  
**Issue**: MCP Connection Fix  
**Status**: ✅ READY TO RESTART













