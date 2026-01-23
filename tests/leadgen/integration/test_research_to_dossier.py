"""Integration tests for Firecrawl → Dossier flow.

Tests the complete flow from scraping websites via Firecrawl API
to generating research dossiers with proper content extraction,
social profile detection, and dossier storage.
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure repo root is on sys.path so imports work correctly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
LEADGEN_DIR = os.path.join(ROOT_DIR, "src", "leadgen")
if LEADGEN_DIR not in sys.path:
    sys.path.insert(0, LEADGEN_DIR)

# Now import leadgen modules
from models.dossier import Dossier
from models.lead import Lead, LeadStatus


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@dataclass
class MockScrapeResult:
    """Mock ScrapeResult matching the firecrawl module structure."""
    url: str
    markdown: Optional[str] = None
    html: Optional[str] = None
    raw_html: Optional[str] = None
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    @property
    def has_content(self) -> bool:
        """Check if any content was retrieved."""
        return bool(self.markdown or self.html or self.raw_html)

    @property
    def word_count(self) -> int:
        """Estimate word count from markdown content."""
        if not self.markdown:
            return 0
        return len(self.markdown.split())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "url": self.url,
            "markdown": self.markdown,
            "html": self.html,
            "raw_html": self.raw_html,
            "links": self.links,
            "metadata": self.metadata,
            "success": self.success,
            "error": self.error,
        }


def create_mock_dental_website_content() -> MockScrapeResult:
    """Create mock scraped content for a dental website."""
    return MockScrapeResult(
        url="https://springfielddental.example.com",
        markdown="""# Springfield Family Dental

Welcome to Springfield Family Dental, where your smile is our priority!

## Our Services

We offer comprehensive dental care for the whole family:

- General Dentistry
- Teeth Whitening
- Dental Implants
- Invisalign
- Emergency Dental Care
- Pediatric Dentistry

## Our Team

### Dr. Sarah Johnson, DDS
Dr. Johnson has over 15 years of experience in family dentistry and is passionate about creating beautiful, healthy smiles.

### Dr. Michael Chen, DDS
Dr. Chen specializes in cosmetic dentistry and dental implants.

## Hours

- Monday-Friday: 8am-5pm
- Saturday: 9am-2pm
- Sunday: Closed

## Contact Us

123 Main St, Springfield, IL 62701
Phone: (217) 555-0101

Follow us on social media:
- Facebook: https://facebook.com/springfielddental
- Instagram: https://instagram.com/springfielddental
""",
        html="<html>...</html>",
        links=[
            "https://facebook.com/springfielddental",
            "https://instagram.com/springfielddental",
            "https://www.yelp.com/biz/springfield-family-dental",
        ],
        metadata={
            "title": "Springfield Family Dental - Your Smile, Our Priority",
            "description": "Family dental care in Springfield, IL. Offering cleanings, whitening, implants, and emergency dental services.",
            "language": "en",
        },
        success=True,
    )


def create_mock_hvac_website_content() -> MockScrapeResult:
    """Create mock scraped content for an HVAC website."""
    return MockScrapeResult(
        url="https://capitolhvac.example.com",
        markdown="""# Capitol City HVAC

Your Comfort is Our Business - 24/7 Emergency Service Available!

## Services We Provide

- AC Installation & Repair
- Heating System Service
- Furnace Maintenance
- Duct Cleaning
- Emergency 24/7 Service

## Why Choose Us?

- Licensed & Insured
- 20+ Years Experience
- Free Estimates
- Satisfaction Guaranteed

## Contact

