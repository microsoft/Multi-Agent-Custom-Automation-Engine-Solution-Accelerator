"""Lead Generation Integration Clients.

This module provides client wrappers for all external API integrations
used in the lead generation pipeline.

Imports are lazy to avoid failures when optional dependencies are not installed.
"""

from typing import TYPE_CHECKING

# Lazy imports to allow partial functionality when dependencies missing
_ApolloClient = None
_FirecrawlClient = None
_GoogleMapsClient = None
_VectorStoreManager = None
_TwilioVoiceClient = None
_SendGridClient = None
_VercelDeployer = None


def _get_apollo_client():
    """Lazy load ApolloClient."""
    global _ApolloClient
    if _ApolloClient is None:
        from .apollo import ApolloClient as _AC
        _ApolloClient = _AC
    return _ApolloClient


def _get_firecrawl_client():
    """Lazy load FirecrawlClient."""
    global _FirecrawlClient
    if _FirecrawlClient is None:
        from .firecrawl import FirecrawlClient as _FC
        _FirecrawlClient = _FC
    return _FirecrawlClient


def _get_googlemaps_client():
    """Lazy load GoogleMapsClient."""
    global _GoogleMapsClient
    if _GoogleMapsClient is None:
        from .google_maps import GoogleMapsClient as _GMC
        _GoogleMapsClient = _GMC
    return _GoogleMapsClient


def _get_vector_store_manager():
    """Lazy load VectorStoreManager."""
    global _VectorStoreManager
    if _VectorStoreManager is None:
        from .openai_vectors import VectorStoreManager as _VSM
        _VectorStoreManager = _VSM
    return _VectorStoreManager


def _get_twilio_voice_client():
    """Lazy load TwilioVoiceClient."""
    global _TwilioVoiceClient
    if _TwilioVoiceClient is None:
        from .twilio_voice import TwilioVoiceClient as _TVC
        _TwilioVoiceClient = _TVC
    return _TwilioVoiceClient


def _get_sendgrid_client():
    """Lazy load SendGridClient."""
    global _SendGridClient
    if _SendGridClient is None:
        from .sendgrid import SendGridClient as _SGC
        _SendGridClient = _SGC
    return _SendGridClient


def _get_vercel_deployer():
    """Lazy load VercelDeployer."""
    global _VercelDeployer
    if _VercelDeployer is None:
        from .vercel import VercelDeployer as _VD
        _VercelDeployer = _VD
    return _VercelDeployer


# For type checking, use actual imports
if TYPE_CHECKING:
    from .apollo import ApolloClient
    from .firecrawl import FirecrawlClient
    from .google_maps import GoogleMapsClient
    from .openai_vectors import VectorStoreManager
    from .twilio_voice import TwilioVoiceClient
    from .sendgrid import SendGridClient
    from .vercel import VercelDeployer


def __getattr__(name: str):
    """Module-level __getattr__ for lazy imports."""
    if name == "ApolloClient":
        return _get_apollo_client()
    elif name == "FirecrawlClient":
        return _get_firecrawl_client()
    elif name == "GoogleMapsClient":
        return _get_googlemaps_client()
    elif name == "VectorStoreManager":
        return _get_vector_store_manager()
    elif name == "TwilioVoiceClient":
        return _get_twilio_voice_client()
    elif name == "SendGridClient":
        return _get_sendgrid_client()
    elif name == "VercelDeployer":
        return _get_vercel_deployer()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ApolloClient",
    "FirecrawlClient",
    "GoogleMapsClient",
    "VectorStoreManager",
    "TwilioVoiceClient",
    "SendGridClient",
    "VercelDeployer",
]
