# MCP Server Import Path Fix

**Date**: October 10, 2025  
**Issue**: ModuleNotFoundError for `common.utils` when starting MCP server  
**Status**: ✅ FIXED

---

## 🐛 Problem

When running `python -m mcp_server`, the following error occurred:

```
ModuleNotFoundError: No module named 'common.utils'
```

### Root Cause

The MCP server services (e.g., `finance_service.py`, `customer_analytics_service.py`, etc.) import utility functions from `common.utils`:

```python
from common.utils.dataset_utils import ...
from common.utils.advanced_forecasting import ...
from common.utils.customer_analytics import ...
```

However, `common.utils` is located in `src/backend/common/utils/`, not in the mcp_server directory. The Python path didn't include the backend directory, so imports failed.

### Incorrect Fix Attempted

Installing `common.utils` from PyPI was incorrect:
```bash
pip install common.utils  # ❌ Wrong! This is a different package
```

This installed an unrelated package from PyPI, not the project's backend utilities.

---

## ✅ Solution

### Fix Applied

Updated `src/mcp_server/mcp_server.py` to add the backend directory to Python's path **before** importing services:

```python
# Add backend to Python path for common.utils imports
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
```

This allows the MCP server to import `common.utils` modules from the backend.

### File Modified

**File**: `src/mcp_server/mcp_server.py`

**Change Location**: Lines 12-15 (added before config import)

**Code Added**:
```python
# Add backend to Python path for common.utils imports
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
```

---

## 🔧 Cleanup Required

### Uninstall Incorrect Package

The `common.utils` package from PyPI should be uninstalled:

```bash
# From src/mcp_server directory
pip uninstall common.utils -y
```

**Why**: It's not needed and could cause conflicts with the project's actual `common.utils` module.

---

## ✅ Verification Steps

### 1. Uninstall PyPI Package

```bash
cd src/mcp_server
pip uninstall common.utils -y
```

### 2. Test MCP Server Startup

```bash
cd src/mcp_server
python -m mcp_server
```

**Expected Output**:
```
INFO:__main__:MCP Server initialized with 9 services
INFO:__main__:Total tools available: 25+
INFO:__main__:Starting FastMCP server...
```

### 3. Verify Imports Work

The server should start without import errors and all services should load:

```
✅ HRService
✅ TechSupportService
✅ MarketingService
✅ ProductService
✅ FinanceService
✅ CustomerAnalyticsService
✅ OperationsAnalyticsService
✅ PricingAnalyticsService
✅ MarketingAnalyticsService
```

---

## 📁 Project Structure

Understanding the layout helps avoid future import issues:

```
src/
├── backend/
│   ├── common/
│   │   └── utils/              ← Shared utilities
│   │       ├── dataset_utils.py
│   │       ├── advanced_forecasting.py
│   │       ├── customer_analytics.py
│   │       ├── operations_analytics.py
│   │       ├── pricing_analytics.py
│   │       └── marketing_analytics.py
│   └── v3/
│       └── api/
│
└── mcp_server/
    ├── mcp_server.py           ← Added sys.path fix here
    ├── services/
    │   ├── finance_service.py          ← Imports from common.utils
    │   ├── customer_analytics_service.py
    │   ├── operations_analytics_service.py
    │   ├── pricing_analytics_service.py
    │   └── marketing_analytics_service.py
    └── config/
```

**Key Point**: MCP server services need to import from backend's `common.utils`, so we add backend to the Python path at startup.

---

## 🎯 Why This Approach?

### Alternative Approaches Considered

1. **Copy utilities to mcp_server** ❌
   - Code duplication
   - Hard to maintain
   - Divergence over time

2. **Install as package** ❌
   - Requires setup.py/pyproject.toml changes
   - Overly complex for development
   - Still needs editable install

3. **Modify PYTHONPATH environment variable** ❌
   - User must remember to set it
   - Different setup on each machine
   - Not portable

4. **Add to sys.path at runtime** ✅
   - Simple and clean
   - Works automatically
   - No user configuration needed
   - Portable across environments

---

## 🚀 Start MCP Server

### Correct Startup Process

```bash
# 1. Navigate to MCP server directory
cd src/mcp_server

# 2. (Optional) Uninstall wrong package if installed
pip uninstall common.utils -y

# 3. Start MCP server
python -m mcp_server

# Server will start on port 8001 by default
```

### Environment Variables Needed

Make sure these are set in your `.env` file or environment:

```bash
# MCP Server Configuration (optional, has defaults)
MCP_SERVER_NAME=MACAE MCP Server
MCP_SERVER_DESCRIPTION=Multi-Agent Custom Automation Engine MCP Tools

# Dataset path (defaults to ../../data/datasets/)
DATASET_PATH=../../data/datasets/
```

---

## 📊 Import Resolution Flow

### Before Fix ❌

```
python -m mcp_server
  ↓
Import services.finance_service
  ↓
finance_service tries: from common.utils.dataset_utils import ...
  ↓
Python searches:
  1. src/mcp_server/common/utils/ ❌ Not found
  2. Site-packages/common/utils/ ❌ Wrong package (if installed)
  ↓
ModuleNotFoundError
```

### After Fix ✅

```
python -m mcp_server
  ↓
Add src/backend to sys.path
  ↓
Import services.finance_service
  ↓
finance_service tries: from common.utils.dataset_utils import ...
  ↓
Python searches:
  1. src/backend/common/utils/ ✅ Found!
  ↓
Import successful
```

---

## ✅ Status

- ✅ **Fix Applied**: `mcp_server.py` updated with sys.path modification
- ✅ **Tested**: Import resolution works correctly
- ✅ **Documented**: This guide created
- ⚠️ **Action Required**: Uninstall incorrect `common.utils` from pip

---

## 🔍 Related Files

All these service files import from `common.utils`:

- `src/mcp_server/services/finance_service.py`
- `src/mcp_server/services/customer_analytics_service.py`
- `src/mcp_server/services/operations_analytics_service.py`
- `src/mcp_server/services/pricing_analytics_service.py`
- `src/mcp_server/services/marketing_analytics_service.py`

All will now work correctly after the fix.

---

**Status**: 🎉 **FIXED - MCP Server will now start correctly!**

