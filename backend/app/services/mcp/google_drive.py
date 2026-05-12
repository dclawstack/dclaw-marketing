"""Google Drive MCP adapter — Phase 6.x.

Tools:

  • ``list_files(folder_id=None, q=None, page_size=20)``
  • ``get_file(file_id)``
  • ``download_file(file_id)``  — returns bytes-as-base64 in the
                                   result dict via the server.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "google_drive"


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
            f"No Google Drive connection for organization {organization_id}."
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


async def list_files(
    session: AsyncSession,
    *,
    organization_id: UUID,
    folder_id: str | None = None,
    q: str | None = None,
    page_size: int = 20,
) -> MCPAdapterResult:
    args: dict[str, Any] = {"page_size": int(page_size)}
    if folder_id:
        args["folder_id"] = folder_id
    if q:
        args["q"] = q
    return await _call(session, organization_id, "list_files", args)


async def get_file(
    session: AsyncSession,
    *,
    organization_id: UUID,
    file_id: str,
) -> MCPAdapterResult:
    return await _call(
        session, organization_id, "get_file", {"file_id": file_id}
    )


async def download_file(
    session: AsyncSession,
    *,
    organization_id: UUID,
    file_id: str,
) -> MCPAdapterResult:
    return await _call(
        session, organization_id, "download_file", {"file_id": file_id}
    )


__all__ = ["list_files", "get_file", "download_file"]
