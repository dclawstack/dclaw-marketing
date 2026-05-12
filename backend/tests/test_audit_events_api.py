"""A4 follow-up — read-only audit event browser tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.organization import Organization
from app.services.seo.audit import list_audit_findings  # type: ignore  # noqa: F401  (smoke import)
from tests.conftest import test_engine


@pytest_asyncio.fixture
async def seeded_org():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="audit-test", name="Audit Co")
        session.add(org)
        await session.flush()
        now = datetime.now(timezone.utc)
        rows = [
            AuditEvent(
                organization_id=org.id,
                actor_kind=AuditActorKind.user,
                action_type="approval.approved",
                target_type="approval",
                target_id="ap_1",
                payload_json={"reason": "lgtm"},
                result=AuditResult.success,
            ),
            AuditEvent(
                organization_id=org.id,
                actor_kind=AuditActorKind.agent,
                actor_agent="creatives_agent_v1",
                action_type="creatives.run",
                target_type="brief",
                target_id="b_1",
                payload_json={"variants": 3},
                result=AuditResult.success,
            ),
            AuditEvent(
                organization_id=org.id,
                actor_kind=AuditActorKind.system,
                action_type="poller.notion.page_seen",
                target_type="notion_page",
                target_id="p_1",
                payload_json={"title": "Roadmap"},
                result=AuditResult.success,
            ),
        ]
        session.add_all(rows)
        await session.flush()
        # Backdate one event so the days filter has something to exclude.
        rows[2].created_at = now - timedelta(days=60)
        await session.commit()
        await session.refresh(org)
        return org


@pytest.mark.asyncio
async def test_list_audit_events_paginates_and_filters_by_action_type(
    seeded_org,
):
    from app.api.v1.audit_events import list_audit_events
    from app.models.user import User

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        admin = User(
            email="admin@x.com",
            hashed_password="x",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        all_recent = await list_audit_events(
            organization_id=seeded_org.id,
            days=30,
            limit=50,
            offset=0,
            user=admin,
            session=session,
            action_type=None,
            actor_kind=None,
        )
    # Backdated row excluded by the 30-day window.
    assert all_recent.total == 2
    assert len(all_recent.items) == 2

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        only_approvals = await list_audit_events(
            organization_id=seeded_org.id,
            action_type="approval.approved",
            days=30,
            limit=10,
            offset=0,
            user=admin,
            session=session,
            actor_kind=None,
        )
    assert only_approvals.total == 1
    assert only_approvals.items[0].action_type == "approval.approved"


@pytest.mark.asyncio
async def test_get_audit_event_returns_full_payload(seeded_org):
    from app.api.v1.audit_events import get_audit_event
    from app.models.user import User

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        admin = User(
            email="admin2@x.com",
            hashed_password="x",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        from sqlalchemy import select

        evs = (
            await session.execute(
                select(AuditEvent).where(
                    AuditEvent.organization_id == seeded_org.id,
                    AuditEvent.action_type == "creatives.run",
                )
            )
        ).scalars().all()
    assert evs

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        out = await get_audit_event(
            event_id=evs[0].id, user=admin, session=session
        )
    assert out.action_type == "creatives.run"
    assert out.payload_json == {"variants": 3}
