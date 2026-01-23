"""Unit tests for dossier generation with all required sections.

Tests the dossier_template module which provides comprehensive research
dossier generation for lead generation, including:
- Company Overview
- Services
- Team
- Pain Points
- Gotcha Q&As
- Competitor Landscape
"""

import os
import sys
from datetime import datetime

import pytest

# Ensure repo root is on sys.path so imports work correctly
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LEADGEN_DIR = os.path.join(ROOT_DIR, "src", "leadgen")
if LEADGEN_DIR not in sys.path:
    sys.path.insert(0, LEADGEN_DIR)

from utils.dossier_template import (
    Competitor,
    CompanyOverview,
    DossierData,
    DossierStatus,
    GotchaQA,
    PainPoint,
    Service,
    TeamMember,
    DEFAULT_PAIN_POINTS,
    generate_dossier,
    generate_dossier_from_dict,
    generate_gotcha_qas_from_data,
    get_default_pain_points,
    is_dossier_valid,
    validate_dossier_sections,
)


class TestTeamMemberDataclass:
    """Tests for TeamMember dataclass."""

    def test_minimal_creation(self):
        """Test creating TeamMember with only required fields."""
        member = TeamMember(name="John Smith")
        assert member.name == "John Smith"
        assert member.title is None
        assert member.email is None
        assert member.linkedin is None
        assert member.bio is None

    def test_full_creation(self):
        """Test creating TeamMember with all fields."""
        member = TeamMember(
            name="Jane Doe",
            title="CEO",
            email="jane@example.com",
            linkedin="https://linkedin.com/in/janedoe",
            bio="Experienced business leader with 20 years in healthcare."
        )
        assert member.name == "Jane Doe"
        assert member.title == "CEO"
        assert member.email == "jane@example.com"
        assert member.linkedin == "https://linkedin.com/in/janedoe"
        assert member.bio == "Experienced business leader with 20 years in healthcare."


class TestServiceDataclass:
    """Tests for Service dataclass."""

    def test_minimal_creation(self):
        """Test creating Service with only required fields."""
        service = Service(name="General Checkup")
        assert service.name == "General Checkup"
        assert service.description is None
        assert service.price_range is None
        assert service.is_primary is False

    def test_full_creation(self):
        """Test creating Service with all fields."""
        service = Service(
            name="Root Canal",
            description="Endodontic treatment to save damaged teeth",
            price_range="$800-$1500",
            is_primary=True
        )
        assert service.name == "Root Canal"
        assert service.description == "Endodontic treatment to save damaged teeth"
        assert service.price_range == "$800-$1500"
        assert service.is_primary is True


class TestPainPointDataclass:
    """Tests for PainPoint dataclass."""

    def test_minimal_creation(self):
        """Test creating PainPoint with only required fields."""
        pain = PainPoint(category="Scheduling", description="Difficult to book appointments")
        assert pain.category == "Scheduling"
        assert pain.description == "Difficult to book appointments"
        assert pain.impact is None
        assert pain.solution_hook is None

    def test_full_creation(self):
        """Test creating PainPoint with all fields."""
        pain = PainPoint(
            category="No-shows",
            description="High rate of appointment no-shows",
            impact="Lost revenue of $50k/year",
            solution_hook="AI reminders reduce no-shows by 60%"
        )
        assert pain.category == "No-shows"
        assert pain.description == "High rate of appointment no-shows"
        assert pain.impact == "Lost revenue of $50k/year"
        assert pain.solution_hook == "AI reminders reduce no-shows by 60%"


class TestGotchaQADataclass:
    """Tests for GotchaQA dataclass."""

    def test_minimal_creation(self):
        """Test creating GotchaQA with only required fields."""
        qa = GotchaQA(question="What are your hours?", answer="9am to 5pm Monday-Friday")
        assert qa.question == "What are your hours?"
        assert qa.answer == "9am to 5pm Monday-Friday"
        assert qa.category == "general"
        assert qa.difficulty == "medium"

    def test_full_creation(self):
        """Test creating GotchaQA with all fields."""
        qa = GotchaQA(
            question="What is the address?",
            answer="123 Main St, City, ST 12345",
            category="location",
            difficulty="easy"
        )
        assert qa.question == "What is the address?"
        assert qa.answer == "123 Main St, City, ST 12345"
        assert qa.category == "location"
        assert qa.difficulty == "easy"


