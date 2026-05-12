"""Workflow runner (Phase 10.3).

Synchronous DAG executor for the ``Workflow.dsl_json`` shape. Walks
nodes in topological order, runs each node's effect, threads an
accumulating ``context`` dict between them.

DSL shape::

    {
      "nodes": [
        {"id": "n1", "type": "llm",
         "system": "You are X.",
         "user_template": "Brief: {{brief}}",
         "output_var": "draft_text"  # optional; defaults to node id
        },
        {"id": "n2", "type": "tool_call",
         "connection_id": "<uuid>",
         "tool_name": "search_contacts",
         "arguments_template": {"q": "{{brief}}"}
        },
        {"id": "n3", "type": "noop", "note": "placeholder"}
      ],
      "edges": [
        {"from": "n1", "to": "n2"},
        {"from": "n2", "to": "n3"}
      ]
    }

Templates use ``{{var}}`` substitution against the running context.
Unknown vars stay literal (``{{missing}}``) — runners that need
strict rendering can post-filter.

Node types in v1:
- ``llm``       → calls ``app.agents.anthropic_client.complete``
- ``tool_call`` → calls ``app.services.mcp_client.invoke_tool``
- ``noop``      → records the node's ``note`` in the output

``approval`` and ``branch`` nodes are recognised but currently raise
``WorkflowDeferredError`` — they need a WorkflowRun model to track
paused state. That's a follow-up.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.anthropic_client import complete
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.connection import Connection
from app.models.ops import Workflow, WorkflowRun, WorkflowRunStatus
from app.services.mcp_client import invoke_tool


_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")


class WorkflowError(RuntimeError):
    pass


class WorkflowDeferredError(WorkflowError):
    """Raised when execution hits a node type that requires a paused
    WorkflowRun model — not yet implemented.
    """


@dataclass
class NodeResult:
    node_id: str
    type: str
    output: Any
    error: str | None = None


@dataclass
class WorkflowRunResult:
    workflow_id: UUID
    completed: bool
    nodes: list[NodeResult] = field(default_factory=list)
    final_context: dict = field(default_factory=dict)
    deferred_reason: str | None = None


# ---------- DSL helpers -----------------------------------------------


def _topological_order(dsl: dict) -> list[dict]:
    """Returns nodes in execution order using Kahn's algorithm."""
    nodes = dsl.get("nodes", [])
    edges = dsl.get("edges", [])
    by_id = {n["id"]: n for n in nodes if "id" in n}

    indegree: dict[str, int] = {nid: 0 for nid in by_id}
    successors: dict[str, list[str]] = {nid: [] for nid in by_id}
    for e in edges:
        src, dst = e.get("from"), e.get("to")
        if src in by_id and dst in by_id:
            indegree[dst] += 1
            successors[src].append(dst)

    ready = [nid for nid, d in indegree.items() if d == 0]
    ordered: list[dict] = []
    while ready:
        nid = ready.pop(0)
        ordered.append(by_id[nid])
        for dst in successors[nid]:
            indegree[dst] -= 1
            if indegree[dst] == 0:
                ready.append(dst)

    if len(ordered) != len(by_id):
        raise WorkflowError(
            f"Workflow has a cycle: {len(ordered)}/{len(by_id)} nodes "
            "reachable. Refusing to run."
        )
    return ordered


def _render(template: str, context: dict) -> str:
    def _replace(m: re.Match) -> str:
        path = m.group(1).split(".")
        cur: Any = context
        for part in path:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return m.group(0)  # leave the {{...}} placeholder
        return str(cur)

    return _VAR_RE.sub(_replace, template)


