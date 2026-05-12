"""Per-server MCP adapters — Phase 6.x.

Each module here defines a small set of "official" tool names for one
external system (HubSpot, GA4, Stripe, …) plus a thin wrapper that
calls ``app.services.mcp_client.invoke_tool`` with the right
arguments shape for that server.

Agents call the adapter by name; the adapter resolves the Org's
Connection row, then dispatches via the MCP protocol layer. Stub
fallback comes free from the protocol layer when the connection's
endpoint isn't configured.

Per-adapter responsibilities:

  • Declare the tool vocabulary (e.g. HubSpot: ``search_contacts``,
    ``create_deal``).
  • Map the agent-side kwargs into the provider's argument shape.
  • Re-shape the provider's response into a flat dict an agent
    expects.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MCPAdapterResult:
    server: str
    tool: str
    arguments: dict
    result: dict
    duration_ms: int
    stub: bool


__all__ = ["MCPAdapterResult"]
