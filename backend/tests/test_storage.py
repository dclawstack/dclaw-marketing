"""Storage service unit tests + assets API integration tests.

The actual S3/MinIO calls are monkey-patched out — these tests verify
our wrapping logic (key shape, route behavior, auth) without needing
a real S3-compatible service running.
"""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetKind, AssetStatus
from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services import storage
from tests.conftest import test_engine


_helper = PasswordHelper()


# ---------- shared fixtures / helpers ----------------------------------

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
    assert res.status_code == 200
    return res.json()["access_token"]


# ---------- storage.make_storage_key ------------------------------------

def test_make_storage_key_with_org():
    key = storage.make_storage_key(
        organization_id="00000000-0000-0000-0000-000000000001",
        kind="image",
        extension="png",
    )
    assert key.startswith("orgs/00000000-0000-0000-0000-000000000001/image/")
    assert key.endswith(".png")


def test_make_storage_key_without_org_uses_global_prefix():
    key = storage.make_storage_key(organization_id=None, kind="document", extension="pdf")
    assert key.startswith("orgs/_global/document/")
    assert key.endswith(".pdf")


def test_make_storage_key_handles_dotted_extension():
    key = storage.make_storage_key(
        organization_id=None, kind="image", extension=".jpg"
    )
    assert key.endswith(".jpg")


def test_make_storage_key_falls_back_to_bin():
    key = storage.make_storage_key(organization_id=None, kind="other", extension="")
    assert key.endswith(".bin")


def test_make_storage_key_uuids_are_distinct():
    """Two calls with identical inputs produce different keys (UUID inside)."""
    a = storage.make_storage_key(None, "image", "png")
    b = storage.make_storage_key(None, "image", "png")
    assert a != b


# ---------- presigned URL routing (mocked) -----------------------------

