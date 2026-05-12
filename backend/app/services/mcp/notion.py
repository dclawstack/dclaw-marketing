"""Notion MCP adapter — Phase 6.x.

Tools:

  • ``search(query, limit=10)``
  • ``get_page(page_id)``
  • ``create_page(parent_id, title, content_blocks)``
  • ``update_page(page_id, properties)``
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "notion"


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
            f"No Notion connection for organization {organization_id}."
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


async def search(
    session: AsyncSession,
    *,
    organization_id: UUID,
    query: str,
    limit: int = 10,
) -> MCPAdapterResult:
    return await _call(
        session, organization_id, "search", {"query": query, "limit": int(limit)}
    )


async def get_page(
    session: AsyncSession,
    *,
    organization_id: UUID,
    page_id: str,
) -> MCPAdapterResult:
    return await _call(
        session, organization_id, "get_page", {"page_id": page_id}
    )


async def create_page(
    session: AsyncSession,
    *,
    organization_id: UUID,
    parent_id: str,
    title: str,
    content_blocks: list[dict],
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "create_page",
        {
            "parent_id": parent_id,
            "title": title,
            "content_blocks": list(content_blocks),
        },
    )


async def update_page(
    session: AsyncSession,
    *,
    organization_id: UUID,
    page_id: str,
    properties: dict,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "update_page",
        {"page_id": page_id, "properties": dict(properties)},
    )


__all__ = ["search", "get_page", "create_page", "update_page"]
