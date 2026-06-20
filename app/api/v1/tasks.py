from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db, require_module_roles
from app.core.config import Settings
from app.domain.enums import ModuleCode, ModuleRole, TaskPriority, TaskType
from app.models.user import User
from app.schemas.tasks import TaskListFilters, TaskListResponse, TaskSummaryRead
from app.services.computed_tasks import get_task_summary, list_computed_tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])

require_task_read = require_module_roles(
    ModuleCode.CAN_COMPLIANCE,
    ModuleRole.CAN_ADMIN,
    ModuleRole.CAN_OPS,
    ModuleRole.CAN_RM,
    ModuleRole.CAN_MANAGEMENT,
)


def task_list_filters(
    task_type: Annotated[TaskType | None, Query(alias="type")] = None,
    rm_id: Annotated[UUID | None, Query()] = None,
    family_id: Annotated[UUID | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    priority: Annotated[TaskPriority | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListFilters:
    return TaskListFilters(
        type=task_type,
        rm_id=rm_id,
        family_id=family_id,
        q=q,
        priority=priority,
        limit=limit,
        offset=offset,
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    filters: TaskListFilters = Depends(task_list_filters),
    current_user: User = Depends(require_task_read),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    return list_computed_tasks(db, filters=filters, actor=current_user, settings=settings)


@router.get("/summary", response_model=TaskSummaryRead)
def task_summary(
    filters: TaskListFilters = Depends(task_list_filters),
    current_user: User = Depends(require_task_read),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    return get_task_summary(db, filters=filters, actor=current_user, settings=settings)
