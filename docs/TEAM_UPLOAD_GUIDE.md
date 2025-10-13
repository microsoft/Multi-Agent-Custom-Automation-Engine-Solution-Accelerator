# Team Upload Guide - Complete Solution

## Current Situation

Your Azure Cosmos DB has **"Local Authorization disabled"** which blocks key-based authentication. This is why you're seeing:
```
(Unauthorized) Local Authorization is disabled. Use an AAD token to authorize all requests.
```

## ✅ RECOMMENDED SOLUTION: Enable Cosmos DB Key Auth

### Step 1: Enable Key-Based Authentication in Azure

1. **Go to Azure Portal:** https://portal.azure.com
2. **Navigate to Cosmos DB:**
   - Search for "cosmos-ngxbol6k"
   - Or go to Resource Groups → Agents → cosmos-ngxbol6k

3. **Enable Local Authentication:**
   - In the left menu, click **Settings** → **Keys** or **Features**
   - Look for one of these settings:
     - "Disable key based metadata write access" → Set to **OFF**
     - "Disable local authentication" → Set to **OFF**  
     - "Enable key based authentication" → Set to **ON**
   
4. **Save changes**

5. **Wait 2-3 minutes** for the setting to propagate

### Step 2: Restart Your Backend

```powershell
# Stop the backend (Ctrl+C in the backend terminal)

# Restart it
cd src/backend
uvicorn app_kernel:app --reload --port 8000
```

### Step 3: Upload Teams via Swagger UI (Easiest!)

1. **Open Swagger UI:** http://localhost:8000/docs

2. **Find the upload endpoint:**
   - Scroll down to find `/api/v3/upload_team_config`
   - Click on it to expand

3. **Upload each team:**
   
   **For HR Team:**
   - Click "Try it out"
   - Set `team_id` = `00000000-0000-0000-0000-000000000001`
   - Click "Choose File" → Select `data/agent_teams/hr.json`
   - Click "Execute"
   - You should see a 200 response
   
   **For Marketing Team:**
   - Set `team_id` = `00000000-0000-0000-0000-000000000002`
   - Upload `data/agent_teams/marketing.json`
   
   **For Retail Team:**
   - Set `team_id` = `00000000-0000-0000-0000-000000000003`
   - Upload `data/agent_teams/retail.json`
   
   **For Finance Team:**
   - Set `team_id` = `00000000-0000-0000-0000-000000000004`
   - Upload `data/agent_teams/finance_forecasting.json`

4. **Verify:**
   - Refresh http://localhost:3001
   - The "team not found" error should be gone!

---

## Alternative: Use Azure CLI to Enable Auth

If you prefer command line:

```powershell
# Enable local auth on Cosmos DB
az cosmosdb update `
  --name cosmos-ngxbol6k `
  --resource-group Agents `
  --disable-local-auth false

# Wait 2 minutes, then restart backend
```

---

## Why This Is Needed

The backend code expects to either:
1. **Use Cosmos DB keys** (if `COSMOS_DB_KEY` is set) ← We have this!
2. **Use Azure AD authentication** (if no key) ← Requires `azd auth login`

But your Cosmos DB is configured to **reject key-based auth entirely**, which overrides our configuration.

The fix modifies your Cosmos DB to accept keys again.

---

## Troubleshooting

### If Swagger upload still fails:

**Check backend logs** in the terminal where uvicorn is running. Look for:
- Authentication errors
- Cosmos DB connection errors
- File validation errors

### If you can't enable local auth:

This might be a corporate policy. In that case:

1. **Use Azure AD authentication:**
   ```powershell
   azd auth login
   ```

2. **Remove `COSMOS_DB_KEY` from `.env`:**
   Edit `src/backend/.env` and comment out:
   ```
   # COSMOS_DB_KEY=...
   ```

3. **Restart backend** - it will use Azure AD instead

---

## Quick Reference

**Team IDs (these are hardcoded in the frontend):**
```
HR Team:        00000000-0000-0000-0000-000000000001
Marketing Team: 00000000-0000-0000-0000-000000000002
Retail Team:    00000000-0000-0000-0000-000000000003
Finance Team:   00000000-0000-0000-0000-000000000004
```

**Team Files:**
```
data/agent_teams/hr.json
data/agent_teams/marketing.json
data/agent_teams/retail.json
data/agent_teams/finance_forecasting.json
```

**Backend Endpoint:**
```
POST http://localhost:8000/api/v3/upload_team_config?team_id={guid}
```

---

## Next Steps After Upload

1. ✅ Teams are in Cosmos DB
2. ✅ Refresh frontend: http://localhost:3001
3. ✅ Team initialization will work
4. ✅ You can now select and use different teams
5. ✅ The console errors will disappear

---

**Recommended: Use Swagger UI (http://localhost:8000/docs) - it's visual and shows you exactly what's happening!**

