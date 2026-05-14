"""OAuth 2.0 authorization-code scaffold for publisher accounts (Phase 5.7).

A small per-provider registry + two generic helpers:

  ``build_authorize_url(provider, account_id, redirect_uri, scopes)``
  ``exchange_code(provider, code, redirect_uri)``

Each provider entry declares its authorize URL, token URL, default
scope list, and the small shape-specific quirks (PKCE for X, instance
URL for Mastodon, etc.). Tokens come back as a ``TokenResponse``; the
caller persists them on the relevant ``SocialAccount`` row.

State token: a JWT signed with ``settings.jwt_secret`` carrying the
account_id + a random nonce + an expiry. The callback re-validates
both to prevent CSRF.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """One row in the OAuth registry."""

    name: str
    authorize_url: str
    token_url: str
    default_scopes: list[str]
    auth_via_basic: bool = False  # POST token request uses Basic auth (Reddit)
    uses_pkce: bool = False         # X / Pinterest require PKCE
    extra_params: dict[str, str] = field(default_factory=dict)
    client_id_setting: str = ""     # name of the settings field
    client_secret_setting: str = ""


PROVIDERS: dict[str, ProviderSpec] = {
    "linkedin": ProviderSpec(
        name="linkedin",
        authorize_url="https://www.linkedin.com/oauth/v2/authorization",
        token_url="https://www.linkedin.com/oauth/v2/accessToken",
        default_scopes=["w_member_social", "r_liteprofile", "r_emailaddress"],
        client_id_setting="linkedin_client_id",
        client_secret_setting="linkedin_client_secret",
    ),
    "x": ProviderSpec(
        name="x",
        authorize_url="https://twitter.com/i/oauth2/authorize",
        token_url="https://api.twitter.com/2/oauth2/token",
        default_scopes=["tweet.read", "tweet.write", "users.read", "offline.access"],
        uses_pkce=True,
        client_id_setting="x_client_id",
        client_secret_setting="x_client_secret",
    ),
    "instagram": ProviderSpec(
        name="instagram",
        authorize_url="https://www.facebook.com/v18.0/dialog/oauth",
        token_url="https://graph.facebook.com/v18.0/oauth/access_token",
        default_scopes=["instagram_basic", "instagram_content_publish", "pages_show_list"],
        client_id_setting="instagram_client_id",
        client_secret_setting="instagram_client_secret",
    ),
    "reddit": ProviderSpec(
        name="reddit",
        authorize_url="https://www.reddit.com/api/v1/authorize",
        token_url="https://www.reddit.com/api/v1/access_token",
        default_scopes=["identity", "submit", "read"],
        auth_via_basic=True,
        client_id_setting="reddit_client_id",
        client_secret_setting="reddit_client_secret",
    ),
    "pinterest": ProviderSpec(
        name="pinterest",
        authorize_url="https://www.pinterest.com/oauth/",
        token_url="https://api.pinterest.com/v5/oauth/token",
        default_scopes=["boards:read", "pins:read", "pins:write"],
        uses_pkce=True,
        client_id_setting="pinterest_client_id",
        client_secret_setting="pinterest_client_secret",
    ),
    "discord": ProviderSpec(
        name="discord",
        authorize_url="https://discord.com/api/oauth2/authorize",
        token_url="https://discord.com/api/oauth2/token",
        default_scopes=["identify", "webhook.incoming"],
        client_id_setting="discord_client_id",
        client_secret_setting="discord_client_secret",
    ),
    # Mastodon is per-instance — the start helper takes an instance_url
    # arg and substitutes it into the templates here.
    "mastodon": ProviderSpec(
        name="mastodon",
        authorize_url="{instance_url}/oauth/authorize",
        token_url="{instance_url}/oauth/token",
        default_scopes=["read", "write", "follow"],
        client_id_setting="mastodon_client_id",
        client_secret_setting="mastodon_client_secret",
    ),
    # Bluesky (AT Protocol) — pluggable per-PDS host, app-password style.
    # The OAuth dance is being standardised at the protocol layer; for
    # Sprint 4 the connect flow stores handle + app-password as the
    # credential pair via SocialAccount/Connection. This spec entry
    # captures the metadata so /admin/health rolls it up like the others.
    "bluesky": ProviderSpec(
        name="bluesky",
        authorize_url="https://bsky.social/xrpc/com.atproto.server.createSession",
        token_url="https://bsky.social/xrpc/com.atproto.server.refreshSession",
        default_scopes=[],
        client_id_setting="bluesky_client_id",
        client_secret_setting="bluesky_client_secret",
    ),
}


class OAuthError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TokenResponse:
    access_token: str
    refresh_token: str | None
    expires_in: int | None  # seconds
    token_type: str
    scope: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AuthorizeUrl:
    url: str
    state: str
    code_verifier: str | None  # only set when PKCE


# ---------- State token ----------------------------------------------------


def _sign_state(*, account_id: str, nonce: str, exp: int) -> str:
    payload = {"acct": account_id, "nonce": nonce, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _verify_state(state: str) -> dict:
    try:
        return jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
    except Exception as exc:
        raise OAuthError(f"State token rejected: {exc}") from exc


# ---------- PKCE -----------------------------------------------------------


def _pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge) using SHA256 S256."""
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        )
        .decode()
        .rstrip("=")
    )
    return verifier, challenge


