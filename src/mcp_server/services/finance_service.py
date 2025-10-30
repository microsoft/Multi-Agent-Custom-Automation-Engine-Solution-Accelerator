"""Finance-focused MCP tools for forecasting and dataset preparation."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from core.factory import Domain, MCPToolBase
from common.utils.dataset_utils import (
    detect_numeric_columns,
    read_preview,
    simple_linear_forecast,
    summarize_numeric_series,
    extract_numeric_series,
)
from common.utils.advanced_forecasting import (
    sarima_forecast,
    exponential_smoothing_forecast,
    prophet_forecast,
    linear_forecast_with_confidence,
    auto_select_forecast_method,
    evaluate_forecast_accuracy,
)

LOGGER = logging.getLogger(__name__)

METADATA_FILENAME = "metadata.json"


def _sanitize_identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)


class FinanceService(MCPToolBase):
    """Tools that operate on uploaded financial datasets."""

    def __init__(self, dataset_root: Optional[Path] = None):
        super().__init__(Domain.FINANCE)
        default_root = Path(__file__).resolve().parents[3] / "data" / "uploads"
        self.dataset_root = dataset_root or default_root
        self.dataset_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    def _metadata_path(self, metadata: Dict[str, str]) -> Path:
        user_folder = _sanitize_identifier(metadata.get("user_id", ""))
        dataset_folder = _sanitize_identifier(metadata.get("dataset_id", ""))
        return self.dataset_root / user_folder / dataset_folder / METADATA_FILENAME

    def _dataset_file(self, metadata: Dict[str, str]) -> Optional[Path]:
        user_folder = _sanitize_identifier(metadata.get("user_id", ""))
        dataset_folder = _sanitize_identifier(metadata.get("dataset_id", ""))
        stored_filename = metadata.get("stored_filename")
        if not stored_filename:
            return None

        file_path = self.dataset_root / user_folder / dataset_folder / stored_filename
        return file_path if file_path.exists() else None

    def _iter_metadata(self) -> Iterable[Dict[str, Any]]:
        for user_dir in self.dataset_root.iterdir():
            if not user_dir.is_dir():
                continue
            for dataset_dir in user_dir.iterdir():
                if not dataset_dir.is_dir():
                    continue
                metadata_file = dataset_dir / METADATA_FILENAME
                if not metadata_file.exists():
                    continue
                try:
                    yield json.loads(metadata_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    LOGGER.warning("Failed to parse metadata %s: %s", metadata_file, exc)

    def _get_metadata(self, dataset_id: str, user_id: str = "default") -> Dict[str, Any]:
        """Get metadata for a dataset. Searches across all users if not found for specified user."""
        user_folder = _sanitize_identifier(user_id)
        dataset_folder = _sanitize_identifier(dataset_id)
        metadata_path = self.dataset_root / user_folder / dataset_folder / METADATA_FILENAME
        
        # Try specified user first
        if metadata_path.exists():
            try:
                return json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                LOGGER.warning("Failed to parse metadata %s: %s", metadata_path, exc)
        
        # Search across all users
        LOGGER.info(f"Metadata for dataset {dataset_id} not found for user {user_id}, searching all users...")
        for user_dir in self.dataset_root.iterdir():
            if not user_dir.is_dir():
                continue
            candidate_metadata = user_dir / dataset_folder / METADATA_FILENAME
            if candidate_metadata.exists():
                try:
                    LOGGER.info(f"Found metadata for dataset {dataset_id} under user {user_dir.name}")
                    return json.loads(candidate_metadata.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    LOGGER.warning("Failed to parse metadata %s: %s", candidate_metadata, exc)
        
        raise FileNotFoundError(f"No metadata found for dataset '{dataset_id}'")

    def _find_metadata(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        target = dataset_id.strip()
        for metadata in self._iter_metadata():
            if metadata.get("dataset_id") == target:
                return metadata
        return None

    def _summarize_numeric_columns(
        self, dataset_path: Path, numeric_columns: List[str]
    ) -> Dict[str, Dict[str, float]]:
        summaries: Dict[str, Dict[str, float]] = {}
        for column in numeric_columns:
            try:
                values, _ = extract_numeric_series(dataset_path, column)
                summaries[column] = summarize_numeric_series(values)
            except ValueError:
                continue
        return summaries

    # ------------------------------------------------------------------
    # MCP tools
    def register_tools(self, mcp) -> None:  # pragma: no cover - decoration
        @mcp.tool(tags={self.domain.value})
        def list_finance_datasets(limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
            """Return available uploaded datasets for forecasting workflows."""

            datasets: List[Dict[str, Any]] = []
            for metadata in self._iter_metadata():
                datasets.append(
                    {
                        "dataset_id": metadata.get("dataset_id"),
                        "original_filename": metadata.get("original_filename"),
                        "uploaded_at": metadata.get("uploaded_at"),
                        "size_bytes": metadata.get("size_bytes"),
                        "numeric_columns": metadata.get("numeric_columns", []),
                    }
                )
                if len(datasets) >= limit:
                    break

            if not datasets:
                return {
                    "message": "No datasets have been uploaded yet. Ask the user to upload a CSV or XLSX file before forecasting.",
                    "datasets": [],
                }

            return {"datasets": datasets}

        @mcp.tool(tags={self.domain.value})
        def summarize_financial_dataset(dataset_id: str) -> Dict[str, Any]:
            """Provide a preview and numeric summary for a dataset."""

            metadata = self._find_metadata(dataset_id)
            if not metadata:
                return {"error": f"Dataset '{dataset_id}' was not found."}

            dataset_path = self._dataset_file(metadata)
            if not dataset_path:
                return {"error": f"Dataset file for '{dataset_id}' is missing."}

            try:
                columns, preview = read_preview(dataset_path)
                numeric_columns = metadata.get("numeric_columns") or detect_numeric_columns(dataset_path)
                numeric_summary = self._summarize_numeric_columns(dataset_path, numeric_columns[:3])

                return {
                    "dataset_id": dataset_id,
                    "original_filename": metadata.get("original_filename"),
                    "columns": columns,
                    "numeric_columns": numeric_columns,
                    "preview": preview,
                    "numeric_summary": numeric_summary,
                }
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to summarize dataset %s", dataset_id)
                return {"error": f"Unable to summarize dataset: {exc}"}

        @mcp.tool(tags={self.domain.value})
        def generate_financial_forecast(
            dataset_id: str,
            target_column: str,
            periods: int = 3,
            method: str = "auto",
            confidence_level: float = 0.95,
        ) -> Dict[str, Any]:
            """Create a forward forecast for the chosen numeric column using advanced methods.
            
            Args:
                dataset_id: Unique identifier for the dataset
                target_column: Column name to forecast
                periods: Number of future periods to forecast
                method: Forecasting method - "auto", "linear", "sarima", "prophet", "exponential_smoothing"
                confidence_level: Confidence level for prediction intervals (0-1)
            
            Returns:
                Forecast with confidence bounds, historical summary, and method metadata
            """

            metadata = self._find_metadata(dataset_id)
            if not metadata:
                return {"error": f"Dataset '{dataset_id}' was not found."}

            dataset_path = self._dataset_file(metadata)
            if not dataset_path:
                return {"error": f"Dataset file for '{dataset_id}' is missing."}

            try:
                values, row_count = extract_numeric_series(dataset_path, target_column)
                baseline = summarize_numeric_series(values)

                # Select and run forecasting method
                if method == "auto":
                    forecast_result = auto_select_forecast_method(values, periods, confidence_level)
                elif method == "linear":
                    forecast_result = linear_forecast_with_confidence(values, periods, confidence_level)
                elif method == "sarima":
                    forecast_result = sarima_forecast(values, periods, confidence_level=confidence_level)
                elif method == "prophet":
                    forecast_result = prophet_forecast(values, periods, confidence_level=confidence_level)
                elif method == "exponential_smoothing":
                    forecast_result = exponential_smoothing_forecast(values, periods, confidence_level=confidence_level)
                else:
                    return {"error": f"Unknown forecasting method: {method}. Use 'auto', 'linear', 'sarima', 'prophet', or 'exponential_smoothing'."}

                return {
                    "dataset_id": dataset_id,
                    "target_column": target_column,
                    "row_count": row_count,
                    "historical_summary": baseline,
                    "forecast": forecast_result.get("forecast", []),
                    "lower_bound": forecast_result.get("lower_bound", []),
                    "upper_bound": forecast_result.get("upper_bound", []),
                    "confidence_level": confidence_level,
                    "method_used": forecast_result.get("method", method),
                    "method_metadata": {k: v for k, v in forecast_result.items() if k not in ["forecast", "lower_bound", "upper_bound", "method"]},
                    "notes": f"Forecast generated using {forecast_result.get('method', method)} method. {forecast_result.get('selection_rationale', '')}",
                }
            except ValueError as exc:
                return {"error": str(exc)}
            except ImportError as exc:
                return {"error": f"Required package not installed: {exc}. Install with pip."}
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to forecast dataset %s", dataset_id)
                return {"error": f"Unable to generate forecast: {exc}"}

        @mcp.tool(tags={self.domain.value})
        def evaluate_forecast_models(
            dataset_id: str,
            target_column: str,
            test_size: int = 3,
        ) -> Dict[str, Any]:
            """Evaluate multiple forecasting methods and rank by accuracy.
            
            Splits data into train/test, fits multiple models, and compares performance.
            
            Args:
                dataset_id: Unique identifier for the dataset
                target_column: Column name to evaluate
                test_size: Number of periods to hold out for testing
            
            Returns:
                Ranked list of methods with accuracy metrics (MAE, RMSE, MAPE)
            """

            metadata = self._find_metadata(dataset_id)
            if not metadata:
                return {"error": f"Dataset '{dataset_id}' was not found."}

            dataset_path = self._dataset_file(metadata)
            if not dataset_path:
                return {"error": f"Dataset file for '{dataset_id}' is missing."}

            try:
                values, row_count = extract_numeric_series(dataset_path, target_column)
                
                if len(values) < test_size + 5:
                    return {"error": f"Need at least {test_size + 5} data points for evaluation (have {len(values)})"}
                
                # Split into train/test
                train_values = values[:-test_size]
                test_values = values[-test_size:]
                
                # Test multiple methods
                methods_to_test = ["linear", "exponential_smoothing", "sarima"]
                results = []
                
                for method in methods_to_test:
                    try:
                        if method == "linear":
                            forecast_result = linear_forecast_with_confidence(train_values, test_size)
                        elif method == "exponential_smoothing":
                            forecast_result = exponential_smoothing_forecast(train_values, test_size)
                        elif method == "sarima":
                            forecast_result = sarima_forecast(train_values, test_size)
                        
                        predicted = forecast_result.get("forecast", [])
                        if len(predicted) != test_size:
                            continue
                        
                        # Calculate accuracy metrics
                        metrics = evaluate_forecast_accuracy(test_values, predicted)
                        
                        results.append({
                            "method": method,
                            "mae": metrics["mae"],
                            "rmse": metrics["rmse"],
                            "mape": metrics["mape"],
                            "forecast": predicted,
                        })
                    except Exception as exc:
                        LOGGER.warning("Method %s failed: %s", method, exc)
                        continue
                
                if not results:
                    return {"error": "All forecasting methods failed. Check data quality."}
                
                # Rank by RMSE (lower is better)
                results.sort(key=lambda x: x["rmse"])
                
                return {
                    "dataset_id": dataset_id,
                    "target_column": target_column,
                    "test_size": test_size,
                    "train_size": len(train_values),
                    "actual_test_values": test_values,
                    "ranked_methods": results,
                    "best_method": results[0]["method"],
                    "recommendation": f"Use {results[0]['method']} method for this dataset (lowest RMSE: {results[0]['rmse']:.2f})",
                }
            except ValueError as exc:
                return {"error": str(exc)}
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to evaluate models for dataset %s", dataset_id)
                return {"error": f"Unable to evaluate models: {exc}"}

        @mcp.tool(tags={self.domain.value})
        def prepare_financial_dataset(
            dataset_id: str, target_column: str
        ) -> Dict[str, Any]:
            """Inspect the dataset for missing or non-numeric rows in the target column."""

            metadata = self._find_metadata(dataset_id)
            if not metadata:
                return {"error": f"Dataset '{dataset_id}' was not found."}

            dataset_path = self._dataset_file(metadata)
            if not dataset_path:
                return {"error": f"Dataset file for '{dataset_id}' is missing."}

            total_rows = 0
            missing_values = 0
            non_numeric = 0

            try:
                from common.utils.dataset_utils import iter_tabular_records

                for row in iter_tabular_records(dataset_path):
                    total_rows += 1
                    value = row.get(target_column)
                    if value in (None, ""):
                        missing_values += 1
                        continue
                    try:
                        float(value)
                    except (TypeError, ValueError):
                        non_numeric += 1

                return {
                    "dataset_id": dataset_id,
                    "target_column": target_column,
                    "rows_scanned": total_rows,
                    "missing_values": missing_values,
                    "non_numeric_values": non_numeric,
                    "recommendation": "Consider removing or correcting rows with missing or non-numeric entries before running forecasts.",
                }
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to profile dataset %s", dataset_id)
                return {"error": f"Unable to prepare dataset: {exc}"}

        @mcp.tool(tags={self.domain.value})
        def create_budget_plan(
            dataset_id: str,
            budget_periods: int = 12,
            growth_rate: float = 0.0
        ) -> Dict[str, Any]:
            """Create a budget plan based on historical financial data."""
            metadata = self._find_metadata(dataset_id)
            if not metadata:
                return {"error": f"Dataset '{dataset_id}' was not found."}

            dataset_path = self._dataset_file(metadata)
            if not dataset_path:
                return {"error": f"Dataset file for '{dataset_id}' is missing."}

            try:
                import csv
                values_list = []
                with open(dataset_path, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        for key, value in row.items():
                            try:
                                numeric_val = float(value)
                                values_list.append(numeric_val)
                                break
                            except (ValueError, TypeError):
                                continue
                
                if not values_list:
                    return {"error": "No numeric columns found in dataset"}
                
                baseline_avg = sum(values_list[-6:]) / min(6, len(values_list))
                
                budget = []
                for period in range(1, budget_periods + 1):
                    projected_value = baseline_avg * (1 + growth_rate) ** period
                    budget.append({
                        "period": period,
                        "projected_value": round(projected_value, 2),
                        "growth_applied": round(growth_rate * 100, 2)
                    })
                
                total_budget = sum(p["projected_value"] for p in budget)
                
                return {
                    "dataset_id": dataset_id,
                    "budget_periods": budget_periods,
                    "growth_rate": growth_rate,
                    "baseline_average": round(baseline_avg, 2),
                    "budget_plan": budget,
                    "total_budget": round(total_budget, 2)
                }
            except Exception as exc:
                LOGGER.exception("Failed to create budget plan")
                return {"error": f"Unable to create budget plan: {exc}"}

        @mcp.tool(tags={self.domain.value})
        def analyze_budget_variance(
            actual_dataset_id: str,
            budget_dataset_id: str,
            variance_threshold: float = 0.10
        ) -> Dict[str, Any]:
            """Analyze variance between actual and budgeted financial performance."""
            actual_metadata = self._find_metadata(actual_dataset_id)
            budget_metadata = self._find_metadata(budget_dataset_id)
            
            if not actual_metadata or not budget_metadata:
                return {"error": "One or both datasets not found"}
            
            actual_path = self._dataset_file(actual_metadata)
            budget_path = self._dataset_file(budget_metadata)
            
            if not actual_path or not budget_path:
                return {"error": "One or both dataset files missing"}

            try:
                import csv
                with open(actual_path, "r", encoding="utf-8") as f:
                    actual_data = list(csv.DictReader(f))
                
                with open(budget_path, "r", encoding="utf-8") as f:
                    budget_data = list(csv.DictReader(f))
                
                min_len = min(len(actual_data), len(budget_data))
                variances = []
                
                for i in range(min_len):
                    actual_val = 0
                    budget_val = 0
                    
                    for key in actual_data[i].keys():
                        try:
                            actual_val = float(actual_data[i][key])
                            budget_val = float(budget_data[i][key])
                            break
                        except (ValueError, TypeError, KeyError):
                            continue
                    
                    if budget_val != 0:
                        variance_pct = (actual_val - budget_val) / abs(budget_val)
                        variances.append({
                            "period": i + 1,
                            "actual": round(actual_val, 2),
                            "budget": round(budget_val, 2),
                            "variance": round(actual_val - budget_val, 2),
                            "variance_percent": round(variance_pct * 100, 2),
                            "is_significant": abs(variance_pct) > variance_threshold
                        })
                
                return {
                    "total_periods": len(variances),
                    "variance_threshold": variance_threshold * 100,
                    "variances": variances
                }
            except Exception as exc:
                LOGGER.exception("Failed to analyze budget variance")
                return {"error": f"Unable to analyze variance: {exc}"}

        @mcp.tool(tags={self.domain.value})
        def calculate_financial_ratios(
            dataset_id: str,
            ratio_types: Optional[List[str]] = None
        ) -> Dict[str, Any]:
            """Calculate key financial ratios from dataset."""
            metadata = self._find_metadata(dataset_id)
            if not metadata:
                return {"error": f"Dataset '{dataset_id}' was not found."}

            dataset_path = self._dataset_file(metadata)
            if not dataset_path:
                return {"error": f"Dataset file for '{dataset_id}' is missing."}

            try:
                columns, preview = read_preview(dataset_path)
                numeric_columns = detect_numeric_columns(dataset_path)
                
                ratios = {}
                revenue_col = None
                profit_col = None
                
                for col in columns:
                    col_lower = col.lower()
                    if 'revenue' in col_lower or 'sales' in col_lower:
                        revenue_col = col
                    if 'profit' in col_lower or 'net' in col_lower:
                        profit_col = col
                
                if revenue_col and revenue_col in numeric_columns:
                    values, _ = extract_numeric_series(dataset_path, revenue_col)
                    avg_revenue = sum(values) / len(values) if values else 0
                    
                    if profit_col and profit_col in numeric_columns:
                        profit_values, _ = extract_numeric_series(dataset_path, profit_col)
                        avg_profit = sum(profit_values) / len(profit_values) if profit_values else 0
                        
                        if avg_revenue > 0:
                            profit_margin = (avg_profit / avg_revenue) * 100
                            ratios["profit_margin"] = {
                                "value": round(profit_margin, 2),
                                "unit": "percent"
                            }
                
                return {
                    "dataset_id": dataset_id,
                    "ratios_calculated": list(ratios.keys()),
                    "ratios": ratios
                }
            except Exception as exc:
                LOGGER.exception("Failed to calculate ratios")
                return {"error": f"Unable to calculate ratios: {exc}"}

        @mcp.tool(tags={self.domain.value})
        def forecast_scenario_analysis(
            dataset_id: str,
            target_column: str,
            scenarios: List[Dict[str, Any]],
            periods: int = 3
        ) -> Dict[str, Any]:
            """Run scenario analysis with multiple forecast scenarios."""
            metadata = self._find_metadata(dataset_id)
            if not metadata:
                return {"error": f"Dataset '{dataset_id}' was not found."}

            dataset_path = self._dataset_file(metadata)
            if not dataset_path:
                return {"error": f"Dataset file for '{dataset_id}' is missing."}

            try:
                values, row_count = extract_numeric_series(dataset_path, target_column)
                baseline = summarize_numeric_series(values)
                baseline_avg = baseline.get("mean", 0)
                
                scenario_results = []
                for scenario in scenarios:
                    scenario_name = scenario.get("name", "Unnamed")
                    growth_rate = scenario.get("growth_rate", 0.0)
                    
                    forecast_values = []
                    for period in range(1, periods + 1):
                        forecast_val = baseline_avg * (1 + growth_rate) ** period
                        forecast_values.append(round(forecast_val, 2))
                    
                    scenario_results.append({
                        "scenario_name": scenario_name,
                        "growth_rate": growth_rate,
                        "forecast": forecast_values
                    })
                
                return {
                    "dataset_id": dataset_id,
                    "target_column": target_column,
                    "scenarios": scenario_results
                }
            except Exception as exc:
                LOGGER.exception("Failed scenario analysis")
                return {"error": f"Unable to run scenario analysis: {exc}"}

        @mcp.tool(tags={self.domain.value})
        def optimize_cash_flow(
            dataset_id: str,
            cash_in_column: str,
            cash_out_column: str
        ) -> Dict[str, Any]:
            """Analyze and optimize cash flow patterns."""
            metadata = self._find_metadata(dataset_id)
            if not metadata:
                return {"error": f"Dataset '{dataset_id}' was not found."}

            dataset_path = self._dataset_file(metadata)
            if not dataset_path:
                return {"error": f"Dataset file for '{dataset_id}' is missing."}

            try:
                cash_in_values, _ = extract_numeric_series(dataset_path, cash_in_column)
                cash_out_values, _ = extract_numeric_series(dataset_path, cash_out_column)
                
                if len(cash_in_values) != len(cash_out_values):
                    return {"error": "Cash in and cash out columns must have same number of rows"}
                
                net_cash_flow = [in_val - out_val for in_val, out_val in zip(cash_in_values, cash_out_values)]
                
                total_in = sum(cash_in_values)
                total_out = sum(cash_out_values)
                total_net = sum(net_cash_flow)
                
                return {
                    "dataset_id": dataset_id,
                    "total_cash_in": round(total_in, 2),
                    "total_cash_out": round(total_out, 2),
                    "net_cash_flow": round(total_net, 2)
                }
            except Exception as exc:
                LOGGER.exception("Failed to optimize cash flow")
                return {"error": f"Unable to analyze cash flow: {exc}"}

    @property
    def tool_count(self) -> int:
        return 9