class TestCompetitorDataclass:
    """Tests for Competitor dataclass."""

    def test_minimal_creation(self):
        """Test creating Competitor with only required fields."""
        comp = Competitor(name="Acme Corp")
        assert comp.name == "Acme Corp"
        assert comp.website is None
        assert comp.strengths == []
        assert comp.weaknesses == []
        assert comp.differentiator is None

    def test_full_creation(self):
        """Test creating Competitor with all fields."""
        comp = Competitor(
            name="Competitor Inc",
            website="https://competitor.com",
            strengths=["Large team", "Established brand"],
            weaknesses=["Slow response time", "Outdated tech"],
            differentiator="We offer faster turnaround"
        )
        assert comp.name == "Competitor Inc"
        assert comp.website == "https://competitor.com"
        assert comp.strengths == ["Large team", "Established brand"]
        assert comp.weaknesses == ["Slow response time", "Outdated tech"]
        assert comp.differentiator == "We offer faster turnaround"


class TestCompanyOverviewDataclass:
    """Tests for CompanyOverview dataclass."""

    def test_minimal_creation(self):
        """Test creating CompanyOverview with only required fields."""
        company = CompanyOverview(name="Test Business")
        assert company.name == "Test Business"
        assert company.address is None
        assert company.phone is None
        assert company.website is None

    def test_full_creation(self):
        """Test creating CompanyOverview with all fields."""
        company = CompanyOverview(
            name="Full Business",
            address="123 Main St, City, ST 12345",
            phone="555-123-4567",
            website="https://example.com",
            industry="dentist",
            description="A family dental practice",
            founding_year=2010,
            employee_count="10-25",
            google_rating=4.7,
            review_count=150,
            estimated_revenue=500000.0,
            operating_hours={"Monday": "9am-5pm", "Tuesday": "9am-5pm"},
            social_profiles={"facebook": "https://facebook.com/business"}
        )
        assert company.name == "Full Business"
        assert company.industry == "dentist"
        assert company.google_rating == 4.7
        assert company.review_count == 150
        assert company.estimated_revenue == 500000.0
        assert company.operating_hours["Monday"] == "9am-5pm"
        assert "facebook" in company.social_profiles


class TestDossierDataDataclass:
    """Tests for DossierData dataclass."""

    def test_minimal_creation(self):
        """Test creating DossierData with only required fields."""
        company = CompanyOverview(name="Test Company")
        data = DossierData(company=company)
        assert data.company.name == "Test Company"
        assert data.services == []
        assert data.team == []
        assert data.pain_points == []
        assert data.gotcha_qas == []
        assert data.competitors == []
        assert data.status == DossierStatus.MINIMAL

    def test_full_creation(self):
        """Test creating DossierData with all fields."""
        company = CompanyOverview(name="Full Company")
        service = Service(name="Service A")
        member = TeamMember(name="Person A")
        pain = PainPoint(category="Issue", description="A problem")
        qa = GotchaQA(question="Q?", answer="A.")
        comp = Competitor(name="Competitor")

        data = DossierData(
            company=company,
            services=[service],
            team=[member],
            pain_points=[pain],
            gotcha_qas=[qa],
            competitors=[comp],
            status=DossierStatus.COMPLETE,
            data_sources=["Google Maps", "Website"],
            generated_at=datetime(2024, 1, 15, 12, 0, 0),
            raw_website_content="Raw content here",
            raw_reviews=[{"text": "Great!"}]
        )
        assert len(data.services) == 1
        assert len(data.team) == 1
        assert data.status == DossierStatus.COMPLETE
        assert "Google Maps" in data.data_sources


class TestDossierStatus:
    """Tests for DossierStatus enum."""

    def test_complete_status(self):
        """Test COMPLETE status value."""
        assert DossierStatus.COMPLETE.value == "complete"

    def test_partial_status(self):
        """Test PARTIAL status value."""
        assert DossierStatus.PARTIAL.value == "partial"

    def test_minimal_status(self):
        """Test MINIMAL status value."""
        assert DossierStatus.MINIMAL.value == "minimal"

    def test_failed_status(self):
        """Test FAILED status value."""
        assert DossierStatus.FAILED.value == "failed"


