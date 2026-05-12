from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.models.campaign import Campaign, CampaignStatus, CampaignType
from app.repositories.base_repo import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Campaign)

    async def list_filtered(
        self,
        organization_id: Optional[UUID] = None,
        status: Optional[CampaignStatus] = None,
        type: Optional[CampaignType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Campaign], int]:
        query = select(Campaign)
        count_query = select(func.count()).select_from(Campaign)

        if organization_id is not None:
            query = query.where(Campaign.organization_id == organization_id)
            count_query = count_query.where(Campaign.organization_id == organization_id)
        if status is not None:
            query = query.where(Campaign.status == status)
            count_query = count_query.where(Campaign.status == status)
        if type is not None:
            query = query.where(Campaign.type == type)
            count_query = count_query.where(Campaign.type == type)

        result = await self.db.execute(query.limit(limit).offset(offset))
        items = list(result.scalars().all())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        return items, total

    async def get_with_relations(self, campaign_id: UUID) -> Optional[Campaign]:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()
