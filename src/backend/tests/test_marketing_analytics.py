"""
Unit tests for marketing analytics utilities.

Tests cover campaign effectiveness analysis, engagement prediction,
and loyalty program optimization.
"""

import pytest
from common.utils.marketing_analytics import (
    analyze_campaign_effectiveness,
    generate_campaign_recommendation,
    predict_engagement,
    optimize_loyalty_program,
    generate_benefit_improvement_action,
)


class TestAnalyzeCampaignEffectiveness:
    """Test campaign effectiveness analysis functionality."""

    def test_analyze_campaigns_basic(self):
        """Test basic campaign analysis."""
        campaign_data = [
            {"Campaign": "Summer Sale", "Opened": "Yes", "Clicked": "Yes", "Unsubscribed": "No"},
            {"Campaign": "New Arrivals", "Opened": "Yes", "Clicked": "No", "Unsubscribed": "No"},
            {"Campaign": "Exclusive Offers", "Opened": "No", "Clicked": "No", "Unsubscribed": "No"},
        ]
        
        result = analyze_campaign_effectiveness(campaign_data)
        
        assert result["total_campaigns"] == 3
        assert len(result["campaigns"]) == 3
        assert "overall_metrics" in result
        assert "best_campaign" in result

    def test_analyze_campaigns_engagement_scores(self):
        """Test campaign engagement score calculation."""
        campaign_data = [
            {"Campaign": "Excellent", "Opened": "Yes", "Clicked": "Yes", "Unsubscribed": "No"},
            {"Campaign": "Good", "Opened": "Yes", "Clicked": "No", "Unsubscribed": "No"},
            {"Campaign": "Poor", "Opened": "No", "Clicked": "No", "Unsubscribed": "Yes"},
        ]
        
        result = analyze_campaign_effectiveness(campaign_data)
        
        excellent = next(c for c in result["campaigns"] if c["campaign"] == "Excellent")
        good = next(c for c in result["campaigns"] if c["campaign"] == "Good")
        poor = next(c for c in result["campaigns"] if c["campaign"] == "Poor")
        
        assert excellent["engagement_score"] > good["engagement_score"]
        assert good["engagement_score"] > poor["engagement_score"]
        assert poor["engagement_score"] < 0  # Negative due to unsubscribe

    def test_analyze_campaigns_performance_tiers(self):
        """Test performance tier classification."""
        campaign_data = [
            {"Campaign": "Excellent", "Opened": "Yes", "Clicked": "Yes", "Unsubscribed": "No"},
            {"Campaign": "Good", "Opened": "Yes", "Clicked": "No", "Unsubscribed": "No"},
            {"Campaign": "Fair", "Opened": "No", "Clicked": "No", "Unsubscribed": "No"},
        ]
        
        result = analyze_campaign_effectiveness(campaign_data)
        
        excellent = next(c for c in result["campaigns"] if c["campaign"] == "Excellent")
        assert excellent["performance"] == "Excellent"
        
        good = next(c for c in result["campaigns"] if c["campaign"] == "Good")
        assert good["performance"] == "Good"

    def test_analyze_campaigns_overall_metrics(self):
        """Test calculation of overall campaign metrics."""
        campaign_data = [
            {"Campaign": "C1", "Opened": "Yes", "Clicked": "Yes", "Unsubscribed": "No"},
            {"Campaign": "C2", "Opened": "Yes", "Clicked": "No", "Unsubscribed": "No"},
            {"Campaign": "C3", "Opened": "No", "Clicked": "No", "Unsubscribed": "No"},
        ]
        
        result = analyze_campaign_effectiveness(campaign_data)
        
        metrics = result["overall_metrics"]
        # 2 out of 3 opened = 66.7%
        assert metrics["open_rate"] == pytest.approx(66.7, abs=0.1)
        # 1 out of 3 clicked = 33.3%
        assert metrics["click_rate"] == pytest.approx(33.3, abs=0.1)
        # 1 out of 2 opened clicked = 50%
        assert metrics["click_through_rate"] == 50.0

    def test_analyze_campaigns_best_performer(self):
        """Test identification of best performing campaign."""
        campaign_data = [
            {"Campaign": "Best", "Opened": "Yes", "Clicked": "Yes", "Unsubscribed": "No"},
            {"Campaign": "Okay", "Opened": "Yes", "Clicked": "No", "Unsubscribed": "No"},
        ]
        
        result = analyze_campaign_effectiveness(campaign_data)
        
        assert result["best_campaign"]["name"] == "Best"
        assert result["best_campaign"]["performance"] == "Excellent"

    def test_analyze_campaigns_recommendations(self):
        """Test generation of campaign recommendations."""
        campaign_data = [
            {"Campaign": "Good", "Opened": "Yes", "Clicked": "Yes", "Unsubscribed": "No"},
            {"Campaign": "Zero Open", "Opened": "No", "Clicked": "No", "Unsubscribed": "No"},
        ]
        
        result = analyze_campaign_effectiveness(campaign_data)
        
        assert len(result["recommendations"]) > 0
        # Should recommend improvements for zero open rate
        assert any("0% open rate" in rec["finding"] or "subject" in rec["action"].lower() 
                  for rec in result["recommendations"])

    def test_analyze_campaigns_unsubscribe_warning(self):
        """Test critical warning for unsubscribes."""
        campaign_data = [
            {"Campaign": "Problem", "Opened": "No", "Clicked": "No", "Unsubscribed": "Yes"},
        ]
        
        result = analyze_campaign_effectiveness(campaign_data)
        
        # Should have critical priority recommendation
        critical_recs = [r for r in result["recommendations"] if r["priority"] == "Critical"]
        assert len(critical_recs) > 0

    def test_analyze_campaigns_empty_data(self):
        """Test handling of empty campaign data."""
        result = analyze_campaign_effectiveness([])
        
        assert "error" in result
        assert result["campaigns"] == []