@pytest.mark.asyncio
async def test_request_upload_returns_presigned_url(client, monkeypatch):
    user = await _seed_user("alice@example.com", "AlicePwd123!")

    async def _fake_put_url(key, content_type="application/octet-stream", **kw):
        return f"https://fake-s3/{key}?signed=yes"

    monkeypatch.setattr(storage, "presigned_put_url", _fake_put_url)

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.post(
        "/api/v1/assets/upload",
        json={
            "filename": "logo.png",
            "mime_type": "image/png",
            "kind": "image",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["asset"]["status"] == "uploading"
    assert body["asset"]["mime_type"] == "image/png"
    assert body["asset"]["original_filename"] == "logo.png"
    assert body["presigned_put_url"].startswith("https://fake-s3/")
    assert "signed=yes" in body["presigned_put_url"]


@pytest.mark.asyncio
async def test_request_upload_rejects_non_member_for_org(client, monkeypatch):
    # Bob has no membership in Alice's Org
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")
    org = await _seed_org_with(alice, OrganizationRole.admin)

    async def _fake_put_url(*a, **kw):
        return "https://fake-s3/never"

    monkeypatch.setattr(storage, "presigned_put_url", _fake_put_url)
    token = await _login(client, "bob@example.com", "BobPwd123456!")

    res = await client.post(
        "/api/v1/assets/upload",
        json={
            "filename": "evil.png",
            "mime_type": "image/png",
            "kind": "image",
            "organization_id": str(org.id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_confirm_marks_asset_ready(client, monkeypatch):
    user = await _seed_user("alice@example.com", "AlicePwd123!")

    async def _fake_put_url(*a, **kw): return "https://fake-s3/x"
    async def _fake_head(key, **kw):
        return {"size": 12345, "etag": "abc123def456", "content_type": "image/png"}

    monkeypatch.setattr(storage, "presigned_put_url", _fake_put_url)
    monkeypatch.setattr(storage, "head_object", _fake_head)

    token = await _login(client, "alice@example.com", "AlicePwd123!")

    # Step 1: request upload
    r1 = await client.post(
        "/api/v1/assets/upload",
        json={"filename": "x.png", "mime_type": "image/png", "kind": "image"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201
    asset_id = r1.json()["asset"]["id"]

    # Step 2 (simulated): client uploads bytes to presigned URL — skipped
    # Step 3: confirm
    r2 = await client.post(
        f"/api/v1/assets/{asset_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["status"] == "ready"
    assert body["size_bytes"] == 12345
    assert body["sha256"] == "abc123def456"


@pytest.mark.asyncio
async def test_confirm_fails_when_object_missing(client, monkeypatch):
    user = await _seed_user("alice@example.com", "AlicePwd123!")

    async def _fake_put_url(*a, **kw): return "https://fake-s3/x"
    async def _fake_head(key, **kw): return None  # not found

    monkeypatch.setattr(storage, "presigned_put_url", _fake_put_url)
    monkeypatch.setattr(storage, "head_object", _fake_head)

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    r1 = await client.post(
        "/api/v1/assets/upload",
        json={"filename": "x.png", "mime_type": "image/png", "kind": "image"},
        headers={"Authorization": f"Bearer {token}"},
    )
    asset_id = r1.json()["asset"]["id"]

    r2 = await client.post(
        f"/api/v1/assets/{asset_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_download_url_requires_ready_status(client, monkeypatch):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        asset = Asset(
            created_by_user_id=user.id,
            kind=AssetKind.image,
            mime_type="image/png",
            bucket="b", storage_key="orgs/_global/image/abc.png",
            status=AssetStatus.uploading,
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)

    async def _fake_get(*a, **kw): return "https://fake-s3/get"
    monkeypatch.setattr(storage, "presigned_get_url", _fake_get)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    res = await client.get(
        f"/api/v1/assets/{asset.id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409  # not ready


@pytest.mark.asyncio
async def test_download_url_returns_presigned_get(client, monkeypatch):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        asset = Asset(
            created_by_user_id=user.id,
            kind=AssetKind.image,
            mime_type="image/png",
            bucket="b", storage_key="orgs/_global/image/abc.png",
            status=AssetStatus.ready,
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)

    async def _fake_get(*a, **kw): return "https://fake-s3/dl?token=xyz"
    monkeypatch.setattr(storage, "presigned_get_url", _fake_get)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    res = await client.get(
        f"/api/v1/assets/{asset.id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["presigned_get_url"] == "https://fake-s3/dl?token=xyz"


@pytest.mark.asyncio
async def test_list_assets_scoped_to_user(client):
    alice = await _seed_user("alice@example.com", "AlicePwd123!")
    bob = await _seed_user("bob@example.com", "BobPwd123456!")
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        session.add(Asset(
            created_by_user_id=alice.id, kind=AssetKind.image,
            mime_type="image/png", bucket="b", storage_key="alice/1",
            status=AssetStatus.ready,
        ))
        session.add(Asset(
            created_by_user_id=bob.id, kind=AssetKind.image,
            mime_type="image/png", bucket="b", storage_key="bob/1",
            status=AssetStatus.ready,
        ))
        await session.commit()

    token = await _login(client, "alice@example.com", "AlicePwd123!")
    res = await client.get("/api/v1/assets", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    keys = [a["storage_key"] for a in res.json()]
    assert "alice/1" in keys
    assert "bob/1" not in keys


@pytest.mark.asyncio
async def test_delete_marks_asset_deleted(client, monkeypatch):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        asset = Asset(
            created_by_user_id=user.id, kind=AssetKind.image,
            mime_type="image/png", bucket="b", storage_key="orgs/_global/image/x",
            status=AssetStatus.ready,
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
        asset_id = asset.id

    async def _fake_delete(*a, **kw): return None
    monkeypatch.setattr(storage, "delete_object", _fake_delete)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    res = await client.delete(
        f"/api/v1/assets/{asset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        refreshed = await session.get(Asset, asset_id)
        assert refreshed.status == AssetStatus.deleted
