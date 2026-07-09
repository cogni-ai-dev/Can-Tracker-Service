from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.errors import raise_api_error
from app.domain.access import user_is_can_rm
from app.domain.compliance import family_completion
from app.domain.enums import KycStatus, PayeezzStatus, ReportExportFormat, ReportType, VerificationStatus
from app.domain.reports import ReportDefinition, get_report_definition
from app.models.family import Family, Member
from app.models.reporting import ReportExport
from app.models.user import User
from app.schemas.reports import ReportExportResult, ReportListFilters
from app.services.report_renderers import render_report

UNASSIGNED_RM_NAME = "Unassigned"


@dataclass(frozen=True)
class ReportQueryResult:
    definition: ReportDefinition
    rows: list[dict[str, Any]]
    total: int
    filters: dict[str, Any]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _forbidden(message: str) -> None:
    raise_api_error(status.HTTP_403_FORBIDDEN, "forbidden", message)


def _validation_error(code: str, message: str) -> None:
    raise_api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, code, message)


def parse_report_type(value: str) -> ReportType:
    try:
        return ReportType(value)
    except ValueError:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "invalid_report_type",
            "Report type is not supported.",
        )


def parse_report_export_format(value: str) -> ReportExportFormat:
    try:
        return ReportExportFormat(value.lower())
    except ValueError:
        _validation_error(
            "invalid_report_format",
            "Report format must be one of: csv, xlsx, pdf.",
        )


def _effective_rm_id(actor: User, requested_rm_id: UUID | None) -> UUID | None:
    if user_is_can_rm(actor):
        if requested_rm_id is not None:
            _forbidden("RM users are automatically scoped and cannot use rm_id filters.")
        return actor.id
    return requested_rm_id


def _serialized_filters(*, actor: User, filters: ReportListFilters) -> dict[str, Any]:
    rm_id = _effective_rm_id(actor, filters.rm_id)
    return {
        "rm_id": str(rm_id) if rm_id is not None else None,
        "family_id": str(filters.family_id) if filters.family_id is not None else None,
    }


def _member_filters(*, actor: User, filters: ReportListFilters) -> list[object]:
    conditions: list[object] = [
        Member.deleted_at.is_(None),
        Family.deleted_at.is_(None),
    ]
    rm_id = _effective_rm_id(actor, filters.rm_id)
    if rm_id is not None:
        conditions.append(Family.primary_rm_id == rm_id)
    if filters.family_id is not None:
        conditions.append(Member.family_id == filters.family_id)
    return conditions


def _family_filters(*, actor: User, filters: ReportListFilters) -> list[object]:
    conditions: list[object] = [Family.deleted_at.is_(None)]
    rm_id = _effective_rm_id(actor, filters.rm_id)
    if rm_id is not None:
        conditions.append(Family.primary_rm_id == rm_id)
    if filters.family_id is not None:
        conditions.append(Family.id == filters.family_id)
    return conditions


def _report_member_filters(report_type: ReportType) -> list[object]:
    if report_type == ReportType.KYC_PENDING:
        return [Member.kyc_status != KycStatus.VERIFIED.value]
    if report_type == ReportType.PAYEEZZ_PENDING:
        return [Member.payeezz_mandate_status != PayeezzStatus.APPROVED.value]
    if report_type == ReportType.CONTACT_PENDING:
        return [
            (Member.mobile_verification_status == VerificationStatus.PENDING_VERIFICATION.value)
            | (Member.email_verification_status == VerificationStatus.PENDING_VERIFICATION.value)
            | (Member.nominee_verification_status == VerificationStatus.PENDING_VERIFICATION.value)
        ]
    return []


