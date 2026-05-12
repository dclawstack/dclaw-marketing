"""Anomaly detection — Phase 9 / Analyst Agent.

Pure-function 3σ rolling-baseline detector. Given a list of daily
metric points::

    [(day, value), (day, value), ...]

returns one ``Anomaly`` per point whose value is outside
``mean ± n_std × stdev`` of the rolling window that precedes it.

Used by the Analyst Agent to flag yesterday's metrics against the
preceding two weeks. The narrative generator threads the anomalies
into a Monday-morning summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from statistics import mean, pstdev
from typing import Iterable


@dataclass(frozen=True, slots=True)
class MetricPoint:
    day: date
    value: float


@dataclass(frozen=True, slots=True)
class Anomaly:
    day: date
    value: float
    baseline_mean: float
    baseline_stdev: float
    z_score: float
    direction: str  # "above" | "below"


def detect_anomalies(
    points: Iterable[MetricPoint],
    *,
    window_days: int = 14,
    n_std: float = 3.0,
    min_window_size: int = 7,
) -> list[Anomaly]:
    """Return anomalies (>= n_std away from the rolling-window mean).

    Args:
        points: list of MetricPoints sorted by day ascending. Out-of-
            order input is sorted as a courtesy.
        window_days: how many days back to look. Default 14.
        n_std: z-score threshold. Default 3.
        min_window_size: don't flag anything when the rolling window
            has fewer than this many points. Default 7.
    """
    rows = sorted(points, key=lambda p: p.day)
    anomalies: list[Anomaly] = []
    for i, p in enumerate(rows):
        window = [r.value for r in rows[max(0, i - window_days) : i]]
        if len(window) < min_window_size:
            continue
        mu = mean(window)
        sd = pstdev(window)
        if sd == 0:
            # Constant baseline — only flag if today's value strictly
            # differs (any non-zero delta is anomalous when σ is 0).
            if p.value != mu:
                anomalies.append(
                    Anomaly(
                        day=p.day,
                        value=p.value,
                        baseline_mean=mu,
                        baseline_stdev=0.0,
                        z_score=float("inf"),
                        direction="above" if p.value > mu else "below",
                    )
                )
            continue
        z = (p.value - mu) / sd
        if abs(z) >= n_std:
            anomalies.append(
                Anomaly(
                    day=p.day,
                    value=p.value,
                    baseline_mean=mu,
                    baseline_stdev=sd,
                    z_score=z,
                    direction="above" if z > 0 else "below",
                )
            )
    return anomalies


def render_narrative(
    anomalies: list[Anomaly],
    *,
    metric_label: str,
) -> str:
    """Markdown one-pager for the Monday-morning Analyst report."""
    if not anomalies:
        return (
            f"### {metric_label}\n\n"
            f"No anomalies detected in the rolling window."
        )

    lines = [f"### {metric_label}", ""]
    for a in anomalies:
        delta = a.value - a.baseline_mean
        pct = (
            (delta / a.baseline_mean) * 100.0 if a.baseline_mean else 0.0
        )
        sign = "+" if delta >= 0 else ""
        lines.append(
            f"- **{a.day.isoformat()}** — {a.value:.2f} vs baseline "
            f"{a.baseline_mean:.2f} ({sign}{pct:.1f}%, "
            f"z={a.z_score:.2f}, direction={a.direction})"
        )
    return "\n".join(lines)


__all__ = ["MetricPoint", "Anomaly", "detect_anomalies", "render_narrative"]
