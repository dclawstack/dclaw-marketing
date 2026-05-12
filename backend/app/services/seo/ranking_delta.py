"""Ranking-delta tracker (Theme H).

Once per day we snapshot each tracked keyword's top-N SERP for an Org
via the Ahrefs MCP `serp_overview` tool. Snapshots are persisted as
AuditEvent rows so we don't need a new table; the delta computation is
a self-join against yesterday's snapshot.

Tracked keywords live on ``Organization.constraints_json["seo"]["tracked_keywords"]``
as a list of strings. Country defaults to "us" unless overridden via
``constraints_json["seo"]["country"]``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.services.mcp.ahrefs import serp_overview


ACTION_RANKING_SNAPSHOT = "seo.ranking_snapshot"


def _our_position(result: dict[str, Any], own_domain: str | None) -> int | None:
    """Pluck our own ranking position from a serp_overview result.

    Result shape (per stub + per Ahrefs docs): {"results": [{"position": 1, "url": "...", "domain": "..."}, ...]}.
    We match by domain when the Org has one configured; otherwise return None.
    """
    if not own_domain or not isinstance(result, dict):
        return None
    own = own_domain.lower().lstrip("www.").rstrip("/")
    for row in result.get("results") or []:
        if not isinstance(row, dict):
            continue
        dom = (row.get("domain") or row.get("url") or "").lower()
        if own and own in dom:
            try:
                return int(row.get("position"))
            except (TypeError, ValueError):
                return None
    return None


async def snapshot_keyword_positions(
    session: AsyncSession,
    *,
    organization_id: UUID,
    keywords: list[str],
    country: str = "us",
    own_domain: str | None = None,
) -> dict[str, Any]:
    """Snapshot the SERP for each keyword. Persists one AuditEvent per
    keyword. Returns a summary dict suitable for the worker log.
    """
    snapshots: list[dict[str, Any]] = []
    for kw in keywords:
        if not kw or not kw.strip():
            continue
        res = await serp_overview(
            session,
            organization_id=organization_id,
            keyword=kw,
            country=country,
            limit=20,
        )
        raw = res.result if isinstance(res.result, dict) else {}
        position = _our_position(raw, own_domain)
        payload = {
            "keyword": kw,
            "country": country,
            "own_domain": own_domain,
            "own_position": position,
            "top_results": raw.get("results", [])[:10],
            "stub": res.stub,
        }
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_kind=AuditActorKind.system,
                actor_agent="seo_agent",
                action_type=ACTION_RANKING_SNAPSHOT,
                target_type="keyword",
                target_id=kw[:64],
                payload_json=payload,
                result=AuditResult.success,
            )
        )
        snapshots.append(payload)

    await session.flush()
    return {"organization_id": str(organization_id), "snapshots": snapshots}


async def compute_ranking_delta(
    session: AsyncSession,
    *,
    organization_id: UUID,
    days: int = 7,
) -> list[dict[str, Any]]:
    """For each tracked keyword, compare the most recent snapshot against
    the one from ``days`` ago. Returns per-keyword deltas:

      [{"keyword": "...", "previous": 4, "current": 9, "delta": +5, "country": "us"}, ...]

    Positive delta means we moved *down* the SERP (worse); negative
    means we moved *up* (better). UI should color accordingly.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=days + 1)

    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.organization_id == organization_id,
            AuditEvent.action_type == ACTION_RANKING_SNAPSHOT,
            AuditEvent.created_at >= window_start,
        )
        .order_by(AuditEvent.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()

    # Group by keyword; first entry per keyword = current, find the
    # latest entry whose created_at is at least ``days`` old = previous.
    cutoff = now - timedelta(days=days)
    by_kw: dict[str, list[AuditEvent]] = {}
    for ev in rows:
        kw = (ev.payload_json or {}).get("keyword")
        if not kw:
            continue
        by_kw.setdefault(kw, []).append(ev)

    out: list[dict[str, Any]] = []
    for kw, events in by_kw.items():
        current = events[0]
        previous = next(
            (e for e in events[1:] if e.created_at <= cutoff),
            None,
        )
        cur_pos = (current.payload_json or {}).get("own_position")
        prev_pos = (previous.payload_json or {}).get("own_position") if previous else None
        if cur_pos is None and prev_pos is None:
            continue
        delta = None
        if isinstance(cur_pos, int) and isinstance(prev_pos, int):
            delta = cur_pos - prev_pos
        out.append(
            {
                "keyword": kw,
                "country": (current.payload_json or {}).get("country", "us"),
                "current": cur_pos,
                "previous": prev_pos,
                "delta": delta,
                "snapshot_at": current.created_at.isoformat(),
            }
        )

    # Worst regressions first (largest positive delta).
    out.sort(
        key=lambda r: (r["delta"] if isinstance(r["delta"], int) else -10_000),
        reverse=True,
    )
    return out


__all__ = [
    "ACTION_RANKING_SNAPSHOT",
    "snapshot_keyword_positions",
    "compute_ranking_delta",
]
