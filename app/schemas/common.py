from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import UserRole


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    role: UserRole


class CountPercentageRead(BaseModel):
    count: int = Field(ge=0)
    percentage: int = Field(ge=0, le=100)


class TimestampedRead(BaseModel):
    created_at: datetime
    updated_at: datetime
