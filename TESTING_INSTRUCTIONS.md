# Testing Instructions - Agent Dataset Access

## ✅ Fixes Applied

1. **Fixed Azure AI Project Client** - Agents will now create properly in Foundry
2. **Corrected Model Names** - Using `gpt-4.1` (your deployed model)
3. **Enabled Code Interpreter** - Financial agents can now process datasets
4. **MCP Tools Configured** - Agents have access to dataset tools

## 🔄 Restart Backend Server

**Important**: You need to restart the backend for the code changes to take effect.

1. Stop the current backend server (Ctrl+C in the PowerShell window)
2. Restart it using:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start-backend-with-az.ps1
   ```

## 🧪 Test Scenario

### 1. Refresh Frontend
- Go to http://localhost:3001
- Refresh the page (F5 or Ctrl+R)

### 2. Select Financial Forecasting Team
- You should see "Financial Forecasting Team" in the dropdown
- Select it and click to initialize

### 3. Submit Test Query
Use the pre-configured starting task:

```
Use our latest sales dataset to project revenue for the next quarter and summarize assumptions.
```

## ✅ Expected Behavior

### What You Should See:

1. **Plan Creation** ✅
   - System creates a plan showing the team and approach
   - You'll be asked to approve the plan

2. **Dataset Auto-Discovery** ✅
   - Agent should call `list_finance_datasets()`
   - Find the uploaded dataset: `b89604c5-7994-463e-ac00-39c79c33ca20`
   - Automatically use it (no clarification needed)

3. **Dataset Analysis** ✅
   - Agent calls `summarize_financial_dataset(dataset_id)`
   - Reviews numeric columns, statistics
   - Identifies revenue/sales columns

4. **Forecast Generation** ✅
   - Agent uses Code Interpreter to analyze trends
   - Generates revenue projections
   - Provides assumptions and confidence intervals

## 🔍 Verify Agents in Foundry Portal

While testing, you can verify agents are being created:

1. Go to Azure Portal → Azure AI Foundry
2. Open your project: **proj-ngxbol6k**
3. Navigate to: **Models + endpoints** → **Agents** tab
4. You should see agents listed:
   - `FinancialStrategistAgent`
   - `DataPreparationAgent`

## 📊 Backend Logs to Watch For

### ✅ Success Indicators:

```
INFO:v3.magentic_agents.magentic_agent_factory:Creating agent 1/3: FinancialStrategistAgent
✅ MCP config created: http://localhost:8001/mcp
INFO:azure.identity.aio._credentials.chained:DefaultAzureCredential acquired a token
INFO:root:Agent with ID <agent_id> created successfully
✅ Agent 1/3 created: FinancialStrategistAgent
```

### ❌ Errors to Watch Out For:

If you still see:
```
ERROR: Failed to create agent: (404) Resource not found
```

Then check your `.env` file has:
```bash
AZURE_AI_AGENT_ENDPOINT=https://proj-ngxbol6k.api.azureml.ms
AZURE_AI_PROJECT_NAME=proj-ngxbol6k
```

## 🐛 Troubleshooting

### Issue: Agents still fail with 404

**Solution**: 
1. Verify `.env` file is in `src/backend/` directory
2. Check all Azure AI configuration variables are set
3. Restart backend server

### Issue: Agents ask for dataset ID clarification

**Current Behavior**: Agents are requesting the dataset ID from the user

**Expected Fix**: With the updated instructions in `finance_forecasting.json`, agents should:
1. Call `list_finance_datasets()` first
2. Auto-match by filename or use most recent
3. Only ask if no datasets exist

If still asking for clarification, the agent's system message needs to emphasize the auto-discovery behavior more strongly.

### Issue: No tools available

**Check**:
1. MCP server is running on port 8001
2. Backend logs show: `✅ MCP plugin initialized successfully`
3. Agent logs show: `✅ Agent has MCP plugin: MACAE MCP Server`

## 📝 What Changed Summary

| Component | Before | After | Impact |
|-----------|--------|-------|--------|
| **Client Init** | `AzureAIAgent.create_client()` | `AIProjectClient(endpoint=...)` | Agents create in correct Foundry project |
| **Model Name** | `gpt-4.1` (correct) | `gpt-4.1` (kept) | Uses your deployed model |
| **Coding Tools** | `false` | `true` | Agents can analyze datasets |
| **MCP Plugin** | Configured | Configured | Access to dataset tools |

---

## Next Step

**Restart your backend server now**, then test with the Financial Forecasting Team!

Watch the backend logs as the agents initialize. You should see successful creation messages instead of 404 errors.



