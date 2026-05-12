"""Phase 2.x / Q4 — weekly freshness re-ingestion tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.ingestion import (
    IngestionSource,
    IngestionSourceType,
    IngestionStatus,
)
from app.models.organization import Organization


def _session():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    return sessionmaker(eng, expire_on_commit=False)()


def test_refresh_only_url_and_git_sources(monkeypatch):
    from app.worker.tasks import freshness as fresh_mod

    # Patch SyncSession to the in-memory engine session factory.
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    Session = sessionmaker(eng, expire_on_commit=False)

    # Patch the late import so it's a no-op.
    class _StubTask:
        def delay(self, *a, **kw):
            pass

    import app.worker.tasks.ingestion as ing_mod

    monkeypatch.setattr(
        ing_mod, "process_ingestion_source", _StubTask(), raising=False
    )
    monkeypatch.setattr(fresh_mod, "SyncSession", Session, raising=False)

    with Session() as s:
        org = Organization(slug="kg", name="KG")
        s.add(org)
        s.flush()
        now = datetime.now(tz=timezone.utc)
        old = now - timedelta(days=10)
        s.add_all(
            [
                IngestionSource(
                    organization_id=org.id,
                    source_type=IngestionSourceType.url,
                    source_reference="https://acme.co/about",
                    status=IngestionStatus.ready,
                    updated_at=old,
                ),
                IngestionSource(
                    organization_id=org.id,
                    source_type=IngestionSourceType.git,
                    source_reference="https://github.com/acme/repo",
                    status=IngestionStatus.ready,
                    updated_at=old,
                ),
                IngestionSource(
                    organization_id=org.id,
                    source_type=IngestionSourceType.file,
                    source_reference="asset-uuid",
                    status=IngestionStatus.ready,
                    updated_at=old,
                ),
                # Fresh URL — shouldn't be refreshed.
                IngestionSource(
                    organization_id=org.id,
                    source_type=IngestionSourceType.url,
                    source_reference="https://fresh.example",
                    status=IngestionStatus.ready,
                    updated_at=now,
                ),
            ]
        )
        s.commit()

    result = fresh_mod.refresh_stale_sources()
    assert result["refreshed"] == 2

    with Session() as s:
        queued_types = sorted(
            r.source_type.value
            for r in s.execute(
                select(IngestionSource).where(
                    IngestionSource.status == IngestionStatus.queued
                )
            )
            .scalars()
            .all()
        )
        assert queued_types == ["git", "url"]

        ready_types = sorted(
            r.source_type.value
            for r in s.execute(
                select(IngestionSource).where(
                    IngestionSource.status == IngestionStatus.ready
                )
            )
            .scalars()
            .all()
        )
        # The file row + the fresh URL stay ready.
        assert ready_types == ["file", "url"]


def test_refresh_skips_failed_sources(monkeypatch):
    from app.worker.tasks import freshness as fresh_mod

    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    Session = sessionmaker(eng, expire_on_commit=False)

    class _StubTask:
        def delay(self, *a, **kw):
            pass

    import app.worker.tasks.ingestion as ing_mod

    monkeypatch.setattr(
        ing_mod, "process_ingestion_source", _StubTask(), raising=False
    )
    monkeypatch.setattr(fresh_mod, "SyncSession", Session, raising=False)

    with Session() as s:
        org = Organization(slug="kg", name="KG")
        s.add(org)
        s.flush()
        s.add(
            IngestionSource(
                organization_id=org.id,
                source_type=IngestionSourceType.url,
                source_reference="https://x.co",
                status=IngestionStatus.failed,
                updated_at=datetime.now(tz=timezone.utc) - timedelta(days=10),
            )
        )
        s.commit()

    result = fresh_mod.refresh_stale_sources()
    assert result["refreshed"] == 0
