"""Slack MCP adapter — Phase 6.x.

Tools:

  • ``post_message(channel, text, blocks=None, thread_ts=None)``
  • ``list_channels(types="public_channel", limit=100)``
  • ``send_dm(user_id, text)``

Stub fallback inherited.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "slack"


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
            f"No Slack connection for organization {organization_id}."
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
    channel: str,
    text: str,
    blocks: list[dict] | None = None,
    thread_ts: str | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {"channel": channel, "text": text}
    if blocks:
        args["blocks"] = blocks
    if thread_ts:
        args["thread_ts"] = thread_ts
    return await _call(session, organization_id, "post_message", args)


async def list_channels(
    session: AsyncSession,
    *,
    organization_id: UUID,
    types: str = "public_channel",
    limit: int = 100,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "list_channels",
        {"types": types, "limit": int(limit)},
    )


async def send_dm(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: str,
    text: str,
) -> MCPAdapterResult:
    return await _call(
        session, organization_id, "send_dm", {"user_id": user_id, "text": text}
    )


__all__ = ["post_message", "list_channels", "send_dm"]
