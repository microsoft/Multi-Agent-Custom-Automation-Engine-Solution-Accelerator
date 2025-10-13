#!/usr/bin/env python3
"""
Comprehensive Agent-MCP Integration Tests

This test suite validates that agents can:
1. Discover datasets using list_finance_datasets
2. Automatically match dataset names to dataset_ids
3. Use MCP tools to analyze and forecast data
4. Complete full workflows without excessive clarification requests

Each test simulates a complete user conversation with expected agent behaviors.
"""

import sys
import json
import pytest
from pathlib import Path
from typing import Dict, Any, List

# Add backend utilities to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "src" / "backend" / "common" / "utils"))

from advanced_forecasting import (
    linear_forecast_with_confidence,
    sarima_forecast,
    auto_select_forecast_method,
    evaluate_forecast_accuracy
)
from customer_analytics import (
    analyze_churn_drivers,
    segment_customers_rfm,
    predict_customer_lifetime_value
)
from operations_analytics import (
    forecast_delivery_performance,
    optimize_inventory_levels,
    analyze_warehouse_incident_severity
)
from pricing_analytics import (
    analyze_competitive_pricing,
    optimize_discount_strategy,
    forecast_revenue_by_category
)
from marketing_analytics import (
    analyze_campaign_effectiveness,
    predict_customer_engagement,
    optimize_loyalty_program
)


# ============================================================================
# Test Fixtures - Simulate Dataset Discovery
# ============================================================================

@pytest.fixture
def mock_uploaded_datasets():
    """Simulate the output of list_finance_datasets MCP tool"""
    return {
        "datasets": [
            {
                "dataset_id": "40adbd2f-0a3d-432c-9ff5-73abcbb2f455",
                "original_filename": "purchase_history.csv",
                "uploaded_at": "2025-10-13T15:56:39.497163+00:00",
                "size_bytes": 503,
                "numeric_columns": ["TotalAmount", "DiscountApplied"]
            },
            {
                "dataset_id": "abc123-delivery-metrics",
                "original_filename": "delivery_performance_metrics.csv",
                "uploaded_at": "2025-10-13T14:00:00.000000+00:00",
                "size_bytes": 1024,
                "numeric_columns": ["OnTimeDeliveries", "LateDeliveries"]
            },
            {
                "dataset_id": "def456-customer-churn",
                "original_filename": "customer_churn_analysis.csv",
                "uploaded_at": "2025-10-13T13:00:00.000000+00:00",
                "size_bytes": 2048,
                "numeric_columns": ["Recency", "Frequency", "MonetaryValue"]
            }
        ]
    }


@pytest.fixture
def sample_purchase_data():
    """Sample purchase history data for testing"""
    return [
        {"OrderID": "O5678", "Date": "2023-03-15", "ItemsPurchased": "Dress", "TotalAmount": 150, "DiscountApplied": 10},
        {"OrderID": "O5721", "Date": "2023-04-10", "ItemsPurchased": "Boots", "TotalAmount": 120, "DiscountApplied": 15},
        {"OrderID": "O5789", "Date": "2023-05-05", "ItemsPurchased": "Scarf", "TotalAmount": 80, "DiscountApplied": 0},
        {"OrderID": "O5832", "Date": "2023-06-18", "ItemsPurchased": "Sneakers", "TotalAmount": 90, "DiscountApplied": 5},
        {"OrderID": "O5890", "Date": "2023-07-22", "ItemsPurchased": "Gown", "TotalAmount": 300, "DiscountApplied": 20},
        {"OrderID": "O5923", "Date": "2023-08-14", "ItemsPurchased": "Jacket", "TotalAmount": 200, "DiscountApplied": 25},
        {"OrderID": "O5967", "Date": "2023-09-18", "ItemsPurchased": "Leggings", "TotalAmount": 130, "DiscountApplied": 25},
    ]


# ============================================================================
# Helper Functions - Simulate Agent Behaviors
# ============================================================================

def agent_discovers_datasets(user_query: str, available_datasets: Dict[str, Any]) -> str:
    """
    Simulate an agent's dataset discovery logic.
    
    Expected behavior:
    1. Agent calls list_finance_datasets
    2. Agent matches user's natural language query to a dataset
    3. Agent returns the dataset_id to use
    """
    datasets = available_datasets.get("datasets", [])
    
    # Extract keywords from user query
    query_lower = user_query.lower()
    
    # Match keywords to dataset filenames
    for dataset in datasets:
        filename = dataset["original_filename"].lower()
        
        # Match common aliases
        if any(keyword in query_lower for keyword in ["purchase", "sales", "revenue"]):
            if "purchase" in filename or "sales" in filename:
                return dataset["dataset_id"]
        
        if any(keyword in query_lower for keyword in ["delivery", "shipping", "logistics"]):
            if "delivery" in filename or "performance" in filename:
                return dataset["dataset_id"]
        
        if any(keyword in query_lower for keyword in ["churn", "retention", "customer"]):
            if "churn" in filename or "customer" in filename:
                return dataset["dataset_id"]
    
    # If no match, return None (agent should ask for clarification)
    return None


