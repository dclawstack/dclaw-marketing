"""Q2 — ingestion_sources and document_chunks

Revision ID: 20260512_0007
Revises: 20260512_0006
Create Date: 2026-05-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260512_0007"
down_revision: Union[str, None] = "20260512_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    source_type = sa.Enum(
        "file", "url", "git", "zip", name="ingestionsourcetype"
    )
    source_type.create(op.get_bind(), checkfirst=False)
    ingest_status = sa.Enum(
        "queued", "fetching", "parsing", "chunking", "embedding", "ready", "failed",
        name="ingestionstatus",
    )
    ingest_status.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "ingestion_sources",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "initiated_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_type",
            sa.Enum(name="ingestionsourcetype", create_type=False),
            nullable=False,
        ),
        sa.Column("source_reference", sa.String(length=2048), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(name="ingestionstatus", create_type=False),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("document_chunks_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_ingestion_sources_organization_id", "ingestion_sources", ["organization_id"])
    op.create_index("ix_ingestion_sources_source_type", "ingestion_sources", ["source_type"])
    op.create_index("ix_ingestion_sources_status", "ingestion_sources", ["status"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.UUID(),
            sa.ForeignKey("ingestion_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("estimated_tokens", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_document_chunks_organization_id", "document_chunks", ["organization_id"])
    op.create_index("ix_document_chunks_source_id", "document_chunks", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_source_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_organization_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_ingestion_sources_status", table_name="ingestion_sources")
    op.drop_index("ix_ingestion_sources_source_type", table_name="ingestion_sources")
    op.drop_index("ix_ingestion_sources_organization_id", table_name="ingestion_sources")
    op.drop_table("ingestion_sources")
    sa.Enum(name="ingestionstatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="ingestionsourcetype").drop(op.get_bind(), checkfirst=False)
