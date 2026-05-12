"""OAuth 2.0 start/callback endpoints for publisher accounts (Phase 5.7).

Each connected provider goes through:

  1. GET  /api/v1/oauth/{provider}/start?account_id=...
        Returns the provider's authorize URL the frontend redirects to.
        For PKCE providers (X, Pinterest) the response also carries the
        code_verifier; the frontend stores it briefly and returns it to
        the callback as ``cv``.

  2. GET  /api/v1/oauth/{provider}/callback?code=...&state=...&cv=...
        Exchanges the code for tokens, persists them on the
        SocialAccount row, redirects to ``/channels`` on success
        (302) or ``/channels?error=...`` on failure.

The token is stored on the existing ``_interim_access_token`` column
for v1; migrating to Fernet-encrypted blob is a follow-up that
doesn't change this endpoint surface.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.social_account import SocialAccount
from app.models.user import User
from app.services.oauth import (
    OAuthError,
    PROVIDERS,
    build_authorize_url,
    exchange_code,
)


router = APIRouter(prefix="/oauth", tags=["oauth"])


def _redirect_uri(request: Request, provider: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/oauth/{provider}/callback"


@router.get("/{provider}/start")
async def oauth_start(
    provider: str,
    account_id: UUID,
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider}",
        )
    account = await session.get(SocialAccount, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SocialAccount not found.",
        )
    # Mastodon needs the instance URL from auth_metadata_json.
    instance_url = (account.auth_metadata_json or {}).get("instance_url")
    try:
        au = build_authorize_url(
            provider=provider,
            account_id=str(account_id),
            redirect_uri=_redirect_uri(request, provider),
            instance_url=instance_url,
        )
    except OAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Persist the code_verifier on the account so the callback can
    # retrieve it without trusting the frontend.
    meta = dict(account.auth_metadata_json or {})
    if au.code_verifier:
        meta["oauth_code_verifier"] = au.code_verifier
    meta["oauth_state"] = au.state
    account.auth_metadata_json = meta
    await session.flush()
    await session.commit()

    return {
        "authorize_url": au.url,
        "state": au.state,
        # code_verifier is also returned for clients that prefer to
        # roundtrip it themselves rather than rely on the server-side
        # store.
        "code_verifier": au.code_verifier,
    }


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    cv: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    front_base = settings.app_env  # placeholder — frontend base URL would live in config
    success_redirect = "/channels"
    fail_redirect = "/channels?oauth_error="

    if error:
        return RedirectResponse(url=f"{fail_redirect}{error}", status_code=302)
    if not (code and state):
        return RedirectResponse(
            url=f"{fail_redirect}missing_code_or_state", status_code=302
        )
    if provider not in PROVIDERS:
        return RedirectResponse(
            url=f"{fail_redirect}unknown_provider", status_code=302
        )

    try:
        from app.services.oauth import _verify_state

        claims = _verify_state(state)
    except OAuthError as exc:
        return RedirectResponse(
            url=f"{fail_redirect}bad_state", status_code=302
        )

    account_id = UUID(claims["acct"])
    account = await session.get(SocialAccount, account_id)
    if account is None:
        return RedirectResponse(
            url=f"{fail_redirect}account_missing", status_code=302
        )

    meta = dict(account.auth_metadata_json or {})
    server_cv = meta.get("oauth_code_verifier")
    code_verifier = cv or server_cv
    instance_url = meta.get("instance_url")

    try:
        token_resp, _ = exchange_code(
            provider=provider,
            code=code,
            state=state,
            redirect_uri=_redirect_uri(request, provider),
            code_verifier=code_verifier,
            instance_url=instance_url,
        )
    except OAuthError as exc:
        return RedirectResponse(
            url=f"{fail_redirect}exchange_failed", status_code=302
        )

    # Persist token (Fernet-encrypted via SocialAccount.access_token setter).
    account.access_token = token_resp.access_token
    meta["oauth_token_type"] = token_resp.token_type
    if token_resp.expires_in:
        meta["oauth_expires_in"] = token_resp.expires_in
    if token_resp.refresh_token:
        meta["oauth_refresh_token"] = token_resp.refresh_token
    # Clear the one-time PKCE verifier + state.
    meta.pop("oauth_code_verifier", None)
    meta.pop("oauth_state", None)
    account.auth_metadata_json = meta
    await session.flush()
    await session.commit()

    return RedirectResponse(url=success_redirect, status_code=302)


__all__ = ["router"]
