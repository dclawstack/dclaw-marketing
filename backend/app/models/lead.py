import enum
from uuid import UUID, uuid4

from sqlalchemy import Enum as SQLEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    converted = "converted"
    lost = "lost"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Tenancy (A1)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        SQLEnum(LeadStatus), nullable=False, default=LeadStatus.new
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )

    campaign: Mapped["Campaign | None"] = relationship(
        "Campaign", back_populates="leads", lazy="selectin"
    )

    # Email is unique per-Org (not globally). Same email can exist in
    # multiple Orgs — agency-platform case where the same contact is
    # tracked across different clients.
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_leads_org_email"),
    )
