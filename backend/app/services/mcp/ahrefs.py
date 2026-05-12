"""Ahrefs MCP adapter — Phase 6.x.

Tools exposed in v1:

  • ``keyword_difficulty(keywords, country="us")``
  • ``serp_overview(keyword, country="us", limit=20)``
  • ``site_audit(domain)``
  • ``backlinks(domain, limit=20)``

Stub fallback inherited from mcp_client.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "ahrefs"


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
            f"No Ahrefs connection for organization {organization_id}."
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


async def keyword_difficulty(
    session: AsyncSession,
    *,
    organization_id: UUID,
    keywords: list[str],
    country: str = "us",
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "keyword_difficulty",
        {"keywords": list(keywords), "country": country},
    )


async def serp_overview(
    session: AsyncSession,
    *,
    organization_id: UUID,
    keyword: str,
    country: str = "us",
    limit: int = 20,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "serp_overview",
        {"keyword": keyword, "country": country, "limit": int(limit)},
    )


async def site_audit(
    session: AsyncSession, *, organization_id: UUID, domain: str
) -> MCPAdapterResult:
    return await _call(session, organization_id, "site_audit", {"domain": domain})


async def backlinks(
    session: AsyncSession,
    *,
    organization_id: UUID,
    domain: str,
    limit: int = 20,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "backlinks",
        {"domain": domain, "limit": int(limit)},
    )


__all__ = ["keyword_difficulty", "serp_overview", "site_audit", "backlinks"]
