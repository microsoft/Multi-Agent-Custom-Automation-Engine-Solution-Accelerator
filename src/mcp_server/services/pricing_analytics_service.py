"""Pricing Analytics MCP tools for competitive analysis, discount optimization, and revenue forecasting."""

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
from common.utils.pricing_analytics import (
    analyze_competitive_pricing,
    optimize_discount_strategy,
    forecast_revenue_by_category,
)

LOGGER = logging.getLogger(__name__)

METADATA_FILENAME = "metadata.json"


def _sanitize_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)


class PricingAnalyticsService(MCPToolBase):
    """Tools for competitive pricing analysis, discount optimization, and revenue forecasting."""

    def __init__(self, dataset_root: Optional[Path] = None):
        super().__init__(Domain.PRICING)
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
        return 3

    def register_tools(self, mcp: Any) -> None:
        """Register all pricing analytics tools with the MCP server."""

        # ------------------------------------------------------------------
        # Tool 1: Competitive Price Analysis
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def competitive_price_analysis(
            pricing_dataset_id: str,
            product_dataset_id: Optional[str] = None,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Analyze competitive pricing gaps and provide pricing recommendations.
            
            Compares your prices against competitor prices, identifies categories that are
            overpriced or underpriced, and recommends optimal pricing strategies.
            
            Args:
                pricing_dataset_id: Dataset with ProductCategory, ContosoAveragePrice, CompetitorAveragePrice
                product_dataset_id: Optional dataset with ReturnRate for additional insights
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with price gap analysis, competitive positioning, and pricing recommendations.
                
            Example:
                {
                    "total_categories": 4,
                    "avg_price_gap_percent": 10.5,
                    "overpriced_categories": 2,
                    "underpriced_categories": 1,
                    "overall_strategy": "Price Reduction Focus",
                    "category_analysis": [
                        {
                            "category": "Dresses",
                            "our_price": 120.00,
                            "competitor_price": 100.00,
                            "price_gap_percent": 20.0,
                            "positioning": "Overpriced",
                            "suggested_price": 105.00,
                            "recommendation": "URGENT: Reduce price by ~15% to regain competitiveness..."
                        }
                    ],
                    "top_priority_actions": [...]
                }
            """
            try:
                LOGGER.info(f"Analyzing competitive pricing for dataset {pricing_dataset_id}")
                
                # Read pricing data
                pricing_path = self._get_dataset_path(pricing_dataset_id, user_id)
                pricing_data = self._read_csv_data(pricing_path)
                
                # Read product data if provided
                product_data = None
                if product_dataset_id:
                    try:
                        product_path = self._get_dataset_path(product_dataset_id, user_id)
                        product_data = self._read_csv_data(product_path)
                    except FileNotFoundError:
                        LOGGER.warning(f"Product dataset {product_dataset_id} not found, continuing without return rate data")
                
                result = analyze_competitive_pricing(pricing_data, product_data)
                
                LOGGER.info(
                    f"Competitive pricing analysis complete: {result.get('total_categories', 0)} categories analyzed, "
                    f"avg gap: {result.get('avg_price_gap_percent', 0):.1f}%"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{pricing_dataset_id}' not found", "analysis": []}
            except Exception as e:
                LOGGER.error(f"Error analyzing competitive pricing: {e}")
                return {"error": str(e), "analysis": []}

        # ------------------------------------------------------------------
        # Tool 2: Optimize Discount Strategy
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def optimize_discount_strategy(
            dataset_id: str,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Optimize discount strategy based on historical purchase patterns.
            
            Analyzes how different discount levels impact order value and revenue,
            identifies optimal discount ranges, and provides recommendations to
            maximize revenue while maintaining customer acquisition.
            
            Args:
                dataset_id: Purchase history dataset (must include TotalAmount, DiscountApplied)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with discount effectiveness analysis, optimal discount range,
                and ROI recommendations.
                
            Example:
                {
                    "total_orders": 7,
                    "orders_with_discount": 6,
                    "discount_penetration": 85.7,
                    "optimal_discount_range": "Small (1-10%)",
                    "bucket_analysis": [
                        {
                            "discount_level": "Small (1-10%)",
                            "order_count": 3,
                            "avg_order_value": 120.00,
                            "total_revenue": 360.00,
                            "revenue_share": 32.1
                        }
                    ],
                    "recommendations": [
                        {
                            "priority": "High",
                            "finding": "'Small (1-10%)' discount range has highest ROI",
                            "recommendation": "Focus promotions in this range - avg order value: $120.00"
                        }
                    ]
                }
            """
            try:
                LOGGER.info(f"Optimizing discount strategy for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                purchase_data = self._read_csv_data(dataset_path)
                
                result = optimize_discount_strategy(purchase_data)
                
                LOGGER.info(
                    f"Discount optimization complete: {result.get('total_orders', 0)} orders analyzed, "
                    f"optimal range: {result.get('optimal_discount_range', 'N/A')}"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "recommendations": []}
            except Exception as e:
                LOGGER.error(f"Error optimizing discount strategy: {e}")
                return {"error": str(e), "recommendations": []}

        # ------------------------------------------------------------------
        # Tool 3: Forecast Revenue by Category
        # ------------------------------------------------------------------
        @mcp.tool(tags={self.domain.value})
        def forecast_revenue_by_category(
            dataset_id: str,
            periods: int = 6,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Forecast revenue by product category with confidence intervals.
            
            Analyzes historical purchase patterns by category and generates
            forward-looking revenue forecasts with confidence bands.
            
            Args:
                dataset_id: Purchase history dataset (must include ItemsPurchased, TotalAmount)
                periods: Number of periods to forecast (default: 6)
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with category-level revenue forecasts, confidence intervals,
                and growth projections.
                
            Example:
                {
                    "total_categories": 5,
                    "total_historical_revenue": 1120.00,
                    "forecast_periods": 6,
                    "category_forecasts": [
                        {
                            "category": "Dresses",
                            "historical_orders": 2,
                            "historical_total_revenue": 450.00,
                            "historical_avg_revenue_per_order": 225.00,
                            "forecast": [236.25, 248.06, 260.47, 273.49, 287.17, 301.52],
                            "lower_bound": [200.81, 210.85, 221.40, 232.47, 244.09, 256.29],
                            "upper_bound": [271.69, 285.27, 299.54, 314.51, 330.24, 346.75],
                            "projected_growth_rate": 0.05
                        }
                    ],
                    "methodology": "Simple growth projection with 5% assumed growth rate"
                }
            """
            try:
                LOGGER.info(f"Forecasting revenue by category for dataset {dataset_id}")
                
                dataset_path = self._get_dataset_path(dataset_id, user_id)
                purchase_data = self._read_csv_data(dataset_path)
                
                result = forecast_revenue_by_category(purchase_data, periods)
                
                LOGGER.info(
                    f"Revenue forecast complete: {result.get('total_categories', 0)} categories, "
                    f"{periods} periods, total historical revenue: ${result.get('total_historical_revenue', 0):.2f}"
                )
                return result
                
            except FileNotFoundError as e:
                LOGGER.error(f"Dataset not found: {e}")
                return {"error": f"Dataset '{dataset_id}' not found", "forecasts": []}
            except Exception as e:
                LOGGER.error(f"Error forecasting revenue: {e}")
                return {"error": str(e), "forecasts": []}

        LOGGER.info(f"Registered {self.tool_count} pricing analytics tools")



