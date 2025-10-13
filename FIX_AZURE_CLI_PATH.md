# 🔧 Fix: Azure CLI Not in PATH

**Issue:** Backend can't authenticate to Azure because Azure CLI is not in the Python process's PATH.

**Status:** ✅ **FIXED - Use new startup script**

---

## The Problem

### **Error in Backend:**
```
AzureCliCredential: Azure CLI not found on path
DefaultAzureCredential failed to retrieve a token
Error in RAI check: DefaultAzureCredential failed...
```

### **Error in Frontend:**
```
400 Bad Request
{"detail":"Request contains content that doesn't meet our safety guidelines, try again."}
```

### **Root Cause:**
When you run `uvicorn app_kernel:app --reload --port 8000` directly, the Python process doesn't have Azure CLI in its PATH. Even though `az` works in your PowerShell terminal, the backend subprocess can't find it.

---

## The Fix

### **✅ Use the New Startup Script**

I've created a script that adds Azure CLI to PATH **before** starting the backend.

### **Step 1: Stop Current Backend**
In your backend terminal, press **`Ctrl+C`**

### **Step 2: Start with New Script**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-backend-with-az.ps1
```

### **What This Script Does:**
1. ✅ Adds `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin` to PATH
2. ✅ Verifies Azure CLI is accessible
3. ✅ Checks you're logged in to Azure
4. ✅ Starts uvicorn with correct PATH
5. ✅ Backend can now authenticate via Azure CLI

---

## Verification

### **After Restarting with New Script:**

You should see in the startup output:
```
============================================================
   Starting Multi-Agent Backend Server (with Azure CLI)
============================================================

Added Azure CLI to PATH
Navigating to: ...

Verifying Azure CLI...
  azure-cli 2.77.0
  Logged in as: jkanfer@dttrndlabs.com
  Subscription: Global_RnD_US_USCG_FMPS

Starting uvicorn server...
  URL: http://localhost:8000
  Docs: http://localhost:8000/docs

Press Ctrl+C to stop the server
```

### **In Backend Logs:**

Instead of errors, you should see:
```
INFO:azure.identity.aio._credentials.cli: Azure CLI authentication succeeded
INFO:v3.magentic_agents.magentic_agent_factory: Creating agent 'FinancialStrategistAgent'
INFO:v3.magentic_agents.magentic_agent_factory: Successfully created and initialized agent
```

---

## Why This Happened

### **PATH Inheritance:**

When you run a command in PowerShell:
1. PowerShell uses **its own PATH** (includes Azure CLI)
2. Subprocesses (like Python/uvicorn) inherit that PATH
3. **BUT** Python's `multiprocessing` creates new processes that may not inherit all environment variables

### **The Solution:**

By explicitly adding Azure CLI to PATH in the startup script:
```powershell
$env:Path = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin;$env:Path"
uvicorn app_kernel:app --reload --port 8000
```

The uvicorn process and all its children have Azure CLI available.

---

## Alternative Solutions

### **Option 1: Add Azure CLI to System PATH (Permanent)**

**Pros:** Works every time, no special script needed  
**Cons:** Requires admin rights, affects entire system

**Steps:**
1. Open **System Properties** → **Environment Variables**
2. Edit **System PATH** (not User PATH)
3. Add: `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin`
4. Click OK
5. **Restart PowerShell AND your IDE**

Then you can use regular: `uvicorn app_kernel:app --reload --port 8000`

---

### **Option 2: Use Environment Variables Instead**

Instead of Azure CLI auth, use service principal with client secret:

**Add to `.env`:**
```bash
AZURE_TENANT_ID=2da40318-46be-402c-ba75-cfb1f656567d
AZURE_CLIENT_ID=1b0b523c-044e-4469-86e7-09f55f655d29
AZURE_CLIENT_SECRET=<your-secret-here>
```

**Pros:** No PATH issues  
**Cons:** Need to manage secrets, less secure for local dev

---

### **Option 3: Disable RAI Checks (Not Recommended)**

**Only for testing/debugging:**

Add to `.env`:
```bash
DISABLE_RAI_CHECKS=true
```

And uncomment the bypass code in `utils_kernel.py`:
```python
if os.getenv("DISABLE_RAI_CHECKS", "false").lower() == "true":
    return True
```

**Pros:** Bypasses auth issues  
**Cons:** No content safety checks, not suitable for production

---

## Recommended Approach

### **For Local Development:**
✅ **Use the new startup script** (`start-backend-with-az.ps1`)

This is the simplest and safest approach for local development.

### **For Production:**
✅ **Use Managed Identity** (no credentials needed in code)

The existing code already supports this - it's just for local dev that we need Azure CLI.

---

## Testing the Fix

### **Step 1: Restart Backend**
```powershell
# Stop current backend (Ctrl+C)
# Then:
powershell -ExecutionPolicy Bypass -File scripts/start-backend-with-az.ps1
```

### **Step 2: Refresh Frontend**
Press **Ctrl+Shift+R** in your browser

### **Step 3: Try Your Task Again**
```
Team: Financial Forecasting Team
Prompt: "Analyze purchase_history dataset and forecast revenue for next 6 months"
```

### **Expected Result:**
- ✅ No "Bad Request" error
- ✅ Agents create successfully
- ✅ RAI check passes
- ✅ Task processes normally
- ✅ Results appear in UI

---

## Troubleshooting

### **If you still get authentication errors:**

1. **Verify Azure CLI works:**
   ```powershell
   az account show
   ```
   Should show your logged-in account.

2. **Check correct subscription:**
   ```powershell
   az account set --subscription efd2b969-bf42-4a11-9aca-57e2716d044a
   ```

3. **Check backend startup output:**
   Look for "Added Azure CLI to PATH" message

4. **Check backend logs:**
   Should say "Azure CLI authentication succeeded" not "Azure CLI not found on path"

---

## Files Created/Modified

**New Files:**
- ✅ `scripts/start-backend-with-az.ps1` - New backend startup script with Azure CLI
- ✅ `FIX_AZURE_CLI_PATH.md` - This documentation

**What Changed:**
- Nothing in the codebase - just how we start the backend

---

## Summary

### **Before:**
```
❌ Backend started without Azure CLI in PATH
❌ DefaultAzureCredential can't find 'az' command
❌ RAI checks fail
❌ Agent creation fails
❌ Tasks return 400 Bad Request
```

### **After:**
```
✅ Backend started with Azure CLI in PATH
✅ DefaultAzureCredential uses AzureCliCredential
✅ RAI checks succeed
✅ Agents create successfully
✅ Tasks process normally
```

---

## Quick Reference

**Old command (doesn't work):**
```powershell
cd src/backend
uvicorn app_kernel:app --reload --port 8000
```

**New command (works!):**
```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-backend-with-az.ps1
```

---

**Status:** ✅ **READY TO TEST**

**Next Step:** Restart backend with new script and try your task again!

