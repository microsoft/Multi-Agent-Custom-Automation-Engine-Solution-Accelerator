"""Apollo/ZoomInfo enrichment client for contact intelligence.

This module provides a client for enriching business and contact data
using Apollo.io API for B2B lead intelligence.
"""

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT_SECONDS = 30
APOLLO_BASE_URL = "https://api.apollo.io/v1"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0


class ApolloError(Exception):
    """Base exception for Apollo client errors."""

    pass


class ApolloRateLimitError(ApolloError):
    """Raised when API rate limit is exceeded."""

    pass


class ApolloAuthError(ApolloError):
    """Raised when API authentication fails."""

    pass


class ApolloNotFoundError(ApolloError):
    """Raised when requested resource is not found."""

    pass


class ApolloEnrichmentError(ApolloError):
    """Raised when enrichment request fails."""

    pass


@dataclass
class PersonEnrichment:
    """Represents enriched person/contact data.

    Attributes:
        email: Email address.
        first_name: First name.
        last_name: Last name.
        full_name: Full name.
        title: Job title.
        linkedin_url: LinkedIn profile URL.
        phone_numbers: List of phone numbers.
        organization: Organization/company name.
        organization_domain: Company domain.
        seniority: Seniority level (e.g., executive, director, manager).
        departments: List of departments.
        city: City location.
        state: State/region.
        country: Country.
        success: Whether enrichment was successful.
        error: Error message if enrichment failed.
    """

    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone_numbers: list[str] = field(default_factory=list)
    organization: Optional[str] = None
    organization_domain: Optional[str] = None
    seniority: Optional[str] = None
    departments: list[str] = field(default_factory=list)
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "title": self.title,
            "linkedin_url": self.linkedin_url,
            "phone_numbers": self.phone_numbers,
            "organization": self.organization,
            "organization_domain": self.organization_domain,
            "seniority": self.seniority,
            "departments": self.departments,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "success": self.success,
            "error": self.error,
        }

    @property
    def has_contact_info(self) -> bool:
        """Check if any contact information was found."""
        return bool(self.email or self.phone_numbers or self.linkedin_url)

    @property
    def is_decision_maker(self) -> bool:
        """Check if person is likely a decision maker based on seniority."""
        if not self.seniority:
            return False
        decision_maker_levels = {"owner", "founder", "c_suite", "vp", "director"}
        return self.seniority.lower() in decision_maker_levels


@dataclass
class OrganizationEnrichment:
    """Represents enriched organization/company data.

    Attributes:
        name: Company name.
        domain: Company domain.
        phone: Main phone number.
        linkedin_url: Company LinkedIn URL.
        website_url: Company website.
        industry: Industry classification.
        industry_tag_id: Apollo industry tag ID.
        keywords: Business keywords.
        estimated_num_employees: Estimated employee count.
        employee_range: Employee count range (e.g., "11-50").
        founded_year: Year company was founded.
        city: Headquarters city.
        state: Headquarters state.
        country: Headquarters country.
        short_description: Brief company description.
        technologies: List of technologies used.
        annual_revenue: Estimated annual revenue.
        total_funding: Total funding raised.
        latest_funding_round: Latest funding round type.
        success: Whether enrichment was successful.
        error: Error message if enrichment failed.
    """

    name: Optional[str] = None
    domain: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    industry_tag_id: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    estimated_num_employees: Optional[int] = None
    employee_range: Optional[str] = None
    founded_year: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    short_description: Optional[str] = None
    technologies: list[str] = field(default_factory=list)
    annual_revenue: Optional[float] = None
    total_funding: Optional[float] = None
    latest_funding_round: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "domain": self.domain,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "website_url": self.website_url,
            "industry": self.industry,
            "industry_tag_id": self.industry_tag_id,
            "keywords": self.keywords,
            "estimated_num_employees": self.estimated_num_employees,
            "employee_range": self.employee_range,
            "founded_year": self.founded_year,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "short_description": self.short_description,
            "technologies": self.technologies,
            "annual_revenue": self.annual_revenue,
            "total_funding": self.total_funding,
            "latest_funding_round": self.latest_funding_round,
            "success": self.success,
            "error": self.error,
        }

    @property
    def is_target_size(self) -> bool:
        """Check if company is in target revenue range ($100K-$1M)."""
        if self.annual_revenue is None:
            return True  # Assume target if unknown
        return 100_000 <= self.annual_revenue <= 1_000_000


