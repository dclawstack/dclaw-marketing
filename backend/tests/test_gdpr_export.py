"""Phase 11.3 — GDPR export unit tests."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.connection import Connection, ConnectionStatus
from app.models.lead import Lead, LeadStatus
from app.models.organization import Organization
from app.models.social_account import (
    SocialAccount,
    SocialAccountStatus,
    SocialPlatform,
)
from app.worker.tasks.gdpr import REDACTED, build_export


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
    o = Organization(slug="t", name="T Org", is_external=False)
    session.add(o)
    session.commit()
    session.refresh(o)
    return o


def test_minimal_export_has_required_top_level_keys(session: Session):
    org = _org(session)
    payload = build_export(session, org.id)

    for k in [
        "schema_version", "exported_at", "organization",
        "memberships", "projects", "brand_kits", "personas",
        "campaigns", "leads", "scheduled_posts", "approval_requests",
        "social_accounts", "connections", "agent_threads",
        "touchpoints", "conversions", "agent_messages",
    ]:
        assert k in payload, f"missing key: {k}"
    assert payload["schema_version"] == 1
    assert payload["organization"]["slug"] == "t"


def test_unknown_org_raises(session: Session):
    import uuid
    with pytest.raises(ValueError):
        build_export(session, uuid.uuid4())


def test_leads_are_included(session: Session):
    org = _org(session)
    session.add(
        Lead(
            organization_id=org.id,
            email="alice@example.com",
            status=LeadStatus.new,
        )
    )
    session.commit()
    payload = build_export(session, org.id)
    assert len(payload["leads"]) == 1
    assert payload["leads"][0]["email"] == "alice@example.com"


def test_social_account_tokens_are_redacted(session: Session):
    org = _org(session)
    sa = SocialAccount(
        organization_id=org.id,
        platform=SocialPlatform.bluesky,
        handle="alice.bsky.social",
        _interim_access_token="SECRET-APP-PASSWORD",
        auth_metadata_json={"refresh_token": "ANOTHER-SECRET"},
        status=SocialAccountStatus.active,
    )
    session.add(sa)
    session.commit()
    payload = build_export(session, org.id)
    sa_dump = payload["social_accounts"][0]
    assert sa_dump["interim_access_token"] == REDACTED
    assert sa_dump["auth_metadata_json"] == REDACTED
    # Non-secret fields still present
    assert sa_dump["handle"] == "alice.bsky.social"
    assert sa_dump["platform"] == "bluesky"


def test_connection_encrypted_blob_is_redacted(session: Session):
    org = _org(session)
    conn = Connection(
        organization_id=org.id,
        server_id="hubspot",
        name="prod",
        auth_kind="oauth2",
        encrypted_secret_blob=b"\x00\x01\x02 SECRET BYTES \x03\x04",
        metadata_json={"workspace": "main"},
        status=ConnectionStatus.active,
    )
    session.add(conn)
    session.commit()
    payload = build_export(session, org.id)
    c_dump = payload["connections"][0]
    assert c_dump["encrypted_secret_blob"] == REDACTED
    # Plaintext metadata stays
    assert c_dump["metadata_json"] == {"workspace": "main"}


def test_organization_id_is_serialized_as_string(session: Session):
    org = _org(session)
    payload = build_export(session, org.id)
    assert payload["organization"]["id"] == str(org.id)
    assert isinstance(payload["organization"]["id"], str)
