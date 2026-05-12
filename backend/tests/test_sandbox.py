"""Phase 11.5 — sandbox / dry-run helper unit tests."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.organization import Organization
from app.services.sandbox import (
    _read_flag,
    is_sandbox_mode_sync,
    sandbox_publish_result,
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


def _org(s: Session, *, constraints: dict | None = None) -> Organization:
    o = Organization(
        slug=f"o-{uuid4().hex[:8]}",
        name="T",
        is_external=False,
        constraints_json=constraints,
    )
    s.add(o)
    s.commit()
    s.refresh(o)
    return o


def test_read_flag_handles_none_org():
    assert _read_flag(None) is False


def test_read_flag_handles_none_constraints():
    fake = SimpleNamespace(constraints_json=None)
    assert _read_flag(fake) is False


def test_read_flag_handles_non_dict():
    fake = SimpleNamespace(constraints_json="not a dict")
    assert _read_flag(fake) is False


def test_read_flag_false_when_missing():
    fake = SimpleNamespace(constraints_json={})
    assert _read_flag(fake) is False


def test_read_flag_returns_true_when_set():
    fake = SimpleNamespace(constraints_json={"sandbox_mode": True})
    assert _read_flag(fake) is True


def test_read_flag_coerces_truthy():
    fake = SimpleNamespace(constraints_json={"sandbox_mode": "yes"})
    # Anything truthy → True
    assert _read_flag(fake) is True


def test_is_sandbox_mode_sync_default_false(session: Session):
    org = _org(session)
    assert is_sandbox_mode_sync(session, org.id) is False


def test_is_sandbox_mode_sync_true_when_set(session: Session):
    org = _org(session, constraints={"sandbox_mode": True})
    assert is_sandbox_mode_sync(session, org.id) is True


def test_is_sandbox_mode_sync_unknown_org_false(session: Session):
    """Conservative: unknown org id returns False (no dry-run)."""
    import uuid
    assert is_sandbox_mode_sync(session, uuid.uuid4()) is False


def test_sandbox_publish_result_shape():
    r = sandbox_publish_result("bluesky", "hello world")
    assert r.provider == "bluesky"
    assert r.remote_id.startswith("sandbox-")
    assert r.permalink is None
    assert r.raw["sandbox"] is True
    assert r.raw["stub"] is True
    assert r.raw["channel"] == "bluesky"


def test_sandbox_publish_result_deterministic():
    a = sandbox_publish_result("x", "same")
    b = sandbox_publish_result("x", "same")
    assert a.remote_id == b.remote_id
