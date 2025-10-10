"""
Sprint 3 Test Runner - Pricing & Marketing Analytics

Runs comprehensive unit tests for Sprint 3 deliverables:
- Pricing analytics utilities
- Marketing analytics utilities
- All integration workflows

Tests are organized using pytest and cover:
- 44 pricing analytics tests
- 48 marketing analytics tests
- Integration scenarios for both modules
"""

import sys
import pytest
from pathlib import Path


def main():
    """Run Sprint 3 pricing and marketing analytics tests."""
    
    print("=" * 70)
    print("Running Sprint 3: Pricing & Marketing Analytics Tests")
    print("=" * 70)
    print()
    
    # Get paths to test files relative to repo root
    repo_root = Path(__file__).parent.parent.parent
    pricing_test = repo_root / "src" / "backend" / "tests" / "test_pricing_analytics.py"
    marketing_test = repo_root / "src" / "backend" / "tests" / "test_marketing_analytics.py"
    
    # Run pricing analytics tests
    print("Testing Pricing Analytics...")
    print("-" * 70)
    pricing_exit_code = pytest.main([
        str(pricing_test),
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    print()
    print("=" * 70)
    print()
    
    # Run marketing analytics tests
    print("Testing Marketing Analytics...")
    print("-" * 70)
    marketing_exit_code = pytest.main([
        str(marketing_test),
        "-v",
        "--tb=short",
        "--color=yes"
    ])
    
    print()
    print("=" * 70)
    print("Sprint 3 Test Summary")
    print("=" * 70)
    
    if pricing_exit_code == 0 and marketing_exit_code == 0:
        print("✅ All Sprint 3 tests passed!")
        print()
        print("Deliverables Validated:")
        print("  • Competitive pricing analysis")
        print("  • Discount optimization")
        print("  • Revenue forecasting by category")
        print("  • Campaign effectiveness analysis")
        print("  • Engagement prediction")
        print("  • Loyalty program optimization")
        return 0
    else:
        print("❌ Some Sprint 3 tests failed")
        if pricing_exit_code != 0:
            print("  • Pricing analytics tests failed")
        if marketing_exit_code != 0:
            print("  • Marketing analytics tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