class TestGetDefaultPainPoints:
    """Tests for get_default_pain_points function."""

    def test_dentist_pain_points(self):
        """Test getting default pain points for dentist industry."""
        pain_points = get_default_pain_points("dentist")
        assert len(pain_points) > 0
        assert any("no-shows" in p.category.lower() for p in pain_points)

    def test_hvac_pain_points(self):
        """Test getting default pain points for HVAC industry."""
        pain_points = get_default_pain_points("hvac")
        assert len(pain_points) > 0
        assert any("emergency" in p.category.lower() for p in pain_points)

    def test_salon_pain_points(self):
        """Test getting default pain points for salon industry."""
        pain_points = get_default_pain_points("salon")
        assert len(pain_points) > 0

    def test_case_insensitive(self):
        """Test that industry matching is case-insensitive."""
        points_lower = get_default_pain_points("dentist")
        points_upper = get_default_pain_points("DENTIST")
        points_mixed = get_default_pain_points("DeNtIsT")
        assert len(points_lower) == len(points_upper) == len(points_mixed)

    def test_whitespace_handling(self):
        """Test that whitespace is stripped from industry."""
        points = get_default_pain_points("  dentist  ")
        assert len(points) > 0

    def test_partial_match(self):
        """Test partial matching for industry names."""
        points = get_default_pain_points("dental office")
        assert len(points) > 0

    def test_unknown_industry_returns_default(self):
        """Test that unknown industry returns default pain points."""
        points = get_default_pain_points("unknown_xyz")
        default_points = DEFAULT_PAIN_POINTS["default"]
        assert len(points) == len(default_points)

    def test_empty_string_returns_default(self):
        """Test that empty string returns default pain points."""
        points = get_default_pain_points("")
        assert len(points) > 0

    def test_none_returns_default(self):
        """Test that None returns default pain points."""
        points = get_default_pain_points(None)
        assert len(points) > 0


