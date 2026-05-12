"""Phase 6.x — MCP adapter tests for Ahrefs, Webflow, WordPress, Ghost."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection, ConnectionStatus
from app.models.organization import Organization
from app.services.mcp import ahrefs as ahrefs_mcp
from app.services.mcp import ghost as ghost_mcp
from app.services.mcp import webflow as webflow_mcp
from app.services.mcp import wordpress as wp_mcp
from app.services.mcp_client import MCPInvocationError
from tests.conftest import test_engine


@pytest_asyncio.fixture
async def org_with_connections():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="mcp2", name="MCP2 Co")
        session.add(org)
        await session.flush()
        for sid in ("ahrefs", "webflow", "wordpress", "ghost"):
            session.add(
                Connection(
                    organization_id=org.id,
                    server_id=sid,
                    name=sid,
                    status=ConnectionStatus.active,
                    metadata_json={},
                )
            )
        await session.commit()
        await session.refresh(org)
        return org


@pytest.mark.asyncio
async def test_ahrefs_keyword_difficulty(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await ahrefs_mcp.keyword_difficulty(
            session,
            organization_id=org.id,
            keywords=["claude code", "agentic ai"],
            country="us",
        )
    assert res.server == "ahrefs"
    assert res.tool == "keyword_difficulty"
    assert res.arguments["keywords"] == ["claude code", "agentic ai"]


@pytest.mark.asyncio
async def test_ahrefs_serp_overview(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await ahrefs_mcp.serp_overview(
            session, organization_id=org.id, keyword="dclaw", limit=10
        )
    assert res.arguments == {"keyword": "dclaw", "country": "us", "limit": 10}


@pytest.mark.asyncio
async def test_webflow_create_blog_post_optional_slug(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await webflow_mcp.create_blog_post(
            session,
            organization_id=org.id,
            site_id="site_1",
            collection_id="col_1",
            title="Launch",
            body_html="<p>Hi</p>",
            slug="launch",
            publish=True,
        )
    assert res.arguments["slug"] == "launch"
    assert res.arguments["publish"] is True


@pytest.mark.asyncio
async def test_webflow_publish_site_optional_domains(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await webflow_mcp.publish_site(
            session,
            organization_id=org.id,
            site_id="site_1",
            domain_ids=["d1", "d2"],
        )
    assert res.arguments["domain_ids"] == ["d1", "d2"]


@pytest.mark.asyncio
async def test_wordpress_create_post_passes_optional_fields(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await wp_mcp.create_post(
            session,
            organization_id=org.id,
            title="t",
            content="c",
            status="publish",
            slug="t",
            categories=[1, 2],
            tags=[3],
        )
    assert res.arguments["status"] == "publish"
    assert res.arguments["categories"] == [1, 2]
    assert res.arguments["tags"] == [3]


@pytest.mark.asyncio
async def test_wordpress_update_post_kwargs_pass_through(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await wp_mcp.update_post(
            session, organization_id=org.id, post_id=42, title="new"
        )
    assert res.arguments == {"post_id": 42, "title": "new"}


@pytest.mark.asyncio
async def test_ghost_create_post_minimal(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await ghost_mcp.create_post(
            session, organization_id=org.id, title="t", html="<p>hi</p>"
        )
    assert res.arguments["status"] == "draft"


@pytest.mark.asyncio
async def test_ghost_publish_post_send_email_flag(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await ghost_mcp.publish_post(
            session,
            organization_id=org.id,
            post_id="p_123",
            send_email=True,
        )
    assert res.arguments == {"post_id": "p_123", "send_email": True}


@pytest.mark.asyncio
async def test_missing_connection_raises_per_server():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="mcp2miss", name="X")
        session.add(org)
        await session.commit()
        await session.refresh(org)
        with pytest.raises(MCPInvocationError):
            await ahrefs_mcp.site_audit(
                session, organization_id=org.id, domain="x.co"
            )
