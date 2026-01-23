"""Lead generation agents using OpenAI Agents SDK.

This module provides specialized agents for the lead generation pipeline:
- Scraper Agent: Scrapes businesses from Google Maps
- Research Agent: Deep research using Firecrawl and Apollo
- Voice Assembler Agent: Creates voice agents with Vector Stores
- Frontend Deployer Agent: Deploys demo sites to Vercel
- Sales Agent: Sends cold emails via SendGrid
"""

from typing import TYPE_CHECKING

# Lazy imports to avoid circular dependencies and improve startup time
if TYPE_CHECKING:
    from .scraper_agent import scraper_agent
    from .research_agent import research_agent
    from .voice_assembler_agent import voice_assembler_agent
    from .frontend_deployer_agent import frontend_deployer_agent

__all__ = [
    "scraper_agent",
    "research_agent",
    "voice_assembler_agent",
    "frontend_deployer_agent",
]


def __getattr__(name: str):
    """Lazy load agents on first access."""
    if name == "scraper_agent":
        from .scraper_agent import scraper_agent
        return scraper_agent
    if name == "research_agent":
        from .research_agent import research_agent
        return research_agent
    if name == "voice_assembler_agent":
        from .voice_assembler_agent import voice_assembler_agent
        return voice_assembler_agent
    if name == "frontend_deployer_agent":
        from .frontend_deployer_agent import frontend_deployer_agent
        return frontend_deployer_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
