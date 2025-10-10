"""
Unit tests for customer analytics utilities.

Tests cover churn analysis, RFM segmentation, CLV prediction,
and sentiment trend analysis.
"""

import pytest
from datetime import datetime
from common.utils.customer_analytics import (
    analyze_churn_drivers,
    segment_customers_rfm,
    predict_customer_lifetime_value,
    analyze_sentiment_trends,
    generate_sentiment_recommendations,
)


class TestAnalyzeChurnDrivers:
    """Test churn driver analysis functionality."""

    def test_analyze_churn_basic(self):
        """Test basic churn analysis with typical data."""
        churn_data = [
            {"ReasonForCancellation": "Service Dissatisfaction", "Percentage": "40"},
            {"ReasonForCancellation": "Competitor Offer", "Percentage": "15"},
            {"ReasonForCancellation": "Financial Reasons", "Percentage": "30"},
            {"ReasonForCancellation": "Other", "Percentage": "15"},
        ]
        
        result = analyze_churn_drivers(churn_data)
        
        assert result["total_churn_rate"] == 100.0
        assert len(result["drivers"]) == 4
        assert result["top_driver"]["reason"] == "Service Dissatisfaction"
        assert result["top_driver"]["percentage"] == 40.0
        assert result["top_driver"]["impact"] == "Critical"
        assert result["risk_level"] == "High"
        assert len(result["recommendations"]) > 0

    def test_analyze_churn_sorted_by_percentage(self):
        """Test that drivers are sorted by percentage descending."""
        churn_data = [
            {"ReasonForCancellation": "Reason A", "Percentage": "10"},
            {"ReasonForCancellation": "Reason B", "Percentage": "50"},
            {"ReasonForCancellation": "Reason C", "Percentage": "25"},
        ]
        
        result = analyze_churn_drivers(churn_data)
        
        assert result["drivers"][0]["percentage"] == 50.0
        assert result["drivers"][1]["percentage"] == 25.0
        assert result["drivers"][2]["percentage"] == 10.0
        assert result["drivers"][0]["rank"] == 1
        assert result["drivers"][1]["rank"] == 2

    def test_analyze_churn_high_service_dissatisfaction(self):
        """Test recommendations for high service dissatisfaction."""
        churn_data = [
            {"ReasonForCancellation": "Service Dissatisfaction", "Percentage": "45"},
            {"ReasonForCancellation": "Other", "Percentage": "10"},
        ]
        
        result = analyze_churn_drivers(churn_data)
        
        # Should have high priority recommendation for service quality
        high_priority_recs = [r for r in result["recommendations"] if r["priority"] == "High"]
        assert len(high_priority_recs) > 0
        assert any("service" in r["action"].lower() for r in high_priority_recs)

    def test_analyze_churn_competitor_offer(self):
        """Test recommendations for competitor offer churn."""
        churn_data = [
            {"ReasonForCancellation": "Competitor Offer", "Percentage": "25"},
            {"ReasonForCancellation": "Other", "Percentage": "10"},
        ]
        
        result = analyze_churn_drivers(churn_data)
        
        # Should have recommendation about competitive pricing
        recs = result["recommendations"]
        assert any("compet" in r["action"].lower() or "pricing" in r["action"].lower() for r in recs)

    def test_analyze_churn_empty_data(self):
        """Test handling of empty churn data."""
        result = analyze_churn_drivers([])
        
        assert "error" in result
        assert result["drivers"] == []

    def test_analyze_churn_low_total_rate(self):
        """Test risk level calculation for low churn."""
        churn_data = [
            {"ReasonForCancellation": "Reason A", "Percentage": "20"},
            {"ReasonForCancellation": "Reason B", "Percentage": "15"},
        ]
        
        result = analyze_churn_drivers(churn_data)
        
        assert result["total_churn_rate"] == 35.0
        assert result["risk_level"] == "Low"


