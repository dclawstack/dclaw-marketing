from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.models.lead import Lead, LeadStatus
from app.repositories.base_repo import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Lead)

    async def list_filtered(
        self,
        organization_id: Optional[UUID] = None,
        search: Optional[str] = None,
        source: Optional[str] = None,
        status: Optional[LeadStatus] = None,
        campaign_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Lead], int]:
        query = select(Lead)
        count_query = select(func.count()).select_from(Lead)

        if organization_id is not None:
            query = query.where(Lead.organization_id == organization_id)
            count_query = count_query.where(Lead.organization_id == organization_id)
        if search:
            like = f"%{search}%"
            query = query.where(
                (Lead.email.ilike(like))
                | (Lead.first_name.ilike(like))
                | (Lead.last_name.ilike(like))
                | (Lead.company.ilike(like))
            )
            count_query = count_query.where(
                (Lead.email.ilike(like))
                | (Lead.first_name.ilike(like))
                | (Lead.last_name.ilike(like))
                | (Lead.company.ilike(like))
            )
        if source:
            query = query.where(Lead.source == source)
            count_query = count_query.where(Lead.source == source)
        if status:
            query = query.where(Lead.status == status)
            count_query = count_query.where(Lead.status == status)
        if campaign_id:
            query = query.where(Lead.campaign_id == campaign_id)
            count_query = count_query.where(Lead.campaign_id == campaign_id)

        result = await self.db.execute(query.limit(limit).offset(offset))
        items = list(result.scalars().all())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        return items, total

    async def get_by_email(
        self, email: str, organization_id: Optional[UUID] = None
    ) -> Optional[Lead]:
        stmt = select(Lead).where(Lead.email == email)
        if organization_id is not None:
            stmt = stmt.where(Lead.organization_id == organization_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
