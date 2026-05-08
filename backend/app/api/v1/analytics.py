from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analytics_event import AnalyticsEvent, EventType
from app.schemas.analytics_event import AnalyticsEventCreate, AnalyticsEventRead
from app.repositories.analytics_event_repo import AnalyticsEventRepository

router = APIRouter()


@router.post("/", response_model=AnalyticsEventRead, status_code=201)
async def create_analytics_event(data: AnalyticsEventCreate, db: AsyncSession = Depends(get_db)):
    repo = AnalyticsEventRepository(db)
    event = AnalyticsEvent(**data.model_dump())
    return await repo.create(event)


@router.get("/campaign/{campaign_id}", response_model=dict)
async def list_analytics_by_campaign(
    campaign_id: UUID,
    event_type: Optional[EventType] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = AnalyticsEventRepository(db)
    items, total = await repo.list_by_campaign(
        campaign_id=campaign_id, event_type=event_type, limit=limit, offset=offset
    )
    return {"items": [AnalyticsEventRead.model_validate(item) for item in items], "total": total}


@router.get("/campaign/{campaign_id}/summary")
async def get_campaign_summary(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = AnalyticsEventRepository(db)
    summary = await repo.get_summary_by_campaign(campaign_id)
    return summary
