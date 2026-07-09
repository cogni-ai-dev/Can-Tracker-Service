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
from app.models.family import Family, Member, MemberBankAccount
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
        "KYCStatus": "Verified",
        "Mobile": "9876543210",
        "MobileStatus": "Verified",
        "Email": "import.member@example.test",
        "EmailStatus": "Verified",
        "NomineeStatus": "Verified",
        "BankName": "HDFC Bank",
        "AccountNumber": "001122334455",
        "IFSC": "HDFC0123456",
        "PayEezzStatus": "Approved",
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
        upload = await upload_file(
            client,
            "valid.csv",
            csv_template_bytes([template_row(Nominee="Initial Nominee")]),
        )
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
    assert row["normalized_data"]["nominee_name"] == "Initial Nominee"
    assert row["status"] == "valid"
    assert row["raw_data"]["PAN"] == "ABCDE****F"
    assert row["normalized_data"]["pan"] == "ABCDE****F"
    assert "ABCDE1234F" not in str(row)
    assert "9876543210" not in str(row)
    assert "001122334455" not in str(row)


@pytest.mark.asyncio
async def test_upload_accepts_nominee_name_aliases_and_commits_nominee(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM One")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(
            client,
            "nominee-alias.csv",
            csv_template_bytes(
                [
                template_row(
                    FamilyCode="FAM-NOM-ALIAS",
                    CANNumber="CAN-NOM-ALIAS",
                    Nominee="Alias Nominee",
                    NomineeName="",
                ),
                template_row(
                    FamilyCode="FAM-NOM-ALIAS-2",
                    CANNumber="CAN-NOM-ALIAS-2",
                    NomineeStatus="Verified",
                    NomineeName="Name Alt",
                ),
                ],
                headers=TEMPLATE_COLUMNS + ("NomineeName",),
            ),
        )
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")
        commit = await client.post(f"/api/v1/imports/{batch['id']}/commit")

    assert upload.status_code == 201, upload.text
    items = rows.json()["items"]
    assert len(items) == 2
    assert [item["normalized_data"]["nominee_name"] for item in items] == ["Alias Nominee", "Name Alt"]
    assert commit.status_code == 200, commit.text

    db_session.expire_all()
    assert db_session.scalar(select(Member).where(Member.can_number == "CAN-NOM-ALIAS")).nominee_name == "Alias Nominee"
    assert db_session.scalar(select(Member).where(Member.can_number == "CAN-NOM-ALIAS-2")).nominee_name == "Name Alt"


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
async def test_upload_accepts_missing_family_code_header_and_commit_generates_family_code(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM One")
    headers = tuple(header for header in TEMPLATE_COLUMNS if header != "FamilyCode")
    row = template_row(
        FamilyHeadName="Generated Import Head",
        PrimaryRMEmail=rm.email,
        CANNumber="CAN-GENERATED-IMPORT",
    )

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "generated-family.csv", csv_template_bytes([row], headers=headers))
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")
        commit = await client.post(f"/api/v1/imports/{batch['id']}/commit")

    assert upload.status_code == 201, upload.text
    assert batch["status"] == "validated"
    assert batch["valid_row_count"] == 1
    normalized = rows.json()["items"][0]["normalized_data"]
    assert normalized["family_code"] is None
    assert commit.status_code == 200, commit.text

    db_session.expire_all()
    family = db_session.scalar(select(Family).where(Family.family_head_name == "Generated Import Head"))
    member = db_session.scalar(select(Member).where(Member.can_number == "CAN-GENERATED-IMPORT"))
    assert family is not None
    assert family.family_code.startswith("FAM-")
    assert family.family_code.endswith("-0001")
    assert member is not None and member.family_id == family.id


@pytest.mark.asyncio
async def test_upload_treats_na_optional_cells_as_blank_values(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    row = template_row(
        FamilyCode="NA",
        FamilyHeadName="NA Optional Head",
        PrimaryRMEmail="NA",
        PrimaryRMName="NA",
        Nominee="NA",
        FamilyRemarks="NA",
        MemberName="NA Optional Member",
        CANNumber="NA",
        PAN="NA",
        DateOfBirth="NA",
        Mobile="NA",
        Email="NA",
        BankName="NA",
        AccountNumber="NA",
        IFSC="NA",
        PayEezzAmount="NA",
        PayEezzStartDate="NA",
        Remarks="NA",
    )

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "na-optional.csv", csv_template_bytes([row]))
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")
        commit = await client.post(f"/api/v1/imports/{batch['id']}/commit")

    assert upload.status_code == 201, upload.text
    assert batch["valid_row_count"] == 1
    normalized = rows.json()["items"][0]["normalized_data"]
    assert normalized["family_code"] is None
    assert normalized["primary_rm_id"] is None
    assert normalized["family_remarks"] is None
    assert normalized["can_number"] is None
    assert normalized["pan"] is None
    assert normalized["nominee_name"] is None
    assert normalized["date_of_birth"] is None
    assert normalized["mobile"] is None
    assert normalized["email"] is None
    assert normalized["bank_name"] is None
    assert normalized["bank_account_number"] is None
    assert normalized["ifsc_code"] is None
    assert normalized["payeezz_amount"] is None
    assert normalized["payeezz_start_date"] is None
    assert normalized["remarks"] is None
    assert commit.status_code == 200, commit.text


