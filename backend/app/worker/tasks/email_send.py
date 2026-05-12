"""Email-send worker task (Phase 7.2).

Triggered when an ApprovalRequest of action_type ``send_email`` is
approved. Reads the payload, fires the email through the Resend
adapter, and stamps the approval with the resulting message id.

The approve endpoint enqueues ``deliver_approved_email.delay(approval_id)``
right after flipping the request to ``approved`` — see
``app.api.v1.approvals.approve``.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.models.approval_request import ApprovalRequest
from app.services.cost_logger import record_cost_sync
from app.services.email_send import SendProvider, SendResult, send_email
from app.services.sandbox import is_sandbox_mode_sync
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


@celery_app.task(
    name="app.worker.tasks.email_send.deliver_approved_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def deliver_approved_email(self, approval_id: str) -> dict:
    """Sends the email payload encoded in the ApprovalRequest, then
    stamps the request's ``payload_json.delivery`` block so the UI
    can show the outcome.
    """
    aid = UUID(approval_id)
    with SyncSession() as session:
        ar = session.get(ApprovalRequest, aid)
        if ar is None:
            return {"approval_id": approval_id, "result": "missing"}

        payload = dict(ar.payload_json or {})
        # Idempotency — if we already recorded a delivery, skip.
        if isinstance(payload.get("delivery"), dict) and payload["delivery"].get(
            "message_id"
        ):
            return {
                "approval_id": approval_id,
                "result": "already_delivered",
                "message_id": payload["delivery"]["message_id"],
            }

        to = payload.get("to") or []
        subject = payload.get("subject") or "(no subject)"
        html = payload.get("html") or ""
        text = payload.get("text")
        from_email = payload.get("from_email")
        reply_to = payload.get("reply_to")

        if not to or not html:
            payload["delivery"] = {
                "error": "Approval payload missing required fields: to/html",
            }
            ar.payload_json = payload
            session.commit()
            return {"approval_id": approval_id, "result": "bad_payload"}

        try:
            # Phase 11.5 — Sandbox / dry-run. Skip the Resend call when
            # the Org is in dry-run; stamp a synthetic id so the rest of
            # the bookkeeping still happens.
            sandbox = (
                ar.organization_id is not None
                and is_sandbox_mode_sync(session, ar.organization_id)
            )
            if sandbox:
                import hashlib
                digest = hashlib.sha256(
                    ("|".join(sorted(to)) + "::" + subject).encode("utf-8")
                ).hexdigest()[:24]
                result = SendResult(
                    message_id=f"msg_sandbox_{digest}",
                    provider=SendProvider.stub,
                    to=list(to),
                    subject=subject,
                )
            else:
                result = asyncio.run(
                    send_email(
                        to=list(to),
                        subject=subject,
                        html=html,
                        text=text,
                        from_email=from_email,
                        reply_to=reply_to,
                    )
                )
        except Exception as exc:
            payload["delivery"] = {"error": str(exc)}
            ar.payload_json = payload
            session.commit()
            raise

        payload["delivery"] = {
            "message_id": result.message_id,
            "provider": result.provider.value,
            "to": result.to,
            "subject": result.subject,
        }
        ar.payload_json = payload
        if ar.organization_id is not None:
            record_cost_sync(
                session,
                organization_id=ar.organization_id,
                provider=result.provider.value,
                kind="email",
                units=float(len(result.to)),
                units_kind="email",
                provider_resource=result.message_id,
                metadata={"approval_id": approval_id, "subject": result.subject},
            )
        session.commit()

    return {
        "approval_id": approval_id,
        "result": "delivered",
        "message_id": result.message_id,
        "provider": result.provider.value,
    }
