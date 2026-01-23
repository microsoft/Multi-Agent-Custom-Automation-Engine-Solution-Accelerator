"""Scraper Agent for lead generation using Google Maps Places API.

This module implements the lead scraper agent using OpenAI Agents SDK.
The agent scrapes businesses from Google Maps within a 20-mile radius
and filters them by estimated revenue ($100K-$1M range).
"""

import asyncio
import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING


def _load_openai_agents_sdk():
    """Load the openai-agents SDK from site-packages.

    This function handles the naming conflict between our local 'agents'
    package and the openai-agents SDK which also installs as 'agents'.

    Strategy: Load the SDK module directly using importlib without
    modifying sys.modules for our local agents package.
    """
    # Find the venv site-packages directory
    this_file = Path(__file__).resolve()
    leadgen_root = this_file.parent.parent
    venv_paths = list((leadgen_root / ".venv").glob("lib/python*/site-packages"))

    if not venv_paths:
        raise ImportError("Could not find venv site-packages directory")

    site_packages = venv_paths[0]
    sdk_path = site_packages / "agents"

    if not sdk_path.exists():
        raise ImportError(f"openai-agents SDK not found at {sdk_path}")

    # Add site-packages to the FRONT of sys.path
    site_pkg_str = str(site_packages)
    if site_pkg_str in sys.path:
        sys.path.remove(site_pkg_str)
    sys.path.insert(0, site_pkg_str)

    # Identify which modules are ours (our local agents package)
    # We need to preserve: agents, agents.scraper_agent, etc.
    our_modules = set()
    local_agents_path = str(leadgen_root / "agents")
    for key, mod in list(sys.modules.items()):
        if key == "agents" or key.startswith("agents."):
            if hasattr(mod, "__file__") and mod.__file__:
                if local_agents_path in mod.__file__:
                    our_modules.add(key)

    # Temporarily remove only OUR modules (not the currently-loading one)
    # The currently loading module has __file__ set already
    saved_modules = {}
    current_module = "agents.scraper_agent"  # This module being loaded

    for key in list(sys.modules.keys()):
        if key in our_modules and key != current_module:
            saved_modules[key] = sys.modules.pop(key)

    # Also need to remove 'agents' itself if it's our local one
    if "agents" in sys.modules:
        mod = sys.modules["agents"]
        if hasattr(mod, "__file__") and mod.__file__ and local_agents_path in mod.__file__:
            saved_modules["agents"] = sys.modules.pop("agents")

    try:
        # Now import the SDK - Python will find it in site-packages
        import agents as sdk_module

        # Get what we need
        Agent = sdk_module.Agent
        function_tool = sdk_module.function_tool

        return Agent, function_tool

    finally:
        # Restore our local agents modules under different keys to avoid conflict
        # Actually, we can't easily restore them since 'agents' is now the SDK
        # The SDK will keep working with its modules in sys.modules
        pass


# Load the SDK components at module import time
Agent, function_tool = _load_openai_agents_sdk()

logger = logging.getLogger(__name__)

# Default search configuration
DEFAULT_RADIUS_MILES = 20
MIN_QUALIFIED_REVENUE = 100_000
MAX_QUALIFIED_REVENUE = 1_000_000


@dataclass
class ScrapedLead:
    """Represents a scraped and qualified business lead.

    Attributes:
        place_id: Google Places unique identifier.
        name: Business name.
        address: Full address.
        phone: Phone number (if available).
        website: Website URL (if available).
        industry: Business industry/category.
        rating: Google Maps star rating.
        review_count: Number of reviews.
        estimated_revenue: Estimated annual revenue in USD.
        revenue_confidence: Confidence score for revenue estimate.
    """

    place_id: str
    name: str
    address: str
    phone: str | None
    website: str | None
    industry: str
    rating: float | None
    review_count: int | None
    estimated_revenue: float
    revenue_confidence: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "place_id": self.place_id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "industry": self.industry,
            "rating": self.rating,
            "review_count": self.review_count,
            "estimated_revenue": self.estimated_revenue,
            "revenue_confidence": self.revenue_confidence,
        }