def _render_value(value: Any, context: dict) -> Any:
    if isinstance(value, str):
        return _render(value, context)
    if isinstance(value, dict):
        return {k: _render_value(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_render_value(v, context) for v in value]
    return value


# ---------- Node runners ----------------------------------------------


async def _run_llm(node: dict, context: dict) -> Any:
    system = _render(node.get("system") or "You are a helpful assistant.", context)
    user = _render(node.get("user_template") or "", context)
    if not user.strip():
        raise WorkflowError(
            f"llm node {node.get('id')!r} has empty user_template"
        )
    text = await complete(system=system, user=user)
    return {"text": text}


async def _run_approval(
    node: dict,
    context: dict,
    *,
    session: AsyncSession,
    workflow: Workflow,
    run_id: UUID | None,
) -> tuple[str, dict | None]:
    """Return value semantics:

      ("filed", {"approval_request_id": ...})  — fresh pause: filed a new
                                                  ApprovalRequest, runner should defer.
      ("approved", {"approval_request_id": ...})  — already-decided approval; runner
                                                  continues with True in context.
      ("rejected", {"approval_request_id": ...})  — decided as rejected; runner
                                                  marks run as failed.

    Resume detection: the runner stores the filed request id in
    ``run.deferred_reason`` as ``approval:<uuid>``. When we re-enter
    this node and that approval is decided we short-circuit.
    """
    request_id_from_reason: UUID | None = None
    if run_id is not None and session is not None:
        run = await session.get(WorkflowRun, run_id)
        if run is not None and run.deferred_reason:
            prefix = "approval:"
            if run.deferred_reason.startswith(prefix):
                try:
                    request_id_from_reason = UUID(
                        run.deferred_reason[len(prefix):]
                    )
                except ValueError:
                    request_id_from_reason = None

    if request_id_from_reason is not None and session is not None:
        req = await session.get(ApprovalRequest, request_id_from_reason)
        if req is not None and req.status == ApprovalStatus.approved:
            return "approved", {"approval_request_id": str(req.id)}
        if req is not None and req.status == ApprovalStatus.rejected:
            return "rejected", {"approval_request_id": str(req.id)}
        # Still pending — fall through to "still waiting"; we don't
        # re-file. Defer again with the same id.
        return "filed", {"approval_request_id": str(request_id_from_reason)}

    # Session-less path (unit tests): defer with a stub id so the
    # caller still sees "this paused" without exploding on .add(None).
    if session is None:
        return "filed", {"approval_request_id": "session-less"}

    # Fresh approval — file a new ApprovalRequest row.
    summary_text = _render(
        node.get("subject_template")
        or f"Approval needed for workflow node {node.get('id')!r}",
        context,
    )
    action_type = node.get("kind") or "workflow.node"
    payload = {
        "workflow_id": str(workflow.id),
        "node_id": node.get("id"),
        "context_snapshot": context,
    }
    req = ApprovalRequest(
        organization_id=workflow.organization_id,
        action_type=action_type,
        summary=summary_text[:255],
        payload_json=payload,
        status=ApprovalStatus.pending,
    )
    session.add(req)
    await session.flush()
    return "filed", {"approval_request_id": str(req.id)}


def _branch_passes(node: dict, context: dict) -> bool:
    """Evaluate a flat ``{var, op, value}`` condition against the context.

    Supported ops: ``eq``, ``neq``, ``gt``, ``gte``, ``lt``, ``lte``,
    ``in``, ``contains``, ``truthy``.
    """
    cond = node.get("condition") or {}
    var = cond.get("var")
    op = cond.get("op", "truthy")
    expected = cond.get("value")
    if var is None:
        return False

    # Dotted-path lookup
    cur: Any = context
    for part in var.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            cur = None
            break
    actual = cur

    if op == "truthy":
        return bool(actual)
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "in" and isinstance(expected, (list, tuple, set)):
        return actual in expected
    if op == "contains" and isinstance(actual, (list, tuple, str)):
        return expected in actual
    if op == "gt" and actual is not None and expected is not None:
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    if op == "gte" and actual is not None and expected is not None:
        try:
            return float(actual) >= float(expected)
        except (TypeError, ValueError):
            return False
    if op == "lt" and actual is not None and expected is not None:
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False
    if op == "lte" and actual is not None and expected is not None:
        try:
            return float(actual) <= float(expected)
        except (TypeError, ValueError):
            return False
    return False


async def _run_tool_call(
    node: dict, context: dict, session: AsyncSession
) -> Any:
    conn_id = node.get("connection_id")
    if not conn_id:
        raise WorkflowError(
            f"tool_call node {node.get('id')!r} missing connection_id"
        )
    conn = await session.get(Connection, UUID(conn_id))
    if conn is None:
        raise WorkflowError(
            f"tool_call node {node.get('id')!r} references missing "
            f"connection {conn_id}"
        )
    tool_name = node.get("tool_name") or ""
    args = _render_value(node.get("arguments_template") or {}, context)
    inv = await invoke_tool(
        connection=conn, tool_name=tool_name, arguments=args
    )
    return {
        "result": inv.result,
        "stub": inv.stub,
        "duration_ms": inv.duration_ms,
    }


# ---------- public entry ----------------------------------------------


async def run_workflow(
    *,
    workflow: Workflow,
    initial_context: dict,
    session: AsyncSession,
    skip_node_ids: set[str] | None = None,
    run_id: UUID | None = None,
) -> WorkflowRunResult:
    """Executes the workflow, returning per-node results + the
    accumulated context.

    Args:
        workflow: the workflow definition.
        initial_context: starting dict; node outputs are merged in.
        session: AsyncSession used by tool_call nodes.
        skip_node_ids: when resuming, IDs of nodes already completed
            in a previous attempt. They are skipped (output assumed to
            already be in ``initial_context``).
        run_id: optional WorkflowRun id, used by approval nodes to
            persist + retrieve the filed ApprovalRequest id across
            pauses.

    Raises ``WorkflowError`` for cycles or per-node config errors. Hits
    an unresolved approval / wait / webhook_listener → returns a
    result with ``completed=False`` and ``deferred_reason`` set.
    """
    dsl = workflow.dsl_json or {}
    ordered = _topological_order(dsl)
    skip = skip_node_ids or set()

    context: dict = dict(initial_context)
    nodes_out: list[NodeResult] = []

    for node in ordered:
        if node["id"] in skip:
            continue
        ntype = node.get("type", "noop")
        out_var = node.get("output_var") or node["id"]

        try:
            if ntype == "llm":
                out = await _run_llm(node, context)
            elif ntype == "tool_call":
                out = await _run_tool_call(node, context, session)
            elif ntype == "noop":
                out = {"note": node.get("note")}
            elif ntype == "approval":
                outcome, meta = await _run_approval(
                    node, context,
                    session=session, workflow=workflow, run_id=run_id,
                )
                if outcome == "filed":
                    nodes_out.append(
                        NodeResult(
                            node_id=node["id"], type=ntype, output=meta
                        )
                    )
                    return WorkflowRunResult(
                        workflow_id=workflow.id,
                        completed=False,
                        nodes=nodes_out,
                        final_context=context,
                        deferred_reason=(
                            f"approval:{meta['approval_request_id']}"
                        ),
                    )
                if outcome == "rejected":
                    nodes_out.append(
                        NodeResult(
                            node_id=node["id"], type=ntype, output=meta,
                            error="rejected",
                        )
                    )
                    return WorkflowRunResult(
                        workflow_id=workflow.id,
                        completed=False,
                        nodes=nodes_out,
                        final_context=context,
                        deferred_reason=(
                            f"approval rejected: {meta['approval_request_id']}"
                        ),
                    )
                # approved
                out = {"approved": True, **meta}
            elif ntype == "branch":
                passed = _branch_passes(node, context)
                out = {"passed": passed}
            elif ntype in ("wait", "webhook_listener"):
                return WorkflowRunResult(
                    workflow_id=workflow.id,
                    completed=False,
                    nodes=nodes_out,
                    final_context=context,
                    deferred_reason=(
                        f"Node type '{ntype}' requires polling /  "
                        "event-listener infrastructure — not yet implemented."
                    ),
                )
            else:
                raise WorkflowError(
                    f"Unknown node type {ntype!r} on node {node.get('id')!r}"
                )
        except WorkflowError:
            raise
        except Exception as exc:
            nodes_out.append(
                NodeResult(
                    node_id=node["id"],
                    type=ntype,
                    output=None,
                    error=str(exc),
                )
            )
            return WorkflowRunResult(
                workflow_id=workflow.id,
                completed=False,
                nodes=nodes_out,
                final_context=context,
                deferred_reason=f"Node {node['id']!r} raised: {exc}",
            )

        context[out_var] = out
        nodes_out.append(
            NodeResult(node_id=node["id"], type=ntype, output=out)
        )

    return WorkflowRunResult(
        workflow_id=workflow.id,
        completed=True,
        nodes=nodes_out,
        final_context=context,
    )


async def resume_workflow_run(
    *,
    run_id: UUID,
    session: AsyncSession,
) -> WorkflowRunResult:
    """Re-enter a paused WorkflowRun. When the deferred condition has
    resolved (e.g. the ApprovalRequest is now approved or rejected),
    pick up from the next node and run to completion / next pause.
    """
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        raise WorkflowError(f"WorkflowRun {run_id} not found.")
    if run.status not in (WorkflowRunStatus.paused, WorkflowRunStatus.running):
        raise WorkflowError(
            f"WorkflowRun {run_id} status={run.status.value}; not resumable."
        )
    workflow = await session.get(Workflow, run.workflow_id)
    if workflow is None:
        raise WorkflowError(
            f"WorkflowRun {run_id} references missing Workflow {run.workflow_id}"
        )

    # Nodes that already completed (no error) are skipped.
    skip = {
        (r.get("node_id") if isinstance(r, dict) else r.node_id)
        for r in (run.node_results or [])
        if (
            r.get("error") is None
            if isinstance(r, dict)
            else r.error is None
        )
    }
    # The deferred node — the last entry without a real output — is
    # NOT in skip, so it'll be re-tried (the approval handler short-
    # circuits when the request is decided).
    last_pending = None
    if run.node_results:
        last = run.node_results[-1] if run.node_results else None
        if last is not None:
            last_pending = (
                last.get("node_id")
                if isinstance(last, dict)
                else last.node_id
            )
    if last_pending:
        skip.discard(last_pending)

    return await run_workflow(
        workflow=workflow,
        initial_context=run.final_context or run.initial_context or {},
        session=session,
        skip_node_ids=skip,
        run_id=run_id,
    )


__all__ = [
    "run_workflow",
    "resume_workflow_run",
    "WorkflowRunResult",
    "NodeResult",
    "WorkflowError",
    "WorkflowDeferredError",
]
