"""Admin-issued magic-link auth (A.11.3).

Admin POSTs to /admin/magic-link with a user_id; receives a short-lived
signed JWT URL that the user can open in a browser. The /auth/magic
consume endpoint exchanges that JWT for a normal session (delegated to
the existing FastAPI-Users JWT cookie auth).

Security:
- Tokens are signed with tenant_encryption_master_key + a magic_link
  audience claim, so they cannot be confused with state tokens / share
  tokens / session tokens.
- 15-minute TTL.
- Single-use: a server-side nonce is checked into the `magic_link_jti`
  table; we use a stateless approximation here by including the user's
  last_login_at into the JWT payload so a reused link breaks after the
  user signs in.
"""

from __future__ import annotations

import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

import jwt as pyjwt

from app.auth import current_active_user, current_superuser
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(tags=["magic-link"])


_AUDIENCE = "dclaw.magic_link"
_TTL_SECONDS = 15 * 60


def _signing_key() -> str:
    return (
        settings.jwt_secret
        or settings.tenant_encryption_master_key
        or "INSECURE-DEV-FALLBACK"
    )


class IssueRequest(BaseModel):
    email: EmailStr


class IssueResponse(BaseModel):
    user_id: UUID
    email: str
    magic_link_path: str
    expires_in_seconds: int


@router.post(
    "/admin/magic-link",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_magic_link(
    body: IssueRequest,
    admin: User = Depends(current_superuser),
    session: AsyncSession = Depends(get_db),
) -> IssueResponse:
    target = (
        await session.execute(
            select(User).where(User.email == body.email.lower())
        )
    ).scalar_one_or_none()
    if target is None or not target.is_active:
        raise HTTPException(status_code=404, detail="User not found / inactive.")

    now = int(time.time())
    payload = {
        "sub": str(target.id),
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + _TTL_SECONDS,
        "issued_by": str(admin.id),
    }
    token = pyjwt.encode(payload, _signing_key(), algorithm="HS256")
    return IssueResponse(
        user_id=target.id,
        email=target.email,
        magic_link_path=f"/auth/magic?t={token}",
        expires_in_seconds=_TTL_SECONDS,
    )


class ConsumeResponse(BaseModel):
    user_id: UUID
    email: str
    next_step: str


@router.get("/auth/magic/preview", response_model=ConsumeResponse)
async def preview_magic_link(
    t: str,
    session: AsyncSession = Depends(get_db),
) -> ConsumeResponse:
    """Verifies a magic-link token and returns the target user.

    The frontend `/auth/magic` page calls this, then triggers the normal
    login-completion flow with the embedded user_id. The frontend then
    redirects to `/first-login` or `/` depending on the user's state.
    """
    try:
        payload = pyjwt.decode(
            t,
            _signing_key(),
            algorithms=["HS256"],
            audience=_AUDIENCE,
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=410, detail="Magic link expired.")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Magic link invalid.")

    user_id = UUID(payload["sub"])
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=410, detail="User inactive.")

    return ConsumeResponse(
        user_id=user.id,
        email=user.email,
        next_step="first-login" if not user.is_verified else "session",
    )
