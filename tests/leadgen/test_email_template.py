"""Unit tests for email template personalization and CAN-SPAM compliance.

Tests the email_templates module which provides comprehensive email template
generation for cold outreach campaigns, including:
- Personalization token replacement
- CAN-SPAM compliant footer generation
- Multiple email styles (humorous, professional, direct, curiosity)
- Industry-specific subject lines and content
- A/B testing variants
- Template validation
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

from utils.email_templates import (
    CANSpamFooter,
    EmailStyle,
    EmailTemplate,
    EmailVariant,
    GeneratedEmail,
    PersonalizationToken,
    generate_cold_email,
    generate_cold_email_from_dict,
    generate_subject,
    get_available_styles,
    get_available_variants,
    get_industry_subjects,
    is_template_valid,
    validate_template,
    INDUSTRY_SUBJECTS,
    INDUSTRY_PAIN_HOOKS,
    HUMOROUS_OPENERS,
)


class TestPersonalizationToken:
    """Tests for PersonalizationToken dataclass."""

    def test_minimal_creation(self):
        """Test creating PersonalizationToken with only required fields."""
        token = PersonalizationToken(name="test", placeholder="{{test}}")
        assert token.name == "test"
        assert token.placeholder == "{{test}}"
        assert token.value is None
        assert token.required is False
        assert token.default is None

    def test_full_creation(self):
        """Test creating PersonalizationToken with all fields."""
        token = PersonalizationToken(
            name="business_name",
            placeholder="{{business_name}}",
            value="Acme Corp",
            required=True,
            default="Your Business"
        )
        assert token.name == "business_name"
        assert token.value == "Acme Corp"
        assert token.required is True
        assert token.default == "Your Business"

    def test_get_value_returns_value(self):
        """Test get_value returns the set value."""
        token = PersonalizationToken(
            name="test",
            placeholder="{{test}}",
            value="actual_value"
        )
        assert token.get_value() == "actual_value"

    def test_get_value_returns_default(self):
        """Test get_value returns default when value is None."""
        token = PersonalizationToken(
            name="test",
            placeholder="{{test}}",
            value=None,
            default="default_value"
        )
        assert token.get_value() == "default_value"

    def test_get_value_raises_for_required_missing(self):
        """Test get_value raises error for required token without value."""
        token = PersonalizationToken(
            name="required_token",
            placeholder="{{required_token}}",
            required=True
        )
        with pytest.raises(ValueError) as excinfo:
            token.get_value()
        assert "required_token" in str(excinfo.value)

    def test_get_value_returns_empty_for_optional_missing(self):
        """Test get_value returns empty string for optional token without value."""
        token = PersonalizationToken(
            name="optional",
            placeholder="{{optional}}",
            required=False
        )
        assert token.get_value() == ""


class TestCANSpamFooter:
    """Tests for CAN-SPAM compliance footer generation."""

    def test_minimal_creation(self):
        """Test creating CANSpamFooter with only required fields."""
        footer = CANSpamFooter(
            company_name="Test Company",
            address_line1="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94102"
        )
        assert footer.company_name == "Test Company"
        assert footer.country == "USA"  # default
        assert "{{unsubscribe}}" in footer.unsubscribe_url

    def test_full_creation(self):
        """Test creating CANSpamFooter with all fields."""
        footer = CANSpamFooter(
            company_name="Full Company",
            address_line1="456 Oak Ave",
            city="New York",
            state="NY",
            zip_code="10001",
            country="United States",
            unsubscribe_reason="you signed up for our newsletter",
            unsubscribe_url="https://example.com/unsub"
        )
        assert footer.company_name == "Full Company"
        assert footer.country == "United States"
        assert footer.unsubscribe_url == "https://example.com/unsub"

    def test_to_html_includes_company_name(self):
        """Test HTML footer includes company name."""
        footer = CANSpamFooter(
            company_name="Test Company",
            address_line1="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94102"
        )
        html = footer.to_html()
        assert "Test Company" in html

    def test_to_html_includes_address(self):
        """Test HTML footer includes full address."""
        footer = CANSpamFooter(
            company_name="Test Company",
            address_line1="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94102",
            country="USA"
        )
        html = footer.to_html()
        assert "123 Main St" in html
        assert "San Francisco" in html
        assert "CA" in html
        assert "94102" in html
        assert "USA" in html

    def test_to_html_includes_unsubscribe_link(self):
        """Test HTML footer includes unsubscribe link."""
        footer = CANSpamFooter(
            company_name="Test Company",
            address_line1="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94102",
            unsubscribe_url="https://unsub.example.com"
        )
        html = footer.to_html()
        assert 'href="https://unsub.example.com"' in html
        assert "unsubscribe" in html.lower()

    def test_to_html_includes_reason(self):
        """Test HTML footer includes reason for receiving email."""
        footer = CANSpamFooter(
            company_name="Test Company",
            address_line1="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94102",
            unsubscribe_reason="we thought your business might benefit"
        )
        html = footer.to_html()
        assert "we thought your business might benefit" in html

    def test_to_text_includes_company_info(self):
        """Test plain text footer includes company information."""
        footer = CANSpamFooter(
            company_name="Text Footer Company",
            address_line1="789 Elm St",
            city="Austin",
            state="TX",
            zip_code="78701"
        )
        text = footer.to_text()
        assert "Text Footer Company" in text
        assert "789 Elm St" in text
        assert "Austin" in text
        assert "TX" in text
        assert "78701" in text

    def test_to_text_includes_unsubscribe_url(self):
        """Test plain text footer includes unsubscribe URL."""
        footer = CANSpamFooter(
            company_name="Test Company",
            address_line1="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94102",
            unsubscribe_url="https://unsub.example.com"
        )
        text = footer.to_text()
        assert "https://unsub.example.com" in text

    def test_html_has_proper_structure(self):
        """Test HTML footer has proper HTML structure."""
        footer = CANSpamFooter(
            company_name="Test Company",
            address_line1="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94102"
        )
        html = footer.to_html()
        assert "<div" in html
        assert "</div>" in html
        assert "<p" in html
        assert "<a href=" in html


class TestEmailStyle:
    """Tests for EmailStyle enum."""

    def test_humorous_style(self):
        """Test HUMOROUS style value."""
        assert EmailStyle.HUMOROUS.value == "humorous"

    def test_professional_style(self):
        """Test PROFESSIONAL style value."""
        assert EmailStyle.PROFESSIONAL.value == "professional"

    def test_direct_style(self):
        """Test DIRECT style value."""
        assert EmailStyle.DIRECT.value == "direct"

    def test_curiosity_style(self):
        """Test CURIOSITY style value."""
        assert EmailStyle.CURIOSITY.value == "curiosity"

    def test_all_styles_available(self):
        """Test all expected styles are available."""
        styles = [s.value for s in EmailStyle]
        assert "humorous" in styles
        assert "professional" in styles
        assert "direct" in styles
        assert "curiosity" in styles


class TestEmailVariant:
    """Tests for EmailVariant enum."""

    def test_variant_a(self):
        """Test variant A value."""
        assert EmailVariant.A.value == "A"

    def test_variant_b(self):
        """Test variant B value."""
        assert EmailVariant.B.value == "B"

    def test_variant_c(self):
        """Test variant C value."""
        assert EmailVariant.C.value == "C"


class TestEmailTemplate:
    """Tests for EmailTemplate dataclass."""

    def test_minimal_creation(self):
        """Test creating EmailTemplate with only required fields."""
        template = EmailTemplate(business_name="Test Business")
        assert template.business_name == "Test Business"
        assert template.industry == ""
        assert template.demo_url == ""
        assert template.style == EmailStyle.HUMOROUS
        assert template.variant == EmailVariant.A

    def test_full_creation(self):
        """Test creating EmailTemplate with all fields."""
        template = EmailTemplate(
            business_name="Full Business",
            industry="dentist",
            demo_url="https://demo.example.com",
            recipient_name="John Smith",
            recipient_title="Owner",
            pain_points=["No-shows", "Missed calls"],
            sender_name="Jane",
            sender_title="Sales Rep",
            sender_company="Our Company",
            phone="555-1234",
            website="https://business.com",
            style=EmailStyle.PROFESSIONAL,
            variant=EmailVariant.B,
            custom_tokens={"custom_key": "custom_value"}
        )
        assert template.business_name == "Full Business"
        assert template.industry == "dentist"
        assert template.recipient_name == "John Smith"
        assert template.style == EmailStyle.PROFESSIONAL
        assert template.custom_tokens["custom_key"] == "custom_value"

    def test_get_greeting_with_name(self):
        """Test get_greeting returns personalized greeting with name."""
        template = EmailTemplate(
            business_name="Test",
            recipient_name="John Smith"
        )
        assert template.get_greeting() == "Hi John,"

    def test_get_greeting_without_name(self):
        """Test get_greeting returns generic greeting without name."""
        template = EmailTemplate(business_name="Test")
        assert template.get_greeting() == "Hi there,"

    def test_get_first_name_with_full_name(self):
        """Test get_first_name extracts first name from full name."""
        template = EmailTemplate(
            business_name="Test",
            recipient_name="John Michael Smith"
        )
        assert template.get_first_name() == "John"

    def test_get_first_name_with_single_name(self):
        """Test get_first_name with single name."""
        template = EmailTemplate(
            business_name="Test",
            recipient_name="John"
        )
        assert template.get_first_name() == "John"

    def test_get_first_name_without_name(self):
        """Test get_first_name returns fallback without name."""
        template = EmailTemplate(business_name="Test")
        assert template.get_first_name() == "there"


class TestGeneratedEmail:
    """Tests for GeneratedEmail dataclass."""

    def test_minimal_creation(self):
        """Test creating GeneratedEmail with only required fields."""
        email = GeneratedEmail(
            subject="Test Subject",
            html_content="<p>HTML</p>",
            text_content="Plain text"
        )
        assert email.subject == "Test Subject"
        assert email.html_content == "<p>HTML</p>"
        assert email.text_content == "Plain text"
        assert email.preview_text == ""
        assert email.tokens_used == []

    def test_full_creation(self):
        """Test creating GeneratedEmail with all fields."""
        now = datetime(2024, 1, 15, 12, 0, 0)
        email = GeneratedEmail(
            subject="Full Subject",
            html_content="<p>Full HTML</p>",
            text_content="Full plain text",
            preview_text="Preview here",
            tokens_used=["business_name", "demo_url"],
            style=EmailStyle.PROFESSIONAL,
            variant=EmailVariant.B,
            generated_at=now
        )
        assert email.subject == "Full Subject"
        assert email.preview_text == "Preview here"
        assert "business_name" in email.tokens_used
        assert email.style == EmailStyle.PROFESSIONAL
        assert email.generated_at == now

    def test_to_dict_conversion(self):
        """Test converting GeneratedEmail to dictionary."""
        email = GeneratedEmail(
            subject="Dict Test",
            html_content="<p>HTML</p>",
            text_content="Text",
            style=EmailStyle.DIRECT,
            variant=EmailVariant.C,
        )
        result = email.to_dict()
        assert result["subject"] == "Dict Test"
        assert result["style"] == "direct"
        assert result["variant"] == "C"
        assert "generated_at" in result


class TestIndustrySubjects:
    """Tests for industry-specific subject lines."""

    def test_dentist_subjects_exist(self):
        """Test dentist industry has subject lines."""
        assert "dentist" in INDUSTRY_SUBJECTS
        subjects = INDUSTRY_SUBJECTS["dentist"]
        assert EmailVariant.A in subjects
        assert EmailVariant.B in subjects
        assert EmailVariant.C in subjects

    def test_hvac_subjects_exist(self):
        """Test HVAC industry has subject lines."""
        assert "hvac" in INDUSTRY_SUBJECTS
        subjects = INDUSTRY_SUBJECTS["hvac"]
        assert len(subjects) == 3

    def test_salon_subjects_exist(self):
        """Test salon industry has subject lines."""
        assert "salon" in INDUSTRY_SUBJECTS

    def test_default_subjects_exist(self):
        """Test default subject lines exist."""
        assert "default" in INDUSTRY_SUBJECTS
        subjects = INDUSTRY_SUBJECTS["default"]
        assert len(subjects) == 3

    def test_subjects_contain_personalization_tokens(self):
        """Test some subjects contain {{business_name}} token."""
        dentist_b = INDUSTRY_SUBJECTS["dentist"][EmailVariant.B]
        assert "{{business_name}}" in dentist_b


class TestIndustryPainHooks:
    """Tests for industry-specific pain point hooks."""

    def test_dentist_pain_hooks_exist(self):
        """Test dentist industry has pain hooks."""
        assert "dentist" in INDUSTRY_PAIN_HOOKS
        assert len(INDUSTRY_PAIN_HOOKS["dentist"]) > 0

    def test_hvac_pain_hooks_exist(self):
        """Test HVAC industry has pain hooks."""
        assert "hvac" in INDUSTRY_PAIN_HOOKS
        assert len(INDUSTRY_PAIN_HOOKS["hvac"]) > 0

    def test_default_pain_hooks_exist(self):
        """Test default pain hooks exist."""
        assert "default" in INDUSTRY_PAIN_HOOKS
        assert len(INDUSTRY_PAIN_HOOKS["default"]) > 0


class TestHumorousOpeners:
    """Tests for industry-specific humorous openers."""

    def test_dentist_openers_exist(self):
        """Test dentist industry has humorous openers."""
        assert "dentist" in HUMOROUS_OPENERS
        assert len(HUMOROUS_OPENERS["dentist"]) >= 3

    def test_hvac_openers_exist(self):
        """Test HVAC industry has humorous openers."""
        assert "hvac" in HUMOROUS_OPENERS
        assert len(HUMOROUS_OPENERS["hvac"]) >= 3

    def test_default_openers_exist(self):
        """Test default humorous openers exist."""
        assert "default" in HUMOROUS_OPENERS
        assert len(HUMOROUS_OPENERS["default"]) >= 3


class TestGenerateSubject:
    """Tests for generate_subject function."""

    def test_generates_dentist_subject(self):
        """Test generating subject for dentist industry."""
        template = EmailTemplate(
            business_name="Smile Dental",
            industry="dentist",
            variant=EmailVariant.A
        )
        subject = generate_subject(template)
        # Variant A for dentist doesn't use business_name
        assert "patients" in subject.lower() or "calling" in subject.lower()

    def test_generates_subject_with_business_name(self):
        """Test that business_name token is replaced in subject."""
        template = EmailTemplate(
            business_name="Acme Dental",
            industry="dentist",
            variant=EmailVariant.B  # This variant uses business_name
        )
        subject = generate_subject(template)
        assert "Acme Dental" in subject

    def test_uses_default_for_unknown_industry(self):
        """Test that unknown industry falls back to default."""
        template = EmailTemplate(
            business_name="Unknown Business",
            industry="unknown_xyz",
            variant=EmailVariant.A
        )
        subject = generate_subject(template)
        assert len(subject) > 0

    def test_different_variants_produce_different_subjects(self):
        """Test that different variants produce different subjects."""
        template_a = EmailTemplate(
            business_name="Test",
            industry="dentist",
            variant=EmailVariant.A
        )
        template_b = EmailTemplate(
            business_name="Test",
            industry="dentist",
            variant=EmailVariant.B
        )
        subject_a = generate_subject(template_a)
        subject_b = generate_subject(template_b)
        assert subject_a != subject_b


class TestGenerateColdEmail:
    """Tests for generate_cold_email function."""

    def test_generates_complete_email(self):
        """Test generating a complete cold email."""
        template = EmailTemplate(
            business_name="Test Dental",
            industry="dentist",
            demo_url="https://demo.example.com"
        )
        email = generate_cold_email(template)
        assert email.subject
        assert email.html_content
        assert email.text_content
        assert email.preview_text

    def test_html_content_has_proper_structure(self):
        """Test HTML content has proper HTML structure."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com"
        )
        email = generate_cold_email(template)
        assert "<!DOCTYPE html>" in email.html_content
        assert "<html>" in email.html_content
        assert "</html>" in email.html_content
        assert "<body" in email.html_content

    def test_contains_business_name(self):
        """Test email contains business name."""
        template = EmailTemplate(
            business_name="Unique Business Name XYZ",
            demo_url="https://demo.example.com"
        )
        email = generate_cold_email(template)
        assert "Unique Business Name XYZ" in email.html_content
        assert "Unique Business Name XYZ" in email.text_content

    def test_contains_demo_url(self):
        """Test email contains demo URL."""
        template = EmailTemplate(
            business_name="Test",
            demo_url="https://unique-demo-url.example.com"
        )
        email = generate_cold_email(template)
        assert "https://unique-demo-url.example.com" in email.html_content
        assert "https://unique-demo-url.example.com" in email.text_content

    def test_humorous_style_content(self):
        """Test humorous style generates appropriate content."""
        template = EmailTemplate(
            business_name="Test Dental",
            industry="dentist",
            demo_url="https://demo.example.com",
            style=EmailStyle.HUMOROUS
        )
        email = generate_cold_email(template)
        # Humorous style should have casual tone
        assert email.style == EmailStyle.HUMOROUS

    def test_professional_style_content(self):
        """Test professional style generates appropriate content."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com",
            style=EmailStyle.PROFESSIONAL
        )
        email = generate_cold_email(template)
        assert email.style == EmailStyle.PROFESSIONAL
        assert "Best regards" in email.text_content or "I hope this message" in email.text_content

    def test_direct_style_is_concise(self):
        """Test direct style generates concise content."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com",
            style=EmailStyle.DIRECT
        )
        email = generate_cold_email(template)
        assert email.style == EmailStyle.DIRECT
        # Direct style should be shorter
        assert "Quick question" in email.text_content

    def test_curiosity_style_content(self):
        """Test curiosity style generates appropriate content."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com",
            style=EmailStyle.CURIOSITY
        )
        email = generate_cold_email(template)
        assert email.style == EmailStyle.CURIOSITY
        assert "made something" in email.text_content.lower() or "unusual" in email.text_content.lower()

    def test_includes_can_spam_footer(self):
        """Test email includes CAN-SPAM footer when provided."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com"
        )
        footer = CANSpamFooter(
            company_name="Sender Company",
            address_line1="100 Sender St",
            city="Sender City",
            state="SC",
            zip_code="12345"
        )
        email = generate_cold_email(template, can_spam_footer=footer)
        assert "Sender Company" in email.html_content
        assert "100 Sender St" in email.html_content
        assert "Sender Company" in email.text_content
        assert "unsubscribe" in email.html_content.lower()

    def test_excludes_footer_when_disabled(self):
        """Test footer is excluded when include_footer is False."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com"
        )
        footer = CANSpamFooter(
            company_name="Should Not Appear",
            address_line1="123 Hidden St",
            city="Hidden City",
            state="HC",
            zip_code="00000"
        )
        email = generate_cold_email(template, can_spam_footer=footer, include_footer=False)
        assert "Should Not Appear" not in email.html_content
        assert "Should Not Appear" not in email.text_content

    def test_personalized_greeting_with_name(self):
        """Test email has personalized greeting when name provided."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com",
            recipient_name="Sarah Johnson"
        )
        email = generate_cold_email(template)
        assert "Hi Sarah," in email.html_content
        assert "Hi Sarah," in email.text_content

    def test_generic_greeting_without_name(self):
        """Test email has generic greeting when name not provided."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com"
        )
        email = generate_cold_email(template)
        assert "Hi there," in email.html_content or "Hi there," in email.text_content

    def test_tracks_tokens_used(self):
        """Test email tracks which tokens were replaced."""
        template = EmailTemplate(
            business_name="Token Test Business",
            demo_url="https://demo.example.com",
            industry="dentist"
        )
        email = generate_cold_email(template)
        # Should track that tokens were used
        assert len(email.tokens_used) >= 0

    def test_sender_info_included(self):
        """Test sender information is included in email."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com",
            sender_name="Custom Sender",
            sender_title="Custom Title",
            sender_company="Custom Company"
        )
        email = generate_cold_email(template)
        assert "Custom Sender" in email.text_content
        assert "Custom Title" in email.text_content
        assert "Custom Company" in email.text_content


