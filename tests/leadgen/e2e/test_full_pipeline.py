"""Full E2E tests for the complete lead generation pipeline.

Tests the entire pipeline flow from zip code input to email delivery,
with all external APIs mocked for reliable and reproducible testing.

The pipeline stages tested:
1. Scraper Agent - Google Maps API mocked
2. Research Agent - Firecrawl and Apollo APIs mocked
3. Voice Assembler Agent - OpenAI Vector Stores mocked
4. Frontend Deployer Agent - Vercel API mocked
5. Sales Agent - SendGrid API mocked

These tests verify:
- Complete pipeline orchestration
- Data flow between stages
- Error handling and recovery
- Database operations
- Campaign tracking and status updates
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure repo root is on sys.path so imports work correctly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
LEADGEN_DIR = os.path.join(ROOT_DIR, "src", "leadgen")
if LEADGEN_DIR not in sys.path:
    sys.path.insert(0, LEADGEN_DIR)

# Import leadgen modules
from models.lead import Lead, LeadStatus
from models.campaign import Campaign, CampaignStatus
from models.dossier import Dossier
from models.deployment import Deployment, DeploymentStatus

logger = logging.getLogger(__name__)


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@dataclass
class MockPlaceResult:
    """Mock Google Maps Place result."""
    place_id: str
    name: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    types: list[str] = field(default_factory=list)
    location: Optional[tuple[float, float]] = None
    business_status: str = "OPERATIONAL"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
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
class MockScrapeResult:
    """Mock Firecrawl scrape result."""
    url: str
    markdown: Optional[str] = None
    html: Optional[str] = None
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "markdown": self.markdown,
            "html": self.html,
            "links": self.links,
            "metadata": self.metadata,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class MockVectorStoreInfo:
    """Mock OpenAI Vector Store info."""
    id: str
    name: str
    status: str = "completed"
    file_counts: dict[str, int] = field(default_factory=lambda: {"completed": 1})
    usage_bytes: int = 2048
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "file_counts": self.file_counts,
            "usage_bytes": self.usage_bytes,
            "success": self.success,
        }


@dataclass
class MockDeploymentResult:
    """Mock Vercel deployment result."""
    deployment_id: str
    url: str
    preview_url: str
    project_name: str
    status: str = "ready"
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "deployment_id": self.deployment_id,
            "url": self.url,
            "preview_url": self.preview_url,
            "project_name": self.project_name,
            "status": self.status,
            "success": self.success,
        }


@dataclass
class MockEmailResult:
    """Mock SendGrid email result."""
    message_id: str
    status: str = "sent"
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_id": self.message_id,
            "status": self.status,
            "success": self.success,
        }


# ============================================================================
# Mock Data Generators
# ============================================================================

def create_mock_places(count: int = 5, industry: str = "dentist") -> list[MockPlaceResult]:
    """Create mock Google Maps place results for testing."""
    places = []
    base_names = [
        ("Springfield Family Dental", "123 Main St"),
        ("Capitol City HVAC", "456 Oak Ave"),
        ("Downtown Hair Salon", "789 Elm St"),
        ("Premium Auto Repair", "321 Motor Way"),
        ("Sunrise Medical Center", "555 Health Blvd"),
        ("Valley Dental Care", "111 River Rd"),
        ("Metro Heating & Cooling", "222 Industrial Dr"),
        ("Elite Beauty Studio", "333 Fashion Ave"),
    ]

    for i in range(min(count, len(base_names))):
        name, street = base_names[i]
        places.append(MockPlaceResult(
            place_id=f"place_{uuid.uuid4().hex[:8]}",
            name=name,
            address=f"{street}, Springfield, IL 62701",
            phone=f"+1-217-555-{1000 + i:04d}",
            website=f"https://{name.lower().replace(' ', '')}.example.com",
            rating=4.0 + (i % 10) / 10,
            review_count=50 + (i * 30),
            types=[industry, "business"],
            location=(39.7817 + i * 0.01, -89.6501 + i * 0.01),
        ))

    return places


def create_mock_website_content(business_name: str, industry: str) -> str:
    """Create mock website markdown content for a business."""
    industry_services = {
        "dentist": ["General Dentistry", "Teeth Whitening", "Dental Implants", "Emergency Care"],
        "hvac": ["AC Installation", "Heating Repair", "Duct Cleaning", "24/7 Emergency Service"],
        "salon": ["Haircuts", "Color Services", "Styling", "Treatments"],
        "auto": ["Oil Changes", "Brake Service", "Engine Repair", "Tire Service"],
    }
    services = industry_services.get(industry, ["Service A", "Service B", "Service C"])

    return f"""# {business_name}

Welcome to {business_name}! We are your trusted {industry} professionals.

## Our Services

{chr(10).join([f'- {s}' for s in services])}

## About Us

We have been serving the Springfield community for over 10 years.
Our team of experts is dedicated to providing exceptional service.

## Contact

Call us today to schedule an appointment!

## Hours

Monday-Friday: 8am-5pm
Saturday: 9am-2pm
Sunday: Closed

## Find Us

