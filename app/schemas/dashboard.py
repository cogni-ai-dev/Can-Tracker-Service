from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UserSummary
from app.schemas.members import MemberRead


class DashboardSummaryRead(BaseModel):
    total_clients: int = Field(ge=0)
    total_families: int = Field(ge=0)
    kyc_validated: int = Field(ge=0)
    kyc_registered: int = Field(ge=0)
    kyc_no_kyc: int = Field(ge=0)
    kyc_pending: int = Field(ge=0)
    kyc_validated_pct: int = Field(ge=0, le=100)
    kyc_pending_pct: int = Field(ge=0, le=100)
    payeezz_accepted: int = Field(ge=0)
    payeezz_sent_for_approval: int = Field(ge=0)
    payeezz_not_available: int = Field(ge=0)
    payeezz_pending: int = Field(ge=0)
    payeezz_accepted_pct: int = Field(ge=0, le=100)
    payeezz_pending_pct: int = Field(ge=0, le=100)
    mobile_verified: int = Field(ge=0)
    mobile_not_verified: int = Field(ge=0)
    email_verified: int = Field(ge=0)
    email_not_verified: int = Field(ge=0)
    nominee_verified: int = Field(ge=0)
    nominee_not_verified: int = Field(ge=0)
    updated_at: datetime | None = None


class FamilyDashboardSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_code: str
    family_head_name: str
    primary_rm: UserSummary
    remarks: str | None = None
    last_updated_at: datetime
    number_of_members: int = Field(ge=0)
    total_cans: int = Field(ge=0)
    kyc_completion_pct: int = Field(ge=0, le=100)
    mobile_verification_pct: int = Field(ge=0, le=100)
    email_verification_pct: int = Field(ge=0, le=100)
    nominee_verification_pct: int = Field(ge=0, le=100)
    payeezz_completion_pct: int = Field(ge=0, le=100)
    members: list[MemberRead]
