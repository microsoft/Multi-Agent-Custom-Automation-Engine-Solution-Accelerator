# 🚀 Quick Start Guide

**Multi-Agent Custom Automation Engine** - Get up and running in minutes!

---

## ✅ Prerequisites

- **Python 3.13+** installed
- **Node.js 18+** and npm installed
- **Azure CLI** installed (for full Azure integration)
- **Git** for version control

---

## 🎯 Choose Your Path

### Path A: Test Analytics Features Locally (No Azure Required)

Perfect for exploring the analytics capabilities without Azure setup.

#### Step 1: Install Python Dependencies

```powershell
cd src/backend
pip install -r requirements.txt
```

#### Step 2: Run Unit Tests

```powershell
# Test Sprint 1: Advanced Forecasting
python ../../scripts/testing/run_sprint1_tests.py

# Test Sprint 2: Customer & Operations Analytics
python ../../scripts/testing/run_sprint2_tests.py

# Test Sprint 3: Pricing & Marketing Analytics
python ../../scripts/testing/run_sprint3_tests.py
```

#### Step 3: Explore Jupyter Notebooks

```powershell
# Install Jupyter
pip install jupyter matplotlib seaborn

# Launch notebooks
cd ../../
jupyter notebook examples/notebooks/
```

**Available Notebooks:**
- `01_revenue_forecasting.ipynb` - Advanced forecasting methods
- `02_customer_segmentation.ipynb` - RFM, churn, CLV analysis
- `03_operations_analytics.ipynb` - Delivery, inventory, warehouse
- `04_pricing_marketing.ipynb` - Pricing optimization & ROI

---

### Path B: Full Azure Integration

Get the complete platform running with Azure backend.

#### Step 1: Azure Login

```powershell
# Login to Azure (opens browser or use device code)
az login

# Or if 'az' is not recognized, use full path:
& "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd" login

# Verify login
az account show
```

#### Step 2: Environment Setup

The `.env` files are already created with your Azure credentials:

```
✅ src/backend/.env       - Backend configuration
✅ src/mcp_server/.env    - MCP server configuration
```

**Test your environment:**

```powershell
python scripts/test_env.py
```

#### Step 3: Start Backend Server

```powershell
cd src/backend
uvicorn app_kernel:app --reload --port 8000
```

**Backend will be available at:** `http://localhost:8000`

**Test it:**
```powershell
# In a new terminal
curl http://localhost:8000/api/v3/analytics/health
```

#### Step 4: Start Frontend (Optional)

```powershell
# In a new terminal
cd src/frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

**Frontend will be available at:** `http://localhost:3001`

#### Step 5: Start MCP Server (Optional)

```powershell
# In a new terminal
cd src/mcp_server
python -m mcp_server
```

**MCP Server will be available at:** `http://localhost:8001`

---

## 🧪 Verify Everything Works

### Test Backend API

```powershell
# Health check
curl http://localhost:8000/api/v3/analytics/health

# Get KPIs
curl http://localhost:8000/api/v3/analytics/kpis

# Get forecast summary
curl "http://localhost:8000/api/v3/analytics/forecast-summary?periods=12"

# Get model comparison
curl http://localhost:8000/api/v3/analytics/model-comparison

# Get recent activity
curl http://localhost:8000/api/v3/analytics/recent-activity
```

### Test Analytics API

```powershell
cd scripts/testing
python test_analytics_api.py
```

Expected output: `5 passed` ✅

---

## 📊 Access the Analytics Dashboard

Once both backend and frontend are running:

1. **Open browser:** `http://localhost:3001`
2. **Navigate to:** `/analytics`
3. **Explore:**
   - KPI cards with trends
   - Interactive forecast charts
   - Model comparison panels
   - Recent activity feed

---

## 🔧 Common Issues

### Issue: `az is not recognized`

**Solution:** Restart PowerShell or use full path:

```powershell
& "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd" login
```

Or run the helper script:

```powershell
.\scripts\az-login.ps1
```

See: `docs/WINDOWS_SETUP_QUICK_FIX.md`

---

### Issue: Backend errors about Cosmos DB

**Solution 1:** Use in-memory database for testing

Edit `src/backend/.env` and add:
```
USE_IN_MEMORY_DB=true
```

**Solution 2:** Verify Cosmos DB credentials

```powershell
python scripts/test_env.py
```

---

### Issue: Frontend can't connect to backend

**Causes:**
- Backend not running on port 8000
- CORS issues
- Incorrect `FRONTEND_SITE_NAME` in `.env`

**Solution:**
```powershell
# Check backend is running
curl http://localhost:8000/api/v3/analytics/health

# Check frontend .env has correct backend URL
# src/frontend/.env should have:
# VITE_API_BASE_URL=http://localhost:8000
```

---

### Issue: Import errors in Python

**Solution:** Install all dependencies

```powershell
cd src/backend
pip install -r requirements.txt

# Verify statsmodels, prophet installed
pip list | findstr -i "statsmodels prophet"
```

---

## 📚 Next Steps

### Learn the Platform

- **User Guide:** `docs/USER_GUIDE.md` - Business user walkthrough
- **Developer Guide:** `docs/DEVELOPER_GUIDE.md` - Technical deep dive
- **API Reference:** `docs/API_REFERENCE.md` - Complete API docs

### Explore Use Cases

- **Retail Revenue Forecasting:** `examples/scenarios/01_retail_revenue_forecasting.md`
- **Customer Churn Prevention:** `examples/scenarios/02_customer_churn_prevention.md`
- **Operations Optimization:** `examples/scenarios/03_operations_optimization.md`
- **Pricing & Marketing ROI:** `examples/scenarios/04_pricing_marketing_roi.md`

### Deploy to Production

- **Full Azure Deployment:** `docs/FULL_AZURE_DEPLOYMENT.md`
- **Environment Variables:** `docs/ENVIRONMENT_VARIABLES.md`
- **Performance Optimization:** `docs/PERFORMANCE_OPTIMIZATION.md`

---

## 🆘 Get Help

### Troubleshooting

1. **Windows Setup:** `docs/WINDOWS_SETUP_QUICK_FIX.md`
2. **Environment Setup:** `docs/ENV_SETUP_GUIDE.md`
3. **Testing Guide:** `TESTING.md`

### Documentation

- **Sprint Progress:** `SPRINT_PROGRESS_SUMMARY.md`
- **Sprint 5 Complete:** `docs/sprints/sprint5/SPRINT5_COMPLETE.md`
- **All Sprint Docs:** `docs/sprints/`

---

## 🎉 You're Ready!

**Current Status:**
- ✅ Azure credentials configured
- ✅ Environment files created
- ✅ Backend ready to start
- ✅ 132 tests passing
- ✅ 15 MCP tools available
- ✅ 5 agent teams configured
- ✅ 4 Jupyter notebooks ready
- ✅ Analytics dashboard implemented

**Quick Commands:**

```powershell
# Backend
cd src/backend; uvicorn app_kernel:app --reload --port 8000

# Frontend
cd src/frontend; npm run dev

# MCP Server
cd src/mcp_server; python -m mcp_server

# Tests
python scripts/testing/run_sprint1_tests.py

# Notebooks
jupyter notebook examples/notebooks/
```

Enjoy exploring the Multi-Agent Custom Automation Engine! 🚀

