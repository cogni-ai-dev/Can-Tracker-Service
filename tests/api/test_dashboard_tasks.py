from uuid import uuid4

import httpx
import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import UserRole
from tests.api.test_family_member_crud import (
    client_for,
    create_family,
    create_member,
    create_test_user,
    login,
)


async def create_mixed_dashboard_fixture(
    client: httpx.AsyncClient,
    *,
    rm_one_id,
    rm_two_id,
) -> tuple[dict[str, object], dict[str, object]]:
    alpha = await create_family(
        client,
        rm_id=rm_one_id,
        family_code="FAM-ALPHA",
        family_head_name="Alpha Head",
    )
    beta = await create_family(
        client,
        rm_id=rm_two_id,
        family_code="FAM-BETA",
        family_head_name="Beta Head",
    )
    await create_member(
        client,
        family_id=alpha["id"],
        name="Alpha A Complete",
        can_number="CAN-A1",
        pan="ABCDE1234F",
    )
    await create_member(
        client,
        family_id=alpha["id"],
        name="Alpha B Registered",
        can_number="CAN-A2",
        pan="BCDEF2345G",
        kyc_status="Registered",
        mobile_status="Not Verified",
        email_status="Verified",
        nominee_status="Not Verified",
        payeezz_status="Sent for Approval",
    )
    await create_member(
        client,
        family_id=alpha["id"],
        name="Alpha C No Kyc",
        can_number="CAN-A3",
        pan="CDEFG3456H",
        kyc_status="No KYC",
        mobile_status="Not Verified",
        email_status="Not Verified",
        nominee_status="Not Verified",
        payeezz_status="Not Available",
    )
    await create_member(
        client,
        family_id=beta["id"],
        name="Beta A Complete",
        can_number="CAN-B1",
        pan="DEFGH4567I",
    )
    return alpha, beta


