"""Internal-linking suggester (Theme H).

Given a draft (markdown body or plain text), embed it and find the
top-K most semantically similar existing DocumentChunks in the Org's
knowledge graph. Surface each match as a candidate internal link the
author can wire into the draft.

The KG already has pgvector embeddings on every chunk, so this is
pure-DB work — no external call needed. The only cost is one embed
call for the draft itself, which falls back to the stub embedder when
no provider is configured.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion import DocumentChunk, IngestionSource, IngestionSourceType
from app.services.embeddings import embed_text


def _anchor_from_chunk(chunk: DocumentChunk) -> str:
    """Pull a short anchor candidate from a chunk's text. First non-empty
    sentence, truncated. Authors edit before insertion.
    """
    txt = (chunk.text or "").strip().split("\n", 1)[0]
    if not txt:
        return ""
    # First sentence, max 80 chars
    for sep in (". ", "? ", "! "):
        if sep in txt:
            txt = txt.split(sep, 1)[0] + sep.strip()
            break
    return txt[:80].strip()


async def suggest_internal_links(
    session: AsyncSession,
    *,
    organization_id: UUID,
    draft_text: str,
    top_k: int = 5,
    min_similarity: float = 0.0,
) -> list[dict[str, Any]]:
    """Return ``top_k`` suggested internal-link candidates for ``draft_text``.

    Each candidate is a dict with: ``chunk_id``, ``source_id``,
    ``source_reference`` (URL/Asset id depending on source type),
    ``source_type``, ``anchor`` (suggested anchor text), ``similarity``.
    """
    if not draft_text or not draft_text.strip():
        return []

    query_vec, _ = await embed_text(draft_text)
    distance = DocumentChunk.embedding.cosine_distance(query_vec)

    stmt = (
        select(DocumentChunk, IngestionSource, distance.label("distance"))
        .join(IngestionSource, IngestionSource.id == DocumentChunk.source_id)
        .where(
            DocumentChunk.organization_id == organization_id,
            DocumentChunk.embedding.is_not(None),
            # Only URL or git sources are sensible internal-link targets —
            # uploaded files don't have a public URL.
            IngestionSource.source_type.in_(
                (IngestionSourceType.url, IngestionSourceType.git)
            ),
        )
        .order_by(distance)
        .limit(int(top_k) * 3)  # over-fetch so we can dedupe by source
    )

    rows = (await session.execute(stmt)).all()

    seen_sources: set[UUID] = set()
    out: list[dict[str, Any]] = []
    for chunk, source, dist in rows:
        if source.id in seen_sources:
            continue
        similarity = 1.0 - float(dist)
        if similarity < min_similarity:
            continue
        seen_sources.add(source.id)
        out.append(
            {
                "chunk_id": str(chunk.id),
                "source_id": str(source.id),
                "source_type": source.source_type.value,
                "source_reference": source.source_reference,
                "anchor": _anchor_from_chunk(chunk) or source.name or source.source_reference[:80],
                "similarity": round(similarity, 4),
            }
        )
        if len(out) >= top_k:
            break

    return out


__all__ = ["suggest_internal_links"]
