"""Lead Generation Database Models.

This module contains SQLAlchemy models for the lead generation system.
"""

from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Import models to register them with Base metadata
from .lead import Lead, LeadStatus
from .campaign import Campaign, CampaignStatus
from .dossier import Dossier

__all__ = [
    "Base",
    "Lead",
    "LeadStatus",
    "Campaign",
    "CampaignStatus",
    "Dossier",
]
