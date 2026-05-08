"""Brand guideline settings for the content_gen pack.

Mirrors the `_BrandGuidelinesSettings` class from
`content-generation-solution-accelerator-1/src/backend/settings.py` so that
brand voice, visual rules, and Responsible-AI guidance are defined in ONE
place and rendered into agent system_messages by `scripts/render_team.py`.

All fields are overridable via `BRAND_*` environment variables.
"""

from __future__ import annotations

import os
from typing import List, Optional

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _PYDANTIC_AVAILABLE = True
except ImportError:  # pragma: no cover - render script can also work without pydantic
    _PYDANTIC_AVAILABLE = False
    BaseSettings = object  # type: ignore[assignment,misc]
    SettingsConfigDict = dict  # type: ignore[assignment,misc]

    def Field(default=None, **_kwargs):  # type: ignore[misc]
        return default


def _parse_csv(value: str) -> List[str]:
    """Parse a comma-separated string into a list, stripping whitespace and empties."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


if _PYDANTIC_AVAILABLE:

    class BrandGuidelinesSettings(BaseSettings):
        """Brand voice, visual, and compliance rules for content generation."""

        model_config = SettingsConfigDict(
            env_prefix="BRAND_",
            extra="ignore",
            env_ignore_empty=True,
        )

        # Voice and tone
        tone: str = "Professional yet approachable"
        voice: str = "Innovative, trustworthy, customer-focused"

        # Content restrictions (comma-separated env vars)
        prohibited_words_str: str = Field(default="", alias="BRAND_PROHIBITED_WORDS")
        required_disclosures_str: str = Field(default="", alias="BRAND_REQUIRED_DISCLOSURES")

        # Visual guidelines
        primary_color: str = "#0078D4"
        secondary_color: str = "#107C10"
        image_style: str = "Modern, clean, minimalist with bright lighting"
        typography: str = "Sans-serif, bold headlines, readable body text"

        # Compliance rules
        max_headline_length: int = 60
        max_body_length: int = 500
        require_cta: bool = True

        @property
        def prohibited_words(self) -> List[str]:
            return _parse_csv(self.prohibited_words_str)

        @property
        def required_disclosures(self) -> List[str]:
            return _parse_csv(self.required_disclosures_str)

else:

    class BrandGuidelinesSettings:  # type: ignore[no-redef]
        """Pydantic-free fallback so the render script works without extra deps."""

        tone: str = "Professional yet approachable"
        voice: str = "Innovative, trustworthy, customer-focused"
        primary_color: str = "#0078D4"
        secondary_color: str = "#107C10"
        image_style: str = "Modern, clean, minimalist with bright lighting"
        typography: str = "Sans-serif, bold headlines, readable body text"
        max_headline_length: int = 60
        max_body_length: int = 500
        require_cta: bool = True

        def __init__(self) -> None:
            self.prohibited_words_str = os.environ.get("BRAND_PROHIBITED_WORDS", "")
            self.required_disclosures_str = os.environ.get("BRAND_REQUIRED_DISCLOSURES", "")
            for attr in (
                "tone",
                "voice",
                "primary_color",
                "secondary_color",
                "image_style",
                "typography",
            ):
                env_val = os.environ.get(f"BRAND_{attr.upper()}")
                if env_val:
                    setattr(self, attr, env_val)
            for int_attr in ("max_headline_length", "max_body_length"):
                env_val = os.environ.get(f"BRAND_{int_attr.upper()}")
                if env_val:
                    try:
                        setattr(self, int_attr, int(env_val))
                    except ValueError:
                        pass
            cta_env = os.environ.get("BRAND_REQUIRE_CTA")
            if cta_env is not None:
                self.require_cta = cta_env.strip().lower() in {"1", "true", "yes", "y", "on"}

        @property
        def prohibited_words(self) -> List[str]:
            return _parse_csv(self.prohibited_words_str)

        @property
        def required_disclosures(self) -> List[str]:
            return _parse_csv(self.required_disclosures_str)


# ---------------------------------------------------------------------------
# Prompt rendering helpers (attached as bound methods on the class)
# ---------------------------------------------------------------------------

def _get_compliance_prompt(self: BrandGuidelinesSettings) -> str:
    """Brand compliance + RAI block — embedded into Triage and Compliance agents."""
    prohibited = ", ".join(self.prohibited_words) if self.prohibited_words else "None specified"
    disclosures = ", ".join(self.required_disclosures) if self.required_disclosures else "None required"
    cta = "Yes" if self.require_cta else "No"
    return f"""
