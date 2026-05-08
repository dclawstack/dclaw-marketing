from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.analytics_event import EventType


class AnalyticsEventBase(BaseModel):
    campaign_id: UUID
    event_type: EventType
    value: float = 0.0
    recorded_at: datetime


class AnalyticsEventCreate(AnalyticsEventBase):
    pass


class AnalyticsEventRead(AnalyticsEventBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
