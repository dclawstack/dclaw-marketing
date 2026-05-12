"""Phase 10.4 — WorkflowRun model unit tests.

Endpoint-level tests live under the integration suite (require the
auth + memberships setup from conftest). Here we just exercise the
model's persistence shape.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.ops import (
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStatus,
)
from app.models.organization import Organization


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _org(s: Session) -> Organization:
    o = Organization(slug=f"o-{uuid4().hex[:8]}", name="T", is_external=False)
    s.add(o)
    s.commit()
    s.refresh(o)
    return o


def _workflow(s: Session, org_id, dsl: dict | None = None) -> Workflow:
    wf = Workflow(
        organization_id=org_id,
        slug=f"wf-{uuid4().hex[:8]}",
        name="Test workflow",
        dsl_json=dsl or {"nodes": [], "edges": []},
        status=WorkflowStatus.active,
    )
    s.add(wf)
    s.commit()
    s.refresh(wf)
    return wf


def test_run_defaults_to_pending(session: Session):
    org = _org(session)
    wf = _workflow(session, org.id)
    run = WorkflowRun(
        workflow_id=wf.id,
        organization_id=org.id,
        initial_context={"x": 1},
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.status == WorkflowRunStatus.pending
    assert run.initial_context == {"x": 1}
    assert run.final_context is None
    assert run.node_results is None
    assert run.deferred_reason is None
    assert run.error_message is None
    assert run.started_at is not None
    assert run.completed_at is None


def test_run_stores_terminal_state(session: Session):
    org = _org(session)
    wf = _workflow(session, org.id)
    run = WorkflowRun(
        workflow_id=wf.id,
        organization_id=org.id,
        initial_context={},
        status=WorkflowRunStatus.completed,
        final_context={"a": {"text": "hello"}},
        node_results=[
            {"node_id": "a", "type": "llm", "output": {"text": "hello"}, "error": None}
        ],
        completed_at=datetime.now(tz=timezone.utc),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.status == WorkflowRunStatus.completed
    assert run.final_context["a"]["text"] == "hello"
    assert run.node_results[0]["node_id"] == "a"


def test_run_paused_state(session: Session):
    org = _org(session)
    wf = _workflow(session, org.id)
    run = WorkflowRun(
        workflow_id=wf.id,
        organization_id=org.id,
        initial_context={},
        status=WorkflowRunStatus.paused,
        deferred_reason="Node 'b' is type 'approval' — needs WorkflowRun resume",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.status == WorkflowRunStatus.paused
    assert "approval" in run.deferred_reason



def test_status_enum_round_trip(session: Session):
    org = _org(session)
    wf = _workflow(session, org.id)
    for s in WorkflowRunStatus:
        run = WorkflowRun(
            workflow_id=wf.id,
            organization_id=org.id,
            initial_context={},
            status=s,
        )
        session.add(run)
    session.commit()
    rows = session.execute(select(WorkflowRun)).scalars().all()
    statuses = {r.status for r in rows}
    assert statuses == set(WorkflowRunStatus)