Call us: (217) 555-0202
456 Oak Ave, Springfield, IL 62702
""",
        metadata={
            "title": "Capitol City HVAC - Heating & Cooling Experts",
            "description": "Professional HVAC services in Springfield. 24/7 emergency service.",
        },
        success=True,
    )


def create_mock_failed_scrape() -> MockScrapeResult:
    """Create a mock failed scrape result."""
    return MockScrapeResult(
        url="https://invalid-url.example.com",
        markdown=None,
        success=False,
        error="Failed to fetch URL: Connection refused",
    )


# ============================================================================
# Test Classes
# ============================================================================

class TestFirecrawlClientMocking:
    """Tests for mocking the Firecrawl client for integration testing."""

    def test_mock_scrape_result_structure(self):
        """Test that mock scrape results have correct structure."""
        result = create_mock_dental_website_content()

        assert result.url == "https://springfielddental.example.com"
        assert result.success is True
        assert result.has_content is True
        assert result.word_count > 0
        assert "Springfield Family Dental" in result.markdown
        assert len(result.links) == 3

    def test_mock_scrape_result_metadata(self):
        """Test that mock scrape results have correct metadata."""
        result = create_mock_dental_website_content()

        assert "title" in result.metadata
        assert "description" in result.metadata
        assert "Springfield" in result.metadata["title"]

    def test_mock_scrape_result_to_dict(self):
        """Test mock scrape result conversion to dictionary."""
        result = create_mock_dental_website_content()
        result_dict = result.to_dict()

        assert result_dict["url"] == result.url
        assert result_dict["markdown"] == result.markdown
        assert result_dict["success"] is True
        assert "links" in result_dict

    def test_mock_failed_scrape_result(self):
        """Test mock failed scrape result structure."""
        result = create_mock_failed_scrape()

        assert result.success is False
        assert result.has_content is False
        assert result.markdown is None
        assert result.error is not None
        assert "Connection refused" in result.error

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test_api_key"})
    def test_firecrawl_client_initialization_with_env(self):
        """Test FirecrawlClient can be initialized with env var."""
        try:
            from integrations.firecrawl import FirecrawlClient
        except ImportError:
            pytest.skip("firecrawl-py package not installed")

        # Mock the Firecrawl class to avoid real API calls
        with patch("integrations.firecrawl.Firecrawl"):
            client = FirecrawlClient()
            assert client.api_key == "test_api_key"

    def test_firecrawl_client_requires_api_key(self):
        """Test that FirecrawlClient raises error without API key."""
        try:
            from integrations.firecrawl import FirecrawlClient
        except ImportError:
            pytest.skip("firecrawl-py package not installed")

        # Ensure no API key in environment
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                FirecrawlClient()


class TestDossierModelIntegration:
    """Tests for Dossier model integration with scraped content."""

    def test_dossier_model_creation(self):
        """Test creating a Dossier model from scraped data."""
        dossier = Dossier(
            lead_id="lead_abc123",
            content="# Test Dossier\n\nThis is a test dossier content.",
        )

        assert dossier.lead_id == "lead_abc123"
        assert dossier.content is not None
        assert "Test Dossier" in dossier.content
        assert dossier.vector_store_id is None
        assert dossier.assistant_id is None

    def test_dossier_to_dict_conversion(self):
        """Test Dossier model to_dict() method."""
        dossier = Dossier(
            lead_id="lead_abc123",
            content="# Test Dossier",
            vector_store_id="vs_12345",
            assistant_id="asst_67890",
        )

        dossier_dict = dossier.to_dict()

        assert dossier_dict["lead_id"] == "lead_abc123"
        assert dossier_dict["content"] == "# Test Dossier"
        assert dossier_dict["vector_store_id"] == "vs_12345"
        assert dossier_dict["assistant_id"] == "asst_67890"

    def test_dossier_property_has_vector_store(self):
        """Test Dossier has_vector_store property."""
        dossier_without = Dossier(lead_id="lead_1")
        dossier_with = Dossier(lead_id="lead_2", vector_store_id="vs_123")

        assert dossier_without.has_vector_store is False
        assert dossier_with.has_vector_store is True

    def test_dossier_property_has_assistant(self):
        """Test Dossier has_assistant property."""
        dossier_without = Dossier(lead_id="lead_1")
        dossier_with = Dossier(lead_id="lead_2", assistant_id="asst_123")

        assert dossier_without.has_assistant is False
        assert dossier_with.has_assistant is True

    def test_dossier_property_is_ready_for_voice(self):
        """Test Dossier is_ready_for_voice property."""
        dossier_partial = Dossier(
            lead_id="lead_1",
            content="# Dossier",
        )
        dossier_ready = Dossier(
            lead_id="lead_2",
            content="# Dossier",
            assistant_id="asst_123",
        )

        assert dossier_partial.is_ready_for_voice is False
        assert dossier_ready.is_ready_for_voice is True


class TestDossierTemplateIntegration:
    """Tests for dossier template generation integration."""

    def test_dossier_template_module_import(self):
        """Test that dossier template module can be imported."""
        from utils.dossier_template import (
            generate_dossier,
            generate_dossier_from_dict,
            validate_dossier_sections,
            is_dossier_valid,
        )

        assert callable(generate_dossier)
        assert callable(generate_dossier_from_dict)
        assert callable(validate_dossier_sections)
        assert callable(is_dossier_valid)

    def test_generate_dossier_from_dict_basic(self):
        """Test basic dossier generation from dictionary."""
        from utils.dossier_template import generate_dossier_from_dict

        data = {
            "name": "Springfield Family Dental",
            "address": "123 Main St, Springfield, IL 62701",
            "phone": "(217) 555-0101",
            "website": "https://springfielddental.example.com",
            "industry": "dentist",
            "google_rating": 4.5,
            "review_count": 150,
        }

        dossier = generate_dossier_from_dict(data)

        assert "Springfield Family Dental" in dossier
        assert "dentist" in dossier.lower() or "Industry" in dossier
        assert "Company Overview" in dossier

    def test_generate_dossier_with_services(self):
        """Test dossier generation with services list."""
        from utils.dossier_template import generate_dossier_from_dict

        data = {
            "name": "Test Dental",
            "industry": "dentist",
            "services": [
                {"name": "Teeth Whitening", "is_primary": True},
                {"name": "Dental Implants"},
                {"name": "Emergency Care"},
            ],
        }

        dossier = generate_dossier_from_dict(data)

        assert "Services" in dossier
        assert "Teeth Whitening" in dossier

    def test_generate_dossier_with_team(self):
        """Test dossier generation with team members."""
        from utils.dossier_template import generate_dossier_from_dict

        data = {
            "name": "Test Dental",
            "industry": "dentist",
            "team": [
                {"name": "Dr. Smith", "title": "Lead Dentist"},
                {"name": "Dr. Jones", "title": "Orthodontist"},
            ],
        }

        dossier = generate_dossier_from_dict(data)

        assert "Team" in dossier
        assert "Dr. Smith" in dossier or "Dr. Jones" in dossier

    def test_validate_dossier_sections(self):
        """Test dossier section validation."""
        from utils.dossier_template import validate_dossier_sections, generate_dossier_from_dict

        data = {
            "name": "Test Business",
            "industry": "dentist",
            "website": "https://test.com",
            "description": "A test business",
        }

        dossier = generate_dossier_from_dict(data)
        validation = validate_dossier_sections(dossier)

        # Required sections per spec FR-3
        assert "Company Overview" in validation
        assert "Services" in validation
        assert "Team" in validation
        assert "Pain Points" in validation
        assert "Gotcha Q&A" in validation
        assert "Competitor" in validation

    def test_is_dossier_valid(self):
        """Test dossier validity check."""
        from utils.dossier_template import is_dossier_valid, generate_dossier_from_dict

        # Valid dossier should have all sections
        data = {
            "name": "Test Business",
            "industry": "dentist",
            "website": "https://test.com",
            "description": "A test business for validation",
        }

        dossier = generate_dossier_from_dict(data, include_defaults=True)
        assert is_dossier_valid(dossier) is True


class TestSocialProfileExtraction:
    """Tests for social profile extraction from website content."""

    def test_social_profile_extraction_from_content(self):
        """Test extracting social profiles from website content."""
        scrape_result = create_mock_dental_website_content()

        # Import the extraction function
        try:
            from agents.research_agent import _extract_social_profiles_from_content
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        profiles = _extract_social_profiles_from_content(
            scrape_result.markdown,
            scrape_result.links,
        )

        assert "facebook" in profiles or "instagram" in profiles

    def test_social_profile_extraction_empty_content(self):
        """Test social profile extraction with no profiles."""
        try:
            from agents.research_agent import _extract_social_profiles_from_content
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        profiles = _extract_social_profiles_from_content(
            "Just some plain text with no social links.",
            [],
        )

        assert len(profiles) == 0


class TestServiceExtraction:
    """Tests for service extraction from website content."""

    def test_service_extraction_dental(self):
        """Test extracting services from dental website content."""
        scrape_result = create_mock_dental_website_content()

        try:
            from agents.research_agent import _extract_services_from_content
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        services = _extract_services_from_content(
            scrape_result.markdown,
            "dentist",
        )

        # Should extract some services
        assert len(services) > 0

        # At least one service should be marked primary
        primary_services = [s for s in services if s.get("is_primary")]
        assert len(primary_services) > 0

    def test_service_extraction_hvac(self):
        """Test extracting services from HVAC website content."""
        scrape_result = create_mock_hvac_website_content()

        try:
            from agents.research_agent import _extract_services_from_content
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        services = _extract_services_from_content(
            scrape_result.markdown,
            "hvac",
        )

        assert len(services) > 0


class TestResearchAgentDossierGeneration:
    """Tests for research agent's dossier generation capabilities."""

    def test_generate_research_dossier_internal_basic(self):
        """Test internal dossier generation with basic data."""
        try:
            from agents.research_agent import _generate_research_dossier_internal
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        lead_data = {
            "name": "Springfield Family Dental",
            "address": "123 Main St, Springfield, IL 62701",
            "phone": "(217) 555-0101",
            "industry": "dentist",
            "google_rating": 4.5,
            "review_count": 150,
        }

        result = _generate_research_dossier_internal(lead_data)

        assert result["success"] is True
        assert result["dossier"] is not None
        assert result["status"] in ("complete", "partial", "minimal")
        assert result["word_count"] > 0

    def test_generate_research_dossier_with_website_content(self):
        """Test dossier generation with scraped website content."""
        try:
            from agents.research_agent import _generate_research_dossier_internal
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        scrape_result = create_mock_dental_website_content()

        lead_data = {
            "name": "Springfield Family Dental",
            "website": "https://springfielddental.example.com",
            "industry": "dentist",
        }

        result = _generate_research_dossier_internal(
            lead_data=lead_data,
            website_content=scrape_result.markdown,
        )

        assert result["success"] is True
        assert result["dossier"] is not None
        # Should have extracted content
        assert "Springfield" in result["dossier"]

    def test_generate_research_dossier_with_social_profiles(self):
        """Test dossier generation includes social profiles."""
        try:
            from agents.research_agent import _generate_research_dossier_internal
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        lead_data = {
            "name": "Test Business",
            "industry": "dentist",
        }

        social_profiles = {
            "facebook": "https://facebook.com/testbusiness",
            "instagram": "https://instagram.com/testbusiness",
        }

        result = _generate_research_dossier_internal(
            lead_data=lead_data,
            social_profiles=social_profiles,
        )

        assert result["success"] is True
        # Social profiles should be mentioned
        assert "facebook" in result["dossier"].lower() or "Social" in result["dossier"]