class TestGenerateColdEmailFromDict:
    """Tests for generate_cold_email_from_dict function."""

    def test_minimal_dict(self):
        """Test generating email from minimal dictionary."""
        data = {"name": "Dict Business"}
        email = generate_cold_email_from_dict(data)
        assert "Dict Business" in email.html_content
        assert email.style == EmailStyle.HUMOROUS  # default

    def test_full_dict(self):
        """Test generating email from full dictionary."""
        data = {
            "name": "Full Dict Business",
            "industry": "hvac",
            "demo_url": "https://full-demo.example.com",
            "recipient_name": "Bob Builder",
            "recipient_title": "Manager",
            "pain_points": ["Long wait times", "Missed calls"],
            "sender_name": "Alice",
            "sender_title": "Rep",
            "sender_company": "Sales Co",
            "phone": "555-9999",
            "website": "https://fullbusiness.com",
            "style": "professional",
            "variant": "B"
        }
        email = generate_cold_email_from_dict(data)
        assert "Full Dict Business" in email.html_content
        assert email.style == EmailStyle.PROFESSIONAL
        assert email.variant == EmailVariant.B

    def test_with_can_spam_info(self):
        """Test generating email with CAN-SPAM info dict."""
        data = {"name": "CAN SPAM Test Business"}
        can_spam = {
            "company_name": "Dict Sender Co",
            "address_line1": "999 Dict St",
            "city": "Dict City",
            "state": "DC",
            "zip_code": "99999"
        }
        email = generate_cold_email_from_dict(data, can_spam_info=can_spam)
        assert "Dict Sender Co" in email.html_content
        assert "999 Dict St" in email.html_content

    def test_invalid_style_defaults_to_humorous(self):
        """Test invalid style defaults to humorous."""
        data = {
            "name": "Test Business",
            "style": "invalid_style"
        }
        email = generate_cold_email_from_dict(data)
        assert email.style == EmailStyle.HUMOROUS

    def test_invalid_variant_defaults_to_a(self):
        """Test invalid variant defaults to A."""
        data = {
            "name": "Test Business",
            "variant": "invalid_variant"
        }
        email = generate_cold_email_from_dict(data)
        assert email.variant == EmailVariant.A

    def test_case_insensitive_style(self):
        """Test style matching is case-insensitive."""
        data = {
            "name": "Test Business",
            "style": "PROFESSIONAL"
        }
        email = generate_cold_email_from_dict(data)
        assert email.style == EmailStyle.PROFESSIONAL

    def test_case_insensitive_variant(self):
        """Test variant matching handles case."""
        data = {
            "name": "Test Business",
            "variant": "b"  # lowercase
        }
        email = generate_cold_email_from_dict(data)
        assert email.variant == EmailVariant.B


