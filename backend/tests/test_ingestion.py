"""Q2 ingestion tests — service unit tests + route integration tests.

The Celery dispatch is monkey-patched so tests don't need a real
worker process. We verify the API contract; the actual ingest task
is unit-tested separately via test_ingest_service.
"""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetKind, AssetStatus
from app.models.ingestion import IngestionSource, IngestionStatus
from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services.ingestion import (
    UnsupportedMimeTypeError,
    chunk_text,
    estimate_tokens,
    extract_text,
)
from tests.conftest import test_engine


_helper = PasswordHelper()


# ---------- service-layer unit tests -----------------------------------

def test_extract_text_from_plain():
    out = extract_text(b"hello world", "text/plain")
    assert out == "hello world"


def test_extract_text_from_markdown():
    md = b"# Title\n\nSome **bold** content."
    out = extract_text(md, "text/markdown")
    assert "Title" in out
    assert "bold" in out


def test_extract_text_from_json():
    out = extract_text(b'{"hello": "world"}', "application/json")
    assert "hello" in out


def test_extract_text_rejects_unknown_mime():
    with pytest.raises(UnsupportedMimeTypeError):
        extract_text(b"data", "application/octet-stream")


def test_extract_text_handles_charset_in_mime():
    out = extract_text(b"hello", "text/plain; charset=utf-8")
    assert out == "hello"


def test_chunk_text_paragraph_aware():
    text = "Para one.\n\nPara two.\n\nPara three."
    chunks = chunk_text(text, max_chars=15)
    # Each paragraph is ~9 chars, ~2 should fit together but the third forces a new chunk
    assert len(chunks) >= 2
    assert all(len(c) <= 15 + 4 for c in chunks)  # +4 for separator


def test_chunk_text_hard_splits_long_paragraph():
    long_para = "x" * 5000
    chunks = chunk_text(long_para, max_chars=1000, overlap_chars=100)
    assert len(chunks) > 1
    # First chunk is exactly 1000 chars
    assert len(chunks[0]) == 1000


def test_chunk_text_empty_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_estimate_tokens_rough_ratio():
    assert estimate_tokens("hello world") == max(1, len("hello world") // 4)
    assert estimate_tokens("") == 1


# ---------- route integration tests -------------------------------------

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


async def _seed_asset(user: User, org: Organization) -> Asset:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        a = Asset(
            organization_id=org.id,
            created_by_user_id=user.id,
            kind=AssetKind.document,
            mime_type="text/plain",
            bucket="dclaw-marketing",
            storage_key=f"orgs/{org.id}/document/test.txt",
            status=AssetStatus.ready,
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a


async def _login(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_ingest_file_dispatches_and_returns_queued(client, monkeypatch):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)
    asset = await _seed_asset(user, org)

    # Patch Celery dispatch so we don't need a worker
    captured = {}
    class _FakeAsyncResult:
        id = "fake-celery-task-id"
    def _fake_delay(job_id, source_id):
        captured["job_id"] = job_id
        captured["source_id"] = source_id
        return _FakeAsyncResult()

    from app.worker.tasks import ingestion as ingestion_task
    monkeypatch.setattr(ingestion_task.ingest_asset, "delay", _fake_delay)

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        "/api/v1/ingest/files",
        json={
            "organization_id": str(org.id),
            "asset_id": str(asset.id),
            "name": "Test brief",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "queued"
    assert "source_id" in body
    assert "job_id" in body

    # Celery dispatch was invoked with the right IDs
    assert captured["source_id"] == body["source_id"]
    assert captured["job_id"] == body["job_id"]


@pytest.mark.asyncio
async def test_viewer_cannot_ingest(client, monkeypatch):
    user = await _seed_user("viewer@example.com", "ViewerPwd123!")
    org = await _seed_org_with(user, OrganizationRole.viewer)
    asset = await _seed_asset(user, org)

    from app.worker.tasks import ingestion as ingestion_task
    monkeypatch.setattr(ingestion_task.ingest_asset, "delay", lambda *a, **kw: None)

    token = await _login(client, "viewer@example.com", "ViewerPwd123!")
    res = await client.post(
        "/api/v1/ingest/files",
        json={"organization_id": str(org.id), "asset_id": str(asset.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_get_ingestion_status(client, monkeypatch):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)
    asset = await _seed_asset(user, org)

    from app.worker.tasks import ingestion as ingestion_task
    monkeypatch.setattr(ingestion_task.ingest_asset, "delay", lambda *a, **kw: type("R", (), {"id": "x"})())

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    create = await client.post(
        "/api/v1/ingest/files",
        json={"organization_id": str(org.id), "asset_id": str(asset.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    source_id = create.json()["source_id"]

    res = await client.get(
        f"/api/v1/ingest/{source_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "queued"
    assert res.json()["source_reference"] == str(asset.id)
