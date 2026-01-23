"""Revenue estimation utilities using industry multipliers and review heuristics.

This module provides heuristic-based revenue estimation for local service businesses
based on their Google Maps data (review count, rating, industry category).

The estimation model uses:
1. Industry multipliers: Different industries have different average revenue per customer
2. Review volume: More reviews correlate with higher customer volume
3. Rating adjustments: Higher ratings can command premium pricing

Target range: $100K-$1M annual revenue (local service business sweet spot)
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union


# Revenue qualification bounds (in USD)
MIN_QUALIFIED_REVENUE = 100_000
MAX_QUALIFIED_REVENUE = 1_000_000

# Base revenue per review (assumes ~10% of customers leave reviews)
# Average transaction value * customers per review
BASE_REVENUE_PER_REVIEW = 1_500

# Industry-specific multipliers based on typical transaction values
# Higher value = higher revenue per customer interaction
INDUSTRY_MULTIPLIERS: Dict[str, float] = {
    # Medical & Health
    "dentist": 2.5,          # High-value procedures
    "dental": 2.5,
    "orthodontist": 3.0,     # Premium dental services
    "doctor": 2.2,
    "medical": 2.2,
    "physician": 2.2,
    "chiropractor": 1.8,
    "optometrist": 2.0,
    "physical therapy": 1.9,
    "veterinarian": 1.7,
    "vet": 1.7,

    # Home Services
    "hvac": 2.8,             # High-ticket installations
    "plumber": 2.2,
    "plumbing": 2.2,
    "electrician": 2.0,
    "electrical": 2.0,
    "roofing": 3.5,          # Large project value
    "roofer": 3.5,
    "contractor": 3.0,
    "landscaping": 1.8,
    "landscaper": 1.8,
    "pest control": 1.4,
    "cleaning": 1.2,
    "home cleaning": 1.2,

    # Personal Services
    "salon": 1.3,
    "hair salon": 1.3,
    "spa": 1.6,
    "barber": 1.1,
    "beauty": 1.4,

    # Automotive
    "auto repair": 1.8,
    "mechanic": 1.8,
    "car wash": 0.9,
    "auto body": 2.5,

    # Legal & Professional
    "lawyer": 4.0,           # High hourly rates
    "attorney": 4.0,
    "accountant": 2.5,
    "cpa": 2.5,
    "real estate": 5.0,      # Commission-based high value
    "insurance": 1.5,

    # Fitness & Recreation
    "gym": 1.0,
    "fitness": 1.0,
    "yoga": 1.2,
    "martial arts": 1.3,
    "personal trainer": 1.5,

    # Food & Hospitality
    "restaurant": 1.0,
    "catering": 2.0,
    "bakery": 0.8,
    "cafe": 0.7,

    # Education & Childcare
    "daycare": 1.8,
    "childcare": 1.8,
    "tutoring": 1.4,
    "driving school": 1.5,

    # Default for unknown industries
    "default": 1.5,
}

# Rating multipliers (higher ratings = premium pricing ability)
# Ratings below 3.5 get penalized, above 4.0 get bonus
RATING_MULTIPLIERS: Dict[str, float] = {
    "excellent": 1.3,    # 4.5+
    "good": 1.15,        # 4.0-4.5
    "average": 1.0,      # 3.5-4.0
    "below_average": 0.8,# 3.0-3.5
    "poor": 0.5,         # Below 3.0
}


@dataclass
class RevenueEstimate:
    """Structured revenue estimation result.

    Attributes:
        estimated_revenue: Calculated annual revenue in USD.
        industry_multiplier: The industry-specific multiplier used.
        review_score: The review-based score component.
        rating_multiplier: The rating-based adjustment factor.
        is_qualified: Whether revenue falls within target range.
        confidence: Confidence level based on data quality (0.0-1.0).
    """
    estimated_revenue: float
    industry_multiplier: float
    review_score: float
    rating_multiplier: float
    is_qualified: bool
    confidence: float


def get_industry_multiplier(industry: str) -> float:
    """Get the revenue multiplier for a given industry.

    Args:
        industry: Industry category string (case-insensitive).

    Returns:
        Float multiplier for the industry (default 1.5 if unknown).
    """
    if not industry:
        return INDUSTRY_MULTIPLIERS["default"]

    # Normalize industry string
    industry_lower = industry.lower().strip()

    # Direct match
    if industry_lower in INDUSTRY_MULTIPLIERS:
        return INDUSTRY_MULTIPLIERS[industry_lower]

    # Partial match (industry contains key or key contains industry)
    for key, multiplier in INDUSTRY_MULTIPLIERS.items():
        if key == "default":
            continue
        if key in industry_lower or industry_lower in key:
            return multiplier

    return INDUSTRY_MULTIPLIERS["default"]


def get_rating_multiplier(rating: Optional[float]) -> float:
    """Get the rating-based revenue multiplier.

    Args:
        rating: Google Maps star rating (0.0-5.0), or None.

    Returns:
        Float multiplier based on rating quality.
    """
    if rating is None:
        return 1.0  # No rating data, use neutral multiplier

    if rating >= 4.5:
        return RATING_MULTIPLIERS["excellent"]
    elif rating >= 4.0:
        return RATING_MULTIPLIERS["good"]
    elif rating >= 3.5:
        return RATING_MULTIPLIERS["average"]
    elif rating >= 3.0:
        return RATING_MULTIPLIERS["below_average"]
    else:
        return RATING_MULTIPLIERS["poor"]


def calculate_review_score(review_count: Optional[int]) -> float:
    """Calculate revenue score based on review volume.

    Uses logarithmic scaling to prevent runaway estimates for
    businesses with very high review counts.

    Args:
        review_count: Number of Google reviews, or None.

    Returns:
        Float score representing review-based revenue potential.
    """
    if not review_count or review_count <= 0:
        return 50.0  # Minimum baseline for businesses with no reviews

    import math

    # Logarithmic scaling with linear component
    # This gives diminishing returns for very high review counts
    # while still rewarding more reviews
    base_score = review_count * BASE_REVENUE_PER_REVIEW

    # Apply logarithmic dampening for high review counts
    # Prevents estimates from becoming unrealistic
    if review_count > 200:
        # Logarithmic scaling after 200 reviews
        dampening = 1 + math.log10(review_count / 200)
        base_score = (200 * BASE_REVENUE_PER_REVIEW) + (
            (review_count - 200) * BASE_REVENUE_PER_REVIEW / dampening
        )

    return base_score


def calculate_confidence(
    review_count: Optional[int],
    rating: Optional[float],
    has_website: bool = False
) -> float:
    """Calculate confidence level for the revenue estimate.

    Args:
        review_count: Number of reviews (more = higher confidence).
        rating: Star rating (presence increases confidence).
        has_website: Whether business has a website.

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    confidence = 0.3  # Base confidence

    # Review count contribution (up to +0.35)
    if review_count:
        if review_count >= 100:
            confidence += 0.35
        elif review_count >= 50:
            confidence += 0.25
        elif review_count >= 20:
            confidence += 0.15
        elif review_count >= 5:
            confidence += 0.10

    # Rating contribution (up to +0.20)
    if rating is not None:
        if rating >= 4.0:
            confidence += 0.20
        elif rating >= 3.0:
            confidence += 0.10

    # Website contribution (+0.15)
    if has_website:
        confidence += 0.15

    return min(confidence, 1.0)


