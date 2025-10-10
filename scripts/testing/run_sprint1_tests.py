"""
Sprint 1 Test Runner - Advanced Forecasting

Runs comprehensive unit tests for Sprint 1 deliverables:
- Advanced forecasting utilities (SARIMA, Prophet, Exponential Smoothing)
- Confidence intervals and uncertainty quantification
- Model evaluation and auto-selection

Tests are organized using pytest and cover:
- 28 advanced forecasting tests
- Seasonality detection, forecast accuracy, confidence intervals
"""

import sys
import pytest
from pathlib import Path


def main():
    """Run Sprint 1 advanced forecasting tests."""
    
    print("=" * 70)
    print("Running Sprint 1: Advanced Forecasting Tests")
    print("=" * 70)
    print()
    
    # Run advanced forecasting tests
    print("Testing Advanced Forecasting Methods...")
    print("-" * 70)
    
    # Get path to test file relative to repo root
    repo_root = Path(__file__).parent.parent.parent
    test_file = repo_root / "src" / "backend" / "tests" / "test_advanced_forecasting.py"
    
    exit_code = pytest.main([
        str(test_file),
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    print()
    print("=" * 70)
    print("Sprint 1 Test Summary")
    print("=" * 70)
    
    if exit_code == 0:
        print("✅ All Sprint 1 tests passed!")
        print()
        print("Deliverables Validated:")
        print("  • SARIMA forecasting with seasonality detection")
        print("  • Prophet forecasting with trend analysis")
        print("  • Exponential smoothing (Holt-Winters)")
        print("  • Linear forecasting with confidence intervals")
        print("  • Automatic method selection")
        print("  • Model evaluation (MAE, RMSE, MAPE)")
        return 0
    else:
        print("❌ Some Sprint 1 tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

