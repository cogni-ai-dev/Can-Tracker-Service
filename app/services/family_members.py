from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import desc, select, update
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
from app.api.v1.users import CAN_SENSITIVE_FIELDS, can_sensitive_access_for_user
from app.domain.access import user_can_write_all_can, user_has_module_role, user_is_can_rm
from app.domain.compliance import CountPercentage, family_completion
from app.domain.enums import AuditAction, AuditEntityType, ChangeSource, ModuleCode, ModuleRole, PayeezzStatus
from app.models.audit import AuditLog
from app.models.family import Family, Member, MemberBankAccount
from app.models.user import User
from app.repositories import families as family_repo
from app.repositories import members as member_repo
from app.schemas.families import FamilyCreate, FamilyListFilters, FamilyUpdate
from app.schemas.members import MemberBankAccountCreate, MemberBankAccountUpdate, MemberCreate, MemberListFilters, MemberUpdate
from app.services.audit import record_create, record_delete, record_sensitive_read, record_update

PII_FIELD_ATTRS = {
    PAN_FIELD: ("pan_encrypted", "pan_masked", "pan_search_hash"),
    MOBILE_FIELD: ("mobile_encrypted", "mobile_masked", "mobile_search_hash"),
    EMAIL_FIELD: ("email_encrypted", "email_masked", "email_search_hash"),
}
BANK_ACCOUNT_FIELD_ATTRS = {
    BANK_ACCOUNT_NUMBER_FIELD: (
        "account_number_encrypted",
        "account_number_masked",
        "account_number_search_hash",
    ),
}
GENERATED_FAMILY_CODE_PREFIX = "FAM"
GENERATED_FAMILY_CODE_RE = re.compile(r"^FAM-\d{8}-(\d{4})$")


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
        "can_completion": _count_percentage(completion.can_completion),
        "can_pending": _count_percentage(completion.can_pending),
        "kyc_completion": _count_percentage(completion.kyc_completion),
        "payeezz_completion": _count_percentage(completion.payeezz_completion),
        "mobile_verification": _count_percentage(completion.mobile_verification),
        "email_verification": _count_percentage(completion.email_verification),
        "nominee_verification": _count_percentage(completion.nominee_verification),
        "can_completion_pct": completion.can_completion_pct,
        "can_pending_pct": completion.can_pending_pct,
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


def _decrypt_bank_account_field(bank_account: MemberBankAccount, field_name: str, settings: Settings) -> str | None:
    encrypted_attr = BANK_ACCOUNT_FIELD_ATTRS[field_name][0]
    return decrypt_pii_value(field_name, getattr(bank_account, encrypted_attr), settings)


def _set_protected_member_field(member: Member, field_name: str, value: object | None, settings: Settings) -> None:
    encrypted_attr, masked_attr, search_hash_attr = PII_FIELD_ATTRS[field_name]
    protected = protect_pii_value(field_name, value, settings)
    setattr(member, encrypted_attr, protected.ciphertext)
    setattr(member, masked_attr, protected.masked)
    setattr(member, search_hash_attr, protected.search_hash)


def _set_protected_bank_account_field(
    bank_account: MemberBankAccount,
    field_name: str,
    value: object | None,
    settings: Settings,
) -> None:
    encrypted_attr, masked_attr, search_hash_attr = BANK_ACCOUNT_FIELD_ATTRS[field_name]
    protected = protect_pii_value(field_name, value, settings)
    if protected.ciphertext is None or protected.masked is None or protected.search_hash is None:
        _validation_error("Bank account number is required.")
    setattr(bank_account, encrypted_attr, protected.ciphertext)
    setattr(bank_account, masked_attr, protected.masked)
    setattr(bank_account, search_hash_attr, protected.search_hash)


def active_bank_accounts(member: Member) -> list[MemberBankAccount]:
    return sorted(
        (account for account in member.bank_accounts if account.deleted_at is None),
        key=lambda account: (not account.is_primary, account.bank_name, str(account.id)),
    )


