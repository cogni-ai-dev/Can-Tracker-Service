from __future__ import annotations

import csv
from io import BytesIO, StringIO
from uuid import UUID
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.domain.enums import AuditAction, ChangeSource, KycStatus, PayeezzStatus, UserRole, VerificationStatus
from app.main import create_app
from app.models.audit import AuditLog
from app.models.family import Family, Member
from app.models.imports import ImportRow
from app.models.user import User
from app.services.mfu_gateway import TEMPLATE_COLUMNS

PASSWORD = "password123"


def create_test_user(
    db_session: Session,
    *,
    email: str,
    role: UserRole,
    password: str = PASSWORD,
    name: str | None = None,
    is_active: bool = True,
) -> User:
    user = User(
        name=name or email.split("@", 1)[0].replace(".", " ").title(),
        email=email.lower(),
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def client_for(settings: Settings) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=create_app(settings=settings))
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def login(client: httpx.AsyncClient, email: str, password: str = PASSWORD) -> httpx.Response:
    return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


def template_row(**overrides: str) -> dict[str, str]:
    row = {
        "FamilyCode": "FAM-IMP",
        "FamilyHeadName": "Import Head",
        "PrimaryRMEmail": "rm@example.test",
        "PrimaryRMName": "",
        "FamilyRemarks": "Imported family",
        "MemberName": "Import Member",
        "CANNumber": "CAN-IMP-001",
        "PAN": "ABCDE1234F",
        "DateOfBirth": "1990-01-01",
        "KYCStatus": "Validated",
        "Mobile": "9876543210",
        "MobileStatus": "Verified",
        "Email": "import.member@example.test",
        "EmailStatus": "Verified",
        "NomineeStatus": "Verified",
        "BankName": "HDFC Bank",
        "AccountNumber": "001122334455",
        "IFSC": "HDFC0123456",
        "PayEezzStatus": "Aggregator Accepted",
        "PayEezzAmount": "1000.00",
        "PayEezzStartDate": "2026-01-01",
        "Remarks": "Imported member",
    }
    row.update(overrides)
    return row