class TestGenerateGotchaQAsFromData:
    """Tests for generate_gotcha_qas_from_data function."""

    def test_generates_address_question(self):
        """Test that address-based Q&A is generated."""
        company = CompanyOverview(
            name="Test Dental",
            address="123 Main St, City, ST 12345"
        )
        data = DossierData(company=company)
        qas = generate_gotcha_qas_from_data(data)
        address_qas = [q for q in qas if q.category == "location"]
        assert len(address_qas) >= 1
        assert "123 Main St" in address_qas[0].answer

    def test_generates_phone_question(self):
        """Test that phone-based Q&A is generated."""
        company = CompanyOverview(
            name="Test Dental",
            phone="555-123-4567"
        )
        data = DossierData(company=company)
        qas = generate_gotcha_qas_from_data(data)
        phone_qas = [q for q in qas if q.category == "contact"]
        assert len(phone_qas) >= 1
        assert "555-123-4567" in phone_qas[0].answer

    def test_generates_hours_question(self):
        """Test that hours-based Q&A is generated."""
        company = CompanyOverview(
            name="Test Dental",
            operating_hours={"Monday": "9am-5pm", "Tuesday": "10am-6pm"}
        )
        data = DossierData(company=company)
        qas = generate_gotcha_qas_from_data(data)
        hours_qas = [q for q in qas if q.category == "hours"]
        assert len(hours_qas) >= 1

    def test_generates_service_questions(self):
        """Test that service-based Q&As are generated."""
        company = CompanyOverview(name="Test Dental")
        services = [
            Service(name="Teeth Cleaning", description="Professional dental cleaning"),
            Service(name="Whitening", description="Cosmetic whitening treatment"),
        ]
        data = DossierData(company=company, services=services)
        qas = generate_gotcha_qas_from_data(data)
        service_qas = [q for q in qas if q.category == "services"]
        assert len(service_qas) >= 1

    def test_generates_pricing_questions(self):
        """Test that pricing Q&As are generated when price_range is available."""
        company = CompanyOverview(name="Test Dental")
        services = [
            Service(name="Cleaning", price_range="$100-$150"),
        ]
        data = DossierData(company=company, services=services)
        qas = generate_gotcha_qas_from_data(data)
        pricing_qas = [q for q in qas if q.category == "pricing"]
        assert len(pricing_qas) >= 1
        assert "$100-$150" in pricing_qas[0].answer

    def test_generates_team_questions(self):
        """Test that team-based Q&As are generated."""
        company = CompanyOverview(name="Test Dental")
        team = [TeamMember(name="Dr. Smith", title="Lead Dentist")]
        data = DossierData(company=company, team=team)
        qas = generate_gotcha_qas_from_data(data)
        team_qas = [q for q in qas if q.category == "team"]
        assert len(team_qas) >= 1
        assert "Dr. Smith" in team_qas[0].answer

    def test_generates_dental_industry_questions(self):
        """Test that dental-specific Q&As are generated."""
        company = CompanyOverview(name="Test Dental", industry="dentist")
        data = DossierData(company=company)
        qas = generate_gotcha_qas_from_data(data)
        # Should have insurance and emergency questions
        questions = [q.question.lower() for q in qas]
        assert any("insurance" in q for q in questions)

    def test_generates_hvac_industry_questions(self):
        """Test that HVAC-specific Q&As are generated."""
        company = CompanyOverview(name="Test HVAC", industry="hvac")
        data = DossierData(company=company)
        qas = generate_gotcha_qas_from_data(data)
        # Should have 24-hour/emergency questions
        questions = [q.question.lower() for q in qas]
        assert any("24" in q or "emergency" in q for q in questions)

    def test_generates_salon_industry_questions(self):
        """Test that salon-specific Q&As are generated."""
        company = CompanyOverview(name="Test Salon", industry="salon")
        data = DossierData(company=company)
        qas = generate_gotcha_qas_from_data(data)
        # Should have appointment/walk-in questions
        questions = [q.question.lower() for q in qas]
        assert any("appointment" in q or "walk-in" in q for q in questions)

    def test_limits_services_to_three(self):
        """Test that only first 3 services generate Q&As."""
        company = CompanyOverview(name="Test Business")
        services = [Service(name=f"Service {i}") for i in range(10)]
        data = DossierData(company=company, services=services)
        qas = generate_gotcha_qas_from_data(data)
        service_qas = [q for q in qas if q.category == "services"]
        # Should have at most 3 service questions
        assert len(service_qas) <= 3

    def test_limits_team_to_two(self):
        """Test that only first 2 team members generate Q&As."""
        company = CompanyOverview(name="Test Business")
        team = [TeamMember(name=f"Person {i}", title=f"Title {i}") for i in range(10)]
        data = DossierData(company=company, team=team)
        qas = generate_gotcha_qas_from_data(data)
        team_qas = [q for q in qas if q.category == "team"]
        # Should have at most 2 team questions
        assert len(team_qas) <= 2


