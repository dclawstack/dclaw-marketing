from datetime import date
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.campaign import CampaignType, CampaignStatus


class CampaignBase(BaseModel):
    name: str
    type: CampaignType
    status: CampaignStatus = CampaignStatus.draft
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    description: Optional[str] = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[CampaignType] = None
    status: Optional[CampaignStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    description: Optional[str] = None


class CampaignRead(CampaignBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class CampaignDetail(CampaignRead):
    lead_count: int = 0
    total_spend: float = 0.0
    conversion_count: int = 0
