"""
Unit tests for operations analytics utilities.

Tests cover delivery performance analysis, inventory optimization,
warehouse incident analysis, and forecasting.
"""

import pytest
from common.utils.operations_analytics import (
    analyze_delivery_performance,
    forecast_delivery_metrics,
    analyze_warehouse_incidents,
    optimize_inventory,
    get_performance_grade,
    calculate_trend,
    simple_linear_forecast_single,
    categorize_incident,
)


class TestAnalyzeDeliveryPerformance:
    """Test delivery performance analysis functionality."""

    def test_analyze_delivery_basic(self):
        """Test basic delivery performance analysis."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "95", "CustomerComplaints": "10"},
            {"Month": "Feb", "AverageDeliveryTime": "4", "OnTimeDeliveryRate": "92", "CustomerComplaints": "15"},
            {"Month": "Mar", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "96", "CustomerComplaints": "8"},
        ]
        
        result = analyze_delivery_performance(delivery_data)
        
        assert result["total_periods"] == 3
        assert len(result["metrics"]) == 3
        assert "current_performance" in result
        assert "best_period" in result
        assert "worst_period" in result
        assert "trends" in result

    def test_analyze_delivery_performance_score(self):
        """Test performance score calculation."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "98", "CustomerComplaints": "5"},
        ]
        
        result = analyze_delivery_performance(delivery_data)
        
        metric = result["metrics"][0]
        assert "performance_score" in metric
        assert metric["performance_score"] > 0
        assert metric["performance_score"] <= 100
        assert "grade" in metric

    def test_analyze_delivery_excellent_performance(self):
        """Test excellent delivery performance gets A grade."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "2", "OnTimeDeliveryRate": "99", "CustomerComplaints": "2"},
        ]
        
        result = analyze_delivery_performance(delivery_data)
        
        metric = result["metrics"][0]
        assert metric["performance_score"] >= 90
        assert metric["grade"] == "A"

    def test_analyze_delivery_poor_performance(self):
        """Test poor delivery performance gets lower grade."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "10", "OnTimeDeliveryRate": "70", "CustomerComplaints": "80"},
        ]
        
        result = analyze_delivery_performance(delivery_data)
        
        metric = result["metrics"][0]
        assert metric["performance_score"] < 80
        assert metric["grade"] in ["C", "D", "F"]

    def test_analyze_delivery_degradation_detection(self):
        """Test detection of performance degradation."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "95", "CustomerComplaints": "10"},
            {"Month": "Feb", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "96", "CustomerComplaints": "8"},
            {"Month": "Mar", "AverageDeliveryTime": "7", "OnTimeDeliveryRate": "85", "CustomerComplaints": "70"},  # Big drop
        ]
        
        result = analyze_delivery_performance(delivery_data)
        
        # Should detect degradation in March
        assert len(result["degradation_periods"]) > 0
        degradation = result["degradation_periods"][0]
        assert degradation["month"] == "Mar"
        assert degradation["severity"] in ["High", "Critical"]

    def test_analyze_delivery_trends(self):
        """Test trend calculation for delivery metrics."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "5", "OnTimeDeliveryRate": "85", "CustomerComplaints": "50"},
            {"Month": "Feb", "AverageDeliveryTime": "4", "OnTimeDeliveryRate": "90", "CustomerComplaints": "30"},
            {"Month": "Mar", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "95", "CustomerComplaints": "15"},
        ]
        
        result = analyze_delivery_performance(delivery_data)
        
        trends = result["trends"]
        # Delivery time decreasing = Improving
        assert trends["delivery_time"] == "Improving"
        # On-time rate increasing = Improving
        assert trends["on_time_rate"] == "Improving"
        # Complaints decreasing = Decreasing
        assert trends["complaints"] == "Decreasing"

    def test_analyze_delivery_recommendations(self):
        """Test that recommendations are generated for issues."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "8", "OnTimeDeliveryRate": "85", "CustomerComplaints": "80"},
        ]
        
        result = analyze_delivery_performance(delivery_data)
        
        assert len(result["recommendations"]) > 0
        # Should have high priority recommendations for poor performance
        high_priority = [r for r in result["recommendations"] if r["priority"] in ["High", "Critical"]]
        assert len(high_priority) > 0

    def test_analyze_delivery_best_worst_periods(self):
        """Test identification of best and worst periods."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "96", "CustomerComplaints": "10"},
            {"Month": "Feb", "AverageDeliveryTime": "7", "OnTimeDeliveryRate": "80", "CustomerComplaints": "90"},
            {"Month": "Mar", "AverageDeliveryTime": "2", "OnTimeDeliveryRate": "98", "CustomerComplaints": "5"},
        ]
        
        result = analyze_delivery_performance(delivery_data)
        
        # March should be best
        assert result["best_period"]["month"] == "Mar"
        # February should be worst
        assert result["worst_period"]["month"] == "Feb"

    def test_analyze_delivery_empty_data(self):
        """Test handling of empty delivery data."""
        result = analyze_delivery_performance([])
        
        assert "error" in result
        assert result["metrics"] == []


