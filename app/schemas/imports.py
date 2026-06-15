from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ImportBatchStatus, ImportRowStatus


class ImportBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    file_sha256: str
    uploaded_by_user_id: UUID
    status: ImportBatchStatus
    row_count: int = Field(ge=0)
    valid_row_count: int = Field(ge=0)
    error_row_count: int = Field(ge=0)
    conflict_row_count: int = Field(ge=0)
    committed_row_count: int = Field(ge=0)
    warnings: list[str]
    errors: list[str]
    created_at: datetime
    committed_at: datetime | None = None


class ImportBatchListResponse(BaseModel):
    items: list[ImportBatchRead]
    total: int
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class ImportRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    import_batch_id: UUID
    row_number: int = Field(ge=1)
    raw_data: dict[str, Any]
    normalized_data: dict[str, Any]
    status: ImportRowStatus
    errors: list[str]
    family_id: UUID | None = None
    member_id: UUID | None = None
    created_at: datetime


class ImportRowListResponse(BaseModel):
    items: list[ImportRowRead]
    total: int
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
