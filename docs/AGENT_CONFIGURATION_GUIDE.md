# Agent Configuration & Troubleshooting Guide

## 🎯 **Problem Identified**

Your agents were asking for too many clarifications because they weren't proactively using MCP tools to discover datasets. This guide explains how to fix it.

---

## 📋 **What Changed**

### **Updated Agent System Messages**

All agent team configurations now include **proactive dataset discovery instructions**:

**Before:**
```
"Always begin by calling the MCP tool `list_finance_datasets` to understand available files, 
then ask the user to confirm the dataset identifier..."
```

**After:**
```
"ALWAYS start by calling `list_finance_datasets` to see available datasets. 
When the user mentions a dataset by name (e.g. 'purchase_history.csv' or 'sales dataset'), 
automatically match it to the most relevant dataset_id from the list. 
Only ask for clarification if NO datasets are available or if the user's request is truly ambiguous."
```

---

## 🔧 **How to Update Agent Teams**

### **Option 1: Via Frontend (Recommended)**

1. **Navigate to**: `http://localhost:3001`

2. **For each team**, delete and re-upload:
   - Financial Forecasting Team (`data/agent_teams/finance_forecasting.json`)
   - Retail Operations Team (`data/agent_teams/retail_operations.json`)
   - Customer Intelligence Team (`data/agent_teams/customer_intelligence.json`)
   - Revenue Optimization Team (`data/agent_teams/revenue_optimization.json`)
   - Marketing Intelligence Team (`data/agent_teams/marketing_intelligence.json`)

3. **Refresh frontend**: Press `Ctrl+Shift+R`

### **Option 2: Via PowerShell (If backend is running)**

```powershell
# Navigate to repo root
cd "C:\Users\jkanfer\OneDrive - Deloitte (O365D)\Desktop\Code\Multi-Agent-Custom-Automation-Engine-Solution-Accelerator"

# Finance Forecasting Team
$json = Get-Content "data/agent_teams/finance_forecasting.json" -Raw
Invoke-RestMethod -Uri "http://localhost:8000/api/v3/upload_team_config?team_id=team-forecasting" -Method Post -ContentType "application/json" -Body $json

# Retail Operations Team
$json = Get-Content "data/agent_teams/retail_operations.json" -Raw
Invoke-RestMethod -Uri "http://localhost:8000/api/v3/upload_team_config?team_id=team-retail-operations" -Method Post -ContentType "application/json" -Body $json

# Customer Intelligence Team
$json = Get-Content "data/agent_teams/customer_intelligence.json" -Raw
Invoke-RestMethod -Uri "http://localhost:8000/api/v3/upload_team_config?team_id=team-customer-intelligence" -Method Post -ContentType "application/json" -Body $json

# Revenue Optimization Team
$json = Get-Content "data/agent_teams/revenue_optimization.json" -Raw
Invoke-RestMethod -Uri "http://localhost:8000/api/v3/upload_team_config?team_id=team-revenue-optimization" -Method Post -ContentType "application/json" -Body $json

# Marketing Intelligence Team
$json = Get-Content "data/agent_teams/marketing_intelligence.json" -Raw
Invoke-RestMethod -Uri "http://localhost:8000/api/v3/upload_team_config?team_id=team-marketing-intelligence" -Method Post -ContentType "application/json" -Body $json
```

---

## ✅ **How Agents Should Behave Now**

### **Expected Workflow:**

1. **User**: "Use our latest sales dataset to project revenue for the next quarter"

2. **Agent (Internally)**:
   - Calls `list_finance_datasets()` MCP tool
   - Sees: `purchase_history.csv` with `dataset_id: 40adbd2f-0a3d-432c-9ff5-73abcbb2f455`
   - Matches "sales dataset" → `purchase_history.csv`
   - Automatically uses `dataset_id: 40adbd2f-0a3d-432c-9ff5-73abcbb2f455`

3. **Agent (Continues)**:
   - Calls `summarize_financial_dataset("40adbd2f-0a3d-432c-9ff5-73abcbb2f455")`
   - Calls `generate_financial_forecast("40adbd2f-0a3d-432c-9ff5-73abcbb2f455", column="TotalAmount", periods=3)`
   - Returns forecast with confidence intervals

