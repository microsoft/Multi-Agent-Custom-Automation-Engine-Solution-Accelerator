"""Customer Analytics MCP tools for churn analysis, segmentation, CLV, and sentiment tracking."""

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
    extract_numeric_series,
)
from common.utils.customer_analytics import (
    analyze_churn_drivers,
    segment_customers_rfm,
    predict_customer_lifetime_value,
    analyze_sentiment_trends,
)

LOGGER = logging.getLogger(__name__)

METADATA_FILENAME = "metadata.json"


def _sanitize_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)


class CustomerAnalyticsService(MCPToolBase):
    """Tools for customer churn analysis, segmentation, CLV prediction, and sentiment tracking."""

    def __init__(self, dataset_root: Optional[Path] = None):
        super().__init__(Domain.CUSTOMER)
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
        return 4

    def register_tools(self, mcp: Any) -> None:
        """Register all customer analytics tools with the MCP server."""

        # ------------------------------------------------------------------
        # Tool 1: Analyze Customer Churn
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def analyze_customer_churn(dataset_id: str, user_id: str = "default") -> Dict[str, Any]:
            """
            Analyze customer churn drivers from churn analysis dataset.
            
            Identifies top reasons for customer cancellations, ranks them by percentage,
            and provides actionable retention recommendations.
            
            Args:
                dataset_id: The ID of the churn analysis dataset (e.g., customer_churn_analysis.csv)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with churn drivers ranked by percentage, retention recommendations,
                and overall risk assessment.
                
            Example:
                {
                    "total_churn_rate": 100.0,
                    "drivers": [
                        {"reason": "Service Dissatisfaction", "percentage": 40, "rank": 1},
                        {"reason": "Competitor Offer", "percentage": 15, "rank": 2}
                    ],
                    "top_driver": {
                        "reason": "Service Dissatisfaction",
                        "percentage": 40,
                        "impact": "Critical"
                    },
                    "recommendations": [
                        {
                            "priority": "High",
                            "action": "Improve service quality",
                            "details": "40% of churn is service-related..."
                        }
                    ]
                }
            """
            try:
                LOGGER.info(f"Analyzing churn for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                churn_data = self._read_csv_data(dataset_path)
                
                result = analyze_churn_drivers(churn_data)
                
                LOGGER.info(f"Churn analysis complete: {len(result.get('drivers', []))} drivers identified")
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "drivers": []}
            except Exception as e:
                LOGGER.error(f"Error analyzing churn: {e}")
                return {"error": str(e), "drivers": []}

        # ------------------------------------------------------------------
        # Tool 2: Segment Customers
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def segment_customers(
            dataset_id: str,
            method: str = "rfm",
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Segment customers using RFM (Recency, Frequency, Monetary) analysis.
            
            Groups customers into segments (Champions, Loyal Customers, Potential Loyalists,
            At Risk, Needs Attention) based on their purchase behavior and value.
            
            Args:
                dataset_id: The ID of customer profile dataset (must include MembershipDuration, TotalSpend)
                method: Segmentation method (currently supports "rfm")
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with customer segments, characteristics, and engagement strategies.
                
            Example:
                {
                    "total_customers": 1,
                    "segments": [
                        {
                            "segment": "Loyal Customers",
                            "count": 1,
                            "total_value": 4800,
                            "avg_spend": 4800,
                            "strategy": "Upsell and increase engagement...",
                            "customers": [...]
                        }
                    ],
                    "methodology": "RFM (Recency, Frequency, Monetary) Analysis"
                }
            """
            try:
                LOGGER.info(f"Segmenting customers from dataset {dataset_id} using {method} method")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                customer_data = self._read_csv_data(dataset_path)
                
                if method.lower() == "rfm":
                    result = segment_customers_rfm(customer_data)
                else:
                    return {"error": f"Unsupported segmentation method: {method}", "segments": []}
                
                LOGGER.info(f"Segmentation complete: {len(result.get('segments', []))} segments created")
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "segments": []}
            except Exception as e:
                LOGGER.error(f"Error segmenting customers: {e}")
                return {"error": str(e), "segments": []}

        # ------------------------------------------------------------------
        # Tool 3: Predict Customer Lifetime Value
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def predict_customer_lifetime_value(
            dataset_id: str,
            customer_id: str,
            projection_months: int = 12,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Predict customer lifetime value (CLV) over a specified projection period.
            
            Calculates projected revenue from a customer based on historical spending patterns,
            retention probability, and churn risk.
            
            Args:
                dataset_id: The ID of customer profile dataset (must include CustomerID, TotalSpend, AvgMonthlySpend, MembershipDuration)
                customer_id: The specific customer ID to analyze
                projection_months: Number of months to project CLV (default: 12)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with CLV projection, confidence intervals, retention rate,
                and value tier classification.
                
            Example:
                {
                    "customer_id": "C1024",
                    "customer_name": "Emily Thompson",
                    "historical_value": 4800.00,
                    "projected_value": 2161.52,
                    "total_clv": 6961.52,
                    "confidence_interval": {"lower": 5569.22, "upper": 8353.82},
                    "projection_months": 12,
                    "avg_monthly_spend": 200.00,
                    "estimated_churn_rate": 0.250,
                    "retention_rate": 0.976,
                    "value_tier": "Medium Value"
                }
            """
            try:
                LOGGER.info(f"Predicting CLV for customer {customer_id} from dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                customer_data = self._read_csv_data(dataset_path)
                
                # Find the specific customer
                target_customer = None
                for customer in customer_data:
                    if customer.get('CustomerID') == customer_id:
                        target_customer = customer
                        break
                
                if not target_customer:
                    return {
                        "error": f"Customer '{customer_id}' not found in dataset",
                        "total_clv": 0
                    }
                
                result = predict_customer_lifetime_value(target_customer, projection_months)
                
                LOGGER.info(f"CLV prediction complete for {customer_id}: ${result.get('total_clv', 0):.2f}")
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "total_clv": 0}
            except Exception as e:
                LOGGER.error(f"Error predicting CLV: {e}")
                return {"error": str(e), "total_clv": 0}

        # ------------------------------------------------------------------
        # Tool 4: Analyze Sentiment Trends
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def analyze_sentiment_trends(
            dataset_id: str,
            forecast_periods: int = 3,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Analyze social media sentiment trends, detect anomalies, and forecast future sentiment.
            
            Calculates net sentiment scores from positive/negative/neutral mentions,
            identifies significant sentiment drops, and projects future trends.
            
            Args:
                dataset_id: The ID of sentiment dataset (must include Month, PositiveMentions, NegativeMentions, NeutralMentions)
                forecast_periods: Number of periods to forecast (default: 3)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with sentiment scores, trends, anomaly detection, forecasts,
                and actionable recommendations.
                
            Example:
                {
                    "total_periods": 7,
                    "current_sentiment": 0.616,
                    "average_sentiment": 0.484,
                    "assessment": "Positive",
                    "anomalies": [
                        {
                            "month": "June",
                            "net_sentiment": 0.321,
                            "change_percentage": -33.6,
                            "severity": "Critical"
                        }
                    ],
                    "forecast": [
                        {"period": 1, "forecasted_sentiment": 0.650, "trend": "Improving"}
                    ],
                    "recommendations": [...]
                }
            """
            try:
                LOGGER.info(f"Analyzing sentiment trends for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                sentiment_data = self._read_csv_data(dataset_path)
                
                result = analyze_sentiment_trends(sentiment_data, forecast_periods)
                
                LOGGER.info(
                    f"Sentiment analysis complete: {result.get('anomaly_count', 0)} anomalies detected, "
                    f"current sentiment: {result.get('current_sentiment', 0):.3f}"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "trends": []}
            except Exception as e:
                LOGGER.error(f"Error analyzing sentiment: {e}")
                return {"error": str(e), "trends": []}

        LOGGER.info(f"Registered {self.tool_count} customer analytics tools")
