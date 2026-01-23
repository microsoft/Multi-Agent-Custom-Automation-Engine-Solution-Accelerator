"""Campaign SQLAlchemy model for tracking batch lead generation operations."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class CampaignStatus(str, Enum):
    """Status of a lead generation campaign."""

    PENDING = "pending"
    SCRAPING = "scraping"
    RESEARCHING = "researching"
    DEPLOYING = "deploying"
    EMAILING = "emailing"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Campaign(Base):
    """SQLAlchemy model representing a lead generation campaign batch.

    A campaign represents a single batch operation that scrapes leads from
    a specific zip code and set of industries. It tracks the overall progress
    and status of the batch through the pipeline stages.

    Attributes:
        id: Unique identifier for the campaign (UUID).
        zip_code: Target zip code for geographic filtering.
        industries: List of target industries (stored as JSON array).
        radius_miles: Search radius in miles from zip code center.
        status: Current campaign status.
        total_leads: Total number of leads found.
        processed_leads: Number of leads processed through pipeline.
        failed_leads: Number of leads that failed processing.
        started_at: Timestamp when campaign processing started.
        completed_at: Timestamp when campaign completed.
        created_at: Timestamp when campaign was created.
        updated_at: Timestamp when campaign was last updated.
        error_message: Error details if campaign failed.
    """

    __tablename__ = "campaigns"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Target parameters
    zip_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Target zip code for lead scraping"
    )

    industries: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        comment="List of target industries (e.g., ['dentist', 'hvac', 'salon'])"
    )

    radius_miles: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=20,
        comment="Search radius in miles from zip code center"
    )

    # Pipeline status
    status: Mapped[CampaignStatus] = mapped_column(
        SQLEnum(CampaignStatus, name="campaign_status"),
        nullable=False,
        default=CampaignStatus.PENDING,
        index=True
    )

    # Progress tracking
    total_leads: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total number of leads found during scraping"
    )

    processed_leads: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of leads successfully processed through pipeline"
    )

    failed_leads: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of leads that failed processing"
    )

    # Execution timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when campaign processing started"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when campaign completed"
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if campaign failed"
    )

    # Standard timestamps
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
        """Return string representation of the campaign."""
        return (
            f"<Campaign(id={self.id!r}, zip_code={self.zip_code!r}, "
            f"status={self.status.value!r})>"
        )

    def to_dict(self) -> dict:
        """Convert campaign to dictionary representation.

        Returns:
            Dictionary with all campaign fields.
        """
        return {
            "id": self.id,
            "zip_code": self.zip_code,
            "industries": self.industries,
            "radius_miles": self.radius_miles,
            "status": self.status.value,
            "total_leads": self.total_leads,
            "processed_leads": self.processed_leads,
            "failed_leads": self.failed_leads,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def progress_percent(self) -> float:
        """Calculate the progress percentage of the campaign.

        Returns:
            Percentage of leads processed (0-100).
        """
        if self.total_leads == 0:
            return 0.0
        return (self.processed_leads / self.total_leads) * 100

    @property
    def is_active(self) -> bool:
        """Check if campaign is currently active.

        Returns:
            True if campaign is in an active processing state.
        """
        return self.status in (
            CampaignStatus.SCRAPING,
            CampaignStatus.RESEARCHING,
            CampaignStatus.DEPLOYING,
            CampaignStatus.EMAILING,
        )

    @property
    def is_complete(self) -> bool:
        """Check if campaign has finished (successfully or not).

        Returns:
            True if campaign is in a terminal state.
        """
        return self.status in (
            CampaignStatus.COMPLETED,
            CampaignStatus.FAILED,
            CampaignStatus.CANCELLED,
        )
