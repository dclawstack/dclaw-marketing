"""Async MCP client (Phase 6.1).

A pragmatic HTTP-transport MCP client. Real MCP servers expose tools
over JSON-RPC; for v1 we use a simpler shape that any HTTP-fronted
MCP server (or our own gateway) can satisfy:

    POST  <endpoint>/tools/<tool_name>/invoke
    body: {"arguments": {...}}
    body: {"result": <any-json>}   on success
    body: {"error":  {...}}        on failure

If the Connection has no ``metadata_json.endpoint``, the client falls
back to a deterministic stub that returns the tool name + arguments
echoed back, so agent code paths can still exercise the flow in dev.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from app.models.connection import Connection
from app.services.secret_box import unseal


class MCPInvocationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MCPInvocation:
    server_id: str
    tool_name: str
    arguments: dict
    result: Any
    duration_ms: int
    stub: bool


def _stub_invoke(
    *, server_id: str, tool_name: str, arguments: dict
) -> MCPInvocation:
    """Returns a deterministic synthetic response so agent code paths
    work in dev without provisioning real MCP servers.
    """
    return MCPInvocation(
        server_id=server_id,
        tool_name=tool_name,
        arguments=arguments,
        result={
            "stub": True,
            "echo": {
                "server_id": server_id,
                "tool_name": tool_name,
                "arguments": arguments,
            },
        },
        duration_ms=0,
        stub=True,
    )


async def invoke_tool(
    *,
    connection: Connection,
    tool_name: str,
    arguments: dict | None = None,
    client: httpx.AsyncClient | None = None,
) -> MCPInvocation:
    """Invokes ``tool_name`` against the MCP server represented by
    ``connection``.

    - If ``connection.metadata_json["endpoint"]`` is set, the call goes
      to that endpoint with the connection's decrypted secret used as
      a bearer token.
    - Otherwise, returns a stub response.

    Raises ``MCPInvocationError`` on transport / server failure.
    """
    args = dict(arguments or {})
    metadata = connection.metadata_json or {}
    endpoint = metadata.get("endpoint") if isinstance(metadata, dict) else None

    if not endpoint or not isinstance(endpoint, str):
        return _stub_invoke(
            server_id=connection.server_id,
            tool_name=tool_name,
            arguments=args,
        )

    secret = ""
    if connection.encrypted_secret_blob:
        try:
            secret = unseal(connection.encrypted_secret_blob)
        except Exception:
            secret = ""

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if secret:
        headers["Authorization"] = f"Bearer {secret}"

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    started = asyncio.get_event_loop().time()
    try:
        resp = await client.post(
            f"{endpoint.rstrip('/')}/tools/{tool_name}/invoke",
            headers=headers,
            json={"arguments": args},
        )
    except httpx.HTTPError as exc:
        raise MCPInvocationError(f"transport: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()

    duration_ms = int((asyncio.get_event_loop().time() - started) * 1000)

    if resp.status_code != 200:
        raise MCPInvocationError(
            f"server {resp.status_code}: {resp.text[:300]}"
        )

    try:
        body = resp.json()
    except Exception as exc:
        raise MCPInvocationError(f"non-JSON response: {exc}") from exc

    if "error" in body and body["error"] is not None:
        raise MCPInvocationError(
            f"tool error: {body['error']}"
        )

    return MCPInvocation(
        server_id=connection.server_id,
        tool_name=tool_name,
        arguments=args,
        result=body.get("result"),
        duration_ms=duration_ms,
        stub=False,
    )


__all__ = ["invoke_tool", "MCPInvocation", "MCPInvocationError"]