def estimate_revenue(
    business_data: Dict[str, Any],
    return_detailed: bool = False
) -> Union[float, RevenueEstimate]:
    """Estimate annual revenue for a business based on available data.

    Uses industry multipliers and review volume heuristics to estimate
    revenue within the target range of $100K-$1M.

    Args:
        business_data: Dictionary containing business information with keys:
            - review_count (int): Number of Google reviews
            - google_rating or rating (float): Star rating (0.0-5.0)
            - industry (str): Business industry/category
            - website (str, optional): Business website URL
        return_detailed: If True, return RevenueEstimate dataclass
            with additional metrics. Default False returns just the
            revenue float.

    Returns:
        If return_detailed is False: Float estimated annual revenue in USD.
        If return_detailed is True: RevenueEstimate dataclass with full details.

    Examples:
        >>> estimate_revenue({'review_count': 100, 'google_rating': 4.5, 'industry': 'dentist'})
        487500.0

        >>> estimate_revenue({'review_count': 50, 'google_rating': 4.0, 'industry': 'salon'})
        112125.0
    """
    # Extract data with defaults
    review_count = business_data.get("review_count", 0)
    rating = business_data.get("google_rating") or business_data.get("rating")
    industry = business_data.get("industry", "")
    website = business_data.get("website", "")

    # Calculate components
    industry_multiplier = get_industry_multiplier(industry)
    rating_multiplier = get_rating_multiplier(rating)
    review_score = calculate_review_score(review_count)

    # Calculate base revenue estimate
    estimated_revenue = review_score * industry_multiplier * rating_multiplier

    # Clamp to target range
    # If below minimum, scale up but flag lower confidence
    # If above maximum, cap at maximum
    estimated_revenue = max(MIN_QUALIFIED_REVENUE, min(estimated_revenue, MAX_QUALIFIED_REVENUE))

    # Check qualification
    is_qualified = MIN_QUALIFIED_REVENUE <= estimated_revenue <= MAX_QUALIFIED_REVENUE

    # Calculate confidence
    confidence = calculate_confidence(
        review_count,
        rating,
        has_website=bool(website)
    )

    if return_detailed:
        return RevenueEstimate(
            estimated_revenue=estimated_revenue,
            industry_multiplier=industry_multiplier,
            review_score=review_score,
            rating_multiplier=rating_multiplier,
            is_qualified=is_qualified,
            confidence=confidence,
        )

    return estimated_revenue


