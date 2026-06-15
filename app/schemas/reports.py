from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import ReportExportFormat, ReportType


class ReportListFilters(BaseModel):
    rm_id: UUID | None = None
    family_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ReportColumnRead(BaseModel):
    key: str
    label: str


class ReportPreviewResponse(BaseModel):
    report_type: ReportType
    title: str
    columns: list[ReportColumnRead]
    items: list[dict[str, Any]]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    filters: dict[str, Any]


class ReportExportResult(BaseModel):
    report_type: ReportType
    format: ReportExportFormat
    filename: str
    media_type: str
    content: bytes
    row_count: int = Field(ge=0)
