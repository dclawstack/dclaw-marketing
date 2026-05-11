"""Auth flow tests — login, first-login mandatory reset, profile."""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.conftest import test_engine


_helper = PasswordHelper()


async def _create_user(email: str, password: str, *, is_superuser: bool = False, password_reset_required: bool = False) -> User:
    """Insert a user directly into the test DB and return it."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        user = User(
            email=email,
            hashed_password=_helper.hash(password),
            is_active=True,
            is_superuser=is_superuser,
            is_verified=True,
            full_name="Test User",
            password_reset_required=password_reset_required,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _login(client, email: str, password: str) -> str:
    """Login via FastAPI-Users OAuth2 form endpoint; return the JWT."""
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_login_with_valid_credentials_returns_token(client):
    await _create_user("alice@example.com", "ValidPassword1!")
    token = await _login(client, "alice@example.com", "ValidPassword1!")
    assert isinstance(token, str)
    assert len(token) > 20


@pytest.mark.asyncio
async def test_login_with_wrong_password_is_rejected(client):
    await _create_user("alice@example.com", "RightPassword1!")
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": "alice@example.com", "password": "WrongPassword!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_me_returns_authenticated_user(client):
    user = await _create_user("alice@example.com", "ValidPassword1!")
    token = await _login(client, "alice@example.com", "ValidPassword1!")

    res = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "alice@example.com"
    assert body["id"] == str(user.id)


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client):
    res = await client.get("/api/v1/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_password_change_clears_first_login_flag(client):
    await _create_user("alice@example.com", "TempPasswordABC1!", password_reset_required=True)
    token = await _login(client, "alice@example.com", "TempPasswordABC1!")

    # Before reset: flag is True
    me_before = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me_before.json()["password_reset_required"] is True

    # Reset
    res = await client.post(
        "/api/v1/me/password",
        json={"current_password": "TempPasswordABC1!", "new_password": "NewPassword123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["password_reset_required"] is False

    # After reset: flag cleared
    me_after = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.json()["password_reset_required"] is False

    # New password works
    new_token = await _login(client, "alice@example.com", "NewPassword123!")
    assert new_token


@pytest.mark.asyncio
async def test_password_change_rejects_wrong_current_password(client):
    await _create_user("alice@example.com", "TempPasswordABC1!")
    token = await _login(client, "alice@example.com", "TempPasswordABC1!")

    res = await client.post(
        "/api/v1/me/password",
        json={"current_password": "WrongOldPassword1!", "new_password": "NewPassword123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "current password" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_password_change_rejects_reuse(client):
    await _create_user("alice@example.com", "SameSamePassword1!")
    token = await _login(client, "alice@example.com", "SameSamePassword1!")

    res = await client.post(
        "/api/v1/me/password",
        json={"current_password": "SameSamePassword1!", "new_password": "SameSamePassword1!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "differ" in res.json()["detail"].lower()
