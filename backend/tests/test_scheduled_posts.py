"""Phase 4 — ScheduledPost endpoint tests."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from app.models.user import User
from tests.conftest import test_engine


_helper = PasswordHelper()


async def _seed_user(
    email: str, password: str, *, is_superuser: bool = False
) -> User:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        u = User(
            email=email,
            hashed_password=_helper.hash(password),
            is_active=True,
            is_superuser=is_superuser,
            is_verified=True,
            full_name="Test",
            password_reset_required=False,
        )
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u


async def _seed_org_with(
    user: User, role: OrganizationRole, slug: str = "acme"
) -> Organization:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug=slug, name=slug.upper())
        session.add(org)
        await session.flush()
        session.add(
            OrganizationMembership(
                user_id=user.id, organization_id=org.id, role=role
            )
        )
        await session.commit()
        await session.refresh(org)
        return org


async def _login(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_create_scheduled_post(client):
    user = await _seed_user("a@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.social_media_manager)
    token = await _login(client, "a@example.com", "AdminPwd123!")

    when = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
    res = await client.post(
        f"/api/v1/orgs/{org.id}/scheduled-posts",
        json={
            "channel": "linkedin",
            "scheduled_at": when,
            "copy": "Hello world",
            "tags": ["product", "launch"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["channel"] == "linkedin"
    assert body["copy"] == "Hello world"
    assert body["status"] == "queued"
    assert body["created_by_user_id"] == str(user.id)


@pytest.mark.asyncio
async def test_create_rejected_for_role_without_write(client):
    user = await _seed_user("v@example.com", "ViewPwd123!")
    org = await _seed_org_with(user, OrganizationRole.viewer)
    token = await _login(client, "v@example.com", "ViewPwd123!")

    when = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
    res = await client.post(
        f"/api/v1/orgs/{org.id}/scheduled-posts",
        json={"channel": "x", "scheduled_at": when, "copy": "nope"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_list_filters_by_status_and_channel(client):
    user = await _seed_user("a@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "a@example.com", "AdminPwd123!")

    base = datetime.now(tz=timezone.utc) + timedelta(hours=2)
    for ch in ("linkedin", "x", "linkedin"):
        res = await client.post(
            f"/api/v1/orgs/{org.id}/scheduled-posts",
            json={"channel": ch, "scheduled_at": base.isoformat(), "copy": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201

    res = await client.get(
        f"/api/v1/orgs/{org.id}/scheduled-posts?channel=linkedin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert len(res.json()) == 2
    assert all(p["channel"] == "linkedin" for p in res.json())


@pytest.mark.asyncio
async def test_cancel_and_publish_now(client):
    user = await _seed_user("a@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "a@example.com", "AdminPwd123!")

    when = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
    create = await client.post(
        f"/api/v1/orgs/{org.id}/scheduled-posts",
        json={"channel": "bluesky", "scheduled_at": when, "copy": "y"},
        headers={"Authorization": f"Bearer {token}"},
    )
    pid = create.json()["id"]

    # publish-now bumps scheduled_at to ~now
    bump = await client.post(
        f"/api/v1/orgs/{org.id}/scheduled-posts/{pid}/publish-now",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bump.status_code == 200
    bumped_at = datetime.fromisoformat(bump.json()["scheduled_at"])
    assert (datetime.now(tz=timezone.utc) - bumped_at).total_seconds() < 5

    # cancel works
    cancel = await client.delete(
        f"/api/v1/orgs/{org.id}/scheduled-posts/{pid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_reject_far_past_scheduled_at(client):
    user = await _seed_user("a@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "a@example.com", "AdminPwd123!")

    far_past = (datetime.now(tz=timezone.utc) - timedelta(days=3)).isoformat()
    res = await client.post(
        f"/api/v1/orgs/{org.id}/scheduled-posts",
        json={"channel": "linkedin", "scheduled_at": far_past, "copy": "old"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
