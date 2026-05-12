"""Phase 8.5 — Lead 2.0 model unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.lead import (
    Lead,
    LeadActivity,
    LeadActivityKind,
    LeadNote,
    LeadStage,
    LeadStatus,
)
from app.models.organization import Organization


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _org(s: Session) -> Organization:
    o = Organization(slug=f"o-{uuid4().hex[:8]}", name="T", is_external=False)
    s.add(o)
    s.commit()
    s.refresh(o)
    return o


def _lead(s: Session, org, *, email: str = "alice@example.com", **kw) -> Lead:
    lead = Lead(
        organization_id=org.id,
        email=email,
        status=LeadStatus.new,
        **kw,
    )
    s.add(lead)
    s.commit()
    s.refresh(lead)
    return lead


def test_lead_2_0_field_defaults(session: Session):
    org = _org(session)
    lead = _lead(session, org)
    assert lead.stage == LeadStage.new
    assert lead.score is None
    assert lead.enrichment_json is None
    assert lead.utm_source is None
    assert lead.last_activity_at is None
    assert lead.activities == []
    assert lead.notes == []


def test_lead_with_enrichment_and_utm(session: Session):
    org = _org(session)
    lead = _lead(
        session,
        org,
        domain="example.com",
        phone="+1-555-0100",
        linkedin_url="https://linkedin.com/in/alice",
        stage=LeadStage.mql,
        score=78.5,
        enrichment_json={"provider": "apollo", "title": "Head of Marketing"},
        utm_source="linkedin",
        utm_medium="cpc",
        utm_campaign="q2-launch",
    )
    assert lead.stage == LeadStage.mql
    assert lead.score == 78.5
    assert lead.enrichment_json["title"] == "Head of Marketing"
    assert lead.utm_campaign == "q2-launch"


def test_lead_activity_kinds_round_trip(session: Session):
    org = _org(session)
    lead = _lead(session, org)
    now = datetime.now(tz=timezone.utc)
    for kind in (
        LeadActivityKind.email_open,
        LeadActivityKind.page_view,
        LeadActivityKind.form_submit,
    ):
        session.add(
            LeadActivity(
                lead_id=lead.id,
                organization_id=org.id,
                kind=kind,
                occurred_at=now,
                summary=f"sample {kind.value}",
            )
        )
    session.commit()
    rows = (
        session.execute(select(LeadActivity).where(LeadActivity.lead_id == lead.id))
        .scalars()
        .all()
    )
    kinds = {r.kind for r in rows}
    assert kinds == {
        LeadActivityKind.email_open,
        LeadActivityKind.page_view,
        LeadActivityKind.form_submit,
    }


def test_lead_notes_basic(session: Session):
    org = _org(session)
    lead = _lead(session, org)
    note = LeadNote(
        lead_id=lead.id,
        organization_id=org.id,
        body="Spoke with Alice — interested in the Q3 release.",
    )
    session.add(note)
    session.commit()
    session.refresh(lead)
    assert len(lead.notes) == 1
    assert "Q3 release" in lead.notes[0].body


def test_all_lead_stage_values_round_trip(session: Session):
    org = _org(session)
    for s in LeadStage:
        _lead(session, org, email=f"l-{s.value}@x.io", stage=s)
    rows = session.execute(select(Lead)).scalars().all()
    assert {r.stage for r in rows} == set(LeadStage)


def test_activity_payload_json_roundtrip(session: Session):
    org = _org(session)
    lead = _lead(session, org)
    payload = {"from": "old@x.io", "to": "new@x.io", "diff": ["status"]}
    session.add(
        LeadActivity(
            lead_id=lead.id,
            organization_id=org.id,
            kind=LeadActivityKind.stage_change,
            occurred_at=datetime.now(tz=timezone.utc),
            payload_json=payload,
        )
    )
    session.commit()
    a = (
        session.execute(
            select(LeadActivity).where(LeadActivity.lead_id == lead.id)
        )
        .scalars()
        .one()
    )
    assert a.payload_json == payload