@pytest.mark.asyncio
async def test_dashboard_summary_and_family_summary_match_canonical_html_style_counts(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm_one = create_test_user(db_session, email="rm.one@example.test", role=UserRole.RM, name="RM One")
    rm_two = create_test_user(db_session, email="rm.two@example.test", role=UserRole.RM, name="RM Two")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        alpha, _beta = await create_mixed_dashboard_fixture(client, rm_one_id=rm_one.id, rm_two_id=rm_two.id)

        summary_response = await client.get("/api/v1/dashboard/summary")
        rm_summary_response = await client.get(f"/api/v1/dashboard/summary?rm_id={rm_one.id}")
        family_response = await client.get(f"/api/v1/dashboard/families/{alpha['id']}")

    summary = summary_response.json()
    assert summary_response.status_code == 200
    assert summary["total_clients"] == 4
    assert summary["total_families"] == 2
    assert summary["kyc_validated"] == 2
    assert summary["kyc_registered"] == 1
    assert summary["kyc_no_kyc"] == 1
    assert summary["kyc_pending"] == 2
    assert summary["kyc_validated_pct"] == 50
    assert summary["kyc_pending_pct"] == 50
    assert summary["payeezz_accepted"] == 2
    assert summary["payeezz_sent_for_approval"] == 1
    assert summary["payeezz_not_available"] == 1
    assert summary["payeezz_pending"] == 2
    assert summary["payeezz_accepted_pct"] == 50
    assert summary["payeezz_pending_pct"] == 50
    assert summary["mobile_verified"] == 2
    assert summary["mobile_not_verified"] == 2
    assert summary["email_verified"] == 3
    assert summary["email_not_verified"] == 1
    assert summary["nominee_verified"] == 2
    assert summary["nominee_not_verified"] == 2
    assert summary["updated_at"] is not None

    rm_summary = rm_summary_response.json()
    assert rm_summary["total_clients"] == 3
    assert rm_summary["total_families"] == 1
    assert rm_summary["kyc_validated"] == 1
    assert rm_summary["kyc_pending"] == 2
    assert rm_summary["payeezz_pending"] == 2

    family = family_response.json()
    assert family_response.status_code == 200
    assert family["family_code"] == "FAM-ALPHA"
    assert family["number_of_members"] == 3
    assert family["total_cans"] == 3
    assert family["kyc_completion_pct"] == 33
    assert family["payeezz_completion_pct"] == 33
    assert family["mobile_verification_pct"] == 33
    assert family["email_verification_pct"] == 67
    assert family["nominee_verification_pct"] == 33
    assert [member["can_number"] for member in family["members"]] == ["CAN-A1", "CAN-A2", "CAN-A3"]
    assert all("pan" not in member for member in family["members"])


@pytest.mark.asyncio
async def test_task_list_summary_filters_and_pagination_are_deterministic(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm_one = create_test_user(db_session, email="rm.one@example.test", role=UserRole.RM, name="RM One")
    rm_two = create_test_user(db_session, email="rm.two@example.test", role=UserRole.RM, name="RM Two")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        alpha, beta = await create_mixed_dashboard_fixture(client, rm_one_id=rm_one.id, rm_two_id=rm_two.id)

        first_page = await client.get("/api/v1/tasks?limit=4")
        second_page = await client.get("/api/v1/tasks?limit=5&offset=4")
        task_summary = await client.get("/api/v1/tasks/summary")
        email_tasks = await client.get("/api/v1/tasks?type=email")
        high_tasks = await client.get("/api/v1/tasks?priority=high")
        alpha_tasks = await client.get(f"/api/v1/tasks?family_id={alpha['id']}")
        beta_tasks = await client.get(f"/api/v1/tasks?family_id={beta['id']}")
        searched_tasks = await client.get("/api/v1/tasks?q=CAN-A2")
        rm_two_tasks = await client.get(f"/api/v1/tasks?rm_id={rm_two.id}")
        high_summary = await client.get("/api/v1/tasks/summary?priority=high")

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 9
    assert first_page.json()["limit"] == 4
    assert [item["member_name"] for item in first_page.json()["items"]] == [
        "Alpha B Registered",
        "Alpha B Registered",
        "Alpha B Registered",
        "Alpha B Registered",
    ]
    assert [item["type"] for item in first_page.json()["items"]] == ["kyc", "payeezz", "mobile", "nominee"]
    assert [item["priority"] for item in first_page.json()["items"]] == ["medium", "medium", "medium", "medium"]
    assert [item["label"] for item in first_page.json()["items"]] == [
        "Re-KYC",
        "Pending",
        "Unverified",
        "Not Verified",
    ]

    assert second_page.json()["total"] == 9
    assert [item["member_name"] for item in second_page.json()["items"]] == ["Alpha C No Kyc"] * 5
    assert [item["type"] for item in second_page.json()["items"]] == [
        "kyc",
        "payeezz",
        "mobile",
        "email",
        "nominee",
    ]

    assert task_summary.json() == {
        "total_tasks": 9,
        "kyc": 2,
        "payeezz": 2,
        "mobile": 2,
        "email": 1,
        "nominee": 2,
    }
    assert email_tasks.json()["total"] == 1
    assert email_tasks.json()["items"][0]["can_number_masked"] == "CAN-A3"
    assert high_tasks.json()["total"] == 2
    assert [item["type"] for item in high_tasks.json()["items"]] == ["kyc", "payeezz"]
    assert alpha_tasks.json()["total"] == 9
    assert beta_tasks.json()["total"] == 0
    assert searched_tasks.json()["total"] == 4
    assert {item["member_name"] for item in searched_tasks.json()["items"]} == {"Alpha B Registered"}
    assert rm_two_tasks.json()["total"] == 0
    assert high_summary.json() == {
        "total_tasks": 2,
        "kyc": 1,
        "payeezz": 1,
        "mobile": 0,
        "email": 0,
        "nominee": 0,
    }


@pytest.mark.asyncio
async def test_empty_dashboard_tasks_and_zero_member_family_return_zeroes(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="RM")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        empty_summary = await client.get("/api/v1/dashboard/summary")
        empty_tasks = await client.get("/api/v1/tasks")
        empty_task_summary = await client.get("/api/v1/tasks/summary")
        family = await create_family(client, rm_id=rm.id, family_code="FAM-EMPTY", family_head_name="Empty Head")
        family_summary = await client.get(f"/api/v1/dashboard/families/{family['id']}")

    assert empty_summary.json() == {
        "total_clients": 0,
        "total_families": 0,
        "kyc_validated": 0,
        "kyc_registered": 0,
        "kyc_no_kyc": 0,
        "kyc_pending": 0,
        "kyc_validated_pct": 0,
        "kyc_pending_pct": 0,
        "payeezz_accepted": 0,
        "payeezz_sent_for_approval": 0,
        "payeezz_not_available": 0,
        "payeezz_pending": 0,
        "payeezz_accepted_pct": 0,
        "payeezz_pending_pct": 0,
        "mobile_verified": 0,
        "mobile_not_verified": 0,
        "email_verified": 0,
        "email_not_verified": 0,
        "nominee_verified": 0,
        "nominee_not_verified": 0,
        "updated_at": None,
    }
    assert empty_tasks.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}
    assert empty_task_summary.json() == {
        "total_tasks": 0,
        "kyc": 0,
        "payeezz": 0,
        "mobile": 0,
        "email": 0,
        "nominee": 0,
    }
    assert family_summary.json()["number_of_members"] == 0
    assert family_summary.json()["total_cans"] == 0
    assert family_summary.json()["kyc_completion_pct"] == 0
    assert family_summary.json()["payeezz_completion_pct"] == 0
    assert family_summary.json()["mobile_verification_pct"] == 0
    assert family_summary.json()["email_verification_pct"] == 0
    assert family_summary.json()["nominee_verification_pct"] == 0
    assert family_summary.json()["members"] == []


@pytest.mark.asyncio
async def test_dashboard_and_tasks_enforce_rm_scoping_and_management_read_access(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    management = create_test_user(db_session, email="management@example.test", role=UserRole.MANAGEMENT)
    rm_one = create_test_user(db_session, email="rm.one@example.test", role=UserRole.RM, name="RM One")
    rm_two = create_test_user(db_session, email="rm.two@example.test", role=UserRole.RM, name="RM Two")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        _alpha, beta = await create_mixed_dashboard_fixture(client, rm_one_id=rm_one.id, rm_two_id=rm_two.id)

    async with client_for(test_settings) as management_client:
        assert (await login(management_client, management.email)).status_code == 200
        assert (await management_client.get("/api/v1/dashboard/summary")).status_code == 200
        assert (await management_client.get("/api/v1/tasks")).status_code == 200
        assert (await management_client.get(f"/api/v1/dashboard/summary?rm_id={rm_one.id}")).status_code == 200

    async with client_for(test_settings) as rm_client:
        assert (await login(rm_client, rm_one.email)).status_code == 200
        rm_summary = await rm_client.get("/api/v1/dashboard/summary")
        rm_tasks = await rm_client.get("/api/v1/tasks")
        rm_task_summary = await rm_client.get("/api/v1/tasks/summary")
        hidden_family = await rm_client.get(f"/api/v1/dashboard/families/{beta['id']}")
        blocked_dashboard_filter = await rm_client.get(f"/api/v1/dashboard/summary?rm_id={rm_one.id}")
        blocked_task_filter = await rm_client.get(f"/api/v1/tasks?rm_id={rm_one.id}")

    assert rm_summary.json()["total_clients"] == 3
    assert rm_summary.json()["total_families"] == 1
    assert rm_tasks.json()["total"] == 9
    assert rm_task_summary.json()["total_tasks"] == 9
    assert hidden_family.status_code == 404
    assert blocked_dashboard_filter.status_code == 403
    assert blocked_task_filter.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/dashboard/summary",
        f"/api/v1/dashboard/families/{uuid4()}",
        "/api/v1/tasks",
        "/api/v1/tasks/summary",
    ],
)
async def test_dashboard_and_task_endpoints_reject_anonymous_access(
    path: str,
    test_settings: Settings,
    db_engine,
) -> None:
    async with client_for(test_settings) as client:
        response = await client.get(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
