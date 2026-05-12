"""Integrations API — MCP Connection management (Theme D / Phase 6).

Endpoints:
  GET    /integrations/registry              — list of all built-in MCP servers
  GET    /orgs/{org_id}/connections          — list this org's connections
  POST   /orgs/{org_id}/connections          — create one (admin)
  GET    /orgs/{org_id}/connections/{id}     — get one
  PATCH  /orgs/{org_id}/connections/{id}     — edit metadata / rotate secret
  POST   /orgs/{org_id}/connections/{id}/health-check
  DELETE /orgs/{org_id}/connections/{id}     — revoke (soft)

The registry endpoint is public-to-members (no token required to read
the catalog), so the /integrations UI can populate tiles before the
user has any connections.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.connection import Connection, ConnectionStatus
from app.models.organization import (
    OrganizationMembership,
    OrganizationRole,
)
from app.models.user import User
from app.services import mcp_registry
from app.services.secret_box import seal


router = APIRouter(tags=["integrations"])

_WRITE_ROLES: tuple[OrganizationRole, ...] = (
    OrganizationRole.admin,
    OrganizationRole.manager,
)


# ---------- registry --------------------------------------------------------


class IntegrationCatalogEntry(BaseModel):
    server_id: str
    name: str
    category: str
    auth: str
    docs_url: str
    description: str
    tools: list[str]


@router.get(
    "/integrations/registry",
    response_model=list[IntegrationCatalogEntry],
)
async def get_registry(
    user: User = Depends(current_active_user),
) -> list[IntegrationCatalogEntry]:
    """All built-in MCP servers — used to render the /integrations grid."""
    _ = user  # authenticated only
    return [
        IntegrationCatalogEntry(
            server_id=s["server_id"],
            name=s["name"],
            category=s["category"].value,
            auth=s["auth"].value,
            docs_url=s["docs_url"],
            description=s["description"],
            tools=s["tools"],
        )
        for s in mcp_registry.SERVERS
    ]


# ---------- connection schemas ----------------------------------------------


class ConnectionCreate(BaseModel):
    server_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    secret: str | None = Field(
        default=None,
        description=(
            "Token / API key / password — encrypted at rest with Fernet "
            "before storage. Never echoed back in reads."
        ),
    )
    metadata_json: dict | None = None
    scopes: list[str] | None = None


class ConnectionUpdate(BaseModel):
    name: str | None = None
    secret: str | None = None  # rotate
    metadata_json: dict | None = None
    scopes: list[str] | None = None
    status: ConnectionStatus | None = None


class ConnectionRead(BaseModel):
    id: UUID
    organization_id: UUID
    server_id: str
    name: str
    auth_kind: str
    metadata_json: dict | None
    scopes: list[str] | None
    status: ConnectionStatus
    has_secret: bool
    last_health_at: datetime | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime


def _to_read(c: Connection) -> ConnectionRead:
    return ConnectionRead(
        id=c.id,
        organization_id=c.organization_id,
        server_id=c.server_id,
        name=c.name,
        auth_kind=c.auth_kind,
        metadata_json=c.metadata_json,
        scopes=c.scopes,
        status=c.status,
        has_secret=bool(c.encrypted_secret_blob),
        last_health_at=c.last_health_at,
        last_error_message=c.last_error_message,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


async def _require_member(
    session: AsyncSession,
    user: User,
    org_id: UUID,
    *,
    write: bool = False,
) -> None:
    if user.is_superuser:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    m = result.scalar_one_or_none()
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member."
        )
    if write and m.role not in _WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or manager can manage connections.",
        )


async def _get_or_404(
    session: AsyncSession, org_id: UUID, connection_id: UUID
) -> Connection:
    result = await session.execute(
        select(Connection).where(
            Connection.id == connection_id,
            Connection.organization_id == org_id,
        )
    )
    c = result.scalar_one_or_none()
    if c is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found."
        )
    return c


# ---------- connection endpoints --------------------------------------------


@router.post(
    "/orgs/{org_id}/connections",
    response_model=ConnectionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    org_id: UUID,
    body: ConnectionCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ConnectionRead:
    await _require_member(session, user, org_id, write=True)

    server = mcp_registry.get(body.server_id)
    if server is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown MCP server '{body.server_id}'.",
        )

    encrypted: bytes | None = seal(body.secret) if body.secret else None

    conn = Connection(
        organization_id=org_id,
        server_id=body.server_id,
        name=body.name,
        auth_kind=server["auth"].value,
        encrypted_secret_blob=encrypted,
        metadata_json=body.metadata_json,
        scopes=body.scopes,
        status=ConnectionStatus.active,
        created_by_user_id=user.id,
    )
    session.add(conn)
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        if "uq_connection_org_server_name" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A connection named '{body.name}' to {body.server_id} "
                    "already exists for this org."
                ),
            )
        raise
    await session.refresh(conn)
    return _to_read(conn)


@router.get(
    "/orgs/{org_id}/connections",
    response_model=list[ConnectionRead],
)
async def list_connections(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[ConnectionRead]:
    await _require_member(session, user, org_id)
    result = await session.execute(
        select(Connection)
        .where(Connection.organization_id == org_id)
        .order_by(Connection.server_id, Connection.name)
    )
    return [_to_read(c) for c in result.scalars().all()]


@router.get(
    "/orgs/{org_id}/connections/{connection_id}",
    response_model=ConnectionRead,
)
async def get_connection(
    org_id: UUID,
    connection_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ConnectionRead:
    await _require_member(session, user, org_id)
    return _to_read(await _get_or_404(session, org_id, connection_id))


@router.patch(
    "/orgs/{org_id}/connections/{connection_id}",
    response_model=ConnectionRead,
)
async def update_connection(
    org_id: UUID,
    connection_id: UUID,
    body: ConnectionUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ConnectionRead:
    await _require_member(session, user, org_id, write=True)
    c = await _get_or_404(session, org_id, connection_id)

    data: dict[str, Any] = body.model_dump(exclude_unset=True)
    if "secret" in data:
        secret = data.pop("secret")
        c.encrypted_secret_blob = seal(secret) if secret else None
    for k, v in data.items():
        setattr(c, k, v)
    await session.commit()
    await session.refresh(c)
    return _to_read(c)


@router.post(
    "/orgs/{org_id}/connections/{connection_id}/health-check",
    response_model=ConnectionRead,
)
async def health_check(
    org_id: UUID,
    connection_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ConnectionRead:
    """Stamp last_health_at + clear stale errors. Real probes ship
    per-server in follow-up PRs.
    """
    await _require_member(session, user, org_id, write=True)
    c = await _get_or_404(session, org_id, connection_id)
    c.last_health_at = datetime.now(tz=timezone.utc)
    c.last_error_message = None
    await session.commit()
    await session.refresh(c)
    return _to_read(c)


@router.delete(
    "/orgs/{org_id}/connections/{connection_id}",
    response_model=ConnectionRead,
)
async def revoke_connection(
    org_id: UUID,
    connection_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ConnectionRead:
    await _require_member(session, user, org_id, write=True)
    c = await _get_or_404(session, org_id, connection_id)
    c.status = ConnectionStatus.revoked
    c.encrypted_secret_blob = None
    await session.commit()
    await session.refresh(c)
    return _to_read(c)
