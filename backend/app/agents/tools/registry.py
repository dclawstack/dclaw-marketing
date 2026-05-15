"""Tool registry — the canonical list of tools the Conductor can call.

Each tool has:
  - `name`: stable identifier passed to Claude
  - `description`: what the tool does + when to use it (Claude reads this)
  - `input_schema`: JSON Schema for the tool's args (Claude validates)
  - `handler`: async coroutine `(ctx, **args) -> dict`
  - `requires_approval`: write tools that need Inbox hard-gate

Handlers are pure async functions; they take a `ToolContext` and the
parsed args, and return a JSON-serializable dict that becomes the
`tool_result` block Claude sees in the next iteration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ToolContext:
    """Per-call execution context handed to every tool handler."""

    org_id: UUID
    user_id: UUID
    session: AsyncSession


ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: ToolHandler
    requires_approval: bool = False
    category: str = "general"


@dataclass
class ToolRegistry:
    """In-process tool registry.

    Module-level singleton `REGISTRY` is populated at import time by
    each tool module. The Conductor reads `as_claude_schema()` for the
    tools=[…] argument; tool calls come back with names that resolve
    via `get(name)`.
    """

    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def all(self) -> list[Tool]:
        return list(self.tools.values())

    def as_claude_schema(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self.tools.values()
        ]


REGISTRY = ToolRegistry()


def tool(
    *,
    name: str,
    description: str,
    input_schema: dict,
    requires_approval: bool = False,
    category: str = "general",
) -> Callable[[ToolHandler], ToolHandler]:
    """Decorator: register a tool handler in REGISTRY.

    Usage:

        @tool(name="list_inbox_items", description="…", input_schema={…})
        async def _impl(ctx: ToolContext, **args) -> dict:
            …
            return {…}
    """

    def _wrap(handler: ToolHandler) -> ToolHandler:
        REGISTRY.register(
            Tool(
                name=name,
                description=description,
                input_schema=input_schema,
                handler=handler,
                requires_approval=requires_approval,
                category=category,
            )
        )
        return handler

    return _wrap


__all__ = ["REGISTRY", "Tool", "ToolContext", "ToolRegistry", "tool"]
