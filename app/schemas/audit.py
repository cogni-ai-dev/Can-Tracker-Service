from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AuditAction, AuditEntityType, ChangeSource


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: AuditEntityType
    entity_id: UUID
    action: AuditAction
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    actor_user_id: UUID | None = None
    source: ChangeSource
    import_batch_id: UUID | None = None
    request_id: str | None = None
    created_at: datetime


class AuditLogList(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