def _member_row(member: Member) -> dict[str, Any]:
    family = member.family
    rm = family.primary_rm
    return {
        "name": member.name,
        "can_number": member.can_number,
        "can_status": member.can_status,
        "pan_masked": member.pan_masked,
        "date_of_birth": member.date_of_birth,
        "kyc_status": member.kyc_status,
        "mobile_verification_status": member.mobile_verification_status,
        "email_verification_status": member.email_verification_status,
        "nominee_verification_status": member.nominee_verification_status,
        "payeezz_mandate_status": member.payeezz_mandate_status,
        "bank_name": member.bank_name,
        "bank_account_number_masked": member.bank_account_number_masked,
        "ifsc_code": member.ifsc_code,
        "family_head_name": family.family_head_name,
        "family_code": family.family_code,
        "rm_name": rm.name if rm is not None else UNASSIGNED_RM_NAME,
        "last_updated_at": _as_utc(member.updated_at),
    }


def _project_row(definition: ReportDefinition, row: dict[str, Any]) -> dict[str, Any]:
    return {column.key: row.get(column.key) for column in definition.columns}


def _family_row(family: Family) -> dict[str, Any]:
    active_members = [member for member in family.members if member.deleted_at is None]
    completion = family_completion(active_members)
    return {
        "family_head_name": family.family_head_name,
        "family_code": family.family_code,
        "rm_name": family.primary_rm.name if family.primary_rm is not None else UNASSIGNED_RM_NAME,
        "members": completion.total_members,
        "kyc_percentage": completion.kyc_completion_pct,
        "payeezz_percentage": completion.payeezz_completion_pct,
        "mobile_percentage": completion.mobile_verification_pct,
        "email_percentage": completion.email_verification_pct,
        "nominee_percentage": completion.nominee_verification_pct,
    }