def agent_should_ask_clarification(dataset_id: str, user_query: str) -> bool:
    """
    Determine if agent should ask for clarification.
    
    Expected behavior:
    - Only ask if dataset_id is None (no datasets found)
    - Do NOT ask if dataset was successfully discovered
    """
    return dataset_id is None


# ============================================================================
# Test Suite 1: Dataset Discovery and Matching
# ============================================================================

class TestDatasetDiscovery:
    """Test that agents can automatically discover and match datasets"""
    
    def test_finance_agent_discovers_purchase_data(self, mock_uploaded_datasets):
        """Financial Forecasting Agent should find purchase_history.csv automatically"""
        user_query = "Use our latest sales dataset to project revenue for the next quarter"
        
        dataset_id = agent_discovers_datasets(user_query, mock_uploaded_datasets)
        
        assert dataset_id is not None, "Agent should discover a dataset"
        assert dataset_id == "40adbd2f-0a3d-432c-9ff5-73abcbb2f455", "Should match purchase_history.csv"
        assert not agent_should_ask_clarification(dataset_id, user_query), "Should NOT ask for clarification"
    
    def test_operations_agent_discovers_delivery_data(self, mock_uploaded_datasets):
        """Operations Agent should find delivery_performance_metrics.csv automatically"""
        user_query = "Analyze delivery performance and forecast trends for next 3 months"
        
        dataset_id = agent_discovers_datasets(user_query, mock_uploaded_datasets)
        
        assert dataset_id is not None, "Agent should discover a dataset"
        assert dataset_id == "abc123-delivery-metrics", "Should match delivery_performance_metrics.csv"
        assert not agent_should_ask_clarification(dataset_id, user_query), "Should NOT ask for clarification"
    
    def test_customer_agent_discovers_churn_data(self, mock_uploaded_datasets):
        """Customer Intelligence Agent should find customer_churn_analysis.csv automatically"""
        user_query = "Identify top churn drivers and recommend retention strategies"
        
        dataset_id = agent_discovers_datasets(user_query, mock_uploaded_datasets)
        
        assert dataset_id is not None, "Agent should discover a dataset"
        assert dataset_id == "def456-customer-churn", "Should match customer_churn_analysis.csv"
        assert not agent_should_ask_clarification(dataset_id, user_query), "Should NOT ask for clarification"
    
    def test_agent_asks_clarification_when_no_datasets(self):
        """Agent should only ask for clarification if NO datasets are uploaded"""
        user_query = "Forecast revenue for next quarter"
        empty_datasets = {"datasets": []}
        
        dataset_id = agent_discovers_datasets(user_query, empty_datasets)
        
        assert dataset_id is None, "Should not find any dataset"
        assert agent_should_ask_clarification(dataset_id, user_query), "SHOULD ask for clarification"


# ============================================================================
# Test Suite 2: Full Agent Workflows
# ============================================================================