class TestGenerateDossier:
    """Tests for generate_dossier function."""

    def test_generates_header(self):
        """Test that dossier has proper header."""
        company = CompanyOverview(name="Acme Dental")
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert "# Research Dossier: Acme Dental" in dossier
        assert "_Generated:" in dossier
        assert "_Status:" in dossier

    def test_has_company_overview_section(self):
        """Test that dossier has Company Overview section."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert "## Company Overview" in dossier

    def test_has_services_section(self):
        """Test that dossier has Services section."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert "## Services" in dossier

    def test_has_team_section(self):
        """Test that dossier has Team section."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert "## Team" in dossier

    def test_has_pain_points_section(self):
        """Test that dossier has Pain Points section."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert "## Pain Points" in dossier

    def test_has_gotcha_qas_section(self):
        """Test that dossier has Gotcha Q&As section."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert "## Gotcha Q&As" in dossier

    def test_has_competitor_section(self):
        """Test that dossier has Competitor Landscape section."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert "## Competitor Landscape" in dossier

    def test_includes_contact_info(self):
        """Test that contact information is included."""
        company = CompanyOverview(
            name="Test Business",
            address="123 Main St",
            phone="555-1234",
            website="https://example.com"
        )
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert "123 Main St" in dossier
        assert "555-1234" in dossier
        assert "https://example.com" in dossier

    def test_includes_business_metrics(self):
        """Test that business metrics are included."""
        company = CompanyOverview(
            name="Test Business",
            google_rating=4.5,
            review_count=100,
            estimated_revenue=500000.0
        )
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert "4.5" in dossier
        assert "100" in dossier
        assert "500,000" in dossier

    def test_includes_services(self):
        """Test that services are included in dossier."""
        company = CompanyOverview(name="Test Business")
        services = [
            Service(name="Service A", description="Description A", is_primary=True),
            Service(name="Service B", description="Description B"),
        ]
        data = DossierData(company=company, services=services)
        dossier = generate_dossier(data)
        assert "Service A" in dossier
        assert "Service B" in dossier
        assert "Description A" in dossier
        assert "Primary Services" in dossier

    def test_includes_team(self):
        """Test that team members are included in dossier."""
        company = CompanyOverview(name="Test Business")
        team = [
            TeamMember(name="John Doe", title="CEO", bio="Experienced leader"),
        ]
        data = DossierData(company=company, team=team)
        dossier = generate_dossier(data)
        assert "John Doe" in dossier
        assert "CEO" in dossier
        assert "Experienced leader" in dossier

    def test_includes_pain_points(self):
        """Test that pain points are included in dossier."""
        company = CompanyOverview(name="Test Business")
        pain_points = [
            PainPoint(
                category="No-shows",
                description="High no-show rate",
                impact="Lost revenue",
                solution_hook="AI reminders help"
            )
        ]
        data = DossierData(company=company, pain_points=pain_points)
        dossier = generate_dossier(data)
        assert "No-shows" in dossier
        assert "High no-show rate" in dossier
        assert "Lost revenue" in dossier
        assert "AI reminders help" in dossier

    def test_includes_gotcha_qas(self):
        """Test that gotcha Q&As are included in dossier."""
        company = CompanyOverview(name="Test Business")
        qas = [
            GotchaQA(
                question="What are your hours?",
                answer="9am to 5pm",
                category="hours",
                difficulty="easy"
            )
        ]
        data = DossierData(company=company, gotcha_qas=qas)
        dossier = generate_dossier(data)
        assert "What are your hours?" in dossier
        assert "9am to 5pm" in dossier
        assert "Easy Questions" in dossier

    def test_includes_competitors(self):
        """Test that competitors are included in dossier."""
        company = CompanyOverview(name="Test Business")
        competitors = [
            Competitor(
                name="Rival Inc",
                website="https://rival.com",
                strengths=["Big team"],
                weaknesses=["Slow service"],
                differentiator="We're faster"
            )
        ]
        data = DossierData(company=company, competitors=competitors)
        dossier = generate_dossier(data)
        assert "Rival Inc" in dossier
        assert "https://rival.com" in dossier
        assert "Big team" in dossier
        assert "Slow service" in dossier
        assert "We're faster" in dossier

    def test_includes_data_sources(self):
        """Test that data sources are included in dossier."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(
            company=company,
            data_sources=["Google Maps", "Website (Firecrawl)"]
        )
        dossier = generate_dossier(data)
        assert "Google Maps" in dossier
        assert "Website (Firecrawl)" in dossier

    def test_includes_raw_content_when_requested(self):
        """Test that raw content is included when requested."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(
            company=company,
            raw_website_content="This is raw website content."
        )
        dossier = generate_dossier(data, include_raw_content=True)
        assert "Raw Website Content" in dossier
        assert "This is raw website content." in dossier

    def test_excludes_raw_content_by_default(self):
        """Test that raw content is excluded by default."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(
            company=company,
            raw_website_content="This is raw website content."
        )
        dossier = generate_dossier(data, include_raw_content=False)
        assert "Raw Website Content" not in dossier

    def test_truncates_long_raw_content(self):
        """Test that long raw content is truncated."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(
            company=company,
            raw_website_content="x" * 10000  # 10000 chars, limit is 5000
        )
        dossier = generate_dossier(data, include_raw_content=True)
        assert "... (truncated)" in dossier


