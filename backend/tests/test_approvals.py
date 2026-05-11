"""Approval queue + audit log tests."""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.audit_event import AuditActorKind, AuditEvent
from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.user import User
from tests.conftest import test_engine


_helper = PasswordHelper()


async def _seed_user(email: str, password: str, *, is_superuser: bool = False) -> User:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        u = User(
            email=email,
            hashed_password=_helper.hash(password),
            is_active=True, is_superuser=is_superuser, is_verified=True,
            full_name="Test", password_reset_required=False,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u


async def _seed_org_with(user: User, role: OrganizationRole, slug: str = "acme") -> Organization:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug=slug, name=slug.upper())
        session.add(org)
        await session.flush()
        session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role=role))
        await session.commit()
        await session.refresh(org)
        return org


async def _add_member(org: Organization, user: User, role: OrganizationRole) -> None:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        session.add(
            OrganizationMembership(user_id=user.id, organization_id=org.id, role=role)
        )
        await session.commit()


async def _login(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return res.json()["access_token"]


# ---------- create + list -----------------------------------------------

@pytest.mark.asyncio
async def test_create_pending_approval(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.creatives)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    res = await client.post(
        "/api/v1/approvals",
        json={
            "organization_id": str(org.id),
            "action_type": "publish_post",
            "target_type": "scheduled_post",
            "target_id": "post-abc",
            "payload": {"channel": "x", "text": "Hello world"},
            "summary": "Publish to @acme: Hello world",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "pending"
    assert body["action_type"] == "publish_post"
    assert body["payload_json"]["text"] == "Hello world"
    assert body["requested_by_user_id"] == str(alice.id)


@pytest.mark.asyncio
async def test_list_approvals_scoped_to_my_orgs(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")
    org_a = await _seed_org_with(alice, OrganizationRole.admin, slug="acme")
    org_b = await _seed_org_with(bob, OrganizationRole.admin, slug="zenith")

    # Alice creates approval in her org; Bob creates one in his
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        session.add(ApprovalRequest(
            organization_id=org_a.id, requested_by_user_id=alice.id,
            action_type="publish_post", payload_json={"x": 1},
        ))
        session.add(ApprovalRequest(
            organization_id=org_b.id, requested_by_user_id=bob.id,
            action_type="send_email", payload_json={"y": 2},
        ))
        await session.commit()

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.get("/api/v1/approvals", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    action_types = [a["action_type"] for a in res.json()]
    assert "publish_post" in action_types
    assert "send_email" not in action_types  # Bob's org, hidden from Alice


# ---------- approve / reject --------------------------------------------

@pytest.mark.asyncio
async def test_reviewer_can_approve_writes_audit(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    reviewer = await _seed_user("rev@example.com", "RevPwd1234567!")
    org = await _seed_org_with(alice, OrganizationRole.creatives)
    await _add_member(org, reviewer, OrganizationRole.reviewer)

    # Alice creates an approval
    alice_token = await _login(client, "alice@example.com", "AlicePwd123!")
    create = await client.post(
        "/api/v1/approvals",
        json={
            "organization_id": str(org.id),
            "action_type": "publish_post",
            "payload": {"text": "hello"},
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    approval_id = create.json()["id"]

    # Reviewer approves
    rev_token = await _login(client, "rev@example.com", "RevPwd1234567!")
    res = await client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"reason": "looks great"},
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "approved"
    assert body["decided_by_user_id"] == str(reviewer.id)
    assert body["decision_reason"] == "looks great"

    # Audit event was written
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        events = await session.execute(
            select(AuditEvent).where(AuditEvent.action_type == "approval.approved")
        )
        evs = list(events.scalars().all())
        assert len(evs) == 1
        assert evs[0].actor_kind == AuditActorKind.user
        assert evs[0].actor_user_id == reviewer.id
        assert evs[0].approval_request_id is not None


@pytest.mark.asyncio
async def test_reject_with_reason(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    reviewer = await _seed_user("rev@example.com", "RevPwd1234567!")
    org = await _seed_org_with(alice, OrganizationRole.creatives)
    await _add_member(org, reviewer, OrganizationRole.reviewer)

    alice_token = await _login(client, "alice@example.com", "AlicePwd123!")
    create = await client.post(
        "/api/v1/approvals",
        json={
            "organization_id": str(org.id),
            "action_type": "publish_post",
            "payload": {"text": "questionable"},
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    approval_id = create.json()["id"]

    rev_token = await _login(client, "rev@example.com", "RevPwd1234567!")
    res = await client.post(
        f"/api/v1/approvals/{approval_id}/reject",
        json={"reason": "off-brand tone"},
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"
    assert res.json()["decision_reason"] == "off-brand tone"


@pytest.mark.asyncio
async def test_cannot_decide_own_approval_four_eye_rule(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.admin)  # alice is admin

    alice_token = await _login(client, "alice@example.com", "AlicePwd123!")
    create = await client.post(
        "/api/v1/approvals",
        json={
            "organization_id": str(org.id),
            "action_type": "publish_post",
            "payload": {"text": "self-approving"},
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    approval_id = create.json()["id"]

    # Alice tries to approve her own request
    res = await client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"reason": "I love it"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res.status_code == 403
    assert "own approval" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_viewer_cannot_decide(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    viewer = await _seed_user("viewer@example.com", "ViewerPwd123!")
    org = await _seed_org_with(alice, OrganizationRole.creatives)
    await _add_member(org, viewer, OrganizationRole.viewer)  # not reviewer/manager/admin

    alice_token = await _login(client, "alice@example.com", "AlicePwd123!")
    create = await client.post(
        "/api/v1/approvals",
        json={
            "organization_id": str(org.id),
            "action_type": "publish_post",
            "payload": {"text": "hello"},
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    approval_id = create.json()["id"]

    viewer_token = await _login(client, "viewer@example.com", "ViewerPwd123!")
    res = await client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"reason": "yolo"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_cannot_approve_twice(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    reviewer = await _seed_user("rev@example.com", "RevPwd1234567!")
    org = await _seed_org_with(alice, OrganizationRole.creatives)
    await _add_member(org, reviewer, OrganizationRole.reviewer)

    alice_token = await _login(client, "alice@example.com", "AlicePwd123!")
    create = await client.post(
        "/api/v1/approvals",
        json={"organization_id": str(org.id), "action_type": "publish_post", "payload": {}},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    approval_id = create.json()["id"]

    rev_token = await _login(client, "rev@example.com", "RevPwd1234567!")
    r1 = await client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"reason": "first"},
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert r1.status_code == 200

    r2 = await client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"reason": "second"},
        headers={"Authorization": f"Bearer {rev_token}"},
    )
    assert r2.status_code == 409


# ---------- cancel ------------------------------------------------------

@pytest.mark.asyncio
async def test_requester_can_cancel_own(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.creatives)

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    create = await client.post(
        "/api/v1/approvals",
        json={"organization_id": str(org.id), "action_type": "publish_post", "payload": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    approval_id = create.json()["id"]

    res = await client.post(
        f"/api/v1/approvals/{approval_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_non_requester_cannot_cancel(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")
    org = await _seed_org_with(alice, OrganizationRole.creatives)
    await _add_member(org, bob, OrganizationRole.creatives)

    alice_token = await _login(client, "alice@example.com", "AlicePwd123!")
    create = await client.post(
        "/api/v1/approvals",
        json={"organization_id": str(org.id), "action_type": "publish_post", "payload": {}},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    approval_id = create.json()["id"]

    bob_token = await _login(client, "bob@example.com", "BobPwd123456!")
    res = await client.post(
        f"/api/v1/approvals/{approval_id}/cancel",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res.status_code == 403