def _member_report_rows(
    db: Session,
    *,
    report_type: ReportType,
    actor: User,
    filters: ReportListFilters,
    limit: int | None,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    conditions = [*_member_filters(actor=actor, filters=filters), *_report_member_filters(report_type)]
    total = db.scalar(select(func.count(Member.id)).select_from(Member).join(Member.family).where(*conditions)) or 0
    statement = (
        select(Member)
        .select_from(Member)
        .join(Member.family)
        .options(joinedload(Member.family).joinedload(Family.primary_rm))
        .where(*conditions)
        .order_by(Family.family_code, Member.name, Member.id)
        .offset(offset)
    )
    if limit is not None:
        statement = statement.limit(limit)
    members = list(db.scalars(statement).all())
    return [_member_row(member) for member in members], int(total)


def _family_report_rows(
    db: Session,
    *,
    actor: User,
    filters: ReportListFilters,
    limit: int | None,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    conditions = _family_filters(actor=actor, filters=filters)
    total = db.scalar(select(func.count(Family.id)).where(*conditions)) or 0
    statement = (
        select(Family)
        .options(selectinload(Family.members), selectinload(Family.primary_rm))
        .where(*conditions)
        .order_by(Family.family_code, Family.id)
        .offset(offset)
    )
    if limit is not None:
        statement = statement.limit(limit)
    families = list(db.scalars(statement).all())
    return [_family_row(family) for family in families], int(total)


def _count_when(condition: object):
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


def _rm_task_rows(
    db: Session,
    *,
    actor: User,
    filters: ReportListFilters,
    limit: int | None,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    conditions = _member_filters(actor=actor, filters=filters)
    kyc_count = _count_when(Member.kyc_status.in_([KycStatus.PENDING_REKYC.value, KycStatus.NOT_STARTED.value]))
    payeezz_count = _count_when(Member.payeezz_mandate_status != PayeezzStatus.APPROVED.value)
    mobile_count = _count_when(Member.mobile_verification_status == VerificationStatus.PENDING_VERIFICATION.value)
    email_count = _count_when(Member.email_verification_status == VerificationStatus.PENDING_VERIFICATION.value)
    nominee_count = _count_when(Member.nominee_verification_status == VerificationStatus.PENDING_VERIFICATION.value)
    total_count = kyc_count + payeezz_count + mobile_count + email_count + nominee_count

    grouped = (
        select(
            func.coalesce(User.name, UNASSIGNED_RM_NAME).label("rm_name"),
            kyc_count.label("kyc_count"),
            payeezz_count.label("payeezz_count"),
            mobile_count.label("mobile_count"),
            email_count.label("email_count"),
            nominee_count.label("nominee_count"),
            total_count.label("total"),
        )
        .select_from(Member)
        .join(Member.family)
        .outerjoin(User, Family.primary_rm_id == User.id)
        .where(*conditions)
        .group_by(Family.primary_rm_id, User.name)
        .having(total_count > 0)
        .order_by(func.coalesce(User.name, UNASSIGNED_RM_NAME), Family.primary_rm_id)
    )
    grouped_subquery = grouped.subquery()
    total = db.scalar(select(func.count()).select_from(grouped_subquery)) or 0
    statement = select(grouped_subquery)
    if limit is not None:
        statement = statement.limit(limit)
    rows = list(db.execute(statement.offset(offset)).mappings().all())
    return [
        {
            "rm_name": row["rm_name"],
            "kyc_count": int(row["kyc_count"] or 0),
            "payeezz_count": int(row["payeezz_count"] or 0),
            "mobile_count": int(row["mobile_count"] or 0),
            "email_count": int(row["email_count"] or 0),
            "nominee_count": int(row["nominee_count"] or 0),
            "total": int(row["total"] or 0),
        }
        for row in rows
    ], int(total)


def list_report_rows(
    db: Session,
    *,
    report_type: str,
    actor: User,
    filters: ReportListFilters,
    limit: int | None,
    offset: int,
) -> ReportQueryResult:
    parsed_report_type = parse_report_type(report_type)
    definition = get_report_definition(parsed_report_type)
    serialized_filters = _serialized_filters(actor=actor, filters=filters)

    if parsed_report_type == ReportType.FAMILY_COMPLIANCE:
        rows, total = _family_report_rows(db, actor=actor, filters=filters, limit=limit, offset=offset)
    elif parsed_report_type == ReportType.RM_TASKS:
        rows, total = _rm_task_rows(db, actor=actor, filters=filters, limit=limit, offset=offset)
    else:
        rows, total = _member_report_rows(
            db,
            report_type=parsed_report_type,
            actor=actor,
            filters=filters,
            limit=limit,
            offset=offset,
        )

    return ReportQueryResult(definition=definition, rows=rows, total=total, filters=serialized_filters)


def preview_report(
    db: Session,
    *,
    report_type: str,
    actor: User,
    filters: ReportListFilters,
) -> dict[str, Any]:
    result = list_report_rows(
        db,
        report_type=report_type,
        actor=actor,
        filters=filters,
        limit=filters.limit,
        offset=filters.offset,
    )
    return {
        "report_type": result.definition.report_type,
        "title": result.definition.title,
        "columns": [{"key": column.key, "label": column.label} for column in result.definition.columns],
        "items": [_project_row(result.definition, row) for row in result.rows],
        "total": result.total,
        "limit": filters.limit,
        "offset": filters.offset,
        "filters": result.filters,
    }


def export_report(
    db: Session,
    *,
    report_type: str,
    export_format: ReportExportFormat,
    actor: User,
    filters: ReportListFilters,
) -> ReportExportResult:
    result = list_report_rows(
        db,
        report_type=report_type,
        actor=actor,
        filters=filters,
        limit=None,
        offset=0,
    )
    generated_at = _utc_now()
    filename = f"{result.definition.report_type}-{generated_at:%Y%m%d%H%M%S}.{export_format.value}"
    rendered = render_report(
        result.definition,
        result.rows,
        export_format,
        filename=filename,
        generated_at=generated_at,
        filters=result.filters,
        actor=actor,
    )
    db.add(
        ReportExport(
            report_type=ReportType(result.definition.report_type),
            format=export_format,
            filters=result.filters,
            row_count=result.total,
            exported_by_user_id=actor.id,
        )
    )
    db.commit()
    return ReportExportResult(
        report_type=ReportType(result.definition.report_type),
        format=export_format,
        filename=rendered.filename,
        media_type=rendered.media_type,
        content=rendered.content,
        row_count=result.total,
    )
