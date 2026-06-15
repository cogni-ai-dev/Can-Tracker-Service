from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import ImportBatchStatus, ImportRowStatus
from app.models.base import GUID, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.family import Family, Member
    from app.models.user import User


class ImportBatch(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "status in ('uploaded', 'validated', 'committed', 'failed')",
            name="import_batches_status_valid",
        ),
        Index("ix_import_batches_uploaded_by_user_id", "uploaded_by_user_id"),
        Index("ix_import_batches_status", "status"),
        Index("ix_import_batches_created_at", "created_at"),
        Index("ix_import_batches_file_sha256", "file_sha256"),
    )

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    status: Mapped[ImportBatchStatus] = mapped_column(
        String(32),
        nullable=False,
        default=ImportBatchStatus.UPLOADED,
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conflict_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    committed_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    uploaded_by: Mapped[User] = relationship("User")
    rows: Mapped[list[ImportRow]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="ImportRow.row_number",
    )


class ImportRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        CheckConstraint(
            "status in ('valid', 'error', 'conflict', 'committed', 'skipped')",
            name="import_rows_status_valid",
        ),
        Index("ix_import_rows_import_batch_id", "import_batch_id"),
        Index("ix_import_rows_status", "status"),
        Index("ix_import_rows_row_number", "row_number"),
        Index("ix_import_rows_family_id", "family_id"),
        Index("ix_import_rows_member_id", "member_id"),
    )

    import_batch_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    normalized_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[ImportRowStatus] = mapped_column(String(32), nullable=False)
    errors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    family_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("families.id"), nullable=True)
    member_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("members.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    batch: Mapped[ImportBatch] = relationship(back_populates="rows")
    family: Mapped[Family | None] = relationship("Family")
    member: Mapped[Member | None] = relationship("Member")
