"""Email template engine with personalization tokens and CAN-SPAM compliance.

This module provides a comprehensive email template system for cold outreach
campaigns with personalization support, industry-specific customization,
humor injection, and CAN-SPAM compliance.

Features:
- Multiple email template styles (professional, humorous, direct)
- Personalization token replacement ({{business_name}}, {{demo_url}}, etc.)
- Industry-specific pain points and messaging
- CAN-SPAM compliant footer generation
- HTML and plain text output
- A/B testing variant support

Usage:
    >>> from utils.email_templates import generate_cold_email, EmailTemplate
    >>> template = EmailTemplate(
    ...     business_name="Acme Dental",
    ...     industry="dentist",
    ...     demo_url="https://acme-dental.demo.app",
    ... )
    >>> email = generate_cold_email(template)
    >>> print(email.subject)
    Your patients are calling... but who's answering?
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EmailStyle(str, Enum):
    """Email tone/style options."""

    HUMOROUS = "humorous"      # Lighthearted, punchy copy (default for cold email)
    PROFESSIONAL = "professional"  # Formal, business-focused
    DIRECT = "direct"          # Short, to-the-point
    CURIOSITY = "curiosity"    # Mystery/intrigue-based


class EmailVariant(str, Enum):
    """A/B testing email variants."""

    A = "A"
    B = "B"
    C = "C"


@dataclass
class PersonalizationToken:
    """Represents a personalization token for email templates.

    Attributes:
        name: Token name (e.g., "business_name").
        placeholder: Placeholder in template (e.g., "{{business_name}}").
        value: Replacement value.
        required: Whether this token is required.
        default: Default value if not provided.
    """
    name: str
    placeholder: str
    value: Optional[str] = None
    required: bool = False
    default: Optional[str] = None

    def get_value(self) -> str:
        """Get the token value, using default if not set."""
        if self.value is not None:
            return self.value
        if self.default is not None:
            return self.default
        if self.required:
            raise ValueError(f"Required token '{self.name}' not provided")
        return ""


@dataclass
class CANSpamFooter:
    """CAN-SPAM compliant footer information.

    All fields are required by the CAN-SPAM Act for commercial emails.

    Attributes:
        company_name: Name of the sending company.
        address_line1: Street address.
        city: City name.
        state: State/province.
        zip_code: Postal/ZIP code.
        country: Country name.
        unsubscribe_reason: Why recipient is receiving the email.
        unsubscribe_url: URL for unsubscribing (supports {{unsubscribe}} token).
    """
    company_name: str
    address_line1: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    unsubscribe_reason: str = "we thought your business might benefit from AI automation"
    unsubscribe_url: str = "{{unsubscribe}}"

    def to_html(self) -> str:
        """Generate CAN-SPAM compliant HTML footer."""
        return f"""
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #666666; font-family: Arial, sans-serif;">
    <p style="margin: 0 0 8px 0;">
        <strong>{self.company_name}</strong><br>
        {self.address_line1}<br>
        {self.city}, {self.state} {self.zip_code}<br>
        {self.country}
    </p>
    <p style="margin: 8px 0;">
        You received this email because {self.unsubscribe_reason}.
    </p>
    <p style="margin: 8px 0;">
        To stop receiving these emails, <a href="{self.unsubscribe_url}" style="color: #0066cc; text-decoration: underline;">click here to unsubscribe</a>.
    </p>
</div>
"""

    def to_text(self) -> str:
        """Generate CAN-SPAM compliant plain text footer."""
        return f"""
--
{self.company_name}
{self.address_line1}
{self.city}, {self.state} {self.zip_code}
{self.country}

