"""Phase 7.6 — ConvertKit + Beehiiv newsletter adapter tests."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from app.services.newsletter import beehiiv as bh
from app.services.newsletter import convertkit as ck


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


# ===== ConvertKit =====


@pytest.mark.asyncio
async def test_ck_stub_when_no_secret(monkeypatch):
    monkeypatch.setattr(ck.settings, "convertkit_api_secret", "")
    res = await ck.send_campaign(subject="hi", html="<p>x</p>")
    assert res.provider == "convertkit"
    assert res.campaign_id.startswith("ck_stub_")
    assert res.raw["stub"] is True


@pytest.mark.asyncio
async def test_ck_full_flow(monkeypatch):
    monkeypatch.setattr(ck.settings, "convertkit_api_secret", "ck-secret")
    calls = []

    def handler(request):
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if path == "/v3/broadcasts" and request.method == "POST":
            return httpx.Response(201, json={"broadcast": {"id": 42}})
        if path.endswith("/send_at"):
            return httpx.Response(200, json={})
        return httpx.Response(404, text=f"unexpected {path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await ck.send_campaign(subject="hi", html="<p>x</p>", client=client)
    await client.aclose()

    assert calls == ["POST /v3/broadcasts", "POST /v3/broadcasts/42/send_at"]
    assert res.campaign_id == "42"


@pytest.mark.asyncio
async def test_ck_401_raises_auth_error(monkeypatch):
    monkeypatch.setattr(ck.settings, "convertkit_api_secret", "bad")

    def handler(request):
        return httpx.Response(401, text="bad secret")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(ck.ConvertKitAuthError):
        await ck.send_campaign(subject="x", html="<p>x</p>", client=client)
    await client.aclose()


@pytest.mark.asyncio
async def test_ck_send_failure(monkeypatch):
    monkeypatch.setattr(ck.settings, "convertkit_api_secret", "k")

    def handler(request):
        path = request.url.path
        if path == "/v3/broadcasts":
            return httpx.Response(201, json={"broadcast": {"id": 1}})
        return httpx.Response(500, text="oops")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(ck.ConvertKitPublishError, match="send"):
        await ck.send_campaign(subject="x", html="<p>x</p>", client=client)
    await client.aclose()


# ===== Beehiiv =====


@pytest.mark.asyncio
async def test_bh_stub_when_no_key(monkeypatch):
    monkeypatch.setattr(bh.settings, "beehiiv_api_key", "")
    monkeypatch.setattr(bh.settings, "beehiiv_publication_id", "pub-1")
    res = await bh.send_campaign(subject="hi", html="<p>x</p>")
    assert res.provider == "beehiiv"
    assert res.campaign_id.startswith("bh_stub_")


@pytest.mark.asyncio
async def test_bh_stub_when_no_publication(monkeypatch):
    monkeypatch.setattr(bh.settings, "beehiiv_api_key", "k")
    monkeypatch.setattr(bh.settings, "beehiiv_publication_id", "")
    res = await bh.send_campaign(subject="hi", html="<p>x</p>")
    assert res.raw["stub"] is True


@pytest.mark.asyncio
async def test_bh_full_flow(monkeypatch):
    monkeypatch.setattr(bh.settings, "beehiiv_api_key", "k")
    monkeypatch.setattr(bh.settings, "beehiiv_publication_id", "pub-1")
    calls = []

    def handler(request):
        path = request.url.path
        calls.append(f"{request.method} {path}")
        assert request.headers.get("Authorization") == "Bearer k"
        if path == "/v2/publications/pub-1/posts" and request.method == "POST":
            return httpx.Response(201, json={"data": {"id": "p-99"}})
        if path.endswith("/send"):
            return httpx.Response(200)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await bh.send_campaign(subject="hi", html="<p>x</p>", client=client)
    await client.aclose()

    assert calls == [
        "POST /v2/publications/pub-1/posts",
        "POST /v2/publications/pub-1/posts/p-99/send",
    ]
    assert res.campaign_id == "p-99"


@pytest.mark.asyncio
async def test_bh_401_raises_auth_error(monkeypatch):
    monkeypatch.setattr(bh.settings, "beehiiv_api_key", "bad")
    monkeypatch.setattr(bh.settings, "beehiiv_publication_id", "pub-1")

    def handler(request):
        return httpx.Response(401, text="invalid")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(bh.BeehiivAuthError):
        await bh.send_campaign(subject="x", html="<p>x</p>", client=client)
    await client.aclose()


@pytest.mark.asyncio
async def test_bh_send_failure(monkeypatch):
    monkeypatch.setattr(bh.settings, "beehiiv_api_key", "k")
    monkeypatch.setattr(bh.settings, "beehiiv_publication_id", "pub-1")

    def handler(request):
        path = request.url.path
        if path.endswith("/posts"):
            return httpx.Response(201, json={"data": {"id": "p-1"}})
        return httpx.Response(500, text="oops")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(bh.BeehiivPublishError, match="send"):
        await bh.send_campaign(subject="x", html="<p>x</p>", client=client)
    await client.aclose()
