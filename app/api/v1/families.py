from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db, get_request_id, require_roles, require_user
from app.core.config import Settings
from app.domain.enums import KycStatus, PayeezzStatus, UserRole, VerificationStatus
from app.models.user import User
from app.schemas.families import (
    FamilyCreate,
    FamilyListFilters,
    FamilyListResponse,
    FamilyRead,
    FamilyStatusFilter,
    FamilyUpdate,
)
from app.schemas.members import MemberCreate, MemberListFilters, MemberListResponse, MemberRead
from app.services.family_members import (
    create_family_record,
    create_member_record,
    delete_family_record,
    get_family_record,
    list_family_records,
    list_member_records,
    update_family_record,
)

router = APIRouter(prefix="/families", tags=["families"])

require_family_read = require_roles(UserRole.ADMIN, UserRole.OPS, UserRole.RM, UserRole.MANAGEMENT)
require_family_create = require_roles(UserRole.ADMIN, UserRole.OPS)
require_family_delete = require_roles(UserRole.ADMIN, UserRole.OPS)


def _request_id(request: Request) -> str | None:
    return get_request_id(request)


def family_list_filters(
    q: Annotated[str | None, Query()] = None,
    rm_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[FamilyStatusFilter, Query()] = FamilyStatusFilter.ALL,
    kyc_status: Annotated[KycStatus | None, Query()] = None,
    payeezz_status: Annotated[PayeezzStatus | None, Query()] = None,
    mobile_status: Annotated[VerificationStatus | None, Query()] = None,
    email_status: Annotated[VerificationStatus | None, Query()] = None,
    nominee_status: Annotated[VerificationStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    sort: Annotated[str, Query()] = "family_head_name",
) -> FamilyListFilters:
    return FamilyListFilters(
        q=q,
        rm_id=rm_id,
        status_filter=status_filter,
        kyc_status=kyc_status,
        payeezz_status=payeezz_status,
        mobile_status=mobile_status,
        email_status=email_status,
        nominee_status=nominee_status,
        limit=limit,
        offset=offset,
        sort=sort,
    )


def member_filters_for_family(
    q: Annotated[str | None, Query()] = None,
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
        rm_id=rm_id,
        kyc_status=kyc_status,
        payeezz_status=payeezz_status,
        mobile_status=mobile_status,
        email_status=email_status,
        nominee_status=nominee_status,
        limit=limit,
        offset=offset,
    )


@router.get("", response_model=FamilyListResponse)
def list_families(
    filters: FamilyListFilters = Depends(family_list_filters),
    current_user: User = Depends(require_family_read),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    return list_family_records(db, filters=filters, actor=current_user, settings=settings)


@router.post("", response_model=FamilyRead, status_code=status.HTTP_201_CREATED)
def create_family(
    payload: FamilyCreate,
    request: Request,
    current_user: User = Depends(require_family_create),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return create_family_record(db, payload=payload, actor=current_user, request_id=_request_id(request))


@router.get("/{family_id}", response_model=FamilyRead)
def get_family(
    family_id: UUID,
    current_user: User = Depends(require_family_read),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return get_family_record(db, family_id=family_id, actor=current_user)


@router.patch("/{family_id}", response_model=FamilyRead)
def update_family(
    family_id: UUID,
    payload: FamilyUpdate,
    request: Request,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return update_family_record(
        db,
        family_id=family_id,
        payload=payload,
        actor=current_user,
        request_id=_request_id(request),
    )


@router.delete("/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_family(
    family_id: UUID,
    request: Request,
    current_user: User = Depends(require_family_delete),
    db: Session = Depends(get_db),
) -> None:
    delete_family_record(db, family_id=family_id, actor=current_user, request_id=_request_id(request))


@router.get("/{family_id}/members", response_model=MemberListResponse, response_model_exclude_none=True)
def list_family_members(
    family_id: UUID,
    request: Request,
    filters: MemberListFilters = Depends(member_filters_for_family),
    include_sensitive: Annotated[bool, Query()] = False,
    current_user: User = Depends(require_family_read),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    get_family_record(db, family_id=family_id, actor=current_user)
    filters.family_id = family_id
    return list_member_records(
        db,
        filters=filters,
        actor=current_user,
        settings=settings,
        include_sensitive=include_sensitive,
        request_id=_request_id(request),
    )


@router.post(
    "/{family_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_none=True,
)
def create_family_member(
    family_id: UUID,
    payload: MemberCreate,
    request: Request,
    current_user: User = Depends(require_family_create),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, object]:
    return create_member_record(
        db,
        family_id=family_id,
        payload=payload,
        actor=current_user,
        settings=settings,
        request_id=_request_id(request),
    )
