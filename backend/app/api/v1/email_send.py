"""Email send API (Phase 7.1).

Currently exposes a single admin-gated test-send endpoint that goes
straight through ``app.services.email_send.send_email`` — useful to
verify Resend credentials from the UI without staging a full campaign.

The campaign / sequence send paths land in a follow-up PR and will
be hard-gated through the Approval Inbox.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
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
