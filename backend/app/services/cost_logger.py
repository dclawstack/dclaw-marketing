"""Cost logging helper (Phase 11.4).

A single ``record_cost`` entry point that adapters / endpoints / workers
call after a billable external request. Writes a row into the
``CostLedger`` table so :mod:`app.api.v1.costs` aggregates real numbers
instead of returning zero.

Two flavours so we work in both async (FastAPI request path) and sync
(Celery worker path) contexts:

  • ``record_cost(session, ...)``       — async, takes ``AsyncSession``
  • ``record_cost_sync(session, ...)``  — sync, takes ``Session``

Both are no-ops when ``session`` is falsy — callers don't have to gate
on whether they have a DB handle.

Best-effort by design: a failure to log a cost row must not break the
underlying user request. All write paths catch + swallow.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.ops import CostLedger


# Rough provider price book — USD per unit. These are conservative
# defaults; the caller can override by passing ``amount_usd`` directly.
# Sourced from each provider's published pricing as of 2026-Q1.
PRICE_BOOK: dict[tuple[str, str], float] = {
    # (provider, units_kind) → USD per unit
    ("replicate", "image"): 0.0030,        # SDXL image, per generation
    ("replicate", "video_second"): 0.0500, # ~$3 per 60s video
    ("replicate", "music_second"): 0.0080, # MusicGen, per second
    ("elevenlabs", "char"): 0.00018,       # ~$0.18 per 1k chars, eleven_turbo
    ("anthropic", "input_token"): 0.000003,   # Sonnet 4.x input
    ("anthropic", "output_token"): 0.000015,  # Sonnet 4.x output
    ("resend", "email"): 0.0010,           # ~$1 per 1k emails
}


def _estimate(provider: str, units_kind: str | None, units: float | None) -> float:
    """Looks up ``PRICE_BOOK`` to estimate amount_usd when not provided."""
    if not units_kind or units is None:
        return 0.0
    price = PRICE_BOOK.get((provider, units_kind))
    if price is None:
        return 0.0
    return float(units) * price


def _build_row(
    *,
    organization_id: UUID,
    project_id: UUID | None,
    provider: str,
    kind: str,
    amount_usd: float | None,
    units: float | None,
    units_kind: str | None,
    provider_resource: str | None,
    job_id: UUID | None,
    agent_message_id: UUID | None,
    metadata: dict[str, Any] | None,
) -> CostLedger:
    if amount_usd is None:
        amount_usd = _estimate(provider, units_kind, units)
    return CostLedger(
        organization_id=organization_id,
        project_id=project_id,
        provider=provider,
        provider_resource=provider_resource,
        kind=kind,
        amount_usd=float(amount_usd),
        units=float(units) if units is not None else None,
        units_kind=units_kind,
        job_id=job_id,
        agent_message_id=agent_message_id,
        occurred_at=datetime.now(tz=timezone.utc),
        metadata_json=metadata,
    )


async def record_cost(
    session: AsyncSession | None,
    *,
    organization_id: UUID,
    provider: str,
    kind: str,
    project_id: UUID | None = None,
    amount_usd: float | None = None,
    units: float | None = None,
    units_kind: str | None = None,
    provider_resource: str | None = None,
    job_id: UUID | None = None,
    agent_message_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Async path. Adds a CostLedger row; caller is responsible for
    commit (we don't commit here so we don't interfere with the calling
    transaction).

    No-op if ``session`` is None / falsy. Best-effort — swallows
    exceptions so cost-logging failures never propagate.
    """
    if not session:
        return
    try:
        row = _build_row(
            organization_id=organization_id,
            project_id=project_id,
            provider=provider,
            kind=kind,
            amount_usd=amount_usd,
            units=units,
            units_kind=units_kind,
            provider_resource=provider_resource,
            job_id=job_id,
            agent_message_id=agent_message_id,
            metadata=metadata,
        )
        session.add(row)
        await session.flush()
    except Exception:
        pass


def record_cost_sync(
    session: Session | None,
    *,
    organization_id: UUID,
    provider: str,
    kind: str,
    project_id: UUID | None = None,
    amount_usd: float | None = None,
    units: float | None = None,
    units_kind: str | None = None,
    provider_resource: str | None = None,
    job_id: UUID | None = None,
    agent_message_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Sync path for Celery worker contexts. Same shape as :func:`record_cost`,
    but uses a sync :class:`sqlalchemy.orm.Session`. Best-effort.
    """
    if not session:
        return
    try:
        row = _build_row(
            organization_id=organization_id,
            project_id=project_id,
            provider=provider,
            kind=kind,
            amount_usd=amount_usd,
            units=units,
            units_kind=units_kind,
            provider_resource=provider_resource,
            job_id=job_id,
            agent_message_id=agent_message_id,
            metadata=metadata,
        )
        session.add(row)
        session.flush()
    except Exception:
        pass


__all__ = ["record_cost", "record_cost_sync", "PRICE_BOOK"]
