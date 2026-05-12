"""Salesforce MCP adapter — Phase 6.x.

Tools exposed in v1:

  * ``create_lead(payload)``
  * ``update_lead(lead_id, payload)``
  * ``find_lead(email)``
  * ``log_activity(record_id, activity)``

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


_SERVER_ID = "salesforce"


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
            f"No Salesforce connection for organization {organization_id}."
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


async def create_lead(
    session: AsyncSession,
    *,
    organization_id: UUID,
    email: str,
    first_name: str | None = None,
    last_name: str | None = None,
    company: str | None = None,
    extra: dict[str, Any] | None = None,
) -> MCPAdapterResult:
    payload: dict[str, Any] = {"Email": email}
    if first_name:
        payload["FirstName"] = first_name
    if last_name:
        payload["LastName"] = last_name
    if company:
        payload["Company"] = company
    if extra:
        payload.update(extra)
    return await _call(session, organization_id, "create_lead", {"payload": payload})


async def update_lead(
    session: AsyncSession,
    *,
    organization_id: UUID,
    lead_id: str,
    payload: dict[str, Any],
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "update_lead",
        {"lead_id": lead_id, "payload": payload},
    )


async def find_lead(
    session: AsyncSession, *, organization_id: UUID, email: str
) -> MCPAdapterResult:
    return await _call(session, organization_id, "find_lead", {"email": email})


async def log_activity(
    session: AsyncSession,
    *,
    organization_id: UUID,
    record_id: str,
    activity: dict[str, Any],
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id,
        "log_activity",
        {"record_id": record_id, "activity": activity},
    )


__all__ = ["create_lead", "update_lead", "find_lead", "log_activity"]