class TestSegmentCustomersRFM:
    """Test RFM customer segmentation functionality."""

    def test_segment_customers_basic(self):
        """Test basic RFM segmentation."""
        customers = [
            {
                "CustomerID": "C001",
                "Name": "Alice Johnson",
                "MembershipDuration": "6",
                "TotalSpend": "1000",
            },
            {
                "CustomerID": "C002",
                "Name": "Bob Smith",
                "MembershipDuration": "24",
                "TotalSpend": "5000",
            },
            {
                "CustomerID": "C003",
                "Name": "Carol White",
                "MembershipDuration": "36",
                "TotalSpend": "8000",
            },
        ]
        
        result = segment_customers_rfm(customers)
        
        assert result["total_customers"] == 3
        assert len(result["segments"]) > 0
        assert "methodology" in result
        assert result["methodology"] == "RFM (Recency, Frequency, Monetary) Analysis"

    def test_segment_customers_champions(self):
        """Test identification of Champions segment."""
        customers = [
            {
                "CustomerID": "C001",
                "Name": "High Value Customer",
                "MembershipDuration": "30",
                "TotalSpend": "10000",
            }
        ]
        
        result = segment_customers_rfm(customers)
        
        # High membership duration + high spend should be Champions
        customer_scores = result["customers_with_scores"][0]
        assert customer_scores["segment"] in ["Champions", "Loyal Customers"]
        assert customer_scores["rfm_score"] >= 4.0

    def test_segment_customers_needs_attention(self):
        """Test identification of Needs Attention segment."""
        customers = [
            {
                "CustomerID": "C001",
                "Name": "Low Value Customer",
                "MembershipDuration": "3",
                "TotalSpend": "200",
            }
        ]
        
        result = segment_customers_rfm(customers)
        
        customer_scores = result["customers_with_scores"][0]
        # Low duration + low spend should be lower tier
        assert customer_scores["rfm_score"] < 4.0

    def test_segment_customers_segment_strategies(self):
        """Test that each segment has a strategy."""
        customers = [
            {"CustomerID": "C001", "Name": "Customer 1", "MembershipDuration": "12", "TotalSpend": "3000"},
            {"CustomerID": "C002", "Name": "Customer 2", "MembershipDuration": "6", "TotalSpend": "800"},
        ]
        
        result = segment_customers_rfm(customers)
        
        for segment in result["segments"]:
            assert "strategy" in segment
            assert len(segment["strategy"]) > 0

    def test_segment_customers_average_spend(self):
        """Test average spend calculation per segment."""
        customers = [
            {"CustomerID": "C001", "Name": "Customer 1", "MembershipDuration": "24", "TotalSpend": "4000"},
            {"CustomerID": "C002", "Name": "Customer 2", "MembershipDuration": "24", "TotalSpend": "6000"},
        ]
        
        result = segment_customers_rfm(customers)
        
        # Both customers should be in similar segment due to similar profiles
        for segment in result["segments"]:
            if segment["count"] > 0:
                assert segment["avg_spend"] == segment["total_value"] / segment["count"]

    def test_segment_customers_empty_data(self):
        """Test handling of empty customer data."""
        result = segment_customers_rfm([])
        
        assert "error" in result
        assert result["segments"] == []