def primary_bank_account(member: Member) -> MemberBankAccount | None:
    return next((account for account in active_bank_accounts(member) if account.is_primary), None)


def effective_payeezz_status(member: Member) -> str:
    primary = primary_bank_account(member)
    if primary is None:
        return PayeezzStatus.NOT_STARTED.value
    return primary.payeezz_mandate_status


def _member_audit_values(member: Member, settings: Settings) -> dict[str, object | None]:
    return {
        "name": member.name,
        "can_number": member.can_number,
        "can_status": member.can_status,
        "pan": _decrypt_member_field(member, PAN_FIELD, settings),
        "date_of_birth": member.date_of_birth,
        "kyc_status": member.kyc_status,
        "mobile": _decrypt_member_field(member, MOBILE_FIELD, settings),
        "mobile_verification_status": member.mobile_verification_status,
        "email": _decrypt_member_field(member, EMAIL_FIELD, settings),
        "email_verification_status": member.email_verification_status,
        "nominee_name": member.nominee_name,
        "nominee_verification_status": member.nominee_verification_status,
        "remarks": member.remarks,
    }


def _bank_account_audit_values(bank_account: MemberBankAccount, settings: Settings) -> dict[str, object | None]:
    return {
        "bank_name": bank_account.bank_name,
        "bank_account_number": _decrypt_bank_account_field(bank_account, BANK_ACCOUNT_NUMBER_FIELD, settings),
        "ifsc_code": bank_account.ifsc_code,
        "is_primary": bank_account.is_primary,
        "payeezz_mandate_status": bank_account.payeezz_mandate_status,
        "payeezz_amount": bank_account.payeezz_amount,
        "payeezz_start_date": bank_account.payeezz_start_date,
    }


def bank_account_to_response(
    db: Session,
    bank_account: MemberBankAccount,
    *,
    settings: Settings,
    include_sensitive: bool,
    allowed_sensitive_fields: set[str],
    actor: User,
    request_id: str | None,
) -> tuple[dict[str, Any], list[str]]:
    data = {
        "id": bank_account.id,
        "bank_name": bank_account.bank_name,
        "account_number_masked": bank_account.account_number_masked,
        "ifsc_code": bank_account.ifsc_code,
        "is_primary": bank_account.is_primary,
        "payeezz_mandate_status": bank_account.payeezz_mandate_status,
        "payeezz_amount": bank_account.payeezz_amount,
        "payeezz_start_date": bank_account.payeezz_start_date,
        "created_at": _as_utc(bank_account.created_at),
        "updated_at": _as_utc(bank_account.updated_at),
    }
    returned_sensitive_fields: list[str] = []
    if include_sensitive and BANK_ACCOUNT_NUMBER_FIELD in allowed_sensitive_fields:
        value = _decrypt_bank_account_field(bank_account, BANK_ACCOUNT_NUMBER_FIELD, settings)
        if value is not None:
            data["account_number"] = value
            returned_sensitive_fields.append(BANK_ACCOUNT_NUMBER_FIELD)
    return data, returned_sensitive_fields


