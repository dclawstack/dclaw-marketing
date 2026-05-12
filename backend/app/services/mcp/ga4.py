"""GA4 (Google Analytics 4) MCP adapter — Phase 6.x.

Tools exposed in v1:

  • ``get_metrics(metrics, start_date, end_date, dimensions=None,
    property_id=None)`` — run a Data API ``runReport`` request and
    return the row table.
  • ``get_realtime(metrics, dimensions=None, property_id=None)`` —
    query the realtime API.
  • ``list_top_pages(start_date, end_date, limit=20, property_id=None)``
    — shortcut for the most-common SEO-Agent query.

Each call resolves the Org's ``ga4`` Connection row, then dispatches
via the protocol-layer ``invoke_tool``. Stub fallback inherited.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "ga4"


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
            f"No GA4 connection for organization {organization_id}; "
            "connect via the Integrations page first."
        )
    return c


async def _call(
    session: AsyncSession,
    organization_id: UUID,
    tool: str,
    arguments: dict,
) -> MCPAdapterResult:
    conn = await _conn(session, organization_id)
    inv = await invoke_tool(
        connection=conn, tool_name=tool, arguments=arguments
    )
    return MCPAdapterResult(
        server=_SERVER_ID,
        tool=tool,
        arguments=arguments,
        result=inv.result if isinstance(inv.result, dict) else {"value": inv.result},
        duration_ms=inv.duration_ms,
        stub=inv.stub,
    )


async def get_metrics(
    session: AsyncSession,
    *,
    organization_id: UUID,
    metrics: list[str],
    start_date: str,
    end_date: str,
    dimensions: list[str] | None = None,
    property_id: str | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {
        "metrics": list(metrics),
        "start_date": start_date,
        "end_date": end_date,
    }
    if dimensions:
        args["dimensions"] = list(dimensions)
    if property_id:
        args["property_id"] = property_id
    return await _call(session, organization_id, "get_metrics", args)


async def get_realtime(
    session: AsyncSession,
    *,
    organization_id: UUID,
    metrics: list[str],
    dimensions: list[str] | None = None,
    property_id: str | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {"metrics": list(metrics)}
    if dimensions:
        args["dimensions"] = list(dimensions)
    if property_id:
        args["property_id"] = property_id
    return await _call(session, organization_id, "get_realtime", args)


async def list_top_pages(
    session: AsyncSession,
    *,
    organization_id: UUID,
    start_date: str,
    end_date: str,
    limit: int = 20,
    property_id: str | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "limit": int(limit),
    }
    if property_id:
        args["property_id"] = property_id
    return await _call(session, organization_id, "list_top_pages", args)


__all__ = ["get_metrics", "get_realtime", "list_top_pages"]