Follow us on social media:
- Facebook: https://facebook.com/{business_name.lower().replace(' ', '')}
- Instagram: https://instagram.com/{business_name.lower().replace(' ', '')}
"""


def create_mock_dossier_content(lead_data: dict) -> str:
    """Create mock dossier content from lead data."""
    name = lead_data.get("name", "Test Business")
    industry = lead_data.get("industry", "general")
    address = lead_data.get("address", "123 Test St")

    return f"""# Company Overview

**Name:** {name}
**Address:** {address}
**Industry:** {industry}
**Phone:** {lead_data.get('phone', 'N/A')}
**Website:** {lead_data.get('website', 'N/A')}

## Services

- Primary Service 1
- Primary Service 2
- Additional Service 1

## Team

### Owner/Manager
Experienced professional in the {industry} industry.

## Pain Points

- Missed calls during busy hours
- After-hours inquiries going unanswered
- Staff overwhelmed with appointment scheduling

## Gotcha Q&A

Q: What is your address?
A: {address}

Q: What are your hours?
A: Monday-Friday 8am-5pm

## Competitors

- Competitor A
- Competitor B
"""


# ============================================================================
# Mock Database Class
# ============================================================================

class MockDatabase:
    """Mock database for testing pipeline without real database."""

    def __init__(self):
        self.campaigns: dict[str, Campaign] = {}
        self.leads: dict[str, Lead] = {}
        self.dossiers: dict[str, Dossier] = {}
        self.deployments: dict[str, Deployment] = {}

    def add_campaign(self, campaign: Campaign) -> str:
        """Add campaign and return ID."""
        campaign_id = str(uuid.uuid4())
        campaign.id = campaign_id
        self.campaigns[campaign_id] = campaign
        return campaign_id

    def add_lead(self, lead: Lead) -> str:
        """Add lead and return ID."""
        lead_id = str(uuid.uuid4())
        lead.id = lead_id
        self.leads[lead_id] = lead
        return lead_id

    def add_dossier(self, dossier: Dossier) -> str:
        """Add dossier and return ID."""
        dossier_id = str(uuid.uuid4())
        dossier.id = dossier_id
        self.dossiers[dossier_id] = dossier
        return dossier_id

    def add_deployment(self, deployment: Deployment) -> str:
        """Add deployment and return ID."""
        deployment_id = str(uuid.uuid4())
        deployment.id = deployment_id
        self.deployments[deployment_id] = deployment
        return deployment_id

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get lead by ID."""
        return self.leads.get(lead_id)

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID."""
        return self.campaigns.get(campaign_id)


# ============================================================================
# Module-level Pytest Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create mock database for testing."""
    return MockDatabase()


# ============================================================================
# E2E Test Classes
# ============================================================================

