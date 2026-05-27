import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.expeditions.models import ExpeditionStatus, MemberState


class ExpeditionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    capacity: int = Field(gt=0)


class ExpeditionRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: ExpeditionStatus
    start_at: datetime
    end_at: datetime | None
    capacity: int
    chief_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemberRead(BaseModel):
    id: uuid.UUID
    expedition_id: uuid.UUID
    user_id: uuid.UUID
    state: MemberState
    invited_at: datetime
    confirmed_at: datetime | None

    model_config = {"from_attributes": True}


class InviteRequest(BaseModel):
    user_id: uuid.UUID
