"""Model Registry CRUD — providers + model entries.

S4-M1 / S4-M2.

Endpoints:
  GET    /api/v1/models/provider-types        — catalog of all 26 supported types
  GET    /api/v1/models/providers             — list providers visible to caller
  POST   /api/v1/models/providers             — create provider
  GET    /api/v1/models/providers/{id}        — get provider detail (no secret)
  PATCH  /api/v1/models/providers/{id}        — edit / rotate key
  DELETE /api/v1/models/providers/{id}        — soft-delete (is_active=false)
  GET    /api/v1/models/entries               — list models visible to caller
  POST   /api/v1/models/entries               — manually add a model entry
  PATCH  /api/v1/models/entries/{id}          — toggle capabilities / is_active
  DELETE /api/v1/models/entries/{id}          — hard delete

Permissions:
- Superadmin (org_id NULL on the provider) — only superadmins can create
  global providers; any authenticated user can read the global catalog.
- Org-scoped providers — only org admins / managers in that org can write.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.model_registry import (
    Capability,
    HealthStatus,
    ModelEntry,
    ModelProvider,
    ProviderType,
)
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services.model_registry import (
    BASE_URLS,
    PROVIDER_SPECS,
    capabilities_for_model_id,
)
from app.services.secret_box import seal


router = APIRouter(prefix="/models", tags=["model-registry"])

_WRITE_ROLES: tuple[OrganizationRole, ...] = (
    OrganizationRole.admin,
    OrganizationRole.manager,
)


# ---------- schemas ---------------------------------------------------------


class ProviderTypeInfo(BaseModel):
    type: ProviderType
    label: str
    tier: int
    fields: list[str]
    base_url_locked: bool
    default_base_url: str | None
    description: str


class ProviderCreate(BaseModel):
    provider_type: ProviderType
    name: str = Field(..., min_length=1, max_length=255)
    organization_id: UUID | None = None  # NULL → global (superadmin)
    base_url: str | None = None
    api_key: str | None = None
    extra_config: dict[str, Any] | None = None


class ProviderUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    extra_config: dict[str, Any] | None = None
    is_active: bool | None = None


class ProviderOut(BaseModel):
    id: UUID
    organization_id: UUID | None
    provider_type: ProviderType
    name: str
    base_url: str | None
    has_api_key: bool
    extra_config: dict[str, Any] | None
    is_active: bool
    health_status: HealthStatus
    health_error: str | None
    last_health_check_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, m: ModelProvider) -> "ProviderOut":
        return cls(
            id=m.id,
            organization_id=m.organization_id,
            provider_type=m.provider_type,
            name=m.name,
            base_url=m.base_url,
            has_api_key=bool(m.encrypted_api_key),
            extra_config=m.extra_config_json,
            is_active=m.is_active,
            health_status=m.health_status,
            health_error=m.health_error,
            last_health_check_at=m.last_health_check_at,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


class ModelEntryCreate(BaseModel):
    provider_id: UUID
    model_id: str
    display_name: str | None = None
    capabilities: list[Capability] | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None


class ModelEntryUpdate(BaseModel):
    display_name: str | None = None
    capabilities: list[Capability] | None = None
    is_active: bool | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None


class ModelEntryOut(BaseModel):
    id: UUID
    provider_id: UUID
    model_id: str
    display_name: str
    capabilities: list[str]
    context_window: int | None
    max_output_tokens: int | None
    pricing_json: dict | None = None
    status: HealthStatus
    health_error: str | None
    last_health_check_at: datetime | None
    capabilities_locked: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, m: ModelEntry) -> "ModelEntryOut":
        return cls(
            id=m.id,
            provider_id=m.provider_id,
            model_id=m.model_id,
            display_name=m.display_name,
            capabilities=list(m.capabilities or []),
            context_window=m.context_window,
            max_output_tokens=m.max_output_tokens,
            pricing_json=m.pricing_json,
            status=m.status,
            health_error=m.health_error,
            last_health_check_at=m.last_health_check_at,
            capabilities_locked=m.capabilities_locked,
            is_active=m.is_active,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )


# ---------- helpers ---------------------------------------------------------


async def _is_org_writer(db: AsyncSession, user: User, org_id: UUID) -> bool:
    row = (
        await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == org_id,
            )
        )
    ).scalar_one_or_none()
    return bool(row and row.role in _WRITE_ROLES)


async def _writable_org_ids(db: AsyncSession, user: User) -> list[UUID]:
    rows = (
        await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.role.in_(_WRITE_ROLES),
            )
        )
    ).scalars().all()
    return [r.organization_id for r in rows]


# ---------- type catalog ----------------------------------------------------


@router.get("/provider-types", response_model=list[ProviderTypeInfo])
async def list_provider_types(
    _: User = Depends(current_active_user),
) -> list[ProviderTypeInfo]:
    """Return all supported provider types with form-field metadata.

    Drives the /admin/models provider radio + dropdown UI.
    """
    return [
        ProviderTypeInfo(
            type=s.type,
            label=s.label,
            tier=s.tier,
            fields=s.fields,
            base_url_locked=s.base_url_locked,
            default_base_url=s.default_base_url or BASE_URLS.get(s.type),
            description=s.description,
        )
        for s in PROVIDER_SPECS
    ]


# ---------- providers -------------------------------------------------------


def _can_create_global(user: User) -> bool:
    return bool(getattr(user, "is_superuser", False))


@router.get("/providers", response_model=list[ProviderOut])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> list[ProviderOut]:
    org_ids = await _writable_org_ids(db, user)
    # Superadmins see everything; others see globals + their orgs.
    if getattr(user, "is_superuser", False):
        rows = (await db.execute(select(ModelProvider))).scalars().all()
    else:
        rows = (
            await db.execute(
                select(ModelProvider).where(
                    or_(
                        ModelProvider.organization_id.is_(None),
                        ModelProvider.organization_id.in_(org_ids) if org_ids else False,
                    )
                )
            )
        ).scalars().all()
    return [ProviderOut.from_model(r) for r in rows]


@router.post(
    "/providers", response_model=ProviderOut, status_code=status.HTTP_201_CREATED
)
async def create_provider(
    payload: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> ProviderOut:
    if payload.organization_id is None:
        if not _can_create_global(user):
            raise HTTPException(
                status_code=403, detail="Only superadmin can create global providers."
            )
    else:
        if not await _is_org_writer(db, user, payload.organization_id):
            raise HTTPException(status_code=403, detail="Not an admin/manager of that org.")

    from app.services.secret_box import SecretBoxNotConfiguredError

    try:
        encrypted = seal(payload.api_key) if payload.api_key else None
    except SecretBoxNotConfiguredError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    base_url = payload.base_url or BASE_URLS.get(payload.provider_type)

    provider = ModelProvider(
        organization_id=payload.organization_id,
        provider_type=payload.provider_type,
        name=payload.name,
        base_url=base_url,
        encrypted_api_key=encrypted,
        extra_config_json=payload.extra_config,
        created_by_user_id=user.id,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    # M3 — kick off auto-discovery in Celery. Best-effort: if Celery is
    # down or the broker is unreachable, the provider still saves; the
    # operator can hit POST /providers/{id}/sync to retry.
    try:
        from app.worker.tasks.model_registry import discover_provider_models

        discover_provider_models.delay(str(provider.id))
    except Exception:  # noqa: BLE001
        pass
    return ProviderOut.from_model(provider)


@router.get("/providers/{provider_id}", response_model=ProviderOut)
async def get_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> ProviderOut:
    p = await db.get(ModelProvider, provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if p.organization_id is not None and not getattr(user, "is_superuser", False):
        if not await _is_org_writer(db, user, p.organization_id):
            # Allow read for any org member.
            row = (
                await db.execute(
                    select(OrganizationMembership).where(
                        OrganizationMembership.user_id == user.id,
                        OrganizationMembership.organization_id == p.organization_id,
                    )
                )
            ).scalar_one_or_none()
            if not row:
                raise HTTPException(status_code=403, detail="Forbidden.")
    return ProviderOut.from_model(p)


@router.patch("/providers/{provider_id}", response_model=ProviderOut)
async def update_provider(
    provider_id: UUID,
    payload: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> ProviderOut:
    p = await db.get(ModelProvider, provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if p.organization_id is None:
        if not _can_create_global(user):
            raise HTTPException(status_code=403, detail="Superadmin only.")
    else:
        if not await _is_org_writer(db, user, p.organization_id):
            raise HTTPException(status_code=403, detail="Not an admin/manager.")

    if payload.name is not None:
        p.name = payload.name
    if payload.base_url is not None:
        p.base_url = payload.base_url
    if payload.api_key is not None and payload.api_key != "":
        from app.services.secret_box import SecretBoxNotConfiguredError
        try:
            p.encrypted_api_key = seal(payload.api_key)
        except SecretBoxNotConfiguredError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
    if payload.extra_config is not None:
        p.extra_config_json = payload.extra_config
    if payload.is_active is not None:
        p.is_active = payload.is_active

    await db.commit()
    await db.refresh(p)
    return ProviderOut.from_model(p)


@router.post("/providers/{provider_id}/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> dict:
    """S4-M3 — manually trigger discovery for this provider."""
    p = await db.get(ModelProvider, provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if p.organization_id is None and not _can_create_global(user):
        raise HTTPException(status_code=403, detail="Superadmin only.")
    if p.organization_id is not None and not await _is_org_writer(
        db, user, p.organization_id
    ):
        raise HTTPException(status_code=403, detail="Not an admin/manager.")
    try:
        from app.worker.tasks.model_registry import discover_provider_models

        discover_provider_models.delay(str(provider_id))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"queue failed: {e}")
    return {"queued": True}


@router.post("/providers/{provider_id}/health-check", status_code=status.HTTP_200_OK)
async def health_check_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> dict:
    """S4-M5 — synchronous health-probe for one provider (UI 'Test Connection')."""
    from app.services.model_discovery import probe_provider_health

    p = await db.get(ModelProvider, provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if p.organization_id is None and not _can_create_global(user):
        raise HTTPException(status_code=403, detail="Superadmin only.")
    if p.organization_id is not None and not await _is_org_writer(
        db, user, p.organization_id
    ):
        raise HTTPException(status_code=403, detail="Not an admin/manager.")
    status_, err = probe_provider_health(p)
    p.health_status = status_
    p.health_error = err
    p.last_health_check_at = datetime.utcnow()
    await db.commit()
    return {"status": status_.value, "error": err}


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> None:
    p = await db.get(ModelProvider, provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if p.organization_id is None:
        if not _can_create_global(user):
            raise HTTPException(status_code=403, detail="Superadmin only.")
    else:
        if not await _is_org_writer(db, user, p.organization_id):
            raise HTTPException(status_code=403, detail="Not an admin/manager.")
    # Soft-delete by deactivating, hard-delete with the cascade if explicitly requested.
    p.is_active = False
    await db.commit()


# ---------- model entries ---------------------------------------------------


@router.get("/entries", response_model=list[ModelEntryOut])
async def list_entries(
    capability: Capability | None = None,
    organization_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> list[ModelEntryOut]:
    """List model entries visible to the caller.

    Optional `capability` filter; entries whose JSON capabilities list
    contains the value pass the filter (Python-side after fetch — small N).
    """
    stmt = select(ModelEntry).join(
        ModelProvider, ModelEntry.provider_id == ModelProvider.id
    )
    if not getattr(user, "is_superuser", False):
        writable = await _writable_org_ids(db, user)
        member_orgs = (
            await db.execute(
                select(OrganizationMembership.organization_id).where(
                    OrganizationMembership.user_id == user.id,
                )
            )
        ).scalars().all()
        visible_orgs = list({*writable, *member_orgs})
        stmt = stmt.where(
            or_(
                ModelProvider.organization_id.is_(None),
                ModelProvider.organization_id.in_(visible_orgs) if visible_orgs else False,
            )
        )
    if organization_id is not None:
        stmt = stmt.where(ModelProvider.organization_id == organization_id)
    rows = (await db.execute(stmt)).scalars().all()
    if capability:
        rows = [r for r in rows if capability.value in (r.capabilities or [])]
    return [ModelEntryOut.from_model(r) for r in rows]


@router.post(
    "/entries", response_model=ModelEntryOut, status_code=status.HTTP_201_CREATED
)
async def create_entry(
    payload: ModelEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> ModelEntryOut:
    p = await db.get(ModelProvider, payload.provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if p.organization_id is None and not _can_create_global(user):
        raise HTTPException(status_code=403, detail="Superadmin only.")
    if p.organization_id is not None and not await _is_org_writer(
        db, user, p.organization_id
    ):
        raise HTTPException(status_code=403, detail="Not an admin/manager.")

    caps = (
        [c.value for c in payload.capabilities]
        if payload.capabilities
        else capabilities_for_model_id(payload.model_id)
    )
    entry = ModelEntry(
        provider_id=p.id,
        model_id=payload.model_id,
        display_name=payload.display_name or payload.model_id,
        capabilities=caps,
        context_window=payload.context_window,
        max_output_tokens=payload.max_output_tokens,
        capabilities_locked=bool(payload.capabilities),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return ModelEntryOut.from_model(entry)


@router.patch("/entries/{entry_id}", response_model=ModelEntryOut)
async def update_entry(
    entry_id: UUID,
    payload: ModelEntryUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> ModelEntryOut:
    e = await db.get(ModelEntry, entry_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Entry not found.")
    p = await db.get(ModelProvider, e.provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Parent provider missing.")
    if p.organization_id is None and not _can_create_global(user):
        raise HTTPException(status_code=403, detail="Superadmin only.")
    if p.organization_id is not None and not await _is_org_writer(
        db, user, p.organization_id
    ):
        raise HTTPException(status_code=403, detail="Not an admin/manager.")

    if payload.display_name is not None:
        e.display_name = payload.display_name
    if payload.capabilities is not None:
        e.capabilities = [c.value for c in payload.capabilities]
        e.capabilities_locked = True
    if payload.is_active is not None:
        e.is_active = payload.is_active
    if payload.context_window is not None:
        e.context_window = payload.context_window
    if payload.max_output_tokens is not None:
        e.max_output_tokens = payload.max_output_tokens

    await db.commit()
    await db.refresh(e)
    return ModelEntryOut.from_model(e)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> None:
    e = await db.get(ModelEntry, entry_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Entry not found.")
    p = await db.get(ModelProvider, e.provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Parent provider missing.")
    if p.organization_id is None and not _can_create_global(user):
        raise HTTPException(status_code=403, detail="Superadmin only.")
    if p.organization_id is not None and not await _is_org_writer(
        db, user, p.organization_id
    ):
        raise HTTPException(status_code=403, detail="Not an admin/manager.")
    await db.delete(e)
    await db.commit()