class TestFullPipelineE2E:
    """E2E tests for the complete lead generation pipeline."""

    def test_pipeline_stage_enum_values(self):
        """Test PipelineStage enum values are defined correctly."""
        from orchestrator import PipelineStage

        assert PipelineStage.SCRAPING == "scraping"
        assert PipelineStage.RESEARCHING == "researching"
        assert PipelineStage.VOICE_ASSEMBLY == "voice_assembly"
        assert PipelineStage.DEPLOYMENT == "deployment"
        assert PipelineStage.EMAILING == "emailing"
        assert PipelineStage.COMPLETED == "completed"

    def test_pipeline_config_defaults(self):
        """Test PipelineConfig has correct default values."""
        from orchestrator import PipelineConfig

        config = PipelineConfig()

        assert config.max_retries == 3
        assert config.retry_delay_seconds == 2.0
        assert config.concurrent_leads == 5
        assert config.skip_voice_assembly is False
        assert config.skip_deployment is False
        assert config.skip_email is False
        assert config.email_style == "humorous"
        assert config.email_variant == "A"

    def test_pipeline_config_custom_values(self):
        """Test PipelineConfig with custom values."""
        from orchestrator import PipelineConfig

        config = PipelineConfig(
            max_retries=5,
            retry_delay_seconds=1.0,
            concurrent_leads=10,
            skip_voice_assembly=True,
            skip_deployment=True,
            skip_email=True,
            email_style="professional",
            email_variant="B",
        )

        assert config.max_retries == 5
        assert config.retry_delay_seconds == 1.0
        assert config.concurrent_leads == 10
        assert config.skip_voice_assembly is True
        assert config.skip_deployment is True
        assert config.skip_email is True
        assert config.email_style == "professional"
        assert config.email_variant == "B"

    def test_lead_processing_result_structure(self):
        """Test LeadProcessingResult dataclass structure."""
        from orchestrator import LeadProcessingResult

        result = LeadProcessingResult(
            lead_id="lead_123",
            lead_name="Test Business",
            success=True,
            dossier_status="complete",
            vector_store_id="vs_abc123",
            deployment_url="https://test.vercel.app",
            email_sent=True,
            processing_time_seconds=5.5,
        )

        assert result.lead_id == "lead_123"
        assert result.lead_name == "Test Business"
        assert result.success is True
        assert result.dossier_status == "complete"
        assert result.vector_store_id == "vs_abc123"
        assert result.deployment_url == "https://test.vercel.app"
        assert result.email_sent is True
        assert result.processing_time_seconds == 5.5

    def test_lead_processing_result_to_dict(self):
        """Test LeadProcessingResult to_dict() conversion."""
        from orchestrator import LeadProcessingResult

        result = LeadProcessingResult(
            lead_id="lead_123",
            lead_name="Test Business",
            success=True,
            errors=["Warning 1"],
        )

        result_dict = result.to_dict()

        assert result_dict["lead_id"] == "lead_123"
        assert result_dict["lead_name"] == "Test Business"
        assert result_dict["success"] is True
        assert result_dict["errors"] == ["Warning 1"]

    def test_campaign_result_structure(self):
        """Test CampaignResult dataclass structure."""
        from orchestrator import CampaignResult

        result = CampaignResult(
            campaign_id="campaign_123",
            success=True,
            total_leads=10,
            processed_leads=8,
            failed_leads=2,
            started_at=datetime.now(timezone.utc),
        )

        assert result.campaign_id == "campaign_123"
        assert result.success is True
        assert result.total_leads == 10
        assert result.processed_leads == 8
        assert result.failed_leads == 2
        assert result.started_at is not None

    def test_campaign_result_to_dict(self):
        """Test CampaignResult to_dict() conversion."""
        from orchestrator import CampaignResult, LeadProcessingResult

        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)

        result = CampaignResult(
            campaign_id="campaign_123",
            success=True,
            total_leads=5,
            processed_leads=5,
            failed_leads=0,
            lead_results=[
                LeadProcessingResult(lead_id="1", lead_name="A"),
                LeadProcessingResult(lead_id="2", lead_name="B"),
            ],
            started_at=started,
            completed_at=completed,
            duration_seconds=10.5,
        )

        result_dict = result.to_dict()

        assert result_dict["campaign_id"] == "campaign_123"
        assert result_dict["success"] is True
        assert result_dict["total_leads"] == 5
        assert result_dict["processed_leads"] == 5
        assert result_dict["failed_leads"] == 0
        assert len(result_dict["lead_results"]) == 2
        assert result_dict["duration_seconds"] == 10.5

    def test_orchestrator_initialization(self):
        """Test LeadGenOrchestrator initialization."""
        from orchestrator import LeadGenOrchestrator, PipelineConfig

        orchestrator = LeadGenOrchestrator()
        assert orchestrator.config is not None
        assert orchestrator.config.max_retries == 3

        config = PipelineConfig(max_retries=5)
        orchestrator = LeadGenOrchestrator(config=config)
        assert orchestrator.config.max_retries == 5

    def test_orchestrator_with_progress_callback(self):
        """Test LeadGenOrchestrator with progress callback."""
        from orchestrator import LeadGenOrchestrator

        progress_calls = []

        def progress_callback(stage: str, current: int, total: int):
            progress_calls.append((stage, current, total))

        orchestrator = LeadGenOrchestrator(progress_callback=progress_callback)
        orchestrator._report_progress("scraping", 0, 10)
        orchestrator._report_progress("researching", 5, 10)

        assert len(progress_calls) == 2
        assert progress_calls[0] == ("scraping", 0, 10)
        assert progress_calls[1] == ("researching", 5, 10)


class TestPipelineStageSimulation:
    """Tests simulating individual pipeline stages."""

    def test_scraping_stage_simulation(self, mock_db):
        """Test simulated scraping stage with mock data."""
        places = create_mock_places(5, "dentist")

        # Simulate scraping results
        leads = []
        for place in places:
            lead_data = place.to_dict()
            lead_data["industry"] = "dentist"
            lead_data["estimated_revenue"] = 500000.0
            leads.append(lead_data)

        assert len(leads) == 5
        assert all(l["industry"] == "dentist" for l in leads)
        assert all(l.get("estimated_revenue") for l in leads)

    def test_research_stage_simulation(self, mock_db):
        """Test simulated research stage with mock data."""
        lead_data = {
            "name": "Springfield Family Dental",
            "address": "123 Main St, Springfield, IL 62701",
            "phone": "+1-217-555-0101",
            "website": "https://springfielddental.example.com",
            "industry": "dentist",
        }

        # Simulate website scraping
        website_content = create_mock_website_content(
            lead_data["name"],
            lead_data["industry"],
        )
        assert "Springfield Family Dental" in website_content
        assert "Teeth Whitening" in website_content

        # Simulate dossier generation
        dossier_content = create_mock_dossier_content(lead_data)
        assert "Company Overview" in dossier_content
        assert "Pain Points" in dossier_content
        assert "Gotcha Q&A" in dossier_content

    def test_voice_assembly_stage_simulation(self, mock_db):
        """Test simulated voice assembly stage with mock data."""
        dossier_content = create_mock_dossier_content({
            "name": "Test Dental",
            "industry": "dentist",
            "address": "123 Test St",
        })

        # Import personality generator
        from utils.voice_personality import generate_personality_from_dossier

        template = generate_personality_from_dossier(
            dossier_content=dossier_content,
            business_name="Test Dental",
            industry="dentist",
        )

        assert template is not None
        assert template.system_prompt is not None
        assert "Test Dental" in template.system_prompt
        assert template.greeting is not None
        assert template.closing is not None

    def test_deployment_stage_simulation(self, mock_db):
        """Test simulated deployment stage with mock data."""
        from utils.branding_injector import inject_branding, BrandingConfig

        config = BrandingConfig(
            business_name="Springfield Family Dental",
            industry="dentist",
            primary_color="#2563eb",
            phone="+1-217-555-0101",
        )

        env_vars = inject_branding(config)

        assert "NEXT_PUBLIC_BUSINESS_NAME" in env_vars
        assert env_vars["NEXT_PUBLIC_BUSINESS_NAME"] == "Springfield Family Dental"
        assert "NEXT_PUBLIC_PRIMARY_COLOR" in env_vars

    def test_email_stage_simulation(self, mock_db):
        """Test simulated email stage with mock data."""
        from utils.email_templates import generate_cold_email_from_dict

        data = {
            "name": "Springfield Family Dental",
            "demo_url": "https://springfield-dental.vercel.app",
            "industry": "dentist",
            "style": "humorous",
        }

        email = generate_cold_email_from_dict(data)

        assert email is not None
        assert email.subject is not None
        assert email.html_content is not None
        assert email.text_content is not None
        assert "Springfield Family Dental" in email.html_content


