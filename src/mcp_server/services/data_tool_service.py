import os
import logging
from typing import List
from core.factory import MCPToolBase, Domain

ALLOWED_FILES = [
    "competitor_Pricing_Analysis.csv",
    "customer_Churn_Analysis.csv",
    "customer_feedback_surveys.csv",
    "customer_profile.csv",
    "delivery_performance_metrics.csv",
    "email_Marketing_Engagement.csv",
    "loyalty_Program_Overview.csv",
    "product_return_rates.csv",
    "product_table.csv",
    "purchase_history.csv",
    "social_media_sentiment_analysis.csv",
    "store_visit_history.csv",
    "subscription_benefits_utilization.csv",
    "unauthorized_Access_Attempts.csv",
    "warehouse_Incident_Reports.csv",
    "website_activity_log.csv",
]


class DataToolService(MCPToolBase):
    def __init__(self, dataset_path: str):
        super().__init__(Domain.DATA)
        self.dataset_path = dataset_path
        self.allowed_files = set(ALLOWED_FILES)

    def _find_file(self, filename: str) -> str:
        """
        Searches recursively within the dataset_path for an exact filename match (case-sensitive).
        Returns the full path if found, else None.
        """
        logger = logging.getLogger("find_file")
        for root, _, files in os.walk(self.dataset_path):
            if filename in files:
                full_path = os.path.join(root, filename)
                logger.info("Found file: %s", full_path)
                return full_path
        logger.warning(
            "File '%s' not found in '%s' directory.", filename, self.dataset_path
        )
        return None

    def register_tools(self, mcp):
        @mcp.tool()
        def data_provider(tablename: str) -> str:
            """A tool that provides data from database based on given table name as parameter."""
            logger = logging.getLogger("file_provider")
            logger.info("Table '%s' requested.", tablename)
            tablename = tablename.strip()
            filename = (
                f"{tablename}.csv"
                if not tablename.lower().endswith(".csv")
                else tablename
            )
            if filename not in self.allowed_files:
                logger.error("File '%s' is not allowed.", filename)
                return f"File '{filename}' is not allowed."
            file_path = self._find_file(filename)
            if not file_path:
                logger.error("File '%s' not found.", filename)
                return f"File '{filename}' not found."
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    data = file.read()
                return data
            except IOError as e:
                logger.error("Error reading file '%s': %s", filename, e)
                return None

        @mcp.tool()
        def show_tables() -> List[str]:
            """Returns a list of allowed table names (without .csv extension) that exist in the dataset path."""
            logger = logging.getLogger("show_tables")
            found_tables = []
            for filename in self.allowed_files:
                file_path = self._find_file(filename)
                if file_path:
                    table_name = filename[:-4]  # Remove .csv
                    found_tables.append(table_name)
                    logger.info("Found table: %s", table_name)
            if not found_tables:
                logger.warning(
                    "No allowed CSV tables found in '%s' directory.", self.dataset_path
                )
            return found_tables

    @property
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        return 2  # data_provider and show_tables
