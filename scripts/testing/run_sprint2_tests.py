#!/usr/bin/env python3
"""Run Sprint 2 Customer & Operations Analytics tests."""

import sys
from pathlib import Path

print("=" * 70)
print("Running Sprint 2: Customer & Operations Analytics Tests")
print("=" * 70)
print()

# Import pytest and run
import pytest

# Get paths to test files relative to repo root
repo_root = Path(__file__).parent.parent.parent
test_file1 = repo_root / "src" / "backend" / "tests" / "test_customer_analytics.py"
test_file2 = repo_root / "src" / "backend" / "tests" / "test_operations_analytics.py"

# Run both test files
exit_code = pytest.main([
    str(test_file1),
    str(test_file2),
    '-v',
    '--tb=short',
    '--color=yes'
])

print()
print("=" * 70)
if exit_code == 0:
    print("✅ All Sprint 2 tests passed!")
else:
    print(f"❌ Some tests failed (exit code: {exit_code})")
print("=" * 70)

sys.exit(exit_code)

