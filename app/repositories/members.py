from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import Settings
from app.core.pii import email_search_hash, mobile_search_hash, pan_search_hash
from app.domain.access import user_is_can_rm
from app.domain.enums import CanStatus, KycStatus, PayeezzStatus, VerificationStatus
from app.models.family import Family, Member, MemberBankAccount
from app.models.user import User


def _status_value(value: object | None) -> object | None:
    return value.value if hasattr(value, "value") else value


def member_visibility_filters(user: User) -> list[object]:
    filters: list[object] = [Member.deleted_at.is_(None), Family.deleted_at.is_(None)]
    if user_is_can_rm(user):
        filters.append(Family.primary_rm_id == user.id)
    return filters


def member_filter_conditions(
    *,
    user: User,
    settings: Settings,
    q: str | None = None,
    family_id: UUID | None = None,
    rm_id: UUID | None = None,
    can_status: CanStatus | str | None = None,
    kyc_status: KycStatus | str | None = None,
    payeezz_mandate_status: PayeezzStatus | str | None = None,
    mobile_verification_status: VerificationStatus | str | None = None,
    email_verification_status: VerificationStatus | str | None = None,
    nominee_verification_status: VerificationStatus | str | None = None,
) -> list[object]:
    filters = member_visibility_filters(user)
    if family_id is not None:
        filters.append(Member.family_id == family_id)
    if rm_id is not None:
        filters.append(Family.primary_rm_id == rm_id)
    if q is not None and q.strip():
        term = q.strip()
        like = f"%{term}%"
        filters.append(
            or_(
                Member.name.ilike(like),
                Member.can_number.ilike(like),
                Family.family_head_name.ilike(like),
                Family.family_code.ilike(like),
                Member.pan_search_hash == pan_search_hash(term, settings),
                Member.mobile_search_hash == mobile_search_hash(term, settings),
                Member.email_search_hash == email_search_hash(term, settings),
                Member.nominee_name.ilike(like),
            )
        )
    if can_status is not None:
        filters.append(Member.can_status == _status_value(can_status))
    if kyc_status is not None:
        filters.append(Member.kyc_status == _status_value(kyc_status))
    if payeezz_mandate_status is not None:
        status = _status_value(payeezz_mandate_status)
        primary_bank_status = (
            select(MemberBankAccount.payeezz_mandate_status)
            .where(
                MemberBankAccount.member_id == Member.id,
                MemberBankAccount.deleted_at.is_(None),
                MemberBankAccount.is_primary.is_(True),
            )
            .limit(1)
            .scalar_subquery()
        )
        if status == PayeezzStatus.NOT_STARTED.value:
            filters.append((primary_bank_status == status) | primary_bank_status.is_(None))
        else:
            filters.append(primary_bank_status == status)
    if mobile_verification_status is not None:
        filters.append(Member.mobile_verification_status == _status_value(mobile_verification_status))
    if email_verification_status is not None:
        filters.append(Member.email_verification_status == _status_value(email_verification_status))
    if nominee_verification_status is not None:
        filters.append(Member.nominee_verification_status == _status_value(nominee_verification_status))
    return filters


def list_members(
    db: Session,
    *,
    user: User,
    settings: Settings,
    q: str | None = None,
    family_id: UUID | None = None,
    rm_id: UUID | None = None,
    can_status: CanStatus | str | None = None,
    kyc_status: KycStatus | str | None = None,
    payeezz_mandate_status: PayeezzStatus | str | None = None,
    mobile_verification_status: VerificationStatus | str | None = None,
    email_verification_status: VerificationStatus | str | None = None,
    nominee_verification_status: VerificationStatus | str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Member], int]:
    filters = member_filter_conditions(
        user=user,
        settings=settings,
        q=q,
        family_id=family_id,
        rm_id=rm_id,
        can_status=can_status,
        kyc_status=kyc_status,
        payeezz_mandate_status=payeezz_mandate_status,
        mobile_verification_status=mobile_verification_status,
        email_verification_status=email_verification_status,
        nominee_verification_status=nominee_verification_status,
    )
    total = db.scalar(select(func.count(Member.id)).join(Member.family).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Member)
            .join(Member.family)
            .options(joinedload(Member.family).joinedload(Family.primary_rm), selectinload(Member.bank_accounts))
            .where(*filters)
            .order_by(Family.family_code, Member.name, Member.id)
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return items, total


def get_active_member(db: Session, member_id: UUID, user: User) -> Member | None:
    return db.scalar(
        select(Member)
        .join(Member.family)
        .options(joinedload(Member.family).joinedload(Family.primary_rm), selectinload(Member.bank_accounts))
        .where(
            Member.id == member_id,
            *member_visibility_filters(user),
        )
    )


def find_active_member_by_can(
    db: Session,
    can_number: str | None,
    *,
    exclude_member_id: UUID | None = None,
) -> Member | None:
    if can_number is None:
        return None
    filters = [Member.can_number == can_number, Member.deleted_at.is_(None)]
    if exclude_member_id is not None:
        filters.append(Member.id != exclude_member_id)
    return db.scalar(select(Member).where(*filters))