## Brand Compliance Rules

### Voice and Tone
- Tone: {self.tone}
- Voice: {self.voice}

### Content Restrictions
- Prohibited words: {prohibited}
- Required disclosures: {disclosures}
- Maximum headline length: approximately {self.max_headline_length} characters (headline field only)
- Maximum body length: approximately {self.max_body_length} characters (body field only, NOT including headline or tagline)
- CTA required: {cta}

**IMPORTANT: Character Limit Guidelines**
- Character limits apply to INDIVIDUAL fields: headline, body, and tagline are counted SEPARATELY
- The body limit ({self.max_body_length} chars) applies ONLY to the body/description text, not the combined content
- Do NOT flag character limit issues as ERROR - use WARNING severity since exact counting may vary
- When in doubt about length, do NOT flag it as a violation - focus on content quality instead

### Visual Guidelines
- Primary brand color: {self.primary_color}
- Secondary brand color: {self.secondary_color}
- Image style: {self.image_style}
- Typography: {self.typography}

### Compliance Severity Levels
- ERROR: Legal/regulatory violations that MUST be fixed before content can be used
- WARNING: Brand guideline deviations that should be reviewed
- INFO: Style suggestions for improvement (optional)

When validating content, categorize each violation with the appropriate severity level.

## Responsible AI Guidelines

### Content Safety Principles
You MUST follow these Responsible AI principles in ALL generated content:

**Fairness & Inclusion**
- Ensure diverse and inclusive representation in all content
- Avoid stereotypes based on gender, race, age, disability, religion, or background
- Use gender-neutral language when appropriate
- Represent diverse body types, abilities, and backgrounds authentically

**Reliability & Safety**
- Do not generate content that could cause physical, emotional, or financial harm
- Avoid misleading claims, exaggerations, or false promises
- Ensure factual accuracy; do not fabricate statistics or testimonials
- Include appropriate disclaimers for health, financial, or legal topics

**Privacy & Security**
- Never include real personal information (names, addresses, phone numbers)
- Do not reference specific individuals without explicit permission
- Avoid content that could enable identity theft or fraud

**Transparency**
- Be transparent about AI-generated content when required by regulations
- Do not create content designed to deceive or manipulate
- Avoid deepfake-style content or impersonation

**Harmful Content Prevention**
- NEVER generate hateful, discriminatory, or offensive content
- NEVER create violent, graphic, or disturbing imagery
- NEVER produce sexually explicit or suggestive content
- NEVER generate content promoting illegal activities
- NEVER create content that exploits or harms minors

### Image Generation Specific Guidelines
When generating images:
- Do not create realistic images of identifiable real people
- Avoid generating images that could be mistaken for real photographs in misleading contexts
- Ensure generated humans represent diverse demographics positively
- Do not generate images depicting violence, weapons, or harmful activities
- Avoid culturally insensitive or appropriative imagery

**IMPORTANT - Photorealistic Product Images Are ACCEPTABLE:**
Photorealistic style for PRODUCT photography (e.g., paint cans, products, room scenes, textures)
is our standard marketing style and should NOT be flagged as a violation. Only flag photorealistic
content when it involves:
- Fake/deepfake identifiable real people (SEVERITY: ERROR)
- Misleading contexts designed to deceive consumers (SEVERITY: ERROR)
Do NOT flag photorealistic product shots, room scenes, or marketing imagery as violations.

### Compliance Validation
The Compliance Agent MUST flag any content that violates these RAI principles as SEVERITY: ERROR.
RAI violations are non-negotiable and content must be regenerated.
""".strip()


def _get_text_generation_prompt(self: BrandGuidelinesSettings) -> str:
    """Brand voice + RAI rules for text content generation."""
    prohibited = ", ".join(self.prohibited_words) if self.prohibited_words else "No restrictions"
    disclosures = ", ".join(self.required_disclosures) if self.required_disclosures else "None required"
    cta_line = "Always include a clear call-to-action" if self.require_cta else "CTA is optional"
    return f"""