class TestFinanceForecastingWorkflow:
    """Test complete Financial Forecasting Agent workflow"""
    
    def test_revenue_forecast_workflow(self, sample_purchase_data):
        """
        Simulate: 'Use our latest sales dataset to project revenue for the next quarter'
        
        Expected agent flow:
        1. Call list_finance_datasets (mocked above)
        2. Match 'sales dataset' to dataset_id
        3. Call summarize_financial_dataset(dataset_id)
        4. Call generate_financial_forecast(dataset_id, column='TotalAmount', periods=3)
        5. Return forecast with confidence intervals
        """
        # Step 1 & 2: Dataset discovery (already tested above)
        dataset_id = "40adbd2f-0a3d-432c-9ff5-73abcbb2f455"
        
        # Step 3: Summarize dataset (extract numeric column)
        revenue_values = [row["TotalAmount"] for row in sample_purchase_data]
        
        # Step 4: Generate forecast
        forecast_result = linear_forecast_with_confidence(
            values=revenue_values,
            periods=3,
            confidence_level=0.95
        )
        
        # Step 5: Validate results
        assert "forecast" in forecast_result, "Should return forecast"
        assert "lower_bound" in forecast_result, "Should return confidence intervals"
        assert "upper_bound" in forecast_result, "Should return confidence intervals"
        assert len(forecast_result["forecast"]) == 3, "Should forecast 3 periods"
        
        # Validate forecast is reasonable (should be near average)
        avg_revenue = sum(revenue_values) / len(revenue_values)
        for forecast_value in forecast_result["forecast"]:
            assert 50 < forecast_value < 400, f"Forecast {forecast_value} should be reasonable"
    
    def test_model_comparison_workflow(self, sample_purchase_data):
        """
        Simulate: 'Compare different forecasting methods and recommend the best one'
        
        Expected agent flow:
        1. Discover dataset
        2. Call evaluate_forecast_models with multiple methods
        3. Return ranking of methods by accuracy
        """
        revenue_values = [row["TotalAmount"] for row in sample_purchase_data]
        
        # Auto-select best method
        best_method_result = auto_select_forecast_method(
            values=revenue_values,
            periods=2,
            methods=["linear", "exponential_smoothing"]
        )
        
        assert "best_method" in best_method_result, "Should identify best method"
        assert "forecast" in best_method_result, "Should return forecast from best method"
        assert "all_forecasts" in best_method_result, "Should return all method results"


class TestCustomerAnalyticsWorkflow:
    """Test complete Customer Intelligence Agent workflow"""
    
    def test_churn_analysis_workflow(self):
        """
        Simulate: 'Analyze customer churn drivers and recommend retention strategies'
        
        Expected agent flow:
        1. Discover customer_churn_analysis.csv dataset
        2. Call analyze_customer_churn(dataset_id)
        3. Return top churn drivers and retention recommendations
        """
        # Sample churn data
        churn_data = [
            {"CustomerID": "C001", "Recency": 120, "Frequency": 2, "MonetaryValue": 100, "Churned": 1},
            {"CustomerID": "C002", "Recency": 10, "Frequency": 15, "MonetaryValue": 5000, "Churned": 0},
            {"CustomerID": "C003", "Recency": 90, "Frequency": 3, "MonetaryValue": 200, "Churned": 1},
            {"CustomerID": "C004", "Recency": 5, "Frequency": 20, "MonetaryValue": 8000, "Churned": 0},
        ]
        
        # Analyze churn drivers
        churn_result = analyze_churn_drivers(churn_data)
        
        assert "drivers" in churn_result, "Should identify churn drivers"
        assert "recommendations" in churn_result, "Should provide recommendations"
        assert len(churn_result["drivers"]) > 0, "Should find at least one driver"
        
        # Validate recommendations are actionable
        recommendations = churn_result["recommendations"]
        assert len(recommendations) > 0, "Should provide at least one recommendation"
    
    def test_rfm_segmentation_workflow(self):
        """
        Simulate: 'Segment customers using RFM analysis and identify Champions'
        
        Expected agent flow:
        1. Discover dataset
        2. Call segment_customers(dataset_id, method='RFM')
        3. Return customer segments with characteristics
        """
        # Sample purchase data for RFM
        purchase_data = [
            {"CustomerID": "C001", "Date": "2024-01-15", "TotalAmount": 500},
            {"CustomerID": "C001", "Date": "2024-02-10", "TotalAmount": 300},
            {"CustomerID": "C002", "Date": "2023-06-01", "TotalAmount": 100},
            {"CustomerID": "C003", "Date": "2024-03-20", "TotalAmount": 1000},
            {"CustomerID": "C003", "Date": "2024-03-25", "TotalAmount": 1500},
            {"CustomerID": "C003", "Date": "2024-04-01", "TotalAmount": 2000},
        ]
        
        # Calculate RFM scores
        rfm_result = segment_customers_rfm(purchase_data, reference_date="2024-04-10")
        
        assert "segments" in rfm_result, "Should return customer segments"
        assert len(rfm_result["segments"]) > 0, "Should have at least one segment"
        
        # Validate segments have required fields
        for segment in rfm_result["segments"]:
            assert "customer_id" in segment, "Segment should have customer_id"
            assert "segment" in segment, "Segment should have segment label"
            assert segment["segment"] in ["Champions", "Loyal", "At Risk", "Lost", "Potential"], \
                f"Segment {segment['segment']} should be valid"