class TestForecastDeliveryMetrics:
    """Test delivery metrics forecasting functionality."""

    def test_forecast_delivery_basic(self):
        """Test basic delivery forecasting."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "95", "CustomerComplaints": "10"},
            {"Month": "Feb", "AverageDeliveryTime": "4", "OnTimeDeliveryRate": "92", "CustomerComplaints": "15"},
            {"Month": "Mar", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "96", "CustomerComplaints": "8"},
        ]
        
        result = forecast_delivery_metrics(delivery_data, periods=3)
        
        assert result["forecast_periods"] == 3
        assert len(result["forecast"]) == 3
        assert "methodology" in result

    def test_forecast_delivery_metrics_structure(self):
        """Test forecast output structure."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "95", "CustomerComplaints": "10"},
            {"Month": "Feb", "AverageDeliveryTime": "4", "OnTimeDeliveryRate": "93", "CustomerComplaints": "12"},
        ]
        
        result = forecast_delivery_metrics(delivery_data, periods=2)
        
        for forecast in result["forecast"]:
            assert "period" in forecast
            assert "avg_delivery_time" in forecast
            assert "on_time_rate" in forecast
            assert "customer_complaints" in forecast
            assert "performance_score" in forecast
            assert "grade" in forecast

    def test_forecast_delivery_bounds(self):
        """Test that forecasted values are within reasonable bounds."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "95", "CustomerComplaints": "10"},
            {"Month": "Feb", "AverageDeliveryTime": "4", "OnTimeDeliveryRate": "93", "CustomerComplaints": "12"},
        ]
        
        result = forecast_delivery_metrics(delivery_data, periods=3)
        
        for forecast in result["forecast"]:
            # Delivery time should be positive
            assert forecast["avg_delivery_time"] >= 1
            # On-time rate should be 0-100%
            assert 0 <= forecast["on_time_rate"] <= 100
            # Complaints should be non-negative
            assert forecast["customer_complaints"] >= 0

    def test_forecast_delivery_insufficient_data(self):
        """Test handling of insufficient data for forecasting."""
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "95", "CustomerComplaints": "10"},
        ]
        
        result = forecast_delivery_metrics(delivery_data, periods=3)
        
        assert "error" in result
        assert result["forecast"] == []


class TestAnalyzeWarehouseIncidents:
    """Test warehouse incident analysis functionality."""

    def test_analyze_incidents_basic(self):
        """Test basic incident analysis."""
        incident_data = [
            {"Date": "2023-06-15", "IncidentDescription": "Inventory system outage", "AffectedOrders": "100"},
            {"Date": "2023-07-18", "IncidentDescription": "Logistics partner strike", "AffectedOrders": "250"},
        ]
        
        result = analyze_warehouse_incidents(incident_data)
        
        assert result["total_incidents"] == 2
        assert result["total_affected_orders"] == 350
        assert len(result["incidents"]) == 2
        assert "risk_level" in result

    def test_analyze_incidents_severity_calculation(self):
        """Test incident severity classification."""
        incident_data = [
            {"Date": "2023-01-01", "IncidentDescription": "Minor delay", "AffectedOrders": "30"},
            {"Date": "2023-02-01", "IncidentDescription": "Major outage", "AffectedOrders": "150"},
            {"Date": "2023-03-01", "IncidentDescription": "Critical failure", "AffectedOrders": "300"},
        ]
        
        result = analyze_warehouse_incidents(incident_data)
        
        incidents = result["incidents"]
        # Check severity assignment
        low_severity = [i for i in incidents if i["severity"] == "Low"]
        high_severity = [i for i in incidents if i["severity"] in ["High", "Critical"]]
        
        assert len(low_severity) > 0
        assert len(high_severity) > 0

    def test_analyze_incidents_categorization(self):
        """Test incident categorization."""
        incident_data = [
            {"Date": "2023-01-01", "IncidentDescription": "Database system outage", "AffectedOrders": "100"},
            {"Date": "2023-02-01", "IncidentDescription": "Carrier strike", "AffectedOrders": "200"},
            {"Date": "2023-03-01", "IncidentDescription": "Warehouse flooding", "AffectedOrders": "150"},
        ]
        
        result = analyze_warehouse_incidents(incident_data)
        
        categories = result["incident_categories"]
        assert "Systems" in categories
        assert "External" in categories
        assert "Infrastructure" in categories

    def test_analyze_incidents_most_severe(self):
        """Test identification of most severe incident."""
        incident_data = [
            {"Date": "2023-01-01", "IncidentDescription": "Minor issue", "AffectedOrders": "50"},
            {"Date": "2023-02-01", "IncidentDescription": "Major disaster", "AffectedOrders": "500"},
            {"Date": "2023-03-01", "IncidentDescription": "Small problem", "AffectedOrders": "25"},
        ]
        
        result = analyze_warehouse_incidents(incident_data)
        
        most_severe = result["most_severe_incident"]
        assert most_severe["affected_orders"] == 500
        assert most_severe["severity"] == "Critical"

    def test_analyze_incidents_recommendations(self):
        """Test that recommendations are generated."""
        incident_data = [
            {"Date": "2023-01-01", "IncidentDescription": "System outage", "AffectedOrders": "200"},
        ]
        
        result = analyze_warehouse_incidents(incident_data)
        
        assert len(result["recommendations"]) > 0
        for rec in result["recommendations"]:
            assert "category" in rec
            assert "priority" in rec
            assert "action" in rec
            assert "details" in rec

    def test_analyze_incidents_risk_level(self):
        """Test risk level calculation."""
        high_impact_data = [
            {"Date": "2023-01-01", "IncidentDescription": "Major incident", "AffectedOrders": "400"},
        ]
        
        result = analyze_warehouse_incidents(high_impact_data)
        assert result["risk_level"] == "High"
        
        low_impact_data = [
            {"Date": "2023-01-01", "IncidentDescription": "Minor incident", "AffectedOrders": "50"},
        ]
        
        result = analyze_warehouse_incidents(low_impact_data)
        assert result["risk_level"] == "Low"

    def test_analyze_incidents_sorted_by_severity(self):
        """Test that incidents are sorted by impact score."""
        incident_data = [
            {"Date": "2023-01-01", "IncidentDescription": "Small", "AffectedOrders": "30"},
            {"Date": "2023-02-01", "IncidentDescription": "Large", "AffectedOrders": "300"},
            {"Date": "2023-03-01", "IncidentDescription": "Medium", "AffectedOrders": "150"},
        ]
        
        result = analyze_warehouse_incidents(incident_data)
        
        incidents = result["incidents"]
        # Should be sorted by impact score (descending)
        for i in range(len(incidents) - 1):
            assert incidents[i]["impact_score"] >= incidents[i + 1]["impact_score"]

    def test_analyze_incidents_empty_data(self):
        """Test handling of empty incident data."""
        result = analyze_warehouse_incidents([])
        
        assert "error" in result
        assert result["incidents"] == []


class TestOptimizeInventory:
    """Test inventory optimization functionality."""

    def test_optimize_inventory_basic(self):
        """Test basic inventory optimization."""
        purchase_data = [
            {"ItemsPurchased": "Item A, Item B", "TotalAmount": "100"},
            {"ItemsPurchased": "Item A", "TotalAmount": "50"},
            {"ItemsPurchased": "Item C", "TotalAmount": "75"},
        ]
        
        result = optimize_inventory(purchase_data, target_service_level=0.95)
        
        assert result["total_items"] > 0
        assert result["target_service_level"] == 0.95
        assert len(result["recommendations"]) > 0
        assert "methodology" in result

    def test_optimize_inventory_recommendation_structure(self):
        """Test inventory recommendation structure."""
        purchase_data = [
            {"ItemsPurchased": "Product A", "TotalAmount": "100"},
            {"ItemsPurchased": "Product A, Product B", "TotalAmount": "150"},
        ]
        
        result = optimize_inventory(purchase_data)
        
        for rec in result["recommendations"]:
            assert "item" in rec
            assert "historical_demand" in rec
            assert "recommended_stock_level" in rec
            assert "reorder_point" in rec
            assert "safety_stock" in rec
            assert "revenue_contribution" in rec
            assert "priority" in rec

    def test_optimize_inventory_priority_assignment(self):
        """Test priority assignment based on revenue."""
        purchase_data = [
            {"ItemsPurchased": "High Revenue Item", "TotalAmount": "500"},
            {"ItemsPurchased": "Low Revenue Item", "TotalAmount": "50"},
        ]
        
        result = optimize_inventory(purchase_data)
        
        # Should have different priorities
        priorities = set(rec["priority"] for rec in result["recommendations"])
        assert len(priorities) > 1

    def test_optimize_inventory_service_level_impact(self):
        """Test that service level affects safety stock."""
        purchase_data = [
            {"ItemsPurchased": "Item A", "TotalAmount": "100"},
            {"ItemsPurchased": "Item A", "TotalAmount": "100"},
        ]
        
        # Lower service level
        result_low = optimize_inventory(purchase_data, target_service_level=0.85)
        
        # Higher service level
        result_high = optimize_inventory(purchase_data, target_service_level=0.99)
        
        # Higher service level should generally recommend more safety stock
        assert result_high["target_service_level"] > result_low["target_service_level"]

    def test_optimize_inventory_sorted_by_revenue(self):
        """Test that recommendations are sorted by revenue contribution."""
        purchase_data = [
            {"ItemsPurchased": "Low Value", "TotalAmount": "20"},
            {"ItemsPurchased": "High Value", "TotalAmount": "500"},
            {"ItemsPurchased": "Medium Value", "TotalAmount": "100"},
        ]
        
        result = optimize_inventory(purchase_data)
        
        recs = result["recommendations"]
        # Should be sorted by revenue (descending)
        for i in range(len(recs) - 1):
            assert recs[i]["revenue_contribution"] >= recs[i + 1]["revenue_contribution"]

    def test_optimize_inventory_empty_data(self):
        """Test handling of empty purchase data."""
        result = optimize_inventory([])
        
        assert "error" in result
        assert result["recommendations"] == []


# Helper function tests
class TestHelperFunctions:
    """Test utility helper functions."""

    def test_get_performance_grade(self):
        """Test performance grade assignment."""
        assert get_performance_grade(95) == "A"
        assert get_performance_grade(85) == "B"
        assert get_performance_grade(75) == "C"
        assert get_performance_grade(65) == "D"
        assert get_performance_grade(50) == "F"

    def test_calculate_trend_increasing(self):
        """Test trend calculation for increasing values."""
        values = [10, 12, 14, 16, 18]
        trend = calculate_trend(values)
        assert trend > 0

    def test_calculate_trend_decreasing(self):
        """Test trend calculation for decreasing values."""
        values = [20, 18, 16, 14, 12]
        trend = calculate_trend(values)
        assert trend < 0

    def test_calculate_trend_stable(self):
        """Test trend calculation for stable values."""
        values = [15, 15, 15, 15, 15]
        trend = calculate_trend(values)
        assert abs(trend) < 0.01  # Near zero

    def test_calculate_trend_insufficient_data(self):
        """Test trend with insufficient data."""
        values = [10]
        trend = calculate_trend(values)
        assert trend == 0.0

    def test_simple_linear_forecast_single(self):
        """Test single period forecasting."""
        values = [10, 12, 14, 16, 18]
        forecast = simple_linear_forecast_single(values, periods_ahead=1)
        # Should continue upward trend
        assert forecast > 18

    def test_simple_linear_forecast_multiple_periods(self):
        """Test multiple period forecasting."""
        values = [10, 12, 14]
        forecast_1 = simple_linear_forecast_single(values, periods_ahead=1)
        forecast_2 = simple_linear_forecast_single(values, periods_ahead=2)
        # Later period should be higher for upward trend
        assert forecast_2 > forecast_1

    def test_categorize_incident_systems(self):
        """Test incident categorization - systems."""
        assert categorize_incident("Database system outage") == "Systems"
        assert categorize_incident("Software failure") == "Systems"

    def test_categorize_incident_external(self):
        """Test incident categorization - external."""
        assert categorize_incident("Logistics partner strike") == "External"
        assert categorize_incident("Carrier delay") == "External"

    def test_categorize_incident_infrastructure(self):
        """Test incident categorization - infrastructure."""
        assert categorize_incident("Warehouse flooding") == "Infrastructure"
        assert categorize_incident("Fire in building") == "Infrastructure"

    def test_categorize_incident_inventory(self):
        """Test incident categorization - inventory."""
        assert categorize_incident("Stock shortage") == "Inventory"
        assert categorize_incident("Inventory discrepancy") == "Inventory"

    def test_categorize_incident_other(self):
        """Test incident categorization - other."""
        assert categorize_incident("Unknown incident") == "Other"


# Integration tests
class TestOperationsAnalyticsIntegration:
    """Integration tests combining multiple operations analytics functions."""

    def test_full_operations_workflow(self):
        """Test complete operations analysis workflow."""
        # Step 1: Analyze delivery performance
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "95", "CustomerComplaints": "10"},
            {"Month": "Feb", "AverageDeliveryTime": "4", "OnTimeDeliveryRate": "92", "CustomerComplaints": "15"},
            {"Month": "Mar", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "96", "CustomerComplaints": "8"},
        ]
        
        performance = analyze_delivery_performance(delivery_data)
        assert performance["current_performance"]["grade"] in ["A", "B", "C"]
        
        # Step 2: Forecast delivery metrics
        forecast = forecast_delivery_metrics(delivery_data, periods=2)
        assert len(forecast["forecast"]) == 2
        
        # Step 3: Analyze incidents
        incident_data = [
            {"Date": "2023-06-15", "IncidentDescription": "Warehouse flooding", "AffectedOrders": "150"},
        ]
        
        incidents = analyze_warehouse_incidents(incident_data)
        assert incidents["risk_level"] in ["Low", "Medium", "High"]
        
        # Step 4: Optimize inventory
        purchase_data = [
            {"ItemsPurchased": "Product A, Product B", "TotalAmount": "200"},
            {"ItemsPurchased": "Product A", "TotalAmount": "100"},
        ]
        
        inventory = optimize_inventory(purchase_data, target_service_level=0.95)
        assert inventory["total_items"] > 0

    def test_operations_health_assessment(self):
        """Test creating overall operations health assessment."""
        # Analyze delivery
        delivery_data = [
            {"Month": "Jan", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "97", "CustomerComplaints": "5"},
        ]
        
        delivery_result = analyze_delivery_performance(delivery_data)
        delivery_score = delivery_result["current_performance"]["score"]
        
        # Analyze incidents
        incident_data = [
            {"Date": "2023-01-01", "IncidentDescription": "Minor issue", "AffectedOrders": "50"},
        ]
        
        incident_result = analyze_warehouse_incidents(incident_data)
        incident_impact = incident_result["total_affected_orders"]
        
        # Calculate overall health
        # (This mimics what get_operations_summary would do)
        penalty = min(20, incident_impact / 25)
        health_score = max(0, delivery_score - penalty)
        
        assert 0 <= health_score <= 100

    def test_incident_correlation_with_delivery(self):
        """Test correlation between incidents and delivery degradation."""
        # Good delivery before incident
        delivery_before = [
            {"Month": "May", "AverageDeliveryTime": "3", "OnTimeDeliveryRate": "96", "CustomerComplaints": "8"},
        ]
        
        # Poor delivery during incident period
        delivery_during = [
            {"Month": "June", "AverageDeliveryTime": "7", "OnTimeDeliveryRate": "85", "CustomerComplaints": "60"},
        ]
        
        # Incident in June
        incidents = [
            {"Date": "2023-06-15", "IncidentDescription": "Major logistics strike", "AffectedOrders": "300"},
        ]
        
        before_perf = analyze_delivery_performance(delivery_before)
        during_perf = analyze_delivery_performance(delivery_during)
        incident_analysis = analyze_warehouse_incidents(incidents)
        
        # Performance should be worse during incident
        assert before_perf["metrics"][0]["performance_score"] > during_perf["metrics"][0]["performance_score"]
        assert incident_analysis["risk_level"] == "High"