def csv_template_bytes(rows: list[dict[str, str]], headers: tuple[str, ...] = TEMPLATE_COLUMNS) -> bytes:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def _cell_ref(column_index: int, row_number: int) -> str:
    letters = ""
    column = column_index + 1
    while column:
        column, remainder = divmod(column - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return f"{letters}{row_number}"


def xlsx_template_bytes(rows: list[dict[str, str]], headers: tuple[str, ...] = TEMPLATE_COLUMNS) -> bytes:
    all_rows = [list(headers), *[[row.get(header, "") for header in headers] for row in rows]]
    sheet_rows = []
    for row_index, values in enumerate(all_rows, start=1):
        cells = []
        for column_index, value in enumerate(values):
            ref = _cell_ref(column_index, row_index)
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData>"
        "</worksheet>"
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    package_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", content_types)
        workbook.writestr("_rels/.rels", package_rels)
        workbook.writestr("xl/workbook.xml", workbook_xml)
        workbook.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


async def upload_file(client: httpx.AsyncClient, file_name: str, content: bytes) -> httpx.Response:
    return await client.post(
        "/api/v1/imports/mfu-template/upload",
        files={"file": (file_name, content, "application/octet-stream")},
    )


@pytest.mark.asyncio
async def test_upload_accepts_valid_csv_and_masks_preview_pii(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM One")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "valid.csv", csv_template_bytes([template_row()]))
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")
        list_response = await client.get("/api/v1/imports")
        detail_response = await client.get(f"/api/v1/imports/{batch['id']}")

    assert upload.status_code == 201, upload.text
    assert batch["status"] == "validated"
    assert batch["valid_row_count"] == 1
    assert batch["error_row_count"] == 0
    assert batch["conflict_row_count"] == 0
    assert list_response.json()["total"] == 1
    assert detail_response.json()["id"] == batch["id"]
    row = rows.json()["items"][0]
    assert row["status"] == "valid"
    assert row["raw_data"]["PAN"] == "ABCDE****F"
    assert row["normalized_data"]["pan"] == "ABCDE****F"
    assert "ABCDE1234F" not in str(row)
    assert "9876543210" not in str(row)
    assert "001122334455" not in str(row)


@pytest.mark.asyncio
async def test_upload_accepts_valid_xlsx(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    ops = create_test_user(db_session, email="ops@example.test", role=UserRole.OPS)
    create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM One")

    async with client_for(test_settings) as client:
        assert (await login(client, ops.email)).status_code == 200
        upload = await upload_file(
            client,
            "valid.xlsx",
            xlsx_template_bytes([template_row(FamilyCode="FAM-XLSX", CANNumber="CAN-XLSX")]),
        )

    assert upload.status_code == 201, upload.text
    assert upload.json()["status"] == "validated"
    assert upload.json()["valid_row_count"] == 1


@pytest.mark.asyncio
async def test_upload_with_missing_required_header_fails_batch_validation(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    create_test_user(db_session, email="rm@example.test", role=UserRole.RM)
    headers = tuple(header for header in TEMPLATE_COLUMNS if header != "CANNumber")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "bad-headers.csv", csv_template_bytes([template_row()], headers=headers))

    body = upload.json()
    assert upload.status_code == 201
    assert body["status"] == "failed"
    assert body["row_count"] == 0
    assert body["errors"] == ["Missing required headers: CANNumber"]


@pytest.mark.asyncio
async def test_upload_marks_invalid_rows_and_duplicate_cans_as_errors(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    create_test_user(db_session, email="rm@example.test", role=UserRole.RM)
    rows = [
        template_row(
            FamilyCode="FAM-BAD",
            CANNumber="CAN-BAD",
            PAN="bad-pan",
            DateOfBirth="01-01-1990",
            KYCStatus="Bad Status",
            IFSC="BAD",
            PayEezzAmount="-1",
        ),
        template_row(FamilyCode="FAM-DUP", CANNumber="CAN-DUP"),
        template_row(FamilyCode="FAM-DUP", CANNumber="CAN-DUP", MemberName="Duplicate Member"),
    ]

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "invalid.csv", csv_template_bytes(rows))
        batch = upload.json()
        row_response = await client.get(f"/api/v1/imports/{batch['id']}/rows?status=error")

    assert upload.status_code == 201
    assert batch["status"] == "validated"
    assert batch["valid_row_count"] == 0
    assert batch["error_row_count"] == 3
    error_rows = row_response.json()["items"]
    assert row_response.json()["total"] == 3
    assert any("KYCStatus" in " ".join(row["errors"]) for row in error_rows)
    assert any("PAN" in " ".join(row["errors"]) for row in error_rows)
    assert sum("duplicate CAN" in " ".join(row["errors"]) for row in error_rows) == 2


@pytest.mark.asyncio
async def test_commit_applies_valid_rows_preserves_local_remarks_leaves_conflicts_and_audits(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm_one = create_test_user(db_session, email="rm.one@example.test", role=UserRole.RM, name="RM One")
    rm_two = create_test_user(db_session, email="rm.two@example.test", role=UserRole.RM, name="RM Two")
    local_family = Family(
        family_code="FAM-LOCAL",
        family_head_name="Local Head",
        primary_rm_id=rm_one.id,
        remarks="Local family remarks",
    )
    other_family = Family(
        family_code="FAM-OTHER",
        family_head_name="Other Head",
        primary_rm_id=rm_one.id,
        remarks="Other family remarks",
    )
    db_session.add_all([local_family, other_family])
    db_session.flush()
    local_member = Member(
        family_id=local_family.id,
        name="Old Member",
        can_number="CAN-UPDATE",
        kyc_status=KycStatus.NO_KYC,
        mobile_status=VerificationStatus.NOT_VERIFIED,
        email_status=VerificationStatus.NOT_VERIFIED,
        nominee_status=VerificationStatus.NOT_VERIFIED,
        payeezz_status=PayeezzStatus.NOT_AVAILABLE,
        remarks="Local member remarks",
    )
    conflict_member = Member(
        family_id=other_family.id,
        name="Conflict Original",
        can_number="CAN-CONFLICT",
        kyc_status=KycStatus.NO_KYC,
        mobile_status=VerificationStatus.NOT_VERIFIED,
        email_status=VerificationStatus.NOT_VERIFIED,
        nominee_status=VerificationStatus.NOT_VERIFIED,
        payeezz_status=PayeezzStatus.NOT_AVAILABLE,
        remarks="Conflict remarks",
    )
    db_session.add_all([local_member, conflict_member])
    db_session.commit()

    import_rows = [
        template_row(
            FamilyCode="FAM-LOCAL",
            FamilyHeadName="Updated Head",
            PrimaryRMEmail=rm_two.email,
            FamilyRemarks="",
            MemberName="Updated Member",
            CANNumber="CAN-UPDATE",
            PAN="XYZAB9876C",
            KYCStatus="Validated",
            MobileStatus="Verified",
            EmailStatus="Verified",
            NomineeStatus="Verified",
            PayEezzStatus="Aggregator Accepted",
            Remarks="",
        ),
        template_row(
            FamilyCode="FAM-LOCAL",
            FamilyHeadName="Updated Head",
            PrimaryRMEmail=rm_two.email,
            CANNumber="CAN-CONFLICT",
            MemberName="Should Not Apply",
        ),
        template_row(
            FamilyCode="FAM-NEW",
            FamilyHeadName="New Head",
            PrimaryRMEmail=rm_two.email,
            FamilyRemarks="New family remarks",
            CANNumber="CAN-NEW",
            MemberName="New Member",
            Remarks="New member remarks",
        ),
    ]

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "commit.csv", csv_template_bytes(import_rows))
        batch = upload.json()
        preview_conflicts = await client.get(f"/api/v1/imports/{batch['id']}/rows?status=conflict")
        commit = await client.post(
            f"/api/v1/imports/{batch['id']}/commit",
            headers={"x-request-id": "req-import-commit"},
        )
        second_commit = await client.post(f"/api/v1/imports/{batch['id']}/commit")

    assert upload.status_code == 201, upload.text
    assert batch["valid_row_count"] == 2
    assert batch["conflict_row_count"] == 1
    assert preview_conflicts.json()["total"] == 1
    assert commit.status_code == 200, commit.text
    committed_batch = commit.json()
    assert committed_batch["status"] == "committed"
    assert committed_batch["committed_row_count"] == 2
    assert committed_batch["conflict_row_count"] == 1
    assert second_commit.status_code == 409
    assert second_commit.json()["error"]["code"] == "import_batch_already_committed"

    db_session.expire_all()
    persisted_family = db_session.get(Family, local_family.id)
    persisted_member = db_session.get(Member, local_member.id)
    persisted_conflict = db_session.get(Member, conflict_member.id)
    new_family = db_session.scalar(select(Family).where(Family.family_code == "FAM-NEW"))
    new_member = db_session.scalar(select(Member).where(Member.can_number == "CAN-NEW"))
    assert persisted_family is not None
    assert persisted_family.family_head_name == "Updated Head"
    assert persisted_family.primary_rm_id == rm_two.id
    assert persisted_family.remarks == "Local family remarks"
    assert persisted_member is not None
    assert persisted_member.name == "Updated Member"
    assert persisted_member.kyc_status == KycStatus.VALIDATED
    assert persisted_member.remarks == "Local member remarks"
    assert persisted_member.family_id == local_family.id
    assert persisted_conflict is not None
    assert persisted_conflict.name == "Conflict Original"
    assert persisted_conflict.family_id == other_family.id
    assert new_family is not None and new_family.remarks == "New family remarks"
    assert new_member is not None and new_member.family_id == new_family.id
    assert new_member.remarks == "New member remarks"

    conflict_row = db_session.scalar(select(ImportRow).where(ImportRow.member_id == conflict_member.id))
    assert conflict_row is not None
    assert conflict_row.status == "conflict"

    audit_logs = list(
        db_session.scalars(
            select(AuditLog)
            .where(AuditLog.import_batch_id == UUID(batch["id"]))
            .order_by(AuditLog.action, AuditLog.field_name)
        )
    )
    assert audit_logs
    assert {log.source for log in audit_logs} == {ChangeSource.IMPORT}
    assert {log.request_id for log in audit_logs} == {"req-import-commit"}
    assert any(log.action == AuditAction.CREATE and log.entity_id == new_member.id for log in audit_logs)
    assert any(log.action == AuditAction.UPDATE and log.field_name == "kyc_status" for log in audit_logs)
    pan_log = next(log for log in audit_logs if log.field_name == "pan")
    assert pan_log.new_value == "XYZAB****C"
    assert "XYZAB9876C" not in str([log.old_value for log in audit_logs] + [log.new_value for log in audit_logs])


@pytest.mark.asyncio
async def test_commit_does_not_mark_batch_committed_when_recheck_conflicts_all_valid_rows(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(
            client,
            "stale.csv",
            csv_template_bytes([template_row(FamilyCode="FAM-STALE", CANNumber="CAN-STALE")]),
        )
        batch = upload.json()

        other_family = Family(family_code="FAM-OTHER", family_head_name="Other", primary_rm_id=rm.id)
        db_session.add(other_family)
        db_session.flush()
        db_session.add(
            Member(
                family_id=other_family.id,
                name="Late Conflict",
                can_number="CAN-STALE",
                kyc_status=KycStatus.NO_KYC,
                mobile_status=VerificationStatus.NOT_VERIFIED,
                email_status=VerificationStatus.NOT_VERIFIED,
                nominee_status=VerificationStatus.NOT_VERIFIED,
                payeezz_status=PayeezzStatus.NOT_AVAILABLE,
            )
        )
        db_session.commit()

        commit = await client.post(f"/api/v1/imports/{batch['id']}/commit")

    assert upload.status_code == 201
    assert batch["valid_row_count"] == 1
    assert commit.status_code == 200
    body = commit.json()
    assert body["status"] == "failed"
    assert body["committed_row_count"] == 0
    assert body["conflict_row_count"] == 1
    assert (
        db_session.scalar(
            select(AuditLog).where(
                AuditLog.import_batch_id == UUID(batch["id"]),
                AuditLog.action == AuditAction.IMPORT_COMMIT,
            )
        )
        is None
    )
