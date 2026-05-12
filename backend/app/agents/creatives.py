"""Creatives Agent — the demo agent for v0.1.

Given a brief + Org context (active Brand Kit + Knowledge Graph
retrieval), generates N variants of social-post copy. Each variant
becomes a pending ApprovalRequest; reviewers act on them in the
Approval Inbox.

Per PLAN-v1.2 §v2.0 §4.2 + §5.2 — outbound posting is Hard-gated
by default, so the agent never publishes directly.
"""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.anthropic_client import complete
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.brand_kit import BrandKit
from app.models.ingestion import DocumentChunk
from app.services.embeddings import embed_text


# ---------- prompt building ---------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """You are the Creatives Agent for the brand defined below. \
Your job is to draft social-media post copy in the brand's voice, \
ready for a human reviewer to approve. You never publish — you \
prepare for review.

BRAND VOICE:
{voice}

DO SAY: {do_say}
DON'T SAY: {dont_say}

POSITIONING:
{positioning}

CONSTRAINTS:
- Each variant is a single complete post.
- Optimize for {channel} — short, punchy, scroll-stopping.
- No emojis unless the brand voice explicitly invites them.
- No hashtags unless the brief asks for them.
- Never invent product features or claims. Stick to what the
  retrieved context supports.
"""


_USER_PROMPT_TEMPLATE = """Brief from the user:
\"\"\"
{brief}
\"\"\"

Relevant context retrieved from our knowledge graph:
{context}

Generate exactly {n_variants} distinct variants of {channel} post copy. \
Format your output as:

VARIANT 1: <text>

VARIANT 2: <text>

VARIANT 3: <text>

Do not include any other commentary."""


def _format_voice(brand: BrandKit | None) -> str:
    if not brand or not brand.voice_json:
        return "(no brand voice configured — write in a clear, modern, professional tone)"
    sliders = brand.voice_json.get("sliders", {})
    if sliders:
        return ", ".join(f"{k}: {v}" for k, v in sliders.items())
    return str(brand.voice_json)


def _format_list_field(brand: BrandKit | None, field: str) -> str:
    if not brand or not brand.voice_json:
        return "(none)"
    val = brand.voice_json.get(field)
    if not val:
        return "(none)"
    if isinstance(val, list):
        return ", ".join(val)
    return str(val)


def _format_positioning(brand: BrandKit | None) -> str:
    if not brand or not brand.positioning_json:
        return "(no positioning configured)"
    return str(brand.positioning_json)


def _format_context(chunks: list[DocumentChunk]) -> str:
    if not chunks:
        return "(no retrieved context — proceed with the brief alone)"
    return "\n\n".join(f"[chunk {i+1}] {c.text}" for i, c in enumerate(chunks))


# ---------- output parsing ---------------------------------------------

_VARIANT_RE = re.compile(r"^VARIANT\s+\d+:\s*(.+?)(?=^VARIANT\s+\d+:|\Z)", re.DOTALL | re.MULTILINE)


def parse_variants(text: str, expected: int) -> list[str]:
    """Pulls 'VARIANT N: <text>' chunks out of the model's response.

    If parsing fails (model deviated from format), falls back to
    splitting on blank lines and returning the first `expected`
    non-empty pieces — always producing SOMETHING usable.
    """
    matches = _VARIANT_RE.findall(text)
    cleaned = [m.strip() for m in matches if m.strip()]
    if cleaned:
        return cleaned[:expected]

    # Fallback: blank-line split
    paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    return paras[:expected] if paras else [text.strip()]


# ---------- orchestration ----------------------------------------------

async def generate_social_posts(
    *,
    session: AsyncSession,
    organization_id: UUID,
    project_id: UUID | None,
    brief: str,
    n_variants: int = 3,
    channel: str = "linkedin",
    requesting_user_id: UUID | None = None,
    kg_top_k: int = 5,
) -> list[dict]:
    """Generates variants and creates pending ApprovalRequest rows.

    Returns: [{"variant": "...", "approval_request_id": "..."}, ...]
    """
    # 1. Look up active brand kit
    bk_q = await session.execute(
        select(BrandKit).where(
            BrandKit.organization_id == organization_id,
            BrandKit.is_active.is_(True),
        )
    )
    brand_kit = bk_q.scalar_one_or_none()

    # 2. KG retrieval — best-effort. Skip silently if it fails (e.g.,
    #    embedding provider hiccup in test env without OpenAI key).
    chunks: list[DocumentChunk] = []
    try:
        query_vec, _ = await embed_text(brief)
        distance = DocumentChunk.embedding.cosine_distance(query_vec)
        ch_q = await session.execute(
            select(DocumentChunk)
            .where(
                DocumentChunk.organization_id == organization_id,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(kg_top_k)
        )
        chunks = list(ch_q.scalars().all())
    except Exception:
        chunks = []

    # 3. Build prompts
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        voice=_format_voice(brand_kit),
        do_say=_format_list_field(brand_kit, "do_say"),
        dont_say=_format_list_field(brand_kit, "dont_say"),
        positioning=_format_positioning(brand_kit),
        channel=channel,
    )
    # §6.2 — append top brand-kit insights so the agent learns from
    # prior runs without a manual prompt edit.
    if brand_kit is not None:
        from app.agents.brand_style import (
            fetch_brand_insights,
            format_insights_block,
        )
        try:
            insights = await fetch_brand_insights(
                session, brand_kit_id=brand_kit.id, top_k=5
            )
        except Exception:
            insights = []
        system_prompt = system_prompt + format_insights_block(insights)
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        brief=brief,
        context=_format_context(chunks),
        n_variants=n_variants,
        channel=channel,
    )

    # 4. Call the LLM (real or stub)
    raw = await complete(
        system=system_prompt,
        user=user_prompt,
        n_variants_hint=n_variants,
    )

    # 5. Parse N variants
    variants = parse_variants(raw, n_variants)

    # 6. Create one pending ApprovalRequest per variant
    results: list[dict] = []
    for variant in variants:
        ar = ApprovalRequest(
            organization_id=organization_id,
            project_id=project_id,
            requested_by_user_id=requesting_user_id,
            requested_by_agent="creatives_agent_v1",
            action_type="publish_social_post",
            target_type="social_post_draft",
            payload_json={
                "channel": channel,
                "text": variant,
                "brief": brief,
                "brand_kit_id": str(brand_kit.id) if brand_kit else None,
                "kg_chunks_used": [str(c.id) for c in chunks],
            },
            summary=f"Publish to {channel}: {variant[:80]}{'…' if len(variant) > 80 else ''}",
            status=ApprovalStatus.pending,
        )
        session.add(ar)
        await session.flush()
        results.append({"variant": variant, "approval_request_id": str(ar.id)})

    await session.commit()
    return results


__all__ = ["generate_social_posts", "parse_variants"]
