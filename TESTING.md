# Testing Guide

This document provides comprehensive testing instructions for the Multi-Agent Custom Automation Engine Solution Accelerator.

## Quick Start

### Run All Sprint Tests

```bash
# Sprint 1: Advanced Forecasting (28 tests)
python scripts/testing/run_sprint1_tests.py

# Sprint 2: Customer & Operations Analytics (75 tests)
python scripts/testing/run_sprint2_tests.py

# Sprint 3: Pricing & Marketing Analytics (68 tests)
python scripts/testing/run_sprint3_tests.py
```

**Expected Results:**
- Sprint 1: 28/28 tests passing
- Sprint 2: 75/75 tests passing  
- Sprint 3: 68/68 tests passing
- **Total: 171/171 tests passing**

## Test Organization

### Backend Tests

**Location:** `src/backend/tests/`

```
src/backend/tests/
├── conftest.py                           # Test configuration & path setup
├── README.md                             # Backend testing documentation
├── test_advanced_forecasting.py          # Sprint 1: Advanced forecasting (28 tests)
├── test_customer_analytics.py            # Sprint 2: Customer analytics (31 tests)
├── test_operations_analytics.py          # Sprint 2: Operations analytics (44 tests)
├── test_pricing_analytics.py             # Sprint 3: Pricing analytics (36 tests)
├── test_marketing_analytics.py           # Sprint 3: Marketing analytics (32 tests)
├── test_app.py                           # Application tests
├── test_config.py                        # Configuration tests
├── auth/                                 # Authentication tests
├── middleware/                           # Middleware tests
└── models/                               # Data model tests
```

### MCP Server Tests

**Location:** `src/tests/mcp_server/`

```
src/tests/mcp_server/
├── test_factory.py                # MCP factory tests
├── test_fastmcp_run.py            # FastMCP runtime tests
├── test_hr_service.py             # HR service tests
└── test_utils.py                  # Utility tests
```

### Agent Tests

**Location:** `src/tests/agents/`

```
src/tests/agents/
├── test_foundry_integration.py    # Azure AI Foundry tests
├── test_human_approval_manager.py # Human approval tests
├── test_proxy_agent.py            # Proxy agent tests
└── test_reasoning_agent.py        # Reasoning agent tests
```

### End-to-End Tests

**Location:** `tests/e2e-test/`

```
tests/e2e-test/
├── tests/
│   └── test_MACAE_GP.py           # E2E orchestration tests
├── pytest.ini
└── README.md
```

## Running Tests

### All Backend Tests

```bash
cd src/backend
pytest
```

### Specific Test Suite

```bash
# Advanced forecasting
cd src/backend
pytest tests/test_advanced_forecasting.py -v

# Auth tests
cd src/backend
pytest tests/auth/ -v

# All with coverage
cd src/backend
pytest --cov=common --cov-report=html
```

### MCP Server Tests

```bash
cd src
pytest tests/mcp_server/ -v
```

### Agent Tests

```bash
cd src
pytest tests/agents/ -v
```

### End-to-End Tests

```bash
cd tests/e2e-test
pytest tests/ -v
```

## Test Scripts

### `run_advanced_tests.py`

Quick runner for Sprint 1 advanced forecasting tests.

**Usage:**
```bash
python run_advanced_tests.py
```

**Output:**
- Runs 28 advanced forecasting unit tests
- Shows detailed pass/fail status
- Displays warnings (expected from statsmodels)

## Dependencies

### Core Testing
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting

### Advanced Forecasting Tests
- `statsmodels>=0.14.0` - SARIMA, Exponential Smoothing
- `prophet>=1.1.5` - Facebook Prophet
- `scikit-learn>=1.3.0` - Metrics and evaluation
- `numpy>=1.24.0` - Numerical computations

**Install all:**
```bash
pip install statsmodels prophet scikit-learn numpy
```

## Test Coverage

### Sprint 1: Advanced Forecasting

**File:** `src/backend/tests/test_advanced_forecasting.py`  
**Tests:** 28 comprehensive unit tests  
**Status:** ✅ 100% passing

| Component | Tests | Coverage |
|-----------|-------|----------|
| Seasonality Detection | 3 | ✅ Complete |
| Linear Forecasting | 5 | ✅ Complete |
| SARIMA | 3 | ✅ Complete |
| Exponential Smoothing | 3 | ✅ Complete |
| Prophet | 2 | ✅ Complete |
| Auto-Selection | 3 | ✅ Complete |
| Accuracy Metrics | 5 | ✅ Complete |
| Confidence Intervals | 2 | ✅ Complete |
| Integration | 2 | ✅ Complete |