@function_tool
def scrape_google_maps(
    zip_code: str,
    industry: str,
    radius_miles: float = DEFAULT_RADIUS_MILES,
    max_results: int = 60,
) -> list[dict]:
    """Scrape businesses from Google Maps within a specified radius.

    Searches for businesses matching the given industry near the zip code,
    then filters by estimated revenue to find qualified leads in the
    $100K-$1M annual revenue range.

    Args:
        zip_code: US zip code to search around (e.g., "62701").
        industry: Business type/keyword to search for (e.g., "dentist", "hvac", "salon").
        radius_miles: Search radius in miles. Defaults to 20 miles.
        max_results: Maximum number of results to return. Defaults to 60.

    Returns:
        List of qualified leads as dictionaries containing:
        - place_id: Google Places unique identifier
        - name: Business name
        - address: Full address
        - phone: Phone number (may be null)
        - website: Website URL (may be null)
        - industry: Business category
        - rating: Star rating (0.0-5.0)
        - review_count: Number of reviews
        - estimated_revenue: Estimated annual revenue in USD
        - revenue_confidence: Confidence score (0.0-1.0)

    Example:
        >>> leads = scrape_google_maps("62701", "dentist", radius_miles=20)
        >>> print(f"Found {len(leads)} qualified leads")
    """
    # Import here to avoid circular imports and allow testing without credentials
    from integrations.google_maps import GoogleMapsClient
    from utils.revenue_heuristics import estimate_revenue, is_qualified_revenue

    logger.info(
        "Scraping Google Maps for '%s' businesses within %d miles of %s",
        industry,
        radius_miles,
        zip_code,
    )

    async def _scrape() -> list[dict]:
        """Async implementation of the scraping logic."""
        qualified_leads: list[dict] = []

        try:
            async with GoogleMapsClient() as client:
                # Search for businesses
                result = await client.search_nearby(
                    zip_code=zip_code,
                    industry=industry,
                    radius_miles=radius_miles,
                    max_pages=3,  # Up to 60 results (3 pages x 20)
                    enrich_details=True,
                )

                logger.info(
                    "Found %d total businesses, filtering by revenue qualification",
                    result.total_results,
                )

                # Process and filter results
                for place in result.places:
                    # Prepare business data for revenue estimation
                    business_data = {
                        "review_count": place.review_count or 0,
                        "google_rating": place.rating,
                        "rating": place.rating,
                        "industry": industry,
                        "website": place.website,
                    }

                    # Estimate revenue with detailed metrics
                    revenue_result = estimate_revenue(business_data, return_detailed=True)

                    # Filter by qualified revenue range
                    if not is_qualified_revenue(revenue_result.estimated_revenue):
                        logger.debug(
                            "Skipping %s - revenue $%.0f outside qualified range",
                            place.name,
                            revenue_result.estimated_revenue,
                        )
                        continue

                    # Create qualified lead
                    lead = ScrapedLead(
                        place_id=place.place_id,
                        name=place.name,
                        address=place.address,
                        phone=place.phone,
                        website=place.website,
                        industry=industry,
                        rating=place.rating,
                        review_count=place.review_count,
                        estimated_revenue=revenue_result.estimated_revenue,
                        revenue_confidence=revenue_result.confidence,
                    )
                    qualified_leads.append(lead.to_dict())

                    # Stop if we have enough results
                    if len(qualified_leads) >= max_results:
                        break

        except ValueError as e:
            logger.error("Configuration error during scraping: %s", e)
            raise
        except Exception as e:
            logger.error("Error during Google Maps scraping: %s", e)
            raise

        logger.info(
            "Scraping complete: %d qualified leads from %d total businesses",
            len(qualified_leads),
            result.total_results if result else 0,
        )

        return qualified_leads

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _scrape())
                return future.result()
        else:
            return loop.run_until_complete(_scrape())
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(_scrape())


