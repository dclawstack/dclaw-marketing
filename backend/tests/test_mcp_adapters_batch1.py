"""Phase 6.x — MCP adapter tests for HubSpot, GA4, Stripe."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection, ConnectionStatus
from app.models.organization import Organization
from app.services.mcp import ga4 as ga4_mcp
from app.services.mcp import hubspot as hubspot_mcp
from app.services.mcp import stripe as stripe_mcp
from app.services.mcp_client import MCPInvocationError
from tests.conftest import test_engine


@pytest_asyncio.fixture
async def org_with_connections():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="mcp", name="MCP Co")
        session.add(org)
        await session.flush()
        for sid in ("hubspot", "ga4", "stripe"):
            session.add(
                Connection(
                    organization_id=org.id,
                    server_id=sid,
                    name=sid,
                    status=ConnectionStatus.active,
                    metadata_json={},  # no endpoint → stub fallback
                )
            )
        await session.commit()
        await session.refresh(org)
        return org


@pytest.mark.asyncio
async def test_hubspot_search_contacts_stub(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await hubspot_mcp.search_contacts(
            session, organization_id=org.id, email="alice@example.com", limit=5
        )
    assert res.server == "hubspot"
    assert res.tool == "search_contacts"
    assert res.arguments == {"email": "alice@example.com", "limit": 5}
    assert res.stub is True


@pytest.mark.asyncio
async def test_hubspot_create_deal_passes_optional_fields(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await hubspot_mcp.create_deal(
            session,
            organization_id=org.id,
            contact_id="c_123",
            name="Acme Q3",
            amount=12500.0,
            stage="proposal",
            pipeline="default",
        )
    assert res.arguments["contact_id"] == "c_123"
    assert res.arguments["amount"] == 12500.0
    assert res.arguments["stage"] == "proposal"
    assert res.arguments["pipeline"] == "default"


@pytest.mark.asyncio
async def test_hubspot_missing_connection_raises():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="hsmiss", name="HSMiss")
        session.add(org)
        await session.commit()
        await session.refresh(org)
        with pytest.raises(MCPInvocationError):
            await hubspot_mcp.search_contacts(
                session,
                organization_id=org.id,
                email="x@y.com",
            )


@pytest.mark.asyncio
async def test_ga4_get_metrics_stub(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await ga4_mcp.get_metrics(
            session,
            organization_id=org.id,
            metrics=["sessions", "totalUsers"],
            start_date="2026-04-01",
            end_date="2026-04-30",
            dimensions=["sessionSource"],
            property_id="properties/123456789",
        )
    assert res.server == "ga4"
    assert res.tool == "get_metrics"
    assert res.arguments["metrics"] == ["sessions", "totalUsers"]
    assert res.arguments["dimensions"] == ["sessionSource"]
    assert res.arguments["property_id"] == "properties/123456789"
    assert res.stub is True


@pytest.mark.asyncio
async def test_ga4_list_top_pages_clamps_limit_int(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await ga4_mcp.list_top_pages(
            session,
            organization_id=org.id,
            start_date="2026-04-01",
            end_date="2026-04-30",
            limit=50,
        )
    assert res.arguments["limit"] == 50


@pytest.mark.asyncio
async def test_stripe_list_charges_optional_filters(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await stripe_mcp.list_charges(
            session,
            organization_id=org.id,
            customer="cus_123",
            limit=20,
            created_gte=1700000000,
        )
    assert res.arguments["customer"] == "cus_123"
    assert res.arguments["limit"] == 20
    assert res.arguments["created_gte"] == 1700000000


@pytest.mark.asyncio
async def test_stripe_get_customer_requires_email_or_id(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        with pytest.raises(MCPInvocationError):
            await stripe_mcp.get_customer(session, organization_id=org.id)
        ok = await stripe_mcp.get_customer(
            session, organization_id=org.id, email="a@b.com"
        )
        assert ok.arguments == {"email": "a@b.com"}


@pytest.mark.asyncio
async def test_stripe_create_refund_partial(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await stripe_mcp.create_refund(
            session,
            organization_id=org.id,
            charge_id="ch_x",
            amount=500,
            reason="requested_by_customer",
        )
    assert res.arguments == {
        "charge_id": "ch_x",
        "amount": 500,
        "reason": "requested_by_customer",
    }
