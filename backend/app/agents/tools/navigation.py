"""Navigation tool — Conductor can deep-link the user to any page.

The handler returns a structured `action` the frontend recognizes; it
doesn't perform any backend work. Pure UI-level routing instruction.
"""

from __future__ import annotations

from app.agents.tools.registry import ToolContext, tool


_KNOWN_ROUTES = [
    "/", "/conductor", "/inbox", "/calendar",
    "/agents/creatives", "/library", "/workflows", "/workflows/templates",
    "/channels", "/email", "/ads",
    "/agents/seo", "/agents/seo/pipeline", "/analytics", "/knowledge",
    "/integrations", "/orgs", "/admin/users", "/admin/models",
]


@tool(
    name="navigate_to",
    description=(
        "Deep-link the user to a specific page on the DClaw platform. "
        "Use when the user asks to 'open', 'go to', 'show me', or "
        "'take me to' a page; the frontend will route them there. "
        "Pass the in-app route (e.g. '/calendar', '/agents/seo'). "
        "Known routes include: " + ", ".join(_KNOWN_ROUTES)
    ),
    input_schema={
        "type": "object",
        "properties": {
            "route": {
                "type": "string",
                "description": "In-app route, starting with '/'. E.g. '/calendar'.",
            },
            "reason": {
                "type": "string",
                "description": "Short one-line reason shown to the user.",
            },
        },
        "required": ["route"],
    },
    category="navigation",
)
async def navigate_to(ctx: ToolContext, *, route: str, reason: str = "") -> dict:
    if not isinstance(route, str) or not route.startswith("/"):
        return {"ok": False, "error": "route must start with '/'"}
    return {
        "ok": True,
        "action": "navigate",
        "route": route,
        "reason": reason,
    }
