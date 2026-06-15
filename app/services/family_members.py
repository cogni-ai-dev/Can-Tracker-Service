from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error
from app.core.config import Settings
from app.core.pii import (
    BANK_ACCOUNT_NUMBER_FIELD,
    EMAIL_FIELD,
    MOBILE_FIELD,
    PAN_FIELD,
    decrypt_pii_value,
    protect_pii_value,
)
from app.domain.compliance import CountPercentage, family_completion
from app.domain.enums import AuditAction, AuditEntityType, ChangeSource, UserRole
from app.models.audit import AuditLog
from app.models.family import Family, Member
from app.models.user import User
from app.repositories import families as family_repo
from app.repositories import members as member_repo
from app.schemas.families import FamilyCreate, FamilyListFilters, FamilyUpdate
from app.schemas.members import MemberCreate, MemberListFilters, MemberUpdate
from app.services.audit import record_create, record_delete, record_sensitive_read, record_update

PII_FIELD_ATTRS = {
    PAN_FIELD: ("pan_encrypted", "pan_masked", "pan_search_hash"),
    MOBILE_FIELD: ("mobile_encrypted", "mobile_masked", "mobile_search_hash"),
    EMAIL_FIELD: ("email_encrypted", "email_masked", "email_search_hash"),
    BANK_ACCOUNT_NUMBER_FIELD: (
        "bank_account_number_encrypted",
        "bank_account_number_masked",
        "bank_account_number_search_hash",
    ),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _not_found(entity: str) -> None:
    raise_api_error(
        status.HTTP_404_NOT_FOUND,
        f"{entity}_not_found",
        f"{entity.replace('_', ' ').title()} was not found.",
    )


def _validation_error(message: str) -> None:
    raise_api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error", message)


def _conflict(code: str, message: str) -> None:
    raise_api_error(status.HTTP_409_CONFLICT, code, message)


def _forbidden(message: str = "User role is not permitted for this action.") -> None:
    raise_api_error(status.HTTP_403_FORBIDDEN, "forbidden", message)


def _user_summary(user: User | None) -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }


def _count_percentage(value: CountPercentage) -> dict[str, int]:
    return {"count": value.count, "percentage": value.percentage}


def _active_members(family: Family) -> list[Member]:
    return [member for member in family.members if member.deleted_at is None]


def family_to_response(family: Family) -> dict[str, Any]:
    active_members = _active_members(family)
    completion = family_completion(active_members)
    updated_values = [family.updated_at, *(member.updated_at for member in active_members)]
    last_updated_at = max(updated_values)
    return {
        "id": family.id,
        "family_code": family.family_code,
        "family_head_name": family.family_head_name,
        "primary_rm": _user_summary(family.primary_rm),
        "total_members": completion.total_members,
        "total_cans": completion.total_cans,
        "last_updated_at": _as_utc(last_updated_at),
        "remarks": family.remarks,
        "kyc_completion": _count_percentage(completion.kyc_completion),
        "payeezz_completion": _count_percentage(completion.payeezz_completion),
        "mobile_verification": _count_percentage(completion.mobile_verification),
        "email_verification": _count_percentage(completion.email_verification),
        "nominee_verification": _count_percentage(completion.nominee_verification),
        "kyc_completion_pct": completion.kyc_completion_pct,
        "payeezz_completion_pct": completion.payeezz_completion_pct,
        "mobile_verification_pct": completion.mobile_verification_pct,
        "email_verification_pct": completion.email_verification_pct,
        "nominee_verification_pct": completion.nominee_verification_pct,
        "created_at": _as_utc(family.created_at),
        "updated_at": _as_utc(family.updated_at),
    }


def _latest_update_actor(db: Session, *, entity_type: AuditEntityType, entity_id: UUID) -> User | None:
    return db.scalar(
        select(User)
        .join(AuditLog, AuditLog.actor_user_id == User.id)
        .where(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
            AuditLog.action.in_([AuditAction.CREATE, AuditAction.UPDATE]),
        )
        .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
        .limit(1)
    )


