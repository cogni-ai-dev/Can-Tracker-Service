from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error
from app.core.config import Settings
from app.domain.compliance import family_completion, percentage
from app.domain.enums import KycStatus, PayeezzStatus, UserRole, VerificationStatus
from app.models.family import Family, Member
from app.models.user import User
from app.repositories import families as family_repo
from app.services.family_members import member_to_response


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _forbidden(message: str) -> None:
    raise_api_error(status.HTTP_403_FORBIDDEN, "forbidden", message)


def _not_found(entity: str) -> None:
    raise_api_error(
        status.HTTP_404_NOT_FOUND,
        f"{entity}_not_found",
        f"{entity.replace('_', ' ').title()} was not found.",
    )


def _user_summary(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }


def _effective_rm_id(actor: User, requested_rm_id: UUID | None) -> UUID | None:
    if actor.role == UserRole.RM:
        if requested_rm_id is not None:
            _forbidden("RM users are automatically scoped and cannot use rm_id filters.")
        return actor.id
    return requested_rm_id


def _family_scope_filters(actor: User, requested_rm_id: UUID | None) -> list[object]:
    filters: list[object] = [Family.deleted_at.is_(None)]
    rm_id = _effective_rm_id(actor, requested_rm_id)
    if rm_id is not None:
        filters.append(Family.primary_rm_id == rm_id)
    return filters


def _member_scope_filters(actor: User, requested_rm_id: UUID | None) -> list[object]:
    return [
        Member.deleted_at.is_(None),
        Family.deleted_at.is_(None),
        *_family_scope_filters(actor, requested_rm_id)[1:],
    ]


def _count_when(condition: object):
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


def get_dashboard_summary(
    db: Session,
    *,
    actor: User,
    rm_id: UUID | None = None,
) -> dict[str, Any]:
    family_filters = _family_scope_filters(actor, rm_id)
    member_filters = _member_scope_filters(actor, rm_id)

    total_families = db.scalar(select(func.count(Family.id)).where(*family_filters)) or 0
    row = db.execute(
        select(
            func.count(Member.id).label("total_clients"),
            _count_when(Member.kyc_status == KycStatus.VALIDATED.value).label("kyc_validated"),
            _count_when(Member.kyc_status == KycStatus.REGISTERED.value).label("kyc_registered"),
            _count_when(Member.kyc_status == KycStatus.NO_KYC.value).label("kyc_no_kyc"),
            _count_when(Member.payeezz_status == PayeezzStatus.AGGREGATOR_ACCEPTED.value).label("payeezz_accepted"),
            _count_when(Member.payeezz_status == PayeezzStatus.SENT_FOR_APPROVAL.value).label(
                "payeezz_sent_for_approval"
            ),
            _count_when(Member.payeezz_status == PayeezzStatus.NOT_AVAILABLE.value).label("payeezz_not_available"),
            _count_when(Member.mobile_status == VerificationStatus.VERIFIED.value).label("mobile_verified"),
            _count_when(Member.mobile_status == VerificationStatus.NOT_VERIFIED.value).label("mobile_not_verified"),
            _count_when(Member.email_status == VerificationStatus.VERIFIED.value).label("email_verified"),
            _count_when(Member.email_status == VerificationStatus.NOT_VERIFIED.value).label("email_not_verified"),
            _count_when(Member.nominee_status == VerificationStatus.VERIFIED.value).label("nominee_verified"),
            _count_when(Member.nominee_status == VerificationStatus.NOT_VERIFIED.value).label("nominee_not_verified"),
        )
        .select_from(Member)
        .join(Member.family)
        .where(*member_filters)
    ).one()
    counts = row._mapping

    total_clients = int(counts["total_clients"] or 0)
    kyc_validated = int(counts["kyc_validated"] or 0)
    kyc_registered = int(counts["kyc_registered"] or 0)
    kyc_no_kyc = int(counts["kyc_no_kyc"] or 0)
    kyc_pending = kyc_registered + kyc_no_kyc
    payeezz_accepted = int(counts["payeezz_accepted"] or 0)
    payeezz_sent_for_approval = int(counts["payeezz_sent_for_approval"] or 0)
    payeezz_not_available = int(counts["payeezz_not_available"] or 0)
    payeezz_pending = payeezz_sent_for_approval + payeezz_not_available

    family_updated_at = db.scalar(select(func.max(Family.updated_at)).where(*family_filters))
    member_updated_at = db.scalar(
        select(func.max(Member.updated_at)).select_from(Member).join(Member.family).where(*member_filters)
    )
    updated_values = [value for value in (family_updated_at, member_updated_at) if value is not None]
    updated_at = _as_utc(max(updated_values)) if updated_values else None

    return {
        "total_clients": total_clients,
        "total_families": int(total_families),
        "kyc_validated": kyc_validated,
        "kyc_registered": kyc_registered,
        "kyc_no_kyc": kyc_no_kyc,
        "kyc_pending": kyc_pending,
        "kyc_validated_pct": percentage(kyc_validated, total_clients),
        "kyc_pending_pct": percentage(kyc_pending, total_clients),
        "payeezz_accepted": payeezz_accepted,
        "payeezz_sent_for_approval": payeezz_sent_for_approval,
        "payeezz_not_available": payeezz_not_available,
        "payeezz_pending": payeezz_pending,
        "payeezz_accepted_pct": percentage(payeezz_accepted, total_clients),
        "payeezz_pending_pct": percentage(payeezz_pending, total_clients),
        "mobile_verified": int(counts["mobile_verified"] or 0),
        "mobile_not_verified": int(counts["mobile_not_verified"] or 0),
        "email_verified": int(counts["email_verified"] or 0),
        "email_not_verified": int(counts["email_not_verified"] or 0),
        "nominee_verified": int(counts["nominee_verified"] or 0),
        "nominee_not_verified": int(counts["nominee_not_verified"] or 0),
        "updated_at": updated_at,
    }


def get_family_dashboard_summary(
    db: Session,
    *,
    family_id: UUID,
    actor: User,
    settings: Settings,
) -> dict[str, Any]:
    family = family_repo.get_active_family(db, family_id, actor)
    if family is None:
        _not_found("family")

    active_members = sorted(
        (member for member in family.members if member.deleted_at is None),
        key=lambda member: (member.name, str(member.id)),
    )
    completion = family_completion(active_members)
    updated_values = [family.updated_at, *(member.updated_at for member in active_members)]
    last_updated_at = _as_utc(max(updated_values))

    return {
        "id": family.id,
        "family_code": family.family_code,
        "family_head_name": family.family_head_name,
        "primary_rm": _user_summary(family.primary_rm),
        "remarks": family.remarks,
        "last_updated_at": last_updated_at,
        "number_of_members": completion.total_members,
        "total_cans": completion.total_cans,
        "kyc_completion_pct": completion.kyc_completion_pct,
        "mobile_verification_pct": completion.mobile_verification_pct,
        "email_verification_pct": completion.email_verification_pct,
        "nominee_verification_pct": completion.nominee_verification_pct,
        "payeezz_completion_pct": completion.payeezz_completion_pct,
        "members": [
            member_to_response(
                db,
                member,
                settings=settings,
                actor=actor,
            )
            for member in active_members
        ],
    }
