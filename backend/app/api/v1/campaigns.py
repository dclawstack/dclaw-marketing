"""Org-scoped campaigns router (Sprint 3 — multi-tenant safety fix).

Pre-Sprint-3 this router was global: any caller could read or mutate
any tenant's campaigns. Now every endpoint requires:
  - `organization_id` query param
  - the caller to be a member of that Org (or a superuser)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.campaign import Campaign, CampaignStatus, CampaignType
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.repositories.analytics_event_repo import AnalyticsEventRepository
from app.repositories.campaign_repo import CampaignRepository
from app.repositories.lead_repo import LeadRepository
from app.schemas.campaign import CampaignCreate, CampaignDetail, CampaignRead, CampaignUpdate

router = APIRouter()


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
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this organization."
        )


async def _scope(
    session: AsyncSession, campaign_id: UUID, organization_id: UUID
) -> Campaign:
    """Fetch a campaign and ensure it belongs to organization_id."""
    res = await session.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.organization_id == organization_id,
        )
    )
    c = res.scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c


@router.post("/", response_model=CampaignRead, status_code=201)
async def create_campaign(
    data: CampaignCreate,
    organization_id: UUID = Query(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_member(db, user, organization_id)
    repo = CampaignRepository(db)
    campaign = Campaign(organization_id=organization_id, **data.model_dump())
    return await repo.create(campaign)


@router.get("/", response_model=dict)
async def list_campaigns(
    organization_id: UUID = Query(...),
    status: Optional[CampaignStatus] = Query(None),
    type: Optional[CampaignType] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_member(db, user, organization_id)
    repo = CampaignRepository(db)
    items, total = await repo.list_filtered(
        organization_id=organization_id,
        status=status,
        type=type,
        limit=limit,
        offset=offset,
    )
    return {"items": [CampaignRead.model_validate(item) for item in items], "total": total}


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(
    campaign_id: UUID,
    organization_id: UUID = Query(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_member(db, user, organization_id)
    campaign = await _scope(db, campaign_id, organization_id)

    lead_repo = LeadRepository(db)
    event_repo = AnalyticsEventRepository(db)

    leads, _ = await lead_repo.list_filtered(
        organization_id=organization_id,
        campaign_id=campaign_id,
        limit=10000,
        offset=0,
    )
    events, _ = await event_repo.list_by_campaign(
        campaign_id=campaign_id, limit=10000, offset=0
    )

    conversion_count = sum(1 for e in events if e.event_type.value == "conversion")
    total_spend = sum(e.value for e in events)

    return CampaignDetail(
        id=campaign.id,
        name=campaign.name,
        type=campaign.type,
        status=campaign.status,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        budget=campaign.budget,
        description=campaign.description,
        lead_count=len(leads),
        total_spend=total_spend,
        conversion_count=conversion_count,
    )


@router.patch("/{campaign_id}", response_model=CampaignRead)
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    organization_id: UUID = Query(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_member(db, user, organization_id)
    campaign = await _scope(db, campaign_id, organization_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(campaign, key, value)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: UUID,
    organization_id: UUID = Query(...),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_member(db, user, organization_id)
    campaign = await _scope(db, campaign_id, organization_id)
    repo = CampaignRepository(db)
    await repo.delete(campaign)
    return None
