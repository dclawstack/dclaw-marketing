"""Phase 8.2 — identity resolution unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.attribution import Touchpoint
from app.models.base import Base
from app.models.lead import Lead, LeadStatus
from app.models.organization import Organization
from app.worker.tasks.identity import resolve_for_org


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _org(session: Session) -> Organization:
    o = Organization(
        slug=f"o-{uuid4().hex[:8]}", name="Test Org", is_external=False
    )
    session.add(o)
    session.commit()
    session.refresh(o)
    return o


def _lead(session: Session, org: Organization, email: str) -> Lead:
    l = Lead(
        organization_id=org.id,
        email=email,
        status=LeadStatus.new,
    )
    session.add(l)
    session.commit()
    session.refresh(l)
    return l


def _touch(
    session: Session,
    org: Organization,
    *,
    visitor_id: str | None,
    lead_id=None,
) -> Touchpoint:
    tp = Touchpoint(
        organization_id=org.id,
        source="pixel",
        channel="twitter",
        visitor_id=visitor_id,
        lead_id=lead_id,
        occurred_at=datetime.now(tz=timezone.utc),
    )
    session.add(tp)
    session.commit()
    session.refresh(tp)
    return tp


def test_stamps_anonymous_touchpoints_with_known_lead(session: Session):
    org = _org(session)
    lead = _lead(session, org, "alice@example.com")
    # Two anonymous touchpoints, then one identified — should propagate
    tp1 = _touch(session, org, visitor_id="v-alice")
    tp2 = _touch(session, org, visitor_id="v-alice")
    tp3 = _touch(session, org, visitor_id="v-alice", lead_id=lead.id)

    stamped = resolve_for_org(session, org.id)
    session.commit()

    assert stamped == 2
    session.expire_all()
    for tp_id in (tp1.id, tp2.id, tp3.id):
        loaded = session.get(Touchpoint, tp_id)
        assert loaded.lead_id == lead.id


def test_unidentified_visitor_left_alone(session: Session):
    org = _org(session)
    tp = _touch(session, org, visitor_id="v-anon")
    stamped = resolve_for_org(session, org.id)
    session.commit()
    assert stamped == 0
    session.expire_all()
    assert session.get(Touchpoint, tp.id).lead_id is None


def test_does_not_overwrite_existing_lead(session: Session):
    org = _org(session)
    lead_a = _lead(session, org, "a@x.io")
    lead_b = _lead(session, org, "b@x.io")
    # Two identified touchpoints, two different leads on same visitor_id
    tp_a = _touch(session, org, visitor_id="shared", lead_id=lead_a.id)
    tp_b = _touch(session, org, visitor_id="shared", lead_id=lead_b.id)
    # plus one anonymous
    tp_n = _touch(session, org, visitor_id="shared")

    stamped = resolve_for_org(session, org.id)
    session.commit()
    session.expire_all()

    # The anonymous one gets stamped (with whichever lead was seen first)
    assert stamped == 1
    assert session.get(Touchpoint, tp_a.id).lead_id == lead_a.id
    assert session.get(Touchpoint, tp_b.id).lead_id == lead_b.id
    # Anonymous picks up one of them
    n_lead = session.get(Touchpoint, tp_n.id).lead_id
    assert n_lead in {lead_a.id, lead_b.id}


def test_idempotent_second_run_is_noop(session: Session):
    org = _org(session)
    lead = _lead(session, org, "x@y.io")
    _touch(session, org, visitor_id="v1")
    _touch(session, org, visitor_id="v1", lead_id=lead.id)

    first = resolve_for_org(session, org.id)
    session.commit()
    second = resolve_for_org(session, org.id)
    session.commit()
    assert first == 1
    assert second == 0


def test_no_visitor_id_is_skipped(session: Session):
    org = _org(session)
    lead = _lead(session, org, "x@y.io")
    # Touchpoint with no visitor_id — should be ignored entirely
    tp = _touch(session, org, visitor_id=None)
    _touch(session, org, visitor_id="v", lead_id=lead.id)

    stamped = resolve_for_org(session, org.id)
    session.commit()
    session.expire_all()
    assert stamped == 0
    assert session.get(Touchpoint, tp.id).lead_id is None
