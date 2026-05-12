"""Phase 10.3 — workflow runner unit tests.

We only exercise the pure DSL pieces (topological order, template
rendering, noop nodes, deferred-type handling). LLM + tool_call nodes
are covered separately under their own services' tests.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio

from app.services.workflow_runner import (
    WorkflowError,
    _render,
    _render_value,
    _topological_order,
    run_workflow,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _workflow(dsl: dict):
    """Workflow-shaped duck — only .id and .dsl_json are read."""
    return SimpleNamespace(id=uuid4(), dsl_json=dsl)


def test_render_substitutes_vars():
    assert _render("hi {{name}}!", {"name": "alice"}) == "hi alice!"


def test_render_keeps_unknown_placeholder():
    assert _render("hi {{name}}!", {}) == "hi {{name}}!"


def test_render_supports_dotted_path():
    ctx = {"node1": {"text": "hello"}}
    assert _render("{{node1.text}} world", ctx) == "hello world"


def test_render_value_walks_nested_structures():
    out = _render_value(
        {"q": "{{brief}}", "limit": 5, "tags": ["t1", "{{topic}}"]},
        {"brief": "Q2 launch", "topic": "ai"},
    )
    assert out == {"q": "Q2 launch", "limit": 5, "tags": ["t1", "ai"]}


def test_topological_order_linear():
    dsl = {
        "nodes": [
            {"id": "a", "type": "noop"},
            {"id": "b", "type": "noop"},
            {"id": "c", "type": "noop"},
        ],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}],
    }
    ordered = _topological_order(dsl)
    assert [n["id"] for n in ordered] == ["a", "b", "c"]


def test_topological_order_detects_cycle():
    dsl = {
        "nodes": [
            {"id": "a", "type": "noop"},
            {"id": "b", "type": "noop"},
        ],
        "edges": [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "a"},
        ],
    }
    with pytest.raises(WorkflowError, match="cycle"):
        _topological_order(dsl)


@pytest.mark.asyncio
async def test_run_workflow_noop_chain():
    wf = _workflow(
        {
            "nodes": [
                {"id": "a", "type": "noop", "note": "first"},
                {"id": "b", "type": "noop", "note": "second"},
            ],
            "edges": [{"from": "a", "to": "b"}],
        }
    )
    result = await run_workflow(
        workflow=wf, initial_context={"x": 1}, session=None  # noqa: not used
    )
    assert result.completed is True
    assert len(result.nodes) == 2
    assert result.final_context["a"] == {"note": "first"}
    assert result.final_context["b"] == {"note": "second"}
    assert result.final_context["x"] == 1


@pytest.mark.asyncio
async def test_run_workflow_defers_on_approval_node():
    wf = _workflow(
        {
            "nodes": [
                {"id": "a", "type": "noop", "note": "ok"},
                {"id": "b", "type": "approval"},
                {"id": "c", "type": "noop", "note": "never runs"},
            ],
            "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}],
        }
    )
    result = await run_workflow(
        workflow=wf, initial_context={}, session=None
    )
    assert result.completed is False
    assert result.deferred_reason is not None
    assert "approval" in result.deferred_reason
    # Only the first node ran; c never executed
    assert [n.node_id for n in result.nodes] == ["a"]


@pytest.mark.asyncio
async def test_run_workflow_unknown_node_type_raises():
    wf = _workflow(
        {
            "nodes": [{"id": "x", "type": "fly_to_moon"}],
            "edges": [],
        }
    )
    with pytest.raises(WorkflowError, match="Unknown node type"):
        await run_workflow(workflow=wf, initial_context={}, session=None)


@pytest.mark.asyncio
async def test_output_var_overrides_default_id():
    wf = _workflow(
        {
            "nodes": [
                {"id": "n1", "type": "noop", "note": "ok", "output_var": "draft"},
            ],
            "edges": [],
        }
    )
    result = await run_workflow(
        workflow=wf, initial_context={}, session=None
    )
    assert result.final_context["draft"] == {"note": "ok"}
    assert "n1" not in result.final_context  # default name suppressed
