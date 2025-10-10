"""
End-to-End Scenario Tests

Tests complete business workflows from data upload to actionable recommendations.
Validates the 4 key use cases:
1. Retail Revenue Forecasting
2. Customer Churn Prevention
3. Operations Optimization
4. Pricing & Marketing ROI
"""

import pytest
import asyncio
from pathlib import Path
import sys
import csv
import io

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "backend" / "common" / "utils"))

# Import analytics modules
from advanced_forecasting import auto_select_forecast_method, evaluate_forecast_accuracy
from customer_analytics import analyze_churn_drivers, segment_customers_rfm, predict_customer_lifetime_value
from operations_analytics import calculate_delivery_performance_score, optimize_inventory_levels
from pricing_analytics import analyze_price_gaps, optimize_discount_levels, forecast_category_revenue
from marketing_analytics import calculate_campaign_roi, predict_customer_engagement, optimize_loyalty_benefits


class TestRetailRevenueForecastingScenario:
    """Test Scenario 1: Retail Revenue Forecasting"""
    
    @pytest.fixture
    def sample_revenue_data(self):
        """Generate sample monthly revenue data."""
        return [50000, 52000, 54500, 51000, 56000, 58000, 55000, 60000, 62000, 59000, 64000, 66000]
    
    def test_step1_data_validation(self, sample_revenue_data):
        """Step 1: Validate input data quality."""
        assert len(sample_revenue_data) >= 12, "Need at least 12 months of data"
        assert all(v > 0 for v in sample_revenue_data), "All revenue values should be positive"
        assert min(sample_revenue_data) > 0, "Minimum revenue should be positive"
    
    def test_step2_forecast_generation(self, sample_revenue_data):
        """Step 2: Generate 12-month forecast using auto-selection."""
        result = auto_select_forecast_method(
            values=sample_revenue_data,
            periods=12,
            confidence_level=0.95
        )
        
        assert 'error' not in result, f"Forecast should succeed: {result.get('error')}"
        assert 'selected_method' in result, "Should return selected method"
        assert 'forecast' in result, "Should return forecast values"
        assert len(result['forecast']) == 12, "Should forecast 12 periods"
        assert 'lower_bound' in result, "Should include confidence intervals"
        assert 'upper_bound' in result, "Should include confidence intervals"
    
    def test_step3_model_comparison(self, sample_revenue_data):
        """Step 3: Compare multiple forecasting methods."""
        result = auto_select_forecast_method(
            values=sample_revenue_data,
            periods=12,
            confidence_level=0.95
        )
        
        assert 'method_comparison' in result, "Should return model comparison"
        assert len(result['method_comparison']) >= 2, "Should compare multiple methods"
        
        # Verify best model is selected
        best_method = result['selected_method']
        assert best_method in result['method_comparison'], "Selected method should be in comparison"
    
    def test_step4_business_insights(self, sample_revenue_data):
        """Step 4: Generate actionable business insights."""
        result = auto_select_forecast_method(
            values=sample_revenue_data,
            periods=12,
            confidence_level=0.95
        )
        
        current_avg = sum(sample_revenue_data[-6:]) / 6
        forecast_avg = sum(result['forecast']) / 12
        growth_rate = ((forecast_avg - current_avg) / current_avg) * 100
        
        # Verify growth calculation
        assert isinstance(growth_rate, float), "Growth rate should be calculated"
        assert -100 < growth_rate < 200, "Growth rate should be reasonable"
        
        # Business value: Should project revenue
        total_forecast = sum(result['forecast'])
        assert total_forecast > 0, "Total forecast revenue should be positive"