class TestGenerateDossierFromDict:
    """Tests for generate_dossier_from_dict function."""

    def test_minimal_dict(self):
        """Test generating dossier from minimal dictionary."""
        data = {"name": "Test Business"}
        dossier = generate_dossier_from_dict(data)
        assert "Test Business" in dossier
        assert "## Company Overview" in dossier

    def test_full_dict(self):
        """Test generating dossier from full dictionary."""
        data = {
            "name": "Full Business",
            "address": "123 Main St",
            "phone": "555-1234",
            "website": "https://example.com",
            "industry": "dentist",
            "description": "A dental practice",
            "google_rating": 4.5,
            "review_count": 100,
            "services": [
                {"name": "Cleaning", "description": "Dental cleaning", "is_primary": True}
            ],
            "team": [
                {"name": "Dr. Smith", "title": "Dentist"}
            ],
        }
        dossier = generate_dossier_from_dict(data)
        assert "Full Business" in dossier
        assert "123 Main St" in dossier
        assert "Cleaning" in dossier
        assert "Dr. Smith" in dossier

    def test_adds_default_pain_points(self):
        """Test that default pain points are added when none provided."""
        data = {"name": "Test Dental", "industry": "dentist"}
        dossier = generate_dossier_from_dict(data, include_defaults=True)
        # Should have pain points section with content
        assert "Pain Points" in dossier
        assert "no-shows" in dossier.lower() or "challenge" in dossier.lower()

    def test_skips_default_pain_points_when_disabled(self):
        """Test that default pain points are skipped when disabled."""
        data = {"name": "Test Dental", "industry": "dentist"}
        dossier = generate_dossier_from_dict(data, include_defaults=False)
        # Should have empty pain points section
        assert "No pain points identified" in dossier

    def test_uses_provided_pain_points(self):
        """Test that provided pain points are used."""
        data = {
            "name": "Test Business",
            "pain_points": [
                {
                    "category": "Custom Issue",
                    "description": "Custom problem description"
                }
            ]
        }
        dossier = generate_dossier_from_dict(data)
        assert "Custom Issue" in dossier
        assert "Custom problem description" in dossier

    def test_string_services_converted(self):
        """Test that string services are converted to Service objects."""
        data = {
            "name": "Test Business",
            "services": ["Service A", "Service B"]
        }
        dossier = generate_dossier_from_dict(data)
        assert "Service A" in dossier
        assert "Service B" in dossier

    def test_string_team_members_converted(self):
        """Test that string team members are converted to TeamMember objects."""
        data = {
            "name": "Test Business",
            "team": ["John Smith", "Jane Doe"]
        }
        dossier = generate_dossier_from_dict(data)
        assert "John Smith" in dossier
        assert "Jane Doe" in dossier

    def test_string_competitors_converted(self):
        """Test that string competitors are converted to Competitor objects."""
        data = {
            "name": "Test Business",
            "competitors": ["Competitor A", "Competitor B"]
        }
        dossier = generate_dossier_from_dict(data)
        assert "Competitor A" in dossier
        assert "Competitor B" in dossier

    def test_determines_complete_status(self):
        """Test that COMPLETE status is determined correctly."""
        data = {
            "name": "Test Business",
            "website": "https://example.com",
            "description": "A business description"
        }
        dossier = generate_dossier_from_dict(data)
        assert "complete" in dossier.lower()

    def test_determines_partial_status(self):
        """Test that PARTIAL status is determined correctly."""
        data = {
            "name": "Test Business",
            "website": "https://example.com"
            # No description
        }
        dossier = generate_dossier_from_dict(data)
        assert "partial" in dossier.lower()

    def test_determines_minimal_status(self):
        """Test that MINIMAL status is determined correctly."""
        data = {
            "name": "Test Business"
            # No website, no description
        }
        dossier = generate_dossier_from_dict(data)
        assert "minimal" in dossier.lower()

    def test_detects_google_maps_source(self):
        """Test that Google Maps is detected as data source."""
        data = {
            "name": "Test Business",
            "google_place_id": "ChIJxxx",
            "google_rating": 4.5
        }
        dossier = generate_dossier_from_dict(data)
        assert "Google Maps" in dossier

    def test_detects_website_source(self):
        """Test that website is detected as data source."""
        data = {
            "name": "Test Business",
            "website": "https://example.com"
        }
        dossier = generate_dossier_from_dict(data)
        assert "Firecrawl" in dossier

    def test_detects_apollo_source(self):
        """Test that Apollo is detected as data source."""
        data = {
            "name": "Test Business",
            "apollo_enriched": True
        }
        dossier = generate_dossier_from_dict(data)
        assert "Apollo.io" in dossier

    def test_generates_gotcha_qas(self):
        """Test that gotcha Q&As are auto-generated."""
        data = {
            "name": "Test Business",
            "address": "123 Main St",
            "phone": "555-1234"
        }
        dossier = generate_dossier_from_dict(data)
        # Should have address and phone based Q&As
        assert "123 Main St" in dossier
        assert "555-1234" in dossier

    def test_adds_custom_gotcha_qas(self):
        """Test that custom gotcha Q&As from input are added."""
        data = {
            "name": "Test Business",
            "gotcha_qas": [
                {
                    "question": "Custom question?",
                    "answer": "Custom answer",
                    "category": "custom"
                }
            ]
        }
        dossier = generate_dossier_from_dict(data)
        assert "Custom question?" in dossier
        assert "Custom answer" in dossier


