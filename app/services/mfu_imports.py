from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from fastapi import status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import raise_api_error
from app.core.config import Settings
from app.core.pii import (
    BANK_ACCOUNT_NUMBER_FIELD,
    EMAIL_FIELD,
    MOBILE_FIELD,
    PAN_FIELD,
    decrypt_pii_value,
    mask_pii_value,
    protect_pii_value,
)
from app.domain.access import user_has_module_role
from app.domain.enums import (
    AuditEntityType,
    CanStatus,
    ChangeSource,
    ImportBatchStatus,
    ImportRowStatus,
    KycStatus,
    ModuleCode,
    ModuleRole,
    PayeezzStatus,
    VerificationStatus,
)
from app.models.family import Family, Member
from app.models.imports import ImportBatch, ImportRow
from app.models.user import User
from app.repositories import families as family_repo
from app.repositories import members as member_repo
from app.schemas.members import (
    normalize_bank_account_number,
    normalize_can_number,
    normalize_email,
    normalize_ifsc,
    normalize_mobile,
    normalize_optional_can_number,
    normalize_pan,
    validate_date_not_future,
)
from app.services.audit import record_create, record_import_commit, record_update
from app.services.family_members import _member_audit_values, generate_family_code
from app.services.mfu_gateway import (
    REQUIRED_TEMPLATE_COLUMNS,
    TEMPLATE_COLUMNS,
    MfuMemberRecord,
    TemplateMfuGateway,
    TemplateParseError,
)

HEADER_TO_FIELD = {
    "FamilyCode": "family_code",
    "FamilyHeadName": "family_head_name",
    "PrimaryRMEmail": "primary_rm_email",
    "PrimaryRMName": "primary_rm_name",
    "FamilyRemarks": "family_remarks",
    "MemberName": "member_name",
    "CANNumber": "can_number",
    "PAN": "pan",
    "DateOfBirth": "date_of_birth",
    "KYCStatus": "kyc_status",
    "Mobile": "mobile",
    "MobileStatus": "mobile_verification_status",
    "Email": "email",
    "EmailStatus": "email_verification_status",
    "NomineeStatus": "nominee_verification_status",
    "BankName": "bank_name",
    "AccountNumber": "bank_account_number",
    "IFSC": "ifsc_code",
    "PayEezzStatus": "payeezz_mandate_status",
    "PayEezzAmount": "payeezz_amount",
    "PayEezzStartDate": "payeezz_start_date",
    "Remarks": "remarks",
}

FIELD_TO_HEADER = {field: header for header, field in HEADER_TO_FIELD.items()}
SENSITIVE_HEADER_FIELDS = {
    "PAN": PAN_FIELD,
    "Mobile": MOBILE_FIELD,
    "Email": EMAIL_FIELD,
    "AccountNumber": BANK_ACCOUNT_NUMBER_FIELD,
}
SENSITIVE_NORMALIZED_FIELDS = {
    "pan": PAN_FIELD,
    "mobile": MOBILE_FIELD,
    "email": EMAIL_FIELD,
    "bank_account_number": BANK_ACCOUNT_NUMBER_FIELD,
}
REQUIRED_ROW_FIELD_HEADERS = (
    "FamilyHeadName",
    "MemberName",
    "KYCStatus",
    "MobileStatus",
    "EmailStatus",
    "NomineeStatus",
    "PayEezzStatus",
)

MEMBER_MFU_FIELDS = (
    "member_name",
    "can_status",
    "pan",
    "date_of_birth",
    "kyc_status",
    "mobile",
    "mobile_verification_status",
    "email",
    "email_verification_status",
    "nominee_verification_status",
    "bank_name",
    "bank_account_number",
    "ifsc_code",
    "payeezz_mandate_status",
    "payeezz_amount",
    "payeezz_start_date",
)


