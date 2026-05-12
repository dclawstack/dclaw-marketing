"""Theme D4 — generic webhook receiver + Automation rules.

Three concerns in one router:

  /api/v1/webhooks               — admin CRUD over the registered
                                   Webhook list (one row per external
                                   system → DClaw inbound endpoint).
  /api/v1/automations            — admin CRUD over Automation rules.
  /api/v1/webhooks/generic/{token}  — public ingest. No JWT — the
                                   secret-token suffix is the only
                                   gate. Optional HMAC body
                                   verification when ``secret`` is set
                                   on the Webhook row.

Every POST to the public endpoint writes a ``WebhookEvent(status=pending)``
row. The Celery task in ``app.worker.tasks.automation.process_pending_events``
picks them up and dispatches matched Automations.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User
from app.models.webhook import (
    Automation,
    Webhook,
    WebhookEvent,
    WebhookEventStatus,
)


router = APIRouter(tags=["webhooks"])


# ---------- schemas -------------------------------------------------------


class WebhookCreate(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    source: str | None = None
    secret: str | None = None


class WebhookRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    source: str | None
    token: str
    enabled: bool
    received_count: int
    last_received_at: datetime | None

    class Config:
        from_attributes = True


class AutomationCreate(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    webhook_id: UUID | None = None
    source_filter: str | None = None
    filter_json: dict | None = None
    actions_json: list | None = None


class AutomationRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    enabled: bool
    webhook_id: UUID | None
    source_filter: str | None
    filter_json: dict | None
    actions_json: list | None
    match_count: int
    last_matched_at: datetime | None

    class Config:
        from_attributes = True


# ---------- helpers -------------------------------------------------------


async def _require_admin(
    session: AsyncSession, user: User, org_id: UUID
) -> None:
    if user.is_superuser:
        return
    res = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    m = res.scalar_one_or_none()
    if m is None or m.role not in (
        OrganizationRole.admin,
        OrganizationRole.manager,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook + Automation management requires admin or manager role.",
        )


def _verify_hmac(body: bytes, secret: str, headers: dict[str, str]) -> bool:
    """Best-effort HMAC body check.

    Accepts a signature in any of these headers (whichever the external
    system sent): ``X-DClaw-Signature``, ``X-Hub-Signature-256``,
    ``X-Signature-256``. Format is ``sha256=<hex>``.
    """
    candidates = (
        headers.get("x-dclaw-signature")
        or headers.get("x-hub-signature-256")
        or headers.get("x-signature-256")
        or ""
    )
    if not candidates:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(candidates, expected)


# ---------- admin CRUD -----------------------------------------------------


@router.post(
    "/webhooks",
    response_model=WebhookRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_webhook(
    body: WebhookCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Webhook:
    await _require_admin(session, user, body.organization_id)
    hook = Webhook(
        organization_id=body.organization_id,
        name=body.name,
        source=body.source,
        secret=body.secret,
        token=secrets.token_urlsafe(24),
        created_by_user_id=user.id,
    )
    session.add(hook)
    await session.flush()
    await session.commit()
    await session.refresh(hook)
    return hook


@router.get("/webhooks", response_model=list[WebhookRead])
async def list_webhooks(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[Webhook]:
    await _require_admin(session, user, organization_id)
    res = await session.execute(
        select(Webhook)
        .where(Webhook.organization_id == organization_id)
        .order_by(Webhook.created_at.desc())
    )
    return list(res.scalars().all())


@router.delete(
    "/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_webhook(
    webhook_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    hook = await session.get(Webhook, webhook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    await _require_admin(session, user, hook.organization_id)
    await session.delete(hook)
    await session.commit()


@router.post(
    "/automations",
    response_model=AutomationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_automation(
    body: AutomationCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Automation:
    await _require_admin(session, user, body.organization_id)
    auto = Automation(
        organization_id=body.organization_id,
        name=body.name,
        enabled=body.enabled,
        webhook_id=body.webhook_id,
        source_filter=body.source_filter,
        filter_json=body.filter_json,
        actions_json=body.actions_json,
        created_by_user_id=user.id,
    )
    session.add(auto)
    await session.flush()
    await session.commit()
    await session.refresh(auto)
    return auto


@router.get("/automations", response_model=list[AutomationRead])
async def list_automations(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[Automation]:
    await _require_admin(session, user, organization_id)
    res = await session.execute(
        select(Automation)
        .where(Automation.organization_id == organization_id)
        .order_by(Automation.created_at.desc())
    )
    return list(res.scalars().all())


@router.delete(
    "/automations/{automation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_automation(
    automation_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    auto = await session.get(Automation, automation_id)
    if auto is None:
        raise HTTPException(status_code=404, detail="Automation not found.")
    await _require_admin(session, user, auto.organization_id)
    await session.delete(auto)
    await session.commit()


# ---------- public ingest -------------------------------------------------


@router.post(
    "/webhooks/generic/{token}",
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_generic_webhook(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    res = await session.execute(select(Webhook).where(Webhook.token == token))
    hook = res.scalar_one_or_none()
    if hook is None or not hook.enabled:
        raise HTTPException(status_code=404, detail="Webhook not found.")

    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Optional HMAC verify.
    if hook.secret:
        if not _verify_hmac(body, hook.secret, headers):
            raise HTTPException(
                status_code=401, detail="Bad webhook signature."
            )

    # Body parse — JSON best-effort; non-JSON survives as a raw string
    # payload key.
    payload: dict[str, Any]
    try:
        import json as _json

        payload = _json.loads(body.decode("utf-8")) if body else {}
        if not isinstance(payload, dict):
            payload = {"_payload": payload}
    except Exception:
        payload = {"_raw": body.decode("utf-8", errors="replace")}

    event = WebhookEvent(
        webhook_id=hook.id,
        organization_id=hook.organization_id,
        payload_json=payload,
        status=WebhookEventStatus.pending,
    )
    session.add(event)
    hook.received_count = (hook.received_count or 0) + 1
    hook.last_received_at = datetime.now(tz=timezone.utc)
    await session.flush()
    await session.commit()

    return {"received": True, "event_id": str(event.id)}


__all__ = ["router"]