You received this email because {self.unsubscribe_reason}.
To stop receiving these emails, visit: {self.unsubscribe_url}
"""


@dataclass
class EmailTemplate:
    """Email template configuration with personalization data.

    Attributes:
        business_name: Target business name.
        industry: Industry category (dentist, hvac, salon, etc.).
        demo_url: URL to the personalized demo site.
        recipient_name: Name of the recipient (if known).
        recipient_title: Job title of the recipient (if known).
        pain_points: List of identified pain points for the business.
        sender_name: Name of the email sender.
        sender_title: Title of the sender.
        sender_company: Sending company name.
        phone: Business phone number.
        website: Business website URL.
        style: Email style (humorous, professional, direct, curiosity).
        variant: A/B test variant.
        custom_tokens: Additional custom personalization tokens.
    """
    business_name: str
    industry: str = ""
    demo_url: str = ""
    recipient_name: Optional[str] = None
    recipient_title: Optional[str] = None
    pain_points: List[str] = field(default_factory=list)
    sender_name: str = "Alex"
    sender_title: str = "AI Solutions Specialist"
    sender_company: str = "LeadGen AI"
    phone: Optional[str] = None
    website: Optional[str] = None
    style: EmailStyle = EmailStyle.HUMOROUS
    variant: EmailVariant = EmailVariant.A
    custom_tokens: Dict[str, str] = field(default_factory=dict)

    def get_greeting(self) -> str:
        """Get personalized greeting."""
        if self.recipient_name:
            return f"Hi {self.recipient_name.split()[0]},"
        return "Hi there,"

    def get_first_name(self) -> str:
        """Get recipient's first name or fallback."""
        if self.recipient_name:
            return self.recipient_name.split()[0]
        return "there"


@dataclass
class GeneratedEmail:
    """Generated email content ready for sending.

    Attributes:
        subject: Email subject line.
        html_content: Full HTML email body.
        text_content: Plain text email body.
        preview_text: Email preview text (shown in inbox).
        tokens_used: List of personalization tokens that were replaced.
        style: Email style used.
        variant: A/B variant.
        generated_at: Timestamp of generation.
    """
    subject: str
    html_content: str
    text_content: str
    preview_text: str = ""
    tokens_used: List[str] = field(default_factory=list)
    style: EmailStyle = EmailStyle.HUMOROUS
    variant: EmailVariant = EmailVariant.A
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "subject": self.subject,
            "html_content": self.html_content,
            "text_content": self.text_content,
            "preview_text": self.preview_text,
            "tokens_used": self.tokens_used,
            "style": self.style.value,
            "variant": self.variant.value,
            "generated_at": self.generated_at.isoformat(),
        }


# Industry-specific subject lines
INDUSTRY_SUBJECTS: Dict[str, Dict[EmailVariant, str]] = {
    "dentist": {
        EmailVariant.A: "Your patients are calling... but who's answering?",
        EmailVariant.B: "I built an AI receptionist just for {{business_name}}",
        EmailVariant.C: "No more missed calls at {{business_name}}?",
    },
    "dental": {
        EmailVariant.A: "Your patients are calling... but who's answering?",
        EmailVariant.B: "I built an AI receptionist just for {{business_name}}",
        EmailVariant.C: "No more missed calls at {{business_name}}?",
    },
    "hvac": {
        EmailVariant.A: "It's 2 AM and a furnace just died...",
        EmailVariant.B: "Your competitors are answering calls 24/7. Here's how.",
        EmailVariant.C: "{{business_name}}: What if you never missed an emergency call?",
    },
    "salon": {
        EmailVariant.A: "Your stylists are artists, not receptionists",
        EmailVariant.B: "{{business_name}}: Stop losing clients to voicemail",
        EmailVariant.C: "I created something for {{business_name}} (takes 30 sec to see)",
    },
    "auto": {
        EmailVariant.A: "{{business_name}}: Your phone is ringing. And ringing. And...",
        EmailVariant.B: "What if {{business_name}} could book appointments while you sleep?",
        EmailVariant.C: "Your service bays could be fuller tomorrow",
    },
    "medical": {
        EmailVariant.A: "Your patients deserve better than hold music",
        EmailVariant.B: "{{business_name}}: AI that actually understands healthcare",
        EmailVariant.C: "30% of patient calls go unanswered. Let's fix that.",
    },
    "legal": {
        EmailVariant.A: "Your next big client might be calling right now",
        EmailVariant.B: "{{business_name}}: Professional intake, 24/7",
        EmailVariant.C: "Missed calls = missed cases (there's a fix)",
    },
    "default": {
        EmailVariant.A: "What if {{business_name}} never missed another call?",
        EmailVariant.B: "I built something for {{business_name}} (30 sec to see)",
        EmailVariant.C: "Your phone is your biggest opportunity (and problem)",
    },
}