## Brand Voice Guidelines

Write content that embodies these characteristics:
- Tone: {self.tone}
- Voice: {self.voice}

### Writing Rules
- Keep headlines under approximately {self.max_headline_length} characters
- Keep body copy (description) under approximately {self.max_body_length} characters
- Note: Character limits are approximate guidelines - focus on concise, impactful writing
- {cta_line}
- NEVER use these words: {prohibited}
- Include these disclosures when applicable: {disclosures}

## Responsible AI - Text Content Rules

NEVER generate text that:
- Contains hateful, discriminatory, or offensive language
- Makes false claims, fabricated statistics, or fake testimonials
- Includes misleading health, financial, or legal advice
- Uses manipulative or deceptive persuasion tactics
- Promotes illegal activities or harmful behaviors
- Stereotypes any group based on gender, race, age, or background
- Contains sexually explicit or inappropriate content
- Could cause physical, emotional, or financial harm

ALWAYS ensure:
- Factual accuracy and honest representation
- Inclusive language that respects all audiences
- Clear disclaimers where legally required
- Transparency about product limitations
- Respectful portrayal of diverse communities
""".strip()


def _get_image_generation_prompt(self: BrandGuidelinesSettings) -> str:
    """Brand visual + RAI rules for image content generation."""
    return f"""
## ⚠️ MANDATORY: ZERO TEXT IN IMAGE

THE GENERATED IMAGE MUST NOT CONTAIN ANY TEXT WHATSOEVER:
- ❌ NO product names (do not write paint or product names)
- ❌ NO color names (do not write "white", "blue", "gray", etc.)
- ❌ NO words, letters, numbers, or typography of any kind
- ❌ NO labels, captions, signage, or watermarks
- ❌ NO logos or brand names
- ✓ ONLY visual elements: paint swatches, color samples, textures, scenes

This is a strict requirement. Text will be added separately by the application.

## Brand Visual Guidelines

Create images that follow these guidelines:
- Style: {self.image_style}
- Primary brand color to incorporate: {self.primary_color}
- Secondary accent color: {self.secondary_color}
- Professional, high-quality imagery suitable for marketing
- Bright, optimistic lighting
- Clean composition with 30% negative space
- No competitor products or logos
- Diverse representation if people are shown

## Color Accuracy

When product colors are specified (especially with hex codes):
- Reproduce the exact colors as accurately as possible
- Use the hex codes as the definitive color reference
- Ensure paint/product colors match the descriptions precisely

## Responsible AI - Image Generation Rules

NEVER generate images that contain:
- Real identifiable people (celebrities, politicians, public figures)
- Violence, weapons, blood, or injury
- Sexually explicit, suggestive, or inappropriate content
- Hateful symbols, slurs, or discriminatory imagery
- Content exploiting or depicting minors inappropriately
- Deepfake-style realistic faces intended to deceive
- Culturally insensitive stereotypes or appropriation
- Illegal activities or substances

ALWAYS ensure:
- Diverse and positive representation of people
- Age-appropriate content suitable for all audiences
- Authentic portrayal without harmful stereotypes
- Clear distinction that this is marketing imagery
- Respect for cultural and religious sensitivities
""".strip()


# Bind the rendering helpers as methods so callers can write
# `brand.get_compliance_prompt()` (matching the reference settings.py API).
BrandGuidelinesSettings.get_compliance_prompt = _get_compliance_prompt  # type: ignore[attr-defined]
BrandGuidelinesSettings.get_text_generation_prompt = _get_text_generation_prompt  # type: ignore[attr-defined]
BrandGuidelinesSettings.get_image_generation_prompt = _get_image_generation_prompt  # type: ignore[attr-defined]


_brand_singleton: Optional[BrandGuidelinesSettings] = None


def get_brand_guidelines() -> BrandGuidelinesSettings:
    """Return a shared brand guidelines instance (loads env vars on first call)."""
    global _brand_singleton
    if _brand_singleton is None:
        _brand_singleton = BrandGuidelinesSettings()
    return _brand_singleton


__all__ = ["BrandGuidelinesSettings", "get_brand_guidelines"]
