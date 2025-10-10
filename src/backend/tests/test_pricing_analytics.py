"""
Unit tests for pricing analytics utilities.

Tests cover competitive pricing analysis, discount optimization,
and revenue forecasting by category.
"""

import pytest
from common.utils.pricing_analytics import (
    analyze_competitive_pricing,
    generate_pricing_recommendation,
    get_top_pricing_actions,
    optimize_discount_strategy,
    forecast_revenue_by_category,
    categorize_item,
)


class TestAnalyzeCompetitivePricing:
    """Test competitive pricing analysis functionality."""

    def test_analyze_pricing_basic(self):
        """Test basic competitive pricing analysis."""
        pricing_data = [
            {"ProductCategory": "Dresses", "ContosoAveragePrice": "120", "CompetitorAveragePrice": "100"},
            {"ProductCategory": "Shoes", "ContosoAveragePrice": "100", "CompetitorAveragePrice": "105"},
            {"ProductCategory": "Accessories", "ContosoAveragePrice": "60", "CompetitorAveragePrice": "55"},
        ]
        
        result = analyze_competitive_pricing(pricing_data)
        
        assert result["total_categories"] == 3
        assert len(result["category_analysis"]) == 3
        assert "avg_price_gap_percent" in result
        assert "overall_strategy" in result

    def test_analyze_pricing_overpriced_category(self):
        """Test identification of overpriced categories."""
        pricing_data = [
            {"ProductCategory": "Dresses", "ContosoAveragePrice": "120", "CompetitorAveragePrice": "100"},
        ]
        
        result = analyze_competitive_pricing(pricing_data)
        
        category = result["category_analysis"][0]
        assert category["price_gap"] == 20.0
        assert category["price_gap_percent"] == 20.0
        assert category["positioning"] == "Overpriced"
        assert category["suggested_price"] < category["our_price"]

    def test_analyze_pricing_underpriced_category(self):
        """Test identification of underpriced categories."""
        pricing_data = [
            {"ProductCategory": "Shoes", "ContosoAveragePrice": "80", "CompetitorAveragePrice": "100"},
        ]
        
        result = analyze_competitive_pricing(pricing_data)
        
        category = result["category_analysis"][0]
        assert category["price_gap"] == -20.0
        assert category["price_gap_percent"] == -20.0
        assert category["positioning"] == "Underpriced"

    def test_analyze_pricing_with_return_rates(self):
        """Test pricing analysis with product return rate data."""
        pricing_data = [
            {"ProductCategory": "Dresses", "ContosoAveragePrice": "120", "CompetitorAveragePrice": "100"},
        ]
        
        product_data = [
            {"ProductCategory": "Dresses", "ReturnRate": "15"},
        ]
        
        result = analyze_competitive_pricing(pricing_data, product_data)
        
        category = result["category_analysis"][0]
        assert category["return_rate"] == 15.0
        # High return rate + overpricing should be flagged in recommendation
        assert "return" in category["recommendation"].lower() or "quality" in category["recommendation"].lower()

    def test_analyze_pricing_competitive_positioning(self):
        """Test competitive positioning classification."""
        pricing_data = [
            {"ProductCategory": "Premium", "ContosoAveragePrice": "105", "CompetitorAveragePrice": "100"},
            {"ProductCategory": "Competitive", "ContosoAveragePrice": "98", "CompetitorAveragePrice": "100"},
        ]
        
        result = analyze_competitive_pricing(pricing_data)
        
        # Premium: 5% above
        premium = next(c for c in result["category_analysis"] if c["category"] == "Premium")
        assert premium["positioning"] in ["Premium", "Overpriced"]
        
        # Competitive: 2% below
        competitive = next(c for c in result["category_analysis"] if c["category"] == "Competitive")
        assert competitive["positioning"] == "Competitive"

    def test_analyze_pricing_strategy_recommendation(self):
        """Test overall strategy recommendation based on pricing mix."""
        # More overpriced than underpriced
        pricing_data = [
            {"ProductCategory": "Cat1", "ContosoAveragePrice": "120", "CompetitorAveragePrice": "100"},
            {"ProductCategory": "Cat2", "ContosoAveragePrice": "115", "CompetitorAveragePrice": "100"},
            {"ProductCategory": "Cat3", "ContosoAveragePrice": "90", "CompetitorAveragePrice": "100"},
        ]
        
        result = analyze_competitive_pricing(pricing_data)
        
        assert result["overpriced_categories"] == 2
        assert result["underpriced_categories"] == 1
        assert "Price Reduction" in result["overall_strategy"]

    def test_analyze_pricing_top_priority_actions(self):
        """Test generation of top priority pricing actions."""
        pricing_data = [
            {"ProductCategory": "VeryOverpriced", "ContosoAveragePrice": "140", "CompetitorAveragePrice": "100"},
            {"ProductCategory": "SlightlyOver", "ContosoAveragePrice": "108", "CompetitorAveragePrice": "100"},
        ]
        
        result = analyze_competitive_pricing(pricing_data)
        
        assert len(result["top_priority_actions"]) > 0
        # Most overpriced should be in top actions
        assert any("VeryOverpriced" in action.get("category", "") for action in result["top_priority_actions"])

    def test_analyze_pricing_empty_data(self):
        """Test handling of empty pricing data."""
        result = analyze_competitive_pricing([])
        
        assert "error" in result
        assert result["analysis"] == []

    def test_analyze_pricing_invalid_prices(self):
        """Test handling of invalid price data."""
        pricing_data = [
            {"ProductCategory": "Cat1", "ContosoAveragePrice": "invalid", "CompetitorAveragePrice": "100"},
            {"ProductCategory": "Cat2", "ContosoAveragePrice": "120", "CompetitorAveragePrice": "0"},
        ]
        
        result = analyze_competitive_pricing(pricing_data)
        
        # Should skip invalid entries
        assert result["total_categories"] == 0