def _decrypt_member_field(member: Member, field_name: str, settings: Settings) -> str | None:
    encrypted_attr = PII_FIELD_ATTRS[field_name][0]
    return decrypt_pii_value(field_name, getattr(member, encrypted_attr), settings)


def _set_protected_member_field(member: Member, field_name: str, value: object | None, settings: Settings) -> None:
    encrypted_attr, masked_attr, search_hash_attr = PII_FIELD_ATTRS[field_name]
    protected = protect_pii_value(field_name, value, settings)
    setattr(member, encrypted_attr, protected.ciphertext)
    setattr(member, masked_attr, protected.masked)
    setattr(member, search_hash_attr, protected.search_hash)


def _member_audit_values(member: Member, settings: Settings) -> dict[str, object | None]:
    return {
        "name": member.name,
        "can_number": member.can_number,
        "pan": _decrypt_member_field(member, PAN_FIELD, settings),
        "date_of_birth": member.date_of_birth,
        "kyc_status": member.kyc_status,
        "mobile": _decrypt_member_field(member, MOBILE_FIELD, settings),
        "mobile_status": member.mobile_status,
        "email": _decrypt_member_field(member, EMAIL_FIELD, settings),
        "email_status": member.email_status,
        "nominee_status": member.nominee_status,
        "bank_name": member.bank_name,
        "bank_account_number": _decrypt_member_field(member, BANK_ACCOUNT_NUMBER_FIELD, settings),
        "ifsc_code": member.ifsc_code,
        "payeezz_status": member.payeezz_status,
        "payeezz_amount": member.payeezz_amount,
        "payeezz_start_date": member.payeezz_start_date,
        "remarks": member.remarks,
    }


def _member_to_response_data(
    db: Session,
    member: Member,
    *,
    settings: Settings,
    include_sensitive: bool,
    actor: User,
    request_id: str | None,
) -> tuple[dict[str, Any], list[str]]:
    family = member.family
    data: dict[str, Any] = {
        "id": member.id,
        "family_id": member.family_id,
        "name": member.name,
        "can_number": member.can_number,
        "pan_masked": member.pan_masked,
        "date_of_birth": member.date_of_birth,
        "kyc_status": member.kyc_status,
        "mobile_masked": member.mobile_masked,
        "mobile_status": member.mobile_status,
        "email_masked": member.email_masked,
        "email_status": member.email_status,
        "nominee_status": member.nominee_status,
        "bank_name": member.bank_name,
        "bank_account_number_masked": member.bank_account_number_masked,
        "ifsc_code": member.ifsc_code,
        "payeezz_status": member.payeezz_status,
        "payeezz_amount": member.payeezz_amount,
        "payeezz_start_date": member.payeezz_start_date,
        "remarks": member.remarks,
        "family_code": family.family_code,
        "family_head_name": family.family_head_name,
        "primary_rm": _user_summary(family.primary_rm),
        "updated_at": _as_utc(member.updated_at),
        "updated_by": _user_summary(_latest_update_actor(db, entity_type=AuditEntityType.MEMBER, entity_id=member.id)),
        "created_at": _as_utc(member.created_at),
    }

    returned_sensitive_fields: list[str] = []
    if include_sensitive:
        for field_name in PII_FIELD_ATTRS:
            value = _decrypt_member_field(member, field_name, settings)
            if value is not None:
                data[field_name] = value
                returned_sensitive_fields.append(field_name)
        if returned_sensitive_fields:
            record_sensitive_read(
                db,
                entity_type=AuditEntityType.MEMBER,
                entity_id=member.id,
                field_names=returned_sensitive_fields,
                actor_user_id=actor.id,
                source=ChangeSource.MANUAL,
                request_id=request_id,
            )

    return data, returned_sensitive_fields


def _ensure_sensitive_read_allowed(actor: User, include_sensitive: bool) -> None:
    if include_sensitive and actor.role != UserRole.ADMIN:
        _forbidden("Only admin users can request full sensitive member values.")


