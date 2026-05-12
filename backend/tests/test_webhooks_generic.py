"""Theme D4 — generic webhook receiver + automation rules tests."""

from __future__ import annotations

import hashlib
import hmac

import pytest
import pytest_asyncio
from fastapi_users.password import PasswordHelper
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from app.models.user import User
from app.models.webhook import (
    Automation,
    Webhook,
    WebhookEvent,
    WebhookEventStatus,
)
from tests.conftest import test_engine


_helper = PasswordHelper()


async def _seed_admin_org(slug: str = "wh") -> tuple[User, Organization, str]:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        user = User(
            email=f"{slug}@x.com",
            hashed_password=_helper.hash("AdminPwd123!"),
            is_active=True,
            is_superuser=False,
            is_verified=True,
            full_name="A",
            password_reset_required=False,
        )
        session.add(user)
        await session.flush()
        org = Organization(slug=slug, name=slug)
        session.add(org)
        await session.flush()
        session.add(
            OrganizationMembership(
                user_id=user.id,
                organization_id=org.id,
                role=OrganizationRole.admin,
            )
        )
        await session.commit()
        await session.refresh(user)
        await session.refresh(org)
        return user, org, "AdminPwd123!"


async def _login(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


# ---------- CRUD ----------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_create_and_list_webhooks(client):
    user, org, pwd = await _seed_admin_org("crud")
    token = await _login(client, user.email, pwd)

    res = await client.post(
        "/api/v1/webhooks",
        json={
            "organization_id": str(org.id),
            "name": "Calendly",
            "source": "calendly",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "Calendly"
    assert body["source"] == "calendly"
    assert len(body["token"]) > 16

    listed = await client.get(
        f"/api/v1/webhooks?organization_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


# ---------- Public ingest -------------------------------------------------


@pytest.mark.asyncio
async def test_generic_webhook_writes_event(client):
    user, org, pwd = await _seed_admin_org("ing")
    token = await _login(client, user.email, pwd)

    # Create a webhook
    create = await client.post(
        "/api/v1/webhooks",
        json={"organization_id": str(org.id), "name": "Stripe"},
        headers={"Authorization": f"Bearer {token}"},
    )
    hook_token = create.json()["token"]

    # Send a payload
    res = await client.post(
        f"/api/v1/webhooks/generic/{hook_token}",
        json={"type": "checkout.session.completed", "id": "evt_1"},
    )
    assert res.status_code == 202, res.text
    assert res.json()["received"] is True

    # Row landed
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        events = (
            (await session.execute(select(WebhookEvent))).scalars().all()
        )
        assert len(events) == 1
        evt = events[0]
        assert evt.status == WebhookEventStatus.pending
        assert evt.payload_json["type"] == "checkout.session.completed"


@pytest.mark.asyncio
async def test_generic_webhook_hmac_rejects_bad_sig(client):
    user, org, pwd = await _seed_admin_org("hmac")
    token = await _login(client, user.email, pwd)

    create = await client.post(
        "/api/v1/webhooks",
        json={
            "organization_id": str(org.id),
            "name": "GitHub",
            "secret": "topsecret",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    hook_token = create.json()["token"]

    # Wrong signature → 401
    bad = await client.post(
        f"/api/v1/webhooks/generic/{hook_token}",
        json={"foo": "bar"},
        headers={"X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert bad.status_code == 401

    # Right signature → 202.
    body = b'{"foo": "bar"}'
    sig = (
        "sha256="
        + hmac.new(b"topsecret", body, hashlib.sha256).hexdigest()
    )
    good = await client.post(
        f"/api/v1/webhooks/generic/{hook_token}",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert good.status_code == 202, good.text


@pytest.mark.asyncio
async def test_generic_webhook_unknown_token_404(client):
    res = await client.post(
        "/api/v1/webhooks/generic/not-a-real-token", json={}
    )
    assert res.status_code == 404


# ---------- Automation runner --------------------------------------------


@pytest.mark.asyncio
async def test_automation_runner_dispatches_audit_for_match(client):
    """Seed a webhook + an Automation that filters on type=
    'lead.created' + audit-only action. Send a matching payload.
    Run the task. AuditEvent should appear."""
    from app.worker.tasks.automation import process_pending_events

    user, org, pwd = await _seed_admin_org("auto")
    token = await _login(client, user.email, pwd)

    create = await client.post(
        "/api/v1/webhooks",
        json={"organization_id": str(org.id), "name": "HubSpot"},
        headers={"Authorization": f"Bearer {token}"},
    )
    hook_token = create.json()["token"]
    webhook_id = create.json()["id"]

    await client.post(
        "/api/v1/automations",
        json={
            "organization_id": str(org.id),
            "name": "New HubSpot lead → audit",
            "webhook_id": webhook_id,
            "filter_json": {"type": "lead.created"},
            "actions_json": [
                {"action": "log_only", "params": {"note": "matched"}}
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Two payloads: one matching, one not.
    await client.post(
        f"/api/v1/webhooks/generic/{hook_token}",
        json={"type": "lead.created", "email": "a@b.co"},
    )
    await client.post(
        f"/api/v1/webhooks/generic/{hook_token}",
        json={"type": "lead.deleted"},
    )

    counts = process_pending_events()
    assert counts["processed"] == 1
    assert counts["ignored"] == 1

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        audits = (
            (
                await session.execute(
                    select(AuditEvent).where(
                        AuditEvent.action_type == "automation.log_only"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(audits) == 1
        assert audits[0].payload_json["automation_name"] == (
            "New HubSpot lead → audit"
        )

        autos = (await session.execute(select(Automation))).scalars().all()
        assert autos[0].match_count == 1
