"""GDPR data export (Phase 11.3).

On request, packages every row across the platform tied to an
organization into a single JSON file. The org admin can fetch it
from MinIO afterwards — typically to fulfil an Article 15 (right of
access) or Article 20 (data portability) request from a Lead in
their CRM.

Structure of the export::

    {
      "schema_version": 1,
      "exported_at": "...",
      "organization": {...},
      "memberships": [...],
      "projects": [...],
      "brand_kits": [...],
      "personas": [...],
      "campaigns": [...],
      "leads": [...],
      "scheduled_posts": [...],
      "approval_requests": [...],
      "social_accounts": [...],     # access tokens REDACTED
      "connections": [...],         # encrypted blobs REDACTED
      "agent_threads": [...],
      "touchpoints": [...],
      "conversions": [...],
    }

Secrets (OAuth tokens, encrypted Fernet blobs, app passwords) are
always REDACTED — the export is meant to ship to a data subject, not
to be a credential leak.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_thread import AgentMessage, AgentThread
from app.models.approval_request import ApprovalRequest
from app.models.attribution import Conversion, Touchpoint
from app.models.brand_kit import BrandKit, Persona
from app.models.campaign import Campaign
from app.models.connection import Connection
from app.models.lead import Lead
from app.models.organization import Organization, OrganizationMembership
from app.models.project import Project
from app.models.scheduled_post import ScheduledPost
from app.models.social_account import SocialAccount
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


REDACTED = "[REDACTED]"


def _serialize(obj: Any) -> Any:
    """Recursively serialize SQLAlchemy column types to JSON-safe values."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (UUID,)):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return REDACTED  # never leak raw bytes (likely an encrypted blob)
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    # Enum
    if hasattr(obj, "value") and not callable(obj.value):
        return obj.value
    return str(obj)


# Per-model column allowlist or redact list. Default: all columns are
# included; entries here REMOVE or REDACT specific columns.
# Keys here are the DB column names (col.name), NOT the Python
# attribute name — SocialAccount uses an attribute alias for its
# interim_access_token column.
_REDACT_COLUMNS: dict[type, set[str]] = {
    SocialAccount: {"interim_access_token", "auth_metadata_json"},
    Connection: {"encrypted_secret_blob"},
}


def _row_to_dict(row, redact: set[str] | None = None) -> dict:
    redact = redact or set()
    result: dict = {}
    for col in row.__table__.columns:
        name = col.name
        if name in redact:
            result[name] = REDACTED
            continue
        # Use the SQLA mapped attribute name (may differ from column name
        # via the `name=` param on mapped_column).
        attr = getattr(row, name, None)
        result[name] = _serialize(attr)
    return result


def _dump_table(
    session: Session, model: type, organization_id: UUID
) -> list[dict]:
    """Generic dumper for any model that has an ``organization_id`` column."""
    rows = (
        session.execute(
            select(model).where(model.organization_id == organization_id)
        )
        .scalars()
        .all()
    )
    redact = _REDACT_COLUMNS.get(model, set())
    return [_row_to_dict(r, redact) for r in rows]


