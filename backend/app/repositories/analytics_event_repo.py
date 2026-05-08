from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.models.analytics_event import AnalyticsEvent, EventType
from app.repositories.base_repo import BaseRepository


class AnalyticsEventRepository(BaseRepository[AnalyticsEvent]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, AnalyticsEvent)

    async def list_by_campaign(
        self,
        campaign_id: UUID,
        event_type: Optional[EventType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AnalyticsEvent], int]:
        query = select(AnalyticsEvent).where(AnalyticsEvent.campaign_id == campaign_id)
        count_query = select(func.count()).select_from(AnalyticsEvent).where(AnalyticsEvent.campaign_id == campaign_id)

        if event_type:
            query = query.where(AnalyticsEvent.event_type == event_type)
            count_query = count_query.where(AnalyticsEvent.event_type == event_type)

        result = await self.db.execute(query.limit(limit).offset(offset))
        items = list(result.scalars().all())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        return items, total

    async def get_summary_by_campaign(self, campaign_id: UUID) -> dict:
        result = await self.db.execute(
            select(AnalyticsEvent.event_type, func.count().label("count"), func.sum(AnalyticsEvent.value).label("total_value"))
            .where(AnalyticsEvent.campaign_id == campaign_id)
            .group_by(AnalyticsEvent.event_type)
        )
        summary = {}
        for row in result.all():
            summary[row.event_type.value] = {
                "count": row.count,
                "total_value": float(row.total_value or 0),
            }
        return summary