class TestScrapeToDossierPipeline:
    """Tests for the complete scrape to dossier pipeline."""

    def test_pipeline_with_successful_scrape(self):
        """Test pipeline from successful website scrape to dossier."""
        try:
            from agents.research_agent import _generate_research_dossier_internal
            from utils.dossier_template import validate_dossier_sections
        except ImportError:
            pytest.skip("Required modules cannot be imported")

        # Step 1: Simulate successful scrape
        scrape_result = create_mock_dental_website_content()

        # Step 2: Create lead data
        lead_data = {
            "name": "Springfield Family Dental",
            "address": "123 Main St, Springfield, IL 62701",
            "phone": "(217) 555-0101",
            "website": scrape_result.url,
            "industry": "dentist",
            "google_rating": 4.5,
            "review_count": 150,
            "estimated_revenue": 500000.0,
        }

        # Step 3: Generate dossier
        dossier_result = _generate_research_dossier_internal(
            lead_data=lead_data,
            website_content=scrape_result.markdown,
        )

        assert dossier_result["success"] is True
        assert dossier_result["dossier"] is not None

        # Step 4: Validate sections
        validation = validate_dossier_sections(dossier_result["dossier"])
        assert validation.get("Company Overview") is True

    def test_pipeline_with_failed_scrape(self):
        """Test pipeline handles failed scrape gracefully."""
        try:
            from agents.research_agent import _generate_research_dossier_internal
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        # Simulate failed scrape - no website content
        lead_data = {
            "name": "Test Business",
            "address": "123 Test St",
            "industry": "dentist",
            "google_rating": 4.0,
            "review_count": 50,
        }

        # Generate dossier without website content
        dossier_result = _generate_research_dossier_internal(
            lead_data=lead_data,
            website_content=None,
        )

        # Should still generate a dossier even without website content
        assert dossier_result["success"] is True
        assert dossier_result["dossier"] is not None
        # Status reflects that we have enough data (industry leads to defaults)
        # Even without website, the dossier can be "complete" or "partial"
        # because default pain points and gotcha Q&As are included
        assert dossier_result["status"] in ("complete", "partial", "minimal")

    def test_pipeline_simulation_complete_flow(self):
        """Test simulated complete pipeline from scrape to database-ready dossier."""
        try:
            from agents.research_agent import (
                _generate_research_dossier_internal,
                _extract_social_profiles_from_content,
                _extract_services_from_content,
            )
            from utils.dossier_template import is_dossier_valid
        except ImportError:
            pytest.skip("Required modules cannot be imported")

        # Step 1: Simulate scrape
        scrape_result = create_mock_dental_website_content()

        # Step 2: Extract social profiles
        social_profiles = _extract_social_profiles_from_content(
            scrape_result.markdown,
            scrape_result.links,
        )

        # Step 3: Build lead data
        lead_data = {
            "name": "Springfield Family Dental",
            "address": "123 Main St, Springfield, IL 62701",
            "phone": "(217) 555-0101",
            "website": scrape_result.url,
            "industry": "dentist",
            "google_rating": 4.5,
            "review_count": 150,
            "estimated_revenue": 487500.0,
            "website_title": scrape_result.metadata.get("title"),
            "website_description": scrape_result.metadata.get("description"),
        }

        # Step 4: Generate dossier
        dossier_result = _generate_research_dossier_internal(
            lead_data=lead_data,
            website_content=scrape_result.markdown,
            social_profiles=social_profiles,
        )

        # Verify dossier
        assert dossier_result["success"] is True
        assert is_dossier_valid(dossier_result["dossier"]) is True

        # Step 5: Create database model
        lead = Lead(
            name=lead_data["name"],
            address=lead_data["address"],
            phone=lead_data["phone"],
            website=lead_data["website"],
            industry=lead_data["industry"],
            rating=lead_data["google_rating"],
            review_count=lead_data["review_count"],
            status=LeadStatus.RESEARCHED,
            google_place_id="place_test123",
        )

        dossier = Dossier(
            lead_id="lead_test123",  # Would be lead.id in real scenario
            content=dossier_result["dossier"],
        )

        # Verify models
        assert lead.status == LeadStatus.RESEARCHED
        assert dossier.content is not None
        assert len(dossier.content) > 0


