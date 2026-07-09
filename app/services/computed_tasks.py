from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error
from app.core.config import Settings
from app.core.pii import email_search_hash, mobile_search_hash, pan_search_hash
from app.domain.access import user_is_can_rm
from app.domain.enums import TaskType
from app.domain.tasks import TASK_RULES, mask_can_number
from app.models.family import Family, Member
from app.models.user import User
from app.schemas.tasks import TaskListFilters

UNASSIGNED_RM_NAME = "Unassigned"


def _forbidden(message: str) -> None:
    raise_api_error(status.HTTP_403_FORBIDDEN, "forbidden", message)


def _effective_rm_id(actor: User, requested_rm_id: UUID | None) -> UUID | None:
    if user_is_can_rm(actor):
        if requested_rm_id is not None:
            _forbidden("RM users are automatically scoped and cannot use rm_id filters.")
        return actor.id
    return requested_rm_id


def _search_filter(q: str | None, settings: Settings) -> object | None:
    if q is None or not q.strip():
        return None
    term = q.strip()
    like = f"%{term}%"
    return or_(
        Member.name.ilike(like),
        Member.can_number.ilike(like),
        Family.family_head_name.ilike(like),
        Family.family_code.ilike(like),
        User.name.ilike(like),
        Member.pan_search_hash == pan_search_hash(term, settings),
        Member.mobile_search_hash == mobile_search_hash(term, settings),
        Member.email_search_hash == email_search_hash(term, settings),
    )


def _base_filters(
    *,
    actor: User,
    settings: Settings,
    filters: TaskListFilters,
) -> list[object]:
    conditions: list[object] = [
        Member.deleted_at.is_(None),
        Family.deleted_at.is_(None),
    ]
    rm_id = _effective_rm_id(actor, filters.rm_id)
    if rm_id is not None:
        conditions.append(Family.primary_rm_id == rm_id)
    if filters.family_id is not None:
        conditions.append(Member.family_id == filters.family_id)
    search_filter = _search_filter(filters.q, settings)
    if search_filter is not None:
        conditions.append(search_filter)
    return conditions


def _task_rows_subquery(
    *,
    actor: User,
    settings: Settings,
    filters: TaskListFilters,
):
    base_filters = _base_filters(actor=actor, settings=settings, filters=filters)
    selects = []
    for rule in TASK_RULES:
        if filters.type is not None and filters.type != rule.type:
            continue
        if filters.priority is not None and filters.priority != rule.priority:
            continue
        status_column = getattr(Member, rule.status_field)
        selects.append(
            select(
                literal(rule.type.value).label("type"),
                literal(rule.priority.value).label("priority"),
                Member.id.label("member_id"),
                Member.name.label("member_name"),
                Family.id.label("family_id"),
                Family.family_head_name.label("family_head_name"),
                Family.family_code.label("family_code"),
                User.id.label("rm_id"),
                func.coalesce(User.name, UNASSIGNED_RM_NAME).label("rm_name"),
                Member.can_number.label("can_number"),
                literal(rule.description).label("description"),
                literal(rule.label).label("label"),
                literal(rule.order).label("task_order"),
            )
            .select_from(Member)
            .join(Member.family)
            .outerjoin(User, Family.primary_rm_id == User.id)
            .where(*base_filters, status_column == rule.status_value)
        )

    if not selects:
        return None
    if len(selects) == 1:
        return selects[0].subquery()
    return union_all(*selects).subquery()


def _task_row_to_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": row["type"],
        "priority": row["priority"],
        "member_id": row["member_id"],
        "member_name": row["member_name"],
        "family_id": row["family_id"],
        "family_head_name": row["family_head_name"],
        "family_code": row["family_code"],
        "rm_id": row["rm_id"],
        "rm_name": row["rm_name"],
        "can_number_masked": mask_can_number(row["can_number"]),
        "description": row["description"],
        "label": row["label"],
    }


def list_computed_tasks(
    db: Session,
    *,
    filters: TaskListFilters,
    actor: User,
    settings: Settings,
) -> dict[str, Any]:
    task_rows = _task_rows_subquery(actor=actor, settings=settings, filters=filters)
    if task_rows is None:
        return {"items": [], "total": 0, "limit": filters.limit, "offset": filters.offset}

    total = db.scalar(select(func.count()).select_from(task_rows)) or 0
    rows = list(
        db.execute(
            select(task_rows)
            .order_by(
                task_rows.c.family_code,
                task_rows.c.member_name,
                task_rows.c.member_id,
                task_rows.c.task_order,
                task_rows.c.type,
            )
            .limit(filters.limit)
            .offset(filters.offset)
        )
        .mappings()
        .all()
    )
    return {
        "items": [_task_row_to_response(dict(row)) for row in rows],
        "total": int(total),
        "limit": filters.limit,
        "offset": filters.offset,
    }


def get_task_summary(
    db: Session,
    *,
    filters: TaskListFilters,
    actor: User,
    settings: Settings,
) -> dict[str, int]:
    task_rows = _task_rows_subquery(actor=actor, settings=settings, filters=filters)
    counts = {task_type.value: 0 for task_type in TaskType}
    if task_rows is None:
        return {
            "total_tasks": 0,
            "kyc": 0,
            "payeezz": 0,
            "mobile": 0,
            "email": 0,
            "nominee": 0,
        }

    grouped_rows = db.execute(
        select(task_rows.c.type, func.count().label("count")).select_from(task_rows).group_by(task_rows.c.type)
    ).all()
    for task_type, count in grouped_rows:
        counts[str(task_type)] = int(count)

    return {
        "total_tasks": sum(counts.values()),
        "kyc": counts[TaskType.KYC.value],
        "payeezz": counts[TaskType.PAYEEZZ.value],
        "mobile": counts[TaskType.MOBILE.value],
        "email": counts[TaskType.EMAIL.value],
        "nominee": counts[TaskType.NOMINEE.value],
    }
