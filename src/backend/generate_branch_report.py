#!/usr/bin/env python3
"""
Standalone script to generate Excel report with GitHub branch information.

Usage:
    python generate_branch_report.py <owner> <repo> [output_file]

Example:
    python generate_branch_report.py microsoft Multi-Agent-Custom-Automation-Engine-Solution-Accelerator
    python generate_branch_report.py microsoft Multi-Agent-Custom-Automation-Engine-Solution-Accelerator custom_output.xlsx

Environment Variables:
    GITHUB_TOKEN: GitHub personal access token for API authentication
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import from common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.utils.github_excel_generator import GitHubExcelGenerator


def main():
    """Main function to run the standalone script."""
    if len(sys.argv) < 3:
        print("Usage: python generate_branch_report.py <owner> <repo> [output_file]")
        print("\nExample:")
        print("  python generate_branch_report.py microsoft Multi-Agent-Custom-Automation-Engine-Solution-Accelerator")
        sys.exit(1)

    owner = sys.argv[1]
    repo = sys.argv[2]
    
    # Generate default output filename if not provided
    if len(sys.argv) >= 4:
        output_file = sys.argv[3]
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"branch_report_{owner}_{repo}_{timestamp}.xlsx"

    # Check for GitHub token
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("WARNING: GITHUB_TOKEN environment variable not set.")
        print("You may encounter API rate limits or access issues.")
        print("\nTo set the token:")
        print("  export GITHUB_TOKEN='your_token_here'")
        print()

    # Initialize generator and create report
    print(f"Generating branch report for {owner}/{repo}...")
    generator = GitHubExcelGenerator(github_token)
    
    success = generator.generate_report(owner, repo, output_file)
    
    if success:
        print(f"\n✅ Report successfully generated: {output_file}")
        return 0
    else:
        print("\n❌ Failed to generate report. Please check the logs for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
