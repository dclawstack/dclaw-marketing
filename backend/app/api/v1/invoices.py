"""Invoice CRUD + status actions (SP3-23).

Per-Org list + a small set of state transitions:
  - POST /invoices/{id}/mark-paid  → status=paid, paid_at=now
  - POST /invoices/{id}/void       → status=void
  - POST /invoices/{id}/uncollectible

The /orgs/{org}/invoices listing was previously hit by the /invoices
page without a backend route — this fills that gap. Stripe sync hooks
are deferred to the webhook receiver; this UI lets the operator move
state manually.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.models.organization import OrganizationMembership
from app.models.user import User


router = APIRouter(tags=["invoices"])


async def _require_member(
    session: AsyncSession, user: User, organization_id: UUID
) -> None:
    if user.is_superuser:
        return
    m = (
        await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )


def _serialize(inv: Invoice) -> dict:
    return {
        "id": str(inv.id),
        "organization_id": str(inv.organization_id),
        "invoice_number": inv.invoice_number,
        "status": inv.status.value,
        "subtotal_usd": float(inv.subtotal_usd or 0.0),
        "tax_usd": float(inv.tax_usd or 0.0),
        "total_usd": float(inv.total_usd or 0.0),
        "currency": inv.currency,
        "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
        "due_at": inv.due_at.isoformat() if inv.due_at else None,
        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
        "stripe_invoice_id": inv.stripe_invoice_id,
        "notes": inv.notes,
    }


@router.get("/orgs/{organization_id}/invoices")
async def list_invoices(
    organization_id: UUID,
    status_filter: InvoiceStatus | None = Query(None, alias="status"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    await _require_member(session, user, organization_id)
    q = select(Invoice).where(Invoice.organization_id == organization_id)
    if status_filter is not None:
        q = q.where(Invoice.status == status_filter)
    q = q.order_by(Invoice.issued_at.desc())
    rows = (await session.execute(q)).scalars().all()
    return [_serialize(r) for r in rows]


async def _load_invoice(
    session: AsyncSession, user: User, invoice_id: UUID
) -> Invoice:
    inv = await session.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    await _require_member(session, user, inv.organization_id)
    return inv


@router.post("/invoices/{invoice_id}/mark-paid")
async def mark_paid(
    invoice_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    inv = await _load_invoice(session, user, invoice_id)
    if inv.status == InvoiceStatus.void:
        raise HTTPException(
            status_code=400, detail="Cannot mark a voided invoice as paid."
        )
    inv.status = InvoiceStatus.paid
    inv.paid_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(inv)
    return _serialize(inv)


@router.post("/invoices/{invoice_id}/void")
async def void_invoice(
    invoice_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    inv = await _load_invoice(session, user, invoice_id)
    if inv.status == InvoiceStatus.paid:
        raise HTTPException(
            status_code=400, detail="Cannot void a paid invoice — refund instead."
        )
    inv.status = InvoiceStatus.void
    await session.commit()
    await session.refresh(inv)
    return _serialize(inv)


@router.post("/invoices/{invoice_id}/uncollectible")
async def mark_uncollectible(
    invoice_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    inv = await _load_invoice(session, user, invoice_id)
    if inv.status == InvoiceStatus.paid:
        raise HTTPException(
            status_code=400, detail="Invoice already paid."
        )
    inv.status = InvoiceStatus.uncollectible
    await session.commit()
    await session.refresh(inv)
    return _serialize(inv)