@pytest.mark.asyncio
async def test_import_without_family_code_matches_existing_family_by_head_and_rm(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM One")
    family = Family(family_code="FAM-EXISTING", family_head_name="Existing Head", primary_rm_id=rm.id)
    db_session.add(family)
    db_session.commit()

    row = template_row(
        FamilyCode="",
        FamilyHeadName="Existing Head",
        PrimaryRMEmail=rm.email,
        CANNumber="CAN-MATCHED-FAMILY",
    )

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "matched-family.csv", csv_template_bytes([row]))
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")
        commit = await client.post(f"/api/v1/imports/{batch['id']}/commit")

    assert upload.status_code == 201, upload.text
    assert batch["valid_row_count"] == 1
    assert rows.json()["items"][0]["family_id"] == str(family.id)
    assert commit.status_code == 200, commit.text

    db_session.expire_all()
    member = db_session.scalar(select(Member).where(Member.can_number == "CAN-MATCHED-FAMILY"))
    assert member is not None and member.family_id == family.id
    assert db_session.scalar(select(Family).where(Family.family_code.like("FAM-%-0001"))) is None


@pytest.mark.asyncio
async def test_import_without_family_code_conflicts_when_head_and_rm_match_multiple_families(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM One")
    db_session.add_all(
        [
            Family(family_code="FAM-DUP-1", family_head_name="Duplicate Head", primary_rm_id=rm.id),
            Family(family_code="FAM-DUP-2", family_head_name="Duplicate Head", primary_rm_id=rm.id),
        ]
    )
    db_session.commit()

    row = template_row(
        FamilyCode="",
        FamilyHeadName="Duplicate Head",
        PrimaryRMEmail=rm.email,
        CANNumber="CAN-DUP-FAMILY-MATCH",
    )

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "ambiguous-family.csv", csv_template_bytes([row]))
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")

    assert upload.status_code == 201, upload.text
    assert batch["valid_row_count"] == 0
    assert batch["conflict_row_count"] == 1
    conflict_row = rows.json()["items"][0]
    assert conflict_row["status"] == "conflict"
    assert "multiple active families match" in " ".join(conflict_row["errors"])


@pytest.mark.asyncio
async def test_import_with_blank_rm_creates_unassigned_family(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    row = template_row(
        FamilyCode="",
        FamilyHeadName="Unassigned Import Head",
        PrimaryRMEmail="",
        PrimaryRMName="",
        CANNumber="CAN-UNASSIGNED-IMPORT",
    )

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "unassigned-family.csv", csv_template_bytes([row]))
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")
        commit = await client.post(f"/api/v1/imports/{batch['id']}/commit")

    assert upload.status_code == 201, upload.text
    assert batch["valid_row_count"] == 1
    assert rows.json()["items"][0]["normalized_data"]["primary_rm_id"] is None
    assert commit.status_code == 200, commit.text

    db_session.expire_all()
    family = db_session.scalar(select(Family).where(Family.family_head_name == "Unassigned Import Head"))
    member = db_session.scalar(select(Member).where(Member.can_number == "CAN-UNASSIGNED-IMPORT"))
    assert family is not None and family.primary_rm_id is None
    assert member is not None and member.family_id == family.id


@pytest.mark.asyncio
async def test_import_without_family_code_matches_unassigned_family_by_head(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    family = Family(family_code="FAM-UNASSIGNED", family_head_name="Unassigned Match Head", primary_rm_id=None)
    db_session.add(family)
    db_session.commit()

    row = template_row(
        FamilyCode="",
        FamilyHeadName="Unassigned Match Head",
        PrimaryRMEmail="",
        PrimaryRMName="",
        CANNumber="CAN-UNASSIGNED-MATCH",
    )

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "unassigned-match.csv", csv_template_bytes([row]))
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")
        commit = await client.post(f"/api/v1/imports/{batch['id']}/commit")

    assert upload.status_code == 201, upload.text
    assert batch["valid_row_count"] == 1
    assert rows.json()["items"][0]["family_id"] == str(family.id)
    assert commit.status_code == 200, commit.text

    db_session.expire_all()
    member = db_session.scalar(select(Member).where(Member.can_number == "CAN-UNASSIGNED-MATCH"))
    assert member is not None and member.family_id == family.id