class TestOperationsAnalyticsWorkflow:
    """Test complete Operations Analytics Agent workflow"""
    
    def test_delivery_forecast_workflow(self):
        """
        Simulate: 'Forecast delivery performance for next 3 months'
        
        Expected agent flow:
        1. Discover delivery_performance_metrics.csv
        2. Call forecast_delivery_performance(dataset_id, periods=3)
        3. Return forecast with on-time delivery predictions
        """
        # Sample delivery data
        delivery_data = [
            {"Week": 1, "OnTimeDeliveries": 95, "TotalDeliveries": 100},
            {"Week": 2, "OnTimeDeliveries": 92, "TotalDeliveries": 100},
            {"Week": 3, "OnTimeDeliveries": 98, "TotalDeliveries": 100},
            {"Week": 4, "OnTimeDeliveries": 90, "TotalDeliveries": 100},
            {"Week": 5, "OnTimeDeliveries": 94, "TotalDeliveries": 100},
        ]
        
        # Forecast delivery performance
        forecast_result = forecast_delivery_performance(delivery_data, periods=3)
        
        assert "forecast" in forecast_result, "Should return forecast"
        assert "on_time_rate_forecast" in forecast_result, "Should forecast on-time rate"
        assert len(forecast_result["on_time_rate_forecast"]) == 3, "Should forecast 3 periods"
        
        # Validate forecast is within reasonable bounds (0-100%)
        for rate in forecast_result["on_time_rate_forecast"]:
            assert 0 <= rate <= 100, f"On-time rate {rate}% should be between 0-100%"
    
    def test_inventory_optimization_workflow(self):
        """
        Simulate: 'Optimize inventory levels for 95% service level'
        
        Expected agent flow:
        1. Discover purchase_history.csv
        2. Call optimize_inventory(dataset_id, service_level=0.95)
        3. Return reorder points and optimal stock levels
        """
        # Sample purchase data
        purchase_data = [
            {"Category": "Dresses", "ItemsPurchased": 5, "Date": "2024-01-15"},
            {"Category": "Dresses", "ItemsPurchased": 3, "Date": "2024-01-20"},
            {"Category": "Shoes", "ItemsPurchased": 2, "Date": "2024-01-18"},
            {"Category": "Dresses", "ItemsPurchased": 7, "Date": "2024-01-25"},
            {"Category": "Shoes", "ItemsPurchased": 4, "Date": "2024-01-28"},
        ]
        
        # Optimize inventory
        inventory_result = optimize_inventory_levels(purchase_data, service_level=0.95)
        
        assert "recommendations" in inventory_result, "Should return recommendations"
        assert len(inventory_result["recommendations"]) > 0, "Should have at least one recommendation"
        
        # Validate recommendations have required fields
        for rec in inventory_result["recommendations"]:
            assert "category" in rec, "Should specify category"
            assert "reorder_point" in rec, "Should specify reorder point"
            assert "optimal_stock" in rec, "Should specify optimal stock level"


class TestPricingAnalyticsWorkflow:
    """Test complete Pricing Analytics Agent workflow"""
    
    def test_competitive_pricing_workflow(self):
        """
        Simulate: 'Analyze competitive pricing and recommend price adjustments'
        
        Expected agent flow:
        1. Discover competitor_pricing_analysis.csv
        2. Call competitive_price_analysis(dataset_id)
        3. Return overpriced/underpriced categories with recommendations
        """
        # Sample pricing data
        pricing_data = [
            {"Category": "Dresses", "OurPrice": 150, "CompetitorPrice": 120, "ReturnRate": 0.05},
            {"Category": "Shoes", "OurPrice": 80, "CompetitorPrice": 90, "ReturnRate": 0.02},
            {"Category": "Accessories", "OurPrice": 30, "CompetitorPrice": 35, "ReturnRate": 0.01},
        ]
        
        # Analyze competitive pricing
        pricing_result = analyze_competitive_pricing(pricing_data)
        
        assert "analysis" in pricing_result, "Should return pricing analysis"
        assert "recommendations" in pricing_result, "Should return recommendations"
        
        # Validate recommendations are actionable
        recommendations = pricing_result["recommendations"]
        assert len(recommendations) > 0, "Should provide at least one recommendation"
        
        # Dresses should be flagged as overpriced
        dress_recs = [r for r in recommendations if "Dresses" in r.get("category", "")]
        assert len(dress_recs) > 0, "Should recommend action for overpriced Dresses"


