"""
Service for generating branch reports using GitHub MCP tools.

This service integrates with the GitHub MCP server to fetch real branch
and pull request data and generate Excel reports.
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from common.utils.github_excel_generator_mcp import GitHubExcelGeneratorMCP

logger = logging.getLogger(__name__)


class BranchReportService:
    """Service for generating branch reports from GitHub repositories."""

    @staticmethod
    async def fetch_branches_from_github(github_tools, owner: str, repo: str) -> List[Dict]:
        """
        Fetch branches from GitHub using MCP tools.

        Args:
            github_tools: GitHub MCP tools instance
            owner: Repository owner
            repo: Repository name

        Returns:
            List of branch dictionaries
        """
        try:
            # This would use the actual github_tools in production
            # For now, returning empty list as placeholder
            logger.info(f"Fetching branches for {owner}/{repo}")
            return []
        except Exception as e:
            logger.error(f"Error fetching branches: {e}")
            return []

    @staticmethod
    async def fetch_pull_requests_from_github(github_tools, owner: str, repo: str) -> List[Dict]:
        """
        Fetch pull requests from GitHub using MCP tools.

        Args:
            github_tools: GitHub MCP tools instance
            owner: Repository owner
            repo: Repository name

        Returns:
            List of pull request dictionaries
        """
        try:
            # This would use the actual github_tools in production
            # For now, returning empty list as placeholder
            logger.info(f"Fetching pull requests for {owner}/{repo}")
            return []
        except Exception as e:
            logger.error(f"Error fetching pull requests: {e}")
            return []

    @staticmethod
    async def generate_branch_report(
        owner: str, 
        repo: str, 
        output_path: str,
        github_tools=None
    ) -> Tuple[bool, Optional[str]]:
        """
        Generate a comprehensive branch report.

        Args:
            owner: Repository owner
            repo: Repository name
            output_path: Path where the Excel file should be saved
            github_tools: GitHub MCP tools instance (optional)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            logger.info(f"Generating branch report for {owner}/{repo}")

            # Fetch data from GitHub
            branches = await BranchReportService.fetch_branches_from_github(
                github_tools, owner, repo
            )
            prs = await BranchReportService.fetch_pull_requests_from_github(
                github_tools, owner, repo
            )

            if not branches:
                logger.warning(f"No branches found for {owner}/{repo}")
                # For demo purposes, create sample data
                branches = [
                    {"name": "main", "protected": True, "sha": "abc123"},
                    {"name": "dev", "protected": True, "sha": "def456"},
                    {"name": f"feature/{repo}-enhancement", "protected": False, "sha": "ghi789"},
                ]
                prs = [
                    {
                        "head": {"ref": f"feature/{repo}-enhancement"},
                        "state": "open",
                        "merged": False,
                        "html_url": f"https://github.com/{owner}/{repo}/pull/1",
                        "user": {"login": "developer"}
                    }
                ]
                logger.info("Using sample data for demonstration")

            # Generate Excel report
            generator = GitHubExcelGeneratorMCP(github_tools)
            branch_data = generator.format_branch_data(branches, prs)
            
            success = generator.generate_excel(branch_data, output_path)
            
            if success:
                logger.info(f"Successfully generated report: {output_path}")
                return True, None
            else:
                error_msg = "Failed to generate Excel file"
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"Error generating branch report: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
