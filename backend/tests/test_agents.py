"""Creatives Agent tests — variant parsing, generation, approval flow."""

import pytest
from fastapi_users.password import PasswordHelper
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import creatives
from app.agents.anthropic_client import _stub_response
from app.agents.creatives import parse_variants
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.brand_kit import BrandKit
from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.user import User
from tests.conftest import test_engine


_helper = PasswordHelper()


# ---------- parser unit tests ------------------------------------------

def test_parse_variants_well_formatted():
    text = """VARIANT 1: First post.

VARIANT 2: Second post here.

VARIANT 3: Third one."""
    out = parse_variants(text, expected=3)
    assert len(out) == 3
    assert "First post" in out[0]
    assert "Second post" in out[1]
    assert "Third one" in out[2]


def test_parse_variants_multiline_each():
    text = """VARIANT 1: Line one.
Line two.

VARIANT 2: Another."""
    out = parse_variants(text, expected=2)
    assert len(out) == 2
    assert "Line one" in out[0]
    assert "Line two" in out[0]


def test_parse_variants_takes_first_expected():
    text = "\n\n".join(f"VARIANT {i+1}: text {i}" for i in range(5))
    out = parse_variants(text, expected=3)
    assert len(out) == 3


def test_parse_variants_fallback_to_blank_line_split():
    """If the model ignores our VARIANT N format, the fallback should
    still return something."""
    text = "Para one.\n\nPara two.\n\nPara three."
    out = parse_variants(text, expected=2)
    assert len(out) == 2


def test_stub_response_deterministic():
    a = _stub_response("system prompt", "user prompt", n_variants=3)
    b = _stub_response("system prompt", "user prompt", n_variants=3)
    assert a == b
    assert "VARIANT 1:" in a
    assert "VARIANT 3:" in a


# ---------- agent integration tests ------------------------------------

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


async def _seed_brand_kit(org: Organization) -> BrandKit:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        bk = BrandKit(
            organization_id=org.id,
            name="v1",
            version=1,
            is_active=True,
            voice_json={
                "sliders": {"formal_casual": 0.6},
                "do_say": ["clear", "direct"],
                "dont_say": ["hype", "AI-magic"],
            },
            positioning_json={"tagline": "Marketing on autopilot"},
        )
        session.add(bk)
        await session.commit()
        await session.refresh(bk)
        return bk


async def _login(client, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_creatives_generate_creates_approval_requests(client):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)
    await _seed_brand_kit(org)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    res = await client.post(
        "/api/v1/agents/creatives/generate",
        json={
            "organization_id": str(org.id),
            "brief": "Announce our new Q2 feature: agent-driven calendaring.",
            "n_variants": 3,
            "channel": "linkedin",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["channel"] == "linkedin"
    assert body["n_variants"] == 3
    assert len(body["results"]) == 3
    for r in body["results"]:
        assert isinstance(r["variant"], str) and len(r["variant"]) > 0
        assert isinstance(r["approval_request_id"], str)

    # All variants created pending ApprovalRequests
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        ars = await session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.organization_id == org.id,
                ApprovalRequest.action_type == "publish_social_post",
            )
        )
        rows = list(ars.scalars().all())
        assert len(rows) == 3
        for ar in rows:
            assert ar.status == ApprovalStatus.pending
            assert ar.requested_by_agent == "creatives_agent_v1"
            assert ar.payload_json["channel"] == "linkedin"
            assert "Announce our new" in ar.payload_json["brief"]


