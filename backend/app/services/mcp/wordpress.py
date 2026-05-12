"""WordPress MCP adapter — Phase 6.x.

Tools exposed in v1:

  • ``create_post(title, content, status="draft", slug=None, categories=None, tags=None)``
  • ``update_post(post_id, **fields)``
  • ``list_categories()``

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


_SERVER_ID = "wordpress"


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
            f"No WordPress connection for organization {organization_id}."
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
    content: str,
    status: str = "draft",
    slug: str | None = None,
    categories: list[int] | None = None,
    tags: list[int] | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {
        "title": title,
        "content": content,
        "status": status,
    }
    if slug:
        args["slug"] = slug
    if categories:
        args["categories"] = list(categories)
    if tags:
        args["tags"] = list(tags)
    return await _call(session, organization_id, "create_post", args)


async def update_post(
    session: AsyncSession,
    *,
    organization_id: UUID,
    post_id: int,
    **fields: Any,
) -> MCPAdapterResult:
    args: dict[str, Any] = {"post_id": int(post_id)}
    args.update(fields)
    return await _call(session, organization_id, "update_post", args)


async def list_categories(
    session: AsyncSession, *, organization_id: UUID
) -> MCPAdapterResult:
    return await _call(session, organization_id, "list_categories", {})


__all__ = ["create_post", "update_post", "list_categories"]
