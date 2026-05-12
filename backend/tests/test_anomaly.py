"""Phase 9 / Analyst — 3σ anomaly detector + narrative rendering."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.anomaly import (
    Anomaly,
    MetricPoint,
    detect_anomalies,
    render_narrative,
)


def _series(values: list[float], start: date = date(2026, 5, 1)) -> list[MetricPoint]:
    return [
        MetricPoint(day=start + timedelta(days=i), value=v)
        for i, v in enumerate(values)
    ]


def test_no_anomaly_within_normal_range():
    pts = _series([10, 11, 10, 12, 11, 10, 11, 10, 11, 12])
    assert detect_anomalies(pts) == []


def test_detects_above_3sigma_spike():
    # 9 quiet days then a huge spike.
    values = [10] * 9 + [10_000]
    anoms = detect_anomalies(_series(values))
    assert len(anoms) == 1
    assert anoms[0].direction == "above"
    assert anoms[0].value == 10_000.0
    assert anoms[0].day == date(2026, 5, 10)


def test_detects_below_3sigma_drop():
    values = [100] * 9 + [0]
    anoms = detect_anomalies(_series(values))
    assert len(anoms) == 1
    assert anoms[0].direction == "below"


def test_skips_until_min_window_reached():
    # Only 5 points — below default min_window_size=7.
    values = [10, 10, 10, 10, 100]
    anoms = detect_anomalies(_series(values))
    assert anoms == []


def test_constant_baseline_flags_any_deviation():
    values = [42] * 9 + [43]
    anoms = detect_anomalies(_series(values))
    assert len(anoms) == 1
    assert anoms[0].direction == "above"
    assert anoms[0].baseline_stdev == 0.0


def test_render_narrative_when_no_anomalies():
    md = render_narrative([], metric_label="leads")
    assert "leads" in md
    assert "No anomalies" in md


def test_render_narrative_includes_each_anomaly():
    a = Anomaly(
        day=date(2026, 5, 10),
        value=200,
        baseline_mean=100,
        baseline_stdev=5,
        z_score=20.0,
        direction="above",
    )
    md = render_narrative([a], metric_label="leads")
    assert "2026-05-10" in md
    assert "above" in md
    assert "200" in md
    assert "100" in md