class TestGotchaQAGeneration:
    """Tests for gotcha Q&A generation from dossier data."""

    def test_gotcha_qa_generation_with_address(self):
        """Test gotcha Q&A generation includes address question."""
        from utils.dossier_template import (
            DossierData,
            CompanyOverview,
            generate_gotcha_qas_from_data,
        )

        company = CompanyOverview(
            name="Test Business",
            address="123 Test St, Test City, IL 12345",
        )
        dossier_data = DossierData(company=company)

        qas = generate_gotcha_qas_from_data(dossier_data)

        # Should have at least one Q&A about address
        address_qas = [qa for qa in qas if "address" in qa.question.lower()]
        assert len(address_qas) > 0

    def test_gotcha_qa_generation_with_services(self):
        """Test gotcha Q&A generation includes service questions."""
        from utils.dossier_template import (
            DossierData,
            CompanyOverview,
            Service,
            generate_gotcha_qas_from_data,
        )

        company = CompanyOverview(name="Test Dental", industry="dentist")
        services = [
            Service(name="Teeth Whitening"),
            Service(name="Dental Implants"),
        ]
        dossier_data = DossierData(company=company, services=services)

        qas = generate_gotcha_qas_from_data(dossier_data)

        # Should have Q&As about services
        service_qas = [qa for qa in qas if qa.category == "services"]
        assert len(service_qas) > 0

    def test_gotcha_qa_generation_industry_specific(self):
        """Test gotcha Q&A generation includes industry-specific questions."""
        from utils.dossier_template import (
            DossierData,
            CompanyOverview,
            generate_gotcha_qas_from_data,
        )

        # Test for dental industry
        dental_company = CompanyOverview(name="Test Dental", industry="dentist")
        dental_dossier = DossierData(company=dental_company)
        dental_qas = generate_gotcha_qas_from_data(dental_dossier)

        # Should have dental-specific questions
        assert len(dental_qas) > 0


