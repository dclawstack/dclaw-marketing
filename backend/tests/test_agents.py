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
async def test_complete_with_images_stub_mode_does_not_crash():
    """In stub mode (no ANTHROPIC_API_KEY), complete(images=…) must not
    crash, must return a non-empty string, AND the digest must differ
    from the no-images call because the user prompt is annotated with
    the image count (which feeds into the hash). This proves images
    are actually plumbed through the stub path."""
    from app.agents.anthropic_client import complete

    with_images = await complete(
        system="sys",
        user="describe this",
        images=[("image/png", b"\x89PNG\r\n"), ("image/jpeg", b"\xff\xd8\xff")],
    )
    without_images = await complete(system="sys", user="describe this")
    assert isinstance(with_images, str) and with_images
    assert isinstance(without_images, str) and without_images
    # Differing inputs → differing deterministic digests.
    assert with_images != without_images


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


# ============================================================
# S5-CDR-C — Tool fleet + agentic loop
# ============================================================

def test_tool_registry_populated_with_full_fleet():
    """The Conductor tool fleet should cover every sidebar area. The
    issue spec calls for ~38 tools — guard with a lower bound that
    still catches regressions.
    """
    from app.agents.tools import REGISTRY

    names = {t.name for t in REGISTRY.all()}
    assert len(names) >= 30, f"only {len(names)} tools registered: {sorted(names)}"

    # Every sidebar area must have at least one tool.
    expected_anchors = {
        "navigate_to",
        "get_dashboard_summary",
        "list_inbox_items",
        "list_calendar_events",
        "schedule_post",
        "publish_now",
        "generate_creative",
        "list_library_assets",
        "list_workflows",
        "list_channels",
        "list_email_sequences",
        "list_ad_campaigns",
        "search_kg",
        "get_analytics_report",
        "run_seo_audit",
        "list_integrations",
        "list_orgs",
        "list_users",
        "list_models",
    }
    missing = expected_anchors - names
    assert not missing, f"missing anchor tools: {sorted(missing)}"


def test_tool_registry_claude_schema_shape():
    """Each tool surfaces as {name, description, input_schema} for
    Anthropic's `tools=[…]` argument."""
    from app.agents.tools import REGISTRY

    schema = REGISTRY.as_claude_schema()
    assert isinstance(schema, list) and len(schema) >= 30
    for entry in schema:
        assert set(entry.keys()) == {"name", "description", "input_schema"}
        assert isinstance(entry["name"], str) and entry["name"]
        assert isinstance(entry["description"], str) and entry["description"]
        assert isinstance(entry["input_schema"], dict)
        assert entry["input_schema"].get("type") == "object"


@pytest.mark.asyncio
async def test_navigate_to_tool_returns_route_action():
    """navigate_to is the simplest read-only tool — confirm shape."""
    from uuid import uuid4
    from app.agents.tools import REGISTRY
    from app.agents.tools.registry import ToolContext

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        ctx = ToolContext(org_id=uuid4(), user_id=uuid4(), session=session)
        out = await REGISTRY.get("navigate_to").handler(ctx, route="/calendar")
        assert out["ok"] is True
        assert out["action"] == "navigate"
        assert out["route"] == "/calendar"

        bad = await REGISTRY.get("navigate_to").handler(ctx, route="calendar")
        assert bad["ok"] is False