# Industry-specific pain point hooks
INDUSTRY_PAIN_HOOKS: Dict[str, List[str]] = {
    "dentist": [
        "Patients calling after hours go to voicemail and often book with your competitor instead",
        "Your front desk is overwhelmed juggling phones, check-ins, and insurance",
        "No-shows are eating into your chair time (and revenue)",
    ],
    "dental": [
        "Patients calling after hours go to voicemail and often book with your competitor instead",
        "Your front desk is overwhelmed juggling phones, check-ins, and insurance",
        "No-shows are eating into your chair time (and revenue)",
    ],
    "hvac": [
        "Emergency calls at 2 AM either wake you up or go to an expensive answering service",
        "Your techs are in the field while calls pile up unanswered",
        "Seasonal spikes mean lost business when you need it most",
    ],
    "salon": [
        "Your stylists keep getting pulled away from clients to answer phones",
        "Walk-in requests and booking conflicts create chaos at the front desk",
        "Last-minute cancellations leave empty chairs and lost revenue",
    ],
    "auto": [
        "Your service writers are too busy with customers to answer every call",
        "Customers calling for estimates often hang up when put on hold",
        "After-hours calls for breakdown assistance go unanswered",
    ],
    "medical": [
        "Patients spend too long on hold and sometimes give up",
        "Your staff is stretched thin handling appointments, refills, and questions",
        "After-hours urgent calls aren't being triaged properly",
    ],
    "legal": [
        "Potential clients calling after hours go to competitors who answer",
        "Your paralegals are spending too much time on basic intake calls",
        "Time-sensitive matters get delayed when phones aren't answered promptly",
    ],
    "default": [
        "Calls during busy periods go to voicemail and often aren't returned",
        "Your team is stretched thin handling routine phone inquiries",
        "After-hours calls represent lost opportunities",
    ],
}

# Humorous opening lines by industry
HUMOROUS_OPENERS: Dict[str, List[str]] = {
    "dentist": [
        "Fun fact: your phone rings approximately 47 times while you're elbow-deep in a root canal. (Okay, I made that number up, but it feels true, right?)",
        "I have a confession: I've been calling dental offices pretending to need an emergency appointment. (Just kidding. But I did notice something...)",
        "Your front desk person deserves a raise. And a clone. Here's the next best thing.",
    ],
    "dental": [
        "Fun fact: your phone rings approximately 47 times while you're elbow-deep in a root canal. (Okay, I made that number up, but it feels true, right?)",
        "I have a confession: I've been calling dental offices pretending to need an emergency appointment. (Just kidding. But I did notice something...)",
        "Your front desk person deserves a raise. And a clone. Here's the next best thing.",
    ],
    "hvac": [
        "Plot twist: your next $10,000 job is currently leaving a voicemail at 11 PM. On a Saturday.",
        "I've been thinking about your overnight emergency calls. (That's not creepy at all, is it?)",
        "Your competitors don't sleep. Neither should your phone system.",
    ],
    "salon": [
        "I'll cut right to it (pun absolutely intended):",
        "Your stylists didn't spend years perfecting their craft to become part-time receptionists.",
        "Confession: I may have called your salon 3 times to test your booking process. For science.",
    ],
    "auto": [
        "I've been thinking about your service bays. (Professionally! I promise it's not weird.)",
        "Fun fact: 60% of car owners choose shops based on who answers the phone first. I might have made that up, but it sounds right.",
        "Your mechanics are great at fixing cars. Answering phones? That's what robots are for.",
    ],
    "medical": [
        "I spent an hour on hold with a doctor's office last week. I now have strong opinions about hold music.",
        "HIPAA compliance is important. So is actually answering the phone.",
        "Your patients didn't choose you so they could talk to voicemail.",
    ],
    "legal": [
        "Fun fact: 42% of legal clients choose their attorney based on who called back first. (I may have made that stat up, but I bet your gut says it's true.)",
        "Your billable hours are too valuable to spend on intake calls.",
        "Someone's looking for a lawyer right now. They'll hire whoever answers first.",
    ],
    "default": [
        "I've been thinking about your phone. (Not in a weird way, I promise.)",
        "Fun fact: most businesses miss about 30% of their calls. That's a lot of potential revenue saying 'hello' to voicemail.",
        "Your team is talented. But even talented people can only answer one phone at a time.",
    ],
}