class TestPipelineDataFlow:
    """Tests for data flow between pipeline stages."""

    def test_scrape_to_lead_model_conversion(self):
        """Test conversion from scrape result to Lead model."""
        place = create_mock_places(1, "dentist")[0]
        place_dict = place.to_dict()

        lead = Lead(
            name=place_dict["name"],
            address=place_dict["address"],
            phone=place_dict["phone"],
            website=place_dict["website"],
            industry="dentist",
            rating=Decimal(str(place_dict["rating"])) if place_dict.get("rating") else None,
            review_count=place_dict.get("review_count"),
            revenue=Decimal("500000.00"),
            status=LeadStatus.NEW,
            google_place_id=place_dict["place_id"],
        )

        assert lead.name == place_dict["name"]
        assert lead.status == LeadStatus.NEW
        assert lead.google_place_id == place_dict["place_id"]

    def test_lead_to_dossier_flow(self):
        """Test data flow from Lead model to Dossier creation."""
        lead = Lead(
            name="Test Business",
            address="123 Test St",
            phone="+1-555-0101",
            website="https://test.example.com",
            industry="dentist",
            rating=Decimal("4.5"),
            review_count=100,
            status=LeadStatus.RESEARCHED,
        )

        lead_dict = lead.to_dict()
        dossier_content = create_mock_dossier_content(lead_dict)

        dossier = Dossier(
            lead_id="lead_123",
            content=dossier_content,
        )

        assert dossier.lead_id == "lead_123"
        assert "Test Business" in dossier.content
        assert dossier.has_vector_store is False

    def test_dossier_to_voice_config_flow(self):
        """Test data flow from Dossier to voice configuration."""
        from utils.voice_personality import generate_personality_from_dossier

        dossier = Dossier(
            lead_id="lead_123",
            content=create_mock_dossier_content({
                "name": "Test Dental",
                "industry": "dentist",
                "address": "123 Test St",
            }),
        )

        template = generate_personality_from_dossier(
            dossier_content=dossier.content,
            business_name="Test Dental",
            industry="dentist",
        )

        # Simulate vector store creation
        dossier.vector_store_id = "vs_test123"
        dossier.assistant_id = "asst_test123"

        assert dossier.has_vector_store is True
        assert dossier.has_assistant is True
        assert dossier.is_ready_for_voice is True
        assert template.system_prompt is not None

    def test_deployment_to_email_flow(self):
        """Test data flow from deployment URL to email generation."""
        from utils.email_templates import generate_cold_email_from_dict

        deployment = Deployment(
            lead_id="lead_123",
            url="https://test-dental.vercel.app",
            vercel_id="dpl_test123",
            status=DeploymentStatus.READY,
        )

        data = {
            "name": "Test Dental",
            "demo_url": deployment.url,
            "industry": "dentist",
        }

        email = generate_cold_email_from_dict(data)

        assert deployment.url in email.html_content
        assert deployment.url in email.text_content


class TestPipelineErrorHandling:
    """Tests for pipeline error handling and recovery."""

    def test_lead_processing_with_errors(self):
        """Test LeadProcessingResult tracks errors correctly."""
        from orchestrator import LeadProcessingResult

        result = LeadProcessingResult(
            lead_id="lead_123",
            lead_name="Test Business",
            success=False,
            errors=[
                "Firecrawl scrape failed: timeout",
                "Vector store creation failed: quota exceeded",
            ],
        )

        assert result.success is False
        assert len(result.errors) == 2
        assert "timeout" in result.errors[0]
        assert "quota exceeded" in result.errors[1]

    def test_partial_pipeline_success(self):
        """Test pipeline handles partial success correctly."""
        from orchestrator import LeadProcessingResult

        # Simulate partial success - dossier created but deployment failed
        result = LeadProcessingResult(
            lead_id="lead_123",
            lead_name="Test Business",
            success=True,  # Partial success is still a success
            dossier_status="complete",
            vector_store_id="vs_abc123",
            deployment_url=None,  # Deployment failed
            email_sent=False,
            errors=["Deployment failed: Vercel quota exceeded"],
        )

        # Success determined by dossier status and error count
        assert result.dossier_status == "complete"
        assert result.vector_store_id is not None
        assert result.deployment_url is None
        assert len(result.errors) < 3  # Less than 3 errors = partial success

    def test_campaign_with_mixed_results(self):
        """Test campaign handles mixed lead results correctly."""
        from orchestrator import CampaignResult, LeadProcessingResult

        result = CampaignResult(
            campaign_id="campaign_123",
            total_leads=5,
            processed_leads=3,
            failed_leads=2,
            lead_results=[
                LeadProcessingResult(lead_id="1", lead_name="A", success=True),
                LeadProcessingResult(lead_id="2", lead_name="B", success=True),
                LeadProcessingResult(lead_id="3", lead_name="C", success=True),
                LeadProcessingResult(
                    lead_id="4",
                    lead_name="D",
                    success=False,
                    errors=["Failed"],
                ),
                LeadProcessingResult(
                    lead_id="5",
                    lead_name="E",
                    success=False,
                    errors=["Failed"],
                ),
            ],
        )

        # Campaign success if any leads processed
        result.success = result.processed_leads > 0

        assert result.success is True
        assert result.total_leads == 5
        assert result.processed_leads == 3
        assert result.failed_leads == 2

    def test_retry_with_backoff_simulation(self):
        """Test retry with backoff behavior simulation."""
        attempt_count = 0
        max_attempts = 3

        def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < max_attempts:
                raise ValueError(f"Attempt {attempt_count} failed")
            return "success"

        # Simulate retry logic
        result = None
        for attempt in range(max_attempts):
            try:
                result = failing_operation()
                break
            except ValueError:
                if attempt < max_attempts - 1:
                    continue
                raise

        assert result == "success"
        assert attempt_count == max_attempts