class TestValidateDossierSections:
    """Tests for validate_dossier_sections function."""

    def test_validates_complete_dossier(self):
        """Test validation of a complete dossier."""
        company = CompanyOverview(name="Test Business")
        pain_points = [PainPoint(category="Test", description="Test")]
        qas = [GotchaQA(question="Q?", answer="A")]
        competitors = [Competitor(name="Rival")]
        services = [Service(name="Service")]
        team = [TeamMember(name="Person")]

        data = DossierData(
            company=company,
            services=services,
            team=team,
            pain_points=pain_points,
            gotcha_qas=qas,
            competitors=competitors
        )
        dossier = generate_dossier(data)
        validation = validate_dossier_sections(dossier)

        assert validation["Company Overview"] is True
        assert validation["Services"] is True
        assert validation["Team"] is True
        assert validation["Pain Points"] is True
        assert validation["Gotcha Q&A"] is True
        assert validation["Competitor"] is True

    def test_validates_minimal_dossier(self):
        """Test validation of a minimal dossier."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        validation = validate_dossier_sections(dossier)

        # All sections should be present (even if empty)
        assert all(validation.values())

    def test_case_insensitive_validation(self):
        """Test that validation is case-insensitive."""
        # Create a dossier with lowercase sections
        dossier = """
        ## company overview
        Test content

        ## services
        Test content

        ## team
        Test content

        ## pain points
        Test content

        ## gotcha q&a
        Test content

        ## competitor
        Test content
        """
        validation = validate_dossier_sections(dossier)
        assert all(validation.values())


class TestIsDossierValid:
    """Tests for is_dossier_valid function."""

    def test_valid_dossier(self):
        """Test that valid dossier returns True."""
        company = CompanyOverview(name="Test Business")
        data = DossierData(company=company)
        dossier = generate_dossier(data)
        assert is_dossier_valid(dossier) is True

    def test_invalid_dossier_missing_section(self):
        """Test that dossier missing sections returns False."""
        # Create a partial dossier missing sections
        dossier = """
        # Research Dossier: Test

        ## Company Overview
        Test content
        """
        assert is_dossier_valid(dossier) is False


class TestDefaultPainPointsStructure:
    """Tests for DEFAULT_PAIN_POINTS constant."""

    def test_has_default_key(self):
        """Test that DEFAULT_PAIN_POINTS has 'default' key."""
        assert "default" in DEFAULT_PAIN_POINTS

    def test_has_dentist_key(self):
        """Test that DEFAULT_PAIN_POINTS has 'dentist' key."""
        assert "dentist" in DEFAULT_PAIN_POINTS

    def test_has_hvac_key(self):
        """Test that DEFAULT_PAIN_POINTS has 'hvac' key."""
        assert "hvac" in DEFAULT_PAIN_POINTS

    def test_has_salon_key(self):
        """Test that DEFAULT_PAIN_POINTS has 'salon' key."""
        assert "salon" in DEFAULT_PAIN_POINTS

    def test_all_entries_have_category(self):
        """Test that all pain point entries have category."""
        for industry, points in DEFAULT_PAIN_POINTS.items():
            for point in points:
                assert point.category, f"Missing category in {industry}"

    def test_all_entries_have_description(self):
        """Test that all pain point entries have description."""
        for industry, points in DEFAULT_PAIN_POINTS.items():
            for point in points:
                assert point.description, f"Missing description in {industry}"

    def test_all_entries_have_solution_hook(self):
        """Test that all pain point entries have solution_hook."""
        for industry, points in DEFAULT_PAIN_POINTS.items():
            for point in points:
                assert point.solution_hook, f"Missing solution_hook in {industry}"


class TestDossierIntegration:
    """Integration tests for complete dossier generation workflow."""

    def test_full_workflow_from_google_data(self):
        """Test generating dossier from typical Google Maps data."""
        google_data = {
            "name": "Smile Dental Care",
            "address": "456 Oak Ave, Townsville, CA 90210",
            "phone": "(555) 987-6543",
            "website": "https://smiledental.com",
            "industry": "dentist",
            "google_rating": 4.8,
            "review_count": 234,
            "google_place_id": "ChIJxxx123",
            "operating_hours": {
                "Monday": "8am-6pm",
                "Tuesday": "8am-6pm",
                "Wednesday": "8am-6pm",
                "Thursday": "8am-6pm",
                "Friday": "8am-5pm",
                "Saturday": "9am-2pm",
                "Sunday": "Closed"
            }
        }

        dossier = generate_dossier_from_dict(google_data)

        # Verify all required sections present
        assert is_dossier_valid(dossier)

        # Verify key data is included
        assert "Smile Dental Care" in dossier
        assert "456 Oak Ave" in dossier
        assert "4.8" in dossier
        assert "234" in dossier
        assert "Monday" in dossier

    def test_full_workflow_with_enrichment(self):
        """Test generating dossier with enrichment data."""
        enriched_data = {
            "name": "Premium HVAC Services",
            "address": "789 Industrial Blvd, Metro City, TX 75001",
            "phone": "(555) 111-2222",
            "website": "https://premiumhvac.com",
            "industry": "hvac",
            "description": "Leading HVAC provider serving the Metro area for 25 years.",
            "google_rating": 4.6,
            "review_count": 156,
            "estimated_revenue": 750000.0,
            "employee_count": "15-30",
            "founding_year": 1998,
            "services": [
                {"name": "AC Installation", "is_primary": True, "price_range": "$3000-$8000"},
                {"name": "Heating Repair", "is_primary": True},
                {"name": "Duct Cleaning", "description": "Complete air duct cleaning service"},
                {"name": "Maintenance Plans", "price_range": "$199/year"}
            ],
            "team": [
                {"name": "Mike Johnson", "title": "Owner", "bio": "Master HVAC technician"},
                {"name": "Sarah Lee", "title": "Operations Manager"}
            ],
            "social_profiles": {
                "facebook": "https://facebook.com/premiumhvac",
                "yelp": "https://yelp.com/biz/premium-hvac"
            },
            "apollo_enriched": True
        }

        dossier = generate_dossier_from_dict(enriched_data)

        # Verify all required sections present
        assert is_dossier_valid(dossier)

        # Verify enrichment data included
        assert "Premium HVAC Services" in dossier
        assert "Leading HVAC provider" in dossier
        assert "Mike Johnson" in dossier
        assert "AC Installation" in dossier
        assert "750,000" in dossier
        assert "Apollo.io" in dossier

    def test_generates_useful_gotcha_qas(self):
        """Test that generated gotcha Q&As are useful for voice agent testing."""
        data = {
            "name": "City Dental Group",
            "address": "100 Healthcare Drive, Suite 200, Medical City, NY 10001",
            "phone": "(212) 555-DENT",
            "industry": "dentist",
            "operating_hours": {"Monday": "8am-5pm"},
            "services": [
                {"name": "Dental Implants", "price_range": "$3000-$5000"}
            ],
            "team": [
                {"name": "Dr. Emily Chen", "title": "Lead Dentist"}
            ]
        }

        dossier = generate_dossier_from_dict(data)

        # Verify gotcha Q&As cover multiple categories
        assert "What is the address" in dossier or "address" in dossier.lower()
        assert "What is the phone" in dossier or "phone" in dossier.lower()
        assert "hours" in dossier.lower()
        assert "dental implants" in dossier.lower()

    def test_minimal_data_produces_valid_dossier(self):
        """Test that minimal data still produces a valid dossier structure."""
        minimal_data = {"name": "Unknown Business"}

        dossier = generate_dossier_from_dict(minimal_data)

        # Should still be structurally valid
        assert is_dossier_valid(dossier)

        # Should have placeholder/default content
        assert "Unknown Business" in dossier
        assert "minimal" in dossier.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
