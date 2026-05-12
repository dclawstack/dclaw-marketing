"""PostHog MCP adapter — Phase 6.x.

Tools exposed in v1:

  * ``capture(event, distinct_id, properties)``
  * ``query_insight(insight_id)``
  * ``query_funnel(funnel_id, date_from=None, date_to=None)``
  * ``list_feature_flags()``

Stub fallback inherited from mcp_client.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "posthog"


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
            f"No PostHog connection for organization {organization_id}."
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


async def capture(
    session: AsyncSession,
    *,
    organization_id: UUID,
    event: str,
    distinct_id: str,
    properties: dict | None = None,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "capture",
        {
            "event": event,
            "distinct_id": distinct_id,
            "properties": properties or {},
        },
    )


async def query_insight(
    session: AsyncSession,
    *,
    organization_id: UUID,
    insight_id: str,
) -> MCPAdapterResult:
    return await _call(
        session, organization_id, "query_insight", {"insight_id": insight_id}
    )


async def query_funnel(
    session: AsyncSession,
    *,
    organization_id: UUID,
    funnel_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
) -> MCPAdapterResult:
    args: dict = {"funnel_id": funnel_id}
    if date_from:
        args["date_from"] = date_from
    if date_to:
        args["date_to"] = date_to
    return await _call(session, organization_id, "query_funnel", args)


async def list_feature_flags(
    session: AsyncSession, *, organization_id: UUID
) -> MCPAdapterResult:
    return await _call(session, organization_id, "list_feature_flags", {})


__all__ = ["capture", "query_insight", "query_funnel", "list_feature_flags"]