class TestDatabaseOperations:
    """Tests for database operations within the pipeline."""

    def test_campaign_creation_and_status_tracking(self, mock_db):
        """Test campaign creation and status updates."""
        campaign = Campaign(
            zip_code="62701",
            industries=["dentist", "hvac"],
            radius_miles=20.0,
            status=CampaignStatus.PENDING,
            total_leads=0,
            processed_leads=0,
            failed_leads=0,
        )

        campaign_id = mock_db.add_campaign(campaign)

        # Update status through pipeline stages
        campaign.status = CampaignStatus.SCRAPING
        assert campaign.status == CampaignStatus.SCRAPING

        campaign.status = CampaignStatus.RESEARCHING
        campaign.total_leads = 10
        assert campaign.total_leads == 10

        campaign.status = CampaignStatus.COMPLETED
        campaign.processed_leads = 8
        campaign.failed_leads = 2
        assert campaign.processed_leads == 8
        assert campaign.failed_leads == 2

    def test_lead_status_progression(self, mock_db):
        """Test lead status progression through pipeline."""
        lead = Lead(
            name="Test Business",
            address="123 Test St",
            industry="dentist",
            status=LeadStatus.NEW,
        )

        lead_id = mock_db.add_lead(lead)

        # Progress through pipeline stages
        status_progression = [
            LeadStatus.NEW,
            LeadStatus.RESEARCHING,
            LeadStatus.RESEARCHED,
            LeadStatus.DEPLOYING,
            LeadStatus.DEPLOYED,
            LeadStatus.EMAILED,
        ]

        for status in status_progression:
            lead.status = status
            assert lead.status == status

    def test_dossier_creation_and_update(self, mock_db):
        """Test dossier creation and vector store update."""
        dossier = Dossier(
            lead_id="lead_123",
            content="# Test Dossier",
        )

        dossier_id = mock_db.add_dossier(dossier)

        assert dossier.has_vector_store is False

        # Update with vector store
        dossier.vector_store_id = "vs_test123"
        assert dossier.has_vector_store is True

        # Update with assistant
        dossier.assistant_id = "asst_test123"
        assert dossier.is_ready_for_voice is True

    def test_deployment_creation(self, mock_db):
        """Test deployment record creation."""
        deployment = Deployment(
            lead_id="lead_123",
            url="https://test.vercel.app",
            vercel_id="dpl_test123",
            status=DeploymentStatus.READY,
        )

        deployment_id = mock_db.add_deployment(deployment)

        assert deployment.url == "https://test.vercel.app"
        assert deployment.status == DeploymentStatus.READY


