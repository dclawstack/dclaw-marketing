from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.campaign import Campaign, CampaignStatus, CampaignType
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignRead, CampaignDetail
from app.repositories.campaign_repo import CampaignRepository
from app.repositories.lead_repo import LeadRepository
from app.repositories.analytics_event_repo import AnalyticsEventRepository

router = APIRouter()


@router.post("/", response_model=CampaignRead, status_code=201)
async def create_campaign(data: CampaignCreate, db: AsyncSession = Depends(get_db)):
    repo = CampaignRepository(db)
    campaign = Campaign(**data.model_dump())
    return await repo.create(campaign)


@router.get("/", response_model=dict)
async def list_campaigns(
    status: Optional[CampaignStatus] = Query(None),
    type: Optional[CampaignType] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = CampaignRepository(db)
    items, total = await repo.list_filtered(status=status, type=type, limit=limit, offset=offset)
    return {"items": [CampaignRead.model_validate(item) for item in items], "total": total}


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = CampaignRepository(db)
    campaign = await repo.get_with_relations(campaign_id)
    if not campaign:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campaign not found")

    lead_repo = LeadRepository(db)
    event_repo = AnalyticsEventRepository(db)

    leads, _ = await lead_repo.list_filtered(campaign_id=campaign_id, limit=10000, offset=0)
    events, _ = await event_repo.list_by_campaign(campaign_id=campaign_id, limit=10000, offset=0)

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
async def update_campaign(campaign_id: UUID, data: CampaignUpdate, db: AsyncSession = Depends(get_db)):
    repo = CampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id)
    if not campaign:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campaign not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(campaign, key, value)
    await repo.db.commit()
    await repo.db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = CampaignRepository(db)
    campaign = await repo.get_by_id(campaign_id)
    if not campaign:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campaign not found")
    await repo.delete(campaign)
    return None
