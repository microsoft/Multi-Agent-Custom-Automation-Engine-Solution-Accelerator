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
from .deployment import Deployment, DeploymentStatus

# Import database utilities
from .database import (
    DatabaseManager,
    get_db_session,
    get_db,
    init_database,
    close_database,
    create_test_engine,
)

__all__ = [
    # Base class
    "Base",
    # Models
    "Lead",
    "LeadStatus",
    "Campaign",
    "CampaignStatus",
    "Dossier",
    "Deployment",
    "DeploymentStatus",
    # Database utilities
    "DatabaseManager",
    "get_db_session",
    "get_db",
    "init_database",
    "close_database",
    "create_test_engine",
]
