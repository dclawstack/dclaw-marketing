"""Phase 11.4 — cost-logging helper unit tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.ops import CostLedger
from app.models.organization import Organization
from app.services.cost_logger import (
    PRICE_BOOK,
    _estimate,
    record_cost_sync,
)


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


def test_estimate_uses_price_book():
    # 3 images @ $0.003 each = $0.009
    assert _estimate("replicate", "image", 3.0) == pytest.approx(0.009)
    # 10s music @ $0.008/s = $0.08
    assert _estimate("replicate", "music_second", 10.0) == pytest.approx(0.08)


def test_estimate_unknown_returns_zero():
    assert _estimate("unknown", "image", 5.0) == 0.0
    assert _estimate("replicate", None, 5.0) == 0.0
    assert _estimate("replicate", "image", None) == 0.0


def test_record_cost_sync_writes_row(session: Session):
    org = _org(session)
    record_cost_sync(
        session,
        organization_id=org.id,
        provider="replicate",
        kind="image",
        units=3.0,
        units_kind="image",
        metadata={"aspect": "1:1"},
    )
    session.commit()
    rows = session.execute(select(CostLedger)).scalars().all()
    assert len(rows) == 1
    r = rows[0]
    assert r.provider == "replicate"
    assert r.kind == "image"
    assert r.units == 3.0
    assert r.amount_usd == pytest.approx(0.009)  # estimated from PRICE_BOOK
    assert r.metadata_json == {"aspect": "1:1"}


def test_explicit_amount_overrides_estimate(session: Session):
    org = _org(session)
    record_cost_sync(
        session,
        organization_id=org.id,
        provider="replicate",
        kind="image",
        units=3.0,
        units_kind="image",
        amount_usd=42.0,  # override
    )
    session.commit()
    r = session.execute(select(CostLedger)).scalars().one()
    assert r.amount_usd == 42.0


def test_none_session_is_noop():
    # Should not raise; should not write anywhere.
    record_cost_sync(
        None,
        organization_id=uuid4(),
        provider="replicate",
        kind="image",
        units=3.0,
        units_kind="image",
    )


def test_price_book_keys_are_consistent():
    expected = {
        ("replicate", "image"),
        ("replicate", "video_second"),
        ("replicate", "music_second"),
        ("elevenlabs", "char"),
        ("anthropic", "input_token"),
        ("anthropic", "output_token"),
        ("resend", "email"),
    }
    assert set(PRICE_BOOK.keys()) == expected


def test_exception_is_swallowed(session: Session, monkeypatch):
    """If session.add raises, record_cost_sync swallows it silently."""
    org = _org(session)

    def boom(*a, **kw):
        raise RuntimeError("DB on fire")

    monkeypatch.setattr(session, "add", boom)
    # Must not raise
    record_cost_sync(
        session,
        organization_id=org.id,
        provider="replicate",
        kind="image",
        units=1.0,
        units_kind="image",
    )