### Existing Test Suites

| Test Suite | Location | Tests | Status |
|------------|----------|-------|--------|
| Backend Core | `src/backend/tests/` | Multiple | ✅ Passing |
| MCP Server | `src/tests/mcp_server/` | 4 files | ✅ Passing |
| Agents | `src/tests/agents/` | 4 files | ✅ Passing |
| E2E | `tests/e2e-test/` | 1 file | ⚠️ Requires deployment |

## Expected Warnings

### Advanced Forecasting Tests (7 warnings)

The advanced forecasting test suite produces **7 expected warnings** from statsmodels:

1. **ConvergenceWarning** (2 warnings)
   - Cause: SARIMA on small test datasets
   - Impact: None - test data limitation
   - Action: None required

2. **UserWarning: Too few observations** (1 warning)
   - Cause: Seasonal ARIMA with minimal data
   - Impact: None - edge case testing
   - Action: None required

3. **RuntimeWarning: divide by zero** (4 warnings)
   - Cause: Perfect fit in exponential smoothing AIC/BIC calculation
   - Impact: None - statsmodels internal calculation
   - Action: None required

**All warnings are from test edge cases and do not indicate failures.**

## Continuous Integration

### Azure DevOps Pipeline

Tests are run automatically in `.azdo/pipelines/azure-dev.yml`:

```yaml
- script: |
    cd src/backend
    pytest tests/ -v --junitxml=test-results.xml
  displayName: 'Run Backend Tests'
```

### GitHub Actions

Tests can be run via `.github/workflows/` (if configured):

```yaml
- name: Run Tests
  run: |
    cd src/backend
    pytest tests/ -v
```

## Troubleshooting

### "ImportError: No module named 'statsmodels'"

**Solution:**
```bash
pip install statsmodels prophet scikit-learn numpy
```

Tests requiring these packages will be skipped if not installed.

### "Tests are slow"

**Cause:** Prophet tests run MCMC sampling (10-30 seconds)

**Solution:** Run subset of tests:
```bash
pytest tests/test_advanced_forecasting.py::TestLinearForecastWithConfidence -v
```

### "No tests collected"

**Cause:** Wrong working directory

**Solution:** Ensure you're in the correct directory:
```bash
# For backend tests
cd src/backend
pytest tests/

# For MCP tests
cd src
pytest tests/mcp_server/
```

### "ModuleNotFoundError: No module named 'common'"

**Cause:** Python path not set correctly

**Solution:** Run from correct directory or use test runner:
```bash
python run_advanced_tests.py
```

## Adding New Tests

### For New Forecasting Methods

1. Add test class to `src/backend/tests/test_advanced_forecasting.py`
2. Follow existing patterns (TestSARIMAForecast, etc.)
3. Include tests for:
   - Basic functionality
   - Edge cases
   - Error handling
   - Data validation
4. Run full suite to ensure no regressions

### For New MCP Services

1. Create test file in `src/tests/mcp_server/`
2. Follow pattern from `test_hr_service.py`
3. Test all MCP tool methods
4. Include integration tests

### For New Agent Features

1. Create test file in `src/tests/agents/`
2. Test agent initialization, lifecycle, methods
3. Include async test support with pytest-asyncio

## Test Data

### Synthetic Data

All advanced forecasting tests use **synthetic data** generated within the test file:

- Linear trends
- Seasonal patterns
- Random noise
- Edge cases (constant values, minimal data)

### Real Datasets

For manual testing with real data, use datasets in `data/datasets/`:

- `delivery_performance_metrics.csv`
- `social_media_sentiment_analysis.csv`
- `competitor_pricing_analysis.csv`
- `purchase_history.csv`

## Documentation

- **Backend Tests:** `src/backend/tests/README.md`
- **Sprint 1 Complete:** `docs/FinanceForecasting_Sprint1_Complete.md`
- **E2E Tests:** `tests/e2e-test/README.md`

## Quick Reference

```bash
# Sprint 1 advanced forecasting tests (recommended)
python run_advanced_tests.py

# All backend tests
cd src/backend && pytest

# Specific test file
cd src/backend && pytest tests/test_advanced_forecasting.py -v

# With coverage report
cd src/backend && pytest --cov=common --cov-report=html

# MCP server tests
cd src && pytest tests/mcp_server/ -v

# Agent tests
cd src && pytest tests/agents/ -v
```

---

**Last Updated:** October 10, 2025  
**Test Suites:** Backend, MCP Server, Agents, E2E  
**Sprint 1 Status:** ✅ All 28 tests passing

