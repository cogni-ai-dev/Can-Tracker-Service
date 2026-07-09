import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.pii import (
    BANK_ACCOUNT_NUMBER_FIELD,
    EMAIL_FIELD,
    MOBILE_FIELD,
    PAN_FIELD,
    normalize_pii_value,
)
from app.domain.enums import CanStatus, KycStatus, PayeezzStatus, VerificationStatus
from app.schemas.common import UserSummary
from app.schemas.families import non_blank, optional_stripped

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def normalize_can_number(value: str) -> str:
    return non_blank(value, "CAN number").upper()


def normalize_optional_can_number(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalize_can_number(normalized)


def normalize_pan(value: str | None) -> str | None:
    normalized = normalize_pii_value(PAN_FIELD, value)
    if normalized is None:
        return None
    if not PAN_RE.fullmatch(normalized):
        raise ValueError("PAN must match Indian PAN format.")
    return normalized


def normalize_email(value: str | None) -> str | None:
    normalized = normalize_pii_value(EMAIL_FIELD, value)
    if normalized is None:
        return None
    if "@" not in normalized:
        raise ValueError("A valid email address is required.")
    return normalized


def normalize_mobile(value: str | None) -> str | None:
    normalized = normalize_pii_value(MOBILE_FIELD, value)
    if normalized is None:
        return None
    return normalized


def normalize_bank_account_number(value: str | None) -> str | None:
    return normalize_pii_value(BANK_ACCOUNT_NUMBER_FIELD, value)


def normalize_ifsc(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if not normalized:
        return None
    if not IFSC_RE.fullmatch(normalized):
        raise ValueError("IFSC must match Indian IFSC format.")
    return normalized


def validate_date_not_future(value: date | None, field_name: str) -> date | None:
    if value is not None and value > date.today():
        raise ValueError(f"{field_name} cannot be in the future.")
    return value


class MemberCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    can_number: str | None = Field(default=None, max_length=64)
    can_status: CanStatus | None = None
    pan: str | None = Field(default=None, max_length=32)
    date_of_birth: date | None = None
    kyc_status: KycStatus
    mobile: str | None = Field(default=None, max_length=32)
    mobile_verification_status: VerificationStatus
    email: str | None = Field(default=None, max_length=320)
    email_verification_status: VerificationStatus
    nominee_verification_status: VerificationStatus
    bank_name: str | None = Field(default=None, max_length=200)
    bank_account_number: str | None = Field(default=None, max_length=64)
    ifsc_code: str | None = Field(default=None, max_length=32)
    payeezz_mandate_status: PayeezzStatus
    payeezz_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    payeezz_start_date: date | None = None
    remarks: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return non_blank(value, "Name")

    @field_validator("can_number")
    @classmethod
    def validate_can_number(cls, value: str | None) -> str | None:
        return normalize_optional_can_number(value)

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        return normalize_pan(value)

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None) -> date | None:
        return validate_date_not_future(value, "Date of birth")

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str | None) -> str | None:
        return normalize_mobile(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return normalize_email(value)

    @field_validator("bank_name", "remarks")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        return optional_stripped(value)

    @field_validator("bank_account_number")
    @classmethod
    def validate_bank_account_number(cls, value: str | None) -> str | None:
        return normalize_bank_account_number(value)

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc_code(cls, value: str | None) -> str | None:
        return normalize_ifsc(value)

    @model_validator(mode="after")
    def default_can_status(self) -> "MemberCreate":
        expected_status = CanStatus.AVAILABLE if self.can_number is not None else CanStatus.PENDING
        if self.can_status is None:
            self.can_status = expected_status
        elif self.can_status != expected_status:
            raise ValueError(f"can_status must be {expected_status.value} when can_number is {'present' if self.can_number else 'blank'}.")
        return self


class MemberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    can_number: str | None = Field(default=None, max_length=64)
    can_status: CanStatus | None = None
    pan: str | None = Field(default=None, max_length=32)
    date_of_birth: date | None = None
    kyc_status: KycStatus | None = None
    mobile: str | None = Field(default=None, max_length=32)
    mobile_verification_status: VerificationStatus | None = None
    email: str | None = Field(default=None, max_length=320)
    email_verification_status: VerificationStatus | None = None
    nominee_verification_status: VerificationStatus | None = None
    bank_name: str | None = Field(default=None, max_length=200)
    bank_account_number: str | None = Field(default=None, max_length=64)
    ifsc_code: str | None = Field(default=None, max_length=32)
    payeezz_mandate_status: PayeezzStatus | None = None
    payeezz_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    payeezz_start_date: date | None = None
    remarks: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return None if value is None else non_blank(value, "Name")

    @field_validator("can_number")
    @classmethod
    def validate_can_number(cls, value: str | None) -> str | None:
        return normalize_optional_can_number(value)

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        return normalize_pan(value)

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None) -> date | None:
        return validate_date_not_future(value, "Date of birth")

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str | None) -> str | None:
        return normalize_mobile(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return normalize_email(value)

    @field_validator("bank_name", "remarks")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        return optional_stripped(value)

    @field_validator("bank_account_number")
    @classmethod
    def validate_bank_account_number(cls, value: str | None) -> str | None:
        return normalize_bank_account_number(value)

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc_code(cls, value: str | None) -> str | None:
        return normalize_ifsc(value)

    @model_validator(mode="after")
    def require_update_field(self) -> "MemberUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        for field_name in (
            "name",
            "kyc_status",
            "mobile_verification_status",
            "email_verification_status",
            "nominee_verification_status",
            "payeezz_mandate_status",
            "can_status",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        if "can_number" in self.model_fields_set:
            expected_status = CanStatus.AVAILABLE if self.can_number is not None else CanStatus.PENDING
            if "can_status" not in self.model_fields_set:
                self.can_status = expected_status
                self.model_fields_set.add("can_status")
            elif self.can_status != expected_status:
                raise ValueError(
                    f"can_status must be {expected_status.value} when can_number is "
                    f"{'present' if self.can_number else 'blank'}."
                )
        return self


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    name: str
    can_number: str | None = None
    can_status: CanStatus
    pan_masked: str | None = None
    pan: str | None = None
    date_of_birth: date | None = None
    kyc_status: KycStatus
    mobile_masked: str | None = None
    mobile: str | None = None
    mobile_verification_status: VerificationStatus
    email_masked: str | None = None
    email: str | None = None
    email_verification_status: VerificationStatus
    nominee_verification_status: VerificationStatus
    bank_name: str | None = None
    bank_account_number_masked: str | None = None
    bank_account_number: str | None = None
    ifsc_code: str | None = None
    payeezz_mandate_status: PayeezzStatus
    payeezz_amount: Decimal | None = None
    payeezz_start_date: date | None = None
    remarks: str | None = None
    family_code: str
    family_head_name: str
    primary_rm: UserSummary | None
    updated_at: datetime
    updated_by: UserSummary | None = None
    created_at: datetime


class MemberListResponse(BaseModel):
    items: list[MemberRead]
    total: int
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class MemberListFilters(BaseModel):
    q: str | None = None
    family_id: UUID | None = None
    rm_id: UUID | None = None
    can_status: CanStatus | None = None
    kyc_status: KycStatus | None = None
    payeezz_mandate_status: PayeezzStatus | None = None
    mobile_verification_status: VerificationStatus | None = None
    email_verification_status: VerificationStatus | None = None
    nominee_verification_status: VerificationStatus | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
