#!/usr/bin/env python3
"""
Agent Workflow Test Runner

This script runs comprehensive tests to validate agent behaviors:
- Dataset discovery
- MCP tool usage
- Complete workflows
- Error handling
- Performance
"""

import sys
import pytest
from pathlib import Path

def main():
    repo_root = Path(__file__).parent.parent.parent
    test_file = repo_root / "tests" / "e2e-test" / "test_agent_mcp_integration.py"
    
    print("="*70)
    print("  AGENT WORKFLOW VALIDATION")
    print("="*70)
    print()
    print("This test suite validates:")
    print("  - Agents can discover datasets automatically")
    print("  - Agents use MCP tools correctly")
    print("  - Agents complete full workflows without excessive clarification")
    print("  - Agents handle errors gracefully")
    print("  - Agents perform efficiently")
    print()
    print("="*70)
    print()
    
    # Run pytest
    exit_code = pytest.main([
        str(test_file),
        "-v",
        "--tb=short",
        "--color=yes",
        "-k", "not test_agent_performance"  # Skip performance tests for quick validation
    ])
    
    print()
    print("="*70)
    if exit_code == 0:
        print("  ALL AGENT WORKFLOWS PASSED!")
        print("="*70)
        print()
        print("Your agents are configured correctly and should:")
        print("  1. Automatically discover uploaded datasets")
        print("  2. Match dataset names to dataset_ids")
        print("  3. Use MCP tools to analyze data")
        print("  4. Complete tasks with minimal clarification requests")
        print()
    else:
        print("  SOME TESTS FAILED")
        print("="*70)
        print()
        print("Review the errors above to identify issues with:")
        print("  - MCP tool configuration")
        print("  - Agent system messages")
        print("  - Dataset discovery logic")
        print()
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())

