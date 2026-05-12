"""Phase 6.x — MCP adapter tests for Slack, Discord, Notion, Google Drive."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection, ConnectionStatus
from app.models.organization import Organization
from app.services.mcp import discord as discord_mcp
from app.services.mcp import google_drive as drive_mcp
from app.services.mcp import notion as notion_mcp
from app.services.mcp import slack as slack_mcp
from app.services.mcp_client import MCPInvocationError
from tests.conftest import test_engine


@pytest_asyncio.fixture
async def org_with_connections():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="mcp3", name="MCP3 Co")
        session.add(org)
        await session.flush()
        for sid in ("slack", "discord", "notion", "google_drive"):
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
async def test_slack_post_message_optional_thread(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await slack_mcp.post_message(
            session,
            organization_id=org.id,
            channel="#general",
            text="hi",
            thread_ts="1700000000.123",
        )
    assert res.arguments["channel"] == "#general"
    assert res.arguments["thread_ts"] == "1700000000.123"


@pytest.mark.asyncio
async def test_slack_list_channels_defaults(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await slack_mcp.list_channels(session, organization_id=org.id)
    assert res.arguments == {"types": "public_channel", "limit": 100}


@pytest.mark.asyncio
async def test_discord_post_message(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await discord_mcp.post_message(
            session,
            organization_id=org.id,
            channel_id="111",
            content="ping",
        )
    assert res.arguments == {"channel_id": "111", "content": "ping", "tts": False}


@pytest.mark.asyncio
async def test_discord_send_dm(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await discord_mcp.send_dm(
            session, organization_id=org.id, user_id="u_1", content="hi"
        )
    assert res.arguments == {"user_id": "u_1", "content": "hi"}


@pytest.mark.asyncio
async def test_notion_search(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await notion_mcp.search(
            session, organization_id=org.id, query="brand guidelines"
        )
    assert res.arguments == {"query": "brand guidelines", "limit": 10}


@pytest.mark.asyncio
async def test_notion_create_page_passes_content_blocks(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await notion_mcp.create_page(
            session,
            organization_id=org.id,
            parent_id="p_root",
            title="Q3 plan",
            content_blocks=[
                {"type": "paragraph", "paragraph": {"rich_text": []}}
            ],
        )
    assert res.arguments["parent_id"] == "p_root"
    assert len(res.arguments["content_blocks"]) == 1


@pytest.mark.asyncio
async def test_drive_list_files_optional_filters(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await drive_mcp.list_files(
            session,
            organization_id=org.id,
            folder_id="folder_x",
            q="name contains 'brief'",
            page_size=50,
        )
    assert res.arguments["folder_id"] == "folder_x"
    assert res.arguments["q"] == "name contains 'brief'"
    assert res.arguments["page_size"] == 50


@pytest.mark.asyncio
async def test_drive_download_file(org_with_connections):
    org = org_with_connections
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        res = await drive_mcp.download_file(
            session, organization_id=org.id, file_id="f_123"
        )
    assert res.arguments == {"file_id": "f_123"}


@pytest.mark.asyncio
async def test_missing_notion_connection_raises():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="mcp3miss", name="X")
        session.add(org)
        await session.commit()
        await session.refresh(org)
        with pytest.raises(MCPInvocationError):
            await notion_mcp.search(
                session, organization_id=org.id, query="x"
            )
