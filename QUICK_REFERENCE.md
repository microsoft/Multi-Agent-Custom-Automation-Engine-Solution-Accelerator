# ⚡ Quick Reference Card

**Keep this handy for daily use!**

---

## 🚀 Starting Services

### Automated (Easiest)
```powershell
# Start everything at once (opens 3 terminals)
.\start-all.ps1

# Or just backend
.\start-backend-only.ps1
```

### Manual (Full Control)
```powershell
# Terminal 1: Backend
cd src/backend
uvicorn app_kernel:app --reload --port 8000

# Terminal 2: MCP Server
cd src/mcp_server
python -m mcp_server

# Terminal 3: Frontend
cd src/frontend
npm run dev
```

---

## 🔗 Access Points

| Service | URL |
|---------|-----|
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/api/v3/analytics/health |
| **Analytics Dashboard** | http://localhost:3001/analytics |
| **Frontend Home** | http://localhost:3001 |

---

## 🧪 Running Tests

```powershell
# All analytics tests
python scripts/testing/test_analytics_api.py

# Sprint 1: Advanced Forecasting (28 tests)
python scripts/testing/run_sprint1_tests.py

# Sprint 2: Customer & Operations (75 tests)
python scripts/testing/run_sprint2_tests.py

# Sprint 3: Pricing & Marketing (68 tests)
python scripts/testing/run_sprint3_tests.py
```

---

## 📓 Jupyter Notebooks

```powershell
# Start Jupyter
jupyter notebook examples/notebooks/

# Notebooks available:
# 1. 01_revenue_forecasting.ipynb
# 2. 02_customer_segmentation.ipynb
# 3. 03_operations_analytics.ipynb
# 4. 04_pricing_marketing.ipynb
```

---

## 🔧 Troubleshooting

### Backend not responding?
```powershell
# Check if running
Invoke-WebRequest http://localhost:8000/api/v3/analytics/health

# Restart backend
cd src/backend
uvicorn app_kernel:app --reload --port 8000
```

### Check environment?
```powershell
python scripts/test_env.py
```

### Port in use?
```powershell
# Find process
netstat -ano | findstr :8000

# Use different port
uvicorn app_kernel:app --reload --port 8001
```

### Import errors?
```powershell
cd src/backend
pip install -r requirements.txt
```

---

## 📚 Documentation

| Topic | File |
|-------|------|
| **Complete Startup Guide** | `START_EVERYTHING.md` |
| **Quick Start** | `GETTING_STARTED_NOW.md` |
| **User Guide** | `docs/USER_GUIDE.md` |
| **Developer Guide** | `docs/DEVELOPER_GUIDE.md` |
| **API Reference** | `docs/API_REFERENCE.md` |
| **Backend Setup** | `docs/BACKEND_STARTUP_FIXED.md` |
| **Windows Fixes** | `docs/WINDOWS_SETUP_QUICK_FIX.md` |

---

## 🎯 Common Workflows

### Testing Analytics
```powershell
1. Start backend only
2. Run: python scripts/testing/test_analytics_api.py
3. Open: http://localhost:8000/docs
```

### Full Demo
```powershell
1. Run: .\start-all.ps1
2. Wait 30 seconds
3. Open: http://localhost:3001/analytics
```

### Data Exploration
```powershell
1. jupyter notebook examples/notebooks/
2. Open any notebook
3. Run cells
```

### Development
```powershell
1. Start backend (Terminal 1)
2. Edit code
3. Backend auto-reloads with --reload flag
4. Run tests to verify
```

---

## 📊 Platform Stats

- **MCP Tools:** 15 available
- **Agent Teams:** 5 configured
- **Tests:** 176 passing
- **Notebooks:** 4 interactive
- **API Endpoints:** 5 operational
- **Datasets:** 15 sample datasets

---

## 🎨 Key Features

| Category | What's Available |
|----------|-----------------|
| **Forecasting** | SARIMA, Prophet, Exponential Smoothing, Linear, Auto-select |
| **Customer** | Churn analysis, RFM segmentation, CLV prediction, Sentiment |
| **Operations** | Delivery forecasting, Inventory optimization, Warehouse analytics |
| **Pricing** | Competitive analysis, Discount optimization, Revenue forecasting |
| **Marketing** | Campaign effectiveness, Engagement prediction, Loyalty optimization |

---

## 🛑 Stopping Services

```powershell
# In each terminal window:
Ctrl + C

# Or close the terminal windows
```

---

## ⚡ One-Liners

```powershell
# Quick health check
Invoke-WebRequest http://localhost:8000/api/v3/analytics/health | ConvertFrom-Json

# Get KPIs
Invoke-WebRequest http://localhost:8000/api/v3/analytics/kpis | ConvertFrom-Json

# Test everything
python scripts/testing/test_analytics_api.py

# Verify environment
python scripts/test_env.py

# Open API docs
start http://localhost:8000/docs

# Open dashboard
start http://localhost:3001/analytics
```

---

## 💾 File Locations

```
Project Root/
├── start-all.ps1              # Start everything
├── start-backend-only.ps1     # Start backend only
├── START_EVERYTHING.md        # Detailed startup guide
├── GETTING_STARTED_NOW.md     # Quick start guide
│
├── src/
│   ├── backend/              # Backend API
│   │   └── .env              # Backend config
│   ├── frontend/             # React dashboard
│   └── mcp_server/           # MCP tools
│       └── .env              # MCP config
│
├── scripts/
│   ├── test_env.py           # Verify environment
│   └── testing/              # Test suites
│
├── examples/
│   ├── notebooks/            # Jupyter notebooks
│   └── scenarios/            # Use case docs
│
└── docs/                     # All documentation
```

---

## 🎓 Learning Path

**Day 1:**
1. Start backend: `.\start-backend-only.ps1`
2. Explore API: http://localhost:8000/docs
3. Run tests: `python scripts/testing/test_analytics_api.py`

**Day 2:**
4. Try notebooks: `jupyter notebook examples/notebooks/`
5. Read use cases: `examples/scenarios/`

**Day 3:**
6. Start full stack: `.\start-all.ps1`
7. Explore dashboard: http://localhost:3001/analytics

**Week 2:**
8. Upload your datasets
9. Customize agent teams
10. Build custom tools

---

## 🆘 Need Help?

1. Check: `START_EVERYTHING.md`
2. Check: `docs/BACKEND_STARTUP_FIXED.md`
3. Verify: `python scripts/test_env.py`
4. Review terminal logs for errors

---

**Print this page and keep it at your desk!** 📋

