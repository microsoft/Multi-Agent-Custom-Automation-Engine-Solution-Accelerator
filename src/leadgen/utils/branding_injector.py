"""Branding injection utility for prospect demo site customization.

This module generates environment variables for Vercel deployments that
customize the demo-frontend with prospect-specific branding (logo, colors,
business name, contact info).

The environment variables generated match those expected by the demo-frontend's
`getBrandingFromEnv()` function in lib/branding.ts:
- NEXT_PUBLIC_BUSINESS_NAME
- NEXT_PUBLIC_PRIMARY_COLOR
- NEXT_PUBLIC_SECONDARY_COLOR
- NEXT_PUBLIC_ACCENT_COLOR
- NEXT_PUBLIC_LOGO_URL
- NEXT_PUBLIC_TAGLINE
- NEXT_PUBLIC_INDUSTRY
- NEXT_PUBLIC_PHONE
- NEXT_PUBLIC_ADDRESS
- NEXT_PUBLIC_WEBSITE
- NEXT_PUBLIC_TWILIO_NUMBER
- NEXT_PUBLIC_VOICE_WEBSOCKET_URL
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class BrandingConfig:
    """Configuration for prospect demo site branding.

    Attributes:
        business_name: Business name displayed in header and page title.
        primary_color: Primary brand color (hex format, e.g., #2563eb).
        secondary_color: Secondary/accent color (hex format).
        accent_color: Accent color for highlights (hex format).
        logo_url: URL to business logo image.
        tagline: Business tagline or slogan.
        industry: Industry type for default styling.
        phone: Contact phone number.
        address: Business address.
        website: Business website URL.
        twilio_number: Twilio phone number for voice demos.
        voice_websocket_url: WebSocket URL for voice server.
    """
    business_name: str
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    logo_url: Optional[str] = None
    tagline: Optional[str] = None
    industry: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    twilio_number: Optional[str] = None
    voice_websocket_url: Optional[str] = None


@dataclass
class BrandingValidationResult:
    """Result of branding configuration validation.

    Attributes:
        is_valid: Whether the configuration is valid.
        errors: List of validation error messages.
        warnings: List of validation warning messages.
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# Industry-specific default color palettes (matching demo-frontend/lib/branding.ts)
INDUSTRY_COLORS: Dict[str, Dict[str, str]] = {
    "dentist": {
        "primary_color": "#0891b2",    # Cyan-600
        "secondary_color": "#0e7490",  # Cyan-700
        "accent_color": "#06b6d4",     # Cyan-500
    },
    "dental": {
        "primary_color": "#0891b2",
        "secondary_color": "#0e7490",
        "accent_color": "#06b6d4",
    },
    "hvac": {
        "primary_color": "#ea580c",    # Orange-600
        "secondary_color": "#c2410c",  # Orange-700
        "accent_color": "#f97316",     # Orange-500
    },
    "salon": {
        "primary_color": "#db2777",    # Pink-600
        "secondary_color": "#be185d",  # Pink-700
        "accent_color": "#ec4899",     # Pink-500
    },
    "hair": {
        "primary_color": "#db2777",
        "secondary_color": "#be185d",
        "accent_color": "#ec4899",
    },
    "auto": {
        "primary_color": "#dc2626",    # Red-600
        "secondary_color": "#b91c1c",  # Red-700
        "accent_color": "#ef4444",     # Red-500
    },
    "automotive": {
        "primary_color": "#dc2626",
        "secondary_color": "#b91c1c",
        "accent_color": "#ef4444",
    },
    "medical": {
        "primary_color": "#2563eb",    # Blue-600
        "secondary_color": "#1d4ed8",  # Blue-700
        "accent_color": "#3b82f6",     # Blue-500
    },
    "healthcare": {
        "primary_color": "#2563eb",
        "secondary_color": "#1d4ed8",
        "accent_color": "#3b82f6",
    },
    "legal": {
        "primary_color": "#4f46e5",    # Indigo-600
        "secondary_color": "#4338ca",  # Indigo-700
        "accent_color": "#6366f1",     # Indigo-500
    },
    "attorney": {
        "primary_color": "#4f46e5",
        "secondary_color": "#4338ca",
        "accent_color": "#6366f1",
    },
    "restaurant": {
        "primary_color": "#ca8a04",    # Yellow-600
        "secondary_color": "#a16207",  # Yellow-700
        "accent_color": "#eab308",     # Yellow-500
    },
    "fitness": {
        "primary_color": "#16a34a",    # Green-600
        "secondary_color": "#15803d",  # Green-700
        "accent_color": "#22c55e",     # Green-500
    },
    "gym": {
        "primary_color": "#16a34a",
        "secondary_color": "#15803d",
        "accent_color": "#22c55e",
    },
    "plumber": {
        "primary_color": "#0284c7",    # Sky-600
        "secondary_color": "#0369a1",  # Sky-700
        "accent_color": "#0ea5e9",     # Sky-500
    },
    "plumbing": {
        "primary_color": "#0284c7",
        "secondary_color": "#0369a1",
        "accent_color": "#0ea5e9",
    },
    "electrician": {
        "primary_color": "#ca8a04",    # Yellow-600
        "secondary_color": "#a16207",  # Yellow-700
        "accent_color": "#eab308",     # Yellow-500
    },
    "electrical": {
        "primary_color": "#ca8a04",
        "secondary_color": "#a16207",
        "accent_color": "#eab308",
    },
    "general": {
        "primary_color": "#2563eb",    # Blue-600
        "secondary_color": "#64748b",  # Slate-500
        "accent_color": "#10b981",     # Emerald-500
    },
}

# Default branding values
DEFAULT_BRANDING: Dict[str, str] = {
    "primary_color": "#2563eb",    # Blue-600
    "secondary_color": "#64748b",  # Slate-500
    "accent_color": "#10b981",     # Emerald-500
    "tagline": "Your AI Appointment Assistant",
}

# Industry-specific default taglines
INDUSTRY_TAGLINES: Dict[str, str] = {
    "dentist": "Your AI Dental Receptionist",
    "dental": "Your AI Dental Receptionist",
    "hvac": "Your 24/7 HVAC Scheduling Assistant",
    "salon": "Your AI Salon Booking Assistant",
    "hair": "Your AI Salon Booking Assistant",
    "auto": "Your AI Auto Service Scheduler",
    "automotive": "Your AI Auto Service Scheduler",
    "medical": "Your AI Medical Appointment Assistant",
    "healthcare": "Your AI Medical Appointment Assistant",
    "legal": "Your AI Legal Consultation Scheduler",
    "attorney": "Your AI Legal Consultation Scheduler",
    "restaurant": "Your AI Reservation Assistant",
    "fitness": "Your AI Fitness Class Scheduler",
    "gym": "Your AI Fitness Class Scheduler",
    "plumber": "Your 24/7 Plumbing Service Scheduler",
    "plumbing": "Your 24/7 Plumbing Service Scheduler",
    "electrician": "Your 24/7 Electrical Service Scheduler",
    "electrical": "Your 24/7 Electrical Service Scheduler",
}


def _is_valid_hex_color(color: str) -> bool:
    """Check if a string is a valid hex color.

    Args:
        color: Color string to validate.

    Returns:
        True if color is a valid 6-digit hex color (with or without #).
    """
    if not color:
        return False

    # Allow colors with or without # prefix
    clean = color.lstrip("#")
    if len(clean) != 6:
        return False

    try:
        int(clean, 16)
        return True
    except ValueError:
        return False


def _normalize_hex_color(color: str) -> str:
    """Normalize hex color to include # prefix.

    Args:
        color: Hex color string.

    Returns:
        Normalized hex color with # prefix.
    """
    if not color:
        return ""

    clean = color.lstrip("#")
    return f"#{clean.lower()}"


def _is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL.

    Args:
        url: URL string to validate.

    Returns:
        True if URL is valid.
    """
    if not url:
        return False

    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def _normalize_phone(phone: str) -> str:
    """Normalize phone number format.

    Args:
        phone: Phone number string.

    Returns:
        Normalized phone number.
    """
    if not phone:
        return ""

    # Remove all non-digit characters except +
    digits = re.sub(r"[^\d+]", "", phone)

    # If starts with 1 and has 11 digits, it's US format
    if digits.startswith("1") and len(digits) == 11:
        return f"+{digits}"

    # If has 10 digits, assume US and add +1
    if len(digits) == 10:
        return f"+1{digits}"

    # If already has + prefix, return as is
    if digits.startswith("+"):
        return digits

    # Otherwise return original (might be international)
    return phone


def _get_industry_key(industry: str) -> str:
    """Get normalized industry key for color lookup.

    Args:
        industry: Industry string.

    Returns:
        Normalized industry key.
    """
    if not industry:
        return "general"

    industry_lower = industry.lower().strip()

    # Direct match
    if industry_lower in INDUSTRY_COLORS:
        return industry_lower

    # Partial match
    for key in INDUSTRY_COLORS:
        if key in industry_lower or industry_lower in key:
            return key

    return "general"


def validate_branding_config(config: BrandingConfig) -> BrandingValidationResult:
    """Validate a branding configuration.

    Args:
        config: BrandingConfig to validate.

    Returns:
        BrandingValidationResult with validation status and any errors/warnings.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Required field: business_name
    if not config.business_name or not config.business_name.strip():
        errors.append("Business name is required")

    # Validate color formats
    if config.primary_color and not _is_valid_hex_color(config.primary_color):
        errors.append(f"Invalid primary color format: {config.primary_color} (expected hex like #2563eb)")

    if config.secondary_color and not _is_valid_hex_color(config.secondary_color):
        errors.append(f"Invalid secondary color format: {config.secondary_color} (expected hex like #64748b)")

    if config.accent_color and not _is_valid_hex_color(config.accent_color):
        errors.append(f"Invalid accent color format: {config.accent_color} (expected hex like #10b981)")

    # Validate URL formats
    if config.logo_url and not _is_valid_url(config.logo_url):
        warnings.append(f"Invalid logo URL format: {config.logo_url}")

    if config.website and not _is_valid_url(config.website):
        warnings.append(f"Invalid website URL format: {config.website}")

    if config.voice_websocket_url:
        if not config.voice_websocket_url.startswith(("ws://", "wss://")):
            warnings.append(f"Voice WebSocket URL should start with ws:// or wss://")

    # Warn about missing recommended fields
    if not config.phone:
        warnings.append("Phone number not provided - call button will not work")

    if not config.industry:
        warnings.append("Industry not specified - using default colors")

    return BrandingValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def get_industry_colors(industry: str) -> Dict[str, str]:
    """Get default colors for an industry.

    Args:
        industry: Industry category string.

    Returns:
        Dictionary with primary_color, secondary_color, accent_color.
    """
    key = _get_industry_key(industry)
    return INDUSTRY_COLORS.get(key, INDUSTRY_COLORS["general"]).copy()


def get_industry_tagline(industry: str) -> str:
    """Get default tagline for an industry.

    Args:
        industry: Industry category string.

    Returns:
        Industry-specific tagline or default.
    """
    key = _get_industry_key(industry)
    return INDUSTRY_TAGLINES.get(key, DEFAULT_BRANDING["tagline"])


def branding_config_from_lead(lead_data: Dict[str, Any]) -> BrandingConfig:
    """Create BrandingConfig from lead/dossier data.

    Extracts branding information from lead data (e.g., from Lead model
    or research dossier) and creates a BrandingConfig.

    Args:
        lead_data: Dictionary with lead information. Expected keys:
            - name (str): Business name (required)
            - phone (str): Phone number
            - address (str): Business address
            - website (str): Website URL
            - industry (str): Industry category
            - logo_url (str): Logo URL (if extracted)
            - primary_color (str): Brand color (if extracted)
            - tagline (str): Business tagline
            - twilio_number (str): Twilio number for demos
            - voice_websocket_url (str): Voice server WebSocket URL

    Returns:
        BrandingConfig populated from lead data.
    """
    industry = lead_data.get("industry", "")
    industry_colors = get_industry_colors(industry)

    return BrandingConfig(
        business_name=lead_data.get("name", "Demo Business"),
        primary_color=lead_data.get("primary_color") or industry_colors.get("primary_color"),
        secondary_color=lead_data.get("secondary_color") or industry_colors.get("secondary_color"),
        accent_color=lead_data.get("accent_color") or industry_colors.get("accent_color"),
        logo_url=lead_data.get("logo_url"),
        tagline=lead_data.get("tagline") or get_industry_tagline(industry),
        industry=industry,
        phone=lead_data.get("phone"),
        address=lead_data.get("address"),
        website=lead_data.get("website"),
        twilio_number=lead_data.get("twilio_number"),
        voice_websocket_url=lead_data.get("voice_websocket_url"),
    )


def inject_branding(
    config: BrandingConfig,
    twilio_number: Optional[str] = None,
    voice_websocket_url: Optional[str] = None,
    validate: bool = True,
) -> Dict[str, str]:
    """Generate environment variables for Vercel deployment.

    Creates a dictionary of NEXT_PUBLIC_* environment variables that
    customize the demo-frontend for a specific prospect.

    Args:
        config: BrandingConfig with prospect branding.
        twilio_number: Override Twilio number (if not in config).
        voice_websocket_url: Override voice WebSocket URL (if not in config).
        validate: Whether to validate config before generating (default True).

    Returns:
        Dictionary mapping environment variable names to values.

    Raises:
        ValueError: If validation is enabled and config is invalid.

    Example:
        >>> config = BrandingConfig(
        ...     business_name="Acme Dental",
        ...     industry="dentist",
        ...     phone="555-123-4567"
        ... )
        >>> env_vars = inject_branding(config)
        >>> print(env_vars["NEXT_PUBLIC_BUSINESS_NAME"])
        Acme Dental
    """
    # Validate if requested
    if validate:
        result = validate_branding_config(config)
        if not result.is_valid:
            raise ValueError(f"Invalid branding config: {'; '.join(result.errors)}")

    # Get industry-specific defaults
    industry_colors = get_industry_colors(config.industry or "")

    # Build environment variables dictionary
    env_vars: Dict[str, str] = {}

    # Business name (required)
    env_vars["NEXT_PUBLIC_BUSINESS_NAME"] = config.business_name

    # Colors (with industry defaults)
    primary = config.primary_color or industry_colors.get("primary_color") or DEFAULT_BRANDING["primary_color"]
    secondary = config.secondary_color or industry_colors.get("secondary_color") or DEFAULT_BRANDING["secondary_color"]
    accent = config.accent_color or industry_colors.get("accent_color") or DEFAULT_BRANDING["accent_color"]

    env_vars["NEXT_PUBLIC_PRIMARY_COLOR"] = _normalize_hex_color(primary)
    env_vars["NEXT_PUBLIC_SECONDARY_COLOR"] = _normalize_hex_color(secondary)
    env_vars["NEXT_PUBLIC_ACCENT_COLOR"] = _normalize_hex_color(accent)

    # Industry
    if config.industry:
        env_vars["NEXT_PUBLIC_INDUSTRY"] = config.industry

    # Tagline (with industry default)
    tagline = config.tagline or get_industry_tagline(config.industry or "")
    env_vars["NEXT_PUBLIC_TAGLINE"] = tagline

    # Optional fields (only include if provided)
    if config.logo_url:
        env_vars["NEXT_PUBLIC_LOGO_URL"] = config.logo_url

    if config.phone:
        env_vars["NEXT_PUBLIC_PHONE"] = config.phone

    if config.address:
        env_vars["NEXT_PUBLIC_ADDRESS"] = config.address

    if config.website:
        env_vars["NEXT_PUBLIC_WEBSITE"] = config.website

    # Twilio number (with override)
    twilio = twilio_number or config.twilio_number
    if twilio:
        env_vars["NEXT_PUBLIC_TWILIO_NUMBER"] = _normalize_phone(twilio)

    # Voice WebSocket URL (with override)
    ws_url = voice_websocket_url or config.voice_websocket_url
    if ws_url:
        env_vars["NEXT_PUBLIC_VOICE_WEBSOCKET_URL"] = ws_url

    return env_vars


def inject_branding_from_lead(
    lead_data: Dict[str, Any],
    twilio_number: Optional[str] = None,
    voice_websocket_url: Optional[str] = None,
    validate: bool = True,
) -> Dict[str, str]:
    """Generate environment variables from lead data.

    Convenience function that combines branding_config_from_lead and
    inject_branding for common use case of generating env vars directly
    from lead/dossier data.

    Args:
        lead_data: Dictionary with lead information.
        twilio_number: Override Twilio number.
        voice_websocket_url: Override voice WebSocket URL.
        validate: Whether to validate config before generating.

    Returns:
        Dictionary mapping environment variable names to values.

    Example:
        >>> lead = {
        ...     "name": "Acme Dental",
        ...     "industry": "dentist",
        ...     "phone": "555-123-4567",
        ...     "website": "https://acme-dental.com"
        ... }
        >>> env_vars = inject_branding_from_lead(lead)
        >>> print(env_vars["NEXT_PUBLIC_BUSINESS_NAME"])
        Acme Dental
    """
    config = branding_config_from_lead(lead_data)

    # Apply overrides to config
    if twilio_number:
        config.twilio_number = twilio_number
    if voice_websocket_url:
        config.voice_websocket_url = voice_websocket_url

    return inject_branding(config, validate=validate)


def format_env_file(env_vars: Dict[str, str]) -> str:
    """Format environment variables as .env file content.

    Args:
        env_vars: Dictionary of environment variables.

    Returns:
        String formatted as .env file content.

    Example:
        >>> env_vars = {"NEXT_PUBLIC_BUSINESS_NAME": "Acme", "NEXT_PUBLIC_PHONE": "555-1234"}
        >>> print(format_env_file(env_vars))
        NEXT_PUBLIC_BUSINESS_NAME="Acme"
        NEXT_PUBLIC_PHONE="555-1234"
    """
    lines = []
    for key, value in sorted(env_vars.items()):
        # Escape special characters in value
        escaped_value = value.replace('"', '\\"')
        lines.append(f'{key}="{escaped_value}"')
    return "\n".join(lines)


def format_vercel_env_json(env_vars: Dict[str, str]) -> List[Dict[str, str]]:
    """Format environment variables for Vercel API.

    Creates the format expected by Vercel's environment variable API.

    Args:
        env_vars: Dictionary of environment variables.

    Returns:
        List of dicts with 'key' and 'value' for Vercel API.

    Example:
        >>> env_vars = {"NEXT_PUBLIC_BUSINESS_NAME": "Acme"}
        >>> result = format_vercel_env_json(env_vars)
        >>> print(result)
        [{'key': 'NEXT_PUBLIC_BUSINESS_NAME', 'value': 'Acme', 'target': ['production', 'preview']}]
    """
    return [
        {
            "key": key,
            "value": value,
            "target": ["production", "preview"],
        }
        for key, value in env_vars.items()
    ]


def merge_branding_configs(
    base: BrandingConfig,
    override: BrandingConfig,
) -> BrandingConfig:
    """Merge two branding configs, with override taking precedence.

    Args:
        base: Base branding configuration.
        override: Override configuration (non-None values take precedence).

    Returns:
        Merged BrandingConfig.
    """
    return BrandingConfig(
        business_name=override.business_name or base.business_name,
        primary_color=override.primary_color or base.primary_color,
        secondary_color=override.secondary_color or base.secondary_color,
        accent_color=override.accent_color or base.accent_color,
        logo_url=override.logo_url or base.logo_url,
        tagline=override.tagline or base.tagline,
        industry=override.industry or base.industry,
        phone=override.phone or base.phone,
        address=override.address or base.address,
        website=override.website or base.website,
        twilio_number=override.twilio_number or base.twilio_number,
        voice_websocket_url=override.voice_websocket_url or base.voice_websocket_url,
    )
