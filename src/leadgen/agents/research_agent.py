"""Research Agent for deep business research using Firecrawl and Apollo.

This module implements the research agent using OpenAI Agents SDK.
The agent performs deep research on business leads including:
- Website scraping via Firecrawl
- Contact enrichment via Apollo
- Social profile extraction
- Review analysis
- Comprehensive dossier generation

Required dossier sections per spec FR-3:
- Company overview
- Services
- Team
- Pain points
- Gotcha Q&As
- Competitor landscape
"""

import asyncio
import concurrent.futures
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


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
    our_modules = set()
    local_agents_path = str(leadgen_root / "agents")
    for key, mod in list(sys.modules.items()):
        if key == "agents" or key.startswith("agents."):
            if hasattr(mod, "__file__") and mod.__file__:
                if local_agents_path in mod.__file__:
                    our_modules.add(key)

    # Temporarily remove only OUR modules (not the currently-loading one)
    saved_modules = {}
    current_module = "agents.research_agent"  # This module being loaded

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
        # The SDK will keep working with its modules in sys.modules
        pass


# Load the SDK components at module import time
Agent, function_tool = _load_openai_agents_sdk()

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Represents the result of researching a business lead.

    Attributes:
        lead_name: Business name.
        website_content: Scraped website markdown content.
        organization_data: Apollo organization enrichment data.
        decision_makers: List of decision maker contacts.
        social_profiles: Extracted social media profiles.
        services_extracted: List of identified services.
        dossier_markdown: Generated dossier in markdown format.
        dossier_status: Status of dossier generation.
        success: Whether research was successful.
        error: Error message if research failed.
    """

    lead_name: str
    website_content: Optional[str] = None
    organization_data: Optional[dict] = None
    decision_makers: list[dict] = field(default_factory=list)
    social_profiles: dict[str, str] = field(default_factory=dict)
    services_extracted: list[str] = field(default_factory=list)
    dossier_markdown: Optional[str] = None
    dossier_status: str = "pending"
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "lead_name": self.lead_name,
            "website_content": self.website_content,
            "organization_data": self.organization_data,
            "decision_makers": self.decision_makers,
            "social_profiles": self.social_profiles,
            "services_extracted": self.services_extracted,
            "dossier_markdown": self.dossier_markdown,
            "dossier_status": self.dossier_status,
            "success": self.success,
            "error": self.error,
        }


def _extract_social_profiles_from_content(
    content: str,
    links: list[str] | None = None,
) -> dict[str, str]:
    """Extract social media profile URLs from website content and links.

    Args:
        content: Website markdown content.
        links: List of links found on the website.

    Returns:
        Dictionary mapping social platform names to profile URLs.
    """
    social_profiles: dict[str, str] = {}

    # Social media URL patterns
    patterns = {
        "facebook": r"(?:https?://)?(?:www\.)?facebook\.com/[a-zA-Z0-9._-]+/?",
        "instagram": r"(?:https?://)?(?:www\.)?instagram\.com/[a-zA-Z0-9._-]+/?",
        "twitter": r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/?",
        "linkedin": r"(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9_-]+/?",
        "youtube": r"(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|@)?[a-zA-Z0-9_-]+/?",
        "tiktok": r"(?:https?://)?(?:www\.)?tiktok\.com/@[a-zA-Z0-9._-]+/?",
        "yelp": r"(?:https?://)?(?:www\.)?yelp\.com/biz/[a-zA-Z0-9_-]+/?",
    }

    # Search in content
    for platform, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            url = match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            social_profiles[platform] = url

    # Search in links list if provided
    if links:
        for link in links:
            link_lower = link.lower()
            for platform in patterns.keys():
                if platform in link_lower and platform not in social_profiles:
                    social_profiles[platform] = link
                    break

    return social_profiles


def _extract_services_from_content(
    content: str,
    industry: str | None = None,
) -> list[dict[str, Any]]:
    """Extract services from website content using keyword patterns.

    Args:
        content: Website markdown content.
        industry: Business industry for context.

    Returns:
        List of extracted service dictionaries.
    """
    services: list[dict[str, Any]] = []

    # Common service section patterns
    service_patterns = [
        r"(?:our\s+)?services?\s*(?:include)?:?\s*([^\n]+)",
        r"(?:we\s+offer|we\s+provide|we\s+specialize\s+in):?\s*([^\n]+)",
        r"##\s*(?:our\s+)?services?\s*\n((?:[*-]\s*[^\n]+\n?)+)",
    ]

    # Industry-specific service keywords
    industry_services: dict[str, list[str]] = {
        "dentist": [
            "cleanings", "fillings", "crowns", "root canal", "extractions",
            "whitening", "veneers", "implants", "orthodontics", "braces",
            "invisalign", "dentures", "bridges", "emergency dental",
        ],
        "hvac": [
            "installation", "repair", "maintenance", "ac repair", "heating",
            "cooling", "furnace", "air conditioning", "duct cleaning",
            "thermostat", "heat pump", "emergency service",
        ],
        "salon": [
            "haircut", "color", "highlights", "balayage", "blowout",
            "styling", "extensions", "keratin", "perm", "manicure",
            "pedicure", "waxing", "facial", "massage",
        ],
    }

    content_lower = content.lower()

    # Try pattern extraction first
    for pattern in service_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if isinstance(match, str):
                # Split by common delimiters
                service_items = re.split(r"[,;•\n]", match)
                for item in service_items:
                    item = item.strip().strip("-*").strip()
                    if item and len(item) > 2 and len(item) < 100:
                        services.append({
                            "name": item,
                            "description": None,
                            "is_primary": False,
                        })

    # Supplement with industry-specific keyword matching
    industry_lower = (industry or "").lower()
    for ind_key, keywords in industry_services.items():
        if ind_key in industry_lower:
            for keyword in keywords:
                if keyword in content_lower:
                    # Check if we already have this service
                    existing = any(
                        keyword in s["name"].lower()
                        for s in services
                    )
                    if not existing:
                        services.append({
                            "name": keyword.title(),
                            "description": None,
                            "is_primary": False,
                        })

    # Mark first few as primary services
    for i, service in enumerate(services[:3]):
        service["is_primary"] = True

    # Deduplicate and limit
    seen = set()
    unique_services = []
    for service in services:
        name_lower = service["name"].lower()
        if name_lower not in seen:
            seen.add(name_lower)
            unique_services.append(service)

    return unique_services[:15]  # Limit to 15 services


def _scrape_website_content_internal(
    url: str,
    extract_links: bool = True,
) -> dict[str, Any]:
    """Internal implementation for website scraping.

    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    from integrations.firecrawl import FirecrawlClient

    logger.info("Scraping website content from: %s", url)

    async def _scrape() -> dict[str, Any]:
        """Async scraping implementation."""
        try:
            async with FirecrawlClient() as client:
                result = await client.scrape_url_safe(
                    url,
                    formats=["markdown"],
                    only_main_content=True,
                )

                return {
                    "url": url,
                    "markdown": result.markdown,
                    "title": result.metadata.get("title"),
                    "description": result.metadata.get("description"),
                    "links": result.links if extract_links else [],
                    "word_count": result.word_count,
                    "success": result.success,
                    "error": result.error,
                }

        except ValueError as e:
            logger.error("Configuration error for Firecrawl: %s", e)
            return {
                "url": url,
                "markdown": None,
                "title": None,
                "description": None,
                "links": [],
                "word_count": 0,
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error("Error scraping %s: %s", url, e)
            return {
                "url": url,
                "markdown": None,
                "title": None,
                "description": None,
                "links": [],
                "word_count": 0,
                "success": False,
                "error": str(e),
            }

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _scrape())
                return future.result()
        else:
            return loop.run_until_complete(_scrape())
    except RuntimeError:
        return asyncio.run(_scrape())