class TestGeneratePricingRecommendation:
    """Test pricing recommendation generation."""

    def test_recommendation_urgent_overpriced(self):
        """Test urgent recommendation for severely overpriced items."""
        rec = generate_pricing_recommendation("Test", 25.0, None, 125, 100)
        
        assert "URGENT" in rec
        assert "Reduce" in rec or "reduce" in rec

    def test_recommendation_moderate_overpriced(self):
        """Test recommendation for moderately overpriced items."""
        rec = generate_pricing_recommendation("Test", 12.0, None, 112, 100)
        
        assert "Consider" in rec or "reduce" in rec.lower()

    def test_recommendation_with_high_return_rate(self):
        """Test recommendation considers high return rates."""
        rec = generate_pricing_recommendation("Test", 15.0, 18.0, 115, 100)
        
        assert "return" in rec.lower() or "quality" in rec.lower()

    def test_recommendation_competitive(self):
        """Test recommendation for competitive pricing."""
        rec = generate_pricing_recommendation("Test", 2.0, None, 102, 100)
        
        assert "competitive" in rec.lower() or "maintain" in rec.lower()

    def test_recommendation_underpriced(self):
        """Test recommendation for underpriced items."""
        rec = generate_pricing_recommendation("Test", -12.0, None, 88, 100)
        
        assert "increase" in rec.lower()


class TestOptimizeDiscountStrategy:
    """Test discount strategy optimization functionality."""

    def test_optimize_discounts_basic(self):
        """Test basic discount optimization."""
        purchase_data = [
            {"TotalAmount": "100", "DiscountApplied": "0"},
            {"TotalAmount": "90", "DiscountApplied": "10"},
            {"TotalAmount": "85", "DiscountApplied": "15"},
        ]
        
        result = optimize_discount_strategy(purchase_data)
        
        assert result["total_orders"] == 3
        assert "optimal_discount_range" in result
        assert len(result["bucket_analysis"]) > 0

    def test_optimize_discounts_bucket_analysis(self):
        """Test discount bucket categorization."""
        purchase_data = [
            {"TotalAmount": "100", "DiscountApplied": "0"},  # No discount
            {"TotalAmount": "95", "DiscountApplied": "5"},   # Small (5%)
            {"TotalAmount": "85", "DiscountApplied": "15"},  # Medium (15%)
            {"TotalAmount": "75", "DiscountApplied": "25"},  # Large (25%)
        ]
        
        result = optimize_discount_strategy(purchase_data)
        
        buckets = {b["discount_level"]: b for b in result["bucket_analysis"]}
        
        assert "No Discount (0%)" in buckets
        assert "Small (1-10%)" in buckets
        assert "Medium (11-20%)" in buckets
        assert "Large (21%+)" in buckets

    def test_optimize_discounts_revenue_share(self):
        """Test revenue share calculation for each discount bucket."""
        purchase_data = [
            {"TotalAmount": "100", "DiscountApplied": "0"},
            {"TotalAmount": "100", "DiscountApplied": "0"},
            {"TotalAmount": "50", "DiscountApplied": "5"},
        ]
        
        result = optimize_discount_strategy(purchase_data)
        
        # Total revenue = 250
        # No discount bucket = 200 (80%)
        no_discount = next(b for b in result["bucket_analysis"] if "No Discount" in b["discount_level"])
        assert no_discount["revenue_share"] == 80.0

    def test_optimize_discounts_recommendations(self):
        """Test that recommendations are generated."""
        purchase_data = [
            {"TotalAmount": "100", "DiscountApplied": "0"},
            {"TotalAmount": "80", "DiscountApplied": "20"},
        ]
        
        result = optimize_discount_strategy(purchase_data)
        
        assert len(result["recommendations"]) > 0
        for rec in result["recommendations"]:
            assert "priority" in rec
            assert "finding" in rec
            assert "recommendation" in rec

    def test_optimize_discounts_penetration_rate(self):
        """Test discount penetration rate calculation."""
        purchase_data = [
            {"TotalAmount": "100", "DiscountApplied": "0"},
            {"TotalAmount": "90", "DiscountApplied": "10"},
            {"TotalAmount": "85", "DiscountApplied": "15"},
            {"TotalAmount": "80", "DiscountApplied": "20"},
        ]
        
        result = optimize_discount_strategy(purchase_data)
        
        # 3 out of 4 orders had discounts = 75%
        assert result["discount_penetration"] == 75.0

    def test_optimize_discounts_empty_data(self):
        """Test handling of empty purchase data."""
        result = optimize_discount_strategy([])
        
        assert "error" in result
        assert result["recommendations"] == []