def _get_industry_key(industry: str) -> str:
    """Get normalized industry key for template lookup.

    Args:
        industry: Industry string.

    Returns:
        Normalized industry key.
    """
    if not industry:
        return "default"

    industry_lower = industry.lower().strip()

    # Direct match
    if industry_lower in INDUSTRY_SUBJECTS:
        return industry_lower

    # Partial match
    for key in INDUSTRY_SUBJECTS:
        if key in industry_lower or industry_lower in key:
            return key

    return "default"


def _replace_tokens(
    text: str,
    template: EmailTemplate,
    additional_tokens: Optional[Dict[str, str]] = None,
) -> tuple[str, List[str]]:
    """Replace personalization tokens in text.

    Args:
        text: Text containing {{token}} placeholders.
        template: EmailTemplate with personalization data.
        additional_tokens: Additional tokens to replace.

    Returns:
        Tuple of (replaced text, list of tokens that were replaced).
    """
    tokens_replaced: List[str] = []

    # Build token map
    token_map = {
        "business_name": template.business_name,
        "industry": template.industry,
        "demo_url": template.demo_url,
        "recipient_name": template.recipient_name or "",
        "recipient_first_name": template.get_first_name(),
        "recipient_title": template.recipient_title or "",
        "sender_name": template.sender_name,
        "sender_title": template.sender_title,
        "sender_company": template.sender_company,
        "phone": template.phone or "",
        "website": template.website or "",
        "greeting": template.get_greeting(),
    }

    # Add custom tokens
    token_map.update(template.custom_tokens)

    # Add additional tokens
    if additional_tokens:
        token_map.update(additional_tokens)

    # Replace all tokens
    result = text
    for token_name, token_value in token_map.items():
        placeholder = "{{" + token_name + "}}"
        if placeholder in result and token_value:
            result = result.replace(placeholder, str(token_value))
            tokens_replaced.append(token_name)

    return result, tokens_replaced


def _get_pain_point_content(template: EmailTemplate) -> str:
    """Get pain point content for email body.

    Args:
        template: EmailTemplate with business data.

    Returns:
        Formatted pain point content.
    """
    # Use provided pain points or industry defaults
    if template.pain_points:
        pain_points = template.pain_points[:3]  # Limit to 3
    else:
        industry_key = _get_industry_key(template.industry)
        pain_points = INDUSTRY_PAIN_HOOKS.get(
            industry_key,
            INDUSTRY_PAIN_HOOKS["default"]
        )[:2]

    if not pain_points:
        return ""

    # Format as bullet points
    bullets = "\n".join(f"  - {point}" for point in pain_points)
    return f"I noticed a few things about businesses like yours:\n\n{bullets}"


