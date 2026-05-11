"""Q3 — knowledge graph: enable pgvector + add embedding column

Revision ID: 20260512_0008
Revises: 20260512_0007
Create Date: 2026-05-12

Adds the semantic-search layer per PLAN-v1.2 §Theme Q3. Every
DocumentChunk gets an embedding column (vector(1536)) populated by
the ingestion task. A KG search endpoint computes cosine similarity
against this column.

Requires pgvector extension. The pgvector/pgvector:pg16 Docker image
(used by docker-compose + CI) has it preinstalled — we just need to
CREATE EXTENSION here.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260512_0008"
down_revision: Union[str, None] = "20260512_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension (idempotent — IF NOT EXISTS).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Add embedding column + provenance column to document_chunks.
    op.execute(
        "ALTER TABLE document_chunks "
        "ADD COLUMN IF NOT EXISTS embedding vector(1536)"
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
    )

    # 3. ANN index for similarity search. IVFFlat is the simplest;
    #    HNSW is faster + better recall but heavier to maintain.
    #    Starting with IVFFlat; can swap later via separate migration.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat "
        "ON document_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.drop_column("document_chunks", "embedding_model")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    # Leave the extension alone — other tables may rely on it.
