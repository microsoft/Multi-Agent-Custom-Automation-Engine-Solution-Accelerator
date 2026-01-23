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

from .dossier_template import (
    generate_dossier,
    generate_dossier_from_dict,
    validate_dossier_sections,
    is_dossier_valid,
    get_default_pain_points,
    generate_gotcha_qas_from_data,
    DossierData,
    DossierStatus,
    CompanyOverview,
    Service,
    TeamMember,
    PainPoint,
    GotchaQA,
    Competitor,
)

__all__ = [
    # Revenue heuristics
    "estimate_revenue",
    "get_industry_multiplier",
    "calculate_review_score",
    "is_qualified_revenue",
    "INDUSTRY_MULTIPLIERS",
    "MIN_QUALIFIED_REVENUE",
    "MAX_QUALIFIED_REVENUE",
    # Dossier template
    "generate_dossier",
    "generate_dossier_from_dict",
    "validate_dossier_sections",
    "is_dossier_valid",
    "get_default_pain_points",
    "generate_gotcha_qas_from_data",
    "DossierData",
    "DossierStatus",
    "CompanyOverview",
    "Service",
    "TeamMember",
    "PainPoint",
    "GotchaQA",
    "Competitor",
]
