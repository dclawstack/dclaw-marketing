"""Q5 — Goals & Constraints endpoint tests."""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

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


async def _seed_org_with(user: User, role: OrganizationRole) -> Organization:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="acme", name="ACME")
        session.add(org)
        await session.flush()
        session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role=role))
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
async def test_get_goals_empty_initially(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.get(
        f"/api/v1/orgs/{org.id}/goals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["goals"] is None
    assert body["constraints"] is None
    assert body["autonomy_posture"] is None


@pytest.mark.asyncio
async def test_put_goals_persists(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.put(
        f"/api/v1/orgs/{org.id}/goals",
        json={
            "goals": {"objectives": ["leads", "revenue"], "target_quarterly_value": 500},
            "constraints": {"brand_safety_lines": ["no political content"]},
            "autonomy_posture": {"social_post": "hard_gate"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["goals"]["objectives"] == ["leads", "revenue"]
    assert body["constraints"]["brand_safety_lines"] == ["no political content"]
    assert body["autonomy_posture"]["social_post"] == "hard_gate"

    # Reload and confirm persistence
    res2 = await client.get(
        f"/api/v1/orgs/{org.id}/goals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.json()["goals"]["target_quarterly_value"] == 500


@pytest.mark.asyncio
async def test_put_goals_patch_style(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    # Set goals
    await client.put(
        f"/api/v1/orgs/{org.id}/goals",
        json={"goals": {"objectives": ["leads"]}, "constraints": {"max_daily_posts": 6}},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Update only autonomy_posture — goals and constraints should remain
    res = await client.put(
        f"/api/v1/orgs/{org.id}/goals",
        json={"autonomy_posture": {"social_post": "soft_gate"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    # Untouched fields preserved
    assert body["goals"]["objectives"] == ["leads"]
    assert body["constraints"]["max_daily_posts"] == 6
    # New field set
    assert body["autonomy_posture"]["social_post"] == "soft_gate"


@pytest.mark.asyncio
async def test_viewer_can_read_but_not_write(client):
    user = await _seed_user("viewer@example.com", "ViewPwd1234!")
    org = await _seed_org_with(user, OrganizationRole.viewer)
    token = await _login(client, "viewer@example.com", "ViewPwd1234!")

    # Read is OK
    read = await client.get(
        f"/api/v1/orgs/{org.id}/goals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert read.status_code == 200

    # Write is forbidden
    write = await client.put(
        f"/api/v1/orgs/{org.id}/goals",
        json={"goals": {"objectives": ["bad"]}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert write.status_code == 403


@pytest.mark.asyncio
async def test_non_member_cannot_read(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    await _seed_user("intruder@example.com", "Intruder123!")

    token = await _login(client, "intruder@example.com", "Intruder123!")
    res = await client.get(
        f"/api/v1/orgs/{org.id}/goals",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_manager_can_write(client):
    user = await _seed_user("mgr@example.com", "MgrPwd1234567!")
    org = await _seed_org_with(user, OrganizationRole.manager)
    token = await _login(client, "mgr@example.com", "MgrPwd1234567!")

    res = await client.put(
        f"/api/v1/orgs/{org.id}/goals",
        json={"goals": {"icps": ["b2b-cmo"]}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