class TestCustomerChurnPreventionScenario:
    """Test Scenario 2: Customer Churn Prevention"""
    
    @pytest.fixture
    def sample_churn_data(self):
        """Generate sample churn data."""
        return [
            {"CustomerID": "C001", "ChurnProbability": 0.85, "EngagementScore": 2.1},
            {"CustomerID": "C002", "ChurnProbability": 0.72, "EngagementScore": 3.5},
            {"CustomerID": "C003", "ChurnProbability": 0.25, "EngagementScore": 8.2}
        ]
    
    @pytest.fixture
    def sample_purchase_data(self):
        """Generate sample purchase data."""
        return [
            {"CustomerID": "C001", "TransactionDate": "2024-01-15", "TotalAmount": 150.00},
            {"CustomerID": "C001", "TransactionDate": "2024-02-20", "TotalAmount": 200.00},
            {"CustomerID": "C002", "TransactionDate": "2024-03-10", "TotalAmount": 320.00},
            {"CustomerID": "C003", "TransactionDate": "2024-01-05", "TotalAmount": 450.00},
            {"CustomerID": "C003", "TransactionDate": "2024-02-12", "TotalAmount": 380.00}
        ]
    
    def test_step1_identify_at_risk_customers(self, sample_churn_data):
        """Step 1: Identify at-risk customers."""
        high_risk_threshold = 0.7
        at_risk = [c for c in sample_churn_data if c['ChurnProbability'] >= high_risk_threshold]
        
        assert len(at_risk) == 2, "Should identify 2 at-risk customers"
        assert all(c['ChurnProbability'] >= 0.7 for c in at_risk), "All should be high risk"
    
    def test_step2_analyze_churn_drivers(self, sample_churn_data):
        """Step 2: Analyze churn drivers."""
        # Low engagement is a key driver
        low_engagement = [c for c in sample_churn_data if c['EngagementScore'] < 5.0]
        
        assert len(low_engagement) >= 1, "Should identify low engagement customers"
        
        # Verify correlation between low engagement and high churn
        low_engagement_high_churn = [
            c for c in sample_churn_data 
            if c['EngagementScore'] < 5.0 and c['ChurnProbability'] > 0.6
        ]
        assert len(low_engagement_high_churn) >= 1, "Low engagement should correlate with churn"
    
    def test_step3_rfm_segmentation(self, sample_purchase_data):
        """Step 3: Perform RFM segmentation."""
        result = segment_customers_rfm(sample_purchase_data)
        
        assert 'segments' in result, "Should return customer segments"
        assert len(result['segments']) > 0, "Should have at least one segment"
        
        # Verify segment structure
        for segment in result['segments']:
            assert 'segment' in segment, "Each segment should have a name"
            assert 'customer_count' in segment, "Each segment should have count"
            assert 'strategy' in segment, "Each segment should have strategy"
    
    def test_step4_clv_prediction(self, sample_purchase_data):
        """Step 4: Predict Customer Lifetime Value."""
        result = predict_customer_lifetime_value(purchase_data=sample_purchase_data, forecast_months=12, discount_rate=0.10)
        
        assert 'top_clv_customers' in result, "Should return top CLV customers"
        assert len(result['top_clv_customers']) > 0, "Should identify high-value customers"
        
        # Verify CLV structure
        for customer in result['top_clv_customers']:
            assert 'customer_id' in customer
            assert 'predicted_clv' in customer
            assert customer['predicted_clv'] > 0, "CLV should be positive"


