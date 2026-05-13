"""Per-Org white-label branding (Theme O — SP3 stretch).

Stores logo / favicon / colors / custom-domain on
Organization.branding_json. The Client Portal reads this to skin the
left-rail and the report PDFs.
"""

from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from app.models.user import User


router = APIRouter(tags=["branding"])


_HEX_RX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_DOMAIN_RX = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")


class Branding(BaseModel):
    logo_url: str | None = Field(default=None, max_length=2048)
    favicon_url: str | None = Field(default=None, max_length=2048)
    primary_color_hex: str | None = Field(default=None, max_length=7)
    secondary_color_hex: str | None = Field(default=None, max_length=7)
    custom_domain: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


async def _require_role(
    session: AsyncSession,
    user: User,
    organization_id: UUID,
    roles: tuple[OrganizationRole, ...],
) -> None:
    if user.is_superuser:
        return
    m = (
        await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()
    if m is None or m.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Org admin / manager required.",
        )


@router.get("/orgs/{organization_id}/branding", response_model=Branding)
async def get_branding(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Branding:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    # Reading is open to any member (UI rendering needs it).
    await _require_role(
        session, user, organization_id,
        tuple(OrganizationRole),  # any member can read
    )
    return Branding(**(org.branding_json or {}))


@router.put("/orgs/{organization_id}/branding", response_model=Branding)
async def update_branding(
    organization_id: UUID,
    body: Branding,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Branding:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    await _require_role(
        session, user, organization_id,
        (OrganizationRole.admin, OrganizationRole.manager),
    )

    if body.primary_color_hex and not _HEX_RX.match(body.primary_color_hex):
        raise HTTPException(status_code=400, detail="primary_color_hex must be #RRGGBB")
    if body.secondary_color_hex and not _HEX_RX.match(body.secondary_color_hex):
        raise HTTPException(status_code=400, detail="secondary_color_hex must be #RRGGBB")
    if body.custom_domain and not _DOMAIN_RX.match(body.custom_domain):
        raise HTTPException(status_code=400, detail="custom_domain must be a bare hostname")

    org.branding_json = body.model_dump(exclude_none=False)
    await session.commit()
    return body
