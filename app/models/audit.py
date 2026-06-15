from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import AuditAction, AuditEntityType, ChangeSource
from app.models.base import GUID, Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.imports import ImportBatch
    from app.models.user import User


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "entity_type in ('family', 'member', 'user', 'import_batch')",
            name="audit_logs_entity_type_valid",
        ),
        CheckConstraint(
            "action in ('create', 'update', 'delete', 'restore', 'sensitive_read', 'import_commit')",
            name="audit_logs_action_valid",
        ),
        CheckConstraint(
            "source in ('manual', 'import', 'mfu_api')",
            name="audit_logs_source_valid",
        ),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_source", "source"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_import_batch_id", "import_batch_id"),
        Index("ix_audit_logs_request_id", "request_id"),
    )

    entity_type: Mapped[AuditEntityType] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    action: Mapped[AuditAction] = mapped_column(String(32), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text(), nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text(), nullable=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[ChangeSource] = mapped_column(String(32), nullable=False)
    import_batch_id: Mapped[UUID | None] = mapped_column(
        GUID(),
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    actor: Mapped[User | None] = relationship(back_populates="audit_logs")
    import_batch: Mapped[ImportBatch | None] = relationship("ImportBatch")