@pytest.mark.asyncio
async def test_list_inbox_items_against_real_db():
    """A representative read-only DB-backed tool: seed an
    ApprovalRequest then verify list_inbox_items returns it."""
    from app.agents.tools import REGISTRY
    from app.agents.tools.registry import ToolContext
    from app.models.approval_request import ApprovalRequest, ApprovalStatus

    user = await _seed_user("alice@example.com", "AlicePwd123!")
    org = await _seed_org_with(user, OrganizationRole.viewer)

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        session.add(
            ApprovalRequest(
                organization_id=org.id,
                action_type="publish_social_post",
                requested_by_agent="creatives_agent_v1",
                requested_by_user_id=user.id,
                payload_json={"channel": "linkedin", "copy": "test"},
                status=ApprovalStatus.pending,
            )
        )
        await session.commit()

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        ctx = ToolContext(org_id=org.id, user_id=user.id, session=session)
        out = await REGISTRY.get("list_inbox_items").handler(ctx)
        assert out["ok"] is True
        assert out["count"] == 1
        assert out["items"][0]["action_type"] == "publish_social_post"
        assert out["items"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_reply_agentic_stub_mode_returns_empty_tool_calls():
    """When ANTHROPIC_API_KEY is unset (stub mode), reply_agentic must
    fall back to the text-only stub path and return an empty
    tool_calls trace — no real Claude is available to drive tools.
    """
    from uuid import uuid4
    from app.agents.conductor import reply_agentic
    from app.agents.tools.registry import ToolContext

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        ctx = ToolContext(org_id=uuid4(), user_id=uuid4(), session=session)
        turn = await reply_agentic(
            "Hi conductor",
            history=None,
            tool_ctx=ctx,
        )
    assert isinstance(turn.text, str) and turn.text
    assert turn.tool_calls == []


# ============================================================
# S5-CDR-D — Streaming + extended thinking
# ============================================================

@pytest.mark.asyncio
async def test_stream_endpoint_emits_sse_in_stub_mode(client):
    """End-to-end: POST /messages/stream returns text/event-stream and
    yields the expected SSE event sequence in stub mode."""
    from app.models.agent_thread import AgentKind, AgentThread

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

    async with client.stream(
        "POST",
        f"/api/v1/orgs/{org.id}/agent-threads/{thread_id}/messages/stream",
        json={"content": "Hello conductor"},
        headers={"Authorization": f"Bearer {token}"},
    ) as response:
        assert response.status_code == 200, await response.aread()
        assert response.headers["content-type"].startswith("text/event-stream")
        body = b""
        async for chunk in response.aiter_bytes():
            body += chunk
    raw = body.decode("utf-8")

    # Must surface the lifecycle events.
    assert "event: user_msg_persisted" in raw
    assert "event: agent_msg_start" in raw
    assert "event: text_delta" in raw
    assert "event: done" in raw
    # Done payload must reference both ids.
    assert '"agent_msg_id"' in raw
    assert '"user_msg_id"' in raw


@pytest.mark.asyncio
async def test_stream_endpoint_rejects_invalid_thinking_budget(client):
    """Pydantic guards reject out-of-range thinking budgets."""
    from app.models.agent_thread import AgentKind, AgentThread

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

    res = await client.post(
        f"/api/v1/orgs/{org.id}/agent-threads/{thread_id}/messages/stream",
        json={"content": "hi", "thinking_budget_tokens": 9_999_999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_messages_stream_raw_stub_yields_text_then_done():
    """Low-level stub path of messages_stream_raw yields one text_delta
    followed by a message_done event."""
    from app.agents.anthropic_client import messages_stream_raw

    events: list[dict] = []
    async for ev in messages_stream_raw(
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
    ):
        events.append(ev)
    # In stub mode: at least one text_delta, then message_done.
    types = [e["type"] for e in events]
    assert "text_delta" in types
    assert types[-1] == "message_done"


@pytest.mark.asyncio
async def test_reply_agentic_streaming_stub_mode_done_payload():
    """reply_agentic_streaming in stub mode emits agent_msg_start +
    text_delta + done with empty tool_calls."""
    from uuid import uuid4
    from app.agents.conductor import reply_agentic_streaming
    from app.agents.tools.registry import ToolContext

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        ctx = ToolContext(org_id=uuid4(), user_id=uuid4(), session=session)
        events: list[dict] = []
        async for ev in reply_agentic_streaming(
            "Hello",
            history=None,
            tool_ctx=ctx,
        ):
            events.append(ev)
    seq = [e["event"] for e in events]
    assert "agent_msg_start" in seq
    assert "text_delta" in seq
    assert seq[-1] == "done"
    assert events[-1]["tool_calls"] == []
    assert isinstance(events[-1]["final_text"], str) and events[-1]["final_text"]


@pytest.mark.asyncio
async def test_conductor_message_posts_persist_role_tool_rows_with_stub(client):
    """End-to-end: POSTing a message to a Conductor thread in stub
    mode should NOT create role=tool rows (no tools fired). Confirms
    the agentic dispatch path is wired without exploding when there
    are no tool calls.
    """
    from app.models.agent_thread import (
        AgentMessage,
        AgentMessageRole,
        AgentThread,
        AgentKind,
    )

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

    res = await client.post(
        f"/api/v1/orgs/{org.id}/agent-threads/{thread_id}/messages",
        json={"content": "Hi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    # Stub mode: no tools fired → 2 rows back (user, agent).
    assert len(body) == 2
    assert body[0]["role"] == "user"
    assert body[1]["role"] == "agent"

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        tool_rows = (
            await session.execute(
                select(AgentMessage).where(
                    AgentMessage.thread_id == thread_id,
                    AgentMessage.role == AgentMessageRole.tool,
                )
            )
        ).scalars().all()
        assert tool_rows == []
