"""Email send API (Phases 7.1 + 7.3).

- POST /email/test-send                  — admin-only no-gate test
  (Phase 7.1)
- POST /email/campaigns/{id}/send        — creates an ApprovalRequest
  with action_type=send_email; on approve, the Phase 7.2 worker fires
  the actual send through Resend. (Phase 7.3 — closes the email
  outbound loop end-to-end.)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.email_ads import EmailCampaign, EmailCampaignStatus, EmailTemplate
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services.email_send import send_email


router = APIRouter(prefix="/email", tags=["email"])


class TestSendRequest(BaseModel):
    organization_id: UUID
    to: list[EmailStr] = Field(min_length=1, max_length=10)
    subject: str = Field(min_length=1, max_length=200)
    html: str = Field(min_length=1, max_length=200_000)
    text: str | None = Field(default=None, max_length=200_000)
    from_email: str | None = None


class TestSendResponse(BaseModel):
    message_id: str
    provider: str
    to: list[str]
    subject: str


_SEND_ROLES = (
    OrganizationRole.admin,
    OrganizationRole.manager,
)


async def _user_in_org(
    session: AsyncSession,
    user: User,
    org_id: UUID,
) -> None:
    if user.is_superuser:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    m = result.scalar_one_or_none()
    if m is None or m.role not in _SEND_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Manager required to send test emails.",
        )


@router.post("/test-send", response_model=TestSendResponse)
async def email_test_send(
    body: TestSendRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TestSendResponse:
    """Sends a test email immediately (no approval gate — this endpoint
    is admin-only and meant for verifying Resend credentials).
    """
    await _user_in_org(session, user, body.organization_id)

    result = await send_email(
        to=[str(addr) for addr in body.to],
        subject=body.subject,
        html=body.html,
        text=body.text,
        from_email=body.from_email,
    )
    return TestSendResponse(
        message_id=result.message_id,
        provider=result.provider.value,
        to=result.to,
        subject=result.subject,
    )


# ---------- Phase 7.3 — campaign send through approval ---------------


class CampaignSendRequest(BaseModel):
    to: list[EmailStr] = Field(min_length=1, max_length=10000)
    subject_override: str | None = Field(default=None, max_length=998)
    html_override: str | None = Field(default=None, max_length=500_000)
    from_email: str | None = None
    reply_to: str | None = None


class CampaignSendResponse(BaseModel):
    approval_request_id: str
    campaign_id: str
    status: str
    summary: str


@router.post(
    "/campaigns/{campaign_id}/send", response_model=CampaignSendResponse
)
async def campaign_send(
    campaign_id: UUID,
    body: CampaignSendRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignSendResponse:
    """Hard-gate: creates a pending ApprovalRequest for the email
    campaign send. On approve, ``app.worker.tasks.email_send.
    deliver_approved_email`` fires the actual Resend call.

    The campaign's template provides the default subject + body_html;
    callers may override either via the request body.
    """
    campaign = await session.get(EmailCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found.",
        )
    await _user_in_org(session, user, campaign.organization_id)

    if campaign.status not in (
        EmailCampaignStatus.draft,
        EmailCampaignStatus.scheduled,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Campaign is {campaign.status.value} — only draft / "
                "scheduled campaigns can be queued for approval."
            ),
        )

    # Resolve subject + html. Override beats template; template beats
    # name-as-subject + empty-body fallback.
    subject = body.subject_override
    html = body.html_override
    if (subject is None or html is None) and campaign.template_id is not None:
        template = await session.get(EmailTemplate, campaign.template_id)
        if template is not None:
            if subject is None:
                subject = template.subject
            if html is None:
                html = template.body_html
    if subject is None:
        subject = campaign.name
    if html is None or not html.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No HTML body — either set html_override or attach a "
                "template with body_html."
            ),
        )

    recipients = [str(addr) for addr in body.to]
    summary = (
        f"Send campaign '{campaign.name}' to {len(recipients)} recipient"
        f"{'s' if len(recipients) != 1 else ''}: "
        f"{subject[:80]}{'…' if len(subject) > 80 else ''}"
    )

    approval = ApprovalRequest(
        organization_id=campaign.organization_id,
        requested_by_user_id=user.id,
        action_type="send_email",
        target_type="email_campaign",
        target_id=str(campaign.id),
        payload_json={
            "campaign_id": str(campaign.id),
            "to": recipients,
            "subject": subject,
            "html": html,
            "from_email": body.from_email,
            "reply_to": body.reply_to,
        },
        summary=summary,
        status=ApprovalStatus.pending,
    )
    session.add(approval)
    await session.commit()
    await session.refresh(approval)

    return CampaignSendResponse(
        approval_request_id=str(approval.id),
        campaign_id=str(campaign.id),
        status=approval.status.value,
        summary=summary,
    )