def _get_humorous_opener(template: EmailTemplate) -> str:
    """Get a humorous opening line based on industry.

    Args:
        template: EmailTemplate with business data.

    Returns:
        Humorous opening line.
    """
    industry_key = _get_industry_key(template.industry)
    openers = HUMOROUS_OPENERS.get(industry_key, HUMOROUS_OPENERS["default"])

    # Select based on variant for A/B testing consistency
    variant_index = {
        EmailVariant.A: 0,
        EmailVariant.B: 1,
        EmailVariant.C: 2,
    }.get(template.variant, 0)

    return openers[variant_index % len(openers)]


def _generate_humorous_email(template: EmailTemplate) -> tuple[str, str]:
    """Generate humorous email content.

    Args:
        template: EmailTemplate with business data.

    Returns:
        Tuple of (html_content, text_content).
    """
    opener = _get_humorous_opener(template)
    pain_content = _get_pain_point_content(template)

    # Plain text version
    text_body = f"""{template.get_greeting()}

{opener}

{pain_content}

So I did something a little forward: I built an AI receptionist specifically for {template.business_name}.

It answers calls 24/7, knows your services, and books appointments just like your best front desk person - except it never takes a lunch break.

I've set up a personalized demo so you can see (and hear) exactly how it would work for your business:

{template.demo_url}

Takes about 30 seconds to try. No commitment, no sales call required.

If it's not for you, no worries - but I think you'll be impressed.

Talk soon,
{template.sender_name}
{template.sender_title}
{template.sender_company}

P.S. The demo even handles those \"gotcha\" questions people ask to trip up AI. Try it!
"""

    # HTML version
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p style="margin-bottom: 16px;">{template.get_greeting()}</p>

    <p style="margin-bottom: 16px;">{opener}</p>

    <p style="margin-bottom: 16px;">{pain_content.replace(chr(10), '<br>')}</p>

    <p style="margin-bottom: 16px;">So I did something a little forward: <strong>I built an AI receptionist specifically for {template.business_name}</strong>.</p>

    <p style="margin-bottom: 16px;">It answers calls 24/7, knows your services, and books appointments just like your best front desk person - except it never takes a lunch break.</p>

    <p style="margin-bottom: 16px;">I've set up a personalized demo so you can see (and hear) exactly how it would work for your business:</p>

    <p style="margin: 24px 0; text-align: center;">
        <a href="{template.demo_url}" style="display: inline-block; background-color: #2563eb; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">Try Your Personalized Demo</a>
    </p>

    <p style="margin-bottom: 16px;">Takes about 30 seconds to try. No commitment, no sales call required.</p>

    <p style="margin-bottom: 16px;">If it's not for you, no worries - but I think you'll be impressed.</p>

    <p style="margin-bottom: 8px;">Talk soon,<br>
    <strong>{template.sender_name}</strong><br>
    {template.sender_title}<br>
    {template.sender_company}</p>

    <p style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #eeeeee; font-size: 13px; color: #666666;">
        <strong>P.S.</strong> The demo even handles those "gotcha" questions people ask to trip up AI. Try it!
    </p>
</body>
</html>
"""

    return html_body, text_body


def _generate_professional_email(template: EmailTemplate) -> tuple[str, str]:
    """Generate professional email content.

    Args:
        template: EmailTemplate with business data.

    Returns:
        Tuple of (html_content, text_content).
    """
    pain_content = _get_pain_point_content(template)

    text_body = f"""{template.get_greeting()}

I hope this message finds you well. I wanted to reach out regarding {template.business_name}'s phone operations.

{pain_content}

We've developed an AI-powered phone receptionist solution that addresses these challenges. Rather than tell you about it, I've prepared a personalized demonstration specifically for {template.business_name}:

{template.demo_url}

The demo takes approximately 30 seconds and requires no commitment. You'll be able to experience exactly how our solution would represent your business.

Key capabilities include:
  - 24/7 availability for all incoming calls
  - Knowledge of your specific services and pricing
  - Intelligent appointment scheduling
  - Natural conversation handling

I'd welcome the opportunity to discuss how this could benefit your operations.