4. **Agent (Response to User)**:
   - "Based on `purchase_history.csv`, here's the revenue forecast for Q1 2024..."
   - Shows forecast values, confidence intervals, assumptions

### **What Should NOT Happen:**

- ❌ Agent asks: "Can you provide the dataset location?"
- ❌ Agent asks: "Which specific dataset should I use?"
- ❌ Agent asks: "Please specify the fiscal quarter dates"
- ❌ Agent asks: "Can you retrieve and provide the dataset contents?"

### **When Agents SHOULD Ask for Clarification:**

- ✅ When **NO datasets** are uploaded
- ✅ When user request is **truly ambiguous** (e.g., "analyze data" with no context)
- ✅ When **multiple equally relevant datasets** exist and the user's intent is unclear

---

## 🧪 **Testing Your Agents**

### **1. Run Automated Tests**

```powershell
# Run comprehensive agent workflow tests
python scripts/testing/test_agent_workflows.py
```

**What this tests:**
- Dataset discovery logic
- MCP tool usage
- Complete workflows (forecasting, churn analysis, etc.)
- Error handling
- Performance

**Expected output:**
```
============================================================
  ALL AGENT WORKFLOWS PASSED!
============================================================

Your agents are configured correctly and should:
  1. Automatically discover uploaded datasets
  2. Match dataset names to dataset_ids
  3. Use MCP tools to analyze data
  4. Complete tasks with minimal clarification requests
```

### **2. Manual Testing via Frontend**

1. **Upload a dataset**:
   - Go to `http://localhost:3001`
   - Upload `data/datasets/purchase_history.csv`

2. **Verify dataset was uploaded**:
   ```powershell
   python scripts/list_uploaded_datasets.py
   ```
   
   You should see:
   ```
   Dataset #1
     File: purchase_history.csv
     Dataset ID: 40adbd2f-0a3d-432c-9ff5-73abcbb2f455
   ```

3. **Test with Financial Forecasting Team**:
   - Select "Financial Forecasting Team"
   - Enter: **"Use our latest sales dataset to project revenue for the next quarter"**
   - Click "Create Plan"

4. **Expected Behavior**:
   - Agent should **immediately start working** (no clarification about dataset location)
   - Agent may ask about fiscal calendar (this is acceptable)
   - Agent should return forecast with assumptions

5. **What to Monitor**:
   - **Good**: Agent calls `list_finance_datasets`, finds dataset, proceeds with forecast
   - **Bad**: Agent asks "Can you provide the dataset?" or "Where is the data?"

---

## 🔍 **Debugging Agent Behavior**

### **Check Backend Logs**

When agents use MCP tools, you'll see logs like:

```
INFO:     MCP tool called: list_finance_datasets
INFO:     MCP tool called: summarize_financial_dataset with dataset_id=40adbd2f-0a3d-432c-9ff5-73abcbb2f455
INFO:     MCP tool called: generate_financial_forecast with dataset_id=40adbd2f-0a3d-432c-9ff5-73abcbb2f455
```

**If you DON'T see these logs**, the agents aren't using MCP tools correctly.

### **Common Issues & Fixes**

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Agents not using MCP tools** | No MCP log messages, agents ask for dataset location | Verify `use_mcp: true` in team JSON |
| **MCP server not responding** | Logs show "MCPConfig Missing required environment variables" | Restart MCP server with `scripts/start-mcp-server.ps1` |
| **Agents can't find datasets** | Agents say "No datasets found" even though you uploaded one | Run `python scripts/list_uploaded_datasets.py` to verify upload |
| **Too many clarifications** | Agents ask for dataset_id, fiscal dates, etc. | Re-upload updated team configs |

---

## 📊 **Dataset Discovery Logic**

### **How Agents Match Dataset Names**

Agents use **fuzzy matching** on keywords:

| User Says | Agent Matches |
|-----------|---------------|
| "sales dataset", "revenue data", "purchase history" | `purchase_history.csv` |
| "delivery performance", "shipping metrics" | `delivery_performance_metrics.csv` |
| "customer churn", "retention data" | `customer_churn_analysis.csv` |
| "competitor prices", "pricing analysis" | `competitor_pricing_analysis.csv` |
| "email campaigns", "marketing engagement" | `email_marketing_engagement.csv` |

