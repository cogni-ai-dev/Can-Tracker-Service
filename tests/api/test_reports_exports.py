import csv
import io
import zipfile
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import ReportExportFormat, ReportType, UserRole
from app.models.reporting import ReportExport
from tests.api.test_dashboard_tasks import create_mixed_dashboard_fixture
from tests.api.test_family_member_crud import (
    client_for,
    create_family,
    create_member,
    create_test_user,
    login,
)

REPORT_EXPECTED_TOTALS = {
    ReportType.KYC_PENDING.value: 2,
    ReportType.PAYEEZZ_PENDING.value: 2,
    ReportType.CONTACT_PENDING.value: 2,
    ReportType.FAMILY_COMPLIANCE.value: 2,
    ReportType.RM_TASKS.value: 1,
    ReportType.FULL.value: 4,
}


async def create_report_fixture(
    client: httpx.AsyncClient,
    *,
    rm_one_id: UUID,
    rm_two_id: UUID,
) -> tuple[dict[str, object], dict[str, object]]:
    return await create_mixed_dashboard_fixture(client, rm_one_id=rm_one_id, rm_two_id=rm_two_id)


def csv_rows(content: bytes) -> list[list[str]]:
    text = content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def xlsx_sheet_xml(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert "[Content_Types].xml" in archive.namelist()
        assert "xl/worksheets/sheet1.xml" in archive.namelist()
        return archive.read("xl/worksheets/sheet1.xml").decode("utf-8")


@pytest.mark.asyncio
@pytest.mark.parametrize("report_type,expected_total", REPORT_EXPECTED_TOTALS.items())
async def test_report_preview_returns_expected_rows_for_each_report_type(
    report_type: str,
    expected_total: int,
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm_one = create_test_user(db_session, email="rm.one@example.test", role=UserRole.RM, name="RM One")
    rm_two = create_test_user(db_session, email="rm.two@example.test", role=UserRole.RM, name="RM Two")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        await create_report_fixture(client, rm_one_id=rm_one.id, rm_two_id=rm_two.id)
        response = await client.get(f"/api/v1/reports/{report_type}/preview?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_type"] == report_type
    assert payload["total"] == expected_total
    assert payload["limit"] == 1
    assert len(payload["items"]) == min(expected_total, 1)
    assert payload["columns"]
    if payload["items"]:
        assert list(payload["items"][0]) == [column["key"] for column in payload["columns"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("report_type", [report_type.value for report_type in ReportType])
@pytest.mark.parametrize("export_format", [export_format.value for export_format in ReportExportFormat])
async def test_every_report_type_exports_every_supported_format(
    report_type: str,
    export_format: str,
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email=f"admin-{report_type}-{export_format}@example.test", role=UserRole.ADMIN)
    rm_one = create_test_user(
        db_session,
        email=f"rm-one-{report_type}-{export_format}@example.test",
        role=UserRole.RM,
        name="RM One",
    )
    rm_two = create_test_user(
        db_session,
        email=f"rm-two-{report_type}-{export_format}@example.test",
        role=UserRole.RM,
        name="RM Two",
    )

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        await create_report_fixture(client, rm_one_id=rm_one.id, rm_two_id=rm_two.id)
        response = await client.get(f"/api/v1/reports/{report_type}/export?format={export_format}")

    assert response.status_code == 200
    assert response.headers["x-report-row-count"] == str(REPORT_EXPECTED_TOTALS[report_type])
    assert response.headers["content-disposition"].endswith(f'.{export_format}"')
    assert response.content

    if export_format == "csv":
        rows = csv_rows(response.content)
        assert len(rows) == REPORT_EXPECTED_TOTALS[report_type] + 1
        assert rows[0][0]
    elif export_format == "xlsx":
        sheet_xml = xlsx_sheet_xml(response.content)
        assert '<pane ySplit="1"' in sheet_xml
        assert "inlineStr" in sheet_xml
    else:
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-1.4")


@pytest.mark.asyncio
async def test_report_exports_mask_sensitive_values_in_preview_and_csv(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        family = await create_family(client, rm_id=rm.id, family_code="FAM-MASK")
        await create_member(
            client,
            family_id=family["id"],
            can_number="CAN-MASK",
            pan="ABCDE1234F",
            bank_account_number="001122334455",
            kyc_status="Registered",
            payeezz_status="Not Available",
        )
        preview = await client.get("/api/v1/reports/payeezz_pending/preview")
        csv_response = await client.get("/api/v1/reports/payeezz_pending/export?format=csv")

    assert preview.status_code == 200
    assert preview.json()["items"][0]["bank_account_number_masked"] == "bank account ending 4455"
    assert "001122334455" not in str(preview.json())

    assert csv_response.status_code == 200
    exported_text = csv_response.content.decode("utf-8-sig")
    assert "bank account ending 4455" in exported_text
    assert "001122334455" not in exported_text
    assert "ABCDE1234F" not in exported_text


@pytest.mark.asyncio
async def test_report_rm_scope_applies_to_preview_and_export(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm_one = create_test_user(db_session, email="rm.one@example.test", role=UserRole.RM, name="RM One")
    rm_two = create_test_user(db_session, email="rm.two@example.test", role=UserRole.RM, name="RM Two")

    async with client_for(test_settings) as admin_client:
        assert (await login(admin_client, admin.email)).status_code == 200
        await create_report_fixture(admin_client, rm_one_id=rm_one.id, rm_two_id=rm_two.id)

    async with client_for(test_settings) as rm_client:
        assert (await login(rm_client, rm_one.email)).status_code == 200
        preview = await rm_client.get("/api/v1/reports/full/preview")
        export = await rm_client.get("/api/v1/reports/full/export?format=csv")
        blocked_filter = await rm_client.get(f"/api/v1/reports/full/preview?rm_id={rm_one.id}")

    assert preview.status_code == 200
    assert preview.json()["total"] == 3
    assert {item["family_code"] for item in preview.json()["items"]} == {"FAM-ALPHA"}
    assert export.headers["x-report-row-count"] == "3"
    assert all(row[12] != "FAM-BETA" for row in csv_rows(export.content)[1:])
    assert blocked_filter.status_code == 403


@pytest.mark.asyncio
async def test_report_export_audit_records_successful_exports(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm_one = create_test_user(db_session, email="rm.one@example.test", role=UserRole.RM, name="RM One")
    rm_two = create_test_user(db_session, email="rm.two@example.test", role=UserRole.RM, name="RM Two")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        await create_report_fixture(client, rm_one_id=rm_one.id, rm_two_id=rm_two.id)
        response = await client.get(f"/api/v1/reports/full/export?format=csv&rm_id={rm_one.id}")

    assert response.status_code == 200
    db_session.expire_all()
    export = db_session.scalar(select(ReportExport))
    assert export is not None
    assert export.report_type == "full"
    assert export.format == "csv"
    assert export.row_count == 3
    assert export.exported_by_user_id == admin.id
    assert export.filters == {"rm_id": str(rm_one.id), "family_id": None}


@pytest.mark.asyncio
async def test_report_invalid_format_and_report_type_return_controlled_errors(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        invalid_format = await client.get("/api/v1/reports/full/export?format=json")
        invalid_type = await client.get("/api/v1/reports/unknown/preview")

    assert invalid_format.status_code == 422
    assert invalid_format.json()["error"]["code"] == "invalid_report_format"
    assert invalid_type.status_code == 404
    assert invalid_type.json()["error"]["code"] == "invalid_report_type"
    assert db_session.scalar(select(ReportExport)) is None


@pytest.mark.asyncio
async def test_report_csv_escapes_commas_quotes_and_newlines(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        family = await create_family(client, rm_id=rm.id, family_code="FAM-CSV")
        await create_member(
            client,
            family_id=family["id"],
            name='Client, "Quoted"\nLine',
            can_number="CAN-CSV",
        )
        response = await client.get("/api/v1/reports/full/export?format=csv")

    assert response.status_code == 200
    rows = csv_rows(response.content)
    assert rows[1][0] == 'Client, "Quoted"\nLine'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/reports/full/preview",
        "/api/v1/reports/full/export?format=csv",
        f"/api/v1/reports/{uuid4()}/preview",
    ],
)
async def test_report_endpoints_reject_anonymous_access(
    path: str,
    test_settings: Settings,
    db_engine,
) -> None:
    async with client_for(test_settings) as client:
        response = await client.get(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
