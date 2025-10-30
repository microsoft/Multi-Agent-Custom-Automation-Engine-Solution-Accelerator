# MCP Architecture - How Agents Connect to Tools

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│                    (React on port 3001)                      │
│                                                              │
│  User: "Use our latest sales dataset to project revenue"    │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP Request
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                         BACKEND                              │
│                   (FastAPI on port 8000)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Financial Forecasting Agent Team             │  │
│  │                                                        │  │
│  │  ┌──────────────────────────────────────────────┐    │  │
│  │  │  FinancialStrategistAgent                     │    │  │
│  │  │  - System Message (instructions)              │    │  │
│  │  │  - use_mcp: true  ← CRITICAL                  │    │  │
│  │  │  - MCP Plugin: ✅ CONNECTED                   │    │  │
│  │  └───────────────┬──────────────────────────────┘    │  │
│  │                  │                                     │  │
│  │                  │ Calls MCP Tools:                    │  │
│  │                  │ 1. list_finance_datasets()          │  │
│  │                  │ 2. summarize_financial_dataset()    │  │
│  │                  │ 3. generate_financial_forecast()    │  │
│  │                  │                                     │  │
│  │                  ▼                                     │  │
│  │       ┌──────────────────────────┐                    │  │
│  │       │    MCP Plugin             │                    │  │
│  │       │  (MCPStreamableHttpPlugin)│                    │  │
│  │       │  - name: "MACAE MCP Server"                   │  │
│  │       │  - url: http://localhost:8001                 │  │
│  │       └──────────┬───────────────┘                    │  │
│  └────────────────────┬──────────────────────────────────┘  │
└────────────────────────┼──────────────────────────────────────┘
                         │ HTTP Request to MCP Server
                         │ POST /tools/list_finance_datasets
                         │ POST /tools/generate_financial_forecast
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      MCP SERVER                              │
│              (Streamable-HTTP on port 8001)                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           FinanceService                              │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  list_finance_datasets()                        │  │  │
│  │  │  - Scans: data/uploads/                         │  │  │
│  │  │  - Returns: List of dataset_ids                 │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  summarize_financial_dataset(dataset_id)        │  │  │
│  │  │  - Reads: data/uploads/{user_id}/{dataset_id}/  │  │  │
│  │  │  - Returns: Column names, preview, stats        │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  generate_financial_forecast(dataset_id, ...)   │  │  │
│  │  │  - Calls: advanced_forecasting utilities        │  │  │
│  │  │  - Returns: Forecast + confidence intervals     │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Other Services:                                             │
│  - CustomerAnalyticsService (churn, RFM, CLV)               │
│  - OperationsAnalyticsService (delivery, inventory)          │
│  - PricingAnalyticsService (competitive pricing)             │
│  - MarketingAnalyticsService (campaigns, loyalty)            │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA STORAGE                            │
│                                                              │
│  data/uploads/                                               │
│  └── 00000000-0000-0000-0000-000000000000/                 │
│      └── b89604c5-7994-463e-ac00-39c79c33ca20/             │
│          ├── metadata.json                                   │
│          └── sales_data_sample.csv                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 **Request Flow Example**

### **Scenario**: User asks to forecast revenue