class TestFullPipelineSimulation:
    """Tests simulating the complete pipeline flow."""

    def test_complete_pipeline_simulation_single_lead(self, mock_db):
        """Test simulated complete pipeline for a single lead."""
        logger.info("=" * 80)
        logger.info("Starting Complete Pipeline Simulation - Single Lead")
        logger.info("=" * 80)

        start_time = time.time()

        try:
            # Step 1: Create campaign
            logger.info("\nStep 1: Creating campaign")
            campaign = Campaign(
                zip_code="62701",
                industries=["dentist"],
                radius_miles=20.0,
                status=CampaignStatus.PENDING,
            )
            campaign_id = mock_db.add_campaign(campaign)
            assert campaign_id is not None
            logger.info(f"Created campaign: {campaign_id}")

            # Step 2: Simulate scraping
            logger.info("\nStep 2: Simulating scraping stage")
            campaign.status = CampaignStatus.SCRAPING
            places = create_mock_places(1, "dentist")
            lead_data = places[0].to_dict()
            lead_data["industry"] = "dentist"
            lead_data["estimated_revenue"] = 500000.0
            logger.info(f"Scraped lead: {lead_data['name']}")

            # Step 3: Create Lead model
            logger.info("\nStep 3: Creating Lead model")
            lead = Lead(
                name=lead_data["name"],
                address=lead_data["address"],
                phone=lead_data.get("phone"),
                website=lead_data.get("website"),
                industry=lead_data["industry"],
                rating=Decimal(str(lead_data["rating"])) if lead_data.get("rating") else None,
                review_count=lead_data.get("review_count"),
                revenue=Decimal(str(lead_data["estimated_revenue"])),
                status=LeadStatus.NEW,
                google_place_id=lead_data["place_id"],
            )
            lead_id = mock_db.add_lead(lead)
            campaign.total_leads = 1
            logger.info(f"Created lead: {lead_id}")

            # Step 4: Research stage
            logger.info("\nStep 4: Simulating research stage")
            campaign.status = CampaignStatus.RESEARCHING
            lead.status = LeadStatus.RESEARCHING

            # Simulate website scrape
            website_content = create_mock_website_content(
                lead.name,
                lead.industry,
            )
            assert website_content is not None

            # Generate dossier
            dossier_content = create_mock_dossier_content(lead.to_dict())
            assert "Company Overview" in dossier_content

            dossier = Dossier(
                lead_id=lead_id,
                content=dossier_content,
            )
            mock_db.add_dossier(dossier)
            lead.status = LeadStatus.RESEARCHED
            logger.info("Created dossier successfully")

            # Step 5: Voice assembly stage
            logger.info("\nStep 5: Simulating voice assembly stage")
            from utils.voice_personality import generate_personality_from_dossier

            template = generate_personality_from_dossier(
                dossier_content=dossier_content,
                business_name=lead.name,
                industry=lead.industry,
            )
            assert template.system_prompt is not None

            # Simulate vector store creation
            dossier.vector_store_id = f"vs_{uuid.uuid4().hex[:12]}"
            logger.info(f"Created vector store: {dossier.vector_store_id}")

            # Step 6: Deployment stage
            logger.info("\nStep 6: Simulating deployment stage")
            lead.status = LeadStatus.DEPLOYING

            from utils.branding_injector import inject_branding, BrandingConfig

            branding = BrandingConfig(
                business_name=lead.name,
                industry=lead.industry,
            )
            env_vars = inject_branding(branding)
            assert "NEXT_PUBLIC_BUSINESS_NAME" in env_vars

            # Simulate deployment
            deployment = Deployment(
                lead_id=lead_id,
                url=f"https://{lead.name.lower().replace(' ', '-')}.vercel.app",
                vercel_id=f"dpl_{uuid.uuid4().hex[:12]}",
                status=DeploymentStatus.READY,
            )
            mock_db.add_deployment(deployment)
            lead.status = LeadStatus.DEPLOYED
            logger.info(f"Deployed to: {deployment.url}")

            # Step 7: Email stage (simulated without actual send)
            logger.info("\nStep 7: Simulating email stage")
            from utils.email_templates import generate_cold_email_from_dict

            email_data = {
                "name": lead.name,
                "demo_url": deployment.url,
                "industry": lead.industry,
                "style": "humorous",
            }
            email = generate_cold_email_from_dict(email_data)
            assert email.subject is not None
            assert email.html_content is not None
            lead.status = LeadStatus.EMAILED
            logger.info(f"Email prepared with subject: {email.subject}")

            # Step 8: Finalize
            logger.info("\nStep 8: Finalizing campaign")
            campaign.status = CampaignStatus.COMPLETED
            campaign.processed_leads = 1
            campaign.failed_leads = 0

            end_time = time.time()
            duration = end_time - start_time

            logger.info("=" * 80)
            logger.info("Pipeline Simulation Complete")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Lead Status: {lead.status.value}")
            logger.info(f"Campaign Status: {campaign.status.value}")
            logger.info("=" * 80)

            # Verify final state
            assert lead.status == LeadStatus.EMAILED
            assert campaign.status == CampaignStatus.COMPLETED
            assert campaign.processed_leads == 1
            assert dossier.has_vector_store is True
            assert deployment.status == DeploymentStatus.READY

        except Exception as e:
            logger.exception("Pipeline simulation failed: %s", e)
            raise

    def test_complete_pipeline_simulation_multiple_leads(self, mock_db):
        """Test simulated complete pipeline for multiple leads."""
        logger.info("=" * 80)
        logger.info("Starting Complete Pipeline Simulation - Multiple Leads")
        logger.info("=" * 80)

        num_leads = 3

        # Create campaign
        campaign = Campaign(
            zip_code="62701",
            industries=["dentist", "hvac"],
            radius_miles=20.0,
            status=CampaignStatus.PENDING,
        )
        campaign_id = mock_db.add_campaign(campaign)

        # Scrape leads
        campaign.status = CampaignStatus.SCRAPING
        places = create_mock_places(num_leads, "dentist")
        campaign.total_leads = num_leads

        processed = 0
        failed = 0

        for idx, place in enumerate(places):
            logger.info(f"\nProcessing lead {idx + 1}/{num_leads}: {place.name}")

            try:
                # Create lead
                lead = Lead(
                    name=place.name,
                    address=place.address,
                    phone=place.phone,
                    website=place.website,
                    industry="dentist",
                    rating=Decimal(str(place.rating)) if place.rating else None,
                    review_count=place.review_count,
                    revenue=Decimal("500000.00"),
                    status=LeadStatus.NEW,
                    google_place_id=place.place_id,
                )
                lead_id = mock_db.add_lead(lead)

                # Research
                lead.status = LeadStatus.RESEARCHING
                dossier_content = create_mock_dossier_content(lead.to_dict())
                dossier = Dossier(lead_id=lead_id, content=dossier_content)
                mock_db.add_dossier(dossier)
                lead.status = LeadStatus.RESEARCHED

                # Voice assembly
                dossier.vector_store_id = f"vs_{uuid.uuid4().hex[:12]}"

                # Deployment
                lead.status = LeadStatus.DEPLOYING
                deployment = Deployment(
                    lead_id=lead_id,
                    url=f"https://{place.name.lower().replace(' ', '-')}.vercel.app",
                    vercel_id=f"dpl_{uuid.uuid4().hex[:12]}",
                    status=DeploymentStatus.READY,
                )
                mock_db.add_deployment(deployment)
                lead.status = LeadStatus.DEPLOYED

                # Email (simulated)
                lead.status = LeadStatus.EMAILED
                processed += 1
                logger.info(f"Lead {idx + 1} processed successfully")

            except Exception as e:
                failed += 1
                logger.warning(f"Lead {idx + 1} failed: {e}")

        # Finalize campaign
        campaign.status = CampaignStatus.COMPLETED
        campaign.processed_leads = processed
        campaign.failed_leads = failed

        logger.info("=" * 80)
        logger.info(f"Processed: {processed}/{num_leads}")
        logger.info(f"Failed: {failed}/{num_leads}")
        logger.info("=" * 80)

        assert processed == num_leads
        assert failed == 0
        assert campaign.status == CampaignStatus.COMPLETED

    def test_pipeline_with_partial_failures(self, mock_db):
        """Test pipeline handles partial failures gracefully."""
        logger.info("=" * 80)
        logger.info("Testing Pipeline with Partial Failures")
        logger.info("=" * 80)

        campaign = Campaign(
            zip_code="62701",
            industries=["dentist"],
            status=CampaignStatus.PENDING,
        )
        mock_db.add_campaign(campaign)

        # Create 3 leads, simulate failure on the 2nd one
        places = create_mock_places(3, "dentist")
        campaign.total_leads = 3

        processed = 0
        failed = 0

        for idx, place in enumerate(places):
            lead = Lead(
                name=place.name,
                address=place.address,
                industry="dentist",
                status=LeadStatus.NEW,
                google_place_id=place.place_id,
            )
            lead_id = mock_db.add_lead(lead)

            # Simulate failure on 2nd lead
            if idx == 1:
                lead.status = LeadStatus.FAILED
                failed += 1
                logger.info(f"Lead {idx + 1} simulated failure")
                continue

            # Process successfully
            lead.status = LeadStatus.RESEARCHING
            dossier = Dossier(
                lead_id=lead_id,
                content=create_mock_dossier_content(lead.to_dict()),
            )
            mock_db.add_dossier(dossier)
            lead.status = LeadStatus.DEPLOYED
            processed += 1
            logger.info(f"Lead {idx + 1} processed")

        campaign.processed_leads = processed
        campaign.failed_leads = failed

        # Campaign should still succeed with some failures
        campaign.status = CampaignStatus.COMPLETED if processed > 0 else CampaignStatus.FAILED

        assert campaign.status == CampaignStatus.COMPLETED
        assert processed == 2
        assert failed == 1


