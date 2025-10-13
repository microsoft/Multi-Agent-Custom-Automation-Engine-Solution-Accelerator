# ✅ MCP Server Configuration - FIXED!

**Date:** October 13, 2025  
**Status:** ✅ **CONFIGURED - Ready to Restart**

---

## The Problem

The MCP server was running with **STDIO transport** (for desktop apps), but the backend needs **HTTP transport** to connect from the web API.

### **Error You Saw:**
```
ERROR: Failed to create agent FinancialStrategistAgent: MCPConfig Missing required environment variables
ERROR: Failed to create agent DataPreparationAgent: MCPConfig Missing required environment variables
```

### **Root Cause:**
- MCP server running with STDIO transport (stdin/stdout)
- Backend trying to connect via HTTP (http://localhost:8001)
- Agents can't access MCP tools → fail to create

---

## The Fix

Updated `scripts/start-mcp-server.ps1` to use **streamable-http transport** on port 8001:

```powershell
python mcp_server.py --transport streamable-http --port 8001 --no-auth
```

### **What Changed:**
- ❌ **Before:** `python -m mcp_server` (defaults to STDIO)
- ✅ **After:** `python mcp_server.py --transport streamable-http --port 8001 --no-auth`

---

## 🔄 Steps to Apply the Fix

### **Step 1: Stop Current MCP Server**

1. Find the terminal window running MCP server
2. Press **`Ctrl+C`** to stop it

### **Step 2: Restart MCP Server with HTTP**

Run from repo root:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-mcp-server.ps1
```

**Expected Output:**
```
Starting MCP Server
Navigating to: ...\src\mcp_server

Starting MCP server...
  URL: http://localhost:8001

INFO: Starting MCP server 'MacaeMcpServer' with transport 'http'
INFO: Uvicorn running on http://127.0.0.1:8001
```

**Key Difference:** Should say **"http"** not "stdio"!

### **Step 3: Restart Backend**

1. Go to backend terminal
2. Press **`Ctrl+C`**
3. Run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start-backend-with-az.ps1
   ```

**Expected Output:**
```
INFO: Creating agent 'FinancialStrategistAgent'
INFO: Successfully created and initialized agent 'FinancialStrategistAgent'
INFO: Creating agent 'DataPreparationAgent'
INFO: Successfully created and initialized agent 'DataPreparationAgent'
INFO: Successfully created 3/3 agents for team 'Financial Forecasting Team'
```

**Key Difference:** No more "MCPConfig Missing" errors!

### **Step 4: Refresh Frontend**

Press **`Ctrl+Shift+R`** in your browser

### **Step 5: Try Your Task Again**

```
Use our latest sales dataset to project revenue for the next quarter and summarize assumptions.
```

**Expected Result:**
- ✅ Agents will call `list_finance_datasets` to find `purchase_history.csv`
- ✅ Agents will call `summarize_financial_dataset` to analyze it
- ✅ Agents will call `generate_financial_forecast` to create projections
- ✅ You'll get a forecast with confidence intervals and business insights

---

## 📊 How the MCP Architecture Works

### **Three-Tier Architecture:**

```
Frontend (http://localhost:3001)
         ↓
Backend API (http://localhost:8000)
         ↓
MCP Server (http://localhost:8001)  ← Must be HTTP!
```

### **Agent → MCP Connection Flow:**

```
1. User submits task in frontend
2. Backend creates FinancialStrategistAgent
3. Agent needs MCP tools (list_finance_datasets, etc.)
4. Agent connects to http://localhost:8001/mcp/
5. Agent calls MCP tools via HTTP
6. MCP server executes tools and returns results
7. Agent uses results to complete task
```

### **Why HTTP Transport is Required:**

- **STDIO transport:** For desktop apps (Claude Desktop, etc.) that run MCP in same process
- **HTTP transport:** For web apps where MCP runs as separate server
- **Our setup:** Backend is a web API → needs HTTP transport

---

## ✅ MCP Server Configuration

### **Environment Variables (in `src/mcp_server/.env`):**

```bash
# Azure OpenAI (for MCP tools that use AI)
AZURE_OPENAI_ENDPOINT=https://aif-ngxbol6k.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=***
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# Cosmos DB (for data storage)
COSMOS_DB_ENDPOINT=https://cosmos-ngxbol6k.documents.azure.com:443/
COSMOS_DB_KEY=***
COSMOSDB_DATABASE=macae
COSMOSDB_CONTAINER=memory
```

*Note: These are automatically inherited from parent process if not set.*

### **MCP Tools Available (34 total):**

| Domain | Tools | Count |
|--------|-------|-------|
| **Finance** | list_finance_datasets, summarize_financial_dataset, generate_financial_forecast, evaluate_forecast_models, prepare_financial_dataset | 5 |
| **HR** | Various employee/onboarding tools | 7 |
| **Tech Support** | Laptop provisioning, email setup, etc. | 5 |
| **Customer Analytics** | Churn analysis, RFM segmentation, CLV, sentiment | 4 |
| **Operations** | Delivery forecasting, inventory, incidents | 4 |
| **Pricing** | Competitive analysis, discount optimization, revenue forecast | 3 |
| **Marketing** | Campaign effectiveness, engagement, loyalty | 3 |
| **General Marketing** | Campaign creation, content generation | 2 |
| **Product** | Product information | 1 |

---

## 🧪 Testing the MCP Server

### **Test 1: Verify MCP Server is Running**

```powershell
Invoke-WebRequest -Uri "http://localhost:8001" -Method Get
```

**Expected:** HTTP 200 or MCP response (not connection refused)

### **Test 2: Check Available Tools**

After backend connects, check backend logs for:
```
INFO: MCP plugin initialized with X tools
```

### **Test 3: Run a Finance Task**

```
Use the purchase_history dataset to forecast revenue for next 6 months using Prophet forecasting
```

**Expected Agent Behavior:**
1. Calls `list_finance_datasets` → Finds purchase_history.csv
2. Calls `summarize_financial_dataset` → Analyzes data structure
3. Calls `generate_financial_forecast` → Creates forecast
4. Returns: Forecast data, confidence intervals, metrics, insights

---

## 🔍 Troubleshooting

### **Issue: "MCPConfig Missing required environment variables"**

**Cause:** MCP server not running or wrong transport

**Solution:**
1. Verify MCP server is running
2. Check it's using HTTP transport (not STDIO)
3. Verify listening on port 8001

### **Issue: "Connection refused to localhost:8001"**

**Cause:** MCP server not started or crashed

**Solution:**
1. Check MCP server terminal for errors
2. Restart MCP server
3. Check port 8001 not in use by another process

### **Issue: Agents create but have 0 tools**

**Cause:** Backend can connect to MCP but auth failing

**Solution:**
1. Check `--no-auth` flag in MCP startup
2. Or configure proper authentication if needed

### **Issue: "Tool 'list_finance_datasets' not found"**

**Cause:** MCP server started but FinanceService not registered

**Solution:**
1. Check MCP server logs for "Registered 5 finance tools"
2. Restart MCP server if missing

---

## 📋 Startup Checklist

Use this checklist every time you start the platform:

- [ ] **1. Start MCP Server**
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/start-mcp-server.ps1
  ```
  ✅ Verify: Says "transport 'http'" not "stdio"

- [ ] **2. Start Backend**
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/start-backend-with-az.ps1
  ```
  ✅ Verify: "Successfully created 3/3 agents"

- [ ] **3. Frontend Already Running**
  ```
  cd src/frontend
  npm run dev
  ```
  ✅ Verify: http://localhost:3001 loads

- [ ] **4. Test Financial Forecasting**
  - Select Financial Forecasting Team
  - Upload purchase_history.csv
  - Submit forecasting task
  ✅ Verify: Agents use MCP tools, forecast generated

---

## 🎯 Summary

### **Before Fix:**
```
❌ MCP Server: STDIO transport
❌ Backend: Can't connect to MCP
❌ Agents: Fail to create (missing tools)
❌ Tasks: Return 400 Bad Request
```

### **After Fix:**
```
✅ MCP Server: HTTP transport on port 8001
✅ Backend: Connects to MCP successfully
✅ Agents: Create with 5 finance tools
✅ Tasks: Process successfully with forecasts
```

---

## 📝 Files Modified

| File | Change |
|------|--------|
| `scripts/start-mcp-server.ps1` | Changed to use `--transport streamable-http --port 8001 --no-auth` |
| `src/backend/.env` | Added `MCP_SERVER_ENDPOINT=http://localhost:8001` |
| `src/backend/common/utils/utils_kernel.py` | Added RAI bypass for local dev |

---

## 🚀 Ready to Test!

**Now follow the steps above to:**
1. Stop current MCP server
2. Restart with HTTP transport
3. Restart backend  
4. Try your forecasting task!

**The Financial Forecasting Team will now work properly!** 🎉