Best regards,
{template.sender_name}
{template.sender_title}
{template.sender_company}
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p style="margin-bottom: 16px;">{template.get_greeting()}</p>

    <p style="margin-bottom: 16px;">I hope this message finds you well. I wanted to reach out regarding <strong>{template.business_name}'s</strong> phone operations.</p>

    <p style="margin-bottom: 16px;">{pain_content.replace(chr(10), '<br>')}</p>

    <p style="margin-bottom: 16px;">We've developed an AI-powered phone receptionist solution that addresses these challenges. Rather than tell you about it, I've prepared a personalized demonstration specifically for {template.business_name}:</p>

    <p style="margin: 24px 0; text-align: center;">
        <a href="{template.demo_url}" style="display: inline-block; background-color: #1e40af; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Your Personalized Demo</a>
    </p>

    <p style="margin-bottom: 16px;">The demo takes approximately 30 seconds and requires no commitment. You'll be able to experience exactly how our solution would represent your business.</p>

    <p style="margin-bottom: 16px;"><strong>Key capabilities include:</strong></p>
    <ul style="margin-bottom: 16px;">
        <li>24/7 availability for all incoming calls</li>
        <li>Knowledge of your specific services and pricing</li>
        <li>Intelligent appointment scheduling</li>
        <li>Natural conversation handling</li>
    </ul>

    <p style="margin-bottom: 16px;">I'd welcome the opportunity to discuss how this could benefit your operations.</p>

    <p style="margin-bottom: 8px;">Best regards,<br>
    <strong>{template.sender_name}</strong><br>
    {template.sender_title}<br>
    {template.sender_company}</p>
</body>
</html>
"""

    return html_body, text_body


def _generate_direct_email(template: EmailTemplate) -> tuple[str, str]:
    """Generate direct/concise email content.

    Args:
        template: EmailTemplate with business data.

    Returns:
        Tuple of (html_content, text_content).
    """
    text_body = f"""{template.get_greeting()}

Quick question: How many calls did {template.business_name} miss last week?

I built an AI receptionist demo specifically for your business. It answers 24/7 and knows your services.

See it in action (30 seconds): {template.demo_url}

No strings attached.

- {template.sender_name}
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p style="margin-bottom: 16px;">{template.get_greeting()}</p>

    <p style="margin-bottom: 16px;">Quick question: <strong>How many calls did {template.business_name} miss last week?</strong></p>

    <p style="margin-bottom: 16px;">I built an AI receptionist demo specifically for your business. It answers 24/7 and knows your services.</p>

    <p style="margin: 24px 0; text-align: center;">
        <a href="{template.demo_url}" style="display: inline-block; background-color: #059669; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">See It In Action (30 sec)</a>
    </p>

    <p style="margin-bottom: 16px;">No strings attached.</p>

    <p style="margin-bottom: 8px;">- {template.sender_name}</p>
</body>
</html>
"""

    return html_body, text_body


def _generate_curiosity_email(template: EmailTemplate) -> tuple[str, str]:
    """Generate curiosity-driven email content.

    Args:
        template: EmailTemplate with business data.

    Returns:
        Tuple of (html_content, text_content).
    """
    text_body = f"""{template.get_greeting()}

I made something for {template.business_name}.

It's a bit unusual - I created an AI assistant that already knows your business. Your services. Your hours. Even some tricky questions customers might ask.

I'm not sure if this is genius or crazy, but I figured the only way to know is to show you:

{template.demo_url}

30 seconds. That's all it takes to see it.

Curious what you'll think.

{template.sender_name}
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <p style="margin-bottom: 16px;">{template.get_greeting()}</p>

    <p style="margin-bottom: 16px;"><strong>I made something for {template.business_name}.</strong></p>

    <p style="margin-bottom: 16px;">It's a bit unusual - I created an AI assistant that already knows your business. Your services. Your hours. Even some tricky questions customers might ask.</p>

    <p style="margin-bottom: 16px;">I'm not sure if this is genius or crazy, but I figured the only way to know is to show you:</p>

    <p style="margin: 24px 0; text-align: center;">
        <a href="{template.demo_url}" style="display: inline-block; background-color: #7c3aed; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold;">See What I Built</a>
    </p>

    <p style="margin-bottom: 16px;">30 seconds. That's all it takes to see it.</p>

    <p style="margin-bottom: 16px;">Curious what you'll think.</p>

    <p style="margin-bottom: 8px;">{template.sender_name}</p>
