from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import AuditAction, AuditEntityType, ChangeSource, UserRole
from app.models.audit import AuditLog
from app.services.audit import (
    field_level_diffs,
    record_create,
    record_import_commit,
    record_sensitive_read,
    record_update,
)


def test_field_level_diffs_skip_unchanged_values_and_mask_sensitive_fields() -> None:
    diffs = field_level_diffs(
        {
            "name": "Client A",
            "pan": "ABCDE1234F",
            "date_of_birth": date(1990, 1, 1),
            "amount": Decimal("100.00"),
            "role": UserRole.OPS,
        },
        {
            "name": "Client B",
            "pan": "XYZAB9876C",
            "date_of_birth": date(1990, 1, 1),
            "amount": Decimal("100.00"),
            "role": UserRole.OPS,
            "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        },
    )

    assert [(diff.field_name, diff.old_value, diff.new_value) for diff in diffs] == [
        ("name", "Client A", "Client B"),
        ("pan", "ABCDE****F", "XYZAB****C"),
    ]


def test_custom_sensitive_fields_union_with_default_pii_fields() -> None:
    diffs = field_level_diffs(
        {"pan": "ABCDE1234F", "password": "configured"},
        {"pan": "XYZAB9876C", "password": "changed"},
        sensitive_fields={"password"},
    )

    assert [(diff.field_name, diff.old_value, diff.new_value) for diff in diffs] == [
        ("pan", "ABCDE****F", "XYZAB****C"),
        ("password", "[REDACTED]", "[REDACTED]"),
    ]


def test_custom_excluded_fields_union_with_default_internal_fields() -> None:
    diffs = field_level_diffs(
        {"password_hash": "old-hash", "name": "Old", "remarks": "Old"},
        {"password_hash": "new-hash", "name": "New", "remarks": "New"},
        excluded_fields={"remarks"},
    )

    assert [(diff.field_name, diff.old_value, diff.new_value) for diff in diffs] == [("name", "Old", "New")]


def test_record_update_adds_one_audit_log_per_changed_field(db_engine, db_session: Session) -> None:
    entity_id = uuid4()
    actor_id = uuid4()

    logs = record_update(
        db_session,
        entity_type=AuditEntityType.MEMBER,
        entity_id=entity_id,
        old_values={"name": "Old", "mobile": "9876543210"},
        new_values={"name": "New", "mobile": "9876500000"},
        actor_user_id=actor_id,
        source=ChangeSource.MANUAL,
        request_id="req-1",
    )
    db_session.commit()

    persisted = list(db_session.scalars(select(AuditLog).order_by(AuditLog.field_name)).all())
    assert logs == persisted
    assert [(log.field_name, log.old_value, log.new_value) for log in persisted] == [
        ("mobile", "******3210", "******0000"),
        ("name", "Old", "New"),
    ]
    assert all(log.entity_type == AuditEntityType.MEMBER for log in persisted)
    assert all(log.action == AuditAction.UPDATE for log in persisted)
    assert all(log.actor_user_id == actor_id for log in persisted)
    assert all(log.request_id == "req-1" for log in persisted)


def test_create_sensitive_read_and_import_commit_audit_helpers(db_engine, db_session: Session) -> None:
    actor_id = uuid4()
    member_id = uuid4()
    import_batch_id = uuid4()

    record_create(
        db_session,
        entity_type=AuditEntityType.MEMBER,
        entity_id=member_id,
        actor_user_id=actor_id,
    )
    record_sensitive_read(
        db_session,
        entity_type=AuditEntityType.MEMBER,
        entity_id=member_id,
        field_names=["pan", "email"],
        actor_user_id=actor_id,
    )
    record_import_commit(
        db_session,
        entity_type=AuditEntityType.IMPORT_BATCH,
        entity_id=import_batch_id,
        actor_user_id=actor_id,
        import_batch_id=import_batch_id,
    )
    db_session.commit()

    logs = list(db_session.scalars(select(AuditLog).order_by(AuditLog.action, AuditLog.field_name)).all())
    assert {(log.action, log.field_name) for log in logs} == {
        (AuditAction.CREATE, None),
        (AuditAction.SENSITIVE_READ, "pan"),
        (AuditAction.SENSITIVE_READ, "email"),
        (AuditAction.IMPORT_COMMIT, None),
    }
    import_commit = next(log for log in logs if log.action == AuditAction.IMPORT_COMMIT)
    assert import_commit.source == ChangeSource.IMPORT
    assert import_commit.import_batch_id == import_batch_id
