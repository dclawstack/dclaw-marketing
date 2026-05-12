"""SEO Agent beat tasks — Theme H.

Two periodic sweeps:

  * ``daily_seo_audit`` — for every Org that has an ``seo.domain``
    configured under ``Organization.constraints_json``, run a site
    audit via the Ahrefs MCP adapter. Findings persist as AuditEvent
    rows (action_type=``seo.audit_finding``).
  * ``daily_ranking_snapshot`` — for every Org with a non-empty
    ``seo.tracked_keywords`` list, snapshot SERP positions so the
    ranking-delta tracker can compare over time.

Both tasks gracefully handle missing config (skip Org) and missing
MCP connections (the adapter returns a stub result; we still
persist).
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine
from app.models.organization import Organization
from app.services.seo.audit import run_site_audit
from app.services.seo.ranking_delta import snapshot_keyword_positions
from app.worker.celery_app import celery_app


def _seo_config(org: Organization) -> dict[str, Any]:
    """Return the ``seo`` slice of constraints_json, or an empty dict."""
    cfg = (org.constraints_json or {}).get("seo")
    return cfg if isinstance(cfg, dict) else {}


async def _run_daily_seo_audit() -> dict[str, Any]:
    audited = 0
    findings = 0
    async with AsyncSession(engine, expire_on_commit=False) as session:
        orgs = (await session.execute(select(Organization))).scalars().all()
        for org in orgs:
            cfg = _seo_config(org)
            domain = cfg.get("domain")
            if not domain or not isinstance(domain, str):
                continue
            try:
                summary = await run_site_audit(
                    session, organization_id=org.id, domain=domain
                )
                findings += int(summary.get("findings_count") or 0)
                audited += 1
            except Exception:  # pragma: no cover — keep the sweep going
                continue
        await session.commit()
    return {"orgs_audited": audited, "total_findings": findings}


async def _run_daily_ranking_snapshot() -> dict[str, Any]:
    orgs_snapped = 0
    keywords_snapped = 0
    async with AsyncSession(engine, expire_on_commit=False) as session:
        orgs = (await session.execute(select(Organization))).scalars().all()
        for org in orgs:
            cfg = _seo_config(org)
            kws = cfg.get("tracked_keywords")
            if not isinstance(kws, list) or not kws:
                continue
            country = cfg.get("country") or "us"
            domain = cfg.get("domain")
            try:
                summary = await snapshot_keyword_positions(
                    session,
                    organization_id=org.id,
                    keywords=[k for k in kws if isinstance(k, str)],
                    country=country,
                    own_domain=domain,
                )
                orgs_snapped += 1
                keywords_snapped += len(summary.get("snapshots") or [])
            except Exception:  # pragma: no cover
                continue
        await session.commit()
    return {"orgs_snapshotted": orgs_snapped, "keywords_snapshotted": keywords_snapped}


@celery_app.task(name="app.worker.tasks.seo.daily_seo_audit")
def daily_seo_audit() -> dict[str, Any]:
    return asyncio.run(_run_daily_seo_audit())


@celery_app.task(name="app.worker.tasks.seo.daily_ranking_snapshot")
def daily_ranking_snapshot() -> dict[str, Any]:
    return asyncio.run(_run_daily_ranking_snapshot())


__all__ = ["daily_seo_audit", "daily_ranking_snapshot"]
