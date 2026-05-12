"""Email-provider webhook ingest — Phase 7.4.

POST /api/v1/webhooks/email/{provider}

Routes per provider (Resend / Postmark / SendGrid for now) verify the
provider's signature, normalise the payload into one or more
``EmailEvent`` rows, and (when the recipient resolves to a ``Lead``)
also emit a corresponding ``LeadActivity(kind=email_*)`` so the
lead timeline reflects engagement.

Auth: these endpoints are intentionally **public** (no JWT) — the
caller is the provider, not the user. Signature verification is the
only gate.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import engine
from app.models.email_event import EmailEvent, EmailEventKind, EmailEventProvider
from app.models.lead import Lead, LeadActivity, LeadActivityKind
from app.services.email_events import (
    SignatureError,
    normalise_postmark_event,
    normalise_resend_event,
    normalise_sendgrid_event,
    verify_postmark,
    verify_resend,
    verify_sendgrid_present,
)


log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/email", tags=["webhooks"])


_KIND_TO_ACTIVITY: dict[EmailEventKind, LeadActivityKind] = {
    EmailEventKind.opened: LeadActivityKind.email_open,
    EmailEventKind.clicked: LeadActivityKind.email_click,
    EmailEventKind.replied: LeadActivityKind.email_reply,
}


async def _persist_event(
    session: AsyncSession,
    *,
    provider: EmailEventProvider,
    normalised: dict[str, Any],
    payload: dict,
) -> EmailEvent:
    """Inserts one EmailEvent + an optional LeadActivity bridge.

    The Lead lookup is best-effort: we resolve by recipient email
    across all orgs. If multiple Leads share an email (unusual but
    possible in a multi-org install), the first match wins.
    """
    activity_id = None
    org_id = None
    recipient = normalised.get("recipient")
    if recipient:
        match = await session.execute(
            select(Lead).where(Lead.email == recipient).limit(1)
        )
        lead = match.scalar_one_or_none()
        if lead is not None:
            org_id = lead.organization_id
            activity_kind = _KIND_TO_ACTIVITY.get(normalised["kind"])
            if activity_kind is not None:
                la = LeadActivity(
                    lead_id=lead.id,
                    organization_id=lead.organization_id,
                    kind=activity_kind,
                    summary=(
                        f"{provider.value} {normalised['kind'].value}"
                    ),
                    payload_json={"provider": provider.value, "raw": payload},
                    occurred_at=normalised["occurred_at"],
                )
                session.add(la)
                await session.flush()
                activity_id = la.id

    event = EmailEvent(
        organization_id=org_id,
        provider=provider,
        kind=normalised["kind"],
        provider_message_id=normalised.get("provider_message_id"),
        recipient=recipient,
        occurred_at=normalised["occurred_at"],
        payload_json=payload,
        lead_activity_id=activity_id,
    )
    session.add(event)
    await session.flush()
    return event


@router.post("/resend", status_code=status.HTTP_202_ACCEPTED)
async def resend_webhook(request: Request) -> dict:
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    secret = settings.resend_webhook_secret
    if secret:
        try:
            verify_resend(body=body, headers=headers, secret=secret)
        except SignatureError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    else:
        log.warning("resend_webhook_secret unset — accepting unverified payload")

    payload = json.loads(body.decode("utf-8") or "{}")
    normalised = normalise_resend_event(payload)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await _persist_event(
            session,
            provider=EmailEventProvider.resend,
            normalised=normalised,
            payload=payload,
        )
        await session.commit()
    return {"received": True, "kind": normalised["kind"].value}


@router.post("/postmark", status_code=status.HTTP_202_ACCEPTED)
async def postmark_webhook(request: Request) -> dict:
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    secret = settings.postmark_webhook_secret
    if secret:
        try:
            verify_postmark(body=body, headers=headers, secret=secret)
        except SignatureError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    else:
        log.warning("postmark_webhook_secret unset — accepting unverified payload")

    payload = json.loads(body.decode("utf-8") or "{}")
    normalised = normalise_postmark_event(payload)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await _persist_event(
            session,
            provider=EmailEventProvider.postmark,
            normalised=normalised,
            payload=payload,
        )
        await session.commit()
    return {"received": True, "kind": normalised["kind"].value}


@router.post("/sendgrid", status_code=status.HTTP_202_ACCEPTED)
async def sendgrid_webhook(request: Request) -> dict:
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    # Structural check only — full ECDSA verify follows with the
    # Connect-with-SendGrid OAuth pubkey rotation work.
    if settings.sendgrid_webhook_verify:
        try:
            verify_sendgrid_present(headers=headers)
        except SignatureError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    payload_list = json.loads(body.decode("utf-8") or "[]")
    if not isinstance(payload_list, list):
        raise HTTPException(
            status_code=400, detail="SendGrid webhook expects a JSON array"
        )

    received = 0
    async with AsyncSession(engine, expire_on_commit=False) as session:
        for evt in payload_list:
            normalised = normalise_sendgrid_event(evt)
            await _persist_event(
                session,
                provider=EmailEventProvider.sendgrid,
                normalised=normalised,
                payload=evt,
            )
            received += 1
        await session.commit()
    return {"received": True, "events": received}


__all__ = ["router"]
