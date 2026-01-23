"""Dossier template generator for structured markdown output with gotcha Q&As.

This module provides utilities for generating comprehensive research dossiers
for lead generation. The dossier format is optimized for:
1. LLM consumption (markdown format with clear section headers)
2. Voice agent training (gotcha Q&As to test business-specific knowledge)
3. Sales enablement (pain points, competitive landscape)

Required dossier sections per spec FR-3:
- Company Overview
- Services
- Team
- Pain Points
- Gotcha Q&As
- Competitor Landscape
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class DossierStatus(str, Enum):
    """Status of dossier generation."""
    COMPLETE = "complete"      # All sections populated
    PARTIAL = "partial"        # Some sections missing (e.g., no website)
    MINIMAL = "minimal"        # Only Google Business data available
    FAILED = "failed"          # Generation failed


@dataclass
class TeamMember:
    """Represents a team member or key contact.

    Attributes:
        name: Full name of the team member.
        title: Job title or role.
        email: Email address (if available).
        linkedin: LinkedIn profile URL (if available).
        bio: Brief biography or description.
    """
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[str] = None
    bio: Optional[str] = None


@dataclass
class Service:
    """Represents a service offered by the business.

    Attributes:
        name: Name of the service.
        description: Detailed description of the service.
        price_range: Price range or pricing info (if available).
        is_primary: Whether this is a primary/featured service.
    """
    name: str
    description: Optional[str] = None
    price_range: Optional[str] = None
    is_primary: bool = False


@dataclass
class PainPoint:
    """Represents a business pain point or challenge.

    Attributes:
        category: Category of pain point (e.g., "scheduling", "no-shows").
        description: Detailed description of the pain point.
        impact: Business impact (e.g., "Lost revenue", "Customer frustration").
        solution_hook: How our solution addresses this pain point.
    """
    category: str
    description: str
    impact: Optional[str] = None
    solution_hook: Optional[str] = None


@dataclass
class GotchaQA:
    """Represents a gotcha Q&A pair for voice agent testing.

    Gotcha questions are designed to test whether the voice agent truly
    understands the business and can answer accurately. These should be
    specific enough that a generic AI couldn't answer correctly without
    the dossier context.

    Attributes:
        question: The gotcha question to ask.
        answer: The expected correct answer.
        category: Category of question (e.g., "services", "hours", "pricing").
        difficulty: Difficulty level ("easy", "medium", "hard").
    """
    question: str
    answer: str
    category: str = "general"
    difficulty: str = "medium"


@dataclass
class Competitor:
    """Represents a competitor in the market.

    Attributes:
        name: Competitor business name.
        website: Competitor website URL.
        strengths: List of competitor strengths.
        weaknesses: List of competitor weaknesses.
        differentiator: What makes our prospect different/better.
    """
    name: str
    website: Optional[str] = None
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    differentiator: Optional[str] = None


@dataclass
class CompanyOverview:
    """Company overview information.

    Attributes:
        name: Business name.
        address: Full address.
        phone: Phone number.
        website: Website URL.
        industry: Industry/category.
        description: Business description.
        founding_year: Year founded (if known).
        employee_count: Approximate employee count.
        google_rating: Google Maps rating.
        review_count: Number of Google reviews.
        estimated_revenue: Estimated annual revenue.
        operating_hours: Business operating hours.
        social_profiles: Dictionary of social media profiles.
    """
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    founding_year: Optional[int] = None
    employee_count: Optional[str] = None
    google_rating: Optional[float] = None
    review_count: Optional[int] = None
    estimated_revenue: Optional[float] = None
    operating_hours: Optional[Dict[str, str]] = None
    social_profiles: Optional[Dict[str, str]] = None


@dataclass
class DossierData:
    """Complete dossier data structure.

    Attributes:
        company: Company overview information.
        services: List of services offered.
        team: List of team members.
        pain_points: Identified pain points.
        gotcha_qas: Q&A pairs for voice agent testing.
        competitors: Competitor analysis.
        status: Dossier completeness status.
        data_sources: List of data sources used.
        generated_at: Timestamp of generation.
        raw_website_content: Raw scraped website content (for reference).
        raw_reviews: Raw review data (for reference).
    """
    company: CompanyOverview
    services: List[Service] = field(default_factory=list)
    team: List[TeamMember] = field(default_factory=list)
    pain_points: List[PainPoint] = field(default_factory=list)
    gotcha_qas: List[GotchaQA] = field(default_factory=list)
    competitors: List[Competitor] = field(default_factory=list)
    status: DossierStatus = DossierStatus.MINIMAL
    data_sources: List[str] = field(default_factory=list)
    generated_at: Optional[datetime] = None
    raw_website_content: Optional[str] = None
    raw_reviews: Optional[List[Dict[str, Any]]] = None


# Default pain points by industry (used when specific data unavailable)
DEFAULT_PAIN_POINTS: Dict[str, List[PainPoint]] = {
    "dentist": [
        PainPoint(
            category="No-shows",
            description="Patients frequently miss appointments without calling to cancel",
            impact="Lost revenue and wasted chair time",
            solution_hook="AI receptionist sends automated reminders and handles rescheduling"
        ),
        PainPoint(
            category="After-hours inquiries",
            description="Potential patients call after office hours and don't leave messages",
            impact="Lost new patient opportunities",
            solution_hook="24/7 AI receptionist captures leads and schedules consultations"
        ),
        PainPoint(
            category="Staff overwhelm",
            description="Front desk staff juggling phones, check-ins, and insurance verification",
            impact="Long hold times and frustrated patients",
            solution_hook="AI handles routine calls so staff can focus on in-office patients"
        ),
    ],
    "hvac": [
        PainPoint(
            category="Emergency dispatch",
            description="After-hours emergency calls require expensive answering services",
            impact="High overhead costs or missed emergency revenue",
            solution_hook="AI receptionist triages emergencies and dispatches 24/7"
        ),
        PainPoint(
            category="Quote requests",
            description="Staff spends hours on phone giving basic quotes and estimates",
            impact="Reduced time for actual service work",
            solution_hook="AI provides instant estimates and schedules in-home assessments"
        ),
        PainPoint(
            category="Seasonal volume",
            description="Call volume spikes during extreme weather, overwhelming staff",
            impact="Lost business during peak revenue periods",
            solution_hook="AI scales instantly to handle any call volume"
        ),
    ],
    "salon": [
        PainPoint(
            category="Booking complexity",
            description="Stylists have different specialties and availability",
            impact="Double-bookings or poorly matched appointments",
            solution_hook="AI knows each stylist's skills and availability"
        ),
        PainPoint(
            category="Cancellations",
            description="Last-minute cancellations leave gaps in the schedule",
            impact="Lost revenue from empty chairs",
            solution_hook="AI automatically fills cancellations from waitlist"
        ),
        PainPoint(
            category="Product questions",
            description="Clients call asking about products, taking staff away from clients",
            impact="Interrupted services and frustrated stylists",
            solution_hook="AI answers product questions and takes orders"
        ),
    ],
    "default": [
        PainPoint(
            category="Missed calls",
            description="Calls go unanswered during busy periods or after hours",
            impact="Lost leads and revenue opportunities",
            solution_hook="AI receptionist answers every call 24/7"
        ),
        PainPoint(
            category="Staff productivity",
            description="Staff spends significant time on routine phone inquiries",
            impact="Less time for core business activities",
            solution_hook="AI handles routine calls so staff can focus on high-value work"
        ),
        PainPoint(
            category="Inconsistent experience",
            description="Call handling quality varies by who answers",
            impact="Inconsistent customer experience",
            solution_hook="AI provides consistent, professional responses every time"
        ),
    ],
}


def get_default_pain_points(industry: str) -> List[PainPoint]:
    """Get default pain points for an industry.

    Args:
        industry: Industry category string.

    Returns:
        List of default PainPoint objects for the industry.
    """
    industry_lower = industry.lower().strip() if industry else ""

    # Try direct match first
    if industry_lower in DEFAULT_PAIN_POINTS:
        return DEFAULT_PAIN_POINTS[industry_lower]

    # Try partial match
    for key in DEFAULT_PAIN_POINTS:
        if key in industry_lower or industry_lower in key:
            return DEFAULT_PAIN_POINTS[key]

    return DEFAULT_PAIN_POINTS["default"]


def generate_gotcha_qas_from_data(dossier_data: DossierData) -> List[GotchaQA]:
    """Generate gotcha Q&As based on available dossier data.

    Creates business-specific questions that a voice agent should be able
    to answer if it has properly ingested the dossier content.

    Args:
        dossier_data: The dossier data to generate Q&As from.

    Returns:
        List of GotchaQA objects.
    """
    qas = []
    company = dossier_data.company

    # Address-based question (easy)
    if company.address:
        qas.append(GotchaQA(
            question=f"What is the address of {company.name}?",
            answer=company.address,
            category="location",
            difficulty="easy"
        ))

    # Phone-based question (easy)
    if company.phone:
        qas.append(GotchaQA(
            question=f"What is the phone number for {company.name}?",
            answer=company.phone,
            category="contact",
            difficulty="easy"
        ))

    # Hours-based questions (medium)
    if company.operating_hours:
        # Get a specific day's hours
        for day, hours in company.operating_hours.items():
            qas.append(GotchaQA(
                question=f"What are your hours on {day}?",
                answer=hours,
                category="hours",
                difficulty="medium"
            ))
            break  # Just one hours question

    # Service-based questions (medium to hard)
    for service in dossier_data.services[:3]:  # Limit to first 3 services
        question = f"Do you offer {service.name.lower()}?"
        answer = f"Yes, we offer {service.name}"
        if service.description:
            answer += f". {service.description}"

        qas.append(GotchaQA(
            question=question,
            answer=answer,
            category="services",
            difficulty="medium"
        ))

        # Price question if available
        if service.price_range:
            qas.append(GotchaQA(
                question=f"How much does {service.name.lower()} cost?",
                answer=f"Our {service.name.lower()} typically costs {service.price_range}",
                category="pricing",
                difficulty="hard"
            ))

    # Team-based questions (hard)
    for member in dossier_data.team[:2]:  # Limit to first 2 team members
        if member.title:
            qas.append(GotchaQA(
                question=f"Who is the {member.title.lower()} at {company.name}?",
                answer=f"{member.name} is our {member.title}",
                category="team",
                difficulty="hard"
            ))

    # Industry-specific gotcha questions
    industry = (company.industry or "").lower()

    if "dent" in industry:
        qas.append(GotchaQA(
            question="Do you accept dental insurance?",
            answer="Yes, we accept most major dental insurance plans. Please call or visit our website for specific plan coverage.",
            category="insurance",
            difficulty="medium"
        ))
        qas.append(GotchaQA(
            question="Do you offer emergency dental services?",
            answer="Yes, we accommodate dental emergencies. Please call us immediately if you have a dental emergency.",
            category="services",
            difficulty="medium"
        ))

    if "hvac" in industry:
        qas.append(GotchaQA(
            question="Do you offer 24-hour emergency service?",
            answer="Yes, we provide 24/7 emergency HVAC service for heating and cooling emergencies.",
            category="services",
            difficulty="medium"
        ))
        qas.append(GotchaQA(
            question="Do you service all HVAC brands?",
            answer="Yes, our technicians are trained to service all major HVAC brands and systems.",
            category="services",
            difficulty="medium"
        ))

    if "salon" in industry or "hair" in industry:
        qas.append(GotchaQA(
            question="Do I need to make an appointment or do you take walk-ins?",
            answer="We recommend making an appointment to ensure your preferred stylist is available, but we do accept walk-ins when possible.",
            category="booking",
            difficulty="medium"
        ))

    return qas


def _format_services_section(services: List[Service]) -> str:
    """Format services list as markdown.

    Args:
        services: List of Service objects.

    Returns:
        Markdown-formatted services section.
    """
    if not services:
        return "_No services information available._\n"

    lines = []

    # Primary services first
    primary = [s for s in services if s.is_primary]
    other = [s for s in services if not s.is_primary]

    if primary:
        lines.append("### Primary Services\n")
        for service in primary:
            lines.append(f"- **{service.name}**")
            if service.description:
                lines.append(f"  - {service.description}")
            if service.price_range:
                lines.append(f"  - Price: {service.price_range}")
        lines.append("")

    if other:
        lines.append("### Additional Services\n")
        for service in other:
            line = f"- {service.name}"
            if service.description:
                line += f": {service.description}"
            lines.append(line)
        lines.append("")

    return "\n".join(lines)


def _format_team_section(team: List[TeamMember]) -> str:
    """Format team list as markdown.

    Args:
        team: List of TeamMember objects.

    Returns:
        Markdown-formatted team section.
    """
    if not team:
        return "_No team information available._\n"

    lines = []
    for member in team:
        title = f" - {member.title}" if member.title else ""
        lines.append(f"- **{member.name}**{title}")
        if member.bio:
            lines.append(f"  - {member.bio}")
        if member.email:
            lines.append(f"  - Email: {member.email}")
        if member.linkedin:
            lines.append(f"  - LinkedIn: {member.linkedin}")

    return "\n".join(lines) + "\n"


def _format_pain_points_section(pain_points: List[PainPoint]) -> str:
    """Format pain points as markdown.

    Args:
        pain_points: List of PainPoint objects.

    Returns:
        Markdown-formatted pain points section.
    """
    if not pain_points:
        return "_No pain points identified._\n"

    lines = []
    for i, pain in enumerate(pain_points, 1):
        lines.append(f"### {i}. {pain.category}\n")
        lines.append(f"**Challenge:** {pain.description}\n")
        if pain.impact:
            lines.append(f"**Business Impact:** {pain.impact}\n")
        if pain.solution_hook:
            lines.append(f"**How We Help:** {pain.solution_hook}\n")
        lines.append("")

    return "\n".join(lines)


def _format_gotcha_qas_section(qas: List[GotchaQA]) -> str:
    """Format gotcha Q&As as markdown.

    Args:
        qas: List of GotchaQA objects.

    Returns:
        Markdown-formatted Q&A section.
    """
    if not qas:
        return "_No Q&As generated._\n"

    lines = []

    # Group by difficulty
    easy = [q for q in qas if q.difficulty == "easy"]
    medium = [q for q in qas if q.difficulty == "medium"]
    hard = [q for q in qas if q.difficulty == "hard"]

    if easy:
        lines.append("### Easy Questions\n")
        for qa in easy:
            lines.append(f"**Q:** {qa.question}")
            lines.append(f"**A:** {qa.answer}")
            lines.append(f"_Category: {qa.category}_\n")

    if medium:
        lines.append("### Medium Questions\n")
        for qa in medium:
            lines.append(f"**Q:** {qa.question}")
            lines.append(f"**A:** {qa.answer}")
            lines.append(f"_Category: {qa.category}_\n")

    if hard:
        lines.append("### Hard Questions\n")
        for qa in hard:
            lines.append(f"**Q:** {qa.question}")
            lines.append(f"**A:** {qa.answer}")
            lines.append(f"_Category: {qa.category}_\n")

    return "\n".join(lines)


def _format_competitors_section(competitors: List[Competitor]) -> str:
    """Format competitor analysis as markdown.

    Args:
        competitors: List of Competitor objects.

    Returns:
        Markdown-formatted competitors section.
    """
    if not competitors:
        return "_No competitor data available._\n"

    lines = []
    for comp in competitors:
        lines.append(f"### {comp.name}\n")
        if comp.website:
            lines.append(f"**Website:** {comp.website}\n")
        if comp.strengths:
            lines.append("**Strengths:**")
            for s in comp.strengths:
                lines.append(f"- {s}")
            lines.append("")
        if comp.weaknesses:
            lines.append("**Weaknesses:**")
            for w in comp.weaknesses:
                lines.append(f"- {w}")
            lines.append("")
        if comp.differentiator:
            lines.append(f"**Our Differentiator:** {comp.differentiator}\n")
        lines.append("")

    return "\n".join(lines)


def _format_operating_hours(hours: Optional[Dict[str, str]]) -> str:
    """Format operating hours as a readable string.

    Args:
        hours: Dictionary mapping day names to hours.

    Returns:
        Formatted hours string.
    """
    if not hours:
        return "Not available"

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    lines = []

    for day in days_order:
        if day in hours:
            lines.append(f"  - {day}: {hours[day]}")

    # Handle any non-standard day keys
    for day, time in hours.items():
        if day not in days_order:
            lines.append(f"  - {day}: {time}")

    return "\n".join(lines) if lines else "Not available"


def generate_dossier(
    dossier_data: DossierData,
    include_raw_content: bool = False
) -> str:
    """Generate a complete markdown dossier from structured data.

    Creates a comprehensive research dossier optimized for:
    - LLM consumption (clear markdown structure)
    - Voice agent training (gotcha Q&As)
    - Sales enablement (pain points, competitive landscape)

    Args:
        dossier_data: Structured dossier data.
        include_raw_content: Whether to include raw website content at the end.

    Returns:
        Complete markdown-formatted dossier string.

    Example:
        >>> company = CompanyOverview(name="Acme Dental", industry="dentist")
        >>> data = DossierData(company=company)
        >>> dossier = generate_dossier(data)
        >>> print(dossier[:50])
        # Research Dossier: Acme Dental
    """
    company = dossier_data.company

    # Build the dossier markdown
    sections = []

    # Header
    sections.append(f"# Research Dossier: {company.name}\n")
    sections.append(f"_Generated: {dossier_data.generated_at or datetime.utcnow().isoformat()}_")
    sections.append(f"_Status: {dossier_data.status.value}_")
    if dossier_data.data_sources:
        sections.append(f"_Data Sources: {', '.join(dossier_data.data_sources)}_")
    sections.append("\n---\n")

    # Company Overview Section
    sections.append("## Company Overview\n")
    sections.append(f"**Business Name:** {company.name}")
    if company.industry:
        sections.append(f"**Industry:** {company.industry}")
    if company.description:
        sections.append(f"\n{company.description}\n")

    sections.append("\n### Contact Information\n")
    if company.address:
        sections.append(f"- **Address:** {company.address}")
    if company.phone:
        sections.append(f"- **Phone:** {company.phone}")
    if company.website:
        sections.append(f"- **Website:** {company.website}")

    if company.social_profiles:
        sections.append("\n### Social Media\n")
        for platform, url in company.social_profiles.items():
            sections.append(f"- **{platform.title()}:** {url}")

    sections.append("\n### Business Metrics\n")
    if company.google_rating is not None:
        sections.append(f"- **Google Rating:** {company.google_rating}/5.0")
    if company.review_count is not None:
        sections.append(f"- **Review Count:** {company.review_count}")
    if company.estimated_revenue is not None:
        sections.append(f"- **Estimated Revenue:** ${company.estimated_revenue:,.0f}/year")
    if company.employee_count:
        sections.append(f"- **Employees:** {company.employee_count}")
    if company.founding_year:
        sections.append(f"- **Founded:** {company.founding_year}")

    sections.append("\n### Operating Hours\n")
    sections.append(_format_operating_hours(company.operating_hours))

    sections.append("\n---\n")

    # Services Section
    sections.append("## Services\n")
    sections.append(_format_services_section(dossier_data.services))
    sections.append("\n---\n")

    # Team Section
    sections.append("## Team\n")
    sections.append(_format_team_section(dossier_data.team))
    sections.append("\n---\n")

    # Pain Points Section
    sections.append("## Pain Points & Opportunities\n")
    sections.append("_Identified challenges that our AI receptionist solution can address._\n")
    sections.append(_format_pain_points_section(dossier_data.pain_points))
    sections.append("\n---\n")

    # Gotcha Q&As Section
    sections.append("## Gotcha Q&As\n")
    sections.append("_Questions to test voice agent knowledge of this specific business._\n")
    sections.append(_format_gotcha_qas_section(dossier_data.gotcha_qas))
    sections.append("\n---\n")

    # Competitor Landscape Section
    sections.append("## Competitor Landscape\n")
    sections.append(_format_competitors_section(dossier_data.competitors))

    # Raw content (optional, for reference)
    if include_raw_content and dossier_data.raw_website_content:
        sections.append("\n---\n")
        sections.append("## Raw Website Content\n")
        sections.append("_Original scraped content for reference._\n")
        sections.append("```")
        sections.append(dossier_data.raw_website_content[:5000])  # Limit to 5000 chars
        if len(dossier_data.raw_website_content) > 5000:
            sections.append("\n... (truncated)")
        sections.append("```")

    return "\n".join(sections)


def generate_dossier_from_dict(
    data: Dict[str, Any],
    include_defaults: bool = True
) -> str:
    """Generate a dossier from a flat dictionary of business data.

    Convenience function that builds DossierData from a simple dictionary
    format, commonly used when data comes from various API sources.

    Args:
        data: Dictionary with business data. Expected keys:
            - name (str): Business name (required)
            - address (str): Business address
            - phone (str): Phone number
            - website (str): Website URL
            - industry (str): Industry category
            - description (str): Business description
            - google_rating (float): Google Maps rating
            - review_count (int): Number of reviews
            - estimated_revenue (float): Estimated annual revenue
            - operating_hours (dict): Day -> hours mapping
            - social_profiles (dict): Platform -> URL mapping
            - services (list): List of service dicts
            - team (list): List of team member dicts
            - pain_points (list): List of pain point dicts
            - competitors (list): List of competitor dicts
        include_defaults: Whether to include default pain points when none provided.

    Returns:
        Complete markdown-formatted dossier string.

    Example:
        >>> data = {"name": "Acme Dental", "industry": "dentist", "phone": "555-1234"}
        >>> dossier = generate_dossier_from_dict(data)
    """
    # Build CompanyOverview
    company = CompanyOverview(
        name=data.get("name", "Unknown Business"),
        address=data.get("address"),
        phone=data.get("phone"),
        website=data.get("website"),
        industry=data.get("industry"),
        description=data.get("description"),
        founding_year=data.get("founding_year"),
        employee_count=data.get("employee_count"),
        google_rating=data.get("google_rating"),
        review_count=data.get("review_count"),
        estimated_revenue=data.get("estimated_revenue"),
        operating_hours=data.get("operating_hours"),
        social_profiles=data.get("social_profiles"),
    )

    # Build services list
    services = []
    for svc_data in data.get("services", []):
        if isinstance(svc_data, dict):
            services.append(Service(
                name=svc_data.get("name", "Unknown Service"),
                description=svc_data.get("description"),
                price_range=svc_data.get("price_range"),
                is_primary=svc_data.get("is_primary", False),
            ))
        elif isinstance(svc_data, str):
            services.append(Service(name=svc_data))

    # Build team list
    team = []
    for member_data in data.get("team", []):
        if isinstance(member_data, dict):
            team.append(TeamMember(
                name=member_data.get("name", "Unknown"),
                title=member_data.get("title"),
                email=member_data.get("email"),
                linkedin=member_data.get("linkedin"),
                bio=member_data.get("bio"),
            ))
        elif isinstance(member_data, str):
            team.append(TeamMember(name=member_data))

    # Build pain points list
    pain_points = []
    for pain_data in data.get("pain_points", []):
        if isinstance(pain_data, dict):
            pain_points.append(PainPoint(
                category=pain_data.get("category", "General"),
                description=pain_data.get("description", ""),
                impact=pain_data.get("impact"),
                solution_hook=pain_data.get("solution_hook"),
            ))

    # Add default pain points if none provided and defaults enabled
    if not pain_points and include_defaults:
        pain_points = get_default_pain_points(company.industry or "")

    # Build competitors list
    competitors = []
    for comp_data in data.get("competitors", []):
        if isinstance(comp_data, dict):
            competitors.append(Competitor(
                name=comp_data.get("name", "Unknown Competitor"),
                website=comp_data.get("website"),
                strengths=comp_data.get("strengths", []),
                weaknesses=comp_data.get("weaknesses", []),
                differentiator=comp_data.get("differentiator"),
            ))
        elif isinstance(comp_data, str):
            competitors.append(Competitor(name=comp_data))

    # Determine status based on data completeness
    if data.get("website") and data.get("description"):
        status = DossierStatus.COMPLETE
    elif data.get("website") or data.get("description"):
        status = DossierStatus.PARTIAL
    else:
        status = DossierStatus.MINIMAL

    # Determine data sources
    data_sources = []
    if data.get("google_place_id") or data.get("google_rating"):
        data_sources.append("Google Maps")
    if data.get("website"):
        data_sources.append("Website (Firecrawl)")
    if data.get("apollo_enriched"):
        data_sources.append("Apollo.io")
    if not data_sources:
        data_sources.append("Manual Entry")

    # Create DossierData
    dossier_data = DossierData(
        company=company,
        services=services,
        team=team,
        pain_points=pain_points,
        gotcha_qas=[],  # Will be generated below
        competitors=competitors,
        status=status,
        data_sources=data_sources,
        generated_at=datetime.utcnow(),
        raw_website_content=data.get("raw_website_content"),
        raw_reviews=data.get("raw_reviews"),
    )

    # Generate gotcha Q&As from the data
    dossier_data.gotcha_qas = generate_gotcha_qas_from_data(dossier_data)

    # Add any custom Q&As from input
    for qa_data in data.get("gotcha_qas", []):
        if isinstance(qa_data, dict):
            dossier_data.gotcha_qas.append(GotchaQA(
                question=qa_data.get("question", ""),
                answer=qa_data.get("answer", ""),
                category=qa_data.get("category", "custom"),
                difficulty=qa_data.get("difficulty", "medium"),
            ))

    return generate_dossier(dossier_data)


def validate_dossier_sections(dossier_markdown: str) -> Dict[str, bool]:
    """Validate that a dossier contains all required sections.

    Checks for presence of all required sections per spec FR-3:
    - Company Overview
    - Services
    - Team
    - Pain Points
    - Gotcha Q&As
    - Competitor Landscape

    Args:
        dossier_markdown: The markdown dossier string to validate.

    Returns:
        Dictionary mapping section names to presence (True/False).
    """
    required_sections = [
        "Company Overview",
        "Services",
        "Team",
        "Pain Points",
        "Gotcha Q&A",
        "Competitor",
    ]

    results = {}
    for section in required_sections:
        results[section] = section.lower() in dossier_markdown.lower()

    return results


def is_dossier_valid(dossier_markdown: str) -> bool:
    """Check if a dossier contains all required sections.

    Args:
        dossier_markdown: The markdown dossier string to validate.

    Returns:
        True if all required sections are present.
    """
    validation = validate_dossier_sections(dossier_markdown)
    return all(validation.values())
