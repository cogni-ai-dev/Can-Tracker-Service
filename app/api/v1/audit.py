from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.domain.enums import AuditAction, AuditEntityType, ChangeSource, UserRole
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogList

router = APIRouter(prefix="/audit", tags=["audit"])
require_admin = require_roles(UserRole.ADMIN)


@router.get("", response_model=AuditLogList)
def list_audit_logs(
    entity_type: AuditEntityType | None = None,
    entity_id: UUID | None = None,
    action: AuditAction | None = None,
    actor_user_id: UUID | None = None,
    source: ChangeSource | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    filters = []
    if entity_type is not None:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        filters.append(AuditLog.entity_id == entity_id)
    if action is not None:
        filters.append(AuditLog.action == action)
    if actor_user_id is not None:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if source is not None:
        filters.append(AuditLog.source == source)

    total = db.scalar(select(func.count(AuditLog.id)).where(*filters)) or 0
    items = list(
        db.scalars(
            select(AuditLog)
            .where(*filters)
            .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}