class TestGenerateCampaignRecommendation:
    """Test campaign recommendation generation."""

    def test_recommendation_unsubscribed(self):
        """Test critical recommendation for unsubscribes."""
        rec = generate_campaign_recommendation("Test", False, False, True)
        
        assert "CRITICAL" in rec
        assert "unsubscribed" in rec.lower()

    def test_recommendation_not_opened(self):
        """Test recommendation for unopened campaigns."""
        rec = generate_campaign_recommendation("Test", False, False, False)
        
        assert "Not opened" in rec or "subject line" in rec.lower()

    def test_recommendation_opened_and_clicked(self):
        """Test positive recommendation for excellent engagement."""
        rec = generate_campaign_recommendation("Test", True, True, False)
        
        assert "Excellent" in rec or "excellent" in rec.lower()
        assert "replicate" in rec.lower() or "analyze" in rec.lower()

    def test_recommendation_opened_not_clicked(self):
        """Test recommendation for opened but not clicked."""
        rec = generate_campaign_recommendation("Test", True, False, False)
        
        assert "no click" in rec.lower() or "call-to-action" in rec.lower()


class TestPredictEngagement:
    """Test engagement prediction functionality."""

    def test_predict_engagement_basic(self):
        """Test basic engagement prediction."""
        customer = {
            "CustomerID": "C001",
            "Name": "Test Customer",
            "TotalSpend": "3000",
            "MembershipDuration": "12"
        }
        
        historical = [
            {"Opened": "Yes", "Clicked": "Yes"},
            {"Opened": "Yes", "Clicked": "No"},
        ]
        
        result = predict_engagement(customer, historical, "sale")
        
        assert "open_probability" in result
        assert "click_probability" in result
        assert "engagement_level" in result
        assert "optimal_send_time" in result

    def test_predict_engagement_high_value_customer(self):
        """Test prediction for high-value customers."""
        customer = {
            "CustomerID": "C001",
            "Name": "VIP Customer",
            "TotalSpend": "8000",
            "MembershipDuration": "24"
        }
        
        historical = [
            {"Opened": "Yes", "Clicked": "Yes"},
        ]
        
        result = predict_engagement(customer, historical, "exclusive_offers")
        
        # High spenders should have higher engagement probability
        assert result["open_probability"] > 0.5
        assert result["engagement_level"] in ["High", "Medium"]

    def test_predict_engagement_new_customer(self):
        """Test prediction for new customers."""
        customer = {
            "CustomerID": "C001",
            "Name": "New Customer",
            "TotalSpend": "500",
            "MembershipDuration": "2"
        }
        
        historical = []
        
        result = predict_engagement(customer, historical, "sale")
        
        # New customers with low spend should have moderate engagement
        assert 0 <= result["open_probability"] <= 1
        assert result["engagement_level"] in ["Low", "Medium", "High"]

    def test_predict_engagement_campaign_type_multiplier(self):
        """Test that campaign type affects engagement prediction."""
        customer = {
            "CustomerID": "C001",
            "Name": "Customer",
            "TotalSpend": "3000",
            "MembershipDuration": "12"
        }
        
        historical = [
            {"Opened": "Yes", "Clicked": "Yes"},
        ]
        
        sale_result = predict_engagement(customer, historical, "sale")
        styling_result = predict_engagement(customer, historical, "styling")
        
        # Sale campaigns typically have higher engagement than styling
        assert sale_result["open_probability"] > styling_result["open_probability"]

    def test_predict_engagement_optimal_timing(self):
        """Test optimal send time recommendation."""
        customer_long = {
            "CustomerID": "C001",
            "Name": "Long-term Customer",
            "TotalSpend": "5000",
            "MembershipDuration": "24"
        }
        
        customer_new = {
            "CustomerID": "C002",
            "Name": "New Customer",
            "TotalSpend": "500",
            "MembershipDuration": "3"
        }
        
        result_long = predict_engagement(customer_long, [], "sale")
        result_new = predict_engagement(customer_new, [], "sale")
        
        # Different customer tiers get different timing recommendations
        assert result_long["optimal_send_time"] != result_new["optimal_send_time"]
        assert result_long["timing_confidence"] in ["High", "Medium", "Low"]


