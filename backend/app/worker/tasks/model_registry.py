"""Celery tasks for the Model Registry — S4-M3 (discovery) + S4-M5 (health).

Two flows:

* `discover_provider_models(provider_id)` — runs once after a provider
  is created, also triggered manually via the "Sync" button on the
  /admin/models page. Replaces / merges entries in `model_entries`,
  preserving operator capability overrides (capabilities_locked).

* `health_check_all_providers()` — Celery beat every 5 minutes. Probes
  each active provider, updates `health_status` / `health_error`, emits
  an `AuditEvent` on state transitions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.model_registry import (
    HealthStatus,
    ModelEntry,
    ModelProvider,
)
from app.services.model_discovery import (
    DiscoveredModel,
    discover_models_for_provider,
    probe_provider_health,
)
from app.worker.celery_app import celery_app

log = logging.getLogger(__name__)


def _sync_url() -> str:
    """Synchronous postgres URL (psycopg) for the worker.

    The app uses an async URL; tasks need a sync engine for the typical
    "open session, do work, commit" pattern inside Celery.
    """
    return settings.database_url.replace("+asyncpg", "")


def _session() -> Session:
    engine = create_engine(_sync_url(), pool_pre_ping=True, future=True)
    return Session(engine, future=True)


def _upsert_entry(db: Session, p: ModelProvider, m: DiscoveredModel) -> None:
    existing = db.execute(
        select(ModelEntry).where(
            ModelEntry.provider_id == p.id,
            ModelEntry.model_id == m.model_id,
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            ModelEntry(
                provider_id=p.id,
                model_id=m.model_id,
                display_name=m.display_name,
                capabilities=m.capabilities,
                context_window=m.context_window,
                max_output_tokens=m.max_output_tokens,
                status=HealthStatus.unknown,
            )
        )
    else:
        # Preserve operator overrides.
        if not existing.capabilities_locked:
            existing.capabilities = m.capabilities
        existing.display_name = m.display_name
        if m.context_window:
            existing.context_window = m.context_window
        if m.max_output_tokens:
            existing.max_output_tokens = m.max_output_tokens


@celery_app.task(name="app.worker.tasks.model_registry.discover_provider_models")
def discover_provider_models(provider_id: str) -> dict:
    """Discover the models offered by one provider; write to model_entries."""
    db = _session()
    try:
        p = db.get(ModelProvider, UUID(provider_id))
        if p is None:
            return {"ok": False, "error": "provider not found"}
        try:
            models = discover_models_for_provider(p)
        except Exception as e:  # noqa: BLE001
            log.exception("discovery failed for %s", p.id)
            return {"ok": False, "error": str(e)}
        for m in models:
            _upsert_entry(db, p, m)
        db.commit()
        return {"ok": True, "count": len(models)}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.model_registry.health_check_all_providers")
def health_check_all_providers() -> dict:
    """Probe every active provider; update health columns; audit transitions."""
    db = _session()
    checked = 0
    try:
        rows = db.execute(
            select(ModelProvider).where(ModelProvider.is_active.is_(True))
        ).scalars().all()
        for p in rows:
            prev = p.health_status
            try:
                status_, err = probe_provider_health(p)
            except Exception as e:  # noqa: BLE001
                status_, err = HealthStatus.unhealthy, str(e)[:500]
            p.health_status = status_
            p.health_error = err
            p.last_health_check_at = datetime.now(timezone.utc)
            checked += 1
            if prev != status_ and status_ in (
                HealthStatus.healthy,
                HealthStatus.unhealthy,
            ):
                db.add(
                    AuditEvent(
                        actor_kind=AuditActorKind.system,
                        action_type=(
                            "model_provider.healthy"
                            if status_ == HealthStatus.healthy
                            else "model_provider.unhealthy"
                        ),
                        organization_id=p.organization_id,
                        target_type="model_provider",
                        target_id=str(p.id),
                        result=AuditResult.success,
                        payload_json={
                            "provider_type": p.provider_type.value,
                            "name": p.name,
                            "error": err,
                        },
                    )
                )
        db.commit()
        return {"ok": True, "checked": checked}
    finally:
        db.close()