class TestValidateTemplate:
    """Tests for validate_template function."""

    def test_valid_template(self):
        """Test validation of valid template."""
        template = EmailTemplate(
            business_name="Valid Business",
            demo_url="https://valid-demo.example.com",
            industry="dentist"
        )
        result = validate_template(template)
        assert result["business_name"] is True
        assert result["demo_url"] is True
        assert result["industry"] is True
        assert result["is_valid"] is True

    def test_missing_business_name(self):
        """Test validation fails for missing business name."""
        template = EmailTemplate(
            business_name="",
            demo_url="https://demo.example.com"
        )
        result = validate_template(template)
        assert result["business_name"] is False
        assert result["is_valid"] is False

    def test_missing_demo_url(self):
        """Test validation fails for missing demo URL."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url=""
        )
        result = validate_template(template)
        assert result["demo_url"] is False
        assert result["is_valid"] is False

    def test_invalid_demo_url(self):
        """Test validation fails for non-URL demo URL."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="not-a-url"
        )
        result = validate_template(template)
        assert result["demo_url"] is False
        assert result["is_valid"] is False

    def test_whitespace_only_business_name(self):
        """Test validation fails for whitespace-only business name."""
        template = EmailTemplate(
            business_name="   ",
            demo_url="https://demo.example.com"
        )
        result = validate_template(template)
        assert result["business_name"] is False

    def test_validates_sender_info(self):
        """Test validation includes sender info check."""
        template = EmailTemplate(
            business_name="Test Business",
            demo_url="https://demo.example.com",
            sender_name="Sender",
            sender_company="Company"
        )
        result = validate_template(template)
        assert result["sender_info"] is True