class TestOptimizeLoyaltyProgram:
    """Test loyalty program optimization functionality."""

    def test_optimize_loyalty_basic(self):
        """Test basic loyalty program optimization."""
        loyalty_data = {
            "TotalPointsEarned": "4800",
            "PointsRedeemed": "3600",
            "CurrentPointBalance": "1200",
            "PointsExpiringNextMonth": "0"
        }
        
        benefits_data = [
            {"Benefit": "Free Shipping", "UsageFrequency": "7"},
            {"Benefit": "Early Access", "UsageFrequency": "2"},
        ]
        
        result = optimize_loyalty_program(loyalty_data, benefits_data)
        
        assert "points_metrics" in result
        assert "benefits_utilization" in result
        assert "recommendations" in result
        assert "program_health" in result

    def test_optimize_loyalty_redemption_rate(self):
        """Test redemption rate calculation."""
        loyalty_data = {
            "TotalPointsEarned": "1000",
            "PointsRedeemed": "750",
            "CurrentPointBalance": "250",
            "PointsExpiringNextMonth": "0"
        }
        
        benefits_data = []
        
        result = optimize_loyalty_program(loyalty_data, benefits_data)
        
        # 750/1000 = 75%
        assert result["points_metrics"]["redemption_rate"] == 75.0

    def test_optimize_loyalty_expiring_points_warning(self):
        """Test critical warning for expiring points."""
        loyalty_data = {
            "TotalPointsEarned": "1000",
            "PointsRedeemed": "0",
            "CurrentPointBalance": "1000",
            "PointsExpiringNextMonth": "800"
        }
        
        benefits_data = []
        
        result = optimize_loyalty_program(loyalty_data, benefits_data)
        
        # Should have critical priority recommendation
        critical_recs = [r for r in result["recommendations"] if r["priority"] == "Critical"]
        assert len(critical_recs) > 0
        assert any("expir" in rec["finding"].lower() for rec in critical_recs)

    def test_optimize_loyalty_unused_benefits(self):
        """Test identification of unused benefits."""
        loyalty_data = {
            "TotalPointsEarned": "1000",
            "PointsRedeemed": "500",
            "CurrentPointBalance": "500",
            "PointsExpiringNextMonth": "0"
        }
        
        benefits_data = [
            {"Benefit": "Free Shipping", "UsageFrequency": "10"},
            {"Benefit": "Styling Sessions", "UsageFrequency": "0"},
            {"Benefit": "Exclusive Discounts", "UsageFrequency": "0"},
        ]
        
        result = optimize_loyalty_program(loyalty_data, benefits_data)
        
        assert result["unused_benefits_count"] == 2
        
        # Should have recommendations for unused benefits
        assert any("utilization" in rec["category"] or "Benefit" in rec["category"] 
                  for rec in result["recommendations"])

    def test_optimize_loyalty_benefit_utilization_tiers(self):
        """Test benefit utilization tier classification."""
        loyalty_data = {
            "TotalPointsEarned": "1000",
            "PointsRedeemed": "500",
            "CurrentPointBalance": "500",
            "PointsExpiringNextMonth": "0"
        }
        
        benefits_data = [
            {"Benefit": "Not Used", "UsageFrequency": "0"},
            {"Benefit": "Low Use", "UsageFrequency": "1"},
            {"Benefit": "Good Use", "UsageFrequency": "5"},
        ]
        
        result = optimize_loyalty_program(loyalty_data, benefits_data)
        
        benefits = {b["benefit"]: b for b in result["benefits_utilization"]}
        
        assert benefits["Not Used"]["utilization"] == "Not Used"
        assert benefits["Low Use"]["utilization"] == "Low"
        assert benefits["Good Use"]["utilization"] == "Good"

    def test_optimize_loyalty_program_health(self):
        """Test program health assessment."""
        # Good program
        good_loyalty = {
            "TotalPointsEarned": "1000",
            "PointsRedeemed": "700",
            "CurrentPointBalance": "300",
            "PointsExpiringNextMonth": "0"
        }
        
        good_benefits = [
            {"Benefit": "Benefit1", "UsageFrequency": "5"},
            {"Benefit": "Benefit2", "UsageFrequency": "3"},
        ]
        
        good_result = optimize_loyalty_program(good_loyalty, good_benefits)
        assert good_result["program_health"] == "Good"
        
        # Poor program
        poor_loyalty = {
            "TotalPointsEarned": "1000",
            "PointsRedeemed": "200",
            "CurrentPointBalance": "800",
            "PointsExpiringNextMonth": "500"
        }
        
        poor_benefits = [
            {"Benefit": "Benefit1", "UsageFrequency": "0"},
        ]
        
        poor_result = optimize_loyalty_program(poor_loyalty, poor_benefits)
        assert poor_result["program_health"] in ["Fair", "Needs Improvement"]

    def test_optimize_loyalty_empty_data(self):
        """Test handling of empty loyalty data."""
        result = optimize_loyalty_program({}, [])
        
        assert "error" in result or result["points_metrics"]["total_earned"] == 0