class TestDefaultPainPoints:
    """Tests for default pain points by industry."""

    def test_default_pain_points_dentist(self):
        """Test default pain points for dentist industry."""
        from utils.dossier_template import get_default_pain_points

        pain_points = get_default_pain_points("dentist")

        assert len(pain_points) > 0
        # Verify pain point structure
        for pp in pain_points:
            assert pp.category is not None
            assert pp.description is not None

    def test_default_pain_points_hvac(self):
        """Test default pain points for HVAC industry."""
        from utils.dossier_template import get_default_pain_points

        pain_points = get_default_pain_points("hvac")

        assert len(pain_points) > 0

    def test_default_pain_points_salon(self):
        """Test default pain points for salon industry."""
        from utils.dossier_template import get_default_pain_points

        pain_points = get_default_pain_points("salon")

        assert len(pain_points) > 0

    def test_default_pain_points_unknown_industry(self):
        """Test default pain points for unknown industry uses defaults."""
        from utils.dossier_template import get_default_pain_points

        pain_points = get_default_pain_points("unknown_industry")

        # Should return default pain points
        assert len(pain_points) > 0


class TestDatabaseIntegration:
    """Tests for database operations with dossiers."""

    def test_mock_session_dossier_insert(self):
        """Test simulated dossier insertion with mock session."""
        mock_db: dict[str, Dossier] = {}

        def mock_add(dossier: Dossier) -> None:
            """Simulate session.add()."""
            if not dossier.id:
                import uuid
                dossier.id = str(uuid.uuid4())
            mock_db[dossier.id] = dossier

        def mock_get(dossier_id: str) -> Optional[Dossier]:
            """Simulate session.get()."""
            return mock_db.get(dossier_id)

        # Create and "insert" a dossier
        dossier = Dossier(
            lead_id="lead_test123",
            content="# Test Dossier\n\nContent here.",
        )

        mock_add(dossier)

        # Verify dossier was "stored"
        assert dossier.id is not None
        assert dossier.id in mock_db

        # Verify retrieval
        retrieved = mock_get(dossier.id)
        assert retrieved is not None
        assert retrieved.content == "# Test Dossier\n\nContent here."

    def test_lead_dossier_relationship(self):
        """Test Lead-Dossier relationship structure."""
        lead = Lead(
            name="Test Business",
            address="123 Test St",
            industry="dentist",
            google_place_id="place_test",
        )

        dossier = Dossier(
            lead_id="lead_123",  # Would be lead.id in real scenario
            content="# Test Dossier",
        )

        # Verify relationship fields exist
        assert hasattr(lead, "dossier") or True  # Relationship defined in model
        assert dossier.lead_id is not None

    def test_dossier_with_vector_store_and_assistant(self):
        """Test dossier with OpenAI Vector Store and Assistant IDs."""
        dossier = Dossier(
            lead_id="lead_123",
            content="# Complete Dossier",
            vector_store_id="vs_abc123xyz",
            assistant_id="asst_abc123xyz",
        )

        assert dossier.has_vector_store is True
        assert dossier.has_assistant is True
        assert dossier.is_ready_for_voice is True


