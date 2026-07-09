from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.pii import email_search_hash, mobile_search_hash, pan_search_hash
from app.domain.access import user_is_can_rm
from app.domain.enums import CanStatus, KycStatus, PayeezzStatus, VerificationStatus
from app.models.family import Family, Member, MemberBankAccount
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


def primary_payeezz_status_for_member():
    return (
        select(MemberBankAccount.payeezz_mandate_status)
        .where(
            MemberBankAccount.member_id == Member.id,
            MemberBankAccount.deleted_at.is_(None),
            MemberBankAccount.is_primary.is_(True),
        )
        .limit(1)
        .scalar_subquery()
    )


def active_member_with_payeezz_status(status: object):
    primary_status = primary_payeezz_status_for_member()
    if status == PayeezzStatus.NOT_STARTED.value:
        return active_member_exists((primary_status == status) | primary_status.is_(None))
    return active_member_exists(primary_status == status)


def active_member_payeezz_pending():
    primary_status = primary_payeezz_status_for_member()
    return active_member_exists((primary_status != PayeezzStatus.APPROVED.value) | primary_status.is_(None))


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
        return active_member_exists(Member.kyc_status.in_([KycStatus.PENDING_REKYC.value, KycStatus.NOT_STARTED.value]))
    if status_filter == "payeezz_pending":
        return active_member_payeezz_pending()
    if status_filter == "contact_pending":
        return active_member_exists(
            or_(
                Member.mobile_verification_status == VerificationStatus.PENDING_VERIFICATION.value,
                Member.email_verification_status == VerificationStatus.PENDING_VERIFICATION.value,
            )
        )
    if status_filter == "nominee_pending":
        return active_member_exists(Member.nominee_verification_status == VerificationStatus.PENDING_VERIFICATION.value)
    return None


def family_filter_conditions(
    *,
    user: User,
    settings: Settings,
    q: str | None = None,
    rm_id: UUID | None = None,
    status_filter: str | None = None,
    can_status: CanStatus | str | None = None,
    kyc_status: KycStatus | str | None = None,
    payeezz_mandate_status: PayeezzStatus | str | None = None,
    mobile_verification_status: VerificationStatus | str | None = None,
    email_verification_status: VerificationStatus | str | None = None,
    nominee_verification_status: VerificationStatus | str | None = None,
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
    if can_status is not None:
        filters.append(active_member_exists(Member.can_status == _status_value(can_status)))
    if kyc_status is not None:
        filters.append(active_member_exists(Member.kyc_status == _status_value(kyc_status)))
    if payeezz_mandate_status is not None:
        filters.append(active_member_with_payeezz_status(_status_value(payeezz_mandate_status)))
    if mobile_verification_status is not None:
        filters.append(active_member_exists(Member.mobile_verification_status == _status_value(mobile_verification_status)))
    if email_verification_status is not None:
        filters.append(active_member_exists(Member.email_verification_status == _status_value(email_verification_status)))
    if nominee_verification_status is not None:
        filters.append(active_member_exists(Member.nominee_verification_status == _status_value(nominee_verification_status)))
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
    can_status: CanStatus | str | None = None,
    kyc_status: KycStatus | str | None = None,
    payeezz_mandate_status: PayeezzStatus | str | None = None,
    mobile_verification_status: VerificationStatus | str | None = None,
    email_verification_status: VerificationStatus | str | None = None,
    nominee_verification_status: VerificationStatus | str | None = None,
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
        can_status=can_status,
        kyc_status=kyc_status,
        payeezz_mandate_status=payeezz_mandate_status,
        mobile_verification_status=mobile_verification_status,
        email_verification_status=email_verification_status,
        nominee_verification_status=nominee_verification_status,
    )
    total = db.scalar(select(func.count(Family.id)).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Family)
            .options(selectinload(Family.members).selectinload(Member.bank_accounts), selectinload(Family.primary_rm))
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
        .options(selectinload(Family.members).selectinload(Member.bank_accounts), selectinload(Family.primary_rm))
        .where(
            Family.id == family_id,
            *active_family_filters(user),
        )
    )


def find_active_family_by_code(
    db: Session,
    family_code: str | None,
    *,
    exclude_family_id: UUID | None = None,
) -> Family | None:
    if family_code is None:
        return None
    filters = [Family.family_code == family_code, Family.deleted_at.is_(None)]
    if exclude_family_id is not None:
        filters.append(Family.id != exclude_family_id)
    return db.scalar(select(Family).where(*filters))


def find_active_families_by_head_and_rm(
    db: Session,
    *,
    family_head_name: str,
    primary_rm_id: UUID | None,
) -> list[Family]:
    rm_filter = Family.primary_rm_id.is_(None) if primary_rm_id is None else Family.primary_rm_id == primary_rm_id
    return list(
        db.scalars(
            select(Family)
            .where(
                func.lower(Family.family_head_name) == family_head_name.strip().lower(),
                rm_filter,
                Family.deleted_at.is_(None),
            )
            .order_by(Family.created_at, Family.id)
        )
    )


def list_family_codes_with_prefix(db: Session, prefix: str) -> list[str]:
    return list(db.scalars(select(Family.family_code).where(Family.family_code.like(f"{prefix}%"))))


def active_family_statement_for_update(user: User) -> Select[tuple[Family]]:
    return select(Family).where(*active_family_filters(user))
