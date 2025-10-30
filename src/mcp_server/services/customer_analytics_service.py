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
        
        # Try specified user first
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # Search across all users
        LOGGER.info(f"Metadata for dataset {dataset_id} not found for user {user_id}, searching all users...")
        for user_dir in self.dataset_root.iterdir():
            if not user_dir.is_dir():
                continue
            candidate_metadata = self._metadata_path({"user_id": user_dir.name, "dataset_id": dataset_id})
            if candidate_metadata.exists():
                LOGGER.info(f"Found metadata for dataset {dataset_id} under user {user_dir.name}")
                with open(candidate_metadata, "r", encoding="utf-8") as f:
                    return json.load(f)
        
        raise FileNotFoundError(f"No metadata found for dataset '{dataset_id}'")

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
        return 8

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

        # ------------------------------------------------------------------
        # Tool 5: Analyze Customer Journey
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def analyze_customer_journey(
            dataset_id: str,
            customer_id: Optional[str] = None,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Analyze customer journey stages and identify drop-off points.
            
            Examines customer touchpoints, engagement patterns, and identifies
            where customers are most likely to churn or disengage.
            
            Args:
                dataset_id: The ID of customer journey dataset (must include CustomerID, Stage, Timestamp, Conversion)
                customer_id: Optional specific customer ID to analyze
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with journey analysis, stage performance, drop-off points, and recommendations.
            """
            try:
                LOGGER.info(f"Analyzing customer journey for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                journey_data = self._read_csv_data(dataset_path)
                
                if customer_id:
                    journey_data = [j for j in journey_data if j.get('CustomerID') == customer_id]
                    if not journey_data:
                        return {"error": f"Customer '{customer_id}' not found in dataset", "stages": []}
                
                # Analyze journey stages
                stages = {}
                total_customers = len(set(j.get('CustomerID', '') for j in journey_data))
                
                for record in journey_data:
                    stage = record.get('Stage', '')
                    if stage not in stages:
                        stages[stage] = {
                            "stage": stage,
                            "customer_count": 0,
                            "conversion_count": 0,
                            "drop_off_count": 0
                        }
                    
                    customer_id_val = record.get('CustomerID', '')
                    if customer_id_val:
                        stages[stage]["customer_count"] += 1
                        
                        conversion = record.get('Conversion', '').lower()
                        if conversion in ['true', '1', 'yes', 'completed']:
                            stages[stage]["conversion_count"] += 1
                        elif conversion in ['false', '0', 'no', 'dropped']:
                            stages[stage]["drop_off_count"] += 1
                
                # Calculate conversion rates
                stage_analysis = []
                for stage, data in stages.items():
                    conversion_rate = (data["conversion_count"] / data["customer_count"] * 100) if data["customer_count"] > 0 else 0
                    drop_off_rate = (data["drop_off_count"] / data["customer_count"] * 100) if data["customer_count"] > 0 else 0
                    
                    stage_analysis.append({
                        "stage": stage,
                        "customers_reached": data["customer_count"],
                        "conversions": data["conversion_count"],
                        "drop_offs": data["drop_off_count"],
                        "conversion_rate": round(conversion_rate, 2),
                        "drop_off_rate": round(drop_off_rate, 2),
                        "priority": "High" if drop_off_rate > 30 else "Medium" if drop_off_rate > 15 else "Low"
                    })
                
                # Sort by drop-off rate
                stage_analysis.sort(key=lambda x: x["drop_off_rate"], reverse=True)
                
                return {
                    "total_customers": total_customers,
                    "customer_id": customer_id or "All",
                    "stages": stage_analysis,
                    "highest_drop_off_stage": stage_analysis[0]["stage"] if stage_analysis else None,
                    "recommendations": [
                        f"Focus on improving {s['stage']} stage (drop-off rate: {s['drop_off_rate']:.1f}%)"
                        for s in stage_analysis[:3] if s["drop_off_rate"] > 10
                    ]
                }
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "stages": []}
            except Exception as e:
                LOGGER.error(f"Error analyzing customer journey: {e}")
                return {"error": str(e), "stages": []}

        # ------------------------------------------------------------------
        # Tool 6: Predict Churn Risk
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def predict_churn_risk(
            dataset_id: str,
            customer_id: Optional[str] = None,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Predict churn risk for individual customers or segments.
            
            Uses customer behavior patterns to assess churn probability
            and recommend retention strategies.
            
            Args:
                dataset_id: The ID of customer profile dataset
                customer_id: Optional specific customer ID to analyze
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with churn risk scores, predictions, and retention recommendations.
            """
            try:
                LOGGER.info(f"Predicting churn risk for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                customer_data = self._read_csv_data(dataset_path)
                
                if customer_id:
                    customer_data = [c for c in customer_data if c.get('CustomerID') == customer_id]
                    if not customer_data:
                        return {"error": f"Customer '{customer_id}' not found in dataset", "risk_scores": []}
                
                risk_scores = []
                for customer in customer_data:
                    total_spend = float(customer.get('TotalSpend', 0) or 0)
                    membership_duration = float(customer.get('MembershipDuration', 0) or 0)
                    avg_monthly_spend = float(customer.get('AvgMonthlySpend', 0) or 0)
                    
                    # Simple risk scoring algorithm
                    risk_score = 0.5  # Base risk
                    
                    # Higher spend = lower risk
                    if total_spend > 5000:
                        risk_score -= 0.2
                    elif total_spend < 1000:
                        risk_score += 0.2
                    
                    # Longer membership = lower risk
                    if membership_duration > 24:
                        risk_score -= 0.15
                    elif membership_duration < 6:
                        risk_score += 0.15
                    
                    # Consistent spending = lower risk
                    if avg_monthly_spend > 100:
                        risk_score -= 0.1
                    elif avg_monthly_spend < 50:
                        risk_score += 0.1
                    
                    risk_score = max(0.0, min(1.0, risk_score))
                    
                    risk_tier = "Low" if risk_score < 0.3 else "Medium" if risk_score < 0.6 else "High"
                    
                    risk_scores.append({
                        "customer_id": customer.get('CustomerID', ''),
                        "customer_name": customer.get('CustomerName', ''),
                        "risk_score": round(risk_score, 3),
                        "risk_tier": risk_tier,
                        "retention_strategy": "Maintain engagement" if risk_tier == "Low" else "Provide incentives" if risk_tier == "Medium" else "Urgent intervention needed"
                    })
                
                # Sort by risk score
                risk_scores.sort(key=lambda x: x["risk_score"], reverse=True)
                
                return {
                    "total_customers": len(risk_scores),
                    "high_risk_count": len([r for r in risk_scores if r["risk_tier"] == "High"]),
                    "medium_risk_count": len([r for r in risk_scores if r["risk_tier"] == "Medium"]),
                    "low_risk_count": len([r for r in risk_scores if r["risk_tier"] == "Low"]),
                    "risk_scores": risk_scores[:50],  # Limit to top 50
                    "recommendations": [
                        "Focus retention efforts on high-risk customers",
                        "Implement win-back campaigns for medium-risk segments",
                        "Maintain engagement programs for low-risk customers"
                    ]
                }
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "risk_scores": []}
            except Exception as e:
                LOGGER.error(f"Error predicting churn risk: {e}")
                return {"error": str(e), "risk_scores": []}

        # ------------------------------------------------------------------
        # Tool 7: Get Customer Retention Metrics
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def get_retention_metrics(
            dataset_id: str,
            period_months: int = 12,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Calculate customer retention metrics and cohort analysis.
            
            Computes retention rates, cohort performance, and identifies
            trends in customer retention over time.
            
            Args:
                dataset_id: The ID of customer profile dataset
                period_months: Number of months to analyze (default: 12)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with retention rates, cohort metrics, and trend analysis.
            """
            try:
                LOGGER.info(f"Calculating retention metrics for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                customer_data = self._read_csv_data(dataset_path)
                
                # Calculate overall retention rate
                total_customers = len(customer_data)
                active_customers = len([c for c in customer_data if float(c.get('MembershipDuration', 0) or 0) > 0])
                retention_rate = (active_customers / total_customers * 100) if total_customers > 0 else 0
                
                # Calculate average lifetime
                lifetimes = [float(c.get('MembershipDuration', 0) or 0) for c in customer_data]
                avg_lifetime = sum(lifetimes) / len(lifetimes) if lifetimes else 0
                
                # Calculate churn rate
                churn_rate = 100 - retention_rate
                
                return {
                    "total_customers": total_customers,
                    "active_customers": active_customers,
                    "retention_rate": round(retention_rate, 2),
                    "churn_rate": round(churn_rate, 2),
                    "average_lifetime_months": round(avg_lifetime, 2),
                    "period_analyzed": period_months,
                    "metrics": {
                        "retention_rate": f"{retention_rate:.1f}%",
                        "churn_rate": f"{churn_rate:.1f}%",
                        "avg_lifetime": f"{avg_lifetime:.1f} months"
                    },
                    "assessment": "Excellent" if retention_rate > 90 else "Good" if retention_rate > 75 else "Needs Improvement",
                    "recommendations": [
                        "Focus on improving retention for customers with < 6 months tenure",
                        "Implement loyalty programs for high-value customers",
                        "Analyze churn drivers to identify improvement opportunities"
                    ]
                }
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "metrics": {}}
            except Exception as e:
                LOGGER.error(f"Error calculating retention metrics: {e}")
                return {"error": str(e), "metrics": {}}

        # ------------------------------------------------------------------
        # Tool 8: Segment by Behavior
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def segment_by_behavior(
            dataset_id: str,
            behavior_attributes: List[str],
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Segment customers based on behavioral attributes.
            
            Creates custom segments based on specified behavioral characteristics
            like purchase frequency, product preferences, engagement levels.
            
            Args:
                dataset_id: The ID of customer profile dataset
                behavior_attributes: List of attributes to use for segmentation (e.g., ["PurchaseFrequency", "ProductCategory"])
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with behavioral segments, characteristics, and targeting strategies.
            """
            try:
                LOGGER.info(f"Segmenting customers by behavior for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                customer_data = self._read_csv_data(dataset_path)
                
                # Validate attributes exist
                if not customer_data:
                    return {"error": "Dataset is empty", "segments": []}
                
                available_columns = list(customer_data[0].keys())
                missing_attributes = [attr for attr in behavior_attributes if attr not in available_columns]
                
                if missing_attributes:
                    return {
                        "error": f"Attributes not found in dataset: {missing_attributes}",
                        "available_attributes": available_columns,
                        "segments": []
                    }
                
                # Create behavioral segments
                segments = {}
                
                for customer in customer_data:
                    # Create segment key based on attribute values
                    segment_key_parts = []
                    for attr in behavior_attributes:
                        value = customer.get(attr, '')
                        segment_key_parts.append(f"{attr}:{value}")
                    
                    segment_key = "|".join(segment_key_parts)
                    
                    if segment_key not in segments:
                        segments[segment_key] = {
                            "segment_key": segment_key,
                            "attributes": {attr: customer.get(attr, '') for attr in behavior_attributes},
                            "customers": [],
                            "count": 0,
                            "total_value": 0
                        }
                    
                    segments[segment_key]["customers"].append(customer.get('CustomerID', ''))
                    segments[segment_key]["count"] += 1
                    
                    total_spend = float(customer.get('TotalSpend', 0) or 0)
                    segments[segment_key]["total_value"] += total_spend
                
                # Format segments
                segment_list = []
                for segment_key, segment_data in segments.items():
                    avg_value = segment_data["total_value"] / segment_data["count"] if segment_data["count"] > 0 else 0
                    segment_list.append({
                        "segment": segment_data["segment_key"],
                        "customer_count": segment_data["count"],
                        "total_value": round(segment_data["total_value"], 2),
                        "avg_value_per_customer": round(avg_value, 2),
                        "attributes": segment_data["attributes"],
                        "targeting_strategy": f"Customize messaging for {segment_data['count']} customers with this behavior profile"
                    })
                
                # Sort by value
                segment_list.sort(key=lambda x: x["total_value"], reverse=True)
                
                return {
                    "total_segments": len(segment_list),
                    "total_customers": len(customer_data),
                    "behavior_attributes": behavior_attributes,
                    "segments": segment_list,
                    "recommendations": [
                        f"Top segment has {segment_list[0]['customer_count']} customers worth ${segment_list[0]['total_value']:.2f}",
                        "Consider creating targeted campaigns for each behavioral segment",
                        "Analyze purchase patterns to refine segmentation further"
                    ]
                }
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "segments": []}
            except Exception as e:
                LOGGER.error(f"Error segmenting by behavior: {e}")
                return {"error": str(e), "segments": []}

        LOGGER.info(f"Registered {self.tool_count} customer analytics tools")