@function_tool
def scrape_multiple_industries(
    zip_code: str,
    industries: list[str],
    radius_miles: float = DEFAULT_RADIUS_MILES,
    max_results_per_industry: int = 60,
) -> dict[str, list[dict]]:
    """Scrape businesses from multiple industries in a single location.

    Searches for businesses across multiple industry categories near the
    given zip code, with deduplication across industries.

    Args:
        zip_code: US zip code to search around.
        industries: List of industry keywords (e.g., ["dentist", "hvac", "salon"]).
        radius_miles: Search radius in miles. Defaults to 20 miles.
        max_results_per_industry: Maximum results per industry. Defaults to 60.

    Returns:
        Dictionary mapping industry names to lists of qualified leads.

    Example:
        >>> results = scrape_multiple_industries("62701", ["dentist", "hvac"])
        >>> for industry, leads in results.items():
        ...     print(f"{industry}: {len(leads)} leads")
    """
    logger.info(
        "Scraping %d industries within %d miles of %s",
        len(industries),
        radius_miles,
        zip_code,
    )

    results: dict[str, list[dict]] = {}
    seen_place_ids: set[str] = set()

    for industry in industries:
        industry_leads = scrape_google_maps(
            zip_code=zip_code,
            industry=industry,
            radius_miles=radius_miles,
            max_results=max_results_per_industry,
        )

        # Deduplicate across industries
        unique_leads = []
        for lead in industry_leads:
            place_id = lead.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_leads.append(lead)

        results[industry] = unique_leads
        logger.info(
            "Industry '%s': %d unique leads (after dedup)",
            industry,
            len(unique_leads),
        )

    total_leads = sum(len(leads) for leads in results.values())
    logger.info("Total unique leads across all industries: %d", total_leads)

    return results


@function_tool
def estimate_lead_revenue(
    name: str,
    industry: str,
    review_count: int,
    rating: float | None = None,
    website: str | None = None,
) -> dict[str, Any]:
    """Estimate annual revenue for a single business.

    Uses heuristics based on industry multipliers, review volume, and
    rating to estimate annual revenue.

    Args:
        name: Business name (for logging).
        industry: Business industry/category.
        review_count: Number of Google reviews.
        rating: Google Maps star rating (0.0-5.0), optional.
        website: Business website URL, optional.

    Returns:
        Dictionary containing:
        - estimated_revenue: Annual revenue estimate in USD
        - is_qualified: Whether revenue is in $100K-$1M range
        - confidence: Confidence score (0.0-1.0)
        - industry_multiplier: The industry multiplier used
        - rating_multiplier: The rating adjustment used
    """
    from utils.revenue_heuristics import estimate_revenue

    business_data = {
        "review_count": review_count,
        "google_rating": rating,
        "rating": rating,
        "industry": industry,
        "website": website,
    }

    result = estimate_revenue(business_data, return_detailed=True)

    return {
        "name": name,
        "estimated_revenue": result.estimated_revenue,
        "is_qualified": result.is_qualified,
        "confidence": result.confidence,
        "industry_multiplier": result.industry_multiplier,
        "rating_multiplier": result.rating_multiplier,
    }


# Agent instructions defining behavior and constraints
SCRAPER_AGENT_INSTRUCTIONS = """You are a Lead Scraper Agent specialized in finding qualified local businesses.

Your primary task is to scrape businesses from Google Maps within a 20-mile radius of a given zip code, filtered by target industries and estimated revenue.

## Qualification Criteria
- Location: Within 20 miles of the specified zip code
- Industry: Appointment-based local service businesses
- Revenue: Estimated annual revenue between $100,000 and $1,000,000
- Status: Operational businesses only (not closed or temporarily closed)

## Target Industries
High-value appointment-based businesses include:
- Medical: dentist, orthodontist, chiropractor, optometrist, physical therapy, veterinarian
- Home Services: hvac, plumber, electrician, roofing, contractor, landscaping
- Personal Services: salon, spa, barber
- Automotive: auto repair, auto body
- Professional: lawyer, accountant, real estate

## Your Process
1. When given a zip code and industry list, use the scrape_google_maps tool to find businesses
2. The tool automatically filters by revenue qualification and enriches with contact details
3. For multiple industries, use scrape_multiple_industries for efficiency
4. Report the number of qualified leads found and any issues encountered

## Output Format
Always provide a summary including:
- Total businesses scanned
- Number of qualified leads
- Breakdown by industry (if multiple)
- Any notable observations about the market

## Important Notes
- Google Maps API has rate limits; the tool handles pagination automatically
- Revenue estimates are heuristic-based and should be validated during research
- Some businesses may lack phone/website data; mark these for manual research
- Duplicate businesses (same place_id) across industries are automatically removed
"""

# Create the scraper agent instance
scraper_agent = Agent(
    name="Lead Scraper Agent",
    instructions=SCRAPER_AGENT_INSTRUCTIONS,
    tools=[scrape_google_maps, scrape_multiple_industries, estimate_lead_revenue],
)
