"""SEO site audit — wraps the Ahrefs MCP `site_audit` tool, persists each
finding as an AuditEvent row so it shows up in the audit trail and can
be queried by the dashboard.

A "finding" is a categorized issue: broken_link, missing_meta_description,
thin_content, slow_page, etc. The Ahrefs adapter returns a `findings`
list under its result dict — we fan that out into one AuditEvent per item.

If no Ahrefs Connection exists (or the adapter falls back to its stub),
the stub still returns a stable shape so the audit task remains useful
in dev / CI.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.services.mcp.ahrefs import site_audit


ACTION_AUDIT_FINDING = "seo.audit_finding"
ACTION_AUDIT_RUN = "seo.audit_run"


async def run_site_audit(
    session: AsyncSession,
    *,
    organization_id: UUID,
    domain: str,
) -> dict[str, Any]:
    """Run one site_audit pass for ``domain`` and persist the findings.

    Returns a dict with ``domain``, ``findings_count``, ``stub`` (bool
    from the MCP layer), and ``findings`` (the raw list — useful for
    API callers that want to render the result immediately).
    """
    res = await site_audit(session, organization_id=organization_id, domain=domain)

    raw = res.result if isinstance(res.result, dict) else {}
    findings = raw.get("findings") or []
    if not isinstance(findings, list):
        findings = []

    # One run-marker (so we can count how many audits we've done even
    # when a particular run had zero findings).
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_kind=AuditActorKind.system,
            actor_agent="seo_agent",
            action_type=ACTION_AUDIT_RUN,
            target_type="domain",
            target_id=domain[:64],
            payload_json={
                "domain": domain,
                "findings_count": len(findings),
                "stub": res.stub,
                "duration_ms": res.duration_ms,
            },
            result=AuditResult.success,
        )
    )

    # Fan out per finding so each shows up individually in /audit logs.
    for f in findings:
        if not isinstance(f, dict):
            continue
        session.add(
            AuditEvent(
                organization_id=organization_id,
                actor_kind=AuditActorKind.system,
                actor_agent="seo_agent",
                action_type=ACTION_AUDIT_FINDING,
                target_type="url",
                target_id=str(f.get("url") or domain)[:64],
                payload_json={
                    "domain": domain,
                    "kind": f.get("kind"),          # broken_link / missing_meta / thin / slow / …
                    "severity": f.get("severity"),  # low / medium / high
                    "url": f.get("url"),
                    "detail": f.get("detail"),
                    "stub": res.stub,
                },
                result=AuditResult.success,
            )
        )

    await session.flush()
    return {
        "domain": domain,
        "findings_count": len(findings),
        "stub": res.stub,
        "findings": findings,
    }


async def list_audit_findings(
    session: AsyncSession,
    *,
    organization_id: UUID,
    domain: str | None = None,
    days: int = 30,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return the most-recent SEO findings for an Org (optionally filtered
    by domain). Used by the GET endpoint + the dashboard.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.organization_id == organization_id,
            AuditEvent.action_type == ACTION_AUDIT_FINDING,
            AuditEvent.created_at >= cutoff,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(int(limit))
    )
    rows = (await session.execute(stmt)).scalars().all()
    out: list[dict[str, Any]] = []
    for ev in rows:
        payload = ev.payload_json or {}
        if domain and payload.get("domain") != domain:
            continue
        out.append(
            {
                "id": str(ev.id),
                "created_at": ev.created_at.isoformat(),
                "domain": payload.get("domain"),
                "kind": payload.get("kind"),
                "severity": payload.get("severity"),
                "url": payload.get("url"),
                "detail": payload.get("detail"),
                "stub": payload.get("stub", False),
            }
        )
    return out


__all__ = [
    "ACTION_AUDIT_FINDING",
    "ACTION_AUDIT_RUN",
    "run_site_audit",
    "list_audit_findings",
]