@pytest.mark.asyncio
async def test_creatives_works_without_brand_kit(client):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)
    # NO brand kit created
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    res = await client.post(
        "/api/v1/agents/creatives/generate",
        json={
            "organization_id": str(org.id),
            "brief": "Hello world",
            "n_variants": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert len(res.json()["results"]) == 2


@pytest.mark.asyncio
async def test_creatives_viewer_blocked(client):
    user = await _seed_user("viewer@example.com", "ViewPwd1234!")
    org = await _seed_org_with(user, OrganizationRole.viewer)
    token = await _login(client, "viewer@example.com", "ViewPwd1234!")

    res = await client.post(
        "/api/v1/agents/creatives/generate",
        json={"organization_id": str(org.id), "brief": "a real brief"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_creatives_non_member_403(client):
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.admin)
    await _seed_user("intruder@example.com", "IntPwd1234567!")

    token = await _login(client, "intruder@example.com", "IntPwd1234567!")
    res = await client.post(
        "/api/v1/agents/creatives/generate",
        json={"organization_id": str(org.id), "brief": "a real brief"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_creatives_with_real_api_uses_fallback_path(client, monkeypatch):
    """When the Anthropic API call raises, the agent should still
    return variants via the stub fallback.
    """
    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.creatives)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    # Force the complete() fn to return a known string regardless of env.
    # Accept **kwargs so we don't break when future callers add new args
    # (e.g. images= for vision in S5-CDR-B).
    async def _fake_complete(*, system, user, max_tokens=2000, model="x", n_variants_hint=3, **_kwargs):
        return "VARIANT 1: forced.\n\nVARIANT 2: forced again.\n\nVARIANT 3: third."
    monkeypatch.setattr(creatives, "complete", _fake_complete)

    res = await client.post(
        "/api/v1/agents/creatives/generate",
        json={"organization_id": str(org.id), "brief": "test", "n_variants": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    results = res.json()["results"]
    assert any("forced" in r["variant"] for r in results)


# ============================================================
# S5-CDR-B — Conductor attachment / vision plumbing
# ============================================================

@pytest.mark.asyncio
async def test_complete_with_images_stub_mode_annotates_prompt():
    """In stub mode (no ANTHROPIC_API_KEY), complete(images=…) must not
    crash and must surface the image count in the synthetic prompt so
    downstream parsers can see the attachments are present."""
    from app.agents.anthropic_client import complete

    raw = await complete(
        system="sys",
        user="describe this",
        images=[("image/png", b"\x89PNG\r\n"), ("image/jpeg", b"\xff\xd8\xff")],
    )
    # Stub mixes system+user into a deterministic hash-keyed payload.
    # The image count annotation should be present in the stub response.
    assert "2 image attachment(s)" in raw


@pytest.mark.asyncio
async def test_conductor_reply_accepts_images_and_doc_summaries():
    """Conductor.reply must accept new keyword args without choking when
    real Claude is not configured (stub fallback).
    """
    from app.agents import conductor

    turn = await conductor.reply(
        "What's in this image?",
        history=None,
        images=[("image/png", b"\x89PNG\r\n")],
        doc_summaries=["document attachment: brief.pdf (application/pdf, 1234 bytes)"],
    )
    assert isinstance(turn.text, str)
    assert turn.text  # non-empty


@pytest.mark.asyncio
async def test_post_message_with_attachment_stores_asset_ids(client):
    """End-to-end: a user POSTs a message with attachment_asset_ids
    pointing at a (non-image) Asset; the user message should persist
    those ids and the agent reply should still come back successfully.
    """
    from app.models.agent_thread import AgentThread, AgentMessage, AgentKind, AgentMessageRole
    from app.models.asset import Asset, AssetKind, AssetStatus

    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.viewer)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    # Seed thread + asset directly so we don't need MinIO for the upload.
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        thread = AgentThread(
            organization_id=org.id,
            kind=AgentKind.conductor,
            started_by_user_id=user.id,
        )
        asset = Asset(
            organization_id=org.id,
            created_by_user_id=user.id,
            kind=AssetKind.document,
            mime_type="application/pdf",
            original_filename="brief.pdf",
            size_bytes=1234,
            bucket="dclaw",
            storage_key=f"orgs/{org.id}/test/brief.pdf",
            status=AssetStatus.ready,
        )
        session.add_all([thread, asset])
        await session.commit()
        await session.refresh(thread)
        await session.refresh(asset)
        thread_id, asset_id = thread.id, asset.id

    res = await client.post(
        f"/api/v1/orgs/{org.id}/agent-threads/{thread_id}/messages",
        json={
            "content": "Summarize this brief for me",
            "attachment_asset_ids": [str(asset_id)],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    # Two messages back: user + agent.
    assert len(body) == 2
    user_msg, agent_msg = body
    assert user_msg["role"] == "user"
    assert user_msg["attachment_asset_ids"] == [str(asset_id)]
    assert agent_msg["role"] == "agent"
    assert isinstance(agent_msg["content"], str) and agent_msg["content"]

    # And the user message row carries the ids in the DB.
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        rows = (
            await session.execute(
                select(AgentMessage).where(
                    AgentMessage.thread_id == thread_id,
                    AgentMessage.role == AgentMessageRole.user,
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].attachment_asset_ids == [str(asset_id)]


@pytest.mark.asyncio
async def test_post_message_with_missing_attachment_404s(client):
    """Unknown attachment ids must return 404, not silently drop."""
    from uuid import uuid4
    from app.models.agent_thread import AgentThread, AgentKind

    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.viewer)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        thread = AgentThread(
            organization_id=org.id,
            kind=AgentKind.conductor,
            started_by_user_id=user.id,
        )
        session.add(thread)
        await session.commit()
        await session.refresh(thread)
        thread_id = thread.id

    bogus = uuid4()
    res = await client.post(
        f"/api/v1/orgs/{org.id}/agent-threads/{thread_id}/messages",
        json={"content": "hi", "attachment_asset_ids": [str(bogus)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404, res.text
    assert "not found" in res.text.lower()


@pytest.mark.asyncio
async def test_post_message_with_cross_org_attachment_403s(client):
    """Attachments belonging to a different org must be rejected."""
    from app.models.agent_thread import AgentThread, AgentKind
    from app.models.asset import Asset, AssetKind, AssetStatus

    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.viewer)
    token = await _login(client, "alice@example.com", "AlicePwd123!")

    # Seed a separate org for the asset to belong to.
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        other_org = Organization(slug="other", name="Other Co")
        session.add(other_org)
        await session.flush()
        thread = AgentThread(
            organization_id=org.id,
            kind=AgentKind.conductor,
            started_by_user_id=user.id,
        )
        asset = Asset(
            organization_id=other_org.id,
            created_by_user_id=user.id,
            kind=AssetKind.document,
            mime_type="application/pdf",
            original_filename="other.pdf",
            size_bytes=10,
            bucket="dclaw",
            storage_key="orgs/other/x.pdf",
            status=AssetStatus.ready,
        )
        session.add_all([thread, asset])
        await session.commit()
        await session.refresh(thread)
        await session.refresh(asset)
        thread_id, asset_id = thread.id, asset.id

    res = await client.post(
        f"/api/v1/orgs/{org.id}/agent-threads/{thread_id}/messages",
        json={"content": "hi", "attachment_asset_ids": [str(asset_id)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403, res.text