@dataclass
class VerifiedTemplateRow:
    row_number: int
    raw_data: dict[str, str]
    normalized_data: dict[str, Any]
    status: ImportRowStatus
    errors: list[str]
    family_id: UUID | None = None
    member_id: UUID | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _not_found(entity: str) -> None:
    raise_api_error(
        status.HTTP_404_NOT_FOUND,
        f"{entity}_not_found",
        f"{entity.replace('_', ' ').title()} was not found.",
    )


def _conflict(code: str, message: str) -> None:
    raise_api_error(status.HTTP_409_CONFLICT, code, message)


def _bad_request(code: str, message: str) -> None:
    raise_api_error(status.HTTP_400_BAD_REQUEST, code, message)


def _cell(record: MfuMemberRecord, header: str) -> str:
    return str(record.raw_data.get(header, "") or "").strip()


def _optional_text(record: MfuMemberRecord, header: str) -> str | None:
    value = _cell(record, header)
    if value.upper() == "NA":
        return None
    return value or None


def _required_text(record: MfuMemberRecord, header: str, errors: list[str]) -> str | None:
    value = _cell(record, header)
    if not value:
        errors.append(f"{header}: value is required.")
        return None
    return value


def _enum_value(
    enum_cls: type[KycStatus] | type[VerificationStatus] | type[PayeezzStatus],
    value: str | None,
    header: str,
    errors: list[str],
) -> str | None:
    if value is None:
        return None
    if value not in enum_cls.values():
        allowed = ", ".join(enum_cls.values())
        errors.append(f"{header}: must be one of {allowed}.")
        return None
    return value


def _normalized_status_value(
    enum_cls: type[KycStatus] | type[VerificationStatus] | type[PayeezzStatus],
    value: str | None,
    header: str,
    errors: list[str],
    *,
    default: str,
    aliases: dict[str, str],
) -> str:
    if value is None or value.strip().upper() in {"", "NA"}:
        return default
    candidate = aliases.get(value.strip(), value.strip())
    if candidate in enum_cls.values():
        return candidate
    allowed = ", ".join(enum_cls.values())
    errors.append(f"{header}: must be one of {allowed}.")
    return default


def _parse_iso_date(value: str | None, header: str, errors: list[str], *, not_future: bool = False) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        errors.append(f"{header}: date must use YYYY-MM-DD.")
        return None
    if not_future:
        try:
            validate_date_not_future(parsed, header)
        except ValueError as exc:
            errors.append(f"{header}: {exc}")
            return None
    return parsed.isoformat()


def _parse_amount(value: str | None, errors: list[str]) -> str | None:
    if value is None:
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation:
        errors.append("PayEezzAmount: amount must be numeric.")
        return None
    if amount < 0:
        errors.append("PayEezzAmount: amount must be non-negative.")
        return None
    return format(amount, "f")


def _normalize_optional(
    record: MfuMemberRecord,
    header: str,
    normalizer,
    errors: list[str],
) -> str | None:
    value = _optional_text(record, header)
    try:
        return normalizer(value)
    except (ValueError, ValidationError) as exc:
        errors.append(f"{header}: {exc}")
        return None


