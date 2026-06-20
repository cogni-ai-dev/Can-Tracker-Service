from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_module_roles
from app.domain.enums import ModuleCode, ModuleRole
from app.models.user import User
from app.schemas.reports import ReportListFilters, ReportPreviewResponse
from app.services.reports import export_report, parse_report_export_format, preview_report

router = APIRouter(prefix="/reports", tags=["reports"])

require_report_read = require_module_roles(
    ModuleCode.CAN_COMPLIANCE,
    ModuleRole.CAN_ADMIN,
    ModuleRole.CAN_OPS,
    ModuleRole.CAN_RM,
    ModuleRole.CAN_MANAGEMENT,
)


def report_list_filters(
    rm_id: Annotated[UUID | None, Query()] = None,
    family_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReportListFilters:
    return ReportListFilters(rm_id=rm_id, family_id=family_id, limit=limit, offset=offset)


@router.get("/{report_type}/preview", response_model=ReportPreviewResponse)
def report_preview(
    report_type: str,
    filters: ReportListFilters = Depends(report_list_filters),
    current_user: User = Depends(require_report_read),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return preview_report(db, report_type=report_type, actor=current_user, filters=filters)


@router.get("/{report_type}/export")
def report_export(
    report_type: str,
    export_format: Annotated[str, Query(alias="format")] = "csv",
    rm_id: Annotated[UUID | None, Query()] = None,
    family_id: Annotated[UUID | None, Query()] = None,
    current_user: User = Depends(require_report_read),
    db: Session = Depends(get_db),
) -> Response:
    parsed_format = parse_report_export_format(export_format)
    result = export_report(
        db,
        report_type=report_type,
        export_format=parsed_format,
        actor=current_user,
        filters=ReportListFilters(rm_id=rm_id, family_id=family_id),
    )
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Report-Row-Count": str(result.row_count),
        },
    )
