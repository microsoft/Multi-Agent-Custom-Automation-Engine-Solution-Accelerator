#!/usr/bin/env python3
"""
Simple script to generate Excel report with GitHub branch information from this repository.

This script demonstrates the branch report functionality using sample data.
"""

import sys
import os
import tempfile
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.utils.github_excel_generator_mcp import GitHubExcelGeneratorMCP


def create_sample_report():
    """Create a sample branch report with demo data."""
    
    # Sample branch data (in real scenario, this would come from GitHub MCP tools)
    branches = [
        {"name": "main", "protected": True},
        {"name": "dev", "protected": True},
        {"name": "copilot/add-excel-sheet-functionality", "protected": False},
        {"name": "feature/new-feature", "protected": False},
    ]
    
    # Sample PR data
    prs = [
        {
            "head": {"ref": "copilot/add-excel-sheet-functionality"},
            "state": "open",
            "merged": False,
            "html_url": "https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator/pull/123",
            "user": {"login": "copilot-swe-agent[bot]"}
        },
        {
            "head": {"ref": "feature/new-feature"},
            "state": "closed",
            "merged": True,
            "html_url": "https://github.com/microsoft/Multi-Agent-Custom-Automation-Engine-Solution-Accelerator/pull/122",
            "user": {"login": "developer"}
        }
    ]
    
    # Create generator (no GitHub tools needed for demo)
    generator = GitHubExcelGeneratorMCP(github_tools=None)
    
    # Format the data
    branch_data = generator.format_branch_data(branches, prs)
    
    # Generate output filename (platform-independent)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(tempfile.gettempdir(), f"sample_branch_report_{timestamp}.xlsx")
    
    # Generate Excel file
    print(f"Generating sample branch report...")
    success = generator.generate_excel(branch_data, output_file)
    
    if success:
        print(f"\n✅ Sample report successfully generated: {output_file}")
        print(f"\nThe report contains {len(branch_data)} branches with the following columns:")
        print("  - Branch Name")
        print("  - PR Status (merged, open, closed, none)")
        print("  - Created By")
        print("  - PR URL")
        print("  - Protected (Yes/No)")
        return 0
    else:
        print("\n❌ Failed to generate sample report")
        return 1


if __name__ == "__main__":
    sys.exit(create_sample_report())
