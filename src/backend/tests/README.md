# Backend Tests

This directory contains all backend unit and integration tests for the Multi-Agent Custom Automation Engine.

## Test Organization

```
tests/
├── auth/                          # Authentication tests
├── middleware/                    # Middleware tests
├── models/                        # Data model tests
├── test_advanced_forecasting.py   # Advanced forecasting tests (Sprint 1)
├── test_app.py                    # Application tests
├── test_config.py                 # Configuration tests
├── test_otlp_tracing.py           # OpenTelemetry tracing tests
├── test_team_specific_methods.py  # Team method tests
└── test_utils_date_enhanced.py    # Date utility tests
```

## Running Tests

### All Tests

```bash
cd src/backend
pytest
```

### Specific Test File

```bash
cd src/backend
pytest tests/test_advanced_forecasting.py -v
```

### Specific Test Class

```bash
cd src/backend
pytest tests/test_advanced_forecasting.py::TestSARIMAForecast -v
```

### With Coverage

```bash
cd src/backend
pytest --cov=common --cov-report=html
```

## Advanced Forecasting Tests

**File:** `test_advanced_forecasting.py`  
**Test Count:** 28 comprehensive unit tests  
**Coverage:** All forecasting methods and utilities

### Test Classes

1. **TestDetectSeasonality** (3 tests)
   - Seasonal pattern detection
   - Non-seasonal data handling
   - Edge cases

2. **TestLinearForecastWithConfidence** (5 tests)
   - Upward/downward trends
   - Constant values
   - Minimum data requirements
   - Confidence intervals

3. **TestSARIMAForecast** (3 tests)
   - Basic forecasting
   - Seasonal patterns
   - Data validation

4. **TestExponentialSmoothingForecast** (3 tests)
   - Basic smoothing
   - Seasonal smoothing
   - Error handling

5. **TestProphetForecast** (2 tests)
   - Basic forecasting
   - Data validation

6. **TestAutoSelectForecastMethod** (3 tests)
   - Small dataset handling
   - Medium dataset handling
   - Confidence level variations

7. **TestEvaluateForecastAccuracy** (5 tests)
   - Perfect forecasts
   - Imperfect forecasts
   - Error conditions
   - Edge cases

8. **TestConfidenceIntervalCoverage** (2 tests)
   - Interval width validation
   - Horizon effects

9. **TestForecastMethodComparison** (2 tests)
   - Multi-method comparison
   - Edge case handling

### Quick Test Run

```bash
# From project root
python run_advanced_tests.py
```

### Expected Results

```
====================================================================================================== test session starts ======================================================================================================
collected 28 items

src/backend/tests/test_advanced_forecasting.py::TestDetectSeasonality::test_detect_seasonality_with_seasonal_data PASSED      [  3%]
...
================================================================================================ 28 passed, 7 warnings in 18.60s ================================================================================================
```

**Note:** The 7 warnings are expected and come from statsmodels edge cases in test data. They do not indicate errors.

## Dependencies

### Core (No Installation Required)
- pytest
- Standard Python libraries

### Advanced Features
```bash
pip install statsmodels prophet scikit-learn numpy
```

Required for:
- SARIMA forecasting tests
- Prophet forecasting tests
- Exponential smoothing tests

## Test Data

All tests use synthetic data generated within the test file. No external datasets required.

## Troubleshooting

### "ImportError: No module named 'statsmodels'"

Install advanced packages:
```bash
pip install statsmodels prophet scikit-learn numpy
```

Or tests will be skipped automatically.

### Tests Are Slow

Prophet tests can take 10-30 seconds due to MCMC sampling. This is expected behavior.

To run faster subset:
```bash
pytest tests/test_advanced_forecasting.py::TestLinearForecastWithConfidence -v
```

### Warnings About Convergence

These are **expected** warnings from statsmodels when working with small test datasets. They do not indicate test failures.

## Adding New Tests

When adding new forecasting methods or analytics tools:

1. Create a new test class following the existing pattern
2. Include tests for:
   - Basic functionality
   - Edge cases
   - Error handling
   - Data validation
3. Run full test suite to ensure no regressions
4. Update test count in this README

---

**Last Updated:** October 10, 2025  
**Test Coverage:** 28 tests for advanced forecasting  
**Status:** All tests passing (100%)