class TestForecastRevenueByCategory:
    """Test revenue forecasting by category functionality."""

    def test_forecast_revenue_basic(self):
        """Test basic revenue forecasting."""
        purchase_data = [
            {"ItemsPurchased": "Summer Dress", "TotalAmount": "150"},
            {"ItemsPurchased": "Leather Boots", "TotalAmount": "120"},
            {"ItemsPurchased": "Summer Dress, Sun Hat", "TotalAmount": "200"},
        ]
        
        result = forecast_revenue_by_category(purchase_data, periods=3)
        
        assert result["total_categories"] > 0
        assert result["forecast_periods"] == 3
        assert len(result["category_forecasts"]) > 0

    def test_forecast_revenue_category_structure(self):
        """Test forecast output structure for categories."""
        purchase_data = [
            {"ItemsPurchased": "Dress", "TotalAmount": "150"},
            {"ItemsPurchased": "Dress", "TotalAmount": "160"},
        ]
        
        result = forecast_revenue_by_category(purchase_data, periods=3)
        
        assert len(result["category_forecasts"]) > 0
        
        forecast = result["category_forecasts"][0]
        assert "category" in forecast
        assert "historical_orders" in forecast
        assert "historical_total_revenue" in forecast
        assert "forecast" in forecast
        assert "lower_bound" in forecast
        assert "upper_bound" in forecast
        assert len(forecast["forecast"]) == 3

    def test_forecast_revenue_confidence_intervals(self):
        """Test that confidence intervals are generated."""
        purchase_data = [
            {"ItemsPurchased": "Product", "TotalAmount": "100"},
        ]
        
        result = forecast_revenue_by_category(purchase_data, periods=2)
        
        forecast = result["category_forecasts"][0]
        
        # Lower bound should be less than forecast
        assert all(forecast["lower_bound"][i] < forecast["forecast"][i] for i in range(2))
        # Upper bound should be greater than forecast
        assert all(forecast["upper_bound"][i] > forecast["forecast"][i] for i in range(2))

    def test_forecast_revenue_growth_projection(self):
        """Test that forecasts show growth."""
        purchase_data = [
            {"ItemsPurchased": "Item", "TotalAmount": "100"},
        ]
        
        result = forecast_revenue_by_category(purchase_data, periods=3)
        
        forecast = result["category_forecasts"][0]
        forecast_values = forecast["forecast"]
        
        # Each period should be higher than previous (5% growth)
        for i in range(1, len(forecast_values)):
            assert forecast_values[i] > forecast_values[i-1]

    def test_forecast_revenue_multiple_categories(self):
        """Test forecasting with multiple product categories."""
        purchase_data = [
            {"ItemsPurchased": "Dress", "TotalAmount": "150"},
            {"ItemsPurchased": "Shoes", "TotalAmount": "120"},
            {"ItemsPurchased": "Accessories", "TotalAmount": "60"},
        ]
        
        result = forecast_revenue_by_category(purchase_data, periods=3)
        
        # Should have 3 categories
        assert len(result["category_forecasts"]) == 3
        categories = [f["category"] for f in result["category_forecasts"]]
        assert "Dresses" in categories
        assert "Shoes" in categories
        assert "Accessories" in categories

    def test_forecast_revenue_sorted_by_revenue(self):
        """Test that forecasts are sorted by historical revenue."""
        purchase_data = [
            {"ItemsPurchased": "Low Revenue", "TotalAmount": "50"},
            {"ItemsPurchased": "Dress", "TotalAmount": "200"},  # Should be first
            {"ItemsPurchased": "Medium Revenue", "TotalAmount": "100"},
        ]
        
        result = forecast_revenue_by_category(purchase_data, periods=3)
        
        forecasts = result["category_forecasts"]
        # First should have highest historical revenue
        for i in range(len(forecasts) - 1):
            assert forecasts[i]["historical_total_revenue"] >= forecasts[i+1]["historical_total_revenue"]

    def test_forecast_revenue_empty_data(self):
        """Test handling of empty purchase data."""
        result = forecast_revenue_by_category([])
        
        assert "error" in result
        assert result["forecasts"] == []


