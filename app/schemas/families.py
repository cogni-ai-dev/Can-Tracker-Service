from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import KycStatus, PayeezzStatus, VerificationStatus
from app.schemas.common import CountPercentageRead, UserSummary


def non_blank(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized


def optional_stripped(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class FamilyStatusFilter(str, Enum):
    ALL = "all"
    KYC_PENDING = "kyc_pending"
    PAYEEZZ_PENDING = "payeezz_pending"
    CONTACT_PENDING = "contact_pending"
    NOMINEE_PENDING = "nominee_pending"


class FamilyCreate(BaseModel):
    family_code: str = Field(min_length=1, max_length=64)
    family_head_name: str = Field(min_length=1, max_length=200)
    primary_rm_id: UUID
    remarks: str | None = Field(default=None, max_length=5000)

    @field_validator("family_code")
    @classmethod
    def validate_family_code(cls, value: str) -> str:
        return non_blank(value, "Family code")

    @field_validator("family_head_name")
    @classmethod
    def validate_family_head_name(cls, value: str) -> str:
        return non_blank(value, "Family head name")

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value: str | None) -> str | None:
        return optional_stripped(value)


class FamilyUpdate(BaseModel):
    family_code: str | None = Field(default=None, min_length=1, max_length=64)
    family_head_name: str | None = Field(default=None, min_length=1, max_length=200)
    primary_rm_id: UUID | None = None
    remarks: str | None = Field(default=None, max_length=5000)

    @field_validator("family_code")
    @classmethod
    def validate_family_code(cls, value: str | None) -> str | None:
        return None if value is None else non_blank(value, "Family code")

    @field_validator("family_head_name")
    @classmethod
    def validate_family_head_name(cls, value: str | None) -> str | None:
        return None if value is None else non_blank(value, "Family head name")

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value: str | None) -> str | None:
        return optional_stripped(value)

    @model_validator(mode="after")
    def require_update_field(self) -> "FamilyUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        for field_name in ("family_code", "family_head_name", "primary_rm_id"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self


class FamilyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_code: str
    family_head_name: str
    primary_rm: UserSummary
    total_members: int
    total_cans: int
    last_updated_at: datetime
    remarks: str | None = None
    kyc_completion: CountPercentageRead
    payeezz_completion: CountPercentageRead
    mobile_verification: CountPercentageRead
    email_verification: CountPercentageRead
    nominee_verification: CountPercentageRead
    kyc_completion_pct: int = Field(ge=0, le=100)
    payeezz_completion_pct: int = Field(ge=0, le=100)
    mobile_verification_pct: int = Field(ge=0, le=100)
    email_verification_pct: int = Field(ge=0, le=100)
    nominee_verification_pct: int = Field(ge=0, le=100)
    created_at: datetime
    updated_at: datetime


class FamilyListResponse(BaseModel):
    items: list[FamilyRead]
    total: int
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class FamilyListFilters(BaseModel):
    q: str | None = None
    rm_id: UUID | None = None
    status_filter: FamilyStatusFilter = FamilyStatusFilter.ALL
    kyc_status: KycStatus | None = None
    payeezz_status: PayeezzStatus | None = None
    mobile_status: VerificationStatus | None = None
    email_status: VerificationStatus | None = None
    nominee_status: VerificationStatus | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    sort: str = "family_head_name"
