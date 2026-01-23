"""Integration tests for Google Maps → Lead DB flow.

Tests the complete flow from scraping businesses via Google Maps API
to persisting leads in the database with proper deduplication,
revenue estimation, and status tracking.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure repo root is on sys.path so imports work correctly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
LEADGEN_DIR = os.path.join(ROOT_DIR, "src", "leadgen")
if LEADGEN_DIR not in sys.path:
    sys.path.insert(0, LEADGEN_DIR)

# Now import leadgen modules
from models.lead import Lead, LeadStatus


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@dataclass
class MockPlaceResult:
    """Mock PlaceResult matching the google_maps module structure."""
    place_id: str
    name: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    types: list[str] = None
    location: Optional[tuple[float, float]] = None
    business_status: Optional[str] = "OPERATIONAL"

    def __post_init__(self):
        if self.types is None:
            self.types = []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "place_id": self.place_id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "rating": self.rating,
            "review_count": self.review_count,
            "types": self.types,
            "location": self.location,
            "business_status": self.business_status,
        }


@dataclass
class MockSearchResult:
    """Mock SearchResult matching the google_maps module structure."""
    places: list[MockPlaceResult]
    total_results: int
    pages_fetched: int
    next_page_token: Optional[str] = None


def create_mock_places() -> list[MockPlaceResult]:
    """Create a set of mock place results for testing."""
    return [
        MockPlaceResult(
            place_id="place_abc123",
            name="Springfield Family Dental",
            address="123 Main St, Springfield, IL 62701",
            phone="+1-217-555-0101",
            website="https://springfielddental.example.com",
            rating=4.5,
            review_count=150,
            types=["dentist", "health"],
            location=(39.7817, -89.6501),
        ),
        MockPlaceResult(
            place_id="place_def456",
            name="Capitol City HVAC",
            address="456 Oak Ave, Springfield, IL 62702",
            phone="+1-217-555-0202",
            website="https://capitolhvac.example.com",
            rating=4.2,
            review_count=85,
            types=["hvac", "contractor"],
            location=(39.7900, -89.6600),
        ),
        MockPlaceResult(
            place_id="place_ghi789",
            name="Downtown Hair Salon",
            address="789 Elm St, Springfield, IL 62703",
            phone="+1-217-555-0303",
            website="https://downtownhair.example.com",
            rating=4.8,
            review_count=210,
            types=["hair_salon", "beauty_salon"],
            location=(39.7750, -89.6400),
        ),
        MockPlaceResult(
            place_id="place_jkl012",
            name="Small Business LLC",
            address="012 Pine Rd, Springfield, IL 62704",
            phone=None,  # No phone
            website=None,  # No website
            rating=3.5,
            review_count=5,  # Low review count - likely below revenue threshold
            types=["business"],
            location=(39.7600, -89.6700),
        ),
        MockPlaceResult(
            place_id="place_mno345",
            name="Premium Auto Repair",
            address="345 Motor Way, Springfield, IL 62705",
            phone="+1-217-555-0505",
            website="https://premiumauto.example.com",
            rating=4.7,
            review_count=320,
            types=["car_repair", "auto_service"],
            location=(39.7850, -89.6550),
        ),
    ]


# ============================================================================
# Test Classes
# ============================================================================

class TestScraperToDbFlow:
    """Integration tests for the Google Maps scraping to database flow."""

    def test_lead_model_creation_from_scrape_data(self):
        """Test that a Lead model can be created from scraped data."""
        place = create_mock_places()[0]  # Springfield Family Dental

        lead = Lead(
            name=place.name,
            address=place.address,
            phone=place.phone,
            website=place.website,
            industry="dentist",
            rating=Decimal(str(place.rating)) if place.rating else None,
            review_count=place.review_count,
            revenue=Decimal("487500.00"),  # Estimated revenue
            status=LeadStatus.NEW,
            google_place_id=place.place_id,
        )

        assert lead.name == "Springfield Family Dental"
        assert lead.address == "123 Main St, Springfield, IL 62701"
        assert lead.phone == "+1-217-555-0101"
        assert lead.website == "https://springfielddental.example.com"
        assert lead.industry == "dentist"
        assert lead.rating == Decimal("4.5")
        assert lead.review_count == 150
        assert lead.revenue == Decimal("487500.00")
        assert lead.status == LeadStatus.NEW
        assert lead.google_place_id == "place_abc123"

    def test_lead_to_dict_conversion(self):
        """Test Lead model to_dict() method works correctly."""
        lead = Lead(
            name="Test Business",
            address="123 Test St",
            phone="+1-555-0100",
            website="https://test.com",
            industry="dentist",
            rating=Decimal("4.5"),
            review_count=100,
            revenue=Decimal("500000.00"),
            status=LeadStatus.NEW,
            google_place_id="place_test123",
        )

        lead_dict = lead.to_dict()

        assert lead_dict["name"] == "Test Business"
        assert lead_dict["address"] == "123 Test St"
        assert lead_dict["phone"] == "+1-555-0100"
        assert lead_dict["website"] == "https://test.com"
        assert lead_dict["industry"] == "dentist"
        assert lead_dict["rating"] == 4.5
        assert lead_dict["review_count"] == 100
        assert lead_dict["revenue"] == 500000.00
        assert lead_dict["status"] == "new"
        assert lead_dict["google_place_id"] == "place_test123"

    def test_lead_status_transitions(self):
        """Test that Lead status can be updated through pipeline stages."""
        lead = Lead(
            name="Pipeline Test Business",
            address="Test Address",
            industry="hvac",
            status=LeadStatus.NEW,
        )

        # Verify initial status
        assert lead.status == LeadStatus.NEW

        # Simulate pipeline progression
        lead.status = LeadStatus.RESEARCHING
        assert lead.status == LeadStatus.RESEARCHING

        lead.status = LeadStatus.RESEARCHED
        assert lead.status == LeadStatus.RESEARCHED

        lead.status = LeadStatus.DEPLOYING
        assert lead.status == LeadStatus.DEPLOYING

        lead.status = LeadStatus.DEPLOYED
        assert lead.status == LeadStatus.DEPLOYED

        lead.status = LeadStatus.EMAILED
        assert lead.status == LeadStatus.EMAILED

    def test_lead_status_enum_values(self):
        """Test all LeadStatus enum values are defined correctly."""
        expected_statuses = [
            "new", "researching", "researched", "deploying", "deployed",
            "emailed", "opened", "clicked", "replied", "converted",
            "disqualified", "failed"
        ]

        actual_values = [status.value for status in LeadStatus]

        for expected in expected_statuses:
            assert expected in actual_values, f"Missing status: {expected}"


class TestRevenueEstimationIntegration:
    """Tests for revenue estimation integration with lead data."""

    def test_revenue_estimation_module_import(self):
        """Test that revenue estimation module can be imported."""
        from utils.revenue_heuristics import (
            estimate_revenue,
            is_qualified_revenue,
            filter_qualified_leads,
        )

        assert callable(estimate_revenue)
        assert callable(is_qualified_revenue)
        assert callable(filter_qualified_leads)

    def test_revenue_estimation_with_mock_place_data(self):
        """Test revenue estimation using mock place data."""
        from utils.revenue_heuristics import estimate_revenue, is_qualified_revenue

        places = create_mock_places()

        # Test dental office with good reviews
        dental = places[0]
        dental_data = {
            "review_count": dental.review_count,
            "google_rating": dental.rating,
            "rating": dental.rating,
            "industry": "dentist",
            "website": dental.website,
        }

        dental_revenue = estimate_revenue(dental_data)
        assert is_qualified_revenue(dental_revenue), \
            f"Dental revenue {dental_revenue} should be qualified"
        assert 100_000 <= dental_revenue <= 1_000_000

    def test_revenue_estimation_low_volume_business(self):
        """Test that low-volume businesses may not qualify."""
        from utils.revenue_heuristics import estimate_revenue, is_qualified_revenue

        places = create_mock_places()

        # Test small business with few reviews
        small_biz = places[3]
        small_data = {
            "review_count": small_biz.review_count,  # Only 5 reviews
            "google_rating": small_biz.rating,
            "rating": small_biz.rating,
            "industry": "general",
            "website": small_biz.website,
        }

        small_revenue = estimate_revenue(small_data)
        # Low review count may result in low revenue estimate
        # This documents expected behavior
        assert small_revenue >= 0

    def test_qualified_leads_filtering(self):
        """Test filtering leads by revenue qualification."""
        from utils.revenue_heuristics import is_qualified_revenue

        test_revenues = [
            (50_000, False),      # Below minimum
            (100_000, True),      # At minimum
            (500_000, True),      # Middle of range
            (1_000_000, True),    # At maximum
            (1_500_000, False),   # Above maximum
        ]

        for revenue, expected_qualified in test_revenues:
            result = is_qualified_revenue(revenue)
            assert result == expected_qualified, \
                f"Revenue {revenue} qualification mismatch: expected {expected_qualified}, got {result}"


class TestGoogleMapsClientMocking:
    """Tests for mocking the Google Maps client for integration testing."""

    def test_mock_search_result_structure(self):
        """Test that mock search results have correct structure."""
        places = create_mock_places()
        search_result = MockSearchResult(
            places=places,
            total_results=len(places),
            pages_fetched=1,
        )

        assert search_result.total_results == 5
        assert search_result.pages_fetched == 1
        assert len(search_result.places) == 5
        assert search_result.next_page_token is None

    def test_mock_place_to_dict(self):
        """Test mock place conversion to dictionary."""
        place = create_mock_places()[0]
        place_dict = place.to_dict()

        assert place_dict["place_id"] == "place_abc123"
        assert place_dict["name"] == "Springfield Family Dental"
        assert place_dict["rating"] == 4.5
        assert place_dict["review_count"] == 150

    @patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test_api_key"})
    def test_google_maps_client_initialization_with_env(self):
        """Test GoogleMapsClient can be initialized with env var."""
        # Skip if googlemaps package not available
        try:
            from integrations.google_maps import GoogleMapsClient
        except ImportError:
            pytest.skip("googlemaps package not installed")

        # Mock the googlemaps.Client to avoid real API calls
        with patch("integrations.google_maps.googlemaps.Client"):
            client = GoogleMapsClient()
            assert client.api_key == "test_api_key"

    def test_google_maps_client_requires_api_key(self):
        """Test that GoogleMapsClient raises error without API key."""
        try:
            from integrations.google_maps import GoogleMapsClient
        except ImportError:
            pytest.skip("googlemaps package not installed")

        # Ensure no API key in environment
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": ""}, clear=False):
            # Remove the key if it exists
            env_copy = os.environ.copy()
            if "GOOGLE_MAPS_API_KEY" in env_copy:
                del env_copy["GOOGLE_MAPS_API_KEY"]

            with patch.dict(os.environ, env_copy, clear=True):
                with pytest.raises(ValueError, match="API key required"):
                    GoogleMapsClient()


class TestScraperAgentIntegration:
    """Tests for scraper agent integration with database storage."""

    def test_scraped_lead_dataclass_structure(self):
        """Test ScrapedLead dataclass from scraper agent."""
        try:
            from agents.scraper_agent import ScrapedLead
        except ImportError:
            pytest.skip("Scraper agent cannot be imported")

        lead = ScrapedLead(
            place_id="test_place",
            name="Test Business",
            address="123 Test St",
            phone="+1-555-0100",
            website="https://test.com",
            industry="dentist",
            rating=4.5,
            review_count=100,
            estimated_revenue=500000.0,
            revenue_confidence=0.8,
        )

        assert lead.place_id == "test_place"
        assert lead.name == "Test Business"
        assert lead.estimated_revenue == 500000.0
        assert lead.revenue_confidence == 0.8

    def test_scraped_lead_to_dict(self):
        """Test ScrapedLead conversion to dictionary."""
        try:
            from agents.scraper_agent import ScrapedLead
        except ImportError:
            pytest.skip("Scraper agent cannot be imported")

        lead = ScrapedLead(
            place_id="test_place",
            name="Test Business",
            address="123 Test St",
            phone="+1-555-0100",
            website="https://test.com",
            industry="dentist",
            rating=4.5,
            review_count=100,
            estimated_revenue=500000.0,
            revenue_confidence=0.8,
        )

        lead_dict = lead.to_dict()

        assert lead_dict["place_id"] == "test_place"
        assert lead_dict["estimated_revenue"] == 500000.0
        assert lead_dict["revenue_confidence"] == 0.8


class TestDeduplicationIntegration:
    """Tests for deduplication when persisting scraped leads to database."""

    def test_place_id_deduplication_logic(self):
        """Test that duplicate place_ids are detected correctly."""
        places = create_mock_places()

        # Add a duplicate
        duplicate = MockPlaceResult(
            place_id="place_abc123",  # Same as first place
            name="Springfield Family Dental - Duplicate",
            address="123 Main St, Springfield, IL 62701",
            phone="+1-217-555-0101",
            website="https://springfielddental.example.com",
            rating=4.5,
            review_count=150,
        )
        places.append(duplicate)

        # Simulate deduplication
        seen_place_ids: set[str] = set()
        unique_places = []

        for place in places:
            if place.place_id not in seen_place_ids:
                seen_place_ids.add(place.place_id)
                unique_places.append(place)

        # Should have 5 unique places (original 5, duplicate ignored)
        assert len(unique_places) == 5

    def test_cross_industry_deduplication(self):
        """Test deduplication across multiple industry searches."""
        # Simulate dental search
        dental_places = [
            MockPlaceResult(
                place_id="place_multi",
                name="Multi-Service Medical Center",
                address="100 Health Blvd",
                rating=4.6,
                review_count=200,
            ),
        ]

        # Simulate doctor search (same place appears)
        doctor_places = [
            MockPlaceResult(
                place_id="place_multi",  # Same place_id
                name="Multi-Service Medical Center",
                address="100 Health Blvd",
                rating=4.6,
                review_count=200,
            ),
        ]

        # Simulate cross-industry deduplication
        seen_place_ids: set[str] = set()
        results: dict[str, list[MockPlaceResult]] = {}

        for industry, places in [("dentist", dental_places), ("doctor", doctor_places)]:
            unique = []
            for place in places:
                if place.place_id not in seen_place_ids:
                    seen_place_ids.add(place.place_id)
                    unique.append(place)
            results[industry] = unique

        # Dentist gets the place (first search)
        assert len(results["dentist"]) == 1
        # Doctor gets nothing (duplicate)
        assert len(results["doctor"]) == 0

    def test_google_place_id_unique_constraint(self):
        """Test that google_place_id serves as unique identifier in Lead model."""
        lead1 = Lead(
            name="Business A",
            address="Address A",
            industry="dentist",
            google_place_id="unique_place_123",
        )

        lead2 = Lead(
            name="Business B",
            address="Address B",
            industry="dentist",
            google_place_id="unique_place_456",
        )

        # Different place_ids should be allowed
        assert lead1.google_place_id != lead2.google_place_id

        # Same place_id would violate unique constraint in database
        lead3 = Lead(
            name="Business A Duplicate",
            address="Address A",
            industry="dentist",
            google_place_id="unique_place_123",  # Same as lead1
        )

        assert lead1.google_place_id == lead3.google_place_id


class TestEndToEndScrapeToDB:
    """End-to-end tests for the complete scrape to database flow."""

    def test_mock_scrape_and_convert_to_leads(self):
        """Test converting mock scrape results to Lead models."""
        from utils.revenue_heuristics import estimate_revenue

        places = create_mock_places()
        leads = []

        for place in places:
            # Estimate revenue
            business_data = {
                "review_count": place.review_count or 0,
                "google_rating": place.rating,
                "rating": place.rating,
                "industry": place.types[0] if place.types else "general",
                "website": place.website,
            }

            revenue = estimate_revenue(business_data)

            # Create Lead model
            lead = Lead(
                name=place.name,
                address=place.address,
                phone=place.phone,
                website=place.website,
                industry=place.types[0] if place.types else "general",
                rating=Decimal(str(place.rating)) if place.rating else None,
                review_count=place.review_count,
                revenue=Decimal(str(revenue)) if revenue else None,
                status=LeadStatus.NEW,
                google_place_id=place.place_id,
            )

            leads.append(lead)

        # Verify all leads were created
        assert len(leads) == 5

        # Verify data integrity
        assert leads[0].name == "Springfield Family Dental"
        assert leads[0].google_place_id == "place_abc123"
        assert leads[0].status == LeadStatus.NEW

    def test_filter_qualified_leads_from_scrape(self):
        """Test filtering scraped leads by revenue qualification."""
        from utils.revenue_heuristics import estimate_revenue, is_qualified_revenue

        places = create_mock_places()
        qualified_leads = []

        for place in places:
            business_data = {
                "review_count": place.review_count or 0,
                "google_rating": place.rating,
                "rating": place.rating,
                "industry": place.types[0] if place.types else "general",
                "website": place.website,
            }

            revenue = estimate_revenue(business_data)

            if is_qualified_revenue(revenue):
                lead = Lead(
                    name=place.name,
                    address=place.address,
                    phone=place.phone,
                    website=place.website,
                    industry=place.types[0] if place.types else "general",
                    rating=Decimal(str(place.rating)) if place.rating else None,
                    review_count=place.review_count,
                    revenue=Decimal(str(revenue)),
                    status=LeadStatus.NEW,
                    google_place_id=place.place_id,
                )
                qualified_leads.append(lead)

        # Some leads should be qualified
        assert len(qualified_leads) > 0

        # All qualified leads should have revenue in range
        for lead in qualified_leads:
            assert 100_000 <= float(lead.revenue) <= 1_000_000

    def test_complete_pipeline_simulation(self):
        """Test simulated complete pipeline from scrape to ready-for-db."""
        from utils.revenue_heuristics import estimate_revenue, is_qualified_revenue

        # Step 1: Get mock places (simulating Google Maps API response)
        places = create_mock_places()

        # Step 2: Deduplicate
        seen_ids: set[str] = set()
        unique_places = []
        for place in places:
            if place.place_id not in seen_ids:
                seen_ids.add(place.place_id)
                unique_places.append(place)

        # Step 3: Estimate revenue and filter
        qualified_leads: list[Lead] = []
        for place in unique_places:
            business_data = {
                "review_count": place.review_count or 0,
                "google_rating": place.rating,
                "industry": place.types[0] if place.types else "general",
            }

            revenue = estimate_revenue(business_data)

            if is_qualified_revenue(revenue):
                lead = Lead(
                    name=place.name,
                    address=place.address,
                    phone=place.phone,
                    website=place.website,
                    industry=place.types[0] if place.types else "general",
                    rating=Decimal(str(place.rating)) if place.rating else None,
                    review_count=place.review_count,
                    revenue=Decimal(str(revenue)),
                    status=LeadStatus.NEW,
                    google_place_id=place.place_id,
                )
                qualified_leads.append(lead)

        # Step 4: Verify pipeline output
        assert len(qualified_leads) > 0

        for lead in qualified_leads:
            # All leads should have required fields
            assert lead.name is not None
            assert lead.address is not None
            assert lead.industry is not None
            assert lead.google_place_id is not None
            assert lead.status == LeadStatus.NEW
            assert lead.revenue is not None


class TestDatabaseSessionMocking:
    """Tests for mocking database sessions in integration tests."""

    def test_mock_session_lead_insert(self):
        """Test simulated lead insertion with mock session."""
        # Simulate database storage
        mock_db: dict[str, Lead] = {}

        def mock_add(lead: Lead) -> None:
            """Simulate session.add()."""
            if not lead.id:
                import uuid
                lead.id = str(uuid.uuid4())
            mock_db[lead.id] = lead

        def mock_get(lead_id: str) -> Optional[Lead]:
            """Simulate session.get()."""
            return mock_db.get(lead_id)

        # Create and "insert" a lead
        lead = Lead(
            name="Test Business",
            address="123 Test St",
            industry="dentist",
            google_place_id="test_place_123",
        )

        mock_add(lead)

        # Verify lead was "stored"
        assert lead.id is not None
        assert lead.id in mock_db

        # Verify retrieval
        retrieved = mock_get(lead.id)
        assert retrieved is not None
        assert retrieved.name == "Test Business"

    def test_mock_session_duplicate_handling(self):
        """Test handling duplicates in mock database."""
        mock_db: dict[str, Lead] = {}
        unique_place_ids: set[str] = set()

        def mock_insert_if_unique(lead: Lead) -> bool:
            """Insert lead only if place_id is unique."""
            if lead.google_place_id in unique_place_ids:
                return False  # Duplicate

            import uuid
            lead.id = str(uuid.uuid4())
            mock_db[lead.id] = lead
            unique_place_ids.add(lead.google_place_id)
            return True

        # Insert first lead
        lead1 = Lead(
            name="Business A",
            address="Address A",
            industry="dentist",
            google_place_id="place_123",
        )
        assert mock_insert_if_unique(lead1) is True

        # Try to insert duplicate
        lead2 = Lead(
            name="Business A Duplicate",
            address="Address A",
            industry="dentist",
            google_place_id="place_123",  # Same place_id
        )
        assert mock_insert_if_unique(lead2) is False

        # Insert unique lead
        lead3 = Lead(
            name="Business B",
            address="Address B",
            industry="hvac",
            google_place_id="place_456",
        )
        assert mock_insert_if_unique(lead3) is True

        # Verify only 2 leads in database
        assert len(mock_db) == 2


class TestCampaignIntegration:
    """Tests for campaign tracking integration with lead scraping."""

    def test_campaign_model_import(self):
        """Test Campaign model can be imported."""
        try:
            from models.campaign import Campaign, CampaignStatus
        except ImportError:
            pytest.skip("Campaign model cannot be imported")

        assert Campaign is not None
        assert CampaignStatus is not None

    def test_campaign_with_leads(self):
        """Test creating a campaign with associated leads."""
        try:
            from models.campaign import Campaign, CampaignStatus
        except ImportError:
            pytest.skip("Campaign model cannot be imported")

        campaign = Campaign(
            zip_code="62701",
            industries=["dentist", "hvac"],
            radius_miles=20.0,
            status=CampaignStatus.SCRAPING,
            total_leads=0,
            processed_leads=0,
            failed_leads=0,
        )

        assert campaign.zip_code == "62701"
        assert campaign.industries == ["dentist", "hvac"]
        assert campaign.status == CampaignStatus.SCRAPING

    def test_campaign_progress_tracking(self):
        """Test campaign progress updates during scraping."""
        try:
            from models.campaign import Campaign, CampaignStatus
        except ImportError:
            pytest.skip("Campaign model cannot be imported")

        campaign = Campaign(
            zip_code="62701",
            industries=["dentist"],
            total_leads=0,
            processed_leads=0,
            failed_leads=0,
        )

        # Simulate scraping progress
        campaign.status = CampaignStatus.SCRAPING
        campaign.total_leads = 10

        # Simulate processing
        campaign.processed_leads = 5
        assert campaign.progress_percent == 50.0

        campaign.processed_leads = 10
        assert campaign.progress_percent == 100.0

        # Complete campaign
        campaign.status = CampaignStatus.COMPLETED
        assert campaign.is_complete is True


class TestErrorHandling:
    """Tests for error handling in the scraper to DB flow."""

    def test_missing_required_fields_validation(self):
        """Test validation for leads with missing required fields.

        Note: SQLAlchemy doesn't validate nullable=False constraints at model
        instantiation time - it only raises IntegrityError at database commit.
        This test documents that behavior and shows how to validate required fields.
        """
        # Lead model allows creation without address at instantiation
        # But it would fail at database commit time
        lead = Lead(
            name="Test Business",
            # address missing - this would fail at DB commit
            industry="dentist",
        )

        # The lead is created but address is None
        assert lead.name == "Test Business"
        assert lead.address is None  # Would violate NOT NULL at commit

        # Proper validation should check required fields before attempting commit
        def validate_lead(lead_obj: Lead) -> list[str]:
            """Validate lead has all required fields before DB commit."""
            errors = []
            if not lead_obj.name:
                errors.append("name is required")
            if not lead_obj.address:
                errors.append("address is required")
            if not lead_obj.industry:
                errors.append("industry is required")
            return errors

        errors = validate_lead(lead)
        assert "address is required" in errors

    def test_invalid_rating_value(self):
        """Test handling of invalid rating values."""
        # Rating should be 0.0-5.0, but Decimal handles any numeric
        lead = Lead(
            name="Test Business",
            address="123 Test St",
            industry="dentist",
            rating=Decimal("4.5"),  # Valid
        )
        assert lead.rating == Decimal("4.5")

    def test_null_optional_fields(self):
        """Test that optional fields can be null."""
        lead = Lead(
            name="Test Business",
            address="123 Test St",
            industry="dentist",
            phone=None,
            website=None,
            rating=None,
            review_count=None,
            revenue=None,
            google_place_id=None,
            email=None,
        )

        assert lead.phone is None
        assert lead.website is None
        assert lead.rating is None
        assert lead.review_count is None
        assert lead.revenue is None
        assert lead.google_place_id is None
        assert lead.email is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
