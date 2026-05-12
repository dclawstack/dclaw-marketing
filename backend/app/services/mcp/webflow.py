"""Webflow MCP adapter — Phase 6.x.

Tools exposed in v1:

  • ``list_sites()``
  • ``create_blog_post(site_id, collection_id, title, body_html, slug=None, publish=False)``
  • ``publish_site(site_id, domain_ids=None)``

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


_SERVER_ID = "webflow"


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
            f"No Webflow connection for organization {organization_id}."
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


async def list_sites(
    session: AsyncSession, *, organization_id: UUID
) -> MCPAdapterResult:
    return await _call(session, organization_id, "list_sites", {})


async def create_blog_post(
    session: AsyncSession,
    *,
    organization_id: UUID,
    site_id: str,
    collection_id: str,
    title: str,
    body_html: str,
    slug: str | None = None,
    publish: bool = False,
) -> MCPAdapterResult:
    args: dict[str, Any] = {
        "site_id": site_id,
        "collection_id": collection_id,
        "title": title,
        "body_html": body_html,
        "publish": bool(publish),
    }
    if slug:
        args["slug"] = slug
    return await _call(session, organization_id, "create_blog_post", args)


async def publish_site(
    session: AsyncSession,
    *,
    organization_id: UUID,
    site_id: str,
    domain_ids: list[str] | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {"site_id": site_id}
    if domain_ids:
        args["domain_ids"] = list(domain_ids)
    return await _call(session, organization_id, "publish_site", args)


__all__ = ["list_sites", "create_blog_post", "publish_site"]
