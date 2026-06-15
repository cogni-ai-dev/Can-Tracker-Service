from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ReportExportFormat, ReportType
from app.models.base import GUID, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ReportExport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "report_exports"
    __table_args__ = (
        CheckConstraint(
            "report_type in ('kyc_pending', 'payeezz_pending', 'contact_pending', "
            "'family_compliance', 'rm_tasks', 'full')",
            name="report_exports_report_type_valid",
        ),
        CheckConstraint(
            "format in ('csv', 'xlsx', 'pdf')",
            name="report_exports_format_valid",
        ),
        Index("ix_report_exports_report_type", "report_type"),
        Index("ix_report_exports_format", "format"),
        Index("ix_report_exports_exported_by_user_id", "exported_by_user_id"),
        Index("ix_report_exports_created_at", "created_at"),
    )

    report_type: Mapped[ReportType] = mapped_column(String(64), nullable=False)
    format: Mapped[ReportExportFormat] = mapped_column(String(16), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    exported_by_user_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    exported_by: Mapped[User] = relationship("User")
