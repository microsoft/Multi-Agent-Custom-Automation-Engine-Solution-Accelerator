"""Visualization MCP tools for creating charts, graphs, and dashboards."""

from __future__ import annotations

import base64
import io
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import pandas as pd
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from core.factory import Domain, MCPToolBase

LOGGER = logging.getLogger(__name__)


class VisualizationService(MCPToolBase):
    """Tools for creating charts, graphs, and visualizations from data."""

    def __init__(self, dataset_root: Optional[Path] = None):
        super().__init__(Domain.VISUALIZATION)
        default_root = Path(__file__).resolve().parents[3] / "data" / "uploads"
        self.dataset_root = dataset_root or default_root
        self.dataset_root.mkdir(parents=True, exist_ok=True)
        self.charts_dir = self.dataset_root.parent / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_identifier(self, value: str) -> str:
        """Sanitize identifier for use in file paths."""
        import re
        return re.sub(r"[^A-Za-z0-9_-]", "_", value)

    def _get_dataset_path(self, dataset_id: str, user_id: str = "default") -> Path:
        """Get path to dataset file. Searches across all users if not found for specified user."""
        user_folder = self._sanitize_identifier(user_id)
        dataset_folder = self._sanitize_identifier(dataset_id)
        dataset_dir = self.dataset_root / user_folder / dataset_folder
        
        # Try specified user first
        if dataset_dir.exists():
            for file in dataset_dir.iterdir():
                if file.suffix.lower() == '.csv':
                    return file
        
        # If not found, search across all users
        LOGGER.info(f"Dataset {dataset_id} not found for user {user_id}, searching all users...")
        for user_dir in self.dataset_root.iterdir():
            if not user_dir.is_dir():
                continue
            candidate_dir = user_dir / dataset_folder
            if candidate_dir.exists():
                for file in candidate_dir.iterdir():
                    if file.suffix.lower() == '.csv':
                        LOGGER.info(f"Found dataset {dataset_id} under user {user_dir.name}")
                        return file
        
        # Return default path if not found anywhere
        return dataset_dir / "data.csv"

    def _read_csv_data(self, file_path: Path) -> tuple[List[str], List[Dict[str, Any]]]:
        """Read CSV file and return headers and rows."""
        import csv
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = list(reader)
        return list(headers), rows

    def _chart_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string."""
        if not MATPLOTLIB_AVAILABLE:
            return ""
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64

    def _save_chart(self, fig, chart_id: str, user_id: str) -> Dict[str, str]:
        """Save chart to file and return paths."""
        user_folder = self._sanitize_identifier(user_id)
        user_charts_dir = self.charts_dir / user_folder
        user_charts_dir.mkdir(parents=True, exist_ok=True)
        
        png_path = user_charts_dir / f"{chart_id}.png"
        svg_path = user_charts_dir / f"{chart_id}.svg"
        
        if MATPLOTLIB_AVAILABLE:
            fig.savefig(png_path, format='png', dpi=100, bbox_inches='tight')
            fig.savefig(svg_path, format='svg', bbox_inches='tight')
            plt.close(fig)
        
        return {
            "png_path": str(png_path),
            "svg_path": str(svg_path),
            "chart_id": chart_id
        }

    @property
    def tool_count(self) -> int:
        return 5

    def register_tools(self, mcp: Any) -> None:
        """Register all visualization tools with the MCP server."""

        @mcp.tool(tags={self.domain.value})
        def create_chart(
            dataset_id: str,
            chart_type: str,
            x_column: str,
            y_column: Optional[str] = None,
            user_id: str = "default",
            options: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            Generate charts from dataset (bar, line, pie, scatter, etc.).
            
            Args:
                dataset_id: Dataset ID to visualize
                chart_type: Type of chart - "bar", "line", "pie", "scatter", "area", "histogram"
                x_column: Column name for X-axis
                y_column: Column name for Y-axis (required for bar, line, scatter, area)
                user_id: User identifier (default: "default")
                options: Additional chart options:
                    - title: Chart title
                    - x_label: X-axis label
                    - y_label: Y-axis label
                    - color: Color scheme
                    - stacked: For bar charts (True/False)
            
            Returns:
                Dictionary with chart ID, image base64, and file paths.
            """
            if not MATPLOTLIB_AVAILABLE:
                return {
                    "success": False,
                    "error": "Visualization requires matplotlib. Install with: pip install matplotlib pandas"
                }
            
            try:
                file_path = self._get_dataset_path(dataset_id, user_id)
                
                if not file_path.exists():
                    return {
                        "success": False,
                        "error": f"Dataset file not found for '{dataset_id}'"
                    }
                
                # Read data
                headers, rows = self._read_csv_data(file_path)
                
                if x_column not in headers:
                    return {
                        "success": False,
                        "error": f"Column '{x_column}' not found in dataset"
                    }
                
                # Load into pandas for easier manipulation
                df = pd.DataFrame(rows)
                
                # Prepare data
                x_data = df[x_column]
                
                chart_options = options or {}
                title = chart_options.get("title", f"{chart_type.title()} Chart")
                x_label = chart_options.get("x_label", x_column)
                y_label = chart_options.get("y_label", y_column or "")
                
                # Create figure
                fig, ax = plt.subplots(figsize=(10, 6))
                
                chart_type_lower = chart_type.lower()
                
                if chart_type_lower == "bar":
                    if not y_column or y_column not in headers:
                        return {
                            "success": False,
                            "error": f"Y column '{y_column}' required for bar chart"
                        }
                    
                    # Convert y to numeric
                    y_data = pd.to_numeric(df[y_column], errors='coerce')
                    
                    if chart_options.get("stacked"):
                        # For stacked bars, need multiple series
                        # Simplified - use first numeric column as y
                        ax.bar(x_data, y_data, label=y_column)
                    else:
                        ax.bar(x_data, y_data)
                    
                    ax.set_ylabel(y_label)
                    ax.set_xlabel(x_label)
                    ax.set_title(title)
                    plt.xticks(rotation=45, ha='right')
                
                elif chart_type_lower == "line":
                    if not y_column or y_column not in headers:
                        return {
                            "success": False,
                            "error": f"Y column '{y_column}' required for line chart"
                        }
                    
                    y_data = pd.to_numeric(df[y_column], errors='coerce')
                    ax.plot(x_data, y_data, marker='o')
                    ax.set_ylabel(y_label)
                    ax.set_xlabel(x_label)
                    ax.set_title(title)
                    plt.xticks(rotation=45, ha='right')
                
                elif chart_type_lower == "pie":
                    # Count values for pie chart
                    value_counts = x_data.value_counts()
                    ax.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%')
                    ax.set_title(title)
                
                elif chart_type_lower == "scatter":
                    if not y_column or y_column not in headers:
                        return {
                            "success": False,
                            "error": f"Y column '{y_column}' required for scatter plot"
                        }
                    
                    # Convert to numeric
                    x_numeric = pd.to_numeric(df[x_column], errors='coerce')
                    y_numeric = pd.to_numeric(df[y_column], errors='coerce')
                    ax.scatter(x_numeric, y_numeric)
                    ax.set_xlabel(x_label)
                    ax.set_ylabel(y_label)
                    ax.set_title(title)
                
                elif chart_type_lower == "area":
                    if not y_column or y_column not in headers:
                        return {
                            "success": False,
                            "error": f"Y column '{y_column}' required for area chart"
                        }
                    
                    y_data = pd.to_numeric(df[y_column], errors='coerce')
                    ax.fill_between(x_data, y_data, alpha=0.5)
                    ax.plot(x_data, y_data, marker='o')
                    ax.set_ylabel(y_label)
                    ax.set_xlabel(x_label)
                    ax.set_title(title)
                    plt.xticks(rotation=45, ha='right')
                
                elif chart_type_lower == "histogram":
                    # Convert x to numeric for histogram
                    x_numeric = pd.to_numeric(df[x_column], errors='coerce').dropna()
                    ax.hist(x_numeric, bins=chart_options.get("bins", 20))
                    ax.set_xlabel(x_label)
                    ax.set_ylabel("Frequency")
                    ax.set_title(title)
                
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported chart type: {chart_type}. Supported: bar, line, pie, scatter, area, histogram"
                    }
                
                # Generate chart ID and save
                chart_id = str(uuid.uuid4())
                chart_paths = self._save_chart(fig, chart_id, user_id)
                image_base64 = self._chart_to_base64(fig)
                
                return {
                    "success": True,
                    "chart_id": chart_id,
                    "chart_type": chart_type,
                    "image_base64": image_base64,
                    "png_path": chart_paths["png_path"],
                    "svg_path": chart_paths["svg_path"],
                    "title": title,
                    "message": f"Chart '{title}' created successfully"
                }
                
            except Exception as e:
                LOGGER.error(f"Error creating chart: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @mcp.tool(tags={self.domain.value})
        def create_dashboard(
            dataset_id: str,
            chart_configs: List[Dict[str, Any]],
            user_id: str = "default",
            layout: Optional[str] = "grid"
        ) -> Dict[str, Any]:
            """
            Create multi-chart dashboard.
            
            Args:
                dataset_id: Dataset ID to visualize
                chart_configs: List of chart configurations, each with:
                    - chart_type: Type of chart
                    - x_column: X-axis column
                    - y_column: Y-axis column (if needed)
                    - title: Chart title
                    - options: Additional options
                user_id: User identifier (default: "default")
                layout: Layout type - "grid", "vertical", or "horizontal"
            
            Returns:
                Dictionary with dashboard ID, chart IDs, and image paths.
            """
            if not MATPLOTLIB_AVAILABLE:
                return {
                    "success": False,
                    "error": "Visualization requires matplotlib. Install with: pip install matplotlib pandas"
                }
            
            try:
                file_path = self._get_dataset_path(dataset_id, user_id)
                
                if not file_path.exists():
                    return {
                        "success": False,
                        "error": f"Dataset file not found for '{dataset_id}'"
                    }
                
                # Read data
                headers, rows = self._read_csv_data(file_path)
                df = pd.DataFrame(rows)
                
                # Determine grid layout
                num_charts = len(chart_configs)
                if layout == "grid":
                    cols = 2
                    rows = (num_charts + 1) // 2
                elif layout == "vertical":
                    cols = 1
                    rows = num_charts
                else:  # horizontal
                    cols = num_charts
                    rows = 1
                
                fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
                if num_charts == 1:
                    axes = [axes]
                elif rows == 1 or cols == 1:
                    axes = axes.flatten()
                else:
                    axes = axes.flatten()
                
                chart_ids = []
                
                for idx, config in enumerate(chart_configs):
                    ax = axes[idx] if num_charts > 1 else axes
                    
                    chart_type = config.get("chart_type", "bar")
                    x_column = config.get("x_column")
                    y_column = config.get("y_column")
                    title = config.get("title", f"Chart {idx + 1}")
                    
                    if not x_column or x_column not in headers:
                        continue
                    
                    x_data = df[x_column]
                    
                    if chart_type == "bar" and y_column:
                        y_data = pd.to_numeric(df[y_column], errors='coerce')
                        ax.bar(x_data, y_data)
                    elif chart_type == "line" and y_column:
                        y_data = pd.to_numeric(df[y_column], errors='coerce')
                        ax.plot(x_data, y_data, marker='o')
                    elif chart_type == "pie":
                        value_counts = x_data.value_counts()
                        ax.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%')
                    elif chart_type == "scatter" and y_column:
                        x_numeric = pd.to_numeric(df[x_column], errors='coerce')
                        y_numeric = pd.to_numeric(df[y_column], errors='coerce')
                        ax.scatter(x_numeric, y_numeric)
                    elif chart_type == "histogram":
                        x_numeric = pd.to_numeric(df[x_column], errors='coerce').dropna()
                        ax.hist(x_numeric, bins=20)
                    
                    ax.set_title(title)
                    if chart_type not in ["pie"]:
                        ax.set_xlabel(x_column)
                        if y_column:
                            ax.set_ylabel(y_column)
                
                # Hide unused subplots
                for idx in range(num_charts, len(axes)):
                    axes[idx].set_visible(False)
                
                plt.tight_layout()
                
                # Generate dashboard ID and save
                dashboard_id = str(uuid.uuid4())
                chart_paths = self._save_chart(fig, dashboard_id, user_id)
                image_base64 = self._chart_to_base64(fig)
                
                return {
                    "success": True,
                    "dashboard_id": dashboard_id,
                    "chart_count": num_charts,
                    "layout": layout,
                    "image_base64": image_base64,
                    "png_path": chart_paths["png_path"],
                    "svg_path": chart_paths["svg_path"],
                    "message": f"Dashboard created with {num_charts} charts"
                }
                
            except Exception as e:
                LOGGER.error(f"Error creating dashboard: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @mcp.tool(tags={self.domain.value})
        def create_visualization_report(
            dataset_id: str,
            visualization_type: str,
            user_id: str = "default",
            params: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            Generate comprehensive visual reports.
            
            Args:
                dataset_id: Dataset ID to visualize
                visualization_type: Type of report - "summary", "trends", "comparison", "distribution"
                user_id: User identifier (default: "default")
                params: Additional parameters for visualization
            
            Returns:
                Dictionary with report ID, charts, and insights.
            """
            if not MATPLOTLIB_AVAILABLE:
                return {
                    "success": False,
                    "error": "Visualization requires matplotlib. Install with: pip install matplotlib pandas"
                }
            
            try:
                file_path = self._get_dataset_path(dataset_id, user_id)
                
                if not file_path.exists():
                    return {
                        "success": False,
                        "error": f"Dataset file not found for '{dataset_id}'"
                    }
                
                # Read data
                headers, rows = self._read_csv_data(file_path)
                df = pd.DataFrame(rows)
                
                # Detect numeric columns
                numeric_cols = []
                for col in headers:
                    try:
                        pd.to_numeric(df[col], errors='raise')
                        numeric_cols.append(col)
                    except:
                        pass
                
                report_id = str(uuid.uuid4())
                charts = []
                
                viz_type = visualization_type.lower()
                
                if viz_type == "summary":
                    # Create summary visualizations
                    if numeric_cols:
                        fig, axes = plt.subplots(1, min(3, len(numeric_cols)), figsize=(15, 5))
                        if len(numeric_cols) == 1:
                            axes = [axes]
                        
                        for idx, col in enumerate(numeric_cols[:3]):
                            ax = axes[idx] if len(numeric_cols) > 1 else axes[0]
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            ax.hist(df[col].dropna(), bins=20)
                            ax.set_title(f"Distribution: {col}")
                            ax.set_xlabel(col)
                            ax.set_ylabel("Frequency")
                        
                        plt.tight_layout()
                        chart_paths = self._save_chart(fig, f"{report_id}_summary", user_id)
                        charts.append({
                            "type": "summary",
                            "chart_id": f"{report_id}_summary",
                            "png_path": chart_paths["png_path"]
                        })
                
                elif viz_type == "trends":
                    # Create trend visualizations
                    if len(numeric_cols) >= 2:
                        fig, ax = plt.subplots(figsize=(12, 6))
                        x_col = headers[0]
                        y_col = numeric_cols[0]
                        
                        x_data = df[x_col]
                        y_data = pd.to_numeric(df[y_col], errors='coerce')
                        
                        ax.plot(x_data, y_data, marker='o')
                        ax.set_title(f"Trend Analysis: {y_col}")
                        ax.set_xlabel(x_col)
                        ax.set_ylabel(y_col)
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()
                        
                        chart_paths = self._save_chart(fig, f"{report_id}_trends", user_id)
                        charts.append({
                            "type": "trends",
                            "chart_id": f"{report_id}_trends",
                            "png_path": chart_paths["png_path"]
                        })
                
                return {
                    "success": True,
                    "report_id": report_id,
                    "visualization_type": visualization_type,
                    "charts": charts,
                    "dataset_id": dataset_id,
                    "message": f"Visualization report '{visualization_type}' created successfully"
                }
                
            except Exception as e:
                LOGGER.error(f"Error creating visualization report: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @mcp.tool(tags={self.domain.value})
        def export_chart(
            chart_id: str,
            format: str,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Export chart in different formats.
            
            Args:
                chart_id: Chart ID to export
                format: Export format - "png", "svg", "pdf"
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with export file path.
            """
            try:
                user_folder = self._sanitize_identifier(user_id)
                user_charts_dir = self.charts_dir / user_folder
                
                chart_file = user_charts_dir / f"{chart_id}.{format}"
                
                if not chart_file.exists():
                    return {
                        "success": False,
                        "error": f"Chart '{chart_id}' not found"
                    }
                
                return {
                    "success": True,
                    "chart_id": chart_id,
                    "format": format,
                    "file_path": str(chart_file),
                    "message": f"Chart exported to {format.upper()} format"
                }
                
            except Exception as e:
                LOGGER.error(f"Error exporting chart: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

        @mcp.tool(tags={self.domain.value})
        def get_chart_recommendations(
            dataset_id: str,
            analysis_type: str,
            user_id: str = "default"
        ) -> Dict[str, Any]:
            """
            Recommend best chart types for data.
            
            Args:
                dataset_id: Dataset ID to analyze
                analysis_type: Type of analysis - "trends", "comparison", "distribution", "correlation"
                user_id: User identifier (default: "default")
            
            Returns:
                Dictionary with recommended chart types and rationale.
            """
            try:
                file_path = self._get_dataset_path(dataset_id, user_id)
                
                if not file_path.exists():
                    return {
                        "success": False,
                        "error": f"Dataset file not found for '{dataset_id}'"
                    }
                
                # Read data
                headers, rows = self._read_csv_data(file_path)
                
                # Detect numeric columns
                numeric_cols = []
                categorical_cols = []
                
                for col in headers:
                    try:
                        pd.to_numeric([row.get(col, "") for row in rows[:10]], errors='raise')
                        numeric_cols.append(col)
                    except:
                        categorical_cols.append(col)
                
                recommendations = []
                
                analysis_lower = analysis_type.lower()
                
                if analysis_lower == "trends":
                    if len(numeric_cols) >= 1:
                        recommendations.append({
                            "chart_type": "line",
                            "x_column": headers[0] if headers else None,
                            "y_column": numeric_cols[0],
                            "rationale": "Line charts are ideal for showing trends over time"
                        })
                
                elif analysis_lower == "comparison":
                    if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
                        recommendations.append({
                            "chart_type": "bar",
                            "x_column": categorical_cols[0],
                            "y_column": numeric_cols[0],
                            "rationale": "Bar charts are best for comparing values across categories"
                        })
                
                elif analysis_lower == "distribution":
                    if len(numeric_cols) >= 1:
                        recommendations.append({
                            "chart_type": "histogram",
                            "x_column": numeric_cols[0],
                            "rationale": "Histograms show the distribution of numeric data"
                        })
                
                elif analysis_lower == "correlation":
                    if len(numeric_cols) >= 2:
                        recommendations.append({
                            "chart_type": "scatter",
                            "x_column": numeric_cols[0],
                            "y_column": numeric_cols[1],
                            "rationale": "Scatter plots reveal relationships between two numeric variables"
                        })
                
                # Default recommendations if none matched
                if not recommendations:
                    if numeric_cols:
                        recommendations.append({
                            "chart_type": "bar",
                            "x_column": headers[0] if headers else None,
                            "y_column": numeric_cols[0],
                            "rationale": "Bar chart is a versatile option for this data"
                        })
                    else:
                        recommendations.append({
                            "chart_type": "pie",
                            "x_column": headers[0] if headers else None,
                            "rationale": "Pie chart shows proportions for categorical data"
                        })
                
                return {
                    "success": True,
                    "dataset_id": dataset_id,
                    "analysis_type": analysis_type,
                    "recommendations": recommendations,
                    "numeric_columns": numeric_cols,
                    "categorical_columns": categorical_cols,
                    "message": f"Generated {len(recommendations)} chart recommendations"
                }
                
            except Exception as e:
                LOGGER.error(f"Error getting chart recommendations: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }

