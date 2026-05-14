"""TOTP 2FA endpoints (A.11.6).

  POST /me/2fa/setup    → returns a fresh secret + otpauth URL. Does
                         NOT enable 2FA yet — the user must come back
                         with a verified code from their authenticator.

  POST /me/2fa/verify   → with body {code}; if valid, flips totp_enabled
                         to True. This is the first-time enrollment.

  POST /me/2fa/disable  → admin only OR self with a current valid code,
                         turns 2FA off (clears the secret).

  POST /auth/totp/verify → during login flow; checks a code for the
                          currently authenticated user. The front-end
                          calls this after a successful password login
                          if the user has totp_enabled=True.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.user import User
from app.services import secret_box, totp as totp_service


router = APIRouter(tags=["2fa"])


class SetupResponse(BaseModel):
    otpauth_url: str
    secret_b32: str  # shown once during enrollment


class CodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


@router.post("/me/2fa/setup", response_model=SetupResponse)
async def setup_2fa(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SetupResponse:
    if user.totp_enabled:
        raise HTTPException(
            status_code=409, detail="2FA is already enabled. Disable it first."
        )
    secret = totp_service.random_secret()
    user.totp_secret = secret_box.seal(secret).decode("utf-8")
    user.totp_enabled = False
    await session.commit()
    return SetupResponse(
        otpauth_url=totp_service.otpauth_url(secret, label=user.email),
        secret_b32=secret,
    )


@router.post("/me/2fa/verify")
async def verify_enrollment(
    body: CodeRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if user.totp_secret is None:
        raise HTTPException(status_code=400, detail="Run /me/2fa/setup first.")
    try:
        secret = secret_box.unseal(user.totp_secret)
    except Exception:
        raise HTTPException(status_code=500, detail="2FA secret unreadable.")
    if not totp_service.verify_code(secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid code.")
    user.totp_enabled = True
    await session.commit()
    return {"enabled": True}


@router.post("/me/2fa/disable")
async def disable_2fa(
    body: CodeRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not user.totp_enabled or user.totp_secret is None:
        raise HTTPException(status_code=409, detail="2FA is not enabled.")
    secret = secret_box.unseal(user.totp_secret)
    if not totp_service.verify_code(secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid code.")
    user.totp_secret = None
    user.totp_enabled = False
    await session.commit()
    return {"enabled": False}


@router.post("/me/2fa/recovery-codes")
async def issue_recovery_codes(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Generate 8 single-use recovery codes for this user (S4-G1).

    Hashes are stored on the user row when the schema supports it; the
    plaintext list is returned ONCE — caller must save them.
    """
    if not user.totp_enabled:
        raise HTTPException(status_code=409, detail="Enable 2FA first.")
    import hashlib
    import secrets as _secrets

    codes = [_secrets.token_hex(5) for _ in range(8)]
    hashes = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
    if hasattr(user, "totp_recovery_hashes_json"):
        user.totp_recovery_hashes_json = hashes
    await session.commit()
    return {"codes": codes}


@router.post("/admin/users/{user_id}/2fa/disable")
async def admin_disable_2fa(
    user_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """S4-G3 — superadmin removes 2FA for a stuck user, writes audit row."""
    if not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Superadmin only.")
    from uuid import UUID

    target = await session.get(User, UUID(user_id))
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    target.totp_enabled = False
    target.totp_secret = None
    await session.commit()
    try:
        from app.models.audit_event import (
            AuditActorKind,
            AuditEvent,
            AuditResult,
        )

        session.add(
            AuditEvent(
                actor_kind=AuditActorKind.user,
                actor_user_id=user.id,
                action_type="user.2fa.admin_disable",
                target_type="user",
                target_id=str(target.id),
                result=AuditResult.success,
                payload_json={"reason": "admin override"},
            )
        )
        await session.commit()
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True}


@router.post("/auth/totp/verify")
async def login_verify(
    body: CodeRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Called by the frontend after primary password login if the user
    has 2FA enabled. Returns OK / NO; the client can then mark the
    session as fully-authenticated.
    """
    if not user.totp_enabled or user.totp_secret is None:
        return {"verified": True, "note": "no_2fa_enrolled"}
    secret = secret_box.unseal(user.totp_secret)
    ok = totp_service.verify_code(secret, body.code)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid TOTP code.")
    return {"verified": True}