@pytest.mark.asyncio
async def test_import_without_family_code_conflicts_when_multiple_unassigned_heads_match(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    db_session.add_all(
        [
            Family(family_code="FAM-UNASSIGNED-1", family_head_name="Duplicate Unassigned", primary_rm_id=None),
            Family(family_code="FAM-UNASSIGNED-2", family_head_name="Duplicate Unassigned", primary_rm_id=None),
        ]
    )
    db_session.commit()

    row = template_row(
        FamilyCode="",
        FamilyHeadName="Duplicate Unassigned",
        PrimaryRMEmail="",
        PrimaryRMName="",
        CANNumber="CAN-UNASSIGNED-CONFLICT",
    )

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "unassigned-conflict.csv", csv_template_bytes([row]))
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")

    assert upload.status_code == 201, upload.text
    assert batch["valid_row_count"] == 0
    assert batch["conflict_row_count"] == 1
    conflict_row = rows.json()["items"][0]
    assert conflict_row["status"] == "conflict"
    assert "multiple active families match" in " ".join(conflict_row["errors"])


@pytest.mark.asyncio
async def test_upload_defaults_blank_can_and_status_cells_to_pending_values(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM One")
    row = template_row(
        FamilyCode="FAM-PENDING-IMPORT",
        MemberName="Pending Import Member",
        CANNumber="",
        KYCStatus="",
        MobileStatus="",
        EmailStatus="",
        NomineeStatus="",
        PayEezzStatus="",
    )

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        upload = await upload_file(client, "pending-defaults.csv", csv_template_bytes([row]))
        batch = upload.json()
        rows = await client.get(f"/api/v1/imports/{batch['id']}/rows")
        commit = await client.post(f"/api/v1/imports/{batch['id']}/commit")

    assert upload.status_code == 201, upload.text
    assert batch["status"] == "validated"
    assert batch["valid_row_count"] == 1
    normalized = rows.json()["items"][0]["normalized_data"]
    assert normalized["can_number"] is None
    assert normalized["can_status"] == "Pending"
    assert normalized["kyc_status"] == "Not Started"
    assert normalized["mobile_verification_status"] == "Pending Verification"
    assert normalized["email_verification_status"] == "Pending Verification"
    assert normalized["nominee_verification_status"] == "Pending Verification"
    assert normalized["payeezz_mandate_status"] == "Not Started"
    assert commit.status_code == 200, commit.text

    db_session.expire_all()
    member = db_session.scalar(select(Member).where(Member.name == "Pending Import Member"))
    assert member is not None
    assert member.can_number is None
    assert member.can_status == "Pending"
    assert member.kyc_status == KycStatus.NOT_STARTED
    assert member.mobile_verification_status == VerificationStatus.PENDING_VERIFICATION
    assert member.email_verification_status == VerificationStatus.PENDING_VERIFICATION
    assert member.nominee_verification_status == VerificationStatus.PENDING_VERIFICATION
    assert len(member.bank_accounts) == 1
    assert member.bank_accounts[0].is_primary is True
    assert member.bank_accounts[0].payeezz_mandate_status == PayeezzStatus.NOT_STARTED


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
    assert batch["valid_row_count"] == 2
    assert batch["error_row_count"] == 1
    error_rows = row_response.json()["items"]
    assert row_response.json()["total"] == 1
    assert any("KYCStatus" in " ".join(row["errors"]) for row in error_rows)
    assert any("PAN" in " ".join(row["errors"]) for row in error_rows)


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
        can_status="Available",
        kyc_status=KycStatus.NOT_STARTED,
        mobile_verification_status=VerificationStatus.PENDING_VERIFICATION,
        email_verification_status=VerificationStatus.PENDING_VERIFICATION,
        nominee_verification_status=VerificationStatus.PENDING_VERIFICATION,
        remarks="Local member remarks",
    )
    conflict_member = Member(
        family_id=other_family.id,
        name="Conflict Original",
        can_number="CAN-CONFLICT",
        can_status="Available",
        kyc_status=KycStatus.NOT_STARTED,
        mobile_verification_status=VerificationStatus.PENDING_VERIFICATION,
        email_verification_status=VerificationStatus.PENDING_VERIFICATION,
        nominee_verification_status=VerificationStatus.PENDING_VERIFICATION,
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
            KYCStatus="Verified",
            MobileStatus="Verified",
            EmailStatus="Verified",
            NomineeStatus="Verified",
            PayEezzStatus="Approved",
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
    assert persisted_member.kyc_status == KycStatus.VERIFIED
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
                can_status="Available",
                kyc_status=KycStatus.NOT_STARTED,
                mobile_verification_status=VerificationStatus.PENDING_VERIFICATION,
                email_verification_status=VerificationStatus.PENDING_VERIFICATION,
                nominee_verification_status=VerificationStatus.PENDING_VERIFICATION,
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
