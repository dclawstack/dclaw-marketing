"""Phase 6.x batch 4 — MCP adapter tests for Salesforce, Mixpanel, PostHog."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection, ConnectionStatus
from app.models.organization import Organization
from app.services.mcp import mixpanel as mixpanel_mcp
from app.services.mcp import posthog as posthog_mcp
from app.services.mcp import salesforce as salesforce_mcp
from app.services.mcp_client import MCPInvocationError
from tests.conftest import test_engine


@pytest_asyncio.fixture
async def org_with_connections():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="mcp4", name="MCP4 Co")
        session.add(org)
        await session.flush()
        for sid in ("salesforce", "mixpanel", "posthog"):
            session.add(
                Connection(
                    organization_id=org.id,
                    server_id=sid,
                    name=sid,
                    status=ConnectionStatus.active,
                    auth_kind="oauth2",
                    metadata_json={},
                )
            )
        await session.commit()
        await session.refresh(org)
        return org


# ---------- Salesforce ------------------------------------------------------


@pytest.mark.asyncio
async def test_salesforce_create_lead_passes_payload(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await salesforce_mcp.create_lead(
            session,
            organization_id=org.id,
            email="ada@example.com",
            first_name="Ada",
            last_name="Lovelace",
            company="Babbage Inc",
        )
    assert res.server == "salesforce"
    assert res.tool == "create_lead"
    payload = res.arguments["payload"]
    assert payload["Email"] == "ada@example.com"
    assert payload["FirstName"] == "Ada"
    assert payload["Company"] == "Babbage Inc"


@pytest.mark.asyncio
async def test_salesforce_find_lead(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await salesforce_mcp.find_lead(
            session, organization_id=org.id, email="x@y.com"
        )
    assert res.arguments == {"email": "x@y.com"}


@pytest.mark.asyncio
async def test_salesforce_missing_connection_raises():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="no-sf", name="No Salesforce")
        session.add(org)
        await session.commit()
        await session.refresh(org)
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        with pytest.raises(MCPInvocationError):
            await salesforce_mcp.find_lead(
                session, organization_id=org.id, email="x@y.com"
            )


# ---------- Mixpanel --------------------------------------------------------


@pytest.mark.asyncio
async def test_mixpanel_query_segmentation_optional_on(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await mixpanel_mcp.query_segmentation(
            session,
            organization_id=org.id,
            event="signup",
            from_date="2026-01-01",
            to_date="2026-01-31",
            on="utm_source",
        )
    assert res.arguments["on"] == "utm_source"
    assert res.arguments["event"] == "signup"


@pytest.mark.asyncio
async def test_mixpanel_track_event_default_props(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await mixpanel_mcp.track_event(
            session, organization_id=org.id, event="page_view"
        )
    assert res.arguments == {"event": "page_view", "properties": {}}


# ---------- PostHog ---------------------------------------------------------


@pytest.mark.asyncio
async def test_posthog_capture(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await posthog_mcp.capture(
            session,
            organization_id=org.id,
            event="$pageview",
            distinct_id="user_1",
            properties={"path": "/pricing"},
        )
    assert res.arguments == {
        "event": "$pageview",
        "distinct_id": "user_1",
        "properties": {"path": "/pricing"},
    }


@pytest.mark.asyncio
async def test_posthog_list_feature_flags(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await posthog_mcp.list_feature_flags(
            session, organization_id=org.id
        )
    assert res.tool == "list_feature_flags"
    assert res.arguments == {}