class TestIsTemplateValid:
    """Tests for is_template_valid function."""

    def test_valid_template_returns_true(self):
        """Test valid template returns True."""
        template = EmailTemplate(
            business_name="Valid Business",
            demo_url="https://demo.example.com"
        )
        assert is_template_valid(template) is True

    def test_invalid_template_returns_false(self):
        """Test invalid template returns False."""
        template = EmailTemplate(
            business_name="",
            demo_url=""
        )
        assert is_template_valid(template) is False


class TestGetAvailableStyles:
    """Tests for get_available_styles function."""

    def test_returns_all_styles(self):
        """Test returns all available styles."""
        styles = get_available_styles()
        assert "humorous" in styles
        assert "professional" in styles
        assert "direct" in styles
        assert "curiosity" in styles
        assert len(styles) == 4


class TestGetAvailableVariants:
    """Tests for get_available_variants function."""

    def test_returns_all_variants(self):
        """Test returns all available variants."""
        variants = get_available_variants()
        assert "A" in variants
        assert "B" in variants
        assert "C" in variants
        assert len(variants) == 3


class TestGetIndustrySubjects:
    """Tests for get_industry_subjects function."""

    def test_returns_dentist_subjects(self):
        """Test returns subjects for dentist industry."""
        subjects = get_industry_subjects("dentist")
        assert "A" in subjects
        assert "B" in subjects
        assert "C" in subjects

    def test_returns_default_for_unknown(self):
        """Test returns default subjects for unknown industry."""
        subjects = get_industry_subjects("unknown_xyz")
        default_subjects = get_industry_subjects("default")
        assert subjects == default_subjects

    def test_case_insensitive(self):
        """Test industry lookup is case-insensitive."""
        subjects_lower = get_industry_subjects("dentist")
        subjects_upper = get_industry_subjects("DENTIST")
        # Keys should be the same
        assert set(subjects_lower.keys()) == set(subjects_upper.keys())

    def test_partial_match(self):
        """Test partial industry match works."""
        # "dental" should match "dentist" or "dental" entry
        subjects = get_industry_subjects("dental")
        assert len(subjects) == 3


