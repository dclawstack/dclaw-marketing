from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.lead import LeadStatus


class LeadBase(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    status: LeadStatus = LeadStatus.new
    campaign_id: Optional[UUID] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    status: Optional[LeadStatus] = None
    campaign_id: Optional[UUID] = None


class LeadRead(LeadBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
