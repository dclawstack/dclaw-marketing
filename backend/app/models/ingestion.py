"""Ingestion models — Theme Q2 (Input Channel Hub).

Records every ingestion job (uploaded file, URL, git repo, zip archive)
and the text chunks it produced. Q3 (Knowledge Graph) adds embeddings
on top of these chunks.

For v0.1 we support uploaded files only (text/markdown/csv/json/pdf).
URL / git / zip ingest comes in follow-up PRs.
"""

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


# Embedding dimensionality. text-embedding-3-small is 1536-dim;
# text-embedding-3-large is 3072 — we pick small for cost + latency
# and configurable later via a feature flag.
EMBEDDING_DIM = 1536


class IngestionSourceType(str, enum.Enum):
    file = "file"
    url = "url"
    git = "git"
    zip = "zip"


class IngestionStatus(str, enum.Enum):
    queued = "queued"
    fetching = "fetching"
    parsing = "parsing"
    chunking = "chunking"
    embedding = "embedding"       # set during Q3 work; v0.1 jumps to ready
    ready = "ready"
    failed = "failed"


class IngestionSource(Base):
    """One ingestion attempt — bundles a source pointer + status."""
    __tablename__ = "ingestion_sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    initiated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    source_type: Mapped[IngestionSourceType] = mapped_column(
        SQLEnum(IngestionSourceType), nullable=False, index=True
    )

    # For source_type=file: this is the Asset.id. For url: the URL.
    # For git: the repo URL. For zip: the Asset.id of the zip.
    source_reference: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Optional human-readable label (e.g., "Q2 product brief").
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[IngestionStatus] = mapped_column(
        SQLEnum(IngestionStatus), nullable=False, default=IngestionStatus.queued, index=True
    )

    # Set by the worker as it progresses
    document_chunks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free-form structured data: file content-type, total bytes, page count, etc.
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Foreign key to the Job row tracking the Celery task
    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="source",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    """A piece of extracted text. Q3 adds a pgvector embedding column.

    For v0.1 the chunker is naive (split on paragraph then size-cap).
    Later: semantic chunking + overlap.
    """
    __tablename__ = "document_chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("ingestion_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Order within the source — pages or paragraph index.
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Tokens (rough character / 4 estimate; will use tiktoken later).
    estimated_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Free-form structured: {"page": 3, "section": "Introduction", ...}
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Q3: pgvector embedding. NULL until the embedder has run.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )
    # Identifier of the embedding model used (e.g.,
    # "openai/text-embedding-3-small"). NULL while embedding is NULL.
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    source: Mapped["IngestionSource"] = relationship(
        "IngestionSource", back_populates="chunks", lazy="selectin"
    )