@function_tool
def scrape_website_content(
    url: str,
    extract_links: bool = True,
) -> str:
    """Scrape a business website and extract content in markdown format.

    Uses Firecrawl to scrape the website, handling JavaScript rendering
    automatically. Returns markdown content optimized for LLM consumption.

    Args:
        url: The website URL to scrape (e.g., "https://acmedental.com").
        extract_links: Whether to extract links from the page. Defaults to True.

    Returns:
        JSON string containing:
        - url: The scraped URL
        - markdown: Markdown content of the website
        - title: Page title
        - description: Meta description
        - links: List of links found on the page (if extract_links=True)
        - word_count: Approximate word count
        - success: Whether scraping was successful
        - error: Error message if scraping failed

    Example:
        >>> result_json = scrape_website_content("https://acmedental.com")
        >>> import json; result = json.loads(result_json)
        >>> print(f"Scraped {result['word_count']} words from {result['title']}")
    """
    import json
    result = _scrape_website_content_internal(url, extract_links)
    return json.dumps(result)


def _extract_social_profiles_internal(
    website_url: str,
    website_content: str | None = None,
) -> dict[str, Any]:
    """Internal implementation for social profile extraction.

    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    logger.info("Extracting social profiles from: %s", website_url)

    try:
        content = website_content
        links: list[str] = []

        # Scrape if content not provided
        if not content:
            scrape_result = _scrape_website_content_internal(website_url, extract_links=True)
            if scrape_result["success"]:
                content = scrape_result["markdown"] or ""
                links = scrape_result.get("links", [])
            else:
                return {
                    "profiles": {},
                    "platforms_found": [],
                    "success": False,
                    "error": f"Failed to scrape website: {scrape_result.get('error')}",
                }

        # Extract social profiles
        profiles = _extract_social_profiles_from_content(content or "", links)

        return {
            "profiles": profiles,
            "platforms_found": list(profiles.keys()),
            "success": True,
            "error": None,
        }

    except Exception as e:
        logger.error("Error extracting social profiles: %s", e)
        return {
            "profiles": {},
            "platforms_found": [],
            "success": False,
            "error": str(e),
        }


@function_tool
def extract_social_profiles(
    website_url: str,
    website_content: str | None = None,
) -> str:
    """Extract social media profiles from a business website.

    Analyzes website content and links to identify social media profile URLs
    for platforms like Facebook, Instagram, Twitter, LinkedIn, and YouTube.

    Args:
        website_url: The business website URL.
        website_content: Pre-scraped website content (optional). If not provided,
                        the website will be scraped first.

    Returns:
        JSON string containing:
        - profiles: Dict mapping platform names to profile URLs
        - platforms_found: List of platform names found
        - success: Whether extraction was successful
        - error: Error message if extraction failed

    Example:
        >>> result_json = extract_social_profiles("https://acmedental.com")
        >>> import json; result = json.loads(result_json)
        >>> print(f"Found profiles: {result['platforms_found']}")
    """
    import json
    result = _extract_social_profiles_internal(website_url, website_content)
    return json.dumps(result)


def _enrich_with_apollo_internal(
    business_name: str,
    website_domain: str | None = None,
    find_contacts: bool = True,
    max_contacts: int = 5,
) -> dict[str, Any]:
    """Internal implementation for Apollo enrichment.

    Returns a dict - the @function_tool version wraps this and returns JSON.
    """
    from integrations.apollo import ApolloClient

    logger.info(
        "Enriching lead with Apollo: name=%s, domain=%s",
        business_name,
        website_domain,
    )

    async def _enrich() -> dict[str, Any]:
        """Async enrichment implementation."""
        result: dict[str, Any] = {
            "organization": None,
            "decision_makers": [],
            "has_data": False,
            "success": False,
            "error": None,
        }

        try:
            async with ApolloClient() as client:
                # Enrich organization
                org = await client.enrich_organization_safe(
                    domain=website_domain,
                    name=business_name,
                )

                if org.success:
                    result["organization"] = org.to_dict()
                    result["has_data"] = True

                # Find decision makers if requested
                if find_contacts and website_domain:
                    try:
                        contacts = await client.find_decision_makers(
                            organization_domain=website_domain,
                            max_results=max_contacts,
                        )
                        result["decision_makers"] = [c.to_dict() for c in contacts]
                        if contacts:
                            result["has_data"] = True
                    except Exception as contact_error:
                        logger.warning(
                            "Failed to find decision makers: %s",
                            contact_error,
                        )
                        # Don't fail the whole enrichment

                result["success"] = True
                return result

        except ValueError as e:
            logger.error("Configuration error for Apollo: %s", e)
            result["error"] = str(e)
            return result
        except Exception as e:
            logger.error("Error enriching with Apollo: %s", e)
            result["error"] = str(e)
            return result

    # Run async code in event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _enrich())
                return future.result()
        else:
            return loop.run_until_complete(_enrich())
    except RuntimeError:
        return asyncio.run(_enrich())


@function_tool
def enrich_with_apollo(
    business_name: str,
    website_domain: str | None = None,
    find_contacts: bool = True,
    max_contacts: int = 5,
) -> str:
    """Enrich a business lead with Apollo.io organization and contact data.

    Uses Apollo API to retrieve:
    - Organization details (industry, employee count, revenue)
    - Decision maker contacts (owners, executives, directors)
    - Contact information (email, phone, LinkedIn)

    Args:
        business_name: The business name to enrich.
        website_domain: Business website domain (e.g., "acmedental.com").
        find_contacts: Whether to find decision maker contacts. Defaults to True.
        max_contacts: Maximum number of contacts to return. Defaults to 5.

    Returns:
        JSON string containing:
        - organization: Enriched organization data dict
        - decision_makers: List of decision maker contact dicts
        - has_data: Whether any enrichment data was found
        - success: Whether enrichment was successful
        - error: Error message if enrichment failed

    Example:
        >>> result_json = enrich_with_apollo("Acme Dental", "acmedental.com")
        >>> import json; result = json.loads(result_json)
        >>> if result["organization"]:
        ...     print(f"Industry: {result['organization']['industry']}")
    """
    import json
    result = _enrich_with_apollo_internal(business_name, website_domain, find_contacts, max_contacts)
    return json.dumps(result)


def _generate_research_dossier_internal(
    lead_data: dict[str, Any],
    website_content: str | None = None,
    organization_data: dict | None = None,
    decision_makers: list[dict] | None = None,
    social_profiles: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Internal implementation for dossier generation.

    This is the implementation that accepts dict parameters. The @function_tool
    decorated version wraps this with explicit parameters.
    """
    from utils.dossier_template import (
        generate_dossier_from_dict,
        validate_dossier_sections,
    )

    logger.info("Generating research dossier for: %s", lead_data.get("name", "Unknown"))

    try:
        # Build combined data for dossier generation
        dossier_input: dict[str, Any] = {
            **lead_data,
            "raw_website_content": website_content,
        }

        # Extract description from website content
        if website_content and not dossier_input.get("description"):
            # Use first paragraph as description
            lines = website_content.strip().split("\n\n")
            for line in lines:
                clean_line = line.strip().strip("#").strip()
                if clean_line and len(clean_line) > 50:
                    dossier_input["description"] = clean_line[:500]
                    break

        # Add organization data from Apollo
        if organization_data:
            if organization_data.get("industry") and not dossier_input.get("industry"):
                dossier_input["industry"] = organization_data["industry"]
            if organization_data.get("short_description") and not dossier_input.get("description"):
                dossier_input["description"] = organization_data["short_description"]
            if organization_data.get("employee_range"):
                dossier_input["employee_count"] = organization_data["employee_range"]
            if organization_data.get("founded_year"):
                dossier_input["founding_year"] = organization_data["founded_year"]
            if organization_data.get("annual_revenue"):
                dossier_input["estimated_revenue"] = organization_data["annual_revenue"]
            dossier_input["apollo_enriched"] = True

        # Add social profiles
        if social_profiles:
            dossier_input["social_profiles"] = social_profiles

        # Extract services from website content
        if website_content:
            services = _extract_services_from_content(
                website_content,
                dossier_input.get("industry"),
            )
            if services:
                dossier_input["services"] = services

        # Add decision makers as team members
        if decision_makers:
            team = []
            for dm in decision_makers:
                if dm.get("full_name") or dm.get("first_name"):
                    team.append({
                        "name": dm.get("full_name") or f"{dm.get('first_name', '')} {dm.get('last_name', '')}".strip(),
                        "title": dm.get("title"),
                        "email": dm.get("email"),
                        "linkedin": dm.get("linkedin_url"),
                    })
            if team:
                dossier_input["team"] = team

        # Generate the dossier
        dossier_markdown = generate_dossier_from_dict(
            dossier_input,
            include_defaults=True,
        )

        # Validate sections
        validation = validate_dossier_sections(dossier_markdown)
        sections_present = [s for s, present in validation.items() if present]

        # Determine status
        if all(validation.values()):
            status = "complete"
        elif any(validation.values()):
            status = "partial"
        else:
            status = "minimal"

        # Calculate word count
        word_count = len(dossier_markdown.split())

        logger.info(
            "Dossier generated: status=%s, sections=%d, words=%d",
            status,
            len(sections_present),
            word_count,
        )

        return {
            "dossier": dossier_markdown,
            "status": status,
            "sections_present": sections_present,
            "word_count": word_count,
            "success": True,
            "error": None,
        }

    except Exception as e:
        logger.error("Error generating dossier: %s", e)
        return {
            "dossier": None,
            "status": "failed",
            "sections_present": [],
            "word_count": 0,
            "success": False,
            "error": str(e),
        }