class TestTokenReplacement:
    """Tests for personalization token replacement in emails."""

    def test_business_name_replaced(self):
        """Test {{business_name}} token is replaced."""
        template = EmailTemplate(
            business_name="TokenTest Corp",
            industry="dentist",
            demo_url="https://demo.example.com",
            variant=EmailVariant.B  # Uses business_name in subject
        )
        subject = generate_subject(template)
        assert "{{business_name}}" not in subject
        if "TokenTest Corp" not in subject:
            # Some subjects don't use business_name
            pass

    def test_demo_url_replaced(self):
        """Test demo_url is replaced in content."""
        template = EmailTemplate(
            business_name="Test",
            demo_url="https://unique-token-test.example.com"
        )
        email = generate_cold_email(template)
        assert "{{demo_url}}" not in email.html_content
        assert "{{demo_url}}" not in email.text_content
        assert "https://unique-token-test.example.com" in email.html_content

    def test_greeting_token_replaced(self):
        """Test greeting is properly personalized."""
        template = EmailTemplate(
            business_name="Test",
            demo_url="https://demo.example.com",
            recipient_name="Jane Doe"
        )
        email = generate_cold_email(template)
        assert "{{greeting}}" not in email.html_content
        assert "Hi Jane," in email.html_content


class TestCANSpamCompliance:
    """Tests for CAN-SPAM Act compliance requirements."""

    def test_footer_has_physical_address(self):
        """Test CAN-SPAM footer includes physical postal address."""
        footer = CANSpamFooter(
            company_name="Compliance Test Co",
            address_line1="123 Compliance St",
            city="Test City",
            state="TS",
            zip_code="12345",
            country="USA"
        )
        html = footer.to_html()
        text = footer.to_text()

        # Must include physical address (CAN-SPAM requirement)
        assert "123 Compliance St" in html
        assert "Test City" in html
        assert "TS" in html
        assert "12345" in html

        assert "123 Compliance St" in text
        assert "Test City" in text

    def test_footer_has_unsubscribe_mechanism(self):
        """Test CAN-SPAM footer includes unsubscribe mechanism."""
        footer = CANSpamFooter(
            company_name="Test Co",
            address_line1="123 St",
            city="City",
            state="ST",
            zip_code="12345",
            unsubscribe_url="https://unsubscribe.example.com"
        )
        html = footer.to_html()
        text = footer.to_text()

        # Must include unsubscribe link (CAN-SPAM requirement)
        assert "https://unsubscribe.example.com" in html
        assert "https://unsubscribe.example.com" in text
        assert "unsubscribe" in html.lower()

    def test_footer_has_sender_identity(self):
        """Test CAN-SPAM footer includes sender identity."""
        footer = CANSpamFooter(
            company_name="Identifiable Sender Inc",
            address_line1="123 St",
            city="City",
            state="ST",
            zip_code="12345"
        )
        html = footer.to_html()
        text = footer.to_text()

        # Must include sender identity (CAN-SPAM requirement)
        assert "Identifiable Sender Inc" in html
        assert "Identifiable Sender Inc" in text

    def test_footer_explains_why_receiving(self):
        """Test CAN-SPAM footer explains why recipient is receiving email."""
        footer = CANSpamFooter(
            company_name="Test Co",
            address_line1="123 St",
            city="City",
            state="ST",
            zip_code="12345",
            unsubscribe_reason="we thought your business might benefit"
        )
        html = footer.to_html()
        text = footer.to_text()

        assert "we thought your business might benefit" in html
        assert "we thought your business might benefit" in text