def build_export(session: Session, organization_id: UUID) -> dict:
    """Builds the export dict. Pure function — no I/O beyond the
    supplied session, so it's directly testable.
    """
    org = session.get(Organization, organization_id)
    if org is None:
        raise ValueError(f"Organization {organization_id} not found.")

    payload: dict = {
        "schema_version": 1,
        "exported_at": datetime.now(tz=timezone.utc).isoformat(),
        "organization": _row_to_dict(org),
        "memberships": _dump_table(session, OrganizationMembership, organization_id),
        "projects": _dump_table(session, Project, organization_id),
        "brand_kits": _dump_table(session, BrandKit, organization_id),
        "personas": [],  # filled below via brand-kit join
        "campaigns": _dump_table(session, Campaign, organization_id),
        "leads": _dump_table(session, Lead, organization_id),
        "scheduled_posts": _dump_table(session, ScheduledPost, organization_id),
        "approval_requests": _dump_table(session, ApprovalRequest, organization_id),
        "social_accounts": _dump_table(session, SocialAccount, organization_id),
        "connections": _dump_table(session, Connection, organization_id),
        "agent_threads": _dump_table(session, AgentThread, organization_id),
        "touchpoints": _dump_table(session, Touchpoint, organization_id),
        "conversions": _dump_table(session, Conversion, organization_id),
    }

    # Personas are child rows of brand_kits; pull them via join.
    bk_ids = [
        bk.id
        for bk in session.execute(
            select(BrandKit).where(BrandKit.organization_id == organization_id)
        )
        .scalars()
        .all()
    ]
    if bk_ids:
        payload["personas"] = [
            _row_to_dict(p)
            for p in session.execute(
                select(Persona).where(Persona.brand_kit_id.in_(bk_ids))
            )
            .scalars()
            .all()
        ]

    # Agent messages are child rows of agent_threads; pull them too.
    thread_ids = [t["id"] for t in payload["agent_threads"]]
    if thread_ids:
        payload["agent_messages"] = [
            _row_to_dict(m)
            for m in session.execute(
                select(AgentMessage).where(AgentMessage.thread_id.in_(thread_ids))
            )
            .scalars()
            .all()
        ]
    else:
        payload["agent_messages"] = []

    return payload


@celery_app.task(name="app.worker.tasks.gdpr.export_organization_data")
def export_organization_data(
    organization_id: str,
    *,
    request_id: str | None = None,
) -> dict:
    """Celery task entry point.

    Builds the JSON payload via ``build_export``, uploads it to the
    MinIO object store under ``gdpr-exports/<org>/<request_id>.json``,
    and updates the ``DataExportRequest`` row with the storage key +
    expires_at (7 days). Returns a summary dict.

    When ``request_id`` is None, the export still runs but isn't
    persisted — useful for in-band tests + ad-hoc tooling.
    """
    from datetime import timedelta

    from app.models.ops import DataExportRequest, DataExportStatus
    from app.services.storage import sync_s3_client

    org_uuid = UUID(organization_id)
    started_at = datetime.now(tz=timezone.utc)

    req_uuid = UUID(request_id) if request_id else None
    with SyncSession() as session:
        # Mark running.
        if req_uuid is not None:
            req = session.get(DataExportRequest, req_uuid)
            if req is not None:
                req.status = DataExportStatus.running
                session.commit()

        payload = build_export(session, org_uuid)

    body = json.dumps(payload, default=str).encode("utf-8")
    size = len(body)

    storage_key: str | None = None
    error: str | None = None
    if req_uuid is not None:
        # Upload to MinIO. We use the sync client so we can run in this
        # Celery worker context.
        storage_key = (
            f"gdpr-exports/{organization_id}/{request_id}.json"
        )
        try:
            from app.core.config import settings as _settings

            client = sync_s3_client()
            client.put_object(
                Bucket=_settings.s3_bucket,
                Key=storage_key,
                Body=body,
                ContentType="application/json",
            )
        except Exception as exc:  # pragma: no cover — surfaced via row
            error = str(exc)
            storage_key = None

        # Update the request row.
        with SyncSession() as session:
            req = session.get(DataExportRequest, req_uuid)
            if req is not None:
                if error or storage_key is None:
                    req.status = DataExportStatus.failed
                    req.error_message = error or "no storage key"
                else:
                    req.status = DataExportStatus.ready
                    req.storage_key = storage_key
                    req.expires_at = started_at + timedelta(days=7)
                req.completed_at = datetime.now(tz=timezone.utc)
                session.commit()

    counts = {
        k: len(v) for k, v in payload.items() if isinstance(v, list)
    }
    return {
        "organization_id": organization_id,
        "request_id": request_id,
        "storage_key": storage_key,
        "exported_at": payload["exported_at"],
        "counts": counts,
        "size_bytes": size,
        "error": error,
    }