class TestGenerateBenefitImprovementAction:
    """Test benefit improvement action generation."""

    def test_action_styling_benefit(self):
        """Test action for styling benefit."""
        action = generate_benefit_improvement_action("Personalized Styling Sessions", 0)
        
        assert "styling" in action.lower()
        assert "proactive" in action.lower() or "offer" in action.lower()

    def test_action_early_access_benefit(self):
        """Test action for early access benefit."""
        action = generate_benefit_improvement_action("Early Access to Collections", 0)
        
        assert "early access" in action.lower() or "preview" in action.lower()

    def test_action_discount_benefit(self):
        """Test action for discount benefit."""
        action = generate_benefit_improvement_action("Exclusive Discounts", 0)
        
        assert "discount" in action.lower()

    def test_action_unknown_benefit_zero_usage(self):
        """Test action for unknown benefit with zero usage."""
        action = generate_benefit_improvement_action("Unknown Benefit", 0)
        
        assert "survey" in action.lower() or "awareness" in action.lower()

    def test_action_unknown_benefit_low_usage(self):
        """Test action for unknown benefit with low usage."""
        action = generate_benefit_improvement_action("Unknown Benefit", 2)
        
        assert "promotion" in action.lower() or "value" in action.lower()


# Integration tests
class TestMarketingAnalyticsIntegration:
    """Integration tests combining multiple marketing analytics functions."""

    def test_full_marketing_workflow(self):
        """Test complete marketing analytics workflow."""
        # Step 1: Analyze campaign effectiveness
        campaign_data = [
            {"Campaign": "Summer Sale", "Opened": "Yes", "Clicked": "Yes", "Unsubscribed": "No"},
            {"Campaign": "New Arrivals", "Opened": "No", "Clicked": "No", "Unsubscribed": "No"},
        ]
        
        campaign_result = analyze_campaign_effectiveness(campaign_data)
        assert campaign_result["total_campaigns"] == 2
        
        # Step 2: Predict engagement for high-value customer
        customer = {
            "CustomerID": "C001",
            "Name": "VIP Customer",
            "TotalSpend": "5000",
            "MembershipDuration": "18"
        }
        
        engagement_result = predict_engagement(customer, campaign_data, "exclusive_offers")
        assert engagement_result["engagement_level"] in ["High", "Medium", "Low"]
        
        # Step 3: Optimize loyalty program
        loyalty_data = {
            "TotalPointsEarned": "4800",
            "PointsRedeemed": "3600",
            "CurrentPointBalance": "1200",
            "PointsExpiringNextMonth": "0"
        }
        
        benefits_data = [
            {"Benefit": "Free Shipping", "UsageFrequency": "7"},
        ]
        
        loyalty_result = optimize_loyalty_program(loyalty_data, benefits_data)
        assert "program_health" in loyalty_result

    def test_customer_engagement_optimization(self):
        """Test optimizing engagement for different customer segments."""
        # High engagement customer
        high_engagement_customer = {
            "CustomerID": "C001",
            "Name": "Active Customer",
            "TotalSpend": "6000",
            "MembershipDuration": "24"
        }
        
        high_engagement_history = [
            {"Opened": "Yes", "Clicked": "Yes"},
            {"Opened": "Yes", "Clicked": "Yes"},
        ]
        
        high_result = predict_engagement(high_engagement_customer, high_engagement_history, "sale")
        
        # Low engagement customer
        low_engagement_customer = {
            "CustomerID": "C002",
            "Name": "Inactive Customer",
            "TotalSpend": "500",
            "MembershipDuration": "3"
        }
        
        low_engagement_history = [
            {"Opened": "No", "Clicked": "No"},
        ]
        
        low_result = predict_engagement(low_engagement_customer, low_engagement_history, "sale")
        
        # High engagement customer should have higher probabilities
        assert high_result["open_probability"] > low_result["open_probability"]

    def test_loyalty_program_improvement_strategy(self):
        """Test developing loyalty program improvement strategy."""
        # Identify issues
        loyalty_data = {
            "TotalPointsEarned": "5000",
            "PointsRedeemed": "1000",
            "CurrentPointBalance": "4000",
            "PointsExpiringNextMonth": "2000"
        }
        
        benefits_data = [
            {"Benefit": "Free Shipping", "UsageFrequency": "10"},
            {"Benefit": "Styling Sessions", "UsageFrequency": "0"},
            {"Benefit": "Early Access", "UsageFrequency": "0"},
        ]
        
        result = optimize_loyalty_program(loyalty_data, benefits_data)
        
        # Should have multiple recommendations
        assert len(result["recommendations"]) >= 2
        
        # Should flag low redemption rate (20%)
        assert result["points_metrics"]["redemption_rate"] == 20.0
        
        # Should flag expiring points
        assert any("expir" in rec["finding"].lower() for rec in result["recommendations"])
        
        # Should flag unused benefits
        assert result["unused_benefits_count"] == 2