# ---------- Public helpers -------------------------------------------------


def build_authorize_url(
    *,
    provider: str,
    account_id: str,
    redirect_uri: str,
    scopes: list[str] | None = None,
    instance_url: str | None = None,
) -> AuthorizeUrl:
    """Compose the authorize URL the user is sent to.

    Returns:
      AuthorizeUrl — caller redirects to ``.url`` and persists ``.state``
      + ``.code_verifier`` (when PKCE) on the SocialAccount row so the
      callback can pair them.
    """
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise OAuthError(f"Unknown OAuth provider: {provider}")
    client_id = getattr(settings, spec.client_id_setting, "")
    if not client_id:
        raise OAuthError(
            f"Missing client_id for {provider} "
            f"(settings.{spec.client_id_setting})"
        )

    nonce = secrets.token_urlsafe(16)
    state = _sign_state(
        account_id=account_id,
        nonce=nonce,
        exp=int(time.time()) + 600,  # 10 min
    )
    scope_str = " ".join(scopes or spec.default_scopes)
    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "scope": scope_str,
        **spec.extra_params,
    }

    code_verifier: str | None = None
    if spec.uses_pkce:
        code_verifier, challenge = _pkce_pair()
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"

    authorize_template = spec.authorize_url
    if "{instance_url}" in authorize_template:
        if not instance_url:
            raise OAuthError(
                f"{provider} authorize requires instance_url"
            )
        authorize_template = authorize_template.format(
            instance_url=instance_url.rstrip("/")
        )

    return AuthorizeUrl(
        url=f"{authorize_template}?{urlencode(params)}",
        state=state,
        code_verifier=code_verifier,
    )


def exchange_code(
    *,
    provider: str,
    code: str,
    state: str,
    redirect_uri: str,
    code_verifier: str | None = None,
    instance_url: str | None = None,
    client: httpx.Client | None = None,
) -> tuple[TokenResponse, str]:
    """Exchange an authorization code for an access token.

    Returns ``(TokenResponse, account_id)``. The account_id comes from
    the state JWT — caller looks it up on SocialAccount and writes the
    token there.
    """
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise OAuthError(f"Unknown OAuth provider: {provider}")
    claims = _verify_state(state)
    account_id = claims.get("acct") or ""
    if not account_id:
        raise OAuthError("State token missing acct claim")

    client_id = getattr(settings, spec.client_id_setting, "")
    client_secret = getattr(settings, spec.client_secret_setting, "")
    if not (client_id and client_secret):
        raise OAuthError(
            f"Missing client credentials for {provider}"
        )

    body: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    if spec.uses_pkce:
        if not code_verifier:
            raise OAuthError(
                f"{provider} token exchange requires code_verifier"
            )
        body["code_verifier"] = code_verifier
        body["client_id"] = client_id
    else:
        body["client_id"] = client_id
        body["client_secret"] = client_secret

    headers: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": "DClawMarketing/1.2 (oauth)",
    }
    if spec.auth_via_basic:
        # Reddit: basic-auth with the client creds, body stays
        # form-encoded sans client_id/secret.
        body.pop("client_id", None)
        body.pop("client_secret", None)
        token_param = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()
        headers["Authorization"] = f"Basic {token_param}"

    token_url = spec.token_url
    if "{instance_url}" in token_url:
        if not instance_url:
            raise OAuthError(f"{provider} token requires instance_url")
        token_url = token_url.format(instance_url=instance_url.rstrip("/"))

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True
    try:
        resp = client.post(token_url, data=body, headers=headers)
    finally:
        if owns_client:
            client.close()

    if resp.status_code != 200:
        raise OAuthError(
            f"{provider} token exchange {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json() or {}
    if "access_token" not in data:
        raise OAuthError(
            f"{provider} token response missing access_token: {data}"
        )
    return (
        TokenResponse(
            access_token=str(data["access_token"]),
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in"),
            token_type=str(data.get("token_type") or "Bearer"),
            scope=data.get("scope"),
            raw=data,
        ),
        account_id,
    )


__all__ = [
    "PROVIDERS",
    "ProviderSpec",
    "OAuthError",
    "TokenResponse",
    "AuthorizeUrl",
    "build_authorize_url",
    "exchange_code",
]
