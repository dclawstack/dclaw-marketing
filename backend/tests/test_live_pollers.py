"""Phase 2.x / Q2 — live input poller tests."""

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
from app.worker.tasks import live_pollers as lp_mod


def _sync_session_factory():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    return sessionmaker(eng, expire_on_commit=False)


def test_poll_git_repos_requeues_stale_only(monkeypatch):
    Session = _sync_session_factory()

    class _StubTask:
        def delay(self, *a, **kw):
            pass

    import app.worker.tasks.ingestion as ing_mod

    monkeypatch.setattr(
        ing_mod, "process_ingestion_source", _StubTask(), raising=False
    )
    monkeypatch.setattr(lp_mod, "SyncSession", Session, raising=False)

    with Session() as s:
        org = Organization(slug="q2g", name="Q2G")
        s.add(org)
        s.flush()
        now = datetime.now(tz=timezone.utc)
        stale = now - timedelta(hours=6)
        fresh = now - timedelta(hours=1)
        s.add_all(
            [
                IngestionSource(
                    organization_id=org.id,
                    source_type=IngestionSourceType.git,
                    source_reference="https://github.com/acme/repo",
                    status=IngestionStatus.ready,
                    updated_at=stale,
                ),
                IngestionSource(
                    organization_id=org.id,
                    source_type=IngestionSourceType.git,
                    source_reference="https://github.com/acme/recent",
                    status=IngestionStatus.ready,
                    updated_at=fresh,
                ),
                # Different type — never touched by poll_git_repos.
                IngestionSource(
                    organization_id=org.id,
                    source_type=IngestionSourceType.url,
                    source_reference="https://acme.co/about",
                    status=IngestionStatus.ready,
                    updated_at=stale,
                ),
            ]
        )
        s.commit()

    result = lp_mod.poll_git_repos()
    assert result["refreshed"] == 1

    with Session() as s:
        queued = (
            s.execute(
                select(IngestionSource).where(
                    IngestionSource.status == IngestionStatus.queued
                )
            )
        ).scalars().all()
        # Only the stale git source got re-queued; the fresh git +
        # the url stayed at ready.
        assert len(queued) == 1
        assert queued[0].source_type == IngestionSourceType.git
        assert queued[0].source_reference == "https://github.com/acme/repo"


def test_poll_website_crawls_uses_24h_threshold(monkeypatch):
    Session = _sync_session_factory()

    class _StubTask:
        def delay(self, *a, **kw):
            pass

    import app.worker.tasks.ingestion as ing_mod

    monkeypatch.setattr(
        ing_mod, "process_ingestion_source", _StubTask(), raising=False
    )
    monkeypatch.setattr(lp_mod, "SyncSession", Session, raising=False)

    with Session() as s:
        org = Organization(slug="q2u", name="Q2U")
        s.add(org)
        s.flush()
        now = datetime.now(tz=timezone.utc)
        s.add_all(
            [
                IngestionSource(
                    organization_id=org.id,
                    source_type=IngestionSourceType.url,
                    source_reference="https://acme.co/landing",
                    status=IngestionStatus.ready,
                    updated_at=now - timedelta(hours=36),  # > 24h → stale
                ),
                IngestionSource(
                    organization_id=org.id,
                    source_type=IngestionSourceType.url,
                    source_reference="https://acme.co/pricing",
                    status=IngestionStatus.ready,
                    updated_at=now - timedelta(hours=12),  # < 24h → fresh
                ),
            ]
        )
        s.commit()

    result = lp_mod.poll_website_crawls()
    assert result["refreshed"] == 1
