"""Project endpoint tests."""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.project import Project, ProjectMembership
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
            full_name="Test",
            password_reset_required=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _seed_org_with(user: User, role: OrganizationRole, slug: str = "acme") -> Organization:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug=slug, name=slug.upper())
        session.add(org)
        await session.flush()
        session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role=role))
        await session.commit()
        await session.refresh(org)
        return org


async def _seed_project(org: Organization, slug: str = "q2-launch") -> Project:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        project = Project(organization_id=org.id, slug=slug, name=slug.title())
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project


async def _login(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_org_admin_can_create_project(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.admin)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    res = await client.post(
        f"/api/v1/orgs/{org.id}/projects",
        json={"slug": "q2-launch", "name": "Q2 Launch"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["slug"] == "q2-launch"
    assert body["organization_id"] == str(org.id)
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_org_viewer_cannot_create_project(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.viewer)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    res = await client.post(
        f"/api/v1/orgs/{org.id}/projects",
        json={"slug": "q2-launch", "name": "Q2 Launch"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_org_admin_sees_all_projects(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.admin)
    await _seed_project(org, slug="p-1")
    await _seed_project(org, slug="p-2")

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.get(f"/api/v1/orgs/{org.id}/projects", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    slugs = {p["slug"] for p in res.json()}
    assert slugs == {"p-1", "p-2"}


@pytest.mark.asyncio
async def test_non_admin_only_sees_assigned_projects(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")
    org = await _seed_org_with(alice, OrganizationRole.admin)
    p1 = await _seed_project(org, slug="p-1")
    p2 = await _seed_project(org, slug="p-2")

    # Make Bob a Creatives at the Org level (non-admin/non-manager)
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        session.add(
            OrganizationMembership(
                user_id=bob.id, organization_id=org.id, role=OrganizationRole.creatives
            )
        )
        # And assign him only to p1
        session.add(
            ProjectMembership(user_id=bob.id, project_id=p1.id, role=OrganizationRole.creatives)
        )
        await session.commit()

    token = await _login(client, "bob@example.com", "BobPwd123456!")
    res = await client.get(f"/api/v1/orgs/{org.id}/projects", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    slugs = {p["slug"] for p in res.json()}
    assert slugs == {"p-1"}, f"Bob should only see p-1, got {slugs}"


@pytest.mark.asyncio
async def test_admin_can_add_project_member(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")
    org = await _seed_org_with(alice, OrganizationRole.admin)
    project = await _seed_project(org)

    # Bob must be an Org member first
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        session.add(
            OrganizationMembership(user_id=bob.id, organization_id=org.id, role=OrganizationRole.creatives)
        )
        await session.commit()

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        f"/api/v1/orgs/{org.id}/projects/{project.id}/memberships",
        json={"user_id": str(bob.id), "role": "creatives"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text


@pytest.mark.asyncio
async def test_project_member_must_be_org_member_first(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")  # NOT in the org
    org = await _seed_org_with(alice, OrganizationRole.admin)
    project = await _seed_project(org)

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        f"/api/v1/orgs/{org.id}/projects/{project.id}/memberships",
        json={"user_id": str(bob.id), "role": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "organization member" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_project_delete_works_for_admin(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.admin)
    project = await _seed_project(org)

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.delete(
        f"/api/v1/orgs/{org.id}/projects/{project.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204