class TestPredictCustomerLifetimeValue:
    """Test CLV prediction functionality."""

    def test_predict_clv_basic(self):
        """Test basic CLV prediction."""
        customer = {
            "CustomerID": "C001",
            "Name": "John Doe",
            "TotalSpend": "2400",
            "AvgMonthlySpend": "200",
            "MembershipDuration": "12",
        }
        
        result = predict_customer_lifetime_value(customer, projection_months=12)
        
        assert result["customer_id"] == "C001"
        assert result["historical_value"] == 2400.0
        assert result["projected_value"] > 0
        assert result["total_clv"] == result["historical_value"] + result["projected_value"]
        assert result["projection_months"] == 12
        assert "confidence_interval" in result
        assert result["confidence_interval"]["lower"] < result["total_clv"]
        assert result["confidence_interval"]["upper"] > result["total_clv"]

    def test_predict_clv_high_value_customer(self):
        """Test CLV prediction for high value customer."""
        customer = {
            "CustomerID": "C001",
            "Name": "VIP Customer",
            "TotalSpend": "10000",
            "AvgMonthlySpend": "500",
            "MembershipDuration": "24",
        }
        
        result = predict_customer_lifetime_value(customer, projection_months=12)
        
        assert result["total_clv"] >= 8000  # Should be high value
        assert result["value_tier"] == "High Value"
        # Lower churn rate for long-term customers
        assert result["estimated_churn_rate"] <= 0.25

    def test_predict_clv_new_customer(self):
        """Test CLV prediction for new customer."""
        customer = {
            "CustomerID": "C001",
            "Name": "New Customer",
            "TotalSpend": "300",
            "AvgMonthlySpend": "100",
            "MembershipDuration": "3",
        }
        
        result = predict_customer_lifetime_value(customer, projection_months=12)
        
        # Higher churn rate for new customers
        assert result["estimated_churn_rate"] >= 0.25
        assert result["value_tier"] in ["Standard", "Medium Value"]

    def test_predict_clv_monthly_breakdown(self):
        """Test that monthly breakdown is provided."""
        customer = {
            "CustomerID": "C001",
            "Name": "Customer",
            "TotalSpend": "1200",
            "AvgMonthlySpend": "100",
            "MembershipDuration": "12",
        }
        
        result = predict_customer_lifetime_value(customer, projection_months=6)
        
        assert "monthly_breakdown" in result
        assert len(result["monthly_breakdown"]) == 6
        
        # Check each month has required fields
        for month in result["monthly_breakdown"]:
            assert "month" in month
            assert "expected_spend" in month
            assert "retention_probability" in month
            assert "cumulative_clv" in month

    def test_predict_clv_retention_decay(self):
        """Test that retention probability decays over time."""
        customer = {
            "CustomerID": "C001",
            "Name": "Customer",
            "TotalSpend": "1200",
            "AvgMonthlySpend": "100",
            "MembershipDuration": "12",
        }
        
        result = predict_customer_lifetime_value(customer, projection_months=12)
        
        breakdown = result["monthly_breakdown"]
        # Retention probability should decrease month over month
        for i in range(1, len(breakdown)):
            assert breakdown[i]["retention_probability"] <= breakdown[i-1]["retention_probability"]

    def test_predict_clv_fallback_avg_monthly_spend(self):
        """Test fallback when AvgMonthlySpend is not provided."""
        customer = {
            "CustomerID": "C001",
            "Name": "Customer",
            "TotalSpend": "1200",
            "AvgMonthlySpend": "0",  # Not provided
            "MembershipDuration": "12",
        }
        
        result = predict_customer_lifetime_value(customer, projection_months=6)
        
        # Should calculate from TotalSpend / MembershipDuration
        assert result["avg_monthly_spend"] == 100.0


