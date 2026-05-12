"""Weekly + monthly client PDF report generator — Phase 10 / M.

Pure-Python HTML emitter — no headless browser dep, no Chrome.
For the v1 cut we emit an HTML report sized for letter-paper print
(which most browsers can render to PDF or send to a real PDF service).
The shape:

  • Cover with org name + period
  • Headline metrics (touchpoints / conversions / revenue)
  • Per-channel breakdown table
  • Top 5 best-performing posts table
  • Footer

Output is a single HTML string; caller persists it to MinIO with a
``.html`` key. A follow-up swaps in WeasyPrint / wkhtmltopdf for true
PDF output when an agency-customer specifically asks.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.attribution import AnalyticsRollup, AttributionModel, AttributionResult
from app.models.organization import Organization
from app.models.scheduled_post import ScheduledPost, ScheduledPostStatus


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Poppins', -apple-system, sans-serif;
  color: #1a1a1a;
  background: #ffffff;
  padding: 48px;
  font-size: 14px;
  line-height: 1.5;
}
.cover {
  border-bottom: 4px solid #7660A8;
  padding-bottom: 24px;
  margin-bottom: 32px;
}
.cover h1 {
  font-size: 36px;
  color: #7660A8;
  margin-bottom: 8px;
}
.cover p { color: #555; font-size: 16px; }
section { margin-bottom: 32px; }
section h2 {
  font-size: 20px;
  color: #1a1a1a;
  margin-bottom: 12px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 6px;
}
.metric-row { display: flex; gap: 16px; margin-bottom: 16px; }
.metric {
  flex: 1;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 16px;
}
.metric .label { color: #777; font-size: 12px; text-transform: uppercase; }
.metric .value { font-size: 28px; font-weight: 600; color: #7660A8; }
table { width: 100%; border-collapse: collapse; }
th, td {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid #eee;
  font-size: 13px;
}
th { background: #f7f5fb; color: #444; font-weight: 600; }
.right { text-align: right; font-family: 'JetBrains Mono', monospace; }
footer { color: #888; font-size: 12px; margin-top: 48px; text-align: center; }
"""


def _fmt_usd(v: float) -> str:
    return f"${v:,.2f}"


def _channel_breakdown(
    session: Session, org_id: UUID, since: datetime, until: datetime
) -> list[tuple[str, float, int]]:
    rows = session.execute(
        select(AttributionResult, ScheduledPost)
        .join(
            ScheduledPost,
            AttributionResult.touchpoint_id == ScheduledPost.id,
            isouter=True,
        )
        .where(
            AttributionResult.organization_id == org_id,
            AttributionResult.model == AttributionModel.linear,
        )
        .limit(500)
    ).all()
    by_channel: dict[str, list[float]] = {}
    for ar, sp in rows:
        channel = sp.channel.value if sp else "unknown"
        by_channel.setdefault(channel, []).append(
            float(ar.credited_amount_usd or 0)
        )
    return [
        (ch, sum(amts), len(amts))
        for ch, amts in sorted(
            by_channel.items(), key=lambda kv: -sum(kv[1])
        )
    ][:10]


def _rollup_totals(
    session: Session, org_id: UUID, since: datetime
) -> dict:
    rows = session.execute(
        select(AnalyticsRollup).where(
            AnalyticsRollup.organization_id == org_id,
            AnalyticsRollup.scope == "org",
            AnalyticsRollup.day >= since,
        )
    ).scalars().all()
    totals = {"touchpoints": 0, "conversions": 0, "revenue_usd": 0.0}
    for r in rows:
        m = r.metric_json or {}
        totals["touchpoints"] += int(m.get("touchpoints", 0) or 0)
        totals["conversions"] += int(m.get("conversions", 0) or 0)
        totals["revenue_usd"] += float(m.get("revenue_usd", 0.0) or 0.0)
    return totals


def _top_posts(
    session: Session, org_id: UUID, since: datetime
) -> list[ScheduledPost]:
    res = session.execute(
        select(ScheduledPost)
        .where(
            ScheduledPost.organization_id == org_id,
            ScheduledPost.status == ScheduledPostStatus.published,
            ScheduledPost.published_at >= since,
        )
        .order_by(desc(ScheduledPost.published_at))
        .limit(5)
    )
    return list(res.scalars().all())


def build_report_html(
    session: Session,
    organization_id: UUID,
    *,
    period_label: str,
    period_days: int,
    now: datetime | None = None,
) -> str:
    clock = now or datetime.now(tz=timezone.utc)
    since = clock - timedelta(days=period_days)
    org = session.get(Organization, organization_id)
    if org is None:
        raise ValueError(f"Organization {organization_id} not found")

    totals = _rollup_totals(session, organization_id, since)
    channels = _channel_breakdown(session, organization_id, since, clock)
    top = _top_posts(session, organization_id, since)

    period_start = since.date().isoformat()
    period_end = clock.date().isoformat()

    chan_rows_html = (
        "".join(
            f"<tr><td>{ch}</td><td class='right'>{_fmt_usd(amt)}</td>"
            f"<td class='right'>{n}</td></tr>"
            for ch, amt, n in channels
        )
        or "<tr><td colspan='3'>No attribution data this period.</td></tr>"
    )
    top_rows_html = (
        "".join(
            f"<tr><td>{p.channel.value}</td>"
            f"<td>{(p.copy or '')[:80].replace('<', '&lt;')}</td>"
            f"<td class='right'>{p.published_at.date().isoformat() if p.published_at else '—'}</td></tr>"
            for p in top
        )
        or "<tr><td colspan='3'>No posts published this period.</td></tr>"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{org.name} — {period_label} report</title>
<style>{_CSS}</style>
</head>
<body>
  <div class="cover">
    <h1>{org.name}</h1>
    <p>{period_label} report · {period_start} → {period_end}</p>
  </div>

  <section>
    <h2>Headline metrics</h2>
    <div class="metric-row">
      <div class="metric">
        <div class="label">Touchpoints</div>
        <div class="value">{totals['touchpoints']:,}</div>
      </div>
      <div class="metric">
        <div class="label">Conversions</div>
        <div class="value">{totals['conversions']:,}</div>
      </div>
      <div class="metric">
        <div class="label">Revenue</div>
        <div class="value">{_fmt_usd(totals['revenue_usd'])}</div>
      </div>
    </div>
  </section>

  <section>
    <h2>Channel breakdown (linear attribution)</h2>
    <table>
      <thead><tr><th>Channel</th><th class="right">Revenue</th><th class="right">Posts</th></tr></thead>
      <tbody>{chan_rows_html}</tbody>
    </table>
  </section>

  <section>
    <h2>Recently published</h2>
    <table>
      <thead><tr><th>Channel</th><th>Copy (truncated)</th><th class="right">Published</th></tr></thead>
      <tbody>{top_rows_html}</tbody>
    </table>
  </section>

  <footer>
    Generated {clock.strftime('%Y-%m-%d %H:%M UTC')} by DClaw Marketing.
  </footer>
</body>
</html>"""


__all__ = ["build_report_html"]