def _ensure_family_update_allowed(actor: User, family: Family, payload: FamilyUpdate) -> None:
    if actor.role in {UserRole.ADMIN, UserRole.OPS}:
        return
    if actor.role == UserRole.RM and str(family.primary_rm_id) == str(actor.id):
        disallowed = payload.model_fields_set - {"remarks"}
        if disallowed:
            _forbidden("RM users can only update remarks on assigned families.")
        return
    _forbidden()


def _ensure_member_update_allowed(actor: User, family: Family, payload: MemberUpdate) -> None:
    if actor.role in {UserRole.ADMIN, UserRole.OPS}:
        return
    if actor.role == UserRole.RM and str(family.primary_rm_id) == str(actor.id):
        disallowed = payload.model_fields_set - {"remarks"}
        if disallowed:
            _forbidden("RM users can only update remarks on assigned members.")
        return
    _forbidden()


def _ensure_active_rm(db: Session, rm_id: UUID) -> User:
    rm = db.get(User, rm_id)
    if rm is None or rm.deleted_at is not None or not rm.is_active or rm.role != UserRole.RM:
        _validation_error("primary_rm_id must reference an active RM user.")
    return rm


def _ensure_family_code_available(db: Session, family_code: str, existing_family_id: UUID | None = None) -> None:
    if family_repo.find_active_family_by_code(db, family_code, exclude_family_id=existing_family_id) is not None:
        _conflict("family_code_already_exists", "An active family with this family_code already exists.")


def _ensure_can_available(db: Session, can_number: str, existing_member_id: UUID | None = None) -> None:
    if member_repo.find_active_member_by_can(db, can_number, exclude_member_id=existing_member_id) is not None:
        _conflict("can_number_already_exists", "An active member with this can_number already exists.")


def list_family_records(
    db: Session,
    *,
    filters: FamilyListFilters,
    actor: User,
    settings: Settings,
) -> dict[str, Any]:
    families, total = family_repo.list_families(
        db,
        user=actor,
        settings=settings,
        q=filters.q,
        rm_id=filters.rm_id,
        status_filter=filters.status_filter.value,
        kyc_status=filters.kyc_status,
        payeezz_status=filters.payeezz_status,
        mobile_status=filters.mobile_status,
        email_status=filters.email_status,
        nominee_status=filters.nominee_status,
        limit=filters.limit,
        offset=filters.offset,
        sort=filters.sort,
    )
    return {
        "items": [family_to_response(family) for family in families],
        "total": total,
        "limit": filters.limit,
        "offset": filters.offset,
    }


def get_family_record(db: Session, *, family_id: UUID, actor: User) -> dict[str, Any]:
    family = family_repo.get_active_family(db, family_id, actor)
    if family is None:
        _not_found("family")
    return family_to_response(family)


def create_family_record(
    db: Session,
    *,
    payload: FamilyCreate,
    actor: User,
    request_id: str | None,
) -> dict[str, Any]:
    _ensure_active_rm(db, payload.primary_rm_id)
    _ensure_family_code_available(db, payload.family_code)
    family = Family(
        family_code=payload.family_code,
        family_head_name=payload.family_head_name,
        primary_rm_id=payload.primary_rm_id,
        remarks=payload.remarks,
    )
    db.add(family)
    db.flush()
    record_create(
        db,
        entity_type=AuditEntityType.FAMILY,
        entity_id=family.id,
        actor_user_id=actor.id,
        source=ChangeSource.MANUAL,
        request_id=request_id,
    )
    db.commit()
    db.refresh(family)
    return family_to_response(family)