def is_qualified_revenue(revenue: float) -> bool:
    """Check if a revenue estimate falls within the qualified range.

    Args:
        revenue: Estimated annual revenue in USD.

    Returns:
        True if revenue is between $100K and $1M.
    """
    return MIN_QUALIFIED_REVENUE <= revenue <= MAX_QUALIFIED_REVENUE


def estimate_revenue_batch(
    businesses: list[Dict[str, Any]]
) -> list[float]:
    """Estimate revenue for multiple businesses.

    Args:
        businesses: List of business data dictionaries.

    Returns:
        List of estimated revenues in same order as input.
    """
    return [estimate_revenue(biz) for biz in businesses]


def filter_qualified_leads(
    businesses: list[Dict[str, Any]],
    min_revenue: float = MIN_QUALIFIED_REVENUE,
    max_revenue: float = MAX_QUALIFIED_REVENUE,
    min_confidence: float = 0.3
) -> list[Dict[str, Any]]:
    """Filter businesses to only those meeting revenue criteria.

    Args:
        businesses: List of business data dictionaries.
        min_revenue: Minimum qualified revenue (default $100K).
        max_revenue: Maximum qualified revenue (default $1M).
        min_confidence: Minimum confidence score required.

    Returns:
        Filtered list of businesses with added 'estimated_revenue'
        and 'revenue_confidence' fields.
    """
    qualified = []

    for business in businesses:
        result = estimate_revenue(business, return_detailed=True)

        if (
            min_revenue <= result.estimated_revenue <= max_revenue
            and result.confidence >= min_confidence
        ):
            # Add revenue data to business dict
            enriched = business.copy()
            enriched["estimated_revenue"] = result.estimated_revenue
            enriched["revenue_confidence"] = result.confidence
            qualified.append(enriched)

    return qualified
