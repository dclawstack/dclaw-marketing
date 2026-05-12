"""Q2 live input-channel pollers — Phase 2.x.

Four periodic Celery beat tasks that surface new content from
external workspaces so the KG stays current:

  • ``poll_notion_workspaces``  — for every org with a notion
    Connection, search recent pages and write audit rows so the
    Knowledge Console UI can offer them as 'available for ingestion'
    candidates.
  • ``poll_google_drive_folders`` — same shape for Drive folders.
  • ``poll_git_repos`` — re-ingest git IngestionSource rows whose
    head sha may have moved. For v1 this is a thin wrapper around
    the existing freshness path with a shorter cadence (4h vs 7d).
  • ``poll_website_crawls`` — re-fetch URL IngestionSource rows on
    a 24h cadence (the Q4 freshness task already does this weekly;
    this poller targets sources marked ``high_frequency`` via the
    metadata_json flag).

Real ingestion of the surfaced items is left to the existing
ingestion pipeline + the Knowledge Console UI follow-up. This task
shipses the *poll* loop + audit trail; the user / agent picks which
items to actually ingest.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine
from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.connection import Connection, ConnectionStatus
from app.models.ingestion import (
    IngestionSource,
    IngestionSourceType,
    IngestionStatus,
)
from app.models.organization import Organization
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


_NOTION_SERVER = "notion"
_DRIVE_SERVER = "google_drive"


# ---------- Notion + Drive (MCP-backed pollers) ---------------------------


async def _poll_notion_org(session: AsyncSession, conn: Connection) -> int:
    """Calls the Notion MCP search for recent pages; writes one
    AuditEvent per page surfaced (capped at 10 to avoid runaway
    logs). Returns the count surfaced."""
    from app.services.mcp import notion as notion_mcp

    res = await notion_mcp.search(
        session,
        organization_id=conn.organization_id,
        query="",  # empty query lists recent pages
        limit=10,
    )
    payload = res.result if isinstance(res.result, dict) else {}
    results = payload.get("results") or payload.get("data") or []
    if not isinstance(results, list):
        results = []
    for item in results[:10]:
        session.add(
            AuditEvent(
                organization_id=conn.organization_id,
                actor_kind=AuditActorKind.system,
                action_type="poller.notion.page_seen",
                target_type="notion_page",
                target_id=str(item.get("id") or "")[:64],
                payload_json={
                    "title": item.get("title")
                    or (item.get("properties") or {}).get("title"),
                    "stub": res.stub,
                },
                result=AuditResult.success,
            )
        )
    return len(results)


async def _poll_drive_org(session: AsyncSession, conn: Connection) -> int:
    """Calls Drive MCP list_files for the configured root folder and
    writes one AuditEvent per file surfaced (cap 20)."""
    from app.services.mcp import google_drive as drive_mcp

    folder_id = (conn.metadata_json or {}).get("root_folder_id")
    res = await drive_mcp.list_files(
        session,
        organization_id=conn.organization_id,
        folder_id=folder_id,
        page_size=20,
    )
    payload = res.result if isinstance(res.result, dict) else {}
    files = payload.get("files") or []
    if not isinstance(files, list):
        files = []
    for f in files[:20]:
        session.add(
            AuditEvent(
                organization_id=conn.organization_id,
                actor_kind=AuditActorKind.system,
                action_type="poller.drive.file_seen",
                target_type="drive_file",
                target_id=str(f.get("id") or "")[:64],
                payload_json={
                    "name": f.get("name"),
                    "mime_type": f.get("mimeType"),
                    "stub": res.stub,
                },
                result=AuditResult.success,
            )
        )
    return len(files)


async def _poll_mcp_server(server_id: str) -> dict:
    """Common driver — iterate active Org connections for ``server_id``,
    call the per-server poller. Async session per Org so a single
    failing call doesn't poison the whole sweep."""
    counts = {"servers_scanned": 0, "items_surfaced": 0}
    async with AsyncSession(engine, expire_on_commit=False) as session:
        rows = (
            await session.execute(
                select(Connection).where(
                    Connection.server_id == server_id,
                    Connection.status == ConnectionStatus.active,
                )
            )
        ).scalars().all()
    for conn in rows:
        try:
            async with AsyncSession(engine, expire_on_commit=False) as s:
                if server_id == _NOTION_SERVER:
                    n = await _poll_notion_org(s, conn)
                elif server_id == _DRIVE_SERVER:
                    n = await _poll_drive_org(s, conn)
                else:
                    n = 0
                await s.commit()
                counts["items_surfaced"] += n
            counts["servers_scanned"] += 1
        except Exception:  # pragma: no cover — keep sweeping
            continue
    return counts


@celery_app.task(name="app.worker.tasks.live_pollers.poll_notion_workspaces")
def poll_notion_workspaces() -> dict:
    return asyncio.run(_poll_mcp_server(_NOTION_SERVER))


@celery_app.task(
    name="app.worker.tasks.live_pollers.poll_google_drive_folders"
)
def poll_google_drive_folders() -> dict:
    return asyncio.run(_poll_mcp_server(_DRIVE_SERVER))


# ---------- URL + git pollers (sync, reuse ingestion path) ----------------


def _requeue_sources(
    *, source_type: IngestionSourceType, stale_after: timedelta
) -> int:
    """Flip ready IngestionSource rows older than ``stale_after`` back
    to ``queued`` so the existing ingestion worker re-fetches them."""
    cutoff = datetime.now(tz=timezone.utc) - stale_after
    refreshed = 0
    with SyncSession() as session:
        rows = (
            session.execute(
                select(IngestionSource).where(
                    IngestionSource.source_type == source_type,
                    IngestionSource.status == IngestionStatus.ready,
                    IngestionSource.updated_at < cutoff,
                )
            )
            .scalars()
            .all()
        )
        for src in rows:
            src.status = IngestionStatus.queued
            src.error_message = None
            refreshed += 1
        session.commit()

    if refreshed:
        from app.worker.tasks.ingestion import process_ingestion_source

        with SyncSession() as session:
            queued = (
                session.execute(
                    select(IngestionSource.id).where(
                        IngestionSource.status == IngestionStatus.queued,
                        IngestionSource.source_type == source_type,
                    )
                )
            ).all()
            for (sid,) in queued:
                try:
                    process_ingestion_source.delay(str(sid))
                except Exception:  # pragma: no cover — broker offline
                    pass
    return refreshed


@celery_app.task(name="app.worker.tasks.live_pollers.poll_git_repos")
def poll_git_repos() -> dict:
    """Every 4 hours, re-queue git IngestionSource rows older than 4h
    so README + docs/ changes flow through to the KG without waiting
    for the Q4 weekly sweep."""
    n = _requeue_sources(
        source_type=IngestionSourceType.git,
        stale_after=timedelta(hours=4),
    )
    return {"refreshed": n}


@celery_app.task(name="app.worker.tasks.live_pollers.poll_website_crawls")
def poll_website_crawls() -> dict:
    """Every 24h, re-queue url IngestionSource rows older than 24h.
    The Q4 weekly task still owns the long-tail; this task targets
    the fast-moving subset (typically the customer's landing pages
    and pricing page)."""
    n = _requeue_sources(
        source_type=IngestionSourceType.url,
        stale_after=timedelta(hours=24),
    )
    return {"refreshed": n}


__all__ = [
    "poll_notion_workspaces",
    "poll_google_drive_folders",
    "poll_git_repos",
    "poll_website_crawls",
]