@function_tool
def generate_research_dossier(
    name: str,
    address: str | None = None,
    phone: str | None = None,
    website: str | None = None,
    industry: str | None = None,
    google_rating: float | None = None,
    review_count: int | None = None,
    estimated_revenue: float | None = None,
    website_content: str | None = None,
) -> str:
    """Generate a comprehensive research dossier for a business lead.

    Combines data from multiple sources (Google Maps, Firecrawl, Apollo)
    into a structured markdown dossier with all required sections:
    - Company Overview
    - Services
    - Team
    - Pain Points
    - Gotcha Q&As
    - Competitor Landscape

    Args:
        name: Business name (required).
        address: Business address.
        phone: Phone number.
        website: Website URL.
        industry: Industry category.
        google_rating: Google Maps rating.
        review_count: Number of Google reviews.
        estimated_revenue: Estimated annual revenue.
        website_content: Scraped website markdown content (optional).

    Returns:
        JSON string containing:
        - dossier: Complete markdown dossier string
        - status: Dossier status ("complete", "partial", "minimal")
        - sections_present: List of sections included
        - word_count: Total word count of dossier
        - success: Whether generation was successful
        - error: Error message if generation failed

    Example:
        >>> result = generate_research_dossier("Acme Dental", industry="dentist")
        >>> import json; data = json.loads(result)
        >>> print(f"Generated {data['word_count']} word dossier")
    """
    import json

    lead_data = {
        "name": name,
        "address": address,
        "phone": phone,
        "website": website,
        "industry": industry,
        "google_rating": google_rating,
        "review_count": review_count,
        "estimated_revenue": estimated_revenue,
    }

    result = _generate_research_dossier_internal(
        lead_data=lead_data,
        website_content=website_content,
    )

    return json.dumps(result)


