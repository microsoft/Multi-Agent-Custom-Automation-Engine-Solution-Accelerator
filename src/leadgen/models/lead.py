"""Lead SQLAlchemy model for storing scraped business information."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, Numeric, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class LeadStatus(str, Enum):
    """Status of a lead in the pipeline."""

    NEW = "new"
    RESEARCHING = "researching"
    RESEARCHED = "researched"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    EMAILED = "emailed"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    CONVERTED = "converted"
    DISQUALIFIED = "disqualified"
    FAILED = "failed"


class Lead(Base):
    """SQLAlchemy model representing a scraped business lead.

    Stores business information from Google Maps Places API along with
    enrichment data from research agents and pipeline status tracking.

    Attributes:
        id: Unique identifier for the lead (UUID).
        name: Business name.
        address: Full street address.
        phone: Primary phone number.
        website: Business website URL.
        industry: Business industry/category.
        rating: Google Maps star rating (0.0-5.0).
        review_count: Number of Google reviews.
        revenue: Estimated annual revenue in USD.
        status: Current pipeline status.
        google_place_id: Google Places API place_id for deduplication.
        email: Contact email (from enrichment).
        created_at: Timestamp when lead was created.
        updated_at: Timestamp when lead was last updated.
    """

    __tablename__ = "leads"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Core business information from Google Maps
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Rating and review data
    rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(2, 1),
        nullable=True,
        comment="Google Maps star rating (0.0-5.0)"
    )
    review_count: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        comment="Number of Google reviews"
    )

    # Revenue estimation
    revenue: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Estimated annual revenue in USD"
    )

    # Pipeline status
    status: Mapped[LeadStatus] = mapped_column(
        SQLEnum(LeadStatus, name="lead_status"),
        nullable=False,
        default=LeadStatus.NEW,
        index=True
    )

    # Google Places deduplication key
    google_place_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Google Places API place_id for deduplication"
    )

    # Enrichment data
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Contact email from enrichment"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        """Return string representation of the lead."""
        return f"<Lead(id={self.id!r}, name={self.name!r}, status={self.status.value!r})>"

    def to_dict(self) -> dict:
        """Convert lead to dictionary representation.

        Returns:
            Dictionary with all lead fields.
        """
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "industry": self.industry,
            "rating": float(self.rating) if self.rating else None,
            "review_count": self.review_count,
            "revenue": float(self.revenue) if self.revenue else None,
            "status": self.status.value,
            "google_place_id": self.google_place_id,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