class TestCategorizeItem:
    """Test item categorization functionality."""

    def test_categorize_dresses(self):
        """Test categorization of dress items."""
        assert categorize_item("Summer Floral Dress") == "Dresses"
        assert categorize_item("Evening Gown") == "Dresses"

    def test_categorize_shoes(self):
        """Test categorization of shoe items."""
        assert categorize_item("Leather Ankle Boots") == "Shoes"
        assert categorize_item("Casual Sneakers") == "Shoes"
        assert categorize_item("Running Shoes") == "Shoes"

    def test_categorize_outerwear(self):
        """Test categorization of outerwear items."""
        assert categorize_item("Denim Jacket") == "Outerwear"
        assert categorize_item("Winter Coat") == "Outerwear"

    def test_categorize_sportswear(self):
        """Test categorization of sportswear items."""
        assert categorize_item("Fitness Leggings") == "Sportswear"
        assert categorize_item("Sports Bra") == "Sportswear"
        assert categorize_item("Athletic Wear") == "Sportswear"

    def test_categorize_accessories(self):
        """Test categorization of accessories."""
        assert categorize_item("Silk Scarf") == "Accessories"
        assert categorize_item("Sun Hat") == "Accessories"
        assert categorize_item("Clutch Bag") == "Accessories"

    def test_categorize_other(self):
        """Test categorization of unknown items."""
        assert categorize_item("Unknown Item") == "Other"


# Integration tests
class TestPricingAnalyticsIntegration:
    """Integration tests combining multiple pricing analytics functions."""

    def test_full_pricing_workflow(self):
        """Test complete pricing analysis workflow."""
        # Step 1: Competitive pricing analysis
        pricing_data = [
            {"ProductCategory": "Dresses", "ContosoAveragePrice": "120", "CompetitorAveragePrice": "100"},
            {"ProductCategory": "Shoes", "ContosoAveragePrice": "100", "CompetitorAveragePrice": "105"},
        ]
        
        product_data = [
            {"ProductCategory": "Dresses", "ReturnRate": "15"},
        ]
        
        pricing_result = analyze_competitive_pricing(pricing_data, product_data)
        assert pricing_result["total_categories"] == 2
        
        # Step 2: Optimize discounts
        discount_purchase_data = [
            {"TotalAmount": "100", "DiscountApplied": "0"},
            {"TotalAmount": "90", "DiscountApplied": "10"},
        ]
        
        discount_result = optimize_discount_strategy(discount_purchase_data)
        assert "optimal_discount_range" in discount_result
        
        # Step 3: Forecast revenue
        forecast_purchase_data = [
            {"ItemsPurchased": "Dress", "TotalAmount": "100"},
            {"ItemsPurchased": "Shoes", "TotalAmount": "90"},
        ]
        forecast_result = forecast_revenue_by_category(forecast_purchase_data, periods=3)
        assert len(forecast_result["category_forecasts"]) > 0

    def test_pricing_strategy_development(self):
        """Test developing comprehensive pricing strategy."""
        # Identify pricing issues
        pricing_data = [
            {"ProductCategory": "Overpriced", "ContosoAveragePrice": "140", "CompetitorAveragePrice": "100"},
            {"ProductCategory": "Competitive", "ContosoAveragePrice": "102", "CompetitorAveragePrice": "100"},
        ]
        
        pricing_analysis = analyze_competitive_pricing(pricing_data)
        
        # Get overpriced categories
        overpriced = [c for c in pricing_analysis["category_analysis"] if c["positioning"] == "Overpriced"]
        assert len(overpriced) > 0
        
        # Verify recommendations include price adjustments
        assert len(pricing_analysis["top_priority_actions"]) > 0

    def test_revenue_impact_analysis(self):
        """Test analysis of pricing changes on revenue."""
        # Historical data
        purchase_data = [
            {"ItemsPurchased": "Dress", "TotalAmount": "120"},
            {"ItemsPurchased": "Dress", "TotalAmount": "120"},
        ]
        
        # Forecast baseline
        baseline_forecast = forecast_revenue_by_category(purchase_data, periods=6)
        baseline_revenue = baseline_forecast["category_forecasts"][0]["forecast"]
        
        # After price reduction, expect volume increase (simplified)
        # This would require more complex modeling in practice
        assert len(baseline_revenue) == 6