def update_family_record(
    db: Session,
    *,
    family_id: UUID,
    payload: FamilyUpdate,
    actor: User,
    request_id: str | None,
) -> dict[str, Any]:
    family = family_repo.get_active_family(db, family_id, actor)
    if family is None:
        _not_found("family")
    _ensure_family_update_allowed(actor, family, payload)
    old_values = {
        "family_code": family.family_code,
        "family_head_name": family.family_head_name,
        "primary_rm_id": family.primary_rm_id,
        "remarks": family.remarks,
    }

    if "family_code" in payload.model_fields_set:
        _ensure_family_code_available(db, payload.family_code, existing_family_id=family.id)
        family.family_code = payload.family_code
    if "family_head_name" in payload.model_fields_set:
        family.family_head_name = payload.family_head_name
    if "primary_rm_id" in payload.model_fields_set:
        _ensure_active_rm(db, payload.primary_rm_id)
        family.primary_rm_id = payload.primary_rm_id
    if "remarks" in payload.model_fields_set:
        family.remarks = payload.remarks

    db.flush()
    record_update(
        db,
        entity_type=AuditEntityType.FAMILY,
        entity_id=family.id,
        old_values=old_values,
        new_values={
            "family_code": family.family_code,
            "family_head_name": family.family_head_name,
            "primary_rm_id": family.primary_rm_id,
            "remarks": family.remarks,
        },
        actor_user_id=actor.id,
        source=ChangeSource.MANUAL,
        request_id=request_id,
    )
    db.commit()
    db.refresh(family)
    return family_to_response(family)


def delete_family_record(
    db: Session,
    *,
    family_id: UUID,
    actor: User,
    request_id: str | None,
) -> None:
    family = family_repo.get_active_family(db, family_id, actor)
    if family is None:
        _not_found("family")
    now = _utc_now()
    family.deleted_at = now
    for member in _active_members(family):
        member.deleted_at = now
        record_delete(
            db,
            entity_type=AuditEntityType.MEMBER,
            entity_id=member.id,
            actor_user_id=actor.id,
            source=ChangeSource.MANUAL,
            request_id=request_id,
        )
    record_delete(
        db,
        entity_type=AuditEntityType.FAMILY,
        entity_id=family.id,
        actor_user_id=actor.id,
        source=ChangeSource.MANUAL,
        request_id=request_id,
    )
    db.commit()


def list_member_records(
    db: Session,
    *,
    filters: MemberListFilters,
    actor: User,
    settings: Settings,
    include_sensitive: bool,
    request_id: str | None,
) -> dict[str, Any]:
    _ensure_sensitive_read_allowed(actor, include_sensitive)
    members, total = member_repo.list_members(
        db,
        user=actor,
        settings=settings,
        q=filters.q,
        family_id=filters.family_id,
        rm_id=filters.rm_id,
        kyc_status=filters.kyc_status,
        payeezz_status=filters.payeezz_status,
        mobile_status=filters.mobile_status,
        email_status=filters.email_status,
        nominee_status=filters.nominee_status,
        limit=filters.limit,
        offset=filters.offset,
    )
    sensitive_reads = 0
    items = []
    for member in members:
        data, field_names = _member_to_response_data(
            db,
            member,
            settings=settings,
            include_sensitive=include_sensitive,
            actor=actor,
            request_id=request_id,
        )
        sensitive_reads += len(field_names)
        items.append(data)
    if sensitive_reads:
        db.commit()
    return {
        "items": items,
        "total": total,
        "limit": filters.limit,
        "offset": filters.offset,
    }


def get_member_record(
    db: Session,
    *,
    member_id: UUID,
    actor: User,
    settings: Settings,
    include_sensitive: bool,
    request_id: str | None,
) -> dict[str, Any]:
    _ensure_sensitive_read_allowed(actor, include_sensitive)
    member = member_repo.get_active_member(db, member_id, actor)
    if member is None:
        _not_found("member")
    data, field_names = _member_to_response_data(
        db,
        member,
        settings=settings,
        include_sensitive=include_sensitive,
        actor=actor,
        request_id=request_id,
    )
    if field_names:
        db.commit()
    return data


def member_to_response(
    db: Session,
    member: Member,
    *,
    settings: Settings,
    actor: User,
) -> dict[str, Any]:
    data, _field_names = _member_to_response_data(
        db,
        member,
        settings=settings,
        include_sensitive=False,
        actor=actor,
        request_id=None,
    )
    return data


