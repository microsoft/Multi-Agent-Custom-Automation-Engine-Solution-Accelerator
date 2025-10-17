# Dataset Discovery & Upload Fixes - Implementation Complete

## Summary

This implementation fixes three critical issues with dataset discovery and follow-up question handling:

1. **Dataset ID Not Being Passed to MCP Tools** - Agents now explicitly extract and use `dataset_id` from list responses
2. **Upload 404 Error** - Fixed incorrect URL construction in frontend upload method
3. **Follow-up Questions After Plan Completion** - New plans now include context from previous completed plans

## Changes Made

### 1. Agent Configuration Updates (10 files modified)

Updated system messages in all agent team configurations to explicitly instruct agents to:
- Extract `dataset_id` from `list_finance_datasets` response
- Pass the exact `dataset_id` to subsequent MCP tool calls
- Present dataset selection with alternatives for user confirmation

**Files Modified:**
- `data/agent_teams/finance_forecasting.json` (FinancialStrategistAgent, DataPreparationAgent)
- `data/agent_teams/retail_operations.json` (OperationsStrategistAgent, SupplyChainAnalystAgent)
- `data/agent_teams/customer_intelligence.json` (ChurnPredictionAgent, SentimentAnalystAgent)
- `data/agent_teams/revenue_optimization.json` (PricingStrategistAgent, RevenueForecasterAgent)
- `data/agent_teams/marketing_intelligence.json` (CampaignAnalystAgent, LoyaltyOptimizationAgent)

**Key Instruction Added:**
```
1. Call `list_finance_datasets` to get all available datasets - the response contains a 'datasets' array with objects having 'dataset_id', 'original_filename', 'uploaded_at', etc.
2. Extract the dataset_id from the selected dataset (e.g., datasets[0]['dataset_id']).
3. Present your selection showing: Selected dataset: [name] (uploaded: [date], size: [X] rows), Other available datasets: [list alternatives].
4. Ask: 'I've selected [name]. Is this correct?'
5. After user confirms, use the exact dataset_id when calling tools: `summarize_financial_dataset(dataset_id='the-exact-id-from-step-2')`, etc.

CRITICAL: Always pass the exact dataset_id string from the list response to subsequent tool calls.
```

### 2. Frontend Upload Fix (1 file modified)

Fixed `uploadDatasetInChat` method to use the existing `apiClient.upload()` method instead of attempting to access non-existent `apiClient.baseURL`.

**File Modified:**
- `src/frontend/src/api/apiService.tsx` (lines 282-284)

**Before:**
```typescript
async uploadDatasetInChat(formData: FormData): Promise<any> {
    const response = await fetch(`${apiClient.baseURL}/v3/datasets/upload_in_chat`, {
        method: 'POST',
        body: formData,
    });
    if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
    }
    return response.json();
}
```

**After:**
```typescript
async uploadDatasetInChat(formData: FormData): Promise<any> {
    return apiClient.upload('/v3/datasets/upload_in_chat', formData);
}
```

### 3. Follow-up Plan Context (2 files modified)

Added functionality to automatically include previous plan results as context when creating a new plan in the same session.

**Files Modified:**
- `src/backend/v3/common/services/plan_service.py` (added `get_latest_completed_plan` method, lines 262-292)
- `src/backend/v3/api/router.py` (integrated context enrichment in `process_request` endpoint, lines 249-272)

**New Method in PlanService:**
```python
@staticmethod
async def get_latest_completed_plan(session_id: str, user_id: str) -> Optional[Dict]:
    """
    Get the most recent completed plan for a session.
    Retrieves plan from database and returns it for context enrichment.
    """
```

**Router Integration:**
```python
# Check for previous completed plan in this session and include its results as context
previous_context = ""
if input_task.session_id:
    previous_plan = await PlanService.get_latest_completed_plan(input_task.session_id, user_id)
    if previous_plan:
        # Extract final result and append to task description
        previous_context = f"\n\nPREVIOUS PLAN CONTEXT:\n..."

# Enrich task description with previous context
if previous_context:
    input_task.description = input_task.description + previous_context
```

### 4. Automated Tests (3 new test files)

**Backend Tests:**
- `tests/test_dataset_discovery.py` - Verifies all agent configs include dataset_id extraction instructions
- `tests/test_upload_endpoint.py` - Tests the upload endpoint exists and handles files correctly

**Frontend Tests:**
- `src/frontend/src/api/__tests__/apiService.test.ts` - Tests uploadDatasetInChat method