```
1. FRONTEND → BACKEND
   POST /api/v3/create_plan
   {
     "user_request": "Use our latest sales dataset to project revenue",
     "team_id": "fcac7929-c6f1-41b4-b374-645c3cd32f80"
   }

2. BACKEND: Initialize Agent Team
   - Load team config from Cosmos DB
   - Create FinancialStrategistAgent with use_mcp=true
   - Initialize MCP Plugin:
     ✅ MCPConfig.from_env()
     ✅ MCPStreamableHttpPlugin(url="http://localhost:8001")
     ✅ Agent receives MCP plugin

3. AGENT: Execute Task
   Step 1: Agent calls list_finance_datasets()
   
   3a. BACKEND → MCP SERVER
       POST http://localhost:8001/tools/list_finance_datasets
       {}
   
   3b. MCP SERVER → BACKEND
       {
         "datasets": [
           {
             "dataset_id": "b89604c5-7994-463e-ac00-39c79c33ca20",
             "original_filename": "sales_data_sample.csv",
             "numeric_columns": ["SALES", "QUANTITYORDERED"]
           }
         ]
       }
   
   Step 2: Agent matches "sales dataset" → dataset_id
   
   Step 3: Agent calls summarize_financial_dataset(dataset_id)
   
   3c. BACKEND → MCP SERVER
       POST http://localhost:8001/tools/summarize_financial_dataset
       {
         "dataset_id": "b89604c5-7994-463e-ac00-39c79c33ca20"
       }
   
   3d. MCP SERVER → BACKEND
       {
         "dataset_id": "b89604c5-7994-463e-ac00-39c79c33ca20",
         "columns": ["ORDERNUMBER", "SALES", "QUANTITYORDERED", ...],
         "numeric_summary": {
           "SALES": {"mean": 3553.89, "min": 482.13, "max": 14082.80}
         }
       }
   
   Step 4: Agent calls generate_financial_forecast(dataset_id, column="SALES", periods=3)
   
   3e. BACKEND → MCP SERVER
       POST http://localhost:8001/tools/generate_financial_forecast
       {
         "dataset_id": "b89604c5-7994-463e-ac00-39c79c33ca20",
         "column": "SALES",
         "periods": 3,
         "method": "auto"
       }
   
   3f. MCP SERVER: Execute Forecast
       - Load data/uploads/.../sales_data_sample.csv
       - Extract SALES column
       - Call auto_select_forecast_method()
       - Run Prophet/SARIMA/Linear Regression
       - Calculate confidence intervals
   
   3g. MCP SERVER → BACKEND
       {
         "forecast": [3800.5, 3950.2, 4100.8],
         "lower_bound": [3500.0, 3650.0, 3800.0],
         "upper_bound": [4100.0, 4250.0, 4400.0],
         "method_used": "prophet",
         "confidence_level": 0.95
       }

4. AGENT: Format Response
   - Summarize forecast
   - List assumptions
   - Provide recommendations

5. BACKEND → FRONTEND
   WebSocket message: agent_message
   {
     "agent": "FinancialStrategistAgent",
     "content": "Revenue Forecast for Next Quarter:
                 Month 1: $3,800 (±$300)
                 Month 2: $3,950 (±$300)
                 Month 3: $4,100 (±$300)
                 
                 Assumptions:
                 - Historical trend continues
                 - No major market disruptions
                 - Prophet model used (best fit)"
   }

6. FRONTEND: Display Result
   ✅ User sees forecast with confidence intervals
```

---

## 🔧 **Critical Configuration Points**

### **1. Backend .env** (`src/backend/.env`)

```bash
# MCP Connection (REQUIRED)
MCP_SERVER_ENDPOINT=http://localhost:8001
MCP_SERVER_NAME=MACAE MCP Server
MCP_SERVER_DESCRIPTION=Multi-Agent Custom Automation Engine MCP Tools

# Azure Auth (OPTIONAL for MCP)
# AZURE_TENANT_ID=...  ← Not needed if MCP runs with --no-auth
# AZURE_CLIENT_ID=...  ← Not needed if MCP runs with --no-auth
```

### **2. Agent Team JSON** (`data/agent_teams/finance_forecasting.json`)

```json
{
  "agents": [
    {
      "name": "FinancialStrategistAgent",
      "use_mcp": true,  ← MUST BE TRUE
      "system_message": "ALWAYS start by calling `list_finance_datasets`..."
    }
  ]
}
```

### **3. MCP Server Startup** (`scripts/start-mcp-server.ps1`)

```powershell
python mcp_server.py --transport streamable-http --port 8001 --no-auth
#                     ^^^^^^^^^^^^ HTTP transport for backend
#                                            ^^^^^^^^ Port 8001
#                                                      ^^^^^^^^^ No auth
```

---

## ❌ **Common Failure Points**

| Symptom | Cause | Fix |
|---------|-------|-----|
| "MCPConfig Missing required environment variables" | `AZURE_TENANT_ID` or `AZURE_CLIENT_ID` required but not set | ✅ **FIXED**: Made these optional |
| "Failed to initialize MCP plugin: Connection refused" | MCP server not running | Start MCP server first |
| Agent asks for "dataset location" | MCP plugin not initialized | Check backend logs for "✅ MCP plugin initialized" |
| No MCP tool logs appear | Agent has `use_mcp: false` | Set `use_mcp: true` in team JSON |
| "404 Not Found" when calling MCP tool | MCP server on wrong port or wrong transport | Verify `http://localhost:8001` |

---

## ✅ **Verification Checklist**

Before testing, ensure:

- [ ] MCP server is running on port 8001
- [ ] Backend .env has `MCP_SERVER_ENDPOINT=http://localhost:8001`
- [ ] Backend logs show "✅ MCP plugin initialized successfully"
- [ ] Agent logs show "✅ Agent initialized with MCP tools enabled"
- [ ] Test endpoint: `curl http://localhost:8001/health` returns 200 OK
- [ ] Dataset is uploaded: `python scripts/list_uploaded_datasets.py` shows your data

---

**Last Updated**: 2025-10-13  
**Purpose**: Understanding MCP Architecture & Troubleshooting