@function_tool
def research_lead_comprehensive(
    name: str,
    website: str | None = None,
    address: str | None = None,
    phone: str | None = None,
    industry: str | None = None,
    google_rating: float | None = None,
    review_count: int | None = None,
    estimated_revenue: float | None = None,
) -> str:
    """Perform comprehensive research on a business lead.

    This is the main research function that orchestrates all research activities:
    1. Scrape website via Firecrawl (if URL provided)
    2. Extract social profiles from website
    3. Enrich with Apollo (organization + decision makers)
    4. Generate comprehensive dossier

    Use this function for full end-to-end research on a single lead.

    Args:
        name: Business name (required).
        website: Business website URL.
        address: Business address.
        phone: Business phone number.
        industry: Business industry/category.
        google_rating: Google Maps rating.
        review_count: Number of Google reviews.
        estimated_revenue: Estimated annual revenue.

    Returns:
        JSON string containing:
        - lead_data: Compiled lead information
        - website_scrape: Results from website scraping
        - social_profiles: Extracted social media profiles
        - apollo_enrichment: Apollo organization and contact data
        - dossier: Generated research dossier
        - dossier_status: Status of dossier ("complete", "partial", "minimal")
        - success: Whether research completed successfully
        - errors: List of any errors encountered

    Example:
        >>> result_json = research_lead_comprehensive(
        ...     name="Acme Dental",
        ...     website="https://acmedental.com",
        ...     industry="dentist"
        ... )
        >>> import json; result = json.loads(result_json)
        >>> print(f"Research complete: {result['dossier_status']}")
    """
    import json

    logger.info("Starting comprehensive research for: %s", name)

    result: dict[str, Any] = {
        "lead_data": {
            "name": name,
            "website": website,
            "address": address,
            "phone": phone,
            "industry": industry,
            "google_rating": google_rating,
            "review_count": review_count,
            "estimated_revenue": estimated_revenue,
        },
        "website_scrape": None,
        "social_profiles": None,
        "apollo_enrichment": None,
        "dossier": None,
        "dossier_status": "pending",
        "success": False,
        "errors": [],
    }

    website_content: str | None = None
    website_links: list[str] = []
    organization_data: dict | None = None
    decision_makers: list[dict] = []
    social_profiles_dict: dict[str, str] = {}

    # Step 1: Scrape website if URL provided
    if website:
        logger.info("Step 1: Scraping website %s", website)
        scrape_result = _scrape_website_content_internal(website, extract_links=True)
        result["website_scrape"] = scrape_result

        if scrape_result["success"]:
            website_content = scrape_result.get("markdown")
            website_links = scrape_result.get("links", [])

            # Update lead data with scraped info
            if scrape_result.get("title"):
                result["lead_data"]["website_title"] = scrape_result["title"]
            if scrape_result.get("description"):
                result["lead_data"]["website_description"] = scrape_result["description"]
        else:
            result["errors"].append(f"Website scrape failed: {scrape_result.get('error')}")

    # Step 2: Extract social profiles
    if website_content or website:
        logger.info("Step 2: Extracting social profiles")
        if website_content:
            social_profiles_dict = _extract_social_profiles_from_content(
                website_content,
                website_links,
            )
        else:
            social_result = _extract_social_profiles_internal(website or "")
            if social_result["success"]:
                social_profiles_dict = social_result.get("profiles", {})

        result["social_profiles"] = {
            "profiles": social_profiles_dict,
            "platforms_found": list(social_profiles_dict.keys()),
        }

    # Step 3: Enrich with Apollo
    # Extract domain from website URL
    domain: str | None = None
    if website:
        domain = website.replace("https://", "").replace("http://", "").split("/")[0]

    if domain or name:
        logger.info("Step 3: Enriching with Apollo")
        apollo_result = _enrich_with_apollo_internal(
            business_name=name,
            website_domain=domain,
            find_contacts=True,
            max_contacts=5,
        )
        result["apollo_enrichment"] = apollo_result

        if apollo_result["success"]:
            organization_data = apollo_result.get("organization")
            decision_makers = apollo_result.get("decision_makers", [])
        else:
            result["errors"].append(f"Apollo enrichment failed: {apollo_result.get('error')}")

    # Step 4: Generate dossier
    logger.info("Step 4: Generating research dossier")
    dossier_result = _generate_research_dossier_internal(
        lead_data=result["lead_data"],
        website_content=website_content,
        organization_data=organization_data,
        decision_makers=decision_makers,
        social_profiles=social_profiles_dict,
    )

    result["dossier"] = dossier_result.get("dossier")
    result["dossier_status"] = dossier_result.get("status", "failed")

    if not dossier_result["success"]:
        result["errors"].append(f"Dossier generation failed: {dossier_result.get('error')}")

    # Determine overall success
    # Research is successful if we generated at least a partial dossier
    result["success"] = result["dossier_status"] in ("complete", "partial", "minimal")

    logger.info(
        "Research complete for %s: status=%s, errors=%d",
        name,
        result["dossier_status"],
        len(result["errors"]),
    )

    return json.dumps(result)


