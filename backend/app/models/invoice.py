"""Invoice + InvoiceLineItem — Phase 10.6.

Agency billing primitive. Each invoice has:
- A customer (the agency's client, modeled as an external Organization
  with ``is_external=True``)
- One or more line items (each linked to TimeEntries or a flat fee)
- A total in USD
- A status state machine: draft → open → paid / void
- An optional Stripe invoice id when synced out

We deliberately model invoices in our own database (not just push to
Stripe) so:
- Agencies without Stripe connections can still issue invoices
- The Approval Inbox can gate large invoices before they're sent
- Time tracking → invoice generation works offline-first
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    open = "open"           # sent to client, awaiting payment
    paid = "paid"
    void = "void"           # cancelled
    uncollectible = "uncollectible"


class Invoice(Base):
    """One invoice issued by an Org (agency) to a client (external Org)."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "invoice_number",
            name="uq_invoice_org_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Sequential per-Org invoice number, e.g. "INV-2026-001"
    invoice_number: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )

    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(InvoiceStatus),
        nullable=False,
        default=InvoiceStatus.draft,
        index=True,
    )

    subtotal_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tax_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # External provider linkage
    stripe_invoice_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    quickbooks_invoice_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        "InvoiceLineItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLineItem.position",
        lazy="selectin",
    )


class InvoiceLineItem(Base):
    """One line on an invoice — either a flat fee, an hours line (linked
    to TimeEntries), or a one-off charge."""

    __tablename__ = "invoice_line_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit_price_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Optional linkage back to source data
    time_entry_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="line_items")