### **Priority Rules**

1. **Most recent upload** wins if multiple matches
2. **Exact filename match** preferred over keyword match
3. **Multiple datasets**: Agent uses context to choose (e.g., forecasting → chooses dataset with time-series columns)

---

## 🚀 **Next Steps After Updating**

1. **Update all 5 agent teams** (via frontend or PowerShell)
2. **Refresh frontend** (`Ctrl+Shift+R`)
3. **Run automated tests**: `python scripts/testing/test_agent_workflows.py`
4. **Manual test** with a real conversation
5. **Monitor backend logs** to see MCP tool calls

---

## 📝 **Summary of Files Changed**

| File | What Changed |
|------|--------------|
| `data/agent_teams/finance_forecasting.json` | Updated `FinancialStrategistAgent` and `DataPreparationAgent` system messages |
| `data/agent_teams/retail_operations.json` | Updated `OperationsStrategistAgent` and `SupplyChainAnalystAgent` system messages |
| `data/agent_teams/customer_intelligence.json` | Updated `ChurnPredictionAgent` and `SentimentAnalystAgent` system messages |
| `data/agent_teams/revenue_optimization.json` | Updated `PricingStrategistAgent` and `RevenueForecasterAgent` system messages |
| `data/agent_teams/marketing_intelligence.json` | Updated `CampaignAnalystAgent` and `LoyaltyOptimizationAgent` system messages |
| `tests/e2e-test/test_agent_mcp_integration.py` | **NEW**: Comprehensive agent workflow tests |
| `scripts/testing/test_agent_workflows.py` | **NEW**: Test runner script |
| `scripts/list_uploaded_datasets.py` | **NEW**: Utility to list all uploaded datasets |
| `scripts/update_teams_auto_discovery.ps1` | **NEW**: Automated team update script |

---

## 🎓 **Best Practices for Agent Configuration**

### **System Message Guidelines**

✅ **DO**:
- Specify exact MCP tools to call
- Provide clear matching logic for datasets
- Define when to ask for clarification
- Include expected output format

❌ **DON'T**:
- Say "you may want to..." (be directive)
- Leave dataset discovery to user
- Ask for clarification as first step
- Assume agents know what "latest" means

### **Example: Good System Message**

```json
{
  "system_message": "You are a Revenue Forecaster. ALWAYS call `list_finance_datasets` first to see available data. When asked about datasets by filename (e.g., 'purchase_history.csv'), automatically locate the matching dataset_id. Only ask for clarification if no datasets are uploaded. Use advanced forecasting methods (SARIMA, Prophet, auto-selection) to predict revenue trends."
}
```

### **Example: Bad System Message**

```json
{
  "system_message": "You help with revenue forecasting. You may want to check for available datasets first. Ask the user which dataset they want to use."
}
```

---

## ❓ **FAQ**

**Q: Why do agents still ask about fiscal quarters?**  
A: This is acceptable! Fiscal calendar definitions vary by company. If you want to avoid this, add "Assume standard calendar quarters unless specified" to system messages.

**Q: How do I add new datasets the agents can recognize?**  
A: Just upload the CSV via the frontend. Agents will discover it automatically via `list_finance_datasets`.

**Q: Can I customize the matching logic?**  
A: Yes! Edit the agent's `system_message` to include specific keywords or aliases. For example: "When user says 'Q4 data', match to `q4_2024_revenue.csv`"

**Q: What if I have multiple versions of the same dataset?**  
A: Agents prefer the **most recently uploaded** dataset by default. You can override by explicitly mentioning the upload date in your request.

---

## 📞 **Getting Help**

If agents still aren't working correctly after following this guide:

1. Run: `python scripts/testing/test_agent_workflows.py`
2. Check: `python scripts/list_uploaded_datasets.py`
3. Review: Backend logs for MCP tool calls
4. Verify: Teams were updated (check `system_message` in Cosmos DB or via frontend)

---

**Last Updated**: 2025-10-13  
**Sprint**: Post-Sprint 5 - Agent Optimization