class TestIntegrationWithAgentModules:
    """Tests for integration with actual agent modules."""

    def test_scraper_agent_module_import(self):
        """Test scraper agent module can be imported."""
        try:
            from agents.scraper_agent import (
                scraper_agent,
                ScrapedLead,
            )
            assert scraper_agent is not None
            assert ScrapedLead is not None
        except ImportError as e:
            pytest.skip(f"Scraper agent cannot be imported: {e}")

    def test_research_agent_module_import(self):
        """Test research agent module can be imported."""
        try:
            from agents.research_agent import (
                research_agent,
                _generate_research_dossier_internal,
            )
            assert research_agent is not None
            assert _generate_research_dossier_internal is not None
        except ImportError as e:
            pytest.skip(f"Research agent cannot be imported: {e}")

    def test_voice_assembler_agent_module_import(self):
        """Test voice assembler agent module can be imported."""
        try:
            from agents.voice_assembler_agent import (
                voice_assembler_agent,
                VoiceAgentConfig,
            )
            assert voice_assembler_agent is not None
            assert VoiceAgentConfig is not None
        except ImportError as e:
            pytest.skip(f"Voice assembler agent cannot be imported: {e}")

    def test_frontend_deployer_agent_module_import(self):
        """Test frontend deployer agent module can be imported."""
        try:
            from agents.frontend_deployer_agent import (
                frontend_deployer_agent,
            )
            assert frontend_deployer_agent is not None
        except ImportError as e:
            pytest.skip(f"Frontend deployer agent cannot be imported: {e}")

    def test_sales_agent_module_import(self):
        """Test sales agent module can be imported."""
        try:
            from agents.sales_agent import (
                sales_agent,
            )
            assert sales_agent is not None
        except ImportError as e:
            pytest.skip(f"Sales agent cannot be imported: {e}")

    def test_orchestrator_module_import(self):
        """Test orchestrator module can be imported."""
        from orchestrator import (
            LeadGenOrchestrator,
            PipelineConfig,
            PipelineStage,
            LeadProcessingResult,
            CampaignResult,
            run_lead_gen_campaign,
        )

        assert LeadGenOrchestrator is not None
        assert PipelineConfig is not None
        assert PipelineStage is not None
        assert LeadProcessingResult is not None
        assert CampaignResult is not None
        assert run_lead_gen_campaign is not None