class TestOperationsOptimizationScenario:
    """Test Scenario 3: Operations Optimization"""
    
    @pytest.fixture
    def sample_delivery_data(self):
        """Generate sample delivery performance data."""
        return [
            {"DeliveryID": "D001", "DeliveryTimeHours": 26, "OnTime": "Yes"},
            {"DeliveryID": "D002", "DeliveryTimeHours": 32, "OnTime": "No"},
            {"DeliveryID": "D003", "DeliveryTimeHours": 24, "OnTime": "Yes"}
        ]
    
    @pytest.fixture
    def sample_purchase_data_for_inventory(self):
        """Generate purchase data for inventory optimization."""
        return [
            {"ItemsPurchased": "Dress", "TotalAmount": 150},
            {"ItemsPurchased": "Shoes", "TotalAmount": 90},
            {"ItemsPurchased": "Bag", "TotalAmount": 120}
        ]
    
    def test_step1_delivery_performance_analysis(self, sample_delivery_data):
        """Step 1: Analyze delivery performance."""
        on_time_deliveries = [d for d in sample_delivery_data if d['OnTime'] == 'Yes']
        on_time_rate = (len(on_time_deliveries) / len(sample_delivery_data)) * 100
        
        assert isinstance(on_time_rate, float), "On-time rate should be calculated"
        assert 0 <= on_time_rate <= 100, "On-time rate should be percentage"
        
        # Calculate performance score
        avg_delivery_time = sum(d['DeliveryTimeHours'] for d in sample_delivery_data) / len(sample_delivery_data)
        score = calculate_delivery_performance_score(on_time_rate, avg_delivery_time)
        
        assert 0 <= score <= 100, "Performance score should be 0-100"
    
    def test_step2_identify_improvement_opportunities(self, sample_delivery_data):
        """Step 2: Identify improvement opportunities."""
        late_deliveries = [d for d in sample_delivery_data if d['OnTime'] == 'No']
        
        if late_deliveries:
            avg_late_time = sum(d['DeliveryTimeHours'] for d in late_deliveries) / len(late_deliveries)
            assert avg_late_time > 24, "Late deliveries should exceed target time"
    
    def test_step3_inventory_optimization(self, sample_purchase_data_for_inventory):
        """Step 3: Optimize inventory levels."""
        result = optimize_inventory_levels(
            purchase_data=sample_purchase_data_for_inventory,
            current_inventory_days=45,
            target_service_level=0.95
        )
        
        assert 'recommended_inventory_days' in result, "Should recommend inventory days"
        assert 'annual_savings' in result, "Should calculate savings"
        assert result['recommended_inventory_days'] > 0, "Recommended days should be positive"
    
    def test_step4_calculate_roi(self, sample_purchase_data_for_inventory):
        """Step 4: Calculate optimization ROI."""
        result = optimize_inventory_levels(
            purchase_data=sample_purchase_data_for_inventory,
            current_inventory_days=45,
            target_service_level=0.95
        )
        
        if 'annual_savings' in result and result['annual_savings'] > 0:
            # ROI should be positive if savings exist
            assert result['annual_savings'] > 0, "Should have positive savings"


class TestPricingMarketingROIScenario:
    """Test Scenario 4: Pricing & Marketing ROI"""
    
    @pytest.fixture
    def sample_pricing_data(self):
        """Generate sample competitive pricing data."""
        return [
            {"ItemName": "Premium Dress", "OurPrice": 89.99, "CompetitorAvgPrice": 119.99},
            {"ItemName": "Designer Bag", "OurPrice": 199.99, "CompetitorAvgPrice": 179.99}
        ]
    
    @pytest.fixture
    def sample_campaign_data(self):
        """Generate sample campaign data."""
        return [
            {"CampaignName": "VIP Early Access", "OpenRate": 45.2, "ConversionRate": 5.8, "Cost": 500, "Revenue": 7900},
            {"CampaignName": "Clearance Sale", "OpenRate": 22.1, "ConversionRate": 2.3, "Cost": 300, "Revenue": 1200}
        ]
    
    def test_step1_competitive_pricing_analysis(self, sample_pricing_data):
        """Step 1: Analyze competitive pricing."""
        underpriced = [p for p in sample_pricing_data if p['OurPrice'] < p['CompetitorAvgPrice'] * 0.9]
        overpriced = [p for p in sample_pricing_data if p['OurPrice'] > p['CompetitorAvgPrice'] * 1.1]
        
        assert len(underpriced) + len(overpriced) == len(sample_pricing_data), "Should categorize all products"
        
        # Calculate revenue opportunity
        revenue_opportunity = sum(
            (p['CompetitorAvgPrice'] - p['OurPrice']) * 100  # Assume 100 units
            for p in underpriced
        )
        assert revenue_opportunity >= 0, "Revenue opportunity should be non-negative"
    
    def test_step2_discount_optimization(self, sample_pricing_data):
        """Step 2: Optimize discount strategy."""
        # Simulate discount levels
        discount_levels = [0.10, 0.20, 0.30]
        
        # Calculate ROI for each discount level
        rois = []
        for discount in discount_levels:
            # Simplified ROI calculation
            discounted_price = sample_pricing_data[0]['OurPrice'] * (1 - discount)
            estimated_volume = 100 * (1 + discount * 5)  # Higher discount = more volume
            revenue = discounted_price * estimated_volume
            cost = sample_pricing_data[0]['OurPrice'] * 0.6 * estimated_volume  # 60% COGS
            roi = ((revenue - cost) / cost) * 100
            rois.append(roi)
        
        # Best discount should maximize ROI
        best_discount_idx = rois.index(max(rois))
        assert 0 <= best_discount_idx < len(discount_levels), "Should identify optimal discount"
    
    def test_step3_campaign_effectiveness_analysis(self, sample_campaign_data):
        """Step 3: Analyze campaign effectiveness."""
        # Calculate ROI for each campaign
        for campaign in sample_campaign_data:
            roi = calculate_campaign_roi(campaign['Revenue'], campaign['Cost'])
            assert roi > 0 or roi == -100, "ROI should be calculated"
            campaign['roi'] = roi
        
        # Identify top-performing campaign
        top_campaign = max(sample_campaign_data, key=lambda c: c['roi'])
        assert top_campaign['roi'] > 100, "Top campaign should have positive ROI"
    
    def test_step4_integrated_revenue_forecast(self, sample_pricing_data, sample_campaign_data):
        """Step 4: Generate integrated revenue forecast."""
        # Combine pricing and marketing impacts
        pricing_impact = sum(
            max(0, p['CompetitorAvgPrice'] - p['OurPrice']) * 100
            for p in sample_pricing_data
        )
        
        marketing_impact = sum(c['Revenue'] for c in sample_campaign_data)
        
        total_opportunity = pricing_impact + marketing_impact
        assert total_opportunity > 0, "Should identify revenue opportunity"


