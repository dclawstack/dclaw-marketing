"""Knowledge Graph search API (Theme Q3).

Semantic search across an Organization's ingested DocumentChunks via
the pgvector cosine-similarity index. Agents call this to retrieve
context when generating content.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ingestion import DocumentChunk
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.services.embeddings import embed_text


router = APIRouter(prefix="/kg", tags=["knowledge-graph"])


class KGSearchRequest(BaseModel):
    organization_id: UUID
    query: str = Field(min_length=1, max_length=4096)
    top_k: int = Field(default=10, ge=1, le=50)


class KGSearchResultChunk(BaseModel):
    chunk_id: UUID
    source_id: UUID
    text: str
    position: int
    similarity: float
    metadata_json: dict | None
    embedding_model: str | None

    class Config:
        from_attributes = True


class KGSearchResponse(BaseModel):
    query: str
    top_k: int
    organization_id: UUID
    results: list[KGSearchResultChunk]


async def _require_member(
    session: AsyncSession, user: User, organization_id: UUID
) -> None:
    if user.is_superuser:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )


@router.post("/search", response_model=KGSearchResponse)
async def search(
    body: KGSearchRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> KGSearchResponse:
    """Semantic search. Embeds the query, finds the top-k most similar
    DocumentChunks in the Organization via pgvector cosine distance.
    """
    await _require_member(session, user, body.organization_id)

    query_vector, _ = await embed_text(body.query)

    # pgvector cosine distance: lower = more similar. similarity = 1 - distance.
    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(
            DocumentChunk,
            distance.label("distance"),
        )
        .where(
            DocumentChunk.organization_id == body.organization_id,
            DocumentChunk.embedding.is_not(None),
        )
        .order_by(distance)
        .limit(body.top_k)
    )
    rows = await session.execute(stmt)
    results = []
    for chunk, dist in rows.all():
        results.append(
            KGSearchResultChunk(
                chunk_id=chunk.id,
                source_id=chunk.source_id,
                text=chunk.text,
                position=chunk.position,
                similarity=1.0 - float(dist),
                metadata_json=chunk.metadata_json,
                embedding_model=chunk.embedding_model,
            )
        )

    return KGSearchResponse(
        query=body.query,
        top_k=body.top_k,
        organization_id=body.organization_id,
        results=results,
    )


class KGStatsResponse(BaseModel):
    organization_id: UUID
    chunk_count: int
    embedded_count: int
    source_count: int


@router.get("/stats", response_model=KGStatsResponse)
async def stats(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> KGStatsResponse:
    """Quick health metrics for an Org's knowledge graph."""
    await _require_member(session, user, organization_id)

    total_q = await session.execute(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.organization_id == organization_id)
    )
    embedded_q = await session.execute(
        select(func.count())
        .select_from(DocumentChunk)
        .where(
            DocumentChunk.organization_id == organization_id,
            DocumentChunk.embedding.is_not(None),
        )
    )
    sources_q = await session.execute(
        select(func.count(func.distinct(DocumentChunk.source_id)))
        .where(DocumentChunk.organization_id == organization_id)
    )

    return KGStatsResponse(
        organization_id=organization_id,
        chunk_count=total_q.scalar() or 0,
        embedded_count=embedded_q.scalar() or 0,
        source_count=sources_q.scalar() or 0,
    )