class TestAnalyzeSentimentTrends:
    """Test sentiment trend analysis functionality."""

    def test_analyze_sentiment_basic(self):
        """Test basic sentiment analysis."""
        sentiment_data = [
            {"Month": "Jan", "PositiveMentions": "100", "NegativeMentions": "20", "NeutralMentions": "30"},
            {"Month": "Feb", "PositiveMentions": "110", "NegativeMentions": "15", "NeutralMentions": "35"},
            {"Month": "Mar", "PositiveMentions": "120", "NegativeMentions": "10", "NeutralMentions": "40"},
        ]
        
        result = analyze_sentiment_trends(sentiment_data, forecast_periods=3)
        
        assert result["total_periods"] == 3
        assert len(result["sentiment_scores"]) == 3
        assert "current_sentiment" in result
        assert "average_sentiment" in result
        assert "assessment" in result
        assert len(result["forecast"]) == 3

    def test_analyze_sentiment_positive_assessment(self):
        """Test positive sentiment assessment."""
        sentiment_data = [
            {"Month": "Jan", "PositiveMentions": "500", "NegativeMentions": "50", "NeutralMentions": "200"},
            {"Month": "Feb", "PositiveMentions": "510", "NegativeMentions": "40", "NeutralMentions": "210"},
        ]
        
        result = analyze_sentiment_trends(sentiment_data)
        
        # High positive rate should be "Positive" assessment
        assert result["current_sentiment"] > 0.3
        assert result["assessment"] == "Positive"

    def test_analyze_sentiment_negative_assessment(self):
        """Test negative sentiment assessment."""
        sentiment_data = [
            {"Month": "Jan", "PositiveMentions": "100", "NegativeMentions": "400", "NeutralMentions": "200"},
            {"Month": "Feb", "PositiveMentions": "90", "NegativeMentions": "450", "NeutralMentions": "210"},
        ]
        
        result = analyze_sentiment_trends(sentiment_data)
        
        # High negative rate should be "Concerning" or "Critical"
        assert result["current_sentiment"] < 0
        assert result["assessment"] in ["Concerning", "Critical"]

    def test_analyze_sentiment_anomaly_detection(self):
        """Test detection of sentiment anomalies."""
        sentiment_data = [
            {"Month": "Jan", "PositiveMentions": "500", "NegativeMentions": "50", "NeutralMentions": "200"},
            {"Month": "Feb", "PositiveMentions": "480", "NegativeMentions": "60", "NeutralMentions": "220"},
            {"Month": "Mar", "PositiveMentions": "300", "NegativeMentions": "300", "NeutralMentions": "200"},  # Big drop
        ]
        
        result = analyze_sentiment_trends(sentiment_data)
        
        # Should detect anomaly in March
        assert result["anomaly_count"] > 0
        assert len(result["anomalies"]) > 0
        
        # Check anomaly properties
        anomaly = result["anomalies"][0]
        assert "month" in anomaly
        assert "change_percentage" in anomaly
        assert "severity" in anomaly

    def test_analyze_sentiment_critical_anomaly(self):
        """Test detection of critical severity anomaly."""
        sentiment_data = [
            {"Month": "Jan", "PositiveMentions": "500", "NegativeMentions": "50", "NeutralMentions": "200"},
            {"Month": "Feb", "PositiveMentions": "100", "NegativeMentions": "500", "NeutralMentions": "200"},  # Massive drop
        ]
        
        result = analyze_sentiment_trends(sentiment_data)
        
        if result["anomalies"]:
            # Huge sentiment drop should be Critical
            critical_anomalies = [a for a in result["anomalies"] if a["severity"] == "Critical"]
            assert len(critical_anomalies) > 0

    def test_analyze_sentiment_forecast_improving(self):
        """Test forecast with improving trend."""
        sentiment_data = [
            {"Month": "Jan", "PositiveMentions": "300", "NegativeMentions": "100", "NeutralMentions": "200"},
            {"Month": "Feb", "PositiveMentions": "400", "NegativeMentions": "80", "NeutralMentions": "200"},
            {"Month": "Mar", "PositiveMentions": "500", "NegativeMentions": "60", "NeutralMentions": "200"},
        ]
        
        result = analyze_sentiment_trends(sentiment_data, forecast_periods=2)
        
        assert len(result["forecast"]) == 2
        # With improving trend, forecast should show "Improving"
        improving_forecasts = [f for f in result["forecast"] if f["trend"] == "Improving"]
        assert len(improving_forecasts) > 0

    def test_analyze_sentiment_net_sentiment_calculation(self):
        """Test net sentiment score calculation."""
        sentiment_data = [
            {"Month": "Jan", "PositiveMentions": "600", "NegativeMentions": "100", "NeutralMentions": "300"},
        ]
        
        result = analyze_sentiment_trends(sentiment_data)
        
        score = result["sentiment_scores"][0]
        # Net sentiment = (600 - 100) / 1000 = 0.5
        assert score["net_sentiment"] == 0.5
        assert score["positive_rate"] == 0.6
        assert score["negative_rate"] == 0.1

    def test_analyze_sentiment_empty_data(self):
        """Test handling of empty sentiment data."""
        result = analyze_sentiment_trends([])
        
        assert "error" in result
        assert result["trends"] == []

    def test_analyze_sentiment_recommendations(self):
        """Test that recommendations are generated."""
        sentiment_data = [
            {"Month": "Jan", "PositiveMentions": "100", "NegativeMentions": "400", "NeutralMentions": "200"},
        ]
        
        result = analyze_sentiment_trends(sentiment_data)
        
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0
        
        # Should have high priority recommendation for negative sentiment
        high_priority = [r for r in result["recommendations"] if r["priority"] in ["High", "Critical"]]
        assert len(high_priority) > 0


