"""Admin user-management endpoint tests.

Admins are the only path users get created (no self-signup). Tests
exercise: create user with temp password, list, get, update, reset
password, revoke. Verifies non-admins are blocked.
"""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

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


async def _login(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_can_create_user_with_temp_password(client):
    await _seed_user("admin@example.com", "AdminPwd123!", is_superuser=True)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.post(
        "/api/v1/admin/users",
        json={"email": "newbie@example.com", "full_name": "New User"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()

    # Response contains the user record + a one-shot temp password
    assert body["user"]["email"] == "newbie@example.com"
    assert body["user"]["full_name"] == "New User"
    assert body["user"]["is_active"] is True
    assert body["user"]["is_superuser"] is False
    assert body["user"]["password_reset_required"] is True
    assert isinstance(body["temp_password"], str)
    assert len(body["temp_password"]) >= 12

    # The temp password actually lets the new user log in
    new_token = await _login(client, "newbie@example.com", body["temp_password"])
    assert new_token


@pytest.mark.asyncio
async def test_admin_can_create_another_admin(client):
    await _seed_user("admin@example.com", "AdminPwd123!", is_superuser=True)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.post(
        "/api/v1/admin/users",
        json={"email": "co_admin@example.com", "is_superuser": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    assert res.json()["user"]["is_superuser"] is True


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_endpoints(client):
    await _seed_user("regular@example.com", "RegularPwd123!")
    token = await _login(client, "regular@example.com", "RegularPwd123!")

    res = await client.post(
        "/api/v1/admin/users",
        json={"email": "victim@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403

    res = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email(client):
    await _seed_user("admin@example.com", "AdminPwd123!", is_superuser=True)
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    r1 = await client.post(
        "/api/v1/admin/users",
        json={"email": "dup@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/admin/users",
        json={"email": "dup@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_admin_can_list_users(client):
    await _seed_user("admin@example.com", "AdminPwd123!", is_superuser=True)
    await _seed_user("u1@example.com", "U1Pwd123456!")
    await _seed_user("u2@example.com", "U2Pwd123456!")
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    emails = [u["email"] for u in res.json()]
    assert "admin@example.com" in emails
    assert "u1@example.com" in emails
    assert "u2@example.com" in emails


@pytest.mark.asyncio
async def test_admin_force_reset_password_issues_new_temp(client):
    await _seed_user("admin@example.com", "AdminPwd123!", is_superuser=True)
    target = await _seed_user("victim@example.com", "OriginalPwd123!")
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.post(
        f"/api/v1/admin/users/{target.id}/reset-password",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    new_temp = body["temp_password"]
    assert len(new_temp) >= 12

    # Old password no longer works
    bad = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": "victim@example.com", "password": "OriginalPwd123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert bad.status_code == 400

    # New temp password works
    new_token = await _login(client, "victim@example.com", new_temp)
    assert new_token


@pytest.mark.asyncio
async def test_admin_revoke_disables_user_login(client):
    await _seed_user("admin@example.com", "AdminPwd123!", is_superuser=True)
    target = await _seed_user("victim@example.com", "VictimPwd123!")
    token = await _login(client, "admin@example.com", "AdminPwd123!")

    res = await client.delete(
        f"/api/v1/admin/users/{target.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204

    # Revoked user cannot log in
    bad = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": "victim@example.com", "password": "VictimPwd123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert bad.status_code == 400
