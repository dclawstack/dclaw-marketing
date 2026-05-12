"""Ghost MCP adapter — Phase 6.x.

Tools exposed in v1:

  • ``create_post(title, html, status="draft", tags=None, feature_image=None)``
  • ``publish_post(post_id, send_email=False)``
  • ``list_posts(limit=10, filter=None)``

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


_SERVER_ID = "ghost"


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
            f"No Ghost connection for organization {organization_id}."
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


async def create_post(
    session: AsyncSession,
    *,
    organization_id: UUID,
    title: str,
    html: str,
    status: str = "draft",
    tags: list[str] | None = None,
    feature_image: str | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {"title": title, "html": html, "status": status}
    if tags:
        args["tags"] = list(tags)
    if feature_image:
        args["feature_image"] = feature_image
    return await _call(session, organization_id, "create_post", args)


async def publish_post(
    session: AsyncSession,
    *,
    organization_id: UUID,
    post_id: str,
    send_email: bool = False,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "publish_post",
        {"post_id": post_id, "send_email": bool(send_email)},
    )


async def list_posts(
    session: AsyncSession,
    *,
    organization_id: UUID,
    limit: int = 10,
    filter: str | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {"limit": int(limit)}
    if filter:
        args["filter"] = filter
    return await _call(session, organization_id, "list_posts", args)


__all__ = ["create_post", "publish_post", "list_posts"]
