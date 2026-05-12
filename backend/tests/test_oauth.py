"""Phase 5.7 — OAuth scaffold tests (pure + httpx MockTransport)."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.services.oauth import (
    OAuthError,
    PROVIDERS,
    build_authorize_url,
    exchange_code,
)


@pytest.fixture(autouse=True)
def _stub_client_creds(monkeypatch):
    """Set non-empty creds for every provider in the registry."""
    for spec in PROVIDERS.values():
        monkeypatch.setattr(
            settings, spec.client_id_setting, "client_id_xyz", raising=False
        )
        monkeypatch.setattr(
            settings, spec.client_secret_setting, "secret_abc", raising=False
        )
    yield


def test_build_url_linkedin_includes_state_and_scopes():
    out = build_authorize_url(
        provider="linkedin",
        account_id="00000000-0000-0000-0000-000000000001",
        redirect_uri="https://app.example/cb",
    )
    assert "linkedin.com/oauth/v2/authorize" in out.url
    assert "client_id=client_id_xyz" in out.url
    assert "redirect_uri=https" in out.url
    assert "scope=w_member_social" in out.url
    assert "state=" in out.url
    assert out.code_verifier is None  # not PKCE


def test_build_url_x_includes_pkce_challenge():
    out = build_authorize_url(
        provider="x",
        account_id="00000000-0000-0000-0000-000000000001",
        redirect_uri="https://app.example/cb",
    )
    assert "code_challenge=" in out.url
    assert "code_challenge_method=S256" in out.url
    assert out.code_verifier is not None
    assert len(out.code_verifier) > 40


def test_build_url_mastodon_requires_instance_url():
    with pytest.raises(OAuthError):
        build_authorize_url(
            provider="mastodon",
            account_id="00000000-0000-0000-0000-000000000001",
            redirect_uri="https://app.example/cb",
        )
    ok = build_authorize_url(
        provider="mastodon",
        account_id="00000000-0000-0000-0000-000000000001",
        redirect_uri="https://app.example/cb",
        instance_url="https://mastodon.social",
    )
    assert "mastodon.social/oauth/authorize" in ok.url


def test_build_url_unknown_provider_raises():
    with pytest.raises(OAuthError):
        build_authorize_url(
            provider="nope",
            account_id="x",
            redirect_uri="https://x/cb",
        )


def test_exchange_code_linkedin_returns_token():
    au = build_authorize_url(
        provider="linkedin",
        account_id="00000000-0000-0000-0000-000000000001",
        redirect_uri="https://app.example/cb",
    )

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = dict(
            [p.split("=", 1) for p in request.content.decode().split("&")]
        )
        return httpx.Response(
            200,
            json={
                "access_token": "AT123",
                "refresh_token": "RT456",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "w_member_social",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    token, account_id = exchange_code(
        provider="linkedin",
        code="ABC",
        state=au.state,
        redirect_uri="https://app.example/cb",
        client=client,
    )
    assert captured["url"] == "https://www.linkedin.com/oauth/v2/accessToken"
    assert captured["body"]["code"] == "ABC"
    assert captured["body"]["grant_type"] == "authorization_code"
    assert captured["body"]["client_id"] == "client_id_xyz"
    assert captured["body"]["client_secret"] == "secret_abc"
    assert token.access_token == "AT123"
    assert token.refresh_token == "RT456"
    assert account_id == "00000000-0000-0000-0000-000000000001"


def test_exchange_code_reddit_uses_basic_auth():
    au = build_authorize_url(
        provider="reddit",
        account_id="00000000-0000-0000-0000-000000000001",
        redirect_uri="https://app.example/cb",
    )

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = dict(
            [p.split("=", 1) for p in request.content.decode().split("&")]
        )
        return httpx.Response(
            200, json={"access_token": "rT", "token_type": "Bearer"}
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    token, _ = exchange_code(
        provider="reddit",
        code="ABC",
        state=au.state,
        redirect_uri="https://app.example/cb",
        client=client,
    )
    assert captured["auth"].startswith("Basic ")
    assert "client_id" not in captured["body"]
    assert "client_secret" not in captured["body"]
    assert token.access_token == "rT"


def test_exchange_code_x_requires_code_verifier():
    au = build_authorize_url(
        provider="x",
        account_id="00000000-0000-0000-0000-000000000001",
        redirect_uri="https://app.example/cb",
    )

    def handler(request):  # pragma: no cover — should never run
        return httpx.Response(200, json={})

    with pytest.raises(OAuthError):
        exchange_code(
            provider="x",
            code="ABC",
            state=au.state,
            redirect_uri="https://app.example/cb",
            code_verifier=None,  # missing → error
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )


def test_exchange_code_non_200_raises():
    au = build_authorize_url(
        provider="linkedin",
        account_id="00000000-0000-0000-0000-000000000001",
        redirect_uri="https://app.example/cb",
    )
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(400, text="bad")
        )
    )
    with pytest.raises(OAuthError):
        exchange_code(
            provider="linkedin",
            code="ABC",
            state=au.state,
            redirect_uri="https://app.example/cb",
            client=client,
        )


def test_exchange_code_bad_state_raises():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    )
    with pytest.raises(OAuthError):
        exchange_code(
            provider="linkedin",
            code="ABC",
            state="not-a-jwt",
            redirect_uri="https://app.example/cb",
            client=client,
        )
