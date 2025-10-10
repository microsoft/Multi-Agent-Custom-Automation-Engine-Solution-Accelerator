"""
Operations Analytics Utilities

Provides functions for delivery performance forecasting, inventory optimization,
and warehouse incident analysis for retail operations.

Built for Sprint 2 - Customer & Operations Analytics
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import math

logger = logging.getLogger(__name__)


def analyze_delivery_performance(
    delivery_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze delivery performance metrics and identify trends.
    
    Args:
        delivery_data: List of dicts with Month, AverageDeliveryTime, OnTimeDeliveryRate, CustomerComplaints
        
    Returns:
        Dictionary with performance analysis, trends, and issues
    """
    try:
        if not delivery_data:
            return {
                "error": "No delivery data provided",
                "metrics": []
            }
        
        # Extract metrics
        metrics = []
        for entry in delivery_data:
            month = entry.get('Month', 'Unknown')
            avg_time = float(entry.get('AverageDeliveryTime', 0))
            on_time_rate = float(entry.get('OnTimeDeliveryRate', 0))
            complaints = int(entry.get('CustomerComplaints', 0))
            
            # Calculate performance score (0-100)
            # Formula: (on_time_rate * 0.6) + ((10 - avg_time) / 10 * 0.3 * 100) + ((100 - complaints) / 100 * 0.1 * 100)
            time_score = max(0, (10 - avg_time) / 10 * 100) if avg_time <= 10 else 0
            complaint_score = max(0, (100 - complaints) / 100 * 100) if complaints <= 100 else 0
            performance_score = (on_time_rate * 0.6) + (time_score * 0.3) + (complaint_score * 0.1)
            
            metrics.append({
                "month": month,
                "avg_delivery_time": avg_time,
                "on_time_rate": on_time_rate,
                "customer_complaints": complaints,
                "performance_score": round(performance_score, 2),
                "grade": get_performance_grade(performance_score)
            })
        
        # Identify worst performing period
        worst_period = min(metrics, key=lambda x: x['performance_score'])
        best_period = max(metrics, key=lambda x: x['performance_score'])
        
        # Calculate overall trends
        avg_delivery_time_trend = calculate_trend([m['avg_delivery_time'] for m in metrics])
        on_time_trend = calculate_trend([m['on_time_rate'] for m in metrics])
        complaint_trend = calculate_trend([m['customer_complaints'] for m in metrics])
        
        # Detect degradation periods (performance drops > 15% from previous)
        degradation_periods = []
        for i in range(1, len(metrics)):
            current_score = metrics[i]['performance_score']
            previous_score = metrics[i - 1]['performance_score']
            
            if previous_score > 0:
                change = (current_score - previous_score) / previous_score
                
                if change < -0.15:  # 15% drop
                    degradation_periods.append({
                        "month": metrics[i]['month'],
                        "performance_score": current_score,
                        "previous_score": previous_score,
                        "change_percentage": round(change * 100, 1),
                        "severity": "Critical" if change < -0.3 else "High"
                    })
        
        # Generate recommendations
        recommendations = []
        
        if worst_period['avg_delivery_time'] > 5:
            recommendations.append({
                "priority": "High",
                "action": "Reduce delivery time",
                "details": f"Worst delivery time: {worst_period['avg_delivery_time']} days in {worst_period['month']}. Review logistics partners, optimize routing, consider additional distribution centers."
            })
        
        if worst_period['on_time_rate'] < 90:
            recommendations.append({
                "priority": "High",
                "action": "Improve on-time delivery",
                "details": f"On-time rate dropped to {worst_period['on_time_rate']}% in {worst_period['month']}. Implement better inventory management, improve coordination with carriers."
            })
        
        if complaint_trend > 0.1:  # Increasing complaints
            recommendations.append({
                "priority": "Medium",
                "action": "Address customer complaint root causes",
                "details": "Customer complaints are trending upward. Conduct surveys, improve packaging, enhance tracking visibility."
            })
        
        if degradation_periods:
            recommendations.append({
                "priority": "Critical",
                "action": "Investigate performance degradation",
                "details": f"Detected {len(degradation_periods)} significant performance drops. Review operational changes, external factors, and incidents during these periods."
            })
        
        # Calculate averages
        avg_performance = sum(m['performance_score'] for m in metrics) / len(metrics)
        current_performance = metrics[-1]['performance_score'] if metrics else 0
        
        return {
            "total_periods": len(metrics),
            "metrics": metrics,
            "current_performance": {
                "month": metrics[-1]['month'] if metrics else 'Unknown',
                "score": current_performance,
                "grade": get_performance_grade(current_performance),
                "avg_delivery_time": metrics[-1]['avg_delivery_time'] if metrics else 0,
                "on_time_rate": metrics[-1]['on_time_rate'] if metrics else 0
            },
            "average_performance": round(avg_performance, 2),
            "best_period": best_period,
            "worst_period": worst_period,
            "trends": {
                "delivery_time": "Improving" if avg_delivery_time_trend < -0.05 else "Worsening" if avg_delivery_time_trend > 0.05 else "Stable",
                "on_time_rate": "Improving" if on_time_trend > 0.02 else "Declining" if on_time_trend < -0.02 else "Stable",
                "complaints": "Increasing" if complaint_trend > 0.1 else "Decreasing" if complaint_trend < -0.1 else "Stable"
            },
            "degradation_periods": degradation_periods,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Error analyzing delivery performance: {e}")
        return {
            "error": str(e),
            "metrics": []
        }


def forecast_delivery_metrics(
    delivery_data: List[Dict[str, Any]],
    periods: int = 3
) -> Dict[str, Any]:
    """
    Forecast delivery performance metrics using trend analysis.
    
    Args:
        delivery_data: Historical delivery data
        periods: Number of periods to forecast
        
    Returns:
        Dictionary with forecasted metrics
    """
    try:
        if len(delivery_data) < 2:
            return {
                "error": "Insufficient data for forecasting (minimum 2 periods required)",
                "forecast": []
            }
        
        # Extract time series for each metric
        delivery_times = [float(d.get('AverageDeliveryTime', 0)) for d in delivery_data]
        on_time_rates = [float(d.get('OnTimeDeliveryRate', 0)) for d in delivery_data]
        complaints = [float(d.get('CustomerComplaints', 0)) for d in delivery_data]
        
        # Simple linear forecast for each metric
        forecast = []
        
        for period in range(1, periods + 1):
            # Forecast delivery time
            time_forecast = simple_linear_forecast_single(delivery_times, period)
            time_forecast = max(1, time_forecast)  # Minimum 1 day
            
            # Forecast on-time rate
            rate_forecast = simple_linear_forecast_single(on_time_rates, period)
            rate_forecast = max(0, min(100, rate_forecast))  # Clamp to 0-100%
            
            # Forecast complaints
            complaint_forecast = simple_linear_forecast_single(complaints, period)
            complaint_forecast = max(0, complaint_forecast)  # Non-negative
            
            # Calculate forecasted performance score
            time_score = max(0, (10 - time_forecast) / 10 * 100) if time_forecast <= 10 else 0
            complaint_score = max(0, (100 - complaint_forecast) / 100 * 100) if complaint_forecast <= 100 else 0
            performance_score = (rate_forecast * 0.6) + (time_score * 0.3) + (complaint_score * 0.1)
            
            forecast.append({
                "period": period,
                "avg_delivery_time": round(time_forecast, 1),
                "on_time_rate": round(rate_forecast, 1),
                "customer_complaints": round(complaint_forecast, 0),
                "performance_score": round(performance_score, 2),
                "grade": get_performance_grade(performance_score)
            })
        
        return {
            "forecast_periods": periods,
            "forecast": forecast,
            "methodology": "Linear trend projection with performance scoring"
        }
        
    except Exception as e:
        logger.error(f"Error forecasting delivery metrics: {e}")
        return {
            "error": str(e),
            "forecast": []
        }


def analyze_warehouse_incidents(
    incident_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze warehouse incidents for impact and risk assessment.
    
    Args:
        incident_data: List of dicts with Date, IncidentDescription, AffectedOrders
        
    Returns:
        Dictionary with incident analysis and recommendations
    """
    try:
        if not incident_data:
            return {
                "error": "No incident data provided",
                "incidents": []
            }
        
        # Analyze each incident
        incidents = []
        total_affected_orders = 0
        
        for entry in incident_data:
            date = entry.get('Date', 'Unknown')
            description = entry.get('IncidentDescription', 'Unknown incident')
            affected_orders = int(entry.get('AffectedOrders', 0))
            
            # Categorize incident
            category = categorize_incident(description)
            
            # Assess severity based on affected orders
            if affected_orders >= 200:
                severity = "Critical"
                impact_score = 10
            elif affected_orders >= 100:
                severity = "High"
                impact_score = 7
            elif affected_orders >= 50:
                severity = "Medium"
                impact_score = 5
            else:
                severity = "Low"
                impact_score = 3
            
            total_affected_orders += affected_orders
            
            incidents.append({
                "date": date,
                "description": description,
                "category": category,
                "affected_orders": affected_orders,
                "severity": severity,
                "impact_score": impact_score
            })
        
        # Sort by severity
        incidents_sorted = sorted(incidents, key=lambda x: x['impact_score'], reverse=True)
        
        # Generate recommendations by category
        categories = set(inc['category'] for inc in incidents)
        recommendations = []
        
        for category in categories:
            category_incidents = [inc for inc in incidents if inc['category'] == category]
            category_impact = sum(inc['affected_orders'] for inc in category_incidents)
            
            if category == "Systems":
                recommendations.append({
                    "category": category,
                    "priority": "High",
                    "action": "Improve system reliability",
                    "details": f"{len(category_incidents)} system incident(s) affected {category_impact} orders. Implement redundancy, improve monitoring, regular maintenance."
                })
            elif category == "External":
                recommendations.append({
                    "category": category,
                    "priority": "Medium" if category_impact < 300 else "High",
                    "action": "Mitigate external risks",
                    "details": f"{len(category_incidents)} external incident(s) affected {category_impact} orders. Diversify logistics partners, create contingency plans, improve contract SLAs."
                })
            elif category == "Infrastructure":
                recommendations.append({
                    "category": category,
                    "priority": "High",
                    "action": "Enhance infrastructure resilience",
                    "details": f"{len(category_incidents)} infrastructure incident(s) affected {category_impact} orders. Improve facility maintenance, disaster preparedness, backup systems."
                })
        
        # Add general recommendations
        if total_affected_orders >= 400:
            recommendations.append({
                "category": "General",
                "priority": "Critical",
                "action": "Comprehensive risk management review",
                "details": f"Total of {total_affected_orders} orders affected by incidents. Conduct full operational risk assessment and implement business continuity plan."
            })
        
        return {
            "total_incidents": len(incidents),
            "total_affected_orders": total_affected_orders,
            "incidents": incidents_sorted,
            "most_severe_incident": incidents_sorted[0] if incidents_sorted else None,
            "incident_categories": list(categories),
            "recommendations": recommendations,
            "risk_level": "High" if total_affected_orders >= 300 else "Medium" if total_affected_orders >= 150 else "Low"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing warehouse incidents: {e}")
        return {
            "error": str(e),
            "incidents": []
        }


def optimize_inventory(
    purchase_history: List[Dict[str, Any]],
    target_service_level: float = 0.95
) -> Dict[str, Any]:
    """
    Recommend inventory levels based on purchase patterns.
    
    Args:
        purchase_history: List of purchase records
        target_service_level: Desired service level (default 95%)
        
    Returns:
        Dictionary with inventory recommendations
    """
    try:
        if not purchase_history:
            return {
                "error": "No purchase history provided",
                "recommendations": []
            }
        
        # Extract items and calculate frequency
        item_frequency = {}
        item_revenue = {}
        
        for purchase in purchase_history:
            items = purchase.get('ItemsPurchased', '')
            amount = float(purchase.get('TotalAmount', 0))
            
            # Split items (assuming comma-separated)
            items_list = [item.strip() for item in items.split(',') if item.strip()]
            
            for item in items_list:
                item_frequency[item] = item_frequency.get(item, 0) + 1
                item_revenue[item] = item_revenue.get(item, 0) + (amount / len(items_list))
        
        # Calculate inventory recommendations
        recommendations = []
        total_orders = len(purchase_history)
        
        for item, frequency in item_frequency.items():
            # Calculate demand rate (orders per period)
            demand_rate = frequency / total_orders
            
            # Estimate safety stock based on service level
            # Using simple newsvendor model approximation
            z_score = 1.65 if target_service_level >= 0.95 else 1.28 if target_service_level >= 0.90 else 1.0
            
            # Assume demand variability (std dev as 30% of mean)
            demand_std = demand_rate * 0.3
            safety_stock = z_score * demand_std * math.sqrt(total_orders)
            
            # Base stock level (for one period)
            base_stock = frequency
            
            # Recommended stock level
            recommended_stock = math.ceil(base_stock + safety_stock)
            
            # Calculate reorder point (assuming lead time of 1 period)
            reorder_point = math.ceil(demand_rate + safety_stock)
            
            # Revenue contribution
            revenue_contribution = item_revenue.get(item, 0)
            
            recommendations.append({
                "item": item,
                "historical_demand": frequency,
                "demand_rate": round(demand_rate, 3),
                "recommended_stock_level": recommended_stock,
                "reorder_point": reorder_point,
                "safety_stock": math.ceil(safety_stock),
                "revenue_contribution": round(revenue_contribution, 2),
                "priority": "High" if revenue_contribution > 200 else "Medium" if revenue_contribution > 100 else "Standard"
            })
        
        # Sort by revenue contribution
        recommendations_sorted = sorted(recommendations, key=lambda x: x['revenue_contribution'], reverse=True)
        
        # Calculate summary statistics
        total_recommended_stock = sum(r['recommended_stock_level'] for r in recommendations)
        total_revenue = sum(r['revenue_contribution'] for r in recommendations)
        
        return {
            "total_items": len(recommendations),
            "target_service_level": target_service_level,
            "total_recommended_stock_units": total_recommended_stock,
            "total_revenue_analyzed": round(total_revenue, 2),
            "recommendations": recommendations_sorted,
            "methodology": f"Newsvendor model with {target_service_level * 100}% service level target",
            "assumptions": {
                "demand_variability": "30% of mean demand",
                "lead_time": "1 period",
                "review_period": "Continuous"
            }
        }
        
    except Exception as e:
        logger.error(f"Error optimizing inventory: {e}")
        return {
            "error": str(e),
            "recommendations": []
        }


# Helper functions

def get_performance_grade(score: float) -> str:
    """Convert performance score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def calculate_trend(values: List[float]) -> float:
    """Calculate simple linear trend (slope) from values."""
    if len(values) < 2:
        return 0.0
    
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    
    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator


def simple_linear_forecast_single(values: List[float], periods_ahead: int) -> float:
    """Simple linear forecast for a single future period."""
    if len(values) < 2:
        return values[0] if values else 0
    
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    
    numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return y_mean
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Forecast for periods_ahead into the future
    forecast_value = intercept + slope * (n - 1 + periods_ahead)
    
    return forecast_value


def categorize_incident(description: str) -> str:
    """Categorize incident based on description keywords."""
    description_lower = description.lower()
    
    if any(word in description_lower for word in ['system', 'outage', 'software', 'database']):
        return "Systems"
    elif any(word in description_lower for word in ['strike', 'partner', 'logistics', 'carrier']):
        return "External"
    elif any(word in description_lower for word in ['flood', 'fire', 'weather', 'building', 'facility']):
        return "Infrastructure"
    elif any(word in description_lower for word in ['inventory', 'stock', 'shortage']):
        return "Inventory"
    else:
        return "Other"

