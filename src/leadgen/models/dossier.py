"""Dossier SQLAlchemy model for storing research data about leads."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class Dossier(Base):
    """SQLAlchemy model representing a research dossier for a lead.

    Stores the compiled research data including website scrapes, social profiles,
    review analysis, and enrichment data. Also tracks the associated OpenAI
    Vector Store and Assistant for voice agent functionality.

    Attributes:
        id: Unique identifier for the dossier (UUID).
        lead_id: Foreign key reference to the associated lead.
        content: Markdown-formatted research dossier content.
        vector_store_id: OpenAI Vector Store ID for RAG functionality.
        assistant_id: OpenAI Assistant ID for voice agent.
        created_at: Timestamp when dossier was created.
        updated_at: Timestamp when dossier was last updated.
    """

    __tablename__ = "dossiers"

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

    # Research content (markdown format)
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Markdown-formatted research dossier content"
    )

    # OpenAI Vector Store ID for RAG functionality
    vector_store_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="OpenAI Vector Store ID for file_search RAG"
    )

    # OpenAI Assistant ID for voice agent
    assistant_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="OpenAI Assistant ID for voice agent"
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

    # Relationship to Lead model (optional, for ORM convenience)
    lead: Mapped["Lead"] = relationship(
        "Lead",
        back_populates="dossier",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        """Return string representation of the dossier."""
        return (
            f"<Dossier(id={self.id!r}, lead_id={self.lead_id!r}, "
            f"has_content={self.content is not None})>"
        )

    def to_dict(self) -> dict:
        """Convert dossier to dictionary representation.

        Returns:
            Dictionary with all dossier fields.
        """
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "content": self.content,
            "vector_store_id": self.vector_store_id,
            "assistant_id": self.assistant_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def has_vector_store(self) -> bool:
        """Check if dossier has an associated Vector Store.

        Returns:
            True if vector_store_id is set.
        """
        return self.vector_store_id is not None

    @property
    def has_assistant(self) -> bool:
        """Check if dossier has an associated Assistant.

        Returns:
            True if assistant_id is set.
        """
        return self.assistant_id is not None

    @property
    def is_ready_for_voice(self) -> bool:
        """Check if dossier is ready for voice agent deployment.

        Returns:
            True if both content and assistant_id are set.
        """
        return self.content is not None and self.assistant_id is not None
