"""Asset model — every file in object storage gets one row here.

Generated content from agents (images, videos, audio, text drafts),
user-uploaded source files (PDFs, brand guidelines, transcripts, …),
exports — all live as Assets. The actual bytes are in S3/MinIO; this
row tracks metadata + provenance + access.
"""

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AssetKind(str, enum.Enum):
    """High-level category — drives renderers and validators."""
    image = "image"
    video = "video"
    audio = "audio"
    document = "document"  # PDF / DOCX / PPTX / Markdown / TXT
    data = "data"          # CSV / JSON / SVG (treated as data, not image)
    archive = "archive"    # ZIP / TAR
    other = "other"


class AssetStatus(str, enum.Enum):
    uploading = "uploading"   # presigned PUT issued; bytes not yet confirmed
    ready = "ready"            # bytes uploaded, sha256 computed, ready to serve
    failed = "failed"          # upload aborted or post-processing failed
    deleted = "deleted"        # soft-deleted; S3 object may still exist briefly


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    kind: Mapped[AssetKind] = mapped_column(SQLEnum(AssetKind), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Optional media-specific metadata, populated post-upload
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    status: Mapped[AssetStatus] = mapped_column(
        SQLEnum(AssetStatus), nullable=False, default=AssetStatus.uploading
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
