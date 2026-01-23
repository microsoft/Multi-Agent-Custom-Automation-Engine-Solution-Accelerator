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


# For type checking, use actual imports
if TYPE_CHECKING:
    from .apollo import ApolloClient
    from .firecrawl import FirecrawlClient
    from .google_maps import GoogleMapsClient


def __getattr__(name: str):
    """Module-level __getattr__ for lazy imports."""
    if name == "ApolloClient":
        return _get_apollo_client()
    elif name == "FirecrawlClient":
        return _get_firecrawl_client()
    elif name == "GoogleMapsClient":
        return _get_googlemaps_client()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ApolloClient",
    "FirecrawlClient",
    "GoogleMapsClient",
]