</body>
</html>
"""

    return html_body, text_body


def generate_subject(
    template: EmailTemplate,
) -> str:
    """Generate email subject line based on template configuration.

    Args:
        template: EmailTemplate with business data.

    Returns:
        Email subject line with tokens replaced.
    """
    industry_key = _get_industry_key(template.industry)
    subjects = INDUSTRY_SUBJECTS.get(industry_key, INDUSTRY_SUBJECTS["default"])
    subject = subjects.get(template.variant, subjects[EmailVariant.A])

    # Replace tokens
    subject, _ = _replace_tokens(subject, template)

    return subject


def generate_cold_email(
    template: EmailTemplate,
    can_spam_footer: Optional[CANSpamFooter] = None,
    include_footer: bool = True,
) -> GeneratedEmail:
    """Generate a complete cold email with personalization and CAN-SPAM footer.

    Creates a personalized cold outreach email based on the template configuration.
    The email includes HTML and plain text versions, subject line, and all
    required CAN-SPAM compliance elements.

    Args:
        template: EmailTemplate with business and personalization data.
        can_spam_footer: CAN-SPAM footer info. Defaults to None (uses placeholder).
        include_footer: Whether to include CAN-SPAM footer. Default True.

    Returns:
        GeneratedEmail ready for sending via SendGrid.

    Example:
        >>> template = EmailTemplate(
        ...     business_name="Acme Dental",
        ...     industry="dentist",
        ...     demo_url="https://acme-dental.demo.app",
        ...     recipient_name="Dr. Smith",
        ... )
        >>> email = generate_cold_email(template)
        >>> print(email.subject)
        Your patients are calling... but who's answering?
        >>> print(email.text_content[:50])
        Hi Dr.,
    """
    # Generate content based on style
    style_generators = {
        EmailStyle.HUMOROUS: _generate_humorous_email,
        EmailStyle.PROFESSIONAL: _generate_professional_email,
        EmailStyle.DIRECT: _generate_direct_email,
        EmailStyle.CURIOSITY: _generate_curiosity_email,
    }

    generator = style_generators.get(template.style, _generate_humorous_email)
    html_content, text_content = generator(template)

    # Replace tokens in content
    html_content, html_tokens = _replace_tokens(html_content, template)
    text_content, text_tokens = _replace_tokens(text_content, template)

    # Combine unique tokens
    tokens_used = list(set(html_tokens + text_tokens))

    # Add CAN-SPAM footer if provided
    if include_footer and can_spam_footer:
        # Insert HTML footer before closing body tag
        if "</body>" in html_content:
            html_content = html_content.replace(
                "</body>",
                can_spam_footer.to_html() + "</body>"
            )
        else:
            html_content += can_spam_footer.to_html()

        text_content += can_spam_footer.to_text()

    # Generate subject
    subject = generate_subject(template)

    # Generate preview text (first ~100 chars of plain text)
    preview_text = text_content.strip()[:150].rsplit(" ", 1)[0] + "..."

    return GeneratedEmail(
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        preview_text=preview_text,
        tokens_used=tokens_used,
        style=template.style,
        variant=template.variant,
    )


def generate_cold_email_from_dict(
    data: Dict[str, Any],
    can_spam_info: Optional[Dict[str, str]] = None,
) -> GeneratedEmail:
    """Generate cold email from a dictionary of business data.

    Convenience function for generating emails directly from lead data
    or dossier information.

    Args:
        data: Dictionary with business data. Expected keys:
            - name (str): Business name (required)
            - industry (str): Industry category
            - demo_url (str): Demo site URL
            - recipient_name (str): Recipient name
            - recipient_title (str): Recipient title
            - pain_points (list): List of pain point strings
            - phone (str): Business phone
            - website (str): Business website
            - style (str): Email style ("humorous", "professional", etc.)
            - variant (str): A/B variant ("A", "B", "C")
        can_spam_info: Optional CAN-SPAM footer info dict.

    Returns:
        GeneratedEmail ready for sending.

    Example:
        >>> data = {
        ...     "name": "Acme Dental",
        ...     "industry": "dentist",
        ...     "demo_url": "https://acme.demo.app"
        ... }
        >>> email = generate_cold_email_from_dict(data)
    """
    # Build template from data
    style_str = data.get("style", "humorous").lower()
    style = EmailStyle(style_str) if style_str in [e.value for e in EmailStyle] else EmailStyle.HUMOROUS

    variant_str = data.get("variant", "A").upper()
    variant = EmailVariant(variant_str) if variant_str in [e.value for e in EmailVariant] else EmailVariant.A

    template = EmailTemplate(
        business_name=data.get("name", "Your Business"),
        industry=data.get("industry", ""),
        demo_url=data.get("demo_url", ""),
        recipient_name=data.get("recipient_name"),
        recipient_title=data.get("recipient_title"),
        pain_points=data.get("pain_points", []),
        sender_name=data.get("sender_name", "Alex"),
        sender_title=data.get("sender_title", "AI Solutions Specialist"),
        sender_company=data.get("sender_company", "LeadGen AI"),
        phone=data.get("phone"),
        website=data.get("website"),
        style=style,
        variant=variant,
    )

    # Build CAN-SPAM footer if provided
    footer = None
    if can_spam_info:
        footer = CANSpamFooter(
            company_name=can_spam_info.get("company_name", "LeadGen AI"),
            address_line1=can_spam_info.get("address_line1", "123 Main St"),
            city=can_spam_info.get("city", "San Francisco"),
            state=can_spam_info.get("state", "CA"),
            zip_code=can_spam_info.get("zip_code", "94102"),
            country=can_spam_info.get("country", "USA"),
            unsubscribe_reason=can_spam_info.get(
                "unsubscribe_reason",
                "we thought your business might benefit from AI automation"
            ),
        )

    return generate_cold_email(template, footer)


def get_available_styles() -> List[str]:
    """Get list of available email styles.

    Returns:
        List of style names.
    """
    return [style.value for style in EmailStyle]


def get_available_variants() -> List[str]:
    """Get list of available A/B test variants.

    Returns:
        List of variant names.
    """
    return [variant.value for variant in EmailVariant]


def get_industry_subjects(industry: str) -> Dict[str, str]:
    """Get available subject lines for an industry.

    Args:
        industry: Industry category string.

    Returns:
        Dictionary mapping variant to subject line.
    """
    industry_key = _get_industry_key(industry)
    subjects = INDUSTRY_SUBJECTS.get(industry_key, INDUSTRY_SUBJECTS["default"])
    return {variant.value: subject for variant, subject in subjects.items()}


def validate_template(template: EmailTemplate) -> Dict[str, bool]:
    """Validate email template configuration.

    Args:
        template: EmailTemplate to validate.

    Returns:
        Dictionary with validation results for each field.
    """
    results = {
        "business_name": bool(template.business_name and template.business_name.strip()),
        "demo_url": bool(template.demo_url and template.demo_url.startswith("http")),
        "industry": bool(template.industry),
        "sender_info": bool(template.sender_name and template.sender_company),
    }

    results["is_valid"] = all([
        results["business_name"],
        results["demo_url"],
    ])

    return results


def is_template_valid(template: EmailTemplate) -> bool:
    """Check if email template has required fields.

    Args:
        template: EmailTemplate to validate.

    Returns:
        True if template is valid for email generation.
    """
    validation = validate_template(template)
    return validation.get("is_valid", False)
