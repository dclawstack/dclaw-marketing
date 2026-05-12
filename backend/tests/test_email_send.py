"""Phase 7.1 — Resend send adapter unit tests (stub path)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from app.services.email_send import SendProvider, send_email


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.mark.asyncio
async def test_stub_returns_synthetic_message_id():
    res = await send_email(
        to=["alice@example.com"],
        subject="hi",
        html="<p>hello</p>",
    )
    assert res.provider == SendProvider.stub
    assert res.message_id.startswith("msg_stub_")
    assert res.to == ["alice@example.com"]
    assert res.subject == "hi"


@pytest.mark.asyncio
async def test_stub_is_deterministic():
    a = await send_email(
        to=["a@x.io", "b@x.io"], subject="s", html="<p>h</p>"
    )
    b = await send_email(
        to=["b@x.io", "a@x.io"], subject="s", html="<p>h</p>"
    )
    # Same content (recipient order should be normalized)
    assert a.message_id == b.message_id


@pytest.mark.asyncio
async def test_empty_recipients_raises():
    with pytest.raises(ValueError):
        await send_email(to=[], subject="x", html="x")
