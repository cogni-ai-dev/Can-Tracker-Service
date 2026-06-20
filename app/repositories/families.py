from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.pii import email_search_hash, mobile_search_hash, pan_search_hash
from app.domain.access import user_is_can_rm
from app.domain.enums import KycStatus, PayeezzStatus, VerificationStatus
from app.models.family import Family, Member
from app.models.user import User


def family_visibility_filter(user: User):
    if user_is_can_rm(user):
        return Family.primary_rm_id == user.id
    return True


def active_family_filters(user: User) -> list[object]:
    return [Family.deleted_at.is_(None), family_visibility_filter(user)]


def active_member_exists(*criteria: object):
    return (
        select(Member.id)
        .where(
            Member.family_id == Family.id,
            Member.deleted_at.is_(None),
            *criteria,
        )
        .exists()
    )


def _status_value(value: object | None) -> object | None:
    return value.value if hasattr(value, "value") else value


def _search_filter(q: str | None, settings: Settings) -> object | None:
    if q is None or not q.strip():
        return None
    term = q.strip()
    like = f"%{term}%"
    return or_(
        Family.family_head_name.ilike(like),
        Family.family_code.ilike(like),
        active_member_exists(
            or_(
                Member.name.ilike(like),
                Member.can_number.ilike(like),
                Member.pan_search_hash == pan_search_hash(term, settings),
                Member.mobile_search_hash == mobile_search_hash(term, settings),
                Member.email_search_hash == email_search_hash(term, settings),
            )
        ),
    )


def _status_filter(status_filter: str | None) -> object | None:
    if status_filter in (None, "all"):
        return None
    if status_filter == "kyc_pending":
        return active_member_exists(Member.kyc_status.in_([KycStatus.REGISTERED.value, KycStatus.NO_KYC.value]))
    if status_filter == "payeezz_pending":
        return active_member_exists(Member.payeezz_status != PayeezzStatus.AGGREGATOR_ACCEPTED.value)
    if status_filter == "contact_pending":
        return active_member_exists(
            or_(
                Member.mobile_status == VerificationStatus.NOT_VERIFIED.value,
                Member.email_status == VerificationStatus.NOT_VERIFIED.value,
            )
        )
    if status_filter == "nominee_pending":
        return active_member_exists(Member.nominee_status == VerificationStatus.NOT_VERIFIED.value)
    return None


def family_filter_conditions(
    *,
    user: User,
    settings: Settings,
    q: str | None = None,
    rm_id: UUID | None = None,
    status_filter: str | None = None,
    kyc_status: KycStatus | str | None = None,
    payeezz_status: PayeezzStatus | str | None = None,
    mobile_status: VerificationStatus | str | None = None,
    email_status: VerificationStatus | str | None = None,
    nominee_status: VerificationStatus | str | None = None,
) -> list[object]:
    filters = active_family_filters(user)
    if rm_id is not None:
        filters.append(Family.primary_rm_id == rm_id)
    search_filter = _search_filter(q, settings)
    if search_filter is not None:
        filters.append(search_filter)
    pending_filter = _status_filter(status_filter)
    if pending_filter is not None:
        filters.append(pending_filter)
    if kyc_status is not None:
        filters.append(active_member_exists(Member.kyc_status == _status_value(kyc_status)))
    if payeezz_status is not None:
        filters.append(active_member_exists(Member.payeezz_status == _status_value(payeezz_status)))
    if mobile_status is not None:
        filters.append(active_member_exists(Member.mobile_status == _status_value(mobile_status)))
    if email_status is not None:
        filters.append(active_member_exists(Member.email_status == _status_value(email_status)))
    if nominee_status is not None:
        filters.append(active_member_exists(Member.nominee_status == _status_value(nominee_status)))
    return filters


def _family_order_by(sort: str):
    return {
        "family_code": Family.family_code,
        "-family_code": Family.family_code.desc(),
        "updated_at": Family.updated_at,
        "-updated_at": Family.updated_at.desc(),
        "-family_head_name": Family.family_head_name.desc(),
    }.get(sort, Family.family_head_name)


def list_families(
    db: Session,
    *,
    user: User,
    settings: Settings,
    q: str | None = None,
    rm_id: UUID | None = None,
    status_filter: str | None = "all",
    kyc_status: KycStatus | str | None = None,
    payeezz_status: PayeezzStatus | str | None = None,
    mobile_status: VerificationStatus | str | None = None,
    email_status: VerificationStatus | str | None = None,
    nominee_status: VerificationStatus | str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "family_head_name",
) -> tuple[list[Family], int]:
    filters = family_filter_conditions(
        user=user,
        settings=settings,
        q=q,
        rm_id=rm_id,
        status_filter=status_filter,
        kyc_status=kyc_status,
        payeezz_status=payeezz_status,
        mobile_status=mobile_status,
        email_status=email_status,
        nominee_status=nominee_status,
    )
    total = db.scalar(select(func.count(Family.id)).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Family)
            .options(selectinload(Family.members), selectinload(Family.primary_rm))
            .where(*filters)
            .order_by(_family_order_by(sort), Family.id)
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return items, total


def get_active_family(db: Session, family_id: UUID, user: User) -> Family | None:
    return db.scalar(
        select(Family)
        .options(selectinload(Family.members), selectinload(Family.primary_rm))
        .where(
            Family.id == family_id,
            *active_family_filters(user),
        )
    )


def find_active_family_by_code(
    db: Session,
    family_code: str,
    *,
    exclude_family_id: UUID | None = None,
) -> Family | None:
    filters = [Family.family_code == family_code, Family.deleted_at.is_(None)]
    if exclude_family_id is not None:
        filters.append(Family.id != exclude_family_id)
    return db.scalar(select(Family).where(*filters))


def active_family_statement_for_update(user: User) -> Select[tuple[Family]]:
    return select(Family).where(*active_family_filters(user))
