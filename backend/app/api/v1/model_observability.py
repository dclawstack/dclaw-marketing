"""Model Registry — feature-availability (M7) + SSE log stream (M8) + metrics (M9)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.model_call_log import ModelCallLog, ModelCallStatus
from app.models.model_registry import (
    Capability,
    HealthStatus,
    ModelEntry,
    ModelProvider,
)
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.services.model_call_logger import _redis_channel

log = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["model-registry"])


# ---------- M7: feature availability ---------------------------------------


# Component → required capabilities map (hardcoded per spec).
COMPONENT_REQUIRES: dict[str, list[str]] = {
    "conductor": [Capability.text.value, Capability.function_calling.value],
    "creatives_agent": [Capability.text.value, Capability.image_generation.value],
    "smm_agent": [Capability.text.value],
    "seo_agent": [Capability.text.value],
    "paid_media_agent": [Capability.text.value],
    "analyst_agent": [Capability.text.value],
    "knowledge_graph": [Capability.embedding.value],
    "image_generation": [Capability.image_generation.value],
    "voice_generation": [Capability.text_to_speech.value],
    "video_generation": [Capability.text_to_video.value],
    "music_generation": [Capability.text_to_music.value],
    "audio_transcription": [Capability.audio_transcription.value],
    "brand_kit_studio": [Capability.text.value],
    "aeo_scorer": [Capability.text.value],
}


async def _visible_entries(db: AsyncSession, user: User) -> list[ModelEntry]:
    stmt = select(ModelEntry).join(
        ModelProvider, ModelEntry.provider_id == ModelProvider.id
    ).where(
        ModelEntry.is_active.is_(True),
        ModelProvider.is_active.is_(True),
    )
    if not getattr(user, "is_superuser", False):
        member_orgs = (
            await db.execute(
                select(OrganizationMembership.organization_id).where(
                    OrganizationMembership.user_id == user.id,
                )
            )
        ).scalars().all()
        from sqlalchemy import or_
        stmt = stmt.where(
            or_(
                ModelProvider.organization_id.is_(None),
                ModelProvider.organization_id.in_(member_orgs) if member_orgs else False,
            )
        )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/feature-availability")
async def feature_availability(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Return component coverage + capability coverage for the caller's tenancy."""
    entries = await _visible_entries(db, user)

    # Capability index.
    cap_index: dict[str, dict[str, int]] = {}
    for c in Capability:
        cap_index[c.value] = {"model_count": 0, "healthy_count": 0}
    for e in entries:
        for cap in e.capabilities or []:
            slot = cap_index.setdefault(cap, {"model_count": 0, "healthy_count": 0})
            slot["model_count"] += 1
            if e.status == HealthStatus.healthy:
                slot["healthy_count"] += 1

    capability_coverage: dict[str, dict[str, Any]] = {
        cap: {
            "available": v["healthy_count"] > 0,
            "model_count": v["model_count"],
            "healthy_count": v["healthy_count"],
        }
        for cap, v in cap_index.items()
    }

    # Component coverage.
    available_caps = {
        cap for cap, v in capability_coverage.items() if v["available"]
    }
    component_coverage: dict[str, dict[str, Any]] = {}
    for comp, required in COMPONENT_REQUIRES.items():
        missing = [c for c in required if c not in available_caps]
        if not missing:
            stat = "full"
        elif len(missing) < len(required):
            stat = "partial"
        else:
            stat = "none"
        component_coverage[comp] = {
            "required": required,
            "covered": [c for c in required if c not in missing],
            "missing": missing,
            "status": stat,
        }

    return {
        "components": component_coverage,
        "capabilities": capability_coverage,
    }


# ---------- M8: live log SSE stream ----------------------------------------


async def _sse_event_stream(channel: str, request: Request):
    """Yield SSE-formatted lines from a Redis pub/sub channel."""
    pubsub = None
    r = None
    try:
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        yield ": connected\n\n"
        while True:
            if await request.is_disconnected():
                break
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=15.0
            )
            if msg is None:
                yield ": keep-alive\n\n"
                continue
            data = msg.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            yield f"data: {data}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception:  # noqa: BLE001
                pass
        if r is not None:
            try:
                await r.aclose()
            except Exception:  # noqa: BLE001
                pass


@router.get("/{model_id}/logs/stream")
async def stream_model_logs(
    model_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> StreamingResponse:
    """SSE stream of model invocation logs for a single model entry."""
    e = await db.get(ModelEntry, model_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Model entry not found.")
    p = await db.get(ModelProvider, e.provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Parent provider missing.")
    # Visibility check.
    if (
        p.organization_id is not None
        and not getattr(user, "is_superuser", False)
    ):
        member = (
            await db.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.user_id == user.id,
                    OrganizationMembership.organization_id == p.organization_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=403, detail="Forbidden.")

    return StreamingResponse(
        _sse_event_stream(_redis_channel(model_id), request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------- M9: metrics endpoint -------------------------------------------


@router.get("/{model_id}/metrics")
async def model_metrics(
    model_id: UUID,
    window: str = Query("7d", pattern=r"^\d+[dh]$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Aggregated metrics for a single model entry over the given window."""
    e = await db.get(ModelEntry, model_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Model entry not found.")
    p = await db.get(ModelProvider, e.provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Parent provider missing.")
    if (
        p.organization_id is not None
        and not getattr(user, "is_superuser", False)
    ):
        member = (
            await db.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.user_id == user.id,
                    OrganizationMembership.organization_id == p.organization_id,
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=403, detail="Forbidden.")

    # Parse window
    n = int(window[:-1])
    unit = window[-1]
    delta = timedelta(days=n) if unit == "d" else timedelta(hours=n)
    since = datetime.now(timezone.utc) - delta

    base = select(ModelCallLog).where(
        ModelCallLog.model_entry_id == model_id,
        ModelCallLog.started_at >= since,
    )
    rows = list((await db.execute(base)).scalars().all())
    total = len(rows)
    success = sum(1 for r in rows if r.status == ModelCallStatus.success)
    total_in = sum(r.input_tokens for r in rows)
    total_out = sum(r.output_tokens for r in rows)
    total_cost = sum(r.cost_usd for r in rows)

    # Latency percentiles
    lats = sorted(r.duration_ms for r in rows)

    def pct(p: float) -> int:
        if not lats:
            return 0
        idx = min(len(lats) - 1, int(round(p * (len(lats) - 1))))
        return lats[idx]

    avg = (sum(lats) // len(lats)) if lats else 0

    # By-component breakdown.
    by_component: dict[str, int] = {}
    for r in rows:
        by_component[r.caller_component] = by_component.get(r.caller_component, 0) + 1

    # Daily time series (UTC day buckets).
    daily: dict[str, dict[str, int]] = {}
    for r in rows:
        day = r.started_at.astimezone(timezone.utc).date().isoformat()
        d = daily.setdefault(day, {"success": 0, "error": 0})
        if r.status == ModelCallStatus.success:
            d["success"] += 1
        else:
            d["error"] += 1
    daily_series = sorted(
        ({"date": k, **v} for k, v in daily.items()), key=lambda x: x["date"]
    )

    return {
        "model_entry_id": str(model_id),
        "window": window,
        "summary": {
            "total_calls": total,
            "success_rate": (success / total) if total else 0.0,
            "avg_latency_ms": avg,
            "p50_latency_ms": pct(0.50),
            "p95_latency_ms": pct(0.95),
            "p99_latency_ms": pct(0.99),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_cost_usd": round(total_cost, 6),
        },
        "by_component": by_component,
        "daily": daily_series,
    }
