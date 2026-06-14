from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import UserRole


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not email or "@" not in email:
        raise ValueError("A valid email address is required.")
    return email


def _non_blank(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    role: UserRole
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    role: UserRole
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _non_blank(value, "Name")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _non_blank(value, "Password")


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    password: str | None = Field(default=None, min_length=8, max_length=256)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return None if value is None else _non_blank(value, "Name")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return None if value is None else normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        return None if value is None else _non_blank(value, "Password")

    @model_validator(mode="after")
    def require_update_field(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _non_blank(value, "Password")


class LoginResponse(BaseModel):
    user: UserRead
