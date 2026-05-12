"""Mixpanel MCP adapter — Phase 6.x.

Tools exposed in v1:

  * ``query_funnel(funnel_id, from_date, to_date)``
  * ``query_segmentation(event, from_date, to_date, on=None)``
  * ``track_event(event, properties)``

Stub fallback inherited from mcp_client.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "mixpanel"


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
            f"No Mixpanel connection for organization {organization_id}."
        )
    return c


async def _call(
    session: AsyncSession,
    organization_id: UUID,
    tool: str,
    arguments: dict,
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


async def query_funnel(
    session: AsyncSession,
    *,
    organization_id: UUID,
    funnel_id: str,
    from_date: str,
    to_date: str,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "query_funnel",
        {"funnel_id": funnel_id, "from_date": from_date, "to_date": to_date},
    )


async def query_segmentation(
    session: AsyncSession,
    *,
    organization_id: UUID,
    event: str,
    from_date: str,
    to_date: str,
    on: str | None = None,
) -> MCPAdapterResult:
    args = {"event": event, "from_date": from_date, "to_date": to_date}
    if on:
        args["on"] = on
    return await _call(session, organization_id, "query_segmentation", args)


async def track_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    event: str,
    properties: dict | None = None,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "track_event",
        {"event": event, "properties": properties or {}},
    )


__all__ = ["query_funnel", "query_segmentation", "track_event"]
