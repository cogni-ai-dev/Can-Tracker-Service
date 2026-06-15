from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pii import AUDIT_REDACTED_FIELDS, SENSITIVE_PII_FIELDS, mask_pii_value, normalize_pii_value
from app.domain.enums import AuditAction, AuditEntityType, ChangeSource
from app.models.audit import AuditLog

DEFAULT_AUDIT_EXCLUDED_FIELDS = frozenset(
    {
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "password_hash",
        "session_token_hash",
    }
)


@dataclass(frozen=True)
class FieldDiff:
    field_name: str
    old_value: str | None
    new_value: str | None


def _enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value


def _canonical_compare_value(field_name: str, value: object | None, sensitive_fields: set[str]) -> object | None:
    value = _enum_value(value)
    if value is None:
        return None
    if field_name in sensitive_fields:
        return normalize_pii_value(field_name, value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    return value


def _audit_display_value(field_name: str, value: object | None, sensitive_fields: set[str]) -> str | None:
    value = _enum_value(value)
    if value is None:
        return None
    if field_name in sensitive_fields or field_name in AUDIT_REDACTED_FIELDS:
        return mask_pii_value(field_name, value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def field_level_diffs(
    old_values: Mapping[str, object | None],
    new_values: Mapping[str, object | None],
    *,
    sensitive_fields: set[str] | None = None,
    excluded_fields: set[str] | None = None,
) -> list[FieldDiff]:
    sensitive = set(SENSITIVE_PII_FIELDS)
    if sensitive_fields is not None:
        sensitive.update(sensitive_fields)
    excluded = set(DEFAULT_AUDIT_EXCLUDED_FIELDS)
    if excluded_fields is not None:
        excluded.update(excluded_fields)
    diffs: list[FieldDiff] = []

    for field_name in sorted(set(old_values) | set(new_values)):
        if field_name in excluded:
            continue
        old_value = old_values.get(field_name)
        new_value = new_values.get(field_name)
        old_compare = _canonical_compare_value(field_name, old_value, sensitive)
        new_compare = _canonical_compare_value(field_name, new_value, sensitive)
        if old_compare == new_compare:
            continue
        diffs.append(
            FieldDiff(
                field_name=field_name,
                old_value=_audit_display_value(field_name, old_value, sensitive),
                new_value=_audit_display_value(field_name, new_value, sensitive),
            )
        )
    return diffs


def add_audit_log(
    db: Session,
    *,
    entity_type: AuditEntityType,
    entity_id: UUID,
    action: AuditAction,
    actor_user_id: UUID | None,
    source: ChangeSource = ChangeSource.MANUAL,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    import_batch_id: UUID | None = None,
    request_id: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        actor_user_id=actor_user_id,
        source=source,
        import_batch_id=import_batch_id,
        request_id=request_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit_log)
    return audit_log


def record_create(
    db: Session,
    *,
    entity_type: AuditEntityType,
    entity_id: UUID,
    actor_user_id: UUID | None,
    source: ChangeSource = ChangeSource.MANUAL,
    import_batch_id: UUID | None = None,
    request_id: str | None = None,
) -> AuditLog:
    return add_audit_log(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.CREATE,
        actor_user_id=actor_user_id,
        source=source,
        new_value="created",
        import_batch_id=import_batch_id,
        request_id=request_id,
    )


def record_update(
    db: Session,
    *,
    entity_type: AuditEntityType,
    entity_id: UUID,
    old_values: Mapping[str, object | None],
    new_values: Mapping[str, object | None],
    actor_user_id: UUID | None,
    source: ChangeSource = ChangeSource.MANUAL,
    sensitive_fields: set[str] | None = None,
    import_batch_id: UUID | None = None,
    request_id: str | None = None,
) -> list[AuditLog]:
    audit_logs = []
    for diff in field_level_diffs(old_values, new_values, sensitive_fields=sensitive_fields):
        audit_logs.append(
            add_audit_log(
                db,
                entity_type=entity_type,
                entity_id=entity_id,
                action=AuditAction.UPDATE,
                actor_user_id=actor_user_id,
                source=source,
                field_name=diff.field_name,
                old_value=diff.old_value,
                new_value=diff.new_value,
                import_batch_id=import_batch_id,
                request_id=request_id,
            )
        )
    return audit_logs


def record_delete(
    db: Session,
    *,
    entity_type: AuditEntityType,
    entity_id: UUID,
    actor_user_id: UUID | None,
    source: ChangeSource = ChangeSource.MANUAL,
    import_batch_id: UUID | None = None,
    request_id: str | None = None,
) -> AuditLog:
    return add_audit_log(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.DELETE,
        actor_user_id=actor_user_id,
        source=source,
        old_value="active",
        new_value="deleted",
        import_batch_id=import_batch_id,
        request_id=request_id,
    )


def record_sensitive_read(
    db: Session,
    *,
    entity_type: AuditEntityType,
    entity_id: UUID,
    field_names: Sequence[str],
    actor_user_id: UUID | None,
    source: ChangeSource = ChangeSource.MANUAL,
    request_id: str | None = None,
) -> list[AuditLog]:
    return [
        add_audit_log(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=AuditAction.SENSITIVE_READ,
            field_name=field_name,
            actor_user_id=actor_user_id,
            source=source,
            request_id=request_id,
        )
        for field_name in field_names
    ]


def record_import_commit(
    db: Session,
    *,
    entity_type: AuditEntityType,
    entity_id: UUID,
    actor_user_id: UUID | None,
    import_batch_id: UUID,
    request_id: str | None = None,
) -> AuditLog:
    return add_audit_log(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.IMPORT_COMMIT,
        actor_user_id=actor_user_id,
        source=ChangeSource.IMPORT,
        import_batch_id=import_batch_id,
        new_value="committed",
        request_id=request_id,
    )
