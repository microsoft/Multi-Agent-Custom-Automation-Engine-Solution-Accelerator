"""Operations Analytics MCP tools for delivery performance, inventory optimization, and incident analysis."""

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
from common.utils.operations_analytics import (
    analyze_delivery_performance,
    forecast_delivery_metrics,
    analyze_warehouse_incidents,
    optimize_inventory,
)

LOGGER = logging.getLogger(__name__)

METADATA_FILENAME = "metadata.json"


def _sanitize_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)


class OperationsAnalyticsService(MCPToolBase):
    """Tools for delivery performance forecasting, inventory optimization, and warehouse incident analysis."""

    def __init__(self, dataset_root: Optional[Path] = None):
        super().__init__(Domain.OPERATIONS)
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
        """Register all operations analytics tools with the MCP server."""

        # ------------------------------------------------------------------
        # Tool 1: Forecast Delivery Performance
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def forecast_delivery_performance(
            dataset_id: str,
            periods: int = 3,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Forecast delivery performance metrics and analyze historical trends.
            
            Analyzes delivery time, on-time rate, and customer complaints to identify
            performance degradation, calculate trends, and forecast future metrics.
            
            Args:
                dataset_id: The ID of delivery performance dataset (must include Month, AverageDeliveryTime, OnTimeDeliveryRate, CustomerComplaints)
                periods: Number of periods to forecast (default: 3)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with historical analysis, performance trends, degradation periods,
                forecasted metrics, and improvement recommendations.
                
            Example:
                {
                    "historical_analysis": {
                        "total_periods": 7,
                        "current_performance": {"score": 96.5, "grade": "A"},
                        "best_period": {...},
                        "worst_period": {...},
                        "trends": {
                            "delivery_time": "Improving",
                            "on_time_rate": "Improving",
                            "complaints": "Decreasing"
                        },
                        "degradation_periods": [...]
                    },
                    "forecast": {
                        "forecast_periods": 3,
                        "forecast": [
                            {"period": 1, "avg_delivery_time": 2.9, "on_time_rate": 97.5, ...}
                        ]
                    },
                    "recommendations": [...]
                }
            """
            try:
                LOGGER.info(f"Forecasting delivery performance for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                delivery_data = self._read_csv_data(dataset_path)
                
                # Analyze historical performance
                historical_analysis = analyze_delivery_performance(delivery_data)
                
                # Generate forecast
                forecast_result = forecast_delivery_metrics(delivery_data, periods)
                
                result = {
                    "historical_analysis": historical_analysis,
                    "forecast": forecast_result,
                    "recommendations": historical_analysis.get('recommendations', [])
                }
                
                LOGGER.info(
                    f"Delivery performance analysis complete: "
                    f"Current score: {historical_analysis.get('current_performance', {}).get('score', 0):.1f}, "
                    f"Forecast {periods} periods"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "forecast": []}
            except Exception as e:
                LOGGER.error(f"Error forecasting delivery performance: {e}")
                return {"error": str(e), "forecast": []}

        # ------------------------------------------------------------------
        # Tool 2: Optimize Inventory
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def optimize_inventory(
            dataset_id: str,
            target_service_level: float = 0.95,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Optimize inventory levels based on historical purchase patterns.
            
            Calculates recommended stock levels, reorder points, and safety stock for each
            product using demand analysis and target service level requirements.
            
            Args:
                dataset_id: The ID of purchase history dataset (must include ItemsPurchased, TotalAmount)
                target_service_level: Desired service level (0.0-1.0, default: 0.95 = 95%)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with inventory recommendations by item, including stock levels,
                reorder points, safety stock, and revenue priority.
                
            Example:
                {
                    "total_items": 12,
                    "target_service_level": 0.95,
                    "total_recommended_stock_units": 45,
                    "recommendations": [
                        {
                            "item": "Summer Floral Dress",
                            "historical_demand": 1,
                            "recommended_stock_level": 2,
                            "reorder_point": 2,
                            "safety_stock": 1,
                            "revenue_contribution": 150.00,
                            "priority": "Medium"
                        },
                        ...
                    ],
                    "methodology": "Newsvendor model with 95.0% service level target"
                }
            """
            try:
                LOGGER.info(f"Optimizing inventory for dataset {dataset_id} with service level {target_service_level}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                purchase_data = self._read_csv_data(dataset_path)
                
                result = optimize_inventory(purchase_data, target_service_level)
                
                LOGGER.info(
                    f"Inventory optimization complete: {result.get('total_items', 0)} items analyzed, "
                    f"{result.get('total_recommended_stock_units', 0)} total stock units recommended"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "recommendations": []}
            except Exception as e:
                LOGGER.error(f"Error optimizing inventory: {e}")
                return {"error": str(e), "recommendations": []}

        # ------------------------------------------------------------------
        # Tool 3: Analyze Warehouse Incidents
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def analyze_warehouse_incidents(
            dataset_id: str,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Analyze warehouse incidents for impact assessment and risk management.
            
            Categorizes incidents, calculates severity based on affected orders,
            and provides recommendations for mitigation and prevention.
            
            Args:
                dataset_id: The ID of incident dataset (must include Date, IncidentDescription, AffectedOrders)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with incident analysis, severity rankings, impact assessment,
                and risk mitigation recommendations.
                
            Example:
                {
                    "total_incidents": 3,
                    "total_affected_orders": 500,
                    "incidents": [
                        {
                            "date": "2023-07-18",
                            "description": "Logistics partner strike",
                            "category": "External",
                            "affected_orders": 250,
                            "severity": "Critical",
                            "impact_score": 10
                        },
                        ...
                    ],
                    "most_severe_incident": {...},
                    "incident_categories": ["External", "Infrastructure", "Systems"],
                    "recommendations": [...],
                    "risk_level": "High"
                }
            """
            try:
                LOGGER.info(f"Analyzing warehouse incidents for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                incident_data = self._read_csv_data(dataset_path)
                
                result = analyze_warehouse_incidents(incident_data)
                
                LOGGER.info(
                    f"Incident analysis complete: {result.get('total_incidents', 0)} incidents, "
                    f"{result.get('total_affected_orders', 0)} orders affected, "
                    f"risk level: {result.get('risk_level', 'Unknown')}"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "incidents": []}
            except Exception as e:
                LOGGER.error(f"Error analyzing incidents: {e}")
                return {"error": str(e), "incidents": []}

        # ------------------------------------------------------------------
        # Tool 4: Get Operations Summary
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def get_operations_summary(
            delivery_dataset_id: str,
            incident_dataset_id: str,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Generate comprehensive operations summary combining delivery and incident data.
            
            Provides high-level overview of operational health, combining delivery performance
            metrics with incident impact analysis for executive reporting.
            
            Args:
                delivery_dataset_id: The ID of delivery performance dataset
                incident_dataset_id: The ID of warehouse incident dataset
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with overall operations health score, key metrics,
                and critical issues requiring attention.
                
            Example:
                {
                    "operations_health_score": 82.3,
                    "health_grade": "B",
                    "delivery_summary": {
                        "current_performance_score": 96.5,
                        "trend": "Improving"
                    },
                    "incident_summary": {
                        "total_incidents": 3,
                        "risk_level": "High"
                    },
                    "critical_issues": [...],
                    "overall_status": "Good with some concerns"
                }
            """
            try:
                LOGGER.info(f"Generating operations summary for delivery:{delivery_dataset_id}, incidents:{incident_dataset_id}")
                
                # Get delivery data
                delivery_path = self._get_dataset_path(delivery_dataset_id, user_id)
                delivery_data = self._read_csv_data(delivery_path)
                delivery_analysis = analyze_delivery_performance(delivery_data)
                
                # Get incident data
                incident_path = self._get_dataset_path(incident_dataset_id, user_id)
                incident_data = self._read_csv_data(incident_path)
                incident_analysis = analyze_warehouse_incidents(incident_data)
                
                # Calculate overall health score
                delivery_score = delivery_analysis.get('current_performance', {}).get('score', 0)
                
                # Incident penalty (reduce score based on incident severity)
                incident_penalty = min(20, incident_analysis.get('total_affected_orders', 0) / 25)
                
                health_score = max(0, delivery_score - incident_penalty)
                
                # Determine health grade
                if health_score >= 90:
                    health_grade = "A"
                    status = "Excellent"
                elif health_score >= 80:
                    health_grade = "B"
                    status = "Good"
                elif health_score >= 70:
                    health_grade = "C"
                    status = "Fair"
                elif health_score >= 60:
                    health_grade = "D"
                    status = "Poor"
                else:
                    health_grade = "F"
                    status = "Critical"
                
                # Collect critical issues
                critical_issues = []
                
                # Add delivery issues
                if delivery_analysis.get('degradation_periods'):
                    critical_issues.append({
                        "category": "Delivery",
                        "issue": f"{len(delivery_analysis['degradation_periods'])} performance degradation periods detected",
                        "severity": "High"
                    })
                
                # Add incident issues
                if incident_analysis.get('risk_level') == "High":
                    critical_issues.append({
                        "category": "Incidents",
                        "issue": f"{incident_analysis.get('total_affected_orders', 0)} orders affected by warehouse incidents",
                        "severity": "High"
                    })
                
                result = {
                    "operations_health_score": round(health_score, 2),
                    "health_grade": health_grade,
                    "overall_status": status,
                    "delivery_summary": {
                        "current_performance_score": delivery_score,
                        "grade": delivery_analysis.get('current_performance', {}).get('grade', 'Unknown'),
                        "avg_delivery_time": delivery_analysis.get('current_performance', {}).get('avg_delivery_time', 0),
                        "on_time_rate": delivery_analysis.get('current_performance', {}).get('on_time_rate', 0),
                        "trend": delivery_analysis.get('trends', {}).get('delivery_time', 'Unknown')
                    },
                    "incident_summary": {
                        "total_incidents": incident_analysis.get('total_incidents', 0),
                        "total_affected_orders": incident_analysis.get('total_affected_orders', 0),
                        "risk_level": incident_analysis.get('risk_level', 'Unknown'),
                        "most_severe": incident_analysis.get('most_severe_incident')
                    },
                    "critical_issues": critical_issues,
                    "recommendations": (
                        delivery_analysis.get('recommendations', [])[:2] +
                        incident_analysis.get('recommendations', [])[:2]
                    )
                }
                
                LOGGER.info(f"Operations summary complete: Health score {health_score:.1f} ({health_grade})")
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": str(e), "operations_health_score": 0}
            except Exception as e:
                LOGGER.error(f"Error generating operations summary: {e}")
                return {"error": str(e), "operations_health_score": 0}

        LOGGER.info(f"Registered {self.tool_count} operations analytics tools")

