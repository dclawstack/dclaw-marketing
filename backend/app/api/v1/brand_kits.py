"""Brand Kits API — versioned per-Org brand identity.

Mounted under /orgs/{org_id}/brand-kits. An Org has many BrandKits
(historical versions); exactly one is_active=True at any time. Agents
default to the active one when generating content.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.brand_kit import BrandKit, Persona
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User


router = APIRouter(prefix="/orgs/{org_id}/brand-kits", tags=["brand-kits"])


# ---------- schemas -----------------------------------------------------

class PersonaIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    demographics: dict[str, Any] | None = None
    jobs_to_be_done: list[str] | None = None
    fears: list[str] | None = None
    desires: list[str] | None = None
    traits: list[str] | None = None


class PersonaRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    demographics: dict | None
    jobs_to_be_done: list | None
    fears: list | None
    desires: list | None
    traits: list | None

    model_config = ConfigDict(from_attributes=True)


class BrandKitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    logo_asset_id: UUID | None = None
    logo_dark_asset_id: UUID | None = None
    palette: dict[str, Any] | None = None
    fonts: dict[str, Any] | None = None
    voice: dict[str, Any] | None = None
    positioning: dict[str, Any] | None = None
    personas: list[PersonaIn] = Field(default_factory=list)


class BrandKitUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    logo_asset_id: UUID | None = None
    logo_dark_asset_id: UUID | None = None
    palette: dict[str, Any] | None = None
    fonts: dict[str, Any] | None = None
    voice: dict[str, Any] | None = None
    positioning: dict[str, Any] | None = None


class BrandKitRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    version: int
    is_active: bool
    logo_asset_id: UUID | None
    logo_dark_asset_id: UUID | None
    palette_json: dict | None
    fonts_json: dict | None
    voice_json: dict | None
    positioning_json: dict | None
    personas: list[PersonaRead]

    model_config = ConfigDict(from_attributes=True)


# ---------- helpers -----------------------------------------------------

async def _require_org_role(
    session: AsyncSession,
    user: User,
    org_id: UUID,
    roles: tuple[OrganizationRole, ...],
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an org member.")
    if m.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {m.role.value} not permitted.",
        )


# Roles allowed to manage Brand Kits: admin, manager, creatives.
MANAGE_ROLES = (OrganizationRole.admin, OrganizationRole.manager, OrganizationRole.creatives)
VIEW_ROLES = tuple(OrganizationRole)  # any member can read


# ---------- routes ------------------------------------------------------

@router.post("", response_model=BrandKitRead, status_code=status.HTTP_201_CREATED)
async def create_brand_kit(
    org_id: UUID,
    body: BrandKitCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BrandKit:
    await _require_org_role(session, user, org_id, MANAGE_ROLES)

    # Deactivate any existing active kit — only one active at a time.
    await session.execute(
        update(BrandKit)
        .where(BrandKit.organization_id == org_id, BrandKit.is_active.is_(True))
        .values(is_active=False)
    )

    # Compute next version
    existing = await session.execute(
        select(BrandKit.version)
        .where(BrandKit.organization_id == org_id)
        .order_by(BrandKit.version.desc())
        .limit(1)
    )
    last_version = existing.scalar() or 0

    kit = BrandKit(
        organization_id=org_id,
        name=body.name,
        description=body.description,
        version=last_version + 1,
        is_active=True,
        logo_asset_id=body.logo_asset_id,
        logo_dark_asset_id=body.logo_dark_asset_id,
        palette_json=body.palette,
        fonts_json=body.fonts,
        voice_json=body.voice,
        positioning_json=body.positioning,
        created_by_user_id=user.id,
    )
    session.add(kit)
    await session.flush()

    for p in body.personas:
        session.add(Persona(brand_kit_id=kit.id, **p.model_dump()))

    await session.flush()
    await session.commit()
    await session.refresh(kit)
    return kit


@router.get("", response_model=list[BrandKitRead])
async def list_brand_kits(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    only_active: bool = False,
) -> list[BrandKit]:
    await _require_org_role(session, user, org_id, VIEW_ROLES)
    stmt = select(BrandKit).where(BrandKit.organization_id == org_id).order_by(BrandKit.version.desc())
    if only_active:
        stmt = stmt.where(BrandKit.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/active", response_model=BrandKitRead)
async def get_active_brand_kit(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BrandKit:
    await _require_org_role(session, user, org_id, VIEW_ROLES)
    result = await session.execute(
        select(BrandKit).where(
            BrandKit.organization_id == org_id, BrandKit.is_active.is_(True)
        )
    )
    kit = result.scalar_one_or_none()
    if kit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active brand kit.")
    return kit


@router.get("/{kit_id}", response_model=BrandKitRead)
async def get_brand_kit(
    org_id: UUID,
    kit_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BrandKit:
    await _require_org_role(session, user, org_id, VIEW_ROLES)
    kit = await session.get(BrandKit, kit_id)
    if kit is None or kit.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return kit


@router.patch("/{kit_id}", response_model=BrandKitRead)
async def update_brand_kit(
    org_id: UUID,
    kit_id: UUID,
    body: BrandKitUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BrandKit:
    """In-place update of a brand kit (does NOT bump version).

    For a versioned change, POST a new BrandKit instead — the previous
    version stays in the DB.
    """
    await _require_org_role(session, user, org_id, MANAGE_ROLES)
    kit = await session.get(BrandKit, kit_id)
    if kit is None or kit.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    data = body.model_dump(exclude_unset=True)
    # Translate the field names to JSON column names
    mapping = {
        "palette": "palette_json",
        "fonts": "fonts_json",
        "voice": "voice_json",
        "positioning": "positioning_json",
    }
    for k, v in data.items():
        setattr(kit, mapping.get(k, k), v)

    await session.flush()
    await session.commit()
    await session.refresh(kit)
    return kit


@router.post("/{kit_id}/activate", response_model=BrandKitRead)
async def activate_brand_kit(
    org_id: UUID,
    kit_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BrandKit:
    """Make `kit_id` the active brand kit for this Org. Deactivates
    whatever was previously active.
    """
    await _require_org_role(session, user, org_id, MANAGE_ROLES)
    kit = await session.get(BrandKit, kit_id)
    if kit is None or kit.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    await session.execute(
        update(BrandKit)
        .where(BrandKit.organization_id == org_id, BrandKit.is_active.is_(True))
        .values(is_active=False)
    )
    kit.is_active = True
    await session.flush()
    await session.commit()
    await session.refresh(kit)
    return kit
