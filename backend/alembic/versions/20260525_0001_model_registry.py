"""Model Registry — model_providers + model_entries tables.

Sprint 4 S4-M1/M2. Adds the per-org & global provider catalog plus the
discovered models table. Both share the `provider_type_enum` /
`health_status_enum` Postgres enums.

Revision ID: 20260525_0001
Revises: 20260524_0004
Create Date: 2026-05-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260525_0001"
down_revision: Union[str, None] = "20260524_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PROVIDER_TYPES = (
    "anthropic", "openai", "google_gemini", "google_vertex_ai", "azure_openai",
    "aws_bedrock", "mistral", "cohere", "voyage_ai", "huggingface",
    "openrouter", "groq", "together_ai", "fireworks_ai", "deepseek",
    "perplexity", "sambanova",
    "replicate", "elevenlabs", "runway", "suno", "deepgram", "cartesia",
    "fal_ai",
    "ollama", "openai_compatible",
)

HEALTH_STATUSES = ("unknown", "healthy", "unhealthy", "disabled")


def upgrade() -> None:
    provider_type_enum = postgresql.ENUM(
        *PROVIDER_TYPES, name="provider_type_enum", create_type=False
    )
    health_status_enum = postgresql.ENUM(
        *HEALTH_STATUSES, name="health_status_enum", create_type=False
    )
    provider_type_enum.create(op.get_bind(), checkfirst=True)
    health_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "model_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("provider_type", provider_type_enum, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=True),
        sa.Column("encrypted_api_key", sa.LargeBinary, nullable=True),
        sa.Column("extra_config_json", postgresql.JSON, nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "health_status",
            health_status_enum,
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("health_error", sa.Text, nullable=True),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "provider_type", "name",
            name="uq_model_provider_org_type_name",
        ),
    )
    op.create_index(
        "ix_model_providers_organization_id", "model_providers", ["organization_id"]
    )
    op.create_index(
        "ix_model_providers_provider_type", "model_providers", ["provider_type"]
    )
    op.create_index(
        "ix_model_providers_created_by_user_id",
        "model_providers",
        ["created_by_user_id"],
    )

    op.create_table(
        "model_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_providers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column(
            "capabilities",
            postgresql.JSON,
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("context_window", sa.Integer, nullable=True),
        sa.Column("max_output_tokens", sa.Integer, nullable=True),
        sa.Column(
            "status",
            health_status_enum,
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("health_error", sa.Text, nullable=True),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "capabilities_locked",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "provider_id", "model_id", name="uq_model_entry_provider_model"
        ),
    )
    op.create_index(
        "ix_model_entries_provider_id", "model_entries", ["provider_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_model_entries_provider_id", table_name="model_entries")
    op.drop_table("model_entries")
    op.drop_index("ix_model_providers_created_by_user_id", table_name="model_providers")
    op.drop_index("ix_model_providers_provider_type", table_name="model_providers")
    op.drop_index("ix_model_providers_organization_id", table_name="model_providers")
    op.drop_table("model_providers")
    sa.Enum(name="health_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="provider_type_enum").drop(op.get_bind(), checkfirst=True)
