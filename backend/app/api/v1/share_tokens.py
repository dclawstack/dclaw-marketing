"""SP3-19 — Embeddable read-only client dashboard URLs.

Two-endpoint pattern:

  POST /api/v1/orgs/{org}/share-tokens  (auth required)
       body: {surface: "analytics", expires_in_days: 30}
       → {token, url, expires_at}

  GET /api/v1/share/{token}            (public; no auth)
       Validates the JWT; returns a white-label snapshot of the surface
       (analytics totals + rollups) for the embedded org.

The token is signed with the existing ``jwt_secret`` so we don't add a
new key. We do NOT issue a session — the share token grants read-only
access to one surface for one Org for the configured TTL.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.attribution import AnalyticsRollup
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User


router = APIRouter(tags=["share-tokens"])


_JWT_ALG = "HS256"
_TOKEN_KIND = "dclaw.share.v1"


class ShareTokenCreate(BaseModel):
    surface: str = Field(default="analytics", pattern=r"^(analytics|approvals|schedule)$")
    expires_in_days: int = Field(default=30, ge=1, le=365)


class ShareTokenResponse(BaseModel):
    token: str
    url: str
    expires_at: datetime
    surface: str


async def _require_admin(
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
    if m is None or m.role.value not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or manager can mint share tokens.",
        )


@router.post(
    "/orgs/{organization_id}/share-tokens",
    response_model=ShareTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_share_token(
    organization_id: UUID,
    body: ShareTokenCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ShareTokenResponse:
    await _require_admin(session, user, organization_id)

    org = await session.get(Organization, organization_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found."
        )

    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(days=int(body.expires_in_days))

    payload = {
        "kind": _TOKEN_KIND,
        "org": str(organization_id),
        "surface": body.surface,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "issued_by": str(user.id),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALG)

    return ShareTokenResponse(
        token=token,
        url=f"/share/{token}",
        expires_at=exp,
        surface=body.surface,
    )


@router.get("/share/{token}")
async def get_share(
    token: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Public endpoint — decodes the share token and returns read-only data."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=410, detail="Share token expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid share token.")

    if payload.get("kind") != _TOKEN_KIND:
        raise HTTPException(status_code=403, detail="Wrong token kind.")
    if payload.get("surface") != "analytics":
        # Only analytics surface supported in v1 of SP3-19; others get a 404.
        raise HTTPException(status_code=404, detail="Surface not supported.")

    organization_id = UUID(payload["org"])
    org = await db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=int(days))
    rollups = (
        await db.execute(
            select(
                AnalyticsRollup.scope,
                AnalyticsRollup.key,
                func.sum(AnalyticsRollup.metric_json["touchpoints"].as_float()).label(
                    "touchpoints"
                ),
            )
            .where(
                AnalyticsRollup.organization_id == organization_id,
                AnalyticsRollup.day >= cutoff.date(),
            )
            .group_by(AnalyticsRollup.scope, AnalyticsRollup.key)
        )
    ).all()

    by_channel: dict[str, float] = {}
    for scope, key, touchpoints in rollups:
        if scope == "channel":
            by_channel[str(key)] = float(touchpoints or 0)

    return {
        "organization": {
            "name": org.name,
            "is_external": org.is_external,
        },
        "surface": "analytics",
        "window_days": days,
        "by_channel": by_channel,
        "expires_at": payload["exp"],
    }
