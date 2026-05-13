"""Landing-page CRUD (SP3-16 — H1 Landing-Page Builder, minimal).

Pages live as a JSON blob on Organization.landing_pages_json. Each page
has a slug (unique within an org) and HTML body. Public-facing render is
a follow-up.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User


router = APIRouter(tags=["pages"])


_SLUG_RX = re.compile(r"^[a-z0-9](-?[a-z0-9])*$")


class PageCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    body_html: str = Field(default="", max_length=100_000)
    published: bool = False


class PageUpdate(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=128)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body_html: str | None = Field(default=None, max_length=100_000)
    published: bool | None = None


class PageRead(BaseModel):
    id: str
    slug: str
    title: str
    body_html: str
    published: bool
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="allow")


async def _require_member(
    session: AsyncSession, user: User, organization_id: UUID
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
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )


def _pages(org: Organization) -> list[dict]:
    blob = org.landing_pages_json or {}
    return list(blob.get("pages") or [])


def _persist(org: Organization, pages: list[dict]) -> None:
    org.landing_pages_json = {"pages": pages}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/orgs/{organization_id}/pages", response_model=list[PageRead])
async def list_pages(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    await _require_member(session, user, organization_id)
    return _pages(org)


@router.post(
    "/orgs/{organization_id}/pages",
    response_model=PageRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_page(
    organization_id: UUID,
    body: PageCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    await _require_member(session, user, organization_id)

    if not _SLUG_RX.match(body.slug):
        raise HTTPException(
            status_code=400,
            detail="Slug must be lowercase alphanumeric, optionally with hyphens.",
        )
    pages = _pages(org)
    if any(p.get("slug") == body.slug for p in pages):
        raise HTTPException(
            status_code=409,
            detail=f"A page with slug '{body.slug}' already exists.",
        )

    new_page = {
        "id": str(uuid.uuid4()),
        "slug": body.slug,
        "title": body.title,
        "body_html": body.body_html,
        "published": body.published,
        "created_at": _now(),
        "updated_at": _now(),
    }
    pages.append(new_page)
    _persist(org, pages)
    await session.commit()
    return new_page


@router.patch(
    "/orgs/{organization_id}/pages/{page_id}", response_model=PageRead
)
async def update_page(
    organization_id: UUID,
    page_id: str,
    body: PageUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    await _require_member(session, user, organization_id)

    pages = _pages(org)
    for p in pages:
        if p.get("id") == page_id:
            patch = body.model_dump(exclude_unset=True)
            if "slug" in patch and patch["slug"] is not None:
                if not _SLUG_RX.match(patch["slug"]):
                    raise HTTPException(
                        status_code=400, detail="Invalid slug format."
                    )
                if any(
                    q.get("slug") == patch["slug"] and q.get("id") != page_id
                    for q in pages
                ):
                    raise HTTPException(
                        status_code=409, detail="Slug already in use."
                    )
            p.update(patch)
            p["updated_at"] = _now()
            _persist(org, pages)
            await session.commit()
            return p
    raise HTTPException(status_code=404, detail="Page not found.")


@router.delete(
    "/orgs/{organization_id}/pages/{page_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_page(
    organization_id: UUID,
    page_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    await _require_member(session, user, organization_id)

    pages = _pages(org)
    remaining = [p for p in pages if p.get("id") != page_id]
    if len(remaining) == len(pages):
        raise HTTPException(status_code=404, detail="Page not found.")
    _persist(org, remaining)
    await session.commit()
    return None
