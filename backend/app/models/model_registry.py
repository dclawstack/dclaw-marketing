"""Model Registry — per-org & global multi-provider AI model management.

Sprint 4 S4-M ships a pair of tables:

* `ModelProvider` — one row per configured provider account. Holds the
  encrypted API key + base URL + provider type. `org_id` is nullable;
  NULL means "superadmin / global", available to every org. An org
  may have multiple providers of the same type (dev / staging / prod
  Anthropic keys, etc.) — uniqueness is on (org_id, provider_type, name).

* `ModelEntry` — one row per concrete model exposed by a provider
  (Claude Opus 4.7, gpt-4o, claude-3-7-sonnet, etc.). Capabilities are
  free-form text tags from `Capability` (kept as a JSON list rather
  than a join table so the discovery worker can write them in one
  transaction and the resolver can read them without a join).

Sibling table `ModelCallLog` (M6) lives in `model_call_log.py` so this
file stays focused on the provider/model catalog surface.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProviderType(str, enum.Enum):
    """All 25 supported provider types per PLAN-v1.2 Sprint 4 §S4-M.

    Tier 1 — Native APIs.
    """

    anthropic = "anthropic"
    openai = "openai"
    google_gemini = "google_gemini"
    google_vertex_ai = "google_vertex_ai"
    azure_openai = "azure_openai"
    aws_bedrock = "aws_bedrock"
    mistral = "mistral"
    cohere = "cohere"
    voyage_ai = "voyage_ai"
    huggingface = "huggingface"

    # Tier 2 — Named OpenAI-compatible aggregators.
    openrouter = "openrouter"
    groq = "groq"
    together_ai = "together_ai"
    fireworks_ai = "fireworks_ai"
    deepseek = "deepseek"
    perplexity = "perplexity"
    sambanova = "sambanova"

    # Tier 3 — Multimedia specialists.
    replicate = "replicate"
    elevenlabs = "elevenlabs"
    runway = "runway"
    suno = "suno"
    deepgram = "deepgram"
    cartesia = "cartesia"
    fal_ai = "fal_ai"

    # Tier 4 — Self-hosted / generic.
    ollama = "ollama"
    openai_compatible = "openai_compatible"


class Capability(str, enum.Enum):
    """What a model can do — drives feature-availability matrix and
    assignment dropdowns. Stored as a list of strings on `ModelEntry`."""

    text = "text"
    embedding = "embedding"
    multimodal_embedding = "multimodal_embedding"
    image_generation = "image_generation"
    image_understanding = "image_understanding"
    audio_transcription = "audio_transcription"
    text_to_speech = "text_to_speech"
    text_to_video = "text_to_video"
    text_to_music = "text_to_music"
    function_calling = "function_calling"
    reasoning = "reasoning"
    reranking = "reranking"
    web_search = "web_search"


class HealthStatus(str, enum.Enum):
    unknown = "unknown"
    healthy = "healthy"
    unhealthy = "unhealthy"
    disabled = "disabled"


class ModelProvider(Base):
    """One provider account (key + base URL) — global or org-scoped."""

    __tablename__ = "model_providers"
    __table_args__ = (
        # Multiple providers of the same type per org are allowed
        # (dev / staging / prod). Uniqueness on the human label.
        UniqueConstraint(
            "organization_id",
            "provider_type",
            "name",
            name="uq_model_provider_org_type_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # NULL = global (superadmin), populated = org-scoped.
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    provider_type: Mapped[ProviderType] = mapped_column(
        SQLEnum(ProviderType, name="provider_type_enum"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Provider endpoint; default per-type lives in the service layer.
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Fernet-encrypted API key. None for Ollama / Vertex (service-acct lives
    # in extra_config_json).
    encrypted_api_key: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )

    # Provider-specific config (gcp_project, region, deployment, headers, etc.)
    extra_config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Last result of the health-check beat (M5).
    health_status: Mapped[HealthStatus] = mapped_column(
        SQLEnum(HealthStatus, name="health_status_enum"),
        nullable=False,
        default=HealthStatus.unknown,
    )
    health_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ModelEntry(Base):
    """One concrete model exposed by a provider."""

    __tablename__ = "model_entries"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "model_id",
            name="uq_model_entry_provider_model",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # List of `Capability.value` strings.
    capabilities: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[HealthStatus] = mapped_column(
        SQLEnum(HealthStatus, name="health_status_enum"),
        nullable=False,
        default=HealthStatus.unknown,
    )
    health_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # When True, operator-edited capability list — auto-discovery should
    # not overwrite on re-sync.
    capabilities_locked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