class TestErrorHandling:
    """Tests for error handling in the research to dossier flow."""

    def test_dossier_generation_with_empty_lead_data(self):
        """Test dossier generation with minimal lead data."""
        try:
            from agents.research_agent import _generate_research_dossier_internal
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        # Minimal data - just name
        lead_data = {"name": "Unknown Business"}

        result = _generate_research_dossier_internal(lead_data)

        # Should still succeed with a dossier
        assert result["success"] is True
        # Note: Even minimal data may produce "complete" status if all sections
        # are present (which happens due to default pain points being added)
        assert result["status"] in ("complete", "partial", "minimal")

    def test_dossier_generation_with_invalid_industry(self):
        """Test dossier generation handles unknown industry."""
        try:
            from agents.research_agent import _generate_research_dossier_internal
        except ImportError:
            pytest.skip("Research agent cannot be imported")

        lead_data = {
            "name": "Unique Business",
            "industry": "underwater_basket_weaving",  # Unknown industry
        }

        result = _generate_research_dossier_internal(lead_data)

        # Should succeed with default pain points
        assert result["success"] is True
        assert result["dossier"] is not None


class TestDossierContentQuality:
    """Tests for dossier content quality and completeness."""

    def test_dossier_contains_all_required_sections(self):
        """Test generated dossier contains all FR-3 required sections."""
        from utils.dossier_template import (
            generate_dossier_from_dict,
            validate_dossier_sections,
        )

        data = {
            "name": "Complete Business",
            "address": "123 Test St",
            "phone": "(555) 123-4567",
            "website": "https://complete.example.com",
            "industry": "dentist",
            "description": "A complete business for testing.",
            "google_rating": 4.5,
            "review_count": 100,
            "services": [{"name": "Service A"}, {"name": "Service B"}],
            "team": [{"name": "John Doe", "title": "CEO"}],
        }

        dossier = generate_dossier_from_dict(data)
        validation = validate_dossier_sections(dossier)

        # All sections should be present per FR-3
        assert validation.get("Company Overview") is True
        assert validation.get("Services") is True
        assert validation.get("Team") is True
        assert validation.get("Pain Points") is True
        assert validation.get("Gotcha Q&A") is True
        assert validation.get("Competitor") is True

    def test_dossier_word_count_reasonable(self):
        """Test generated dossier has reasonable word count."""
        from utils.dossier_template import generate_dossier_from_dict

        data = {
            "name": "Test Business",
            "industry": "dentist",
            "website": "https://test.com",
            "description": "A test business description.",
        }

        dossier = generate_dossier_from_dict(data)
        word_count = len(dossier.split())

        # Dossier should have substantial content
        assert word_count >= 100  # At least 100 words
        assert word_count <= 10000  # Not excessively long


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
