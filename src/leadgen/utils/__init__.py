"""Lead Generation Utility Functions.

This module provides utility functions for lead generation operations
including revenue estimation, dossier generation, and email templates.
"""

from typing import TYPE_CHECKING

# Direct imports for utilities (no external dependencies)
from .revenue_heuristics import (
    estimate_revenue,
    get_industry_multiplier,
    calculate_review_score,
    is_qualified_revenue,
    INDUSTRY_MULTIPLIERS,
    MIN_QUALIFIED_REVENUE,
    MAX_QUALIFIED_REVENUE,
)

__all__ = [
    "estimate_revenue",
    "get_industry_multiplier",
    "calculate_review_score",
    "is_qualified_revenue",
    "INDUSTRY_MULTIPLIERS",
    "MIN_QUALIFIED_REVENUE",
    "MAX_QUALIFIED_REVENUE",
]
