"""Phase 6.1 — async MCP client unit tests."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio

from app.services.mcp_client import MCPInvocationError, invoke_tool


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _conn(endpoint: str | None = None, secret_blob: bytes | None = None):
    """Returns a Connection-shaped duck."""
    return SimpleNamespace(
        server_id="hubspot",
        metadata_json={"endpoint": endpoint} if endpoint else None,
        encrypted_secret_blob=secret_blob,
    )


def _transport(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_stub_when_no_endpoint():
    conn = _conn(endpoint=None)
    inv = await invoke_tool(
        connection=conn, tool_name="search_contacts",
        arguments={"q": "alice"},
    )
    assert inv.stub is True
    assert inv.tool_name == "search_contacts"
    assert inv.result["echo"]["arguments"] == {"q": "alice"}


@pytest.mark.asyncio
async def test_real_invocation_returns_server_result():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/mcp/tools/search_contacts/invoke"
        body = json.loads(request.content.decode("utf-8"))
        assert body == {"arguments": {"q": "alice"}}
        return httpx.Response(200, json={"result": {"hits": [{"id": 1}]}})

    async with _transport(handler) as client:
        conn = _conn(endpoint="https://mcp.example.com/api/mcp")
        inv = await invoke_tool(
            connection=conn,
            tool_name="search_contacts",
            arguments={"q": "alice"},
            client=client,
        )
    assert inv.stub is False
    assert inv.result == {"hits": [{"id": 1}]}


@pytest.mark.asyncio
async def test_server_error_raises_invocation_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream down")

    async with _transport(handler) as client:
        conn = _conn(endpoint="https://mcp.example.com/api/mcp")
        with pytest.raises(MCPInvocationError) as ei:
            await invoke_tool(
                connection=conn,
                tool_name="x",
                arguments={},
                client=client,
            )
        assert "503" in str(ei.value)


@pytest.mark.asyncio
async def test_error_field_in_body_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": {"code": -32000, "msg": "rate limited"}})

    async with _transport(handler) as client:
        conn = _conn(endpoint="https://mcp.example.com/api/mcp")
        with pytest.raises(MCPInvocationError) as ei:
            await invoke_tool(
                connection=conn,
                tool_name="x",
                arguments={},
                client=client,
            )
        assert "rate limited" in str(ei.value)
