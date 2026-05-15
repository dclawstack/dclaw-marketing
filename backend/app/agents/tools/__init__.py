"""Conductor tool fleet (S5-CDR-C).

Importing this package side-effect-registers every tool the Conductor
can call. Each sub-module covers one sidebar area; collectively they
give the Conductor agentic operation of the whole platform.
"""

from app.agents.tools.registry import (
    REGISTRY,
    Tool,
    ToolContext,
    ToolRegistry,
)

# Side-effect imports — each module registers its tools at import time.
from app.agents.tools import (  # noqa: F401  — registration side-effects
    admin as _admin,
    channels as _channels,
    content as _content,
    insights as _insights,
    navigation as _navigation,
    overview as _overview,
    research as _research,
    work as _work,
)


__all__ = ["REGISTRY", "Tool", "ToolContext", "ToolRegistry"]
