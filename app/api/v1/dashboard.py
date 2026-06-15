from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db, require_roles
from app.core.config import Settings
from app.domain.enums import UserRole
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryRead, FamilyDashboardSummaryRead
from app.services.dashboard import get_dashboard_summary, get_family_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

require_dashboard_read = require_roles(UserRole.ADMIN, UserRole.OPS, UserRole.RM, UserRole.MANAGEMENT)


@router.get("/summary", response_model=DashboardSummaryRead)
def dashboard_summary(
    rm_id: Annotated[UUID | None, Query()] = None,
    current_user: User = Depends(require_dashboard_read),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return get_dashboard_summary(db, actor=current_user, rm_id=rm_id)


@router.get(
    "/families/{family_id}",
    response_model=FamilyDashboardSummaryRead,
    response_model_exclude_none=True,
)
def family_dashboard_summary(
    family_id: UUID,
    current_user: User = Depends(require_dashboard_read),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    return get_family_dashboard_summary(db, family_id=family_id, actor=current_user, settings=settings)
