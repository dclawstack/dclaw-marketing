"""BrandKit + Persona endpoint tests."""

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


async def _seed_org_with(user: User, role: OrganizationRole, slug: str = "acme") -> Organization:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug=slug, name=slug.upper())
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
async def test_create_first_brand_kit_is_active_v1(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits",
        json={
            "name": "v1",
            "palette": {"primary": "#7660A8", "secondary": "#9384BD"},
            "fonts": {"display": "Poppins"},
            "voice": {"do_say": ["clear"], "dont_say": ["hype"]},
            "personas": [
                {"name": "CMO", "fears": ["budget overrun"], "desires": ["growth"]}
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "v1"
    assert body["version"] == 1
    assert body["is_active"] is True
    assert body["palette_json"]["primary"] == "#7660A8"
    assert len(body["personas"]) == 1
    assert body["personas"][0]["name"] == "CMO"


@pytest.mark.asyncio
async def test_creating_new_kit_deactivates_previous_and_bumps_version(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    # First kit
    r1 = await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits",
        json={"name": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201
    v1_id = r1.json()["id"]
    assert r1.json()["version"] == 1

    # Second kit — should bump to v2 and deactivate v1
    r2 = await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits",
        json={"name": "v2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 201
    assert r2.json()["version"] == 2
    assert r2.json()["is_active"] is True

    # Refetch v1 — should be inactive
    rv1 = await client.get(
        f"/api/v1/orgs/{org.id}/brand-kits/{v1_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rv1.status_code == 200
    assert rv1.json()["is_active"] is False


@pytest.mark.asyncio
async def test_get_active_brand_kit(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits",
        json={"name": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    res = await client.get(
        f"/api/v1/orgs/{org.id}/brand-kits/active",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is True
    assert res.json()["name"] == "v1"


@pytest.mark.asyncio
async def test_active_404_when_none_exists(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.get(
        f"/api/v1/orgs/{org.id}/brand-kits/active",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_activate_old_version(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    r1 = await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits",
        json={"name": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    v1_id = r1.json()["id"]
    await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits",
        json={"name": "v2"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Roll back to v1
    res = await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits/{v1_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is True

    active = await client.get(
        f"/api/v1/orgs/{org.id}/brand-kits/active",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert active.json()["id"] == v1_id


@pytest.mark.asyncio
async def test_viewer_cannot_create(client):
    user = await _seed_user("viewer@example.com", "ViewPwd1234!")
    org = await _seed_org_with(user, OrganizationRole.viewer)
    token = await _login(client, "viewer@example.com", "ViewPwd1234!")

    res = await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits",
        json={"name": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_creatives_role_can_create(client):
    user = await _seed_user("designer@example.com", "DesignPwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)
    token = await _login(client, "designer@example.com", "DesignPwd123!")

    res = await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits",
        json={"name": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_patch_updates_palette_voice_etc(client):
    user = await _seed_user("admin@example.com", "AdminPwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    r1 = await client.post(
        f"/api/v1/orgs/{org.id}/brand-kits",
        json={"name": "v1", "palette": {"primary": "#111"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    kit_id = r1.json()["id"]

    r2 = await client.patch(
        f"/api/v1/orgs/{org.id}/brand-kits/{kit_id}",
        json={"palette": {"primary": "#222", "secondary": "#aaa"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["palette_json"]["primary"] == "#222"
    assert r2.json()["palette_json"]["secondary"] == "#aaa"
    # version still 1 — PATCH doesn't bump version (use POST for that)
    assert r2.json()["version"] == 1
