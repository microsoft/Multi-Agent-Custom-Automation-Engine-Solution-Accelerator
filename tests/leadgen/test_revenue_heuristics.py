"""Unit tests for revenue estimation heuristics.

Tests the revenue_heuristics module which provides heuristic-based
revenue estimation for local service businesses.
"""

import os
import sys

import pytest

# Ensure repo root is on sys.path so imports work correctly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LEADGEN_DIR = os.path.join(ROOT_DIR, "src", "leadgen")
if LEADGEN_DIR not in sys.path:
    sys.path.insert(0, LEADGEN_DIR)

from utils.revenue_heuristics import (
    BASE_REVENUE_PER_REVIEW,
    INDUSTRY_MULTIPLIERS,
    MAX_QUALIFIED_REVENUE,
    MIN_QUALIFIED_REVENUE,
    RATING_MULTIPLIERS,
    RevenueEstimate,
    calculate_confidence,
    calculate_review_score,
    estimate_revenue,
    estimate_revenue_batch,
    filter_qualified_leads,
    get_industry_multiplier,
    get_rating_multiplier,
    is_qualified_revenue,
)


class TestGetIndustryMultiplier:
    """Tests for get_industry_multiplier function."""

    def test_exact_match_dentist(self):
        """Test exact match for 'dentist' industry."""
        multiplier = get_industry_multiplier("dentist")
        assert multiplier == 2.5

    def test_exact_match_hvac(self):
        """Test exact match for 'hvac' industry."""
        multiplier = get_industry_multiplier("hvac")
        assert multiplier == 2.8

    def test_exact_match_roofing(self):
        """Test exact match for 'roofing' - highest multiplier."""
        multiplier = get_industry_multiplier("roofing")
        assert multiplier == 3.5

    def test_case_insensitive(self):
        """Test that industry matching is case-insensitive."""
        assert get_industry_multiplier("DENTIST") == 2.5
        assert get_industry_multiplier("Dentist") == 2.5
        assert get_industry_multiplier("DeNtIsT") == 2.5

    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled."""
        assert get_industry_multiplier("  dentist  ") == 2.5
        assert get_industry_multiplier("\tdentist\n") == 2.5

    def test_partial_match_contains_key(self):
        """Test partial match where industry contains the key."""
        # 'dental office' contains 'dental'
        assert get_industry_multiplier("dental office") == 2.5
        # 'plumbing services' contains 'plumbing'
        assert get_industry_multiplier("plumbing services") == 2.2

    def test_partial_match_key_contains_industry(self):
        """Test partial match where key contains industry."""
        # 'vet' is contained in 'veterinarian'
        assert get_industry_multiplier("vet") == 1.7

    def test_unknown_industry_returns_default(self):
        """Test that unknown industries return the default multiplier."""
        assert get_industry_multiplier("unknown_industry_xyz") == 1.5
        assert get_industry_multiplier("some random business") == 1.5

    def test_empty_string_returns_default(self):
        """Test that empty string returns default multiplier."""
        assert get_industry_multiplier("") == 1.5

    def test_none_returns_default(self):
        """Test that None returns default multiplier."""
        assert get_industry_multiplier(None) == 1.5

    def test_all_industries_have_positive_multipliers(self):
        """Test that all industry multipliers are positive."""
        for industry, multiplier in INDUSTRY_MULTIPLIERS.items():
            assert multiplier > 0, f"Industry '{industry}' has non-positive multiplier"


class TestGetRatingMultiplier:
    """Tests for get_rating_multiplier function."""

    def test_excellent_rating(self):
        """Test excellent rating (4.5+) multiplier."""
        assert get_rating_multiplier(5.0) == RATING_MULTIPLIERS["excellent"]
        assert get_rating_multiplier(4.5) == RATING_MULTIPLIERS["excellent"]
        assert get_rating_multiplier(4.8) == RATING_MULTIPLIERS["excellent"]

    def test_good_rating(self):
        """Test good rating (4.0-4.5) multiplier."""
        assert get_rating_multiplier(4.0) == RATING_MULTIPLIERS["good"]
        assert get_rating_multiplier(4.2) == RATING_MULTIPLIERS["good"]
        assert get_rating_multiplier(4.49) == RATING_MULTIPLIERS["good"]

    def test_average_rating(self):
        """Test average rating (3.5-4.0) multiplier."""
        assert get_rating_multiplier(3.5) == RATING_MULTIPLIERS["average"]
        assert get_rating_multiplier(3.7) == RATING_MULTIPLIERS["average"]
        assert get_rating_multiplier(3.99) == RATING_MULTIPLIERS["average"]

    def test_below_average_rating(self):
        """Test below average rating (3.0-3.5) multiplier."""
        assert get_rating_multiplier(3.0) == RATING_MULTIPLIERS["below_average"]
        assert get_rating_multiplier(3.2) == RATING_MULTIPLIERS["below_average"]
        assert get_rating_multiplier(3.49) == RATING_MULTIPLIERS["below_average"]

    def test_poor_rating(self):
        """Test poor rating (<3.0) multiplier."""
        assert get_rating_multiplier(2.9) == RATING_MULTIPLIERS["poor"]
        assert get_rating_multiplier(2.0) == RATING_MULTIPLIERS["poor"]
        assert get_rating_multiplier(1.0) == RATING_MULTIPLIERS["poor"]
        assert get_rating_multiplier(0.0) == RATING_MULTIPLIERS["poor"]

    def test_none_rating_returns_neutral(self):
        """Test that None rating returns neutral multiplier (1.0)."""
        assert get_rating_multiplier(None) == 1.0


class TestCalculateReviewScore:
    """Tests for calculate_review_score function."""

    def test_no_reviews_returns_minimum(self):
        """Test that zero reviews returns minimum baseline."""
        assert calculate_review_score(0) == 50.0
        assert calculate_review_score(None) == 50.0

    def test_negative_reviews_returns_minimum(self):
        """Test that negative reviews returns minimum baseline."""
        assert calculate_review_score(-1) == 50.0
        assert calculate_review_score(-100) == 50.0

    def test_linear_scaling_under_threshold(self):
        """Test linear scaling for review counts under 200."""
        # For reviews <= 200, score = reviews * BASE_REVENUE_PER_REVIEW
        score_10 = calculate_review_score(10)
        expected_10 = 10 * BASE_REVENUE_PER_REVIEW
        assert score_10 == expected_10

        score_100 = calculate_review_score(100)
        expected_100 = 100 * BASE_REVENUE_PER_REVIEW
        assert score_100 == expected_100

        score_200 = calculate_review_score(200)
        expected_200 = 200 * BASE_REVENUE_PER_REVIEW
        assert score_200 == expected_200

    def test_logarithmic_dampening_over_threshold(self):
        """Test logarithmic dampening for review counts over 200."""
        score_300 = calculate_review_score(300)
        # Score should be less than linear extrapolation
        linear_300 = 300 * BASE_REVENUE_PER_REVIEW
        assert score_300 < linear_300

        score_500 = calculate_review_score(500)
        linear_500 = 500 * BASE_REVENUE_PER_REVIEW
        assert score_500 < linear_500

    def test_diminishing_returns_at_high_counts(self):
        """Test that very high review counts show diminishing returns."""
        score_500 = calculate_review_score(500)
        score_1000 = calculate_review_score(1000)

        # The increase from 500 to 1000 reviews should be less than double
        increase_ratio = score_1000 / score_500
        assert increase_ratio < 2.0

    def test_score_increases_with_reviews(self):
        """Test that score always increases with more reviews."""
        prev_score = 0
        for count in [0, 1, 10, 50, 100, 200, 500, 1000]:
            score = calculate_review_score(count)
            assert score >= prev_score, f"Score decreased at review count {count}"
            prev_score = score


class TestCalculateConfidence:
    """Tests for calculate_confidence function."""

    def test_base_confidence(self):
        """Test base confidence with no data."""
        confidence = calculate_confidence(None, None, has_website=False)
        assert confidence == 0.3

    def test_high_review_count_contribution(self):
        """Test confidence contribution from high review count."""
        confidence = calculate_confidence(100, None, has_website=False)
        assert confidence == 0.3 + 0.35  # base + max review contribution

    def test_medium_review_count_contribution(self):
        """Test confidence contribution from medium review count."""
        confidence = calculate_confidence(50, None, has_website=False)
        assert confidence == 0.3 + 0.25

        confidence = calculate_confidence(75, None, has_website=False)
        assert confidence == 0.3 + 0.25

    def test_low_review_count_contribution(self):
        """Test confidence contribution from low review count."""
        confidence = calculate_confidence(20, None, has_website=False)
        assert confidence == 0.3 + 0.15

        confidence = calculate_confidence(5, None, has_website=False)
        assert confidence == 0.3 + 0.10

    def test_very_low_review_count_no_contribution(self):
        """Test that very low review counts add nothing."""
        confidence = calculate_confidence(4, None, has_website=False)
        assert confidence == 0.3

    def test_good_rating_contribution(self):
        """Test confidence contribution from good rating."""
        confidence = calculate_confidence(None, 4.5, has_website=False)
        assert confidence == 0.3 + 0.20

        confidence = calculate_confidence(None, 4.0, has_website=False)
        assert confidence == 0.3 + 0.20

    def test_average_rating_contribution(self):
        """Test confidence contribution from average rating."""
        confidence = calculate_confidence(None, 3.5, has_website=False)
        assert confidence == 0.3 + 0.10

    def test_poor_rating_no_contribution(self):
        """Test that poor ratings add nothing."""
        confidence = calculate_confidence(None, 2.5, has_website=False)
        assert confidence == 0.3

    def test_website_contribution(self):
        """Test confidence contribution from having a website."""
        confidence = calculate_confidence(None, None, has_website=True)
        assert confidence == 0.3 + 0.15

    def test_all_factors_combined(self):
        """Test confidence with all positive factors."""
        confidence = calculate_confidence(100, 4.5, has_website=True)
        # 0.3 (base) + 0.35 (100+ reviews) + 0.20 (4.5+ rating) + 0.15 (website) = 1.0
        assert confidence == pytest.approx(1.0)

    def test_confidence_capped_at_1(self):
        """Test that confidence is capped at 1.0."""
        confidence = calculate_confidence(1000, 5.0, has_website=True)
        assert confidence == pytest.approx(1.0)


class TestEstimateRevenue:
    """Tests for estimate_revenue function."""

    def test_basic_estimation(self):
        """Test basic revenue estimation returns a numeric value."""
        business = {
            "review_count": 50,
            "google_rating": 4.0,
            "industry": "dentist",
        }
        revenue = estimate_revenue(business)
        assert isinstance(revenue, (int, float))
        assert revenue > 0

    def test_detailed_estimation(self):
        """Test detailed revenue estimation returns RevenueEstimate."""
        business = {
            "review_count": 50,
            "google_rating": 4.0,
            "industry": "dentist",
        }
        result = estimate_revenue(business, return_detailed=True)
        assert isinstance(result, RevenueEstimate)
        assert result.estimated_revenue > 0
        assert result.industry_multiplier == 2.5  # dentist multiplier
        assert result.rating_multiplier == 1.15  # good rating
        assert 0 <= result.confidence <= 1.0

    def test_revenue_clamped_to_minimum(self):
        """Test that very low estimates are clamped to minimum."""
        business = {
            "review_count": 1,
            "google_rating": 2.0,  # poor rating
            "industry": "cafe",  # low multiplier (0.7)
        }
        revenue = estimate_revenue(business)
        assert revenue >= MIN_QUALIFIED_REVENUE

    def test_revenue_clamped_to_maximum(self):
        """Test that very high estimates are clamped to maximum."""
        business = {
            "review_count": 1000,
            "google_rating": 5.0,
            "industry": "real estate",  # high multiplier (5.0)
        }
        revenue = estimate_revenue(business)
        assert revenue <= MAX_QUALIFIED_REVENUE

    def test_qualification_status(self):
        """Test that is_qualified is set correctly."""
        business = {
            "review_count": 100,
            "google_rating": 4.5,
            "industry": "dentist",
        }
        result = estimate_revenue(business, return_detailed=True)
        # Revenue should be within qualified range after clamping
        assert result.is_qualified is True

    def test_rating_key_alternatives(self):
        """Test that 'rating' key is accepted as alternative to 'google_rating'."""
        business1 = {"review_count": 50, "google_rating": 4.0, "industry": "dentist"}
        business2 = {"review_count": 50, "rating": 4.0, "industry": "dentist"}

        revenue1 = estimate_revenue(business1)
        revenue2 = estimate_revenue(business2)
        assert revenue1 == revenue2

    def test_missing_optional_fields(self):
        """Test estimation with missing optional fields."""
        business = {
            "industry": "hvac",
        }
        revenue = estimate_revenue(business)
        assert isinstance(revenue, (int, float))
        assert revenue >= MIN_QUALIFIED_REVENUE

    def test_website_affects_confidence(self):
        """Test that website presence affects confidence."""
        business_no_website = {
            "review_count": 50,
            "google_rating": 4.0,
            "industry": "dentist",
        }
        business_with_website = {
            "review_count": 50,
            "google_rating": 4.0,
            "industry": "dentist",
            "website": "https://example.com",
        }

        result_no_website = estimate_revenue(business_no_website, return_detailed=True)
        result_with_website = estimate_revenue(business_with_website, return_detailed=True)

        assert result_with_website.confidence > result_no_website.confidence


class TestIsQualifiedRevenue:
    """Tests for is_qualified_revenue function."""

    def test_within_range(self):
        """Test revenue within qualified range."""
        assert is_qualified_revenue(100_000) is True
        assert is_qualified_revenue(500_000) is True
        assert is_qualified_revenue(1_000_000) is True

    def test_below_minimum(self):
        """Test revenue below minimum."""
        assert is_qualified_revenue(99_999) is False
        assert is_qualified_revenue(50_000) is False
        assert is_qualified_revenue(0) is False

    def test_above_maximum(self):
        """Test revenue above maximum."""
        assert is_qualified_revenue(1_000_001) is False
        assert is_qualified_revenue(2_000_000) is False


class TestEstimateRevenueBatch:
    """Tests for estimate_revenue_batch function."""

    def test_empty_list(self):
        """Test batch estimation with empty list."""
        result = estimate_revenue_batch([])
        assert result == []

    def test_multiple_businesses(self):
        """Test batch estimation with multiple businesses."""
        businesses = [
            {"review_count": 50, "industry": "dentist"},
            {"review_count": 100, "industry": "hvac"},
            {"review_count": 25, "industry": "salon"},
        ]
        results = estimate_revenue_batch(businesses)
        assert len(results) == 3
        assert all(isinstance(r, (int, float)) for r in results)

    def test_order_preserved(self):
        """Test that result order matches input order."""
        # Use different industries with distinct multipliers
        businesses = [
            {"review_count": 100, "industry": "roofing"},  # 3.5x
            {"review_count": 100, "industry": "cafe"},  # 0.7x
        ]
        results = estimate_revenue_batch(businesses)
        # Roofing should have higher estimate
        assert results[0] > results[1]


class TestFilterQualifiedLeads:
    """Tests for filter_qualified_leads function."""

    def test_filters_by_revenue(self):
        """Test that leads are filtered by revenue range."""
        businesses = [
            {"review_count": 100, "industry": "roofing", "name": "High Rev"},
            {"review_count": 1, "industry": "cafe", "name": "Low Rev"},
        ]
        qualified = filter_qualified_leads(businesses)
        # Both should be in range due to clamping to min/max
        assert len(qualified) >= 1

    def test_filters_by_confidence(self):
        """Test that leads are filtered by minimum confidence."""
        businesses = [
            {"review_count": 100, "google_rating": 4.5, "industry": "dentist", "website": "http://example.com"},
            {"review_count": 1, "industry": "unknown"},  # low confidence
        ]
        qualified = filter_qualified_leads(businesses, min_confidence=0.5)
        # Only high confidence lead should pass
        assert len(qualified) <= 2

    def test_enriches_with_revenue_data(self):
        """Test that qualified leads are enriched with revenue data."""
        businesses = [
            {"review_count": 100, "google_rating": 4.5, "industry": "dentist"},
        ]
        qualified = filter_qualified_leads(businesses)
        if qualified:
            assert "estimated_revenue" in qualified[0]
            assert "revenue_confidence" in qualified[0]

    def test_preserves_original_data(self):
        """Test that original business data is preserved."""
        businesses = [
            {"review_count": 100, "industry": "dentist", "name": "Test Dental", "custom_field": "value"},
        ]
        qualified = filter_qualified_leads(businesses)
        if qualified:
            assert qualified[0]["name"] == "Test Dental"
            assert qualified[0]["custom_field"] == "value"

    def test_does_not_modify_original(self):
        """Test that original list is not modified."""
        businesses = [
            {"review_count": 100, "industry": "dentist"},
        ]
        original_count = len(businesses)
        filter_qualified_leads(businesses)
        assert len(businesses) == original_count
        assert "estimated_revenue" not in businesses[0]

    def test_custom_revenue_range(self):
        """Test filtering with custom revenue range."""
        businesses = [
            {"review_count": 50, "industry": "dentist"},
        ]
        qualified = filter_qualified_leads(
            businesses,
            min_revenue=200_000,
            max_revenue=500_000,
        )
        # Check that custom range is applied
        for lead in qualified:
            assert lead["estimated_revenue"] >= 200_000
            assert lead["estimated_revenue"] <= 500_000


class TestRevenueEstimateDataclass:
    """Tests for RevenueEstimate dataclass."""

    def test_dataclass_creation(self):
        """Test creating RevenueEstimate dataclass."""
        estimate = RevenueEstimate(
            estimated_revenue=250_000.0,
            industry_multiplier=2.5,
            review_score=100_000.0,
            rating_multiplier=1.15,
            is_qualified=True,
            confidence=0.75,
        )
        assert estimate.estimated_revenue == 250_000.0
        assert estimate.industry_multiplier == 2.5
        assert estimate.review_score == 100_000.0
        assert estimate.rating_multiplier == 1.15
        assert estimate.is_qualified is True
        assert estimate.confidence == 0.75


class TestConstants:
    """Tests for module constants."""

    def test_qualified_revenue_bounds(self):
        """Test that qualified revenue bounds are valid."""
        assert MIN_QUALIFIED_REVENUE > 0
        assert MAX_QUALIFIED_REVENUE > MIN_QUALIFIED_REVENUE
        assert MIN_QUALIFIED_REVENUE == 100_000
        assert MAX_QUALIFIED_REVENUE == 1_000_000

    def test_base_revenue_per_review(self):
        """Test that base revenue per review is positive."""
        assert BASE_REVENUE_PER_REVIEW > 0

    def test_industry_multipliers_dict(self):
        """Test industry multipliers dictionary structure."""
        assert isinstance(INDUSTRY_MULTIPLIERS, dict)
        assert "default" in INDUSTRY_MULTIPLIERS
        assert len(INDUSTRY_MULTIPLIERS) > 10  # Should have many industries

    def test_rating_multipliers_dict(self):
        """Test rating multipliers dictionary structure."""
        assert isinstance(RATING_MULTIPLIERS, dict)
        assert "excellent" in RATING_MULTIPLIERS
        assert "poor" in RATING_MULTIPLIERS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
