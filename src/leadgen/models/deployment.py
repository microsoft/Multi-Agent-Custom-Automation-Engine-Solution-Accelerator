"""Deployment SQLAlchemy model for tracking demo site deployments to Vercel."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base

if TYPE_CHECKING:
    from .lead import Lead


class DeploymentStatus(str, Enum):
    """Status of a demo site deployment."""

    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class Deployment(Base):
    """SQLAlchemy model representing a demo site deployment to Vercel.

    Tracks the deployment of personalized Next.js demo sites for each lead.
    Each deployment is associated with a specific lead and contains the
    Vercel deployment URL and project identifiers for management.

    Attributes:
        id: Unique identifier for the deployment (UUID).
        lead_id: Foreign key reference to the associated lead.
        url: Public URL of the deployed demo site.
        vercel_id: Vercel deployment/project ID for management.
        status: Current deployment status.
        error_message: Error details if deployment failed.
        created_at: Timestamp when deployment was created.
        updated_at: Timestamp when deployment was last updated.
    """

    __tablename__ = "deployments"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Foreign key to leads table
    lead_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Foreign key reference to the associated lead"
    )

    # Deployment URL (e.g., https://acme-dental.leadgen.app)
    url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Public URL of the deployed demo site"
    )

    # Vercel deployment/project identifier
    vercel_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Vercel deployment/project ID for management"
    )

    # Deployment status
    status: Mapped[DeploymentStatus] = mapped_column(
        SQLEnum(DeploymentStatus, name="deployment_status"),
        nullable=False,
        default=DeploymentStatus.PENDING,
        index=True
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if deployment failed"
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

    # Relationship to Lead model
    lead: Mapped["Lead"] = relationship(
        "Lead",
        back_populates="deployment",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        """Return string representation of the deployment."""
        return (
            f"<Deployment(id={self.id!r}, lead_id={self.lead_id!r}, "
            f"status={self.status.value!r})>"
        )

    def to_dict(self) -> dict:
        """Convert deployment to dictionary representation.

        Returns:
            Dictionary with all deployment fields.
        """
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "url": self.url,
            "vercel_id": self.vercel_id,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def is_live(self) -> bool:
        """Check if deployment is live and accessible.

        Returns:
            True if deployment status is READY.
        """
        return self.status == DeploymentStatus.READY

    @property
    def is_pending(self) -> bool:
        """Check if deployment is still in progress.

        Returns:
            True if deployment is in PENDING, BUILDING, or DEPLOYING state.
        """
        return self.status in (
            DeploymentStatus.PENDING,
            DeploymentStatus.BUILDING,
            DeploymentStatus.DEPLOYING,
        )

    @property
    def has_failed(self) -> bool:
        """Check if deployment has failed.

        Returns:
            True if deployment status is FAILED.
        """
        return self.status == DeploymentStatus.FAILED
