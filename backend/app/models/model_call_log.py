"""ModelCallLog (S4-M6) — every model invocation anywhere in the platform.

Row shape per spec:

    (model_entry_id, org_id, caller_component, started_at, duration_ms,
     input_tokens, output_tokens, cost_usd, status, error_message,
     request_id)

`caller_component` is a free-form string constant defined per call site
(`"conductor"`, `"creatives_agent"`, `"embeddings"`, `"image_gen"`, ...).
Use the constants in `app.services.model_call_logger` for consistency.

Writes are async / fire-and-forget so they never block the live request.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ModelCallStatus(str, enum.Enum):
    success = "success"
    error = "error"
    timeout = "timeout"


class ModelCallLog(Base):
    __tablename__ = "model_call_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    model_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    caller_component: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[ModelCallStatus] = mapped_column(
        SQLEnum(ModelCallStatus, name="model_call_status_enum"),
        nullable=False,
        default=ModelCallStatus.success,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