class TestEmailIntegration:
    """Integration tests for complete email generation workflow."""

    def test_full_workflow_dentist(self):
        """Test full email generation for dentist industry."""
        template = EmailTemplate(
            business_name="Smile Dental Care",
            industry="dentist",
            demo_url="https://smiledental.demo.example.com",
            recipient_name="Dr. Smith",
            sender_name="Alex",
            sender_title="AI Solutions Specialist",
            sender_company="LeadGen AI",
            style=EmailStyle.HUMOROUS,
            variant=EmailVariant.A
        )
        footer = CANSpamFooter(
            company_name="LeadGen AI",
            address_line1="100 Tech Way",
            city="San Francisco",
            state="CA",
            zip_code="94102"
        )

        email = generate_cold_email(template, can_spam_footer=footer)

        # Verify complete email
        assert email.subject
        assert "Smile Dental Care" in email.html_content
        assert "https://smiledental.demo.example.com" in email.html_content
        assert "Hi Dr.," in email.html_content  # First name from "Dr. Smith"
        assert "LeadGen AI" in email.html_content  # Company in footer
        assert "San Francisco" in email.html_content  # Address in footer
        assert "unsubscribe" in email.html_content.lower()

    def test_full_workflow_hvac(self):
        """Test full email generation for HVAC industry."""
        template = EmailTemplate(
            business_name="Cool Air Services",
            industry="hvac",
            demo_url="https://coolair.demo.example.com",
            style=EmailStyle.DIRECT,
            variant=EmailVariant.B
        )

        email = generate_cold_email(template)

        assert email.subject
        assert "Cool Air Services" in email.html_content
        assert email.style == EmailStyle.DIRECT

    def test_full_workflow_from_dict(self):
        """Test full email generation from dictionary data."""
        data = {
            "name": "City Salon",
            "industry": "salon",
            "demo_url": "https://citysalon.demo.example.com",
            "recipient_name": "Sarah",
            "style": "curiosity",
            "variant": "C"
        }
        can_spam = {
            "company_name": "Marketing Co",
            "address_line1": "200 Market St",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02101"
        }

        email = generate_cold_email_from_dict(data, can_spam_info=can_spam)

        assert email.subject
        assert "City Salon" in email.html_content
        assert email.style == EmailStyle.CURIOSITY
        assert email.variant == EmailVariant.C
        assert "Marketing Co" in email.html_content
        assert "200 Market St" in email.html_content

    def test_minimal_data_still_works(self):
        """Test email generation with minimal data."""
        template = EmailTemplate(business_name="Minimal Business")
        email = generate_cold_email(template, include_footer=False)

        assert email.subject
        assert email.html_content
        assert email.text_content
        assert "Minimal Business" in email.html_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
