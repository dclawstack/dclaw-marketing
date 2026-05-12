"""Phase 10.x — WorkflowRun resume + approval/branch nodes tests."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.ops import (
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStatus,
)
from app.models.organization import Organization
from app.services.workflow_runner import (
    _branch_passes,
    resume_workflow_run,
    run_workflow,
)
from tests.conftest import test_engine


# ---------- Pure branch helper -------------------------------------------


def test_branch_truthy_default():
    assert _branch_passes({"condition": {"var": "x"}}, {"x": "non-empty"})
    assert not _branch_passes({"condition": {"var": "x"}}, {"x": ""})


def test_branch_gte_lte_numeric():
    n = {"condition": {"var": "score", "op": "gte", "value": 60}}
    assert _branch_passes(n, {"score": 60})
    assert _branch_passes(n, {"score": 99})
    assert not _branch_passes(n, {"score": 59})


def test_branch_eq_string():
    n = {"condition": {"var": "stage", "op": "eq", "value": "mql"}}
    assert _branch_passes(n, {"stage": "mql"})
    assert not _branch_passes(n, {"stage": "sql"})


def test_branch_in_list():
    n = {
        "condition": {
            "var": "channel",
            "op": "in",
            "value": ["linkedin", "x"],
        }
    }
    assert _branch_passes(n, {"channel": "linkedin"})
    assert not _branch_passes(n, {"channel": "bluesky"})


def test_branch_dotted_path():
    n = {"condition": {"var": "lead.score", "op": "gte", "value": 50}}
    assert _branch_passes(n, {"lead": {"score": 75}})
    assert not _branch_passes(n, {"lead": {"score": 25}})


def test_branch_missing_var_returns_false():
    n = {"condition": {"var": "nope", "op": "eq", "value": "x"}}
    assert not _branch_passes(n, {})


# ---------- End-to-end approval + resume ---------------------------------


async def _seed_workflow(
    *, dsl: dict, slug: str = "wfres"
) -> tuple[Organization, Workflow]:
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug=slug, name="WFR")
        session.add(org)
        await session.flush()
        wf = Workflow(
            organization_id=org.id,
            name="Test Workflow",
            description="approval-then-noop test",
            status=WorkflowStatus.published,
            dsl_json=dsl,
        )
        session.add(wf)
        await session.commit()
        await session.refresh(org)
        await session.refresh(wf)
        return org, wf


@pytest.mark.asyncio
async def test_approval_node_pauses_then_resumes_when_approved():
    dsl = {
        "nodes": [
            {
                "id": "ask",
                "type": "approval",
                "subject_template": "Approve the post",
                "kind": "post.publish",
            },
            {"id": "done", "type": "noop", "note": "post published"},
        ],
        "edges": [{"from": "ask", "to": "done"}],
    }
    org, wf = await _seed_workflow(dsl=dsl)

    # Create a WorkflowRun row up front (mirrors the route's flow).
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        run = WorkflowRun(
            workflow_id=wf.id,
            organization_id=org.id,
            initial_context={},
            status=WorkflowRunStatus.running,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

        # First pass — should pause at the approval node.
        result = await run_workflow(
            workflow=wf,
            initial_context={},
            session=session,
            run_id=run.id,
        )
        assert not result.completed
        assert result.deferred_reason and result.deferred_reason.startswith(
            "approval:"
        )
        # Persist the deferred state on the run row (so resume can find it).
        run.status = WorkflowRunStatus.paused
        run.deferred_reason = result.deferred_reason
        run.node_results = [
            {
                "node_id": n.node_id,
                "type": n.type,
                "output": n.output,
                "error": n.error,
            }
            for n in result.nodes
        ]
        run.final_context = result.final_context
        await session.commit()
        approval_id = result.deferred_reason.split(":", 1)[1]
        run_id = run.id

    # Reviewer approves the request.
    from uuid import UUID

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        req = await session.get(ApprovalRequest, UUID(approval_id))
        assert req is not None
        req.status = ApprovalStatus.approved
        await session.commit()

    # Second pass — runner resumes, sees approved, finishes.
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        result2 = await resume_workflow_run(
            run_id=run_id, session=session
        )
        assert result2.completed
        # Approval node + done node both produced output now.
        node_ids = [n.node_id for n in result2.nodes]
        assert "done" in node_ids


@pytest.mark.asyncio
async def test_approval_rejected_marks_run_failed_path():
    dsl = {
        "nodes": [
            {"id": "ask", "type": "approval"},
            {"id": "done", "type": "noop"},
        ],
        "edges": [{"from": "ask", "to": "done"}],
    }
    org, wf = await _seed_workflow(dsl=dsl, slug="wfrej")

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        run = WorkflowRun(
            workflow_id=wf.id,
            organization_id=org.id,
            initial_context={},
            status=WorkflowRunStatus.running,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

        first = await run_workflow(
            workflow=wf,
            initial_context={},
            session=session,
            run_id=run.id,
        )
        assert not first.completed
        run.status = WorkflowRunStatus.paused
        run.deferred_reason = first.deferred_reason
        run.node_results = [
            {
                "node_id": n.node_id,
                "type": n.type,
                "output": n.output,
                "error": n.error,
            }
            for n in first.nodes
        ]
        run.final_context = first.final_context
        await session.commit()
        approval_id = first.deferred_reason.split(":", 1)[1]
        run_id = run.id

    from uuid import UUID

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        req = await session.get(ApprovalRequest, UUID(approval_id))
        req.status = ApprovalStatus.rejected
        await session.commit()

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        result2 = await resume_workflow_run(run_id=run_id, session=session)
        assert not result2.completed
        assert "rejected" in (result2.deferred_reason or "")
        # The "done" node should NOT have run.
        assert all(n.node_id != "done" for n in result2.nodes)
