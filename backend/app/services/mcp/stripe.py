"""Stripe MCP adapter — Phase 6.x.

Tools exposed in v1:

  • ``list_charges(customer=None, limit=10, created_gte=None)``
  • ``create_refund(charge_id, amount=None, reason=None)``
  • ``get_customer(email=None, customer_id=None)``

Distinct from the Stripe *send_invoice* billing adapter
(``app.services.billing.stripe``), which is the direct REST path used
by the in-platform Invoice model. The MCP adapter is the agent-facing
surface — the Conductor or Paid Media agent can ask "what's our
total spend at Stripe this month" without the platform owning the
specific REST mechanics.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.services.mcp import MCPAdapterResult
from app.services.mcp_client import MCPInvocationError, invoke_tool


_SERVER_ID = "stripe"


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
            f"No Stripe connection for organization {organization_id}."
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


async def list_charges(
    session: AsyncSession,
    *,
    organization_id: UUID,
    customer: str | None = None,
    limit: int = 10,
    created_gte: int | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {"limit": int(limit)}
    if customer:
        args["customer"] = customer
    if created_gte is not None:
        args["created_gte"] = int(created_gte)
    return await _call(session, organization_id, "list_charges", args)


async def create_refund(
    session: AsyncSession,
    *,
    organization_id: UUID,
    charge_id: str,
    amount: int | None = None,
    reason: str | None = None,
) -> MCPAdapterResult:
    args: dict[str, Any] = {"charge_id": charge_id}
    if amount is not None:
        args["amount"] = int(amount)
    if reason:
        args["reason"] = reason
    return await _call(session, organization_id, "create_refund", args)


async def get_customer(
    session: AsyncSession,
    *,
    organization_id: UUID,
    email: str | None = None,
    customer_id: str | None = None,
) -> MCPAdapterResult:
    if not (email or customer_id):
        raise MCPInvocationError("get_customer requires email or customer_id")
    args: dict[str, Any] = {}
    if email:
        args["email"] = email
    if customer_id:
        args["customer_id"] = customer_id
    return await _call(session, organization_id, "get_customer", args)


__all__ = ["list_charges", "create_refund", "get_customer"]
