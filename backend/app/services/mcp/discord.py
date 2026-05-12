"""Discord MCP adapter — Phase 6.x.

Tools:

  • ``post_message(channel_id, content, tts=False)``
  • ``list_channels(guild_id)``
  • ``send_dm(user_id, content)``
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "discord"


async def _conn(session: AsyncSession, organization_id: UUID) -> Connection:
    res = await session.execute(
        select(Connection).where(
            Connection.organization_id == organization_id,
            Connection.server_id == _SERVER_ID,
        )
    )
    c = res.scalar_one_or_none()
    if c is None:
        raise MCPInvocationError(
            f"No Discord connection for organization {organization_id}."
        )
    return c


async def _call(
    session: AsyncSession, organization_id: UUID, tool: str, arguments: dict
) -> MCPAdapterResult:
    conn = await _conn(session, organization_id)
    inv = await invoke_tool(connection=conn, tool_name=tool, arguments=arguments)
    return MCPAdapterResult(
        server=_SERVER_ID,
        tool=tool,
        arguments=arguments,
        result=inv.result if isinstance(inv.result, dict) else {"value": inv.result},
        duration_ms=inv.duration_ms,
        stub=inv.stub,
    )


async def post_message(
    session: AsyncSession,
    *,
    organization_id: UUID,
    channel_id: str,
    content: str,
    tts: bool = False,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "post_message",
        {"channel_id": channel_id, "content": content, "tts": bool(tts)},
    )


async def list_channels(
    session: AsyncSession,
    *,
    organization_id: UUID,
    guild_id: str,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "list_channels",
        {"guild_id": guild_id},
    )


async def send_dm(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: str,
    content: str,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "send_dm",
        {"user_id": user_id, "content": content},
    )


__all__ = ["post_message", "list_channels", "send_dm"]