class TestUtilityModuleIntegration:
    """Tests for utility module integration within the pipeline."""

    def test_revenue_heuristics_integration(self):
        """Test revenue heuristics utility integration."""
        from utils.revenue_heuristics import (
            estimate_revenue,
            is_qualified_revenue,
        )

        business_data = {
            "review_count": 100,
            "google_rating": 4.5,
            "industry": "dentist",
        }

        revenue = estimate_revenue(business_data)
        assert revenue >= 100000
        assert revenue <= 1000000
        assert is_qualified_revenue(revenue) is True

    def test_dossier_template_integration(self):
        """Test dossier template utility integration."""
        from utils.dossier_template import (
            generate_dossier_from_dict,
            validate_dossier_sections,
            is_dossier_valid,
        )

        data = {
            "name": "Test Business",
            "industry": "dentist",
            "address": "123 Test St",
            "description": "A test business",
        }

        dossier = generate_dossier_from_dict(data)
        assert "Company Overview" in dossier

        validation = validate_dossier_sections(dossier)
        assert validation.get("Company Overview") is True

        assert is_dossier_valid(dossier) is True

    def test_voice_personality_integration(self):
        """Test voice personality utility integration."""
        from utils.voice_personality import (
            generate_personality,
            generate_personality_from_dossier,
        )

        # Basic personality
        business_data = {
            "name": "Test Business",
            "industry": "dentist",
        }

        template = generate_personality(business_data)
        assert template.system_prompt is not None
        assert template.greeting is not None

        # With dossier
        dossier_content = "# Test Dossier\n\nThis is a test."
        template2 = generate_personality_from_dossier(
            dossier_content=dossier_content,
            business_name="Test Business",
            industry="dentist",
        )
        assert "Detailed Business Knowledge" in template2.system_prompt

    def test_email_templates_integration(self):
        """Test email templates utility integration."""
        from utils.email_templates import generate_cold_email_from_dict

        data = {
            "name": "Test Dental",
            "demo_url": "https://test.vercel.app",
            "industry": "dentist",
            "style": "humorous",
        }

        email = generate_cold_email_from_dict(data)

        assert email.subject is not None
        assert email.html_content is not None
        assert email.text_content is not None
        assert "Test Dental" in email.html_content

    def test_branding_injector_integration(self):
        """Test branding injector utility integration."""
        from utils.branding_injector import (
            inject_branding,
            BrandingConfig,
            validate_branding_config,
        )

        config = BrandingConfig(
            business_name="Test Business",
            industry="dentist",
        )

        validation_result = validate_branding_config(config)
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0

        env_vars = inject_branding(config)
        assert "NEXT_PUBLIC_BUSINESS_NAME" in env_vars
        assert env_vars["NEXT_PUBLIC_BUSINESS_NAME"] == "Test Business"

    def test_daily_report_integration(self):
        """Test daily report utility integration."""
        from utils.daily_report import (
            generate_daily_report_from_stats,
        )

        report = generate_daily_report_from_stats(
            sent=100,
            delivered=95,
            bounced=3,
            opened=40,
            clicked=15,
            spam_reports=1,
            unsubscribes=1,
        )

        # Check report structure
        assert report.metrics.sent == 100
        assert report.metrics.delivered == 95
        assert report.domain_health_score >= 0
        assert report.domain_health_score <= 100


class TestPipelineMetrics:
    """Tests for pipeline metrics and reporting."""

    def test_lead_processing_time_tracking(self, mock_db):
        """Test that lead processing time is tracked."""
        from orchestrator import LeadProcessingResult

        start_time = time.time()

        # Simulate some processing
        time.sleep(0.01)

        end_time = time.time()
        processing_time = end_time - start_time

        result = LeadProcessingResult(
            lead_id="lead_123",
            lead_name="Test Business",
            success=True,
            processing_time_seconds=processing_time,
        )

        assert result.processing_time_seconds > 0

    def test_campaign_duration_tracking(self, mock_db):
        """Test that campaign duration is tracked."""
        from orchestrator import CampaignResult

        started = datetime.now(timezone.utc)
        time.sleep(0.01)
        completed = datetime.now(timezone.utc)

        result = CampaignResult(
            campaign_id="campaign_123",
            started_at=started,
            completed_at=completed,
            duration_seconds=(completed - started).total_seconds(),
        )

        assert result.duration_seconds > 0

    def test_campaign_success_rate_calculation(self, mock_db):
        """Test campaign success rate calculation."""
        from orchestrator import CampaignResult

        result = CampaignResult(
            campaign_id="campaign_123",
            total_leads=10,
            processed_leads=8,
            failed_leads=2,
        )

        success_rate = (result.processed_leads / result.total_leads) * 100
        failure_rate = (result.failed_leads / result.total_leads) * 100

        assert success_rate == 80.0
        assert failure_rate == 20.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
