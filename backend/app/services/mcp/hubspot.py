"""HubSpot MCP adapter — Phase 6.x.

Wraps the ``hubspot`` server in the MCP registry with a typed tool
vocabulary the Conductor / role-agents can call by name.

Tools exposed in v1:

  • ``search_contacts(email, limit=10)`` — find contacts by email
    substring.
  • ``create_deal(contact_id, name, amount, stage=...)`` — create a
    deal linked to an existing contact.
  • ``list_recent_activities(contact_id, days=30)`` — pull the
    contact's recent activity timeline.

Each function is a thin shim that resolves the Org's ``hubspot``
Connection row, then dispatches via the protocol-layer
``invoke_tool``. Stub fallback inherited from that layer.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "hubspot"


async def _resolve_connection(
    session: AsyncSession, *, organization_id: UUID
) -> Connection:
    """Return the Org's hubspot Connection row, or raise."""
    res = await session.execute(
        select(Connection).where(
            Connection.organization_id == organization_id,
            Connection.server_id == _SERVER_ID,
        )
    )
    conn = res.scalar_one_or_none()
    if conn is None:
        raise MCPInvocationError(
            f"No HubSpot connection for organization {organization_id}; "
            "connect via the Integrations page first."
        )
    return conn


async def _call(
    session: AsyncSession,
    *,
    organization_id: UUID,
    tool: str,
    arguments: dict,
) -> MCPAdapterResult:
    conn = await _resolve_connection(session, organization_id=organization_id)
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


# ---------- Tools --------------------------------------------------------


async def search_contacts(
    session: AsyncSession,
    *,
    organization_id: UUID,
    email: str,
    limit: int = 10,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id=organization_id,
        tool="search_contacts",
        arguments={"email": email, "limit": int(limit)},
    )


async def create_deal(
    session: AsyncSession,
    *,
    organization_id: UUID,
    contact_id: str,
    name: str,
    amount: float,
    stage: str | None = None,
    pipeline: str | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {
        "contact_id": str(contact_id),
        "name": name,
        "amount": float(amount),
    }
    if stage:
        args["stage"] = stage
    if pipeline:
        args["pipeline"] = pipeline
    return await _call(
        session,
        organization_id=organization_id,
        tool="create_deal",
        arguments=args,
    )


async def list_recent_activities(
    session: AsyncSession,
    *,
    organization_id: UUID,
    contact_id: str,
    days: int = 30,
) -> MCPAdapterResult:
    return await _call(
        session,
        organization_id=organization_id,
        tool="list_recent_activities",
        arguments={"contact_id": str(contact_id), "days": int(days)},
    )


__all__ = [
    "search_contacts",
    "create_deal",
    "list_recent_activities",
]