def _member_to_response_data(
    db: Session,
    member: Member,
    *,
    settings: Settings,
    include_sensitive: bool,
    allowed_sensitive_fields: set[str] | None = None,
    actor: User,
    request_id: str | None,
) -> tuple[dict[str, Any], list[str]]:
    family = member.family
    data: dict[str, Any] = {
        "id": member.id,
        "family_id": member.family_id,
        "name": member.name,
        "can_number": member.can_number,
        "can_status": member.can_status,
        "pan_masked": member.pan_masked,
        "date_of_birth": member.date_of_birth,
        "kyc_status": member.kyc_status,
        "mobile_masked": member.mobile_masked,
        "mobile_verification_status": member.mobile_verification_status,
        "email_masked": member.email_masked,
        "email_verification_status": member.email_verification_status,
        "nominee_name": member.nominee_name,
        "nominee_verification_status": member.nominee_verification_status,
        "effective_payeezz_mandate_status": effective_payeezz_status(member),
        "remarks": member.remarks,
        "family_code": family.family_code,
        "family_head_name": family.family_head_name,
        "primary_rm": _user_summary(family.primary_rm),
        "updated_at": _as_utc(member.updated_at),
        "updated_by": _user_summary(_latest_update_actor(db, entity_type=AuditEntityType.MEMBER, entity_id=member.id)),
        "created_at": _as_utc(member.created_at),
    }

    returned_sensitive_fields: list[str] = []
    allowed_sensitive_fields = allowed_sensitive_fields or set()
    bank_account_items = []
    primary_bank_item = None
    for bank_account in active_bank_accounts(member):
        item, bank_sensitive_fields = bank_account_to_response(
            db,
            bank_account,
            settings=settings,
            include_sensitive=include_sensitive,
            allowed_sensitive_fields=allowed_sensitive_fields,
            actor=actor,
            request_id=request_id,
        )
        returned_sensitive_fields.extend(bank_sensitive_fields)
        bank_account_items.append(item)
        if bank_account.is_primary:
            primary_bank_item = item
    data["bank_accounts"] = bank_account_items
    data["primary_bank_account"] = primary_bank_item

    if include_sensitive:
        for field_name in PII_FIELD_ATTRS:
            if field_name not in allowed_sensitive_fields:
                continue
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


def _allowed_sensitive_fields(actor: User, db: Session, include_sensitive: bool) -> set[str]:
    if not include_sensitive:
        return set()
    access = can_sensitive_access_for_user(actor, db)
    allowed = {field_name for field_name in CAN_SENSITIVE_FIELDS if access.get(field_name)}
    if not allowed:
        _forbidden("Your role is not permitted to reveal sensitive member values.")
    return allowed


def _ensure_family_update_allowed(actor: User, family: Family, payload: FamilyUpdate) -> None:
    if user_can_write_all_can(actor):
        return
    if user_is_can_rm(actor) and str(family.primary_rm_id) == str(actor.id):
        disallowed = payload.model_fields_set - {"remarks"}
        if disallowed:
            _forbidden("RM users can only update remarks on assigned families.")
        return
    _forbidden()


def _ensure_member_update_allowed(actor: User, family: Family, payload: MemberUpdate) -> None:
    if user_can_write_all_can(actor):
        return
    if user_is_can_rm(actor) and str(family.primary_rm_id) == str(actor.id):
        disallowed = payload.model_fields_set - {"remarks"}
        if disallowed:
            _forbidden("RM users can only update remarks on assigned members.")
        return
    _forbidden()


def _ensure_active_rm(db: Session, rm_id: UUID | None) -> User | None:
    if rm_id is None:
        return None
    rm = db.get(User, rm_id)
    if (
        rm is None
        or rm.deleted_at is not None
        or not rm.is_active
        or not user_has_module_role(
            rm,
            ModuleCode.CAN_COMPLIANCE,
            ModuleRole.CAN_RM,
            platform_admin_bypass=False,
        )
    ):
        _validation_error("primary_rm_id must reference an active RM user.")
    return rm


def _ensure_family_code_available(db: Session, family_code: str, existing_family_id: UUID | None = None) -> None:
    if family_repo.find_active_family_by_code(db, family_code, exclude_family_id=existing_family_id) is not None:
        _conflict("family_code_already_exists", "An active family with this family_code already exists.")


