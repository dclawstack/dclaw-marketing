"""Phase 11.4 — GDPR export HTTP endpoint tests.

(The Celery task itself is exercised in ``test_gdpr_export.py``.)
"""

from __future__ import annotations

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.ops import DataExportRequest, DataExportStatus
from app.models.user import User
from tests.conftest import test_engine


_helper = PasswordHelper()


async def _seed_user(email: str, password: str, *, is_superuser: bool = False) -> User:
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


async def _seed_org_with(user: User, role: OrganizationRole) -> Organization:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="exp" + str(user.id)[:4], name="Exp")
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
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_can_request_export(client, monkeypatch):
    """The endpoint creates a DataExportRequest row and queues the
    Celery task. We stub out the ``.delay()`` call so the test doesn't
    need a worker."""
    alice = await _seed_user("a@x.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.admin)
    token = await _login(client, "a@x.com", "AlicePwd123!")

    called_with = {}

    class _Fake:
        def delay(self, org_id, *, request_id):
            called_with["org_id"] = org_id
            called_with["request_id"] = request_id

    from app.worker.tasks import gdpr as gdpr_task

    monkeypatch.setattr(
        gdpr_task, "export_organization_data", _Fake(), raising=False
    )

    res = await client.post(
        f"/api/v1/orgs/{org.id}/gdpr-export",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 202, res.text
    body = res.json()
    assert body["organization_id"] == str(org.id)
    assert body["status"] == "queued"
    assert called_with["org_id"] == str(org.id)
    assert called_with["request_id"] == body["id"]


@pytest.mark.asyncio
async def test_manager_cannot_request_export(client):
    alice = await _seed_user("a@x.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.manager)
    token = await _login(client, "a@x.com", "AlicePwd123!")
    res = await client.post(
        f"/api/v1/orgs/{org.id}/gdpr-export",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_status_returns_download_url_when_ready(client, monkeypatch):
    alice = await _seed_user("a@x.com", "AlicePwd123!")
    org = await _seed_org_with(alice, OrganizationRole.admin)
    token = await _login(client, "a@x.com", "AlicePwd123!")

    from datetime import datetime, timedelta, timezone

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        req = DataExportRequest(
            organization_id=org.id,
            requested_by_user_id=alice.id,
            scope="full",
            status=DataExportStatus.ready,
            storage_key="gdpr-exports/test/req.json",
            expires_at=datetime.now(tz=timezone.utc) + timedelta(days=7),
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)

    from app.api.v1 import gdpr as gdpr_route

    async def _fake_presigned(key, *, expires_in):
        return f"https://stub.example/{key}?expires={expires_in}"

    monkeypatch.setattr(
        gdpr_route, "presigned_get_url", _fake_presigned, raising=False
    )

    res = await client.get(
        f"/api/v1/orgs/{org.id}/gdpr-exports/{req.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "ready"
    assert body["download_url"] == (
        "https://stub.example/gdpr-exports/test/req.json?expires=86400"
    )


@pytest.mark.asyncio
async def test_status_404_for_wrong_org(client):
    alice = await _seed_user("a@x.com", "AlicePwd123!")
    bob = await _seed_user("b@x.com", "BobPwd123456!")
    org_a = await _seed_org_with(alice, OrganizationRole.admin)
    org_b = await _seed_org_with(bob, OrganizationRole.admin)

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        req = DataExportRequest(
            organization_id=org_a.id,
            requested_by_user_id=alice.id,
            scope="full",
            status=DataExportStatus.queued,
        )
        session.add(req)
        await session.commit()
        await session.refresh(req)

    token_b = await _login(client, "b@x.com", "BobPwd123456!")
    res = await client.get(
        f"/api/v1/orgs/{org_b.id}/gdpr-exports/{req.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404