@dataclass
class ContactSearchResult:
    """Represents results from a contact search.

    Attributes:
        contacts: List of enriched person results.
        total_results: Total number of matching results.
        page: Current page number.
        per_page: Results per page.
    """

    contacts: list[PersonEnrichment]
    total_results: int
    page: int
    per_page: int

    def get_decision_makers(self) -> list[PersonEnrichment]:
        """Filter contacts to only decision makers."""
        return [c for c in self.contacts if c.is_decision_maker]


class ApolloClient:
    """Client for Apollo.io API with async support.

    Provides methods for enriching business and contact data for
    B2B lead generation and sales intelligence.

    Attributes:
        api_key: Apollo.io API key.
        timeout_seconds: Request timeout in seconds.

    Example:
        >>> client = ApolloClient()
        >>> org = await client.enrich_organization(domain="acmedental.com")
        >>> print(org.name, org.estimated_num_employees)
        Acme Dental 25
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize Apollo client.

        Args:
            api_key: Apollo.io API key. Defaults to APOLLO_API_KEY env var.
            timeout_seconds: Request timeout in seconds. Defaults to 30.

        Raises:
            ValueError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.environ.get("APOLLO_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Apollo API key required. Set APOLLO_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self.timeout_seconds = timeout_seconds
        logger.info("ApolloClient initialized with %ds timeout", timeout_seconds)

    def _make_request_sync(
        self,
        endpoint: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Make a synchronous API request.

        Args:
            endpoint: API endpoint path.
            data: Request body data.

        Returns:
            Parsed JSON response.

        Raises:
            ApolloAuthError: If authentication fails.
            ApolloRateLimitError: If rate limit is exceeded.
            ApolloEnrichmentError: If request fails.
        """
        url = f"{APOLLO_BASE_URL}{endpoint}"

        # Add API key to request body (Apollo's preferred method)
        data["api_key"] = self.api_key

        request_data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise ApolloAuthError("Invalid API key or unauthorized access") from e
            elif e.code == 404:
                raise ApolloNotFoundError(f"Resource not found: {endpoint}") from e
            elif e.code == 429:
                raise ApolloRateLimitError("API rate limit exceeded") from e
            else:
                error_body = e.read().decode("utf-8") if e.fp else str(e)
                raise ApolloEnrichmentError(f"API error {e.code}: {error_body}") from e
        except urllib.error.URLError as e:
            raise ApolloEnrichmentError(f"Request failed: {e.reason}") from e

    async def _make_request(
        self,
        endpoint: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Make an async API request with retry logic.

        Args:
            endpoint: API endpoint path.
            data: Request body data.

        Returns:
            Parsed JSON response.

        Raises:
            ApolloAuthError: If authentication fails.
            ApolloRateLimitError: If rate limit is exceeded.
            ApolloEnrichmentError: If request fails after retries.
        """
        loop = asyncio.get_event_loop()
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda d=data.copy(): self._make_request_sync(endpoint, d),
                )
                return result
            except ApolloRateLimitError:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_SECONDS * (2**attempt)
                    logger.warning(
                        "Rate limited, retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise
            except (ApolloAuthError, ApolloNotFoundError):
                raise
            except ApolloEnrichmentError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue
                raise
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue

        raise ApolloEnrichmentError(f"Request failed after {MAX_RETRIES} attempts: {last_error}")

    def _parse_person(self, person_data: dict[str, Any]) -> PersonEnrichment:
        """Parse raw API response into PersonEnrichment.

        Args:
            person_data: Raw person data from API response.

        Returns:
            Parsed PersonEnrichment object.
        """
        # Extract phone numbers
        phone_numbers = []
        if person_data.get("phone_numbers"):
            for phone in person_data["phone_numbers"]:
                if isinstance(phone, dict):
                    phone_numbers.append(phone.get("sanitized_number", phone.get("raw_number", "")))
                else:
                    phone_numbers.append(str(phone))
        elif person_data.get("phone"):
            phone_numbers.append(person_data["phone"])

        # Extract organization info
        org = person_data.get("organization", {}) or {}

        # Extract organization domain safely
        org_domain = None
        if org.get("primary_domain"):
            org_domain = org["primary_domain"]
        elif org.get("website_url"):
            website = org["website_url"]
            org_domain = website.replace("https://", "").replace("http://", "").split("/")[0]

        return PersonEnrichment(
            email=person_data.get("email"),
            first_name=person_data.get("first_name"),
            last_name=person_data.get("last_name"),
            full_name=person_data.get("name"),
            title=person_data.get("title"),
            linkedin_url=person_data.get("linkedin_url"),
            phone_numbers=phone_numbers,
            organization=org.get("name") or person_data.get("organization_name"),
            organization_domain=org_domain,
            seniority=person_data.get("seniority"),
            departments=person_data.get("departments", []),
            city=person_data.get("city"),
            state=person_data.get("state"),
            country=person_data.get("country"),
            success=True,
            error=None,
        )

    def _parse_organization(self, org_data: dict[str, Any]) -> OrganizationEnrichment:
        """Parse raw API response into OrganizationEnrichment.

        Args:
            org_data: Raw organization data from API response.

        Returns:
            Parsed OrganizationEnrichment object.
        """
        # Parse annual revenue
        annual_revenue = None
        if org_data.get("annual_revenue"):
            try:
                annual_revenue = float(org_data["annual_revenue"])
            except (ValueError, TypeError):
                pass

        # Parse total funding
        total_funding = None
        if org_data.get("total_funding"):
            try:
                total_funding = float(org_data["total_funding"])
            except (ValueError, TypeError):
                pass

        return OrganizationEnrichment(
            name=org_data.get("name"),
            domain=org_data.get("primary_domain") or org_data.get("domain"),
            phone=org_data.get("phone"),
            linkedin_url=org_data.get("linkedin_url"),
            website_url=org_data.get("website_url"),
            industry=org_data.get("industry"),
            industry_tag_id=org_data.get("industry_tag_id"),
            keywords=org_data.get("keywords", []) or [],
            estimated_num_employees=org_data.get("estimated_num_employees"),
            employee_range=org_data.get("employee_range"),
            founded_year=org_data.get("founded_year"),
            city=org_data.get("city"),
            state=org_data.get("state"),
            country=org_data.get("country"),
            short_description=org_data.get("short_description"),
            technologies=org_data.get("technologies", []) or [],
            annual_revenue=annual_revenue,
            total_funding=total_funding,
            latest_funding_round=org_data.get("latest_funding_round_type"),
            success=True,
            error=None,
        )

    async def enrich_person(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> PersonEnrichment:
        """Enrich a person/contact with additional data.

        Provide either an email or a combination of name and organization/domain
        to find and enrich contact data.

        Args:
            email: Person's email address.
            first_name: Person's first name.
            last_name: Person's last name.
            organization_name: Company name.
            domain: Company domain.

        Returns:
            PersonEnrichment with contact intelligence.

        Raises:
            ValueError: If insufficient identifying information provided.
            ApolloEnrichmentError: If enrichment fails.
        """
        if not email and not (first_name and last_name and (organization_name or domain)):
            raise ValueError(
                "Provide either email, or first_name + last_name + organization/domain"
            )

        logger.info(
            "Enriching person: email=%s, name=%s %s, org=%s",
            email,
            first_name,
            last_name,
            organization_name or domain,
        )

        data: dict[str, Any] = {}
        if email:
            data["email"] = email
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if organization_name:
            data["organization_name"] = organization_name
        if domain:
            data["domain"] = domain

        try:
            response = await self._make_request("/people/match", data=data)

            person_data = response.get("person", {})
            if not person_data:
                logger.warning("No person data found in enrichment response")
                return PersonEnrichment(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    success=False,
                    error="No matching person found",
                )

            result = self._parse_person(person_data)
            logger.info(
                "Successfully enriched person: %s (%s at %s)",
                result.full_name,
                result.title,
                result.organization,
            )
            return result

        except ApolloNotFoundError:
            return PersonEnrichment(
                email=email,
                first_name=first_name,
                last_name=last_name,
                success=False,
                error="Person not found",
            )
        except ApolloError:
            raise
        except Exception as e:
            logger.error("Failed to enrich person: %s", e)
            raise ApolloEnrichmentError(f"Person enrichment failed: {e}") from e

    async def enrich_person_safe(
        self,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        organization_name: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> PersonEnrichment:
        """Enrich a person with error handling (returns result instead of raising).

        This method catches errors and returns a PersonEnrichment with success=False
        and the error message, rather than raising exceptions.

        Args:
            email: Person's email address.
            first_name: Person's first name.
            last_name: Person's last name.
            organization_name: Company name.
            domain: Company domain.

        Returns:
            PersonEnrichment (with success=False if enrichment failed).
        """
        try:
            return await self.enrich_person(
                email=email,
                first_name=first_name,
                last_name=last_name,
                organization_name=organization_name,
                domain=domain,
            )
        except ApolloError as e:
            logger.warning("Safe person enrichment failed: %s", e)
            return PersonEnrichment(
                email=email,
                first_name=first_name,
                last_name=last_name,
                success=False,
                error=str(e),
            )
        except Exception as e:
            logger.error("Unexpected error in person enrichment: %s", e)
            return PersonEnrichment(
                email=email,
                first_name=first_name,
                last_name=last_name,
                success=False,
                error=f"Unexpected error: {e}",
            )

    async def enrich_organization(
        self,
        domain: Optional[str] = None,
        name: Optional[str] = None,
    ) -> OrganizationEnrichment:
        """Enrich an organization/company with additional data.

        Provide either a domain or company name to find and enrich organization data.

        Args:
            domain: Company website domain (e.g., "acmedental.com").
            name: Company name.

        Returns:
            OrganizationEnrichment with company intelligence.

        Raises:
            ValueError: If neither domain nor name provided.
            ApolloEnrichmentError: If enrichment fails.
        """
        if not domain and not name:
            raise ValueError("Provide either domain or name")

        logger.info("Enriching organization: domain=%s, name=%s", domain, name)

        data: dict[str, Any] = {}
        if domain:
            data["domain"] = domain
        if name:
            data["name"] = name

        try:
            response = await self._make_request("/organizations/enrich", data=data)

            org_data = response.get("organization", {})
            if not org_data:
                logger.warning("No organization data found in enrichment response")
                return OrganizationEnrichment(
                    domain=domain,
                    name=name,
                    success=False,
                    error="No matching organization found",
                )

            result = self._parse_organization(org_data)
            logger.info(
                "Successfully enriched organization: %s (%s, %d employees)",
                result.name,
                result.industry,
                result.estimated_num_employees or 0,
            )
            return result

        except ApolloNotFoundError:
            return OrganizationEnrichment(
                domain=domain,
                name=name,
                success=False,
                error="Organization not found",
            )
        except ApolloError:
            raise
        except Exception as e:
            logger.error("Failed to enrich organization: %s", e)
            raise ApolloEnrichmentError(f"Organization enrichment failed: {e}") from e

    async def enrich_organization_safe(
        self,
        domain: Optional[str] = None,
        name: Optional[str] = None,
    ) -> OrganizationEnrichment:
        """Enrich an organization with error handling (returns result instead of raising).

        This method catches errors and returns an OrganizationEnrichment with success=False
        and the error message, rather than raising exceptions.

        Args:
            domain: Company website domain.
            name: Company name.

        Returns:
            OrganizationEnrichment (with success=False if enrichment failed).
        """
        try:
            return await self.enrich_organization(domain=domain, name=name)
        except ApolloError as e:
            logger.warning("Safe organization enrichment failed: %s", e)
            return OrganizationEnrichment(
                domain=domain,
                name=name,
                success=False,
                error=str(e),
            )
        except Exception as e:
            logger.error("Unexpected error in organization enrichment: %s", e)
            return OrganizationEnrichment(
                domain=domain,
                name=name,
                success=False,
                error=f"Unexpected error: {e}",
            )

    async def search_contacts(
        self,
        organization_domain: Optional[str] = None,
        organization_name: Optional[str] = None,
        titles: Optional[list[str]] = None,
        seniorities: Optional[list[str]] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> ContactSearchResult:
        """Search for contacts at an organization.

        Find contacts at a company matching title and seniority filters.

        Args:
            organization_domain: Company domain to search.
            organization_name: Company name to search.
            titles: List of job titles to filter by.
            seniorities: List of seniority levels (owner, c_suite, vp, director, manager).
            page: Page number (1-indexed).
            per_page: Results per page (max 100).

        Returns:
            ContactSearchResult with matching contacts.

        Raises:
            ValueError: If neither domain nor name provided.
            ApolloEnrichmentError: If search fails.
        """
        if not organization_domain and not organization_name:
            raise ValueError("Provide either organization_domain or organization_name")

        logger.info(
            "Searching contacts: domain=%s, name=%s, titles=%s, seniorities=%s",
            organization_domain,
            organization_name,
            titles,
            seniorities,
        )

        data: dict[str, Any] = {
            "page": page,
            "per_page": min(per_page, 100),
        }

        if organization_domain:
            data["q_organization_domains"] = organization_domain
        if organization_name:
            data["q_organization_name"] = organization_name
        if titles:
            data["person_titles"] = titles
        if seniorities:
            data["person_seniorities"] = seniorities

        try:
            response = await self._make_request("/mixed_people/search", data=data)

            people_data = response.get("people", [])
            pagination = response.get("pagination", {})

            contacts = [self._parse_person(p) for p in people_data]

            result = ContactSearchResult(
                contacts=contacts,
                total_results=pagination.get("total_entries", len(contacts)),
                page=pagination.get("page", page),
                per_page=pagination.get("per_page", per_page),
            )

            logger.info(
                "Contact search complete: found %d contacts (page %d of %d)",
                len(contacts),
                result.page,
                (result.total_results + per_page - 1) // per_page,
            )
            return result

        except ApolloError:
            raise
        except Exception as e:
            logger.error("Failed to search contacts: %s", e)
            raise ApolloEnrichmentError(f"Contact search failed: {e}") from e

    async def find_decision_makers(
        self,
        organization_domain: Optional[str] = None,
        organization_name: Optional[str] = None,
        max_results: int = 10,
    ) -> list[PersonEnrichment]:
        """Find decision makers at an organization.

        Convenience method to find owners, executives, VPs, and directors
        at a company.

        Args:
            organization_domain: Company domain to search.
            organization_name: Company name to search.
            max_results: Maximum number of decision makers to return.

        Returns:
            List of PersonEnrichment for decision makers.
        """
        decision_maker_seniorities = ["owner", "founder", "c_suite", "vp", "director"]

        result = await self.search_contacts(
            organization_domain=organization_domain,
            organization_name=organization_name,
            seniorities=decision_maker_seniorities,
            per_page=min(max_results, 100),
        )

        return result.contacts[:max_results]

    async def enrich_lead(
        self,
        name: str,
        domain: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> dict[str, Any]:
        """Enrich a lead with both organization and contact data.

        Comprehensive enrichment that combines organization data with
        decision maker contacts for a business lead.

        Args:
            name: Business name.
            domain: Business website domain.
            phone: Business phone number.

        Returns:
            Dictionary with organization and contacts data.
        """
        logger.info("Enriching lead: name=%s, domain=%s", name, domain)

        result: dict[str, Any] = {
            "name": name,
            "domain": domain,
            "phone": phone,
            "organization": None,
            "decision_makers": [],
            "success": False,
        }

        # Enrich organization
        if domain or name:
            org = await self.enrich_organization_safe(domain=domain, name=name)
            if org.success:
                result["organization"] = org.to_dict()
                result["success"] = True

        # Find decision makers if we have domain info
        search_domain = domain
        if not search_domain and result.get("organization") and result["organization"].get("domain"):
            search_domain = result["organization"]["domain"]

        if search_domain:
            try:
                decision_makers = await self.find_decision_makers(
                    organization_domain=search_domain,
                    max_results=5,
                )
                result["decision_makers"] = [dm.to_dict() for dm in decision_makers]
            except ApolloError as e:
                logger.warning("Failed to find decision makers: %s", e)

        return result

    def close(self) -> None:
        """Clean up client resources."""
        # No persistent connections to clean up with urllib
        pass

    async def __aenter__(self) -> "ApolloClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        self.close()