## Testing Instructions

### Backend Tests

Run pytest from the repository root:

```powershell
# Test dataset discovery configurations
pytest tests/test_dataset_discovery.py -v

# Test upload endpoint
pytest tests/test_upload_endpoint.py -v

# Run all new tests
pytest tests/test_dataset_discovery.py tests/test_upload_endpoint.py -v
```

### Frontend Tests

Run Jest tests from the frontend directory:

```powershell
cd src/frontend
npm test -- apiService.test.ts
```

### Manual End-to-End Testing

#### Test 1: Dataset ID Extraction
1. Upload a dataset (e.g., `sales_data_sample.csv`)
2. Start a new plan: "Analyze our latest sales dataset and create a forecast"
3. **Verify in backend logs:**
   - Agent calls `list_finance_datasets()`
   - Agent extracts `dataset_id` from response
   - Agent calls `summarize_financial_dataset(dataset_id='<actual-id>')`
   - No follow-up asking "which dataset_id?" should occur

**Expected Behavior:**
- Agent presents: "I've selected sales_data_sample.csv (uploaded: [date]). Is this correct?"
- After user confirms, agent directly calls tools with the correct `dataset_id`
- No more asking for clarification about which dataset

#### Test 2: File Upload in Chat
1. Start a new plan
2. Click the attach button (📎 icon) in the chat input
3. Select a CSV file
4. **Verify:**
   - No 404 error in browser console
   - Toast notification shows "Uploading..."
   - Toast changes to "Dataset uploaded: [filename]"
   - Dataset appears in available datasets list

**Expected Behavior:**
- File uploads successfully without errors
- WebSocket notification updates the chat
- Agent can immediately access the newly uploaded dataset

#### Test 3: Follow-up Questions
1. Complete a plan (e.g., "Forecast revenue for next quarter")
2. Wait for plan to reach COMPLETED status
3. Ask a follow-up question in the same session: "What were the key assumptions in that forecast?"
4. **Verify in new plan:**
   - Backend logs show previous plan context being retrieved
   - Agent response references specific numbers/details from previous forecast
   - New plan is created (not appended to old one)

**Expected Behavior:**
- New plan is created but includes previous plan's final result as context
- Agent can answer questions about previous results without asking "which forecast?"
- Context is limited to ~500 characters to avoid token bloat

## Next Steps

1. **Upload Updated Teams to Database:**
   ```powershell
   python scripts/upload_default_teams.py
   ```

2. **Restart Backend Server:**
   ```powershell
   # Stop current backend (Ctrl+C)
   # Start fresh
   python -m uvicorn src.backend.app_kernel:app --reload --port 8000
   ```

3. **Test with Real Data:**
   - Upload a dataset via the UI
   - Create a plan using that dataset
   - Verify agent uses dataset_id correctly
   - Test file upload in chat
   - Test follow-up questions after completion

## Expected Impact

### Before Fixes:
- ❌ Agent: "Which dataset_id would you like to use?" (every time)
- ❌ Upload button: 404 error
- ❌ Follow-up questions: No context from previous plan

### After Fixes:
- ✅ Agent: "I've selected sales_data.csv. Is this correct?" then proceeds automatically
- ✅ Upload button: Successfully uploads and notifies agents
- ✅ Follow-up questions: "Based on the previous forecast showing 15% growth..."

## Rollback Instructions

If issues occur, revert these commits:
```powershell
git checkout HEAD~1 -- data/agent_teams/
git checkout HEAD~1 -- src/frontend/src/api/apiService.tsx
git checkout HEAD~1 -- src/backend/v3/common/services/plan_service.py
git checkout HEAD~1 -- src/backend/v3/api/router.py
```

## Files Changed Summary

**Agent Configurations (10 agents across 5 files):**
- finance_forecasting.json
- retail_operations.json
- customer_intelligence.json
- revenue_optimization.json
- marketing_intelligence.json

**Backend (2 files):**
- v3/common/services/plan_service.py (added `get_latest_completed_plan`)
- v3/api/router.py (integrated context enrichment)

**Frontend (1 file):**
- api/apiService.tsx (fixed `uploadDatasetInChat`)

**Tests (3 new files):**
- tests/test_dataset_discovery.py
- tests/test_upload_endpoint.py
- src/frontend/src/api/__tests__/apiService.test.ts

---

**Implementation Status:** ✅ Complete
**Tests Written:** ✅ Yes (3 test files)
**Linter Errors:** ✅ None
**Ready for Testing:** ✅ Yes


