from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db, get_request_id, require_module_roles, require_user
from app.core.config import Settings
from app.domain.enums import KycStatus, ModuleCode, ModuleRole, PayeezzStatus, VerificationStatus
from app.models.user import User
from app.schemas.members import MemberListFilters, MemberListResponse, MemberRead, MemberUpdate
from app.services.family_members import (
    delete_member_record,
    get_member_record,
    list_member_records,
    update_member_record,
)

router = APIRouter(prefix="/members", tags=["members"])

require_member_read = require_module_roles(
    ModuleCode.CAN_COMPLIANCE,
    ModuleRole.CAN_ADMIN,
    ModuleRole.CAN_OPS,
    ModuleRole.CAN_RM,
    ModuleRole.CAN_MANAGEMENT,
)
require_member_delete = require_module_roles(ModuleCode.CAN_COMPLIANCE, ModuleRole.CAN_ADMIN, ModuleRole.CAN_OPS)


def _request_id(request: Request) -> str | None:
    return get_request_id(request)


def member_list_filters(
    q: Annotated[str | None, Query()] = None,
    family_id: Annotated[UUID | None, Query()] = None,
    rm_id: Annotated[UUID | None, Query()] = None,
    kyc_status: Annotated[KycStatus | None, Query()] = None,
    payeezz_status: Annotated[PayeezzStatus | None, Query()] = None,
    mobile_status: Annotated[VerificationStatus | None, Query()] = None,
    email_status: Annotated[VerificationStatus | None, Query()] = None,
    nominee_status: Annotated[VerificationStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MemberListFilters:
    return MemberListFilters(
        q=q,
        family_id=family_id,
        rm_id=rm_id,
        kyc_status=kyc_status,
        payeezz_status=payeezz_status,
        mobile_status=mobile_status,
        email_status=email_status,
        nominee_status=nominee_status,
        limit=limit,
        offset=offset,
    )


@router.get("", response_model=MemberListResponse, response_model_exclude_none=True)
def list_members(
    request: Request,
    filters: MemberListFilters = Depends(member_list_filters),
    include_sensitive: Annotated[bool, Query()] = False,
    current_user: User = Depends(require_member_read),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    return list_member_records(
        db,
        filters=filters,
        actor=current_user,
        settings=settings,
        include_sensitive=include_sensitive,
        request_id=_request_id(request),
    )


@router.get("/{member_id}", response_model=MemberRead, response_model_exclude_none=True)
def get_member(
    member_id: UUID,
    request: Request,
    include_sensitive: Annotated[bool, Query()] = False,
    current_user: User = Depends(require_member_read),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    return get_member_record(
        db,
        member_id=member_id,
        actor=current_user,
        settings=settings,
        include_sensitive=include_sensitive,
        request_id=_request_id(request),
    )


@router.patch("/{member_id}", response_model=MemberRead, response_model_exclude_none=True)
def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    request: Request,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    return update_member_record(
        db,
        member_id=member_id,
        payload=payload,
        actor=current_user,
        settings=settings,
        request_id=_request_id(request),
    )


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: UUID,
    request: Request,
    current_user: User = Depends(require_member_delete),
    db: Session = Depends(get_db),
) -> None:
    delete_member_record(db, member_id=member_id, actor=current_user, request_id=_request_id(request))