# Agent instructions defining behavior and constraints
RESEARCH_AGENT_INSTRUCTIONS = """You are a Research Agent specialized in deep business intelligence gathering.

Your primary task is to research business leads and generate comprehensive dossiers containing:
1. Company Overview - Basic information, description, metrics
2. Services - What the business offers
3. Team - Key personnel and decision makers
4. Pain Points - Business challenges we can solve
5. Gotcha Q&As - Questions to test voice agent knowledge
6. Competitor Landscape - Market positioning

## Your Research Process

When given a lead to research, follow these steps:

1. **Website Scraping** (if URL available)
   - Use `scrape_website_content` to get markdown content
   - This captures services, team, and company info

2. **Social Profile Extraction**
   - Use `extract_social_profiles` to find social media presence
   - Important for verifying legitimacy and engagement

3. **Apollo Enrichment**
   - Use `enrich_with_apollo` to get organization data
   - Find decision maker contacts (owners, executives, directors)
   - Get industry classification and employee count

4. **Dossier Generation**
   - Use `generate_research_dossier` to create the final dossier
   - Or use `research_lead_comprehensive` for end-to-end automation

## Edge Cases to Handle

- **No website found**: Skip Firecrawl, use Google Business data only, mark dossier as "partial"
- **API rate limits**: Note the error and continue with available data
- **Invalid data**: Log warnings but don't fail the entire research
- **Missing enrichment**: Use default pain points for the industry

## Output Format

Always provide a summary including:
- Research completion status (complete/partial/minimal)
- Data sources used (Google Maps, Firecrawl, Apollo)
- Key findings (decision makers, services, pain points)
- Any errors or missing data

## Important Notes

- Firecrawl handles JavaScript rendering automatically
- Apollo enrichment requires domain or business name
- Default pain points are added for known industries when specific data unavailable
- Always generate gotcha Q&As even with minimal data
"""

# Create the research agent instance
research_agent = Agent(
    name="Research Agent",
    instructions=RESEARCH_AGENT_INSTRUCTIONS,
    tools=[
        scrape_website_content,
        extract_social_profiles,
        enrich_with_apollo,
        generate_research_dossier,
        research_lead_comprehensive,
    ],
)