def generate_family_code(db: Session, *, now: datetime | None = None) -> str:
    creation_time = now or _utc_now()
    date_stamp = creation_time.strftime("%Y%m%d")
    prefix = f"{GENERATED_FAMILY_CODE_PREFIX}-{date_stamp}-"
    highest_sequence = 0
    for code in family_repo.list_family_codes_with_prefix(db, prefix):
        match = GENERATED_FAMILY_CODE_RE.match(code)
        if match:
            highest_sequence = max(highest_sequence, int(match.group(1)))
    return f"{prefix}{highest_sequence + 1:04d}"


def _ensure_can_available(db: Session, can_number: str | None, existing_member_id: UUID | None = None) -> None:
    if can_number is None:
        return
    if member_repo.find_active_member_by_can(db, can_number, exclude_member_id=existing_member_id) is not None:
        _conflict("can_number_already_exists", "An active member with this can_number already exists.")


def _ensure_member_can_state(member: Member) -> None:
    if member.can_number is None and member.can_status != "Pending":
        _validation_error("can_status must be Pending when can_number is blank.")
    if member.can_number is not None and member.can_status != "Available":
        _validation_error("can_status must be Available when can_number is present.")


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
        can_status=filters.can_status,
        kyc_status=filters.kyc_status,
        payeezz_mandate_status=filters.payeezz_mandate_status,
        mobile_verification_status=filters.mobile_verification_status,
        email_verification_status=filters.email_verification_status,
        nominee_verification_status=filters.nominee_verification_status,
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
    family_code = payload.family_code or generate_family_code(db)
    _ensure_family_code_available(db, family_code)
    family = Family(
        family_code=family_code,
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
    allowed_sensitive_fields = _allowed_sensitive_fields(actor, db, include_sensitive)
    members, total = member_repo.list_members(
        db,
        user=actor,
        settings=settings,
        q=filters.q,
        family_id=filters.family_id,
        rm_id=filters.rm_id,
        can_status=filters.can_status,
        kyc_status=filters.kyc_status,
        payeezz_mandate_status=filters.payeezz_mandate_status,
        mobile_verification_status=filters.mobile_verification_status,
        email_verification_status=filters.email_verification_status,
        nominee_verification_status=filters.nominee_verification_status,
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
            allowed_sensitive_fields=allowed_sensitive_fields,
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
    allowed_sensitive_fields = _allowed_sensitive_fields(actor, db, include_sensitive)
    member = member_repo.get_active_member(db, member_id, actor)
    if member is None:
        _not_found("member")
    data, field_names = _member_to_response_data(
        db,
        member,
        settings=settings,
        include_sensitive=include_sensitive,
        allowed_sensitive_fields=allowed_sensitive_fields,
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
        allowed_sensitive_fields=set(),
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
    if "can_status" in fields or isinstance(payload, MemberCreate):
        member.can_status = payload.can_status
    if "pan" in fields:
        _set_protected_member_field(member, PAN_FIELD, payload.pan, settings)
    if "date_of_birth" in fields:
        member.date_of_birth = payload.date_of_birth
    if "kyc_status" in fields:
        member.kyc_status = payload.kyc_status
    if "mobile" in fields:
        _set_protected_member_field(member, MOBILE_FIELD, payload.mobile, settings)
    if "mobile_verification_status" in fields:
        member.mobile_verification_status = payload.mobile_verification_status
    if "email" in fields:
        _set_protected_member_field(member, EMAIL_FIELD, payload.email, settings)
    if "email_verification_status" in fields:
        member.email_verification_status = payload.email_verification_status
    if "nominee_name" in fields:
        member.nominee_name = payload.nominee_name
    if "nominee_verification_status" in fields:
        member.nominee_verification_status = payload.nominee_verification_status
    if "remarks" in fields:
        member.remarks = payload.remarks


def _ensure_bank_account_write_allowed(actor: User, member: Member) -> None:
    if user_can_write_all_can(actor):
        return
    _forbidden("Only CAN Admin and CAN Ops can manage bank accounts.")


def _active_bank_accounts_query(db: Session, member_id: UUID) -> list[MemberBankAccount]:
    return list(
        db.scalars(
            select(MemberBankAccount).where(
                MemberBankAccount.member_id == member_id,
                MemberBankAccount.deleted_at.is_(None),
            )
        ).all()
    )


def _ensure_bank_account_available(
    db: Session,
    *,
    member_id: UUID,
    bank_name: str,
    account_number_search_hash: str,
    existing_bank_account_id: UUID | None = None,
) -> None:
    filters = [
        MemberBankAccount.member_id == member_id,
        MemberBankAccount.bank_name == bank_name,
        MemberBankAccount.account_number_search_hash == account_number_search_hash,
        MemberBankAccount.deleted_at.is_(None),
    ]
    if existing_bank_account_id is not None:
        filters.append(MemberBankAccount.id != existing_bank_account_id)
    if db.scalar(select(MemberBankAccount.id).where(*filters).limit(1)) is not None:
        _conflict("bank_account_already_exists", "An active bank account with this bank name and account number already exists for the member.")


def _apply_bank_account_payload(
    bank_account: MemberBankAccount,
    payload: MemberBankAccountCreate | MemberBankAccountUpdate,
    settings: Settings,
) -> None:
    fields = payload.model_fields_set
    if "bank_name" in fields:
        bank_account.bank_name = payload.bank_name
    if "account_number" in fields:
        _set_protected_bank_account_field(bank_account, BANK_ACCOUNT_NUMBER_FIELD, payload.account_number, settings)
    if "ifsc_code" in fields:
        bank_account.ifsc_code = payload.ifsc_code
    if "is_primary" in fields:
        bank_account.is_primary = bool(payload.is_primary)
    if "payeezz_mandate_status" in fields:
        bank_account.payeezz_mandate_status = payload.payeezz_mandate_status
    if "payeezz_amount" in fields:
        bank_account.payeezz_amount = payload.payeezz_amount
    if "payeezz_start_date" in fields:
        bank_account.payeezz_start_date = payload.payeezz_start_date


def _promote_primary(db: Session, member_id: UUID, bank_account: MemberBankAccount) -> None:
    bank_account.is_primary = False
    db.execute(
        update(MemberBankAccount)
        .where(
            MemberBankAccount.member_id == member_id,
            MemberBankAccount.id != bank_account.id,
            MemberBankAccount.deleted_at.is_(None),
        )
        .values(is_primary=False)
    )
    db.flush()
    bank_account.is_primary = True


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
    _ensure_member_can_state(member)
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
    _ensure_member_can_state(member)
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


def create_member_bank_account(
    db: Session,
    *,
    member_id: UUID,
    payload: MemberBankAccountCreate,
    actor: User,
    settings: Settings,
    request_id: str | None,
) -> dict[str, Any]:
    member = member_repo.get_active_member(db, member_id, actor)
    if member is None:
        _not_found("member")
    _ensure_bank_account_write_allowed(actor, member)
    active_accounts = _active_bank_accounts_query(db, member.id)
    bank_account = MemberBankAccount(
        member_id=member.id,
        payeezz_mandate_status=PayeezzStatus.NOT_STARTED,
        is_primary=payload.is_primary or not active_accounts,
    )
    db.add(bank_account)
    _apply_bank_account_payload(bank_account, payload, settings)
    if not active_accounts:
        bank_account.is_primary = True
    _ensure_bank_account_available(
        db,
        member_id=member.id,
        bank_name=bank_account.bank_name,
        account_number_search_hash=bank_account.account_number_search_hash,
    )
    if bank_account.is_primary:
        _promote_primary(db, member.id, bank_account)
    db.flush()
    record_update(
        db,
        entity_type=AuditEntityType.MEMBER,
        entity_id=member.id,
        old_values={},
        new_values={f"bank_account:{bank_account.id}": "created", **_bank_account_audit_values(bank_account, settings)},
        actor_user_id=actor.id,
        source=ChangeSource.MANUAL,
        request_id=request_id,
    )
    db.commit()
    db.refresh(bank_account)
    data, _fields = bank_account_to_response(
        db,
        bank_account,
        settings=settings,
        include_sensitive=False,
        allowed_sensitive_fields=set(),
        actor=actor,
        request_id=request_id,
    )
    return data


def update_member_bank_account(
    db: Session,
    *,
    member_id: UUID,
    bank_account_id: UUID,
    payload: MemberBankAccountUpdate,
    actor: User,
    settings: Settings,
    request_id: str | None,
) -> dict[str, Any]:
    member = member_repo.get_active_member(db, member_id, actor)
    if member is None:
        _not_found("member")
    _ensure_bank_account_write_allowed(actor, member)
    bank_account = db.scalar(
        select(MemberBankAccount).where(
            MemberBankAccount.id == bank_account_id,
            MemberBankAccount.member_id == member.id,
            MemberBankAccount.deleted_at.is_(None),
        )
    )
    if bank_account is None:
        _not_found("bank_account")
    old_values = _bank_account_audit_values(bank_account, settings)
    _apply_bank_account_payload(bank_account, payload, settings)
    _ensure_bank_account_available(
        db,
        member_id=member.id,
        bank_name=bank_account.bank_name,
        account_number_search_hash=bank_account.account_number_search_hash,
        existing_bank_account_id=bank_account.id,
    )
    active_accounts = _active_bank_accounts_query(db, member.id)
    if bank_account.is_primary:
        _promote_primary(db, member.id, bank_account)
    elif old_values.get("is_primary") is True and len(active_accounts) > 1:
        _validation_error("A member with multiple bank accounts must have exactly one primary account.")
    db.flush()
    record_update(
        db,
        entity_type=AuditEntityType.MEMBER,
        entity_id=member.id,
        old_values=old_values,
        new_values=_bank_account_audit_values(bank_account, settings),
        actor_user_id=actor.id,
        source=ChangeSource.MANUAL,
        request_id=request_id,
    )
    db.commit()
    db.refresh(bank_account)
    data, _fields = bank_account_to_response(
        db,
        bank_account,
        settings=settings,
        include_sensitive=False,
        allowed_sensitive_fields=set(),
        actor=actor,
        request_id=request_id,
    )
    return data


def delete_member_bank_account(
    db: Session,
    *,
    member_id: UUID,
    bank_account_id: UUID,
    actor: User,
    request_id: str | None,
) -> None:
    member = member_repo.get_active_member(db, member_id, actor)
    if member is None:
        _not_found("member")
    _ensure_bank_account_write_allowed(actor, member)
    bank_account = db.scalar(
        select(MemberBankAccount).where(
            MemberBankAccount.id == bank_account_id,
            MemberBankAccount.member_id == member.id,
            MemberBankAccount.deleted_at.is_(None),
        )
    )
    if bank_account is None:
        _not_found("bank_account")
    active_accounts = _active_bank_accounts_query(db, member.id)
    if bank_account.is_primary and len(active_accounts) > 1:
        _validation_error("Set another bank account as primary before deleting this primary account.")
    bank_account.deleted_at = _utc_now()
    record_update(
        db,
        entity_type=AuditEntityType.MEMBER,
        entity_id=member.id,
        old_values={f"bank_account:{bank_account.id}": "active"},
        new_values={f"bank_account:{bank_account.id}": "deleted"},
        actor_user_id=actor.id,
        source=ChangeSource.MANUAL,
        request_id=request_id,
    )
    db.commit()


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
    "create_member_bank_account",
    "create_member_record",
    "delete_member_bank_account",
    "delete_family_record",
    "delete_member_record",
    "family_to_response",
    "get_family_record",
    "get_member_record",
    "list_family_records",
    "list_member_records",
    "member_to_response",
    "update_member_bank_account",
    "update_family_record",
    "update_member_record",
]