class TestGenerateSentimentRecommendations:
    """Test sentiment recommendation generation."""

    def test_recommendations_negative_sentiment(self):
        """Test recommendations for negative current sentiment."""
        recs = generate_sentiment_recommendations(-0.2, [], [])
        
        assert len(recs) > 0
        high_priority = [r for r in recs if r["priority"] == "High"]
        assert len(high_priority) > 0

    def test_recommendations_critical_anomalies(self):
        """Test recommendations when critical anomalies detected."""
        anomalies = [
            {"severity": "Critical", "month": "June", "change_percentage": -40}
        ]
        
        recs = generate_sentiment_recommendations(0.3, anomalies, [])
        
        critical_recs = [r for r in recs if r["priority"] == "Critical"]
        assert len(critical_recs) > 0

    def test_recommendations_declining_forecast(self):
        """Test recommendations for declining forecast."""
        forecast = [
            {"trend": "Declining", "period": 1}
        ]
        
        recs = generate_sentiment_recommendations(0.2, [], forecast)
        
        # Should have proactive recommendation
        assert any("proactive" in r["action"].lower() for r in recs)

    def test_recommendations_positive_sentiment(self):
        """Test recommendations for strong positive sentiment."""
        recs = generate_sentiment_recommendations(0.5, [], [])
        
        # Should have low priority maintenance recommendation
        assert len(recs) > 0
        assert any(r["priority"] == "Low" for r in recs)


# Integration tests
class TestCustomerAnalyticsIntegration:
    """Integration tests combining multiple analytics functions."""

    def test_full_customer_analysis_workflow(self):
        """Test complete customer analysis workflow."""
        # Step 1: Analyze churn
        churn_data = [
            {"ReasonForCancellation": "Service Dissatisfaction", "Percentage": "40"},
            {"ReasonForCancellation": "Price", "Percentage": "30"},
        ]
        churn_result = analyze_churn_drivers(churn_data)
        assert churn_result["risk_level"] in ["Medium", "High"]
        
        # Step 2: Segment customers
        customers = [
            {"CustomerID": "C001", "Name": "Alice", "MembershipDuration": "24", "TotalSpend": "5000"},
            {"CustomerID": "C002", "Name": "Bob", "MembershipDuration": "6", "TotalSpend": "800"},
        ]
        segment_result = segment_customers_rfm(customers)
        assert len(segment_result["segments"]) >= 2
        
        # Step 3: Predict CLV for high-value segment
        high_value_customer = customers[0]  # Alice
        clv_result = predict_customer_lifetime_value(high_value_customer, projection_months=12)
        assert clv_result["value_tier"] in ["Medium Value", "High Value"]
        
        # Step 4: Analyze sentiment
        sentiment_data = [
            {"Month": "Jan", "PositiveMentions": "400", "NegativeMentions": "100", "NeutralMentions": "200"},
            {"Month": "Feb", "PositiveMentions": "450", "NegativeMentions": "80", "NeutralMentions": "220"},
        ]
        sentiment_result = analyze_sentiment_trends(sentiment_data)
        assert sentiment_result["assessment"] in ["Positive", "Neutral"]

    def test_customer_retention_strategy(self):
        """Test creating a retention strategy from analytics."""
        # Identify at-risk customer
        customer = {
            "CustomerID": "C001",
            "Name": "At Risk Customer",
            "TotalSpend": "3000",
            "AvgMonthlySpend": "150",
            "MembershipDuration": "20",
        }
        
        clv = predict_customer_lifetime_value(customer, projection_months=12)
        
        # Check CLV to determine retention value
        if clv["total_clv"] >= 4000:
            # High value - worth retention effort
            assert clv["value_tier"] in ["Medium Value", "High Value"]
            
            # Segment to determine retention approach
            customers = [customer]
            segments = segment_customers_rfm(customers)
            
            # Should have specific strategy
            assert len(segments["segments"]) > 0
            for segment in segments["segments"]:
                assert "strategy" in segment