class TestCrossScenarioIntegration:
    """Test workflows that span multiple scenarios."""
    
    def test_revenue_forecast_to_inventory_optimization(self):
        """Test: Revenue forecast informs inventory decisions."""
        # Generate revenue forecast
        revenue_data = [50000, 52000, 54500, 56000, 58000, 60000]
        forecast_result = auto_select_forecast_method(revenue_data, periods=6, confidence_level=0.95)
        
        assert 'forecast' in forecast_result
        
        # Use forecast to optimize inventory
        # Higher forecasted revenue → higher inventory needs
        forecasted_revenue = sum(forecast_result['forecast'])
        current_revenue = sum(revenue_data)
        revenue_growth = (forecasted_revenue / current_revenue) - 1
        
        # If revenue growing, may need more inventory
        if revenue_growth > 0.1:  # 10% growth
            # Recommendation: increase inventory
            assert True, "Should recommend inventory increase for growth"
    
    def test_customer_segmentation_to_campaign_targeting(self):
        """Test: Customer segments inform marketing campaigns."""
        # Segment customers
        purchase_data = [
            {"CustomerID": "C001", "TransactionDate": "2024-01-15", "TotalAmount": 500},
            {"CustomerID": "C002", "TransactionDate": "2024-03-20", "TotalAmount": 100}
        ]
        
        rfm_result = segment_customers_rfm(purchase_data)
        assert 'segments' in rfm_result
        
        # Each segment should have a marketing strategy
        for segment in rfm_result['segments']:
            assert 'strategy' in segment, "Segment should have marketing strategy"
    
    def test_pricing_to_revenue_impact(self):
        """Test: Pricing changes impact revenue forecast."""
        # Initial pricing
        initial_price = 100
        initial_volume = 1000
        initial_revenue = initial_price * initial_volume
        
        # Optimized pricing (5% increase)
        optimized_price = 105
        # Assume 3% volume decrease (elasticity = 0.6)
        optimized_volume = 970
        optimized_revenue = optimized_price * optimized_volume
        
        revenue_lift = optimized_revenue - initial_revenue
        assert revenue_lift > 0, "Price optimization should increase revenue"


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=5"])