def _apply_member_payload(member: Member, payload: MemberCreate | MemberUpdate, settings: Settings) -> None:
    fields = payload.model_fields_set
    if "name" in fields:
        member.name = payload.name
    if "can_number" in fields:
        member.can_number = payload.can_number
    if "pan" in fields:
        _set_protected_member_field(member, PAN_FIELD, payload.pan, settings)
    if "date_of_birth" in fields:
        member.date_of_birth = payload.date_of_birth
    if "kyc_status" in fields:
        member.kyc_status = payload.kyc_status
    if "mobile" in fields:
        _set_protected_member_field(member, MOBILE_FIELD, payload.mobile, settings)
    if "mobile_status" in fields:
        member.mobile_status = payload.mobile_status
    if "email" in fields:
        _set_protected_member_field(member, EMAIL_FIELD, payload.email, settings)
    if "email_status" in fields:
        member.email_status = payload.email_status
    if "nominee_status" in fields:
        member.nominee_status = payload.nominee_status
    if "bank_name" in fields:
        member.bank_name = payload.bank_name
    if "bank_account_number" in fields:
        _set_protected_member_field(member, BANK_ACCOUNT_NUMBER_FIELD, payload.bank_account_number, settings)
    if "ifsc_code" in fields:
        member.ifsc_code = payload.ifsc_code
    if "payeezz_status" in fields:
        member.payeezz_status = payload.payeezz_status
    if "payeezz_amount" in fields:
        member.payeezz_amount = payload.payeezz_amount
    if "payeezz_start_date" in fields:
        member.payeezz_start_date = payload.payeezz_start_date
    if "remarks" in fields:
        member.remarks = payload.remarks


def create_member_record(
    db: Session,
    *,
    family_id: UUID,
    payload: MemberCreate,
    actor: User,
    settings: Settings,
    request_id: str | None,
) -> dict[str, Any]:
    family = family_repo.get_active_family(db, family_id, actor)
    if family is None:
        _not_found("family")
    _ensure_can_available(db, payload.can_number)
    member = Member(family_id=family.id)
    db.add(member)
    _apply_member_payload(member, payload, settings)
    db.flush()
    record_create(
        db,
        entity_type=AuditEntityType.MEMBER,
        entity_id=member.id,
        actor_user_id=actor.id,
        source=ChangeSource.MANUAL,
        request_id=request_id,
    )
    db.commit()
    db.refresh(member)
    return get_member_record(
        db,
        member_id=member.id,
        actor=actor,
        settings=settings,
        include_sensitive=False,
        request_id=request_id,
    )


def update_member_record(
    db: Session,
    *,
    member_id: UUID,
    payload: MemberUpdate,
    actor: User,
    settings: Settings,
    request_id: str | None,
) -> dict[str, Any]:
    member = member_repo.get_active_member(db, member_id, actor)
    if member is None:
        _not_found("member")
    _ensure_member_update_allowed(actor, member.family, payload)
    old_values = _member_audit_values(member, settings)
    if "can_number" in payload.model_fields_set:
        _ensure_can_available(db, payload.can_number, existing_member_id=member.id)
    _apply_member_payload(member, payload, settings)
    db.flush()
    record_update(
        db,
        entity_type=AuditEntityType.MEMBER,
        entity_id=member.id,
        old_values=old_values,
        new_values=_member_audit_values(member, settings),
        actor_user_id=actor.id,
        source=ChangeSource.MANUAL,
        request_id=request_id,
    )
    db.commit()
    db.refresh(member)
    return get_member_record(
        db,
        member_id=member.id,
        actor=actor,
        settings=settings,
        include_sensitive=False,
        request_id=request_id,
    )


def delete_member_record(
    db: Session,
    *,
    member_id: UUID,
    actor: User,
    request_id: str | None,
) -> None:
    member = member_repo.get_active_member(db, member_id, actor)
    if member is None:
        _not_found("member")
    member.deleted_at = _utc_now()
    record_delete(
        db,
        entity_type=AuditEntityType.MEMBER,
        entity_id=member.id,
        actor_user_id=actor.id,
        source=ChangeSource.MANUAL,
        request_id=request_id,
    )
    db.commit()


__all__ = [
    "create_family_record",
    "create_member_record",
    "delete_family_record",
    "delete_member_record",
    "family_to_response",
    "get_family_record",
    "get_member_record",
    "list_family_records",
    "list_member_records",
    "member_to_response",
    "update_family_record",
    "update_member_record",
]
