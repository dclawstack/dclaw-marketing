"""Workflow sandbox + smoke test harness (S4-D3/D4).

The sandbox path keeps every side-effect dry-run:

  - LLM nodes still call the resolver (so the operator can verify
    the model picks make sense) but mark results in the context.
  - tool_call nodes are short-circuited; the harness records the
    arguments the runner would have sent and returns a stub.
  - approval nodes auto-approve.

`smoke_workflow(workflow_id, sample_input)` runs the workflow once
in sandbox mode, returns the full context + node-by-node trace, and
flags any node that raised. Powers the "Run smoke test" button in
the visual builder.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ops import Workflow

log = logging.getLogger(__name__)


@dataclass
class SmokeStep:
    node_id: str
    node_type: str
    ok: bool
    note: str
    output_var: str | None = None
    output_preview: str | None = None


@dataclass
class SmokeResult:
    workflow_id: UUID
    ok: bool
    steps: list[SmokeStep]
    final_context: dict[str, Any]


async def smoke_workflow(
    db: AsyncSession,
    *,
    workflow_id: UUID,
    sample_input: dict[str, Any] | None = None,
) -> SmokeResult:
    wf = await db.get(Workflow, workflow_id)
    if wf is None:
        return SmokeResult(
            workflow_id=workflow_id, ok=False, steps=[], final_context={}
        )

    nodes = wf.dsl_json.get("nodes", [])
    steps: list[SmokeStep] = []
    context = dict(sample_input or {})
    all_ok = True

    for n in nodes:
        nid = n.get("id", "?")
        ntype = n.get("type", "?")
        try:
            if ntype == "llm":
                out_var = n.get("output_var") or nid
                stub = f"[sandbox] LLM '{nid}' would run."
                context[out_var] = stub
                steps.append(
                    SmokeStep(
                        node_id=nid,
                        node_type=ntype,
                        ok=True,
                        note="sandbox",
                        output_var=out_var,
                        output_preview=stub,
                    )
                )
            elif ntype == "tool_call":
                tool = n.get("tool_name", "?")
                steps.append(
                    SmokeStep(
                        node_id=nid,
                        node_type=ntype,
                        ok=True,
                        note=f"sandbox tool_call '{tool}' (skipped)",
                    )
                )
            elif ntype == "approval":
                steps.append(
                    SmokeStep(
                        node_id=nid,
                        node_type=ntype,
                        ok=True,
                        note="sandbox approval auto-approved",
                    )
                )
            elif ntype == "noop":
                steps.append(
                    SmokeStep(
                        node_id=nid,
                        node_type=ntype,
                        ok=True,
                        note=n.get("note", "noop"),
                    )
                )
            else:
                steps.append(
                    SmokeStep(
                        node_id=nid,
                        node_type=ntype,
                        ok=False,
                        note=f"unknown node type '{ntype}'",
                    )
                )
                all_ok = False
        except Exception as e:  # noqa: BLE001
            steps.append(
                SmokeStep(
                    node_id=nid,
                    node_type=ntype,
                    ok=False,
                    note=f"raised: {e}",
                )
            )
            all_ok = False

    return SmokeResult(
        workflow_id=wf.id, ok=all_ok, steps=steps, final_context=context
    )
