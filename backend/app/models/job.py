"""Job model — the durable record for a Celery background task.

Every long-running operation (ingestion, generation, repurposing,
analytics rollup, scheduled publish) is dispatched through Celery
and gets one row in this table tracking lifecycle + progress +
result.

The /api/v1/jobs/{id}/stream endpoint exposes a Server-Sent Events
feed of a Job's evolving state, used by the UI to show live progress
on agent runs.
"""

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


class Job(Base):
    """A unit of background work owned by an Org + initiating User."""
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Tenancy — both nullable for v0.1.0 because some jobs (system-level
    # health checks, bootstrap) won't have an Org context yet. Most
    # user-initiated work WILL have org_id set; routes enforce it.
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    initiated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Task identifier — matches the Celery task name registered in
    # app.worker.tasks (e.g., "app.worker.tasks.ingest_file").
    kind: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus), nullable=False, default=JobStatus.queued, index=True
    )

    # Progress 0.0..1.0. Workers update this periodically.
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Short human-readable label of what the worker is currently doing
    # ("parsing PDF", "embedding chunks 12/40", "publishing to LinkedIn").
    progress_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Free-form output. Different task kinds put different things here
    # (asset IDs, count of chunks ingested, generation IDs, ...).
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # When the result is a downloadable artifact (e.g., generated video,
    # exported PDF), this is the S3-presigned GET URL.
    result_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Celery's own task UUID — kept so we can call `revoke` to cancel.
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
