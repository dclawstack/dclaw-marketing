"""Organization endpoint tests."""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.user import User
from tests.conftest import test_engine


_helper = PasswordHelper()


async def _seed_user(email: str, password: str, *, is_superuser: bool = False) -> User:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        user = User(
            email=email,
            hashed_password=_helper.hash(password),
            is_active=True,
            is_superuser=is_superuser,
            is_verified=True,
            full_name="Test User",
            password_reset_required=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _seed_org_with_member(slug: str, user: User, role: OrganizationRole) -> Organization:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug=slug, name=f"Org {slug}", description="seed")
        session.add(org)
        await session.flush()
        session.add(
            OrganizationMembership(user_id=user.id, organization_id=org.id, role=role)
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
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_superuser_creates_org_and_becomes_admin(client):
    admin = await _seed_user("admin@example.com", "AdminPwd123!", is_superuser=True)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.post(
        "/api/v1/orgs",
        json={"slug": "acme", "name": "Acme Inc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["slug"] == "acme"
    assert body["name"] == "Acme Inc"
    assert body["is_external"] is False

    # The creating superuser is auto-added as Org Admin
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        from sqlalchemy import select
        result = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == admin.id,
                OrganizationMembership.organization_id == body["id"],
            )
        )
        membership = result.scalar_one_or_none()
        assert membership is not None
        assert membership.role == OrganizationRole.admin


@pytest.mark.asyncio
async def test_non_superuser_cannot_create_org(client):
    await _seed_user("regular@example.com", "RegularPwd123!")
    token = await _login(client, "regular@example.com", "RegularPwd123!")

    res = await client.post(
        "/api/v1/orgs",
        json={"slug": "stealth", "name": "Stealth"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_slug_rejected(client):
    await _seed_user("admin@example.com", "AdminPwd123!", is_superuser=True)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    r1 = await client.post(
        "/api/v1/orgs",
        json={"slug": "acme", "name": "Acme"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/orgs",
        json={"slug": "acme", "name": "Acme Duplicate"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_user_only_sees_their_own_orgs(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")
    org_a = await _seed_org_with_member("alice-org", alice, OrganizationRole.manager)
    org_b = await _seed_org_with_member("bob-org", bob, OrganizationRole.manager)

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.get("/api/v1/orgs", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    slugs = [o["slug"] for o in res.json()]
    assert "alice-org" in slugs
    assert "bob-org" not in slugs


@pytest.mark.asyncio
async def test_superuser_sees_all_orgs(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    await _seed_org_with_member("alice-org", alice, OrganizationRole.manager)

    await _seed_user("admin@example.com", "AdminPwd123!", is_superuser=True)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.get("/api/v1/orgs", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    slugs = [o["slug"] for o in res.json()]
    assert "alice-org" in slugs


@pytest.mark.asyncio
async def test_non_member_cannot_get_org_detail(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with_member("private-org", alice, OrganizationRole.admin)
    await _seed_user("intruder@example.com", "Intruder123!")

    token = await _login(client, "intruder@example.com", "Intruder123!")
    res = await client.get(f"/api/v1/orgs/{org.id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_add_member_to_org(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")
    org = await _seed_org_with_member("acme", alice, OrganizationRole.admin)

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        f"/api/v1/orgs/{org.id}/memberships",
        json={"user_id": str(bob.id), "role": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["role"] == "viewer"


@pytest.mark.asyncio
async def test_viewer_cannot_add_member(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")
    org = await _seed_org_with_member("acme", alice, OrganizationRole.viewer)

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        f"/api/v1/orgs/{org.id}/memberships",
        json={"user_id": str(bob.id), "role": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
