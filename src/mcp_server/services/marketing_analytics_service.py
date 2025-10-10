"""Marketing Analytics MCP tools for campaign analysis, engagement prediction, and loyalty optimization."""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.factory import Domain, MCPToolBase
from common.utils.dataset_utils import (
    detect_numeric_columns,
    read_preview,
)
from common.utils.marketing_analytics import (
    analyze_campaign_effectiveness,
    predict_engagement,
    optimize_loyalty_program,
)

LOGGER = logging.getLogger(__name__)

METADATA_FILENAME = "metadata.json"


def _sanitize_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)


class MarketingAnalyticsService(MCPToolBase):
    """Tools for marketing campaign analysis, engagement prediction, and loyalty program optimization."""

    def __init__(self, dataset_root: Optional[Path] = None):
        super().__init__(Domain.MARKETING_ANALYTICS)
        default_root = Path(__file__).resolve().parents[3] / "data" / "uploads"
        self.dataset_root = dataset_root or default_root
        self.dataset_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    def _metadata_path(self, metadata: Dict[str, str]) -> Path:
        user_folder = _sanitize_identifier(metadata.get("user_id", ""))
        dataset_folder = _sanitize_identifier(metadata.get("dataset_id", ""))
        return self.dataset_root / user_folder / dataset_folder / METADATA_FILENAME

    def _get_metadata(self, dataset_id: str, user_id: str = "default") -> Dict[str, Any]:
        metadata_path = self._metadata_path({"user_id": user_id, "dataset_id": dataset_id})
        if not metadata_path.exists():
            raise FileNotFoundError(f"No metadata found for dataset '{dataset_id}'")
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_dataset_path(self, dataset_id: str, user_id: str = "default") -> Path:
        metadata = self._get_metadata(dataset_id, user_id)
        user_folder = _sanitize_identifier(metadata.get("user_id", user_id))
        dataset_folder = _sanitize_identifier(metadata.get("dataset_id", dataset_id))
        filename = metadata.get("original_filename", "data.csv")
        return self.dataset_root / user_folder / dataset_folder / filename

    def _read_csv_data(self, dataset_path: Path) -> List[Dict[str, Any]]:
        """Read CSV file and return list of dictionaries."""
        data = []
        with open(dataset_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data

    # ------------------------------------------------------------------
    # MCP Tool Registration
    @property
    def tool_count(self) -> int:
        return 3

    def register_tools(self, mcp: Any) -> None:
        """Register all marketing analytics tools with the MCP server."""

        # ------------------------------------------------------------------
        # Tool 1: Analyze Campaign Effectiveness
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def analyze_campaign_effectiveness(
            dataset_id: str,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Analyze email marketing campaign effectiveness.
            
            Evaluates campaign performance based on open rates, click rates, and unsubscribes.
            Identifies best and worst performing campaigns and provides optimization recommendations.
            
            Args:
                dataset_id: Campaign dataset (must include Campaign, Opened, Clicked, Unsubscribed)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with campaign performance metrics, engagement scores, and recommendations.
                
            Example:
                {
                    "total_campaigns": 5,
                    "overall_metrics": {
                        "open_rate": 60.0,
                        "click_rate": 40.0,
                        "click_through_rate": 66.7,
                        "unsubscribe_rate": 0.0
                    },
                    "best_campaign": {
                        "name": "Summer Sale",
                        "engagement_score": 90,
                        "performance": "Excellent"
                    },
                    "campaigns": [
                        {
                            "campaign": "Summer Sale",
                            "opened": true,
                            "clicked": true,
                            "engagement_score": 90,
                            "performance": "Excellent",
                            "recommendation": "Excellent engagement! Analyze what worked..."
                        }
                    ],
                    "recommendations": [...]
                }
            """
            try:
                LOGGER.info(f"Analyzing campaign effectiveness for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                campaign_data = self._read_csv_data(dataset_path)
                
                result = analyze_campaign_effectiveness(campaign_data)
                
                LOGGER.info(
                    f"Campaign analysis complete: {result.get('total_campaigns', 0)} campaigns, "
                    f"open rate: {result.get('overall_metrics', {}).get('open_rate', 0):.1f}%"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "campaigns": []}
            except Exception as e:
                LOGGER.error(f"Error analyzing campaigns: {e}")
                return {"error": str(e), "campaigns": []}

        # ------------------------------------------------------------------
        # Tool 2: Predict Engagement
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def predict_engagement(
            customer_dataset_id: str,
            customer_id: str,
            campaign_dataset_id: Optional[str] = None,
            campaign_type: str = "sale",
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Predict customer engagement for a specific campaign type.
            
            Uses customer profile and historical campaign performance to predict
            likelihood of email open and click, plus optimal send timing.
            
            Args:
                customer_dataset_id: Customer profile dataset (CustomerID, TotalSpend, MembershipDuration)
                customer_id: Specific customer to analyze
                campaign_dataset_id: Optional historical campaign data for better predictions
                campaign_type: Type of campaign (e.g., "sale", "new_arrivals", "exclusive_offers")
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with engagement probabilities, optimal timing, and recommendations.
                
            Example:
                {
                    "customer_id": "C1024",
                    "customer_name": "Emily Thompson",
                    "campaign_type": "sale",
                    "open_probability": 0.780,
                    "click_probability": 0.546,
                    "engagement_level": "High",
                    "optimal_send_time": "Tuesday 10 AM",
                    "timing_confidence": "High",
                    "recommendation": "High engagement expected. Prioritize this customer for sale campaigns."
                }
            """
            try:
                LOGGER.info(f"Predicting engagement for customer {customer_id}, campaign type: {campaign_type}")
                
                # Read customer data
                customer_path = self._get_dataset_path(customer_dataset_id, user_id)
                customer_data = self._read_csv_data(customer_path)
                
                # Find the specific customer
                target_customer = None
                for customer in customer_data:
                    if customer.get('CustomerID') == customer_id:
                        target_customer = customer
                        break
                
                if not target_customer:
                    return {
                        "error": f"Customer '{customer_id}' not found in dataset",
                        "open_probability": 0,
                        "click_probability": 0
                    }
                
                # Read historical campaign data if provided
                historical_campaigns = []
                if campaign_dataset_id:
                    try:
                        campaign_path = self._get_dataset_path(campaign_dataset_id, user_id)
                        historical_campaigns = self._read_csv_data(campaign_path)
                    except FileNotFoundError:
                        LOGGER.warning(f"Campaign dataset {campaign_dataset_id} not found, using default probabilities")
                
                result = predict_engagement(target_customer, historical_campaigns, campaign_type)
                
                LOGGER.info(
                    f"Engagement prediction complete for {customer_id}: "
                    f"open prob: {result.get('open_probability', 0):.3f}, "
                    f"engagement level: {result.get('engagement_level', 'Unknown')}"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": str(e), "open_probability": 0, "click_probability": 0}
            except Exception as e:
                LOGGER.error(f"Error predicting engagement: {e}")
                return {"error": str(e), "open_probability": 0, "click_probability": 0}

        # ------------------------------------------------------------------
        # Tool 3: Optimize Loyalty Program
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def optimize_loyalty_program(
            loyalty_dataset_id: str,
            benefits_dataset_id: str,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Optimize loyalty program based on points usage and benefits utilization.
            
            Analyzes redemption patterns, identifies underutilized benefits, flags expiring
            points, and provides recommendations to increase program engagement and value.
            
            Args:
                loyalty_dataset_id: Loyalty data (TotalPointsEarned, PointsRedeemed, CurrentPointBalance, PointsExpiringNextMonth)
                benefits_dataset_id: Benefits utilization data (Benefit, UsageFrequency)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with loyalty program health metrics, utilization analysis, and recommendations.
                
            Example:
                {
                    "points_metrics": {
                        "total_earned": 4800,
                        "points_redeemed": 3600,
                        "current_balance": 1200,
                        "redemption_rate": 75.0,
                        "points_expiring_soon": 1200,
                        "expiration_risk": 100.0
                    },
                    "benefits_utilization": [
                        {
                            "benefit": "Personalized Styling Sessions",
                            "usage_frequency": 0,
                            "utilization": "Not Used",
                            "improvement_priority": "High"
                        }
                    ],
                    "recommendations": [
                        {
                            "priority": "Critical",
                            "category": "Points Expiration",
                            "finding": "1200 points (100% of balance) expiring next month",
                            "action": "Send urgent expiration reminder with curated redemption options"
                        }
                    ],
                    "program_health": "Fair"
                }
            """
            try:
                LOGGER.info(f"Optimizing loyalty program for datasets {loyalty_dataset_id}, {benefits_dataset_id}")
                
                # Read loyalty data (single row)
                loyalty_path = self._get_dataset_path(loyalty_dataset_id, user_id)
                loyalty_data_list = self._read_csv_data(loyalty_path)
                loyalty_data = loyalty_data_list[0] if loyalty_data_list else {}
                
                # Read benefits data
                benefits_path = self._get_dataset_path(benefits_dataset_id, user_id)
                benefits_data = self._read_csv_data(benefits_path)
                
                result = optimize_loyalty_program(loyalty_data, benefits_data)
                
                LOGGER.info(
                    f"Loyalty program optimization complete: "
                    f"program health: {result.get('program_health', 'Unknown')}, "
                    f"redemption rate: {result.get('points_metrics', {}).get('redemption_rate', 0):.1f}%"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": str(e), "recommendations": []}
            except Exception as e:
                LOGGER.error(f"Error optimizing loyalty program: {e}")
                return {"error": str(e), "recommendations": []}

        LOGGER.info(f"Registered {self.tool_count} marketing analytics tools")