def _find_active_rm(db: Session, *, email: str | None, name: str | None, errors: list[str]) -> User | None:
    if email:
        rm = db.scalar(
            select(User).where(
                User.email == email.lower(),
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        if rm is not None and not user_has_module_role(
            rm,
            ModuleCode.CAN_COMPLIANCE,
            ModuleRole.CAN_RM,
            platform_admin_bypass=False,
        ):
            rm = None
        if rm is None:
            errors.append("PrimaryRMEmail: must match an active RM user.")
        return rm

    if name:
        matches = list(
            db.scalars(
                select(User).where(
                    User.name == name,
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                )
            )
        )
        matches = [
            user
            for user in matches
            if user_has_module_role(
                user,
                ModuleCode.CAN_COMPLIANCE,
                ModuleRole.CAN_RM,
                platform_admin_bypass=False,
            )
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            errors.append("PrimaryRMName: must match an active RM user.")
        else:
            errors.append("PrimaryRMName: must match exactly one active RM user.")
        return None

    return None


def _validate_record(db: Session, record: MfuMemberRecord) -> VerifiedTemplateRow:
    errors: list[str] = []
    family_code = _optional_text(record, "FamilyCode")
    family_head_name = _required_text(record, "FamilyHeadName", errors)
    member_name = _required_text(record, "MemberName", errors)
    raw_can_number = _optional_text(record, "CANNumber")
    try:
        can_number = normalize_optional_can_number(raw_can_number)
    except ValueError as exc:
        errors.append(f"CANNumber: {exc}")
        can_number = None
    can_status = CanStatus.AVAILABLE.value if can_number is not None else CanStatus.PENDING.value

    kyc_status = _normalized_status_value(
        KycStatus,
        _optional_text(record, "KYCStatus"),
        "KYCStatus",
        errors,
        default=KycStatus.NOT_STARTED.value,
        aliases={
            "Validated": KycStatus.VERIFIED.value,
            "Registered": KycStatus.PENDING_REKYC.value,
            "No KYC": KycStatus.NOT_STARTED.value,
            "Choose 1": KycStatus.NOT_STARTED.value,
        },
    )
    mobile_verification_status = _normalized_status_value(
        VerificationStatus,
        _optional_text(record, "MobileStatus"),
        "MobileStatus",
        errors,
        default=VerificationStatus.PENDING_VERIFICATION.value,
        aliases={
            "Not Verified": VerificationStatus.PENDING_VERIFICATION.value,
            "Choose": VerificationStatus.PENDING_VERIFICATION.value,
        },
    )
    email_verification_status = _normalized_status_value(
        VerificationStatus,
        _optional_text(record, "EmailStatus"),
        "EmailStatus",
        errors,
        default=VerificationStatus.PENDING_VERIFICATION.value,
        aliases={"Not Verified": VerificationStatus.PENDING_VERIFICATION.value},
    )
    nominee_verification_status = _normalized_status_value(
        VerificationStatus,
        _optional_text(record, "NomineeStatus"),
        "NomineeStatus",
        errors,
        default=VerificationStatus.PENDING_VERIFICATION.value,
        aliases={
            "Not Verified": VerificationStatus.PENDING_VERIFICATION.value,
            "Choose": VerificationStatus.PENDING_VERIFICATION.value,
        },
    )
    payeezz_mandate_status = _normalized_status_value(
        PayeezzStatus,
        _optional_text(record, "PayEezzStatus"),
        "PayEezzStatus",
        errors,
        default=PayeezzStatus.NOT_STARTED.value,
        aliases={
            "Not Available": PayeezzStatus.NOT_STARTED.value,
            "Sent for Approval": PayeezzStatus.PENDING_APPROVAL.value,
            "Aggregator Accepted": PayeezzStatus.APPROVED.value,
        },
    )

    primary_rm_email = _optional_text(record, "PrimaryRMEmail")
    if primary_rm_email is not None:
        primary_rm_email = primary_rm_email.lower()
    primary_rm_name = _optional_text(record, "PrimaryRMName")
    rm = _find_active_rm(db, email=primary_rm_email, name=primary_rm_name, errors=errors)

    normalized_data = {
        "family_code": family_code,
        "family_head_name": family_head_name,
        "primary_rm_id": str(rm.id) if rm is not None else None,
        "primary_rm_email": primary_rm_email,
        "primary_rm_name": primary_rm_name,
        "family_remarks": _optional_text(record, "FamilyRemarks"),
        "member_name": member_name,
        "can_number": can_number,
        "can_status": can_status,
        "pan": _normalize_optional(record, "PAN", normalize_pan, errors),
        "date_of_birth": _parse_iso_date(_optional_text(record, "DateOfBirth"), "DateOfBirth", errors, not_future=True),
        "kyc_status": kyc_status,
        "mobile": _normalize_optional(record, "Mobile", normalize_mobile, errors),
        "mobile_verification_status": mobile_verification_status,
        "email": _normalize_optional(record, "Email", normalize_email, errors),
        "email_verification_status": email_verification_status,
        "nominee_verification_status": nominee_verification_status,
        "bank_name": _optional_text(record, "BankName"),
        "bank_account_number": _normalize_optional(record, "AccountNumber", normalize_bank_account_number, errors),
        "ifsc_code": _normalize_optional(record, "IFSC", normalize_ifsc, errors),
        "payeezz_mandate_status": payeezz_mandate_status,
        "payeezz_amount": _parse_amount(_optional_text(record, "PayEezzAmount"), errors),
        "payeezz_start_date": _parse_iso_date(_optional_text(record, "PayEezzStartDate"), "PayEezzStartDate", errors),
        "remarks": _optional_text(record, "Remarks"),
    }
    return VerifiedTemplateRow(
        row_number=record.row_number,
        raw_data={header: record.raw_data.get(header, "") for header in TEMPLATE_COLUMNS},
        normalized_data=normalized_data,
        status=ImportRowStatus.ERROR if errors else ImportRowStatus.VALID,
        errors=errors,
    )


def _apply_duplicate_can_errors(rows: list[VerifiedTemplateRow]) -> None:
    can_counts: dict[str, int] = {}
    for row in rows:
        can_number = row.normalized_data.get("can_number")
        if isinstance(can_number, str):
            can_counts[can_number] = can_counts.get(can_number, 0) + 1
    duplicates = {can for can, count in can_counts.items() if count > 1}
    for row in rows:
        if row.normalized_data.get("can_number") in duplicates:
            row.errors.append("CANNumber: duplicate CAN number in import file.")
            row.status = ImportRowStatus.ERROR


def _apply_existing_record_status(db: Session, rows: list[VerifiedTemplateRow]) -> None:
    for row in rows:
        if row.status == ImportRowStatus.ERROR:
            continue
        family_code = row.normalized_data.get("family_code")
        family_head_name = row.normalized_data["family_head_name"]
        raw_primary_rm_id = row.normalized_data.get("primary_rm_id")
        primary_rm_id = UUID(raw_primary_rm_id) if raw_primary_rm_id is not None else None
        can_number = row.normalized_data["can_number"]
        family = family_repo.find_active_family_by_code(db, family_code)
        if family is None and family_code is None:
            matches = family_repo.find_active_families_by_head_and_rm(
                db,
                family_head_name=family_head_name,
                primary_rm_id=primary_rm_id,
            )
            if len(matches) == 1:
                family = matches[0]
            elif len(matches) > 1:
                row.status = ImportRowStatus.CONFLICT
                row.errors.append("FamilyHeadName/PrimaryRM: multiple active families match this row.")
                continue
        member = member_repo.find_active_member_by_can(db, can_number)
        if family is not None:
            row.family_id = family.id
        if member is not None:
            row.member_id = member.id
            if family is not None and member.family_id != family.id:
                row.status = ImportRowStatus.CONFLICT
                row.errors.append(f"CANNumber: existing CAN belongs to family {member.family.family_code}.")
            elif family is None and family_code is None:
                if (
                    member.family.family_head_name.strip().lower() == family_head_name.strip().lower()
                    and member.family.primary_rm_id == primary_rm_id
                ):
                    row.family_id = member.family_id
                else:
                    row.status = ImportRowStatus.CONFLICT
                    row.errors.append(f"CANNumber: existing CAN belongs to family {member.family.family_code}.")


def _safe_raw_data(raw_data: dict[str, str]) -> dict[str, str | None]:
    safe: dict[str, str | None] = {}
    for header in TEMPLATE_COLUMNS:
        value = raw_data.get(header, "")
        sensitive_field = SENSITIVE_HEADER_FIELDS.get(header)
        if sensitive_field is not None:
            safe[header] = mask_pii_value(sensitive_field, value) if str(value).strip() else ""
        else:
            safe[header] = value
    return safe


def _stored_normalized_data(normalized_data: dict[str, Any], settings: Settings) -> dict[str, Any]:
    stored = dict(normalized_data)
    for field_name, pii_field in SENSITIVE_NORMALIZED_FIELDS.items():
        protected = protect_pii_value(pii_field, normalized_data.get(field_name), settings)
        if protected.ciphertext is None:
            stored[field_name] = None
        else:
            stored[field_name] = {
                "ciphertext": protected.ciphertext,
                "masked": protected.masked,
                "search_hash": protected.search_hash,
            }
    return stored


def public_normalized_data(stored_data: dict[str, Any]) -> dict[str, Any]:
    public = dict(stored_data)
    for field_name in SENSITIVE_NORMALIZED_FIELDS:
        value = stored_data.get(field_name)
        public[field_name] = value.get("masked") if isinstance(value, dict) else None
    return public


def import_row_to_response(row: ImportRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "import_batch_id": row.import_batch_id,
        "row_number": row.row_number,
        "raw_data": row.raw_data,
        "normalized_data": public_normalized_data(row.normalized_data),
        "status": row.status,
        "errors": row.errors,
        "family_id": row.family_id,
        "member_id": row.member_id,
        "created_at": row.created_at,
    }


def _batch_to_response(batch: ImportBatch) -> dict[str, Any]:
    return {
        "id": batch.id,
        "file_name": batch.file_name,
        "file_sha256": batch.file_sha256,
        "uploaded_by_user_id": batch.uploaded_by_user_id,
        "status": batch.status,
        "row_count": batch.row_count,
        "valid_row_count": batch.valid_row_count,
        "error_row_count": batch.error_row_count,
        "conflict_row_count": batch.conflict_row_count,
        "committed_row_count": batch.committed_row_count,
        "warnings": batch.warnings,
        "errors": batch.errors,
        "created_at": batch.created_at,
        "committed_at": batch.committed_at,
    }


def _refresh_batch_counts(batch: ImportBatch) -> None:
    rows = list(batch.rows)
    batch.row_count = len(rows)
    batch.valid_row_count = sum(row.status == ImportRowStatus.VALID for row in rows)
    batch.error_row_count = sum(row.status == ImportRowStatus.ERROR for row in rows)
    batch.conflict_row_count = sum(row.status == ImportRowStatus.CONFLICT for row in rows)
    batch.committed_row_count = sum(row.status == ImportRowStatus.COMMITTED for row in rows)


def upload_mfu_template(
    db: Session,
    *,
    file_name: str,
    content: bytes,
    actor: User,
    settings: Settings,
) -> dict[str, Any]:
    if not content:
        _bad_request("empty_import_file", "Import file is empty.")

    batch = ImportBatch(
        file_name=file_name,
        file_sha256=hashlib.sha256(content).hexdigest(),
        uploaded_by_user_id=actor.id,
        status=ImportBatchStatus.UPLOADED,
        row_count=0,
        valid_row_count=0,
        error_row_count=0,
        conflict_row_count=0,
        committed_row_count=0,
        warnings=[],
        errors=[],
    )
    db.add(batch)

    try:
        gateway = TemplateMfuGateway.from_file(file_name, content)
    except TemplateParseError as exc:
        batch.status = ImportBatchStatus.FAILED
        batch.errors = [str(exc)]
        db.commit()
        db.refresh(batch)
        return _batch_to_response(batch)

    batch.warnings = gateway.warnings
    missing_headers = [header for header in REQUIRED_TEMPLATE_COLUMNS if header not in set(gateway.headers)]
    if missing_headers:
        batch.status = ImportBatchStatus.FAILED
        batch.errors = [f"Missing required headers: {', '.join(missing_headers)}"]
        db.commit()
        db.refresh(batch)
        return _batch_to_response(batch)

    rows = [_validate_record(db, record) for record in gateway.fetch_members_since(None)]
    _apply_duplicate_can_errors(rows)
    _apply_existing_record_status(db, rows)

    for validated_row in rows:
        db.add(
            ImportRow(
                batch=batch,
                row_number=validated_row.row_number,
                raw_data=_safe_raw_data(validated_row.raw_data),
                normalized_data=_stored_normalized_data(validated_row.normalized_data, settings),
                status=validated_row.status,
                errors=validated_row.errors,
                family_id=validated_row.family_id,
                member_id=validated_row.member_id,
            )
        )
    db.flush()
    _refresh_batch_counts(batch)
    batch.status = ImportBatchStatus.VALIDATED
    db.commit()
    db.refresh(batch)
    return _batch_to_response(batch)


def list_import_batches(
    db: Session,
    *,
    import_status: ImportBatchStatus | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    filters = []
    if import_status is not None:
        filters.append(ImportBatch.status == import_status)
    total = db.scalar(select(func.count(ImportBatch.id)).where(*filters)) or 0
    batches = list(
        db.scalars(
            select(ImportBatch)
            .where(*filters)
            .order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return {
        "items": [_batch_to_response(batch) for batch in batches],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_import_batch(db: Session, *, batch_id: UUID) -> dict[str, Any]:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        _not_found("import_batch")
    return _batch_to_response(batch)


def list_import_rows(
    db: Session,
    *,
    batch_id: UUID,
    row_status: ImportRowStatus | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    if db.get(ImportBatch, batch_id) is None:
        _not_found("import_batch")
    filters = [ImportRow.import_batch_id == batch_id]
    if row_status is not None:
        filters.append(ImportRow.status == row_status)
    total = db.scalar(select(func.count(ImportRow.id)).where(*filters)) or 0
    rows = list(
        db.scalars(
            select(ImportRow).where(*filters).order_by(ImportRow.row_number, ImportRow.id).limit(limit).offset(offset)
        )
    )
    return {
        "items": [import_row_to_response(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _decrypted_pii_value(field_name: str, stored_data: dict[str, Any], settings: Settings) -> str | None:
    value = stored_data.get(field_name)
    if not isinstance(value, dict):
        return None
    ciphertext = value.get("ciphertext")
    if not isinstance(ciphertext, str):
        return None
    return decrypt_pii_value(SENSITIVE_NORMALIZED_FIELDS[field_name], ciphertext, settings)


def _row_data_for_commit(stored_data: dict[str, Any], settings: Settings) -> dict[str, Any]:
    data = dict(stored_data)
    for field_name in SENSITIVE_NORMALIZED_FIELDS:
        data[field_name] = _decrypted_pii_value(field_name, stored_data, settings)
    return data


def _date_value(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _decimal_value(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def _set_member_protected_field_from_stored(member: Member, field_name: str, stored_data: dict[str, Any]) -> None:
    value = stored_data.get(field_name)
    encrypted_attr = f"{field_name}_encrypted"
    masked_attr = f"{field_name}_masked"
    search_hash_attr = f"{field_name}_search_hash"
    if field_name == "bank_account_number":
        encrypted_attr = "bank_account_number_encrypted"
        masked_attr = "bank_account_number_masked"
        search_hash_attr = "bank_account_number_search_hash"
    if not isinstance(value, dict):
        setattr(member, encrypted_attr, None)
        setattr(member, masked_attr, None)
        setattr(member, search_hash_attr, None)
        return
    setattr(member, encrypted_attr, value.get("ciphertext"))
    setattr(member, masked_attr, value.get("masked"))
    setattr(member, search_hash_attr, value.get("search_hash"))


def _apply_import_member_data(
    member: Member,
    *,
    data: dict[str, Any],
    stored_data: dict[str, Any],
    is_new: bool,
) -> None:
    if is_new:
        member.can_number = data["can_number"]
    member.can_status = data["can_status"]
    member.name = data["member_name"]
    _set_member_protected_field_from_stored(member, "pan", stored_data)
    member.date_of_birth = _date_value(data["date_of_birth"])
    member.kyc_status = data["kyc_status"]
    _set_member_protected_field_from_stored(member, "mobile", stored_data)
    member.mobile_verification_status = data["mobile_verification_status"]
    _set_member_protected_field_from_stored(member, "email", stored_data)
    member.email_verification_status = data["email_verification_status"]
    member.nominee_verification_status = data["nominee_verification_status"]
    member.bank_name = data["bank_name"]
    _set_member_protected_field_from_stored(member, "bank_account_number", stored_data)
    member.ifsc_code = data["ifsc_code"]
    member.payeezz_mandate_status = data["payeezz_mandate_status"]
    member.payeezz_amount = _decimal_value(data["payeezz_amount"])
    member.payeezz_start_date = _date_value(data["payeezz_start_date"])
    if is_new or data.get("remarks"):
        member.remarks = data.get("remarks")


def _active_rm_by_id(db: Session, rm_id: str | UUID | None) -> User | None:
    if rm_id is None:
        return None
    rm = db.scalar(
        select(User).where(
            User.id == UUID(str(rm_id)),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    if rm is None or not user_has_module_role(
        rm,
        ModuleCode.CAN_COMPLIANCE,
        ModuleRole.CAN_RM,
        platform_admin_bypass=False,
    ):
        return None
    return rm


def _mark_commit_conflict(row: ImportRow, message: str) -> None:
    row.status = ImportRowStatus.CONFLICT
    row.errors = [*row.errors, message]
    row.family_id = None
    row.member_id = None


def _family_for_import_row(db: Session, row: ImportRow, data: dict[str, Any], rm: User | None) -> Family | None:
    family_code = data.get("family_code")
    if family_code is not None:
        return family_repo.find_active_family_by_code(db, family_code)
    if row.family_id is not None:
        family = db.get(Family, row.family_id)
        if family is not None and family.deleted_at is None:
            return family
    matches = family_repo.find_active_families_by_head_and_rm(
        db,
        family_head_name=data["family_head_name"],
        primary_rm_id=rm.id if rm is not None else None,
    )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        _mark_commit_conflict(row, "FamilyHeadName/PrimaryRM: multiple active families match this row.")
    return None


def commit_import_batch(
    db: Session,
    *,
    batch_id: UUID,
    actor: User,
    settings: Settings,
    request_id: str | None,
) -> dict[str, Any]:
    batch = db.scalar(select(ImportBatch).options(selectinload(ImportBatch.rows)).where(ImportBatch.id == batch_id))
    if batch is None:
        _not_found("import_batch")
    if batch.status == ImportBatchStatus.COMMITTED:
        _conflict("import_batch_already_committed", "Import batch has already been committed.")
    if batch.status == ImportBatchStatus.FAILED:
        _conflict("import_batch_not_committable", "Failed import batches cannot be committed.")

    valid_rows = [row for row in batch.rows if row.status == ImportRowStatus.VALID]
    if not valid_rows:
        _conflict("no_valid_import_rows", "Import batch has no valid rows to commit.")

    committed_this_run = 0
    for row in sorted(valid_rows, key=lambda item: item.row_number):
        stored_data = row.normalized_data
        data = _row_data_for_commit(stored_data, settings)
        raw_primary_rm_id = data.get("primary_rm_id")
        rm = _active_rm_by_id(db, raw_primary_rm_id)
        if raw_primary_rm_id is not None and rm is None:
            row.status = ImportRowStatus.ERROR
            row.errors = [*row.errors, "PrimaryRM: active RM user no longer exists."]
            continue

        can_number = data["can_number"]
        existing_member = member_repo.find_active_member_by_can(db, can_number)
        family = _family_for_import_row(db, row, data, rm)
        if row.status == ImportRowStatus.CONFLICT:
            continue
        if existing_member is not None and family is not None and existing_member.family_id != family.id:
            _mark_commit_conflict(
                row,
                f"CANNumber: existing CAN belongs to family {existing_member.family.family_code}.",
            )
            continue
        if existing_member is not None and family is None and data.get("family_code") is not None:
            _mark_commit_conflict(
                row,
                f"CANNumber: existing CAN belongs to family {existing_member.family.family_code}.",
            )
            continue
        if existing_member is not None and family is None and data.get("family_code") is None:
            if (
                existing_member.family.family_head_name.strip().lower() == data["family_head_name"].strip().lower()
                and existing_member.family.primary_rm_id == (rm.id if rm is not None else None)
            ):
                family = existing_member.family
            else:
                _mark_commit_conflict(
                    row,
                    f"CANNumber: existing CAN belongs to family {existing_member.family.family_code}.",
                )
                continue

        if family is None:
            family = Family(
                family_code=data.get("family_code") or generate_family_code(db),
                family_head_name=data["family_head_name"],
                primary_rm_id=rm.id if rm is not None else None,
                remarks=data.get("family_remarks"),
            )
            db.add(family)
            db.flush()
            record_create(
                db,
                entity_type=AuditEntityType.FAMILY,
                entity_id=family.id,
                actor_user_id=actor.id,
                source=ChangeSource.IMPORT,
                import_batch_id=batch.id,
                request_id=request_id,
            )
        else:
            old_family_values = {
                "family_code": family.family_code,
                "family_head_name": family.family_head_name,
                "primary_rm_id": family.primary_rm_id,
                "remarks": family.remarks,
            }
            family.family_head_name = data["family_head_name"]
            family.primary_rm_id = rm.id if rm is not None else None
            if data.get("family_remarks"):
                family.remarks = data["family_remarks"]
            db.flush()
            record_update(
                db,
                entity_type=AuditEntityType.FAMILY,
                entity_id=family.id,
                old_values=old_family_values,
                new_values={
                    "family_code": family.family_code,
                    "family_head_name": family.family_head_name,
                    "primary_rm_id": family.primary_rm_id,
                    "remarks": family.remarks,
                },
                actor_user_id=actor.id,
                source=ChangeSource.IMPORT,
                import_batch_id=batch.id,
                request_id=request_id,
            )

        member = existing_member
        if member is None:
            member = Member(family_id=family.id)
            db.add(member)
            _apply_import_member_data(member, data=data, stored_data=stored_data, is_new=True)
            db.flush()
            record_create(
                db,
                entity_type=AuditEntityType.MEMBER,
                entity_id=member.id,
                actor_user_id=actor.id,
                source=ChangeSource.IMPORT,
                import_batch_id=batch.id,
                request_id=request_id,
            )
        else:
            old_member_values = _member_audit_values(member, settings)
            _apply_import_member_data(member, data=data, stored_data=stored_data, is_new=False)
            db.flush()
            record_update(
                db,
                entity_type=AuditEntityType.MEMBER,
                entity_id=member.id,
                old_values=old_member_values,
                new_values=_member_audit_values(member, settings),
                actor_user_id=actor.id,
                source=ChangeSource.IMPORT,
                import_batch_id=batch.id,
                request_id=request_id,
            )

        row.status = ImportRowStatus.COMMITTED
        row.family_id = family.id
        row.member_id = member.id
        row.errors = []
        committed_this_run += 1

    _refresh_batch_counts(batch)
    if committed_this_run:
        batch.status = ImportBatchStatus.COMMITTED
        batch.committed_at = _utc_now()
        record_import_commit(
            db,
            entity_type=AuditEntityType.IMPORT_BATCH,
            entity_id=batch.id,
            actor_user_id=actor.id,
            import_batch_id=batch.id,
            request_id=request_id,
        )
    else:
        batch.status = ImportBatchStatus.FAILED
        batch.committed_at = None
    db.commit()
    db.refresh(batch)
    return _batch_to_response(batch)


__all__ = [
    "FIELD_TO_HEADER",
    "HEADER_TO_FIELD",
    "TEMPLATE_COLUMNS",
    "commit_import_batch",
    "get_import_batch",
    "import_row_to_response",
    "list_import_batches",
    "list_import_rows",
    "public_normalized_data",
    "upload_mfu_template",
]