class TestMarketingAnalyticsWorkflow:
    """Test complete Marketing Analytics Agent workflow"""
    
    def test_campaign_effectiveness_workflow(self):
        """
        Simulate: 'Analyze email campaign effectiveness and recommend improvements'
        
        Expected agent flow:
        1. Discover email_marketing_engagement.csv
        2. Call analyze_campaign_effectiveness(dataset_id)
        3. Return best/worst performers with improvement recommendations
        """
        # Sample campaign data
        campaign_data = [
            {"CampaignID": "C001", "CampaignType": "Promotional", "EmailsSent": 1000, "Opened": 500, "Clicked": 200, "Unsubscribed": 10},
            {"CampaignID": "C002", "CampaignType": "Newsletter", "EmailsSent": 1000, "Opened": 0, "Clicked": 0, "Unsubscribed": 50},
            {"CampaignID": "C003", "CampaignType": "Seasonal", "EmailsSent": 1000, "Opened": 700, "Clicked": 350, "Unsubscribed": 5},
        ]
        
        # Analyze campaign effectiveness
        campaign_result = analyze_campaign_effectiveness(campaign_data)
        
        assert "best_performers" in campaign_result, "Should identify best performers"
        assert "worst_performers" in campaign_result, "Should identify worst performers"
        assert "recommendations" in campaign_result, "Should provide recommendations"
        
        # C002 should be flagged as worst performer (0% open rate)
        worst = campaign_result["worst_performers"]
        assert len(worst) > 0, "Should identify at least one worst performer"
        assert any(c["campaign_id"] == "C002" for c in worst), "C002 should be worst performer"


# ============================================================================
# Test Suite 3: Error Handling and Edge Cases
# ============================================================================

class TestAgentErrorHandling:
    """Test that agents handle errors gracefully"""
    
    def test_forecast_with_insufficient_data(self):
        """Agent should handle datasets with too few data points"""
        short_data = [100, 110]  # Only 2 points
        
        # Linear forecast should still work
        result = linear_forecast_with_confidence(short_data, periods=1)
        assert "forecast" in result, "Should handle short datasets gracefully"
    
    def test_churn_analysis_with_no_churned_customers(self):
        """Agent should handle datasets where no customers churned"""
        no_churn_data = [
            {"CustomerID": "C001", "Recency": 10, "Frequency": 15, "MonetaryValue": 5000, "Churned": 0},
            {"CustomerID": "C002", "Recency": 5, "Frequency": 20, "MonetaryValue": 8000, "Churned": 0},
        ]
        
        # Should still provide analysis
        result = analyze_churn_drivers(no_churn_data)
        assert "drivers" in result or "message" in result, "Should handle no-churn scenario"
    
    def test_inventory_with_single_category(self):
        """Agent should handle inventory optimization with only one category"""
        single_category_data = [
            {"Category": "Dresses", "ItemsPurchased": 5, "Date": "2024-01-15"},
            {"Category": "Dresses", "ItemsPurchased": 3, "Date": "2024-01-20"},
        ]
        
        result = optimize_inventory_levels(single_category_data, service_level=0.95)
        assert "recommendations" in result, "Should handle single category"
        assert len(result["recommendations"]) >= 1, "Should provide recommendation for the category"


# ============================================================================
# Performance and Integration Tests
# ============================================================================

class TestAgentPerformance:
    """Test that agents complete tasks within acceptable time"""
    
    def test_forecast_completes_quickly(self, sample_purchase_data):
        """Forecast should complete in under 5 seconds"""
        import time
        
        revenue_values = [row["TotalAmount"] for row in sample_purchase_data]
        
        start_time = time.time()
        result = linear_forecast_with_confidence(revenue_values, periods=3)
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 5.0, f"Forecast took {elapsed_time}s, should be < 5s"
        assert "forecast" in result, "Should return valid result"
    
    def test_multiple_methods_comparison_performance(self, sample_purchase_data):
        """Model comparison should complete in under 10 seconds"""
        import time
        
        revenue_values = [row["TotalAmount"] for row in sample_purchase_data]
        
        start_time = time.time()
        result = auto_select_forecast_method(
            values=revenue_values,
            periods=2,
            methods=["linear", "exponential_smoothing"]
        )
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 10.0, f"Model comparison took {elapsed_time}s, should be < 10s"
        assert "best_method" in result, "Should return valid result"


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("  AGENT-MCP INTEGRATION TEST SUITE")
    print("="*70)
    print()
    print("Testing agent workflows:")
    print("  1. Dataset Discovery & Matching")
    print("  2. Financial Forecasting Workflows")
    print("  3. Customer Analytics Workflows")
    print("  4. Operations Analytics Workflows")
    print("  5. Pricing Analytics Workflows")
    print("  6. Marketing Analytics Workflows")
    print("  7. Error Handling")
    print("  8. Performance")
    print()
    print("="*70)
    print()
    
    # Run pytest with verbose output
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
        "-v"
    ])
    
    sys.exit(exit_code)

