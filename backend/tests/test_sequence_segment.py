"""Phase 7.x — sequence runner + segment materializer tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.worker.tasks.segments import lead_matches_filter


# ---------- Segment filter DSL --------------------------------------------


def test_empty_filter_matches_everyone():
    lead = SimpleNamespace(stage="mql", score=80, company="Acme")
    assert lead_matches_filter(lead, {})
    assert lead_matches_filter(lead, None)


def test_exact_match_eq():
    lead = SimpleNamespace(stage="mql", score=80)
    assert lead_matches_filter(lead, {"stage": "mql"})
    assert not lead_matches_filter(lead, {"stage": "sql"})


def test_numeric_gte_lte():
    lead = SimpleNamespace(score=75, stage="mql")
    assert lead_matches_filter(lead, {"score__gte": 60})
    assert lead_matches_filter(lead, {"score__lte": 100})
    assert not lead_matches_filter(lead, {"score__gte": 80})


def test_in_list():
    lead = SimpleNamespace(stage="sql", domain="acme.co")
    assert lead_matches_filter(
        lead, {"stage__in": ["mql", "sql", "customer"]}
    )
    assert not lead_matches_filter(lead, {"stage__in": ["visitor"]})


def test_contains_substring():
    lead = SimpleNamespace(company="Acme Industries", stage="mql")
    assert lead_matches_filter(lead, {"company__contains": "Industries"})
    assert not lead_matches_filter(lead, {"company__contains": "Zzz"})


def test_startswith_endswith():
    lead = SimpleNamespace(domain="acme.co", stage="mql")
    assert lead_matches_filter(lead, {"domain__startswith": "acme"})
    assert lead_matches_filter(lead, {"domain__endswith": ".co"})


def test_any_of_or_clauses():
    lead = SimpleNamespace(stage="sql", score=30)
    f = {
        "any_of": [
            {"stage": "mql"},
            {"stage": "sql"},
        ]
    }
    assert lead_matches_filter(lead, f)
    f2 = {"any_of": [{"stage": "customer"}, {"stage": "churned"}]}
    assert not lead_matches_filter(lead, f2)


def test_combined_and_with_any_of():
    """top-level keys AND'd with any_of."""
    lead = SimpleNamespace(stage="sql", score=85, company="Acme")
    f = {
        "score__gte": 80,
        "any_of": [{"stage": "mql"}, {"stage": "sql"}],
    }
    assert lead_matches_filter(lead, f)
    # Same lead but lower score should fail the AND.
    lead.score = 50
    assert not lead_matches_filter(lead, f)


def test_enum_value_unwrapped():
    """Enum-typed fields are unwrapped to their .value for comparison."""
    enum_like = SimpleNamespace(value="mql")
    lead = SimpleNamespace(stage=enum_like, score=80)
    assert lead_matches_filter(lead, {"stage": "mql"})


def test_neq_operator():
    lead = SimpleNamespace(stage="mql")
    assert lead_matches_filter(lead, {"stage__neq": "sql"})
    assert not lead_matches_filter(lead, {"stage__neq": "mql"})
