from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.domain.enums import AuditAction, AuditEntityType, UserRole
from app.main import create_app
from app.models.audit import AuditLog
from app.models.family import Family, Member, MemberBankAccount
from app.models.user import User

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


def member_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Client One",
        "can_number": "CAN-001",
        "pan": "ABCDE1234F",
        "date_of_birth": "1990-01-01",
        "kyc_status": "Verified",
        "mobile": "9876543210",
        "mobile_verification_status": "Verified",
        "email": "client.one@example.test",
        "email_verification_status": "Verified",
        "nominee_verification_status": "Verified",
        "remarks": "Initial record",
    }
    payload.update(overrides)
    return payload


def bank_account_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "bank_name": "HDFC Bank",
        "account_number": "001122334455",
        "ifsc_code": "HDFC0123456",
        "is_primary": True,
        "payeezz_mandate_status": "Approved",
        "payeezz_amount": "1000.00",
        "payeezz_start_date": "2026-01-01",
    }
    payload.update(overrides)
    return payload


async def create_family(
    client: httpx.AsyncClient,
    *,
    rm_id: UUID,
    family_code: str = "FAM-001",
    family_head_name: str = "Alpha Head",
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/families",
        json={
            "family_code": family_code,
            "family_head_name": family_head_name,
            "primary_rm_id": str(rm_id),
            "remarks": "Family remarks",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_member(
    client: httpx.AsyncClient,
    *,
    family_id: str,
    **overrides: object,
) -> dict[str, object]:
    bank_keys = {
        "bank_name",
        "bank_account_number",
        "account_number",
        "ifsc_code",
        "is_primary",
        "payeezz_mandate_status",
        "payeezz_amount",
        "payeezz_start_date",
    }
    member_overrides = {key: value for key, value in overrides.items() if key not in bank_keys}
    bank_overrides = {key: value for key, value in overrides.items() if key in bank_keys}
    response = await client.post(f"/api/v1/families/{family_id}/members", json=member_payload(**member_overrides))
    assert response.status_code == 201, response.text
    member = response.json()
    bank_payload = bank_account_payload(**bank_overrides)
    if "bank_account_number" in bank_overrides:
        bank_payload["account_number"] = bank_overrides["bank_account_number"]
    bank_response = await client.post(f"/api/v1/members/{member['id']}/bank-accounts", json=bank_payload)
    assert bank_response.status_code == 201, bank_response.text
    refreshed = await client.get(f"/api/v1/members/{member['id']}")
    assert refreshed.status_code == 200, refreshed.text
    return refreshed.json()


@pytest.mark.asyncio
async def test_admin_can_crud_family_and_member_with_masked_pii_and_audit(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    ops = create_test_user(db_session, email="ops@example.test", role=UserRole.OPS)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM, name="Relationship Manager")

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        family = await create_family(client, rm_id=rm.id)
        assert family["primary_rm"]["id"] == str(rm.id)
        assert family["total_members"] == 0

        member = await create_member(client, family_id=family["id"])
        assert member["pan_masked"] == "ABCDE****F"
        assert member["mobile_masked"] == "******3210"
        assert member["email_masked"] == "c*********@e******.test"
        assert member["primary_bank_account"]["account_number_masked"] == "bank account ending 4455"
        assert "pan" not in member
        assert "bank_account_number" not in member
        assert member["updated_by"]["id"] == str(admin.id)

    async with client_for(test_settings) as client:
        assert (await login(client, ops.email)).status_code == 200
        patch_response = await client.patch(
            f"/api/v1/members/{member['id']}",
            json={
                "pan": "XYZAB9876C",
                "mobile_verification_status": "Pending Verification",
                "remarks": "Updated by ops",
            },
            headers={"x-request-id": "req-member-update"},
        )

    assert patch_response.status_code == 200
    assert patch_response.json()["pan_masked"] == "XYZAB****C"
    assert patch_response.json()["updated_by"]["id"] == str(ops.id)
    assert "XYZAB9876C" not in str(patch_response.json())

    db_session.expire_all()
    stored_member = db_session.get(Member, UUID(member["id"]))
    assert stored_member is not None
    assert stored_member.pan_encrypted is not None
    assert "XYZAB9876C" not in stored_member.pan_encrypted
    assert stored_member.pan_search_hash is not None

    audit_rows = list(
        db_session.scalars(
            select(AuditLog)
            .where(AuditLog.entity_id == UUID(member["id"]))
            .order_by(AuditLog.action, AuditLog.field_name)
        )
    )
    assert {(row.action, row.field_name) for row in audit_rows} >= {
        (AuditAction.CREATE, None),
        (AuditAction.UPDATE, "mobile_verification_status"),
        (AuditAction.UPDATE, "pan"),
        (AuditAction.UPDATE, "remarks"),
    }
    pan_update = next(row for row in audit_rows if row.field_name == "pan")
    assert pan_update.old_value == "ABCDE****F"
    assert pan_update.new_value == "XYZAB****C"
    assert pan_update.request_id == "req-member-update"


@pytest.mark.asyncio
async def test_member_crud_includes_nominee_name(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        family = await create_family(client, rm_id=create_test_user(db_session, email="rm@example.test", role=UserRole.RM).id)
        created = await create_member(
            client,
            family_id=family["id"],
            nominee_name="Aarav Sharma",
            remarks="Has nominee",
        )

        updated = await client.patch(
            f"/api/v1/members/{created['id']}",
            json={"nominee_name": "Meera Sharma"},
        )

    assert created["nominee_name"] == "Aarav Sharma"
    assert updated.status_code == 200
    assert updated.json()["nominee_name"] == "Meera Sharma"


@pytest.mark.asyncio
async def test_management_cannot_write_and_rm_is_scoped_to_assigned_records(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    management = create_test_user(db_session, email="management@example.test", role=UserRole.MANAGEMENT)
    rm_one = create_test_user(db_session, email="rm.one@example.test", role=UserRole.RM, name="RM One")
    rm_two = create_test_user(db_session, email="rm.two@example.test", role=UserRole.RM, name="RM Two")

    async with client_for(test_settings) as admin_client:
        assert (await login(admin_client, admin.email)).status_code == 200
        family_one = await create_family(
            admin_client,
            rm_id=rm_one.id,
            family_code="FAM-RM-1",
            family_head_name="Assigned Head",
        )
        family_two = await create_family(
            admin_client,
            rm_id=rm_two.id,
            family_code="FAM-RM-2",
            family_head_name="Other Head",
        )
        member_one = await create_member(admin_client, family_id=family_one["id"], can_number="CAN-RM-1")
        member_two = await create_member(admin_client, family_id=family_two["id"], can_number="CAN-RM-2")

    async with client_for(test_settings) as management_client:
        assert (await login(management_client, management.email)).status_code == 200
        assert (await management_client.post("/api/v1/families", json={})).status_code == 403
        management_patch = await management_client.patch(
            f"/api/v1/members/{member_one['id']}",
            json={"remarks": "blocked"},
        )
        assert management_patch.status_code == 403
        assert (await management_client.delete(f"/api/v1/members/{member_one['id']}")).status_code == 403

    async with client_for(test_settings) as rm_client:
        assert (await login(rm_client, rm_one.email)).status_code == 200
        families_response = await rm_client.get("/api/v1/families")
        members_response = await rm_client.get("/api/v1/members")
        hidden_family_response = await rm_client.get(f"/api/v1/families/{family_two['id']}")
        hidden_member_response = await rm_client.get(f"/api/v1/members/{member_two['id']}")
        rm_member_patch = await rm_client.patch(f"/api/v1/members/{member_one['id']}", json={"remarks": "RM note"})
        rm_member_identity_patch = await rm_client.patch(
            f"/api/v1/members/{member_one['id']}",
            json={"can_number": "CAN-RM-CHANGED"},
        )
        rm_family_patch = await rm_client.patch(
            f"/api/v1/families/{family_one['id']}",
            json={"remarks": "RM family note"},
        )
        rm_reassign_attempt = await rm_client.patch(
            f"/api/v1/families/{family_one['id']}",
            json={"primary_rm_id": str(rm_two.id)},
        )

    assert [item["family_code"] for item in families_response.json()["items"]] == ["FAM-RM-1"]
    assert [item["can_number"] for item in members_response.json()["items"]] == ["CAN-RM-1"]
    assert hidden_family_response.status_code == 404
    assert hidden_member_response.status_code == 404
    assert rm_member_patch.status_code == 200
    assert rm_member_identity_patch.status_code == 403
    assert rm_family_patch.status_code == 200
    assert rm_reassign_attempt.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.OPS, UserRole.RM, UserRole.MANAGEMENT])
async def test_family_and_member_delete_are_admin_only(
    role: UserRole,
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    blocked_user = create_test_user(db_session, email=f"{role.value}@example.test", role=role)
    rm = blocked_user if role == UserRole.RM else create_test_user(db_session, email="rm@example.test", role=UserRole.RM)

    async with client_for(test_settings) as admin_client:
        assert (await login(admin_client, admin.email)).status_code == 200
        family = await create_family(
            admin_client,
            rm_id=rm.id,
            family_code=f"FAM-DELETE-{role.value.upper()}",
            family_head_name=f"{role.value.title()} Delete Head",
        )
        member = await create_member(
            admin_client,
            family_id=family["id"],
            can_number=f"CAN-DELETE-{role.value.upper()}",
        )

    async with client_for(test_settings) as blocked_client:
        assert (await login(blocked_client, blocked_user.email)).status_code == 200
        member_delete = await blocked_client.delete(f"/api/v1/members/{member['id']}")
        family_delete = await blocked_client.delete(f"/api/v1/families/{family['id']}")

    assert member_delete.status_code == 403
    assert member_delete.json()["error"]["code"] == "forbidden"
    assert family_delete.status_code == 403
    assert family_delete.json()["error"]["code"] == "forbidden"

    db_session.expire_all()
    stored_family = db_session.get(Family, UUID(family["id"]))
    stored_member = db_session.get(Member, UUID(member["id"]))
    assert stored_family is not None and stored_family.deleted_at is None
    assert stored_member is not None and stored_member.deleted_at is None


@pytest.mark.asyncio
async def test_validation_and_active_uniqueness_for_families_and_members(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM)
    ops = create_test_user(db_session, email="ops@example.test", role=UserRole.OPS)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        family = await create_family(client, rm_id=rm.id, family_code="FAM-UNIQUE")
        member = await create_member(client, family_id=family["id"], can_number="CAN-UNIQUE")

        duplicate_family = await client.post(
            "/api/v1/families",
            json={"family_code": "FAM-UNIQUE", "family_head_name": "Duplicate", "primary_rm_id": str(rm.id)},
        )
        duplicate_member = await client.post(
            f"/api/v1/families/{family['id']}/members",
            json=member_payload(can_number="CAN-UNIQUE", pan="ABCDE1234F"),
        )
        invalid_pan = await client.post(
            f"/api/v1/families/{family['id']}/members",
            json=member_payload(can_number="CAN-BAD-PAN", pan="bad-pan"),
        )
        invalid_ifsc = await client.post(
            f"/api/v1/members/{member['id']}/bank-accounts",
            json=bank_account_payload(account_number="99887766", ifsc_code="BAD", bank_name="Bad IFSC Bank"),
        )
        invalid_rm = await client.post(
            "/api/v1/families",
            json={"family_code": "FAM-BAD-RM", "family_head_name": "Bad RM", "primary_rm_id": str(ops.id)},
        )

        assert (await client.delete(f"/api/v1/members/{member['id']}")).status_code == 204
        reused_member = await client.post(
            f"/api/v1/families/{family['id']}/members",
            json=member_payload(can_number="CAN-UNIQUE", pan="XYZAB9876C"),
        )
        assert (await client.delete(f"/api/v1/families/{family['id']}")).status_code == 204
        reused_family = await client.post(
            "/api/v1/families",
            json={"family_code": "FAM-UNIQUE", "family_head_name": "Reused", "primary_rm_id": str(rm.id)},
        )

    assert duplicate_family.status_code == 409
    assert duplicate_family.json()["error"]["code"] == "family_code_already_exists"
    assert duplicate_member.status_code == 409
    assert duplicate_member.json()["error"]["code"] == "can_number_already_exists"
    assert invalid_pan.status_code == 422
    assert invalid_ifsc.status_code == 422
    assert invalid_rm.status_code == 422
    assert reused_member.status_code == 201
    assert reused_family.status_code == 201


@pytest.mark.asyncio
async def test_member_bank_accounts_enforce_duplicate_and_primary_rules(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        family = await create_family(client, rm_id=rm.id)
        member = await create_member(client, family_id=family["id"])
        primary = member["primary_bank_account"]

        duplicate = await client.post(
            f"/api/v1/members/{member['id']}/bank-accounts",
            json=bank_account_payload(bank_name="HDFC Bank", account_number="001122334455"),
        )
        second = await client.post(
            f"/api/v1/members/{member['id']}/bank-accounts",
            json=bank_account_payload(
                bank_name="ICICI Bank",
                account_number="9988776655",
                ifsc_code="ICIC0123456",
                is_primary=False,
                payeezz_mandate_status="Pending Approval",
            ),
        )
        clear_primary = await client.patch(
            f"/api/v1/members/{member['id']}/bank-accounts/{primary['id']}",
            json={"is_primary": False},
        )
        delete_primary = await client.delete(f"/api/v1/members/{member['id']}/bank-accounts/{primary['id']}")
        promote_second = await client.patch(
            f"/api/v1/members/{member['id']}/bank-accounts/{second.json()['id']}",
            json={"is_primary": True},
        )
        refreshed = await client.get(f"/api/v1/members/{member['id']}")

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "bank_account_already_exists"
    assert second.status_code == 201, second.text
    assert clear_primary.status_code == 422
    assert delete_primary.status_code == 422
    assert promote_second.status_code == 200, promote_second.text
    body = refreshed.json()
    assert body["primary_bank_account"]["bank_name"] == "ICICI Bank"
    assert sum(account["is_primary"] for account in body["bank_accounts"]) == 1


@pytest.mark.asyncio
async def test_family_create_generates_date_stamped_code_and_does_not_reuse_soft_deleted_codes(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        first = await client.post(
            "/api/v1/families",
            json={"family_head_name": "Generated One", "primary_rm_id": str(rm.id)},
        )
        second = await client.post(
            "/api/v1/families",
            json={"family_head_name": "Generated Two", "primary_rm_id": str(rm.id)},
        )
        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["family_code"].startswith("FAM-")
        assert first.json()["family_code"].endswith("-0001")
        assert second.json()["family_code"].endswith("-0002")

        assert (await client.delete(f"/api/v1/families/{first.json()['id']}")).status_code == 204
        third = await client.post(
            "/api/v1/families",
            json={"family_head_name": "Generated Three", "primary_rm_id": str(rm.id)},
        )

    assert third.status_code == 201, third.text
    assert third.json()["family_code"].endswith("-0003")


@pytest.mark.asyncio
async def test_family_can_be_created_assigned_and_cleared_without_rm(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        create_response = await client.post(
            "/api/v1/families",
            json={"family_head_name": "Unassigned Head", "remarks": "Needs RM"},
        )
        family = create_response.json()
        member = await create_member(client, family_id=family["id"], can_number="CAN-UNASSIGNED")
        assign_response = await client.patch(f"/api/v1/families/{family['id']}", json={"primary_rm_id": str(rm.id)})
        clear_response = await client.patch(f"/api/v1/families/{family['id']}", json={"primary_rm_id": None})
        detail_response = await client.get(f"/api/v1/families/{family['id']}")

    assert create_response.status_code == 201, create_response.text
    assert family["primary_rm"] is None
    assert member.get("primary_rm") is None
    assert assign_response.status_code == 200, assign_response.text
    assert assign_response.json()["primary_rm"]["id"] == str(rm.id)
    assert clear_response.status_code == 200, clear_response.text
    assert clear_response.json()["primary_rm"] is None
    assert detail_response.json()["primary_rm"] is None

    async with client_for(test_settings) as rm_client:
        assert (await login(rm_client, rm.email)).status_code == 200
        family_list = await rm_client.get("/api/v1/families")
        family_detail = await rm_client.get(f"/api/v1/families/{family['id']}")
        member_list = await rm_client.get("/api/v1/members")

    assert family_list.status_code == 200
    assert family_list.json()["total"] == 0
    assert family_detail.status_code == 404
    assert member_list.json()["total"] == 0


@pytest.mark.asyncio
async def test_members_can_be_pending_without_can_and_later_assigned(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        family = await create_family(client, rm_id=rm.id, family_code="FAM-PENDING-CAN")
        first_pending = await create_member(
            client,
            family_id=family["id"],
            name="Pending One",
            can_number=None,
            pan="ABCDE1234F",
        )
        second_pending = await create_member(
            client,
            family_id=family["id"],
            name="Pending Two",
            can_number="",
            pan="XYZAB9876C",
        )
        inconsistent_can_status = await client.patch(
            f"/api/v1/members/{first_pending['id']}",
            json={"can_number": None, "can_status": "Available"},
        )
        assigned = await client.patch(
            f"/api/v1/members/{first_pending['id']}",
            json={"can_number": "CAN-ASSIGNED"},
        )
        available_members = await client.get("/api/v1/members?can_status=Available")
        cleared = await client.patch(
            f"/api/v1/members/{first_pending['id']}",
            json={"can_number": None},
        )
        pending_members = await client.get("/api/v1/members?can_status=Pending")

    assert first_pending.get("can_number") is None
    assert first_pending["can_status"] == "Pending"
    assert second_pending.get("can_number") is None
    assert second_pending["can_status"] == "Pending"
    assert inconsistent_can_status.status_code == 422
    assert assigned.status_code == 200
    assert assigned.json()["can_number"] == "CAN-ASSIGNED"
    assert assigned.json()["can_status"] == "Available"
    assert [item["can_number"] for item in available_members.json()["items"]] == ["CAN-ASSIGNED"]
    assert cleared.status_code == 200
    assert cleared.json().get("can_number") is None
    assert cleared.json()["can_status"] == "Pending"
    assert {item["name"] for item in pending_members.json()["items"]} == {"Pending One", "Pending Two"}


@pytest.mark.asyncio
async def test_search_and_filters_cover_family_member_rm_and_status_fields(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm_one = create_test_user(db_session, email="rm.one@example.test", role=UserRole.RM)
    rm_two = create_test_user(db_session, email="rm.two@example.test", role=UserRole.RM)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        alpha = await create_family(client, rm_id=rm_one.id, family_code="FAM-ALPHA", family_head_name="Alpha Head")
        beta = await create_family(client, rm_id=rm_two.id, family_code="FAM-BETA", family_head_name="Beta Head")
        await create_member(
            client,
            family_id=alpha["id"],
            name="Alice Alpha",
            can_number="CAN-ALPHA",
            nominee_name="Nominee One",
            pan="ABCDE1234F",
            kyc_status="Not Started",
            mobile_verification_status="Pending Verification",
            email_verification_status="Verified",
            nominee_verification_status="Pending Verification",
            payeezz_mandate_status="Not Started",
        )
        await create_member(
            client,
            family_id=beta["id"],
            name="Bob Beta",
            can_number="CAN-BETA",
            pan="XYZAB9876C",
            kyc_status="Verified",
            mobile_verification_status="Verified",
            email_verification_status="Verified",
            nominee_verification_status="Verified",
            payeezz_mandate_status="Approved",
        )

        family_by_member = await client.get("/api/v1/families?q=Alice")
        family_by_can = await client.get("/api/v1/families?q=CAN-BETA")
        family_by_pan = await client.get("/api/v1/families?q=ABCDE1234F")
        family_kyc_pending = await client.get("/api/v1/families?status_filter=kyc_pending")
        family_can_available = await client.get("/api/v1/families?status_filter=can_available")
        family_nominee_pending = await client.get("/api/v1/families?status_filter=nominee_pending")
        family_payeezz_done = await client.get("/api/v1/families?payeezz_mandate_status=Approved")
        family_rm = await client.get(f"/api/v1/families?rm_id={rm_two.id}")

        await create_member(
            client,
            family_id=alpha["id"],
            name="Alice Pending CAN",
            can_number=None,
            pan="LMNOP1234Q",
        )
        family_can_pending = await client.get("/api/v1/families?status_filter=can_pending")

        member_by_family = await client.get(f"/api/v1/members?family_id={alpha['id']}")
        member_by_search_pan = await client.get("/api/v1/members?q=XYZAB9876C")
        member_by_nominee = await client.get("/api/v1/members?q=Nominee One")
        member_mobile_pending = await client.get("/api/v1/members?mobile_verification_status=Pending%20Verification")
        member_rm = await client.get(f"/api/v1/members?rm_id={rm_two.id}")

    assert [item["family_code"] for item in family_by_member.json()["items"]] == ["FAM-ALPHA"]
    assert [item["family_code"] for item in family_by_can.json()["items"]] == ["FAM-BETA"]
    assert [item["family_code"] for item in family_by_pan.json()["items"]] == ["FAM-ALPHA"]
    assert [item["family_code"] for item in family_kyc_pending.json()["items"]] == ["FAM-ALPHA"]
    assert [item["family_code"] for item in family_can_available.json()["items"]] == ["FAM-ALPHA", "FAM-BETA"]
    assert [item["family_code"] for item in family_can_pending.json()["items"]] == ["FAM-ALPHA"]
    assert family_can_pending.json()["items"][0]["can_pending"]["count"] == 1
    assert family_can_pending.json()["items"][0]["can_pending_pct"] == 50
    assert [item["family_code"] for item in family_nominee_pending.json()["items"]] == ["FAM-ALPHA"]
    assert [item["family_code"] for item in family_payeezz_done.json()["items"]] == ["FAM-BETA"]
    assert [item["family_code"] for item in family_rm.json()["items"]] == ["FAM-BETA"]
    assert [item.get("can_number") for item in member_by_family.json()["items"]] == ["CAN-ALPHA", None]
    assert [item["can_number"] for item in member_by_search_pan.json()["items"]] == ["CAN-BETA"]
    assert [item["can_number"] for item in member_by_nominee.json()["items"]] == ["CAN-ALPHA"]
    assert [item["can_number"] for item in member_mobile_pending.json()["items"]] == ["CAN-ALPHA"]
    assert [item["can_number"] for item in member_rm.json()["items"]] == ["CAN-BETA"]


@pytest.mark.asyncio
async def test_role_based_sensitive_access_reveals_allowed_fields_and_audits(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    ops = create_test_user(db_session, email="ops@example.test", role=UserRole.OPS)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM)
    management = create_test_user(db_session, email="management@example.test", role=UserRole.MANAGEMENT)

    async with client_for(test_settings) as admin_client:
        assert (await login(admin_client, admin.email)).status_code == 200
        family = await create_family(admin_client, rm_id=rm.id)
        member = await create_member(admin_client, family_id=family["id"])
        default_response = await admin_client.get(f"/api/v1/members/{member['id']}")
        sensitive_response = await admin_client.get(
            f"/api/v1/members/{member['id']}?include_sensitive=true",
            headers={"x-request-id": "req-sensitive"},
        )
        settings_response = await admin_client.get("/api/v1/admin/can-sensitive-access")
        update_settings_response = await admin_client.patch(
            "/api/v1/admin/can-sensitive-access",
            json={
                "can_ops": {"pan": True, "mobile": True, "email": False, "bank_account_number": False},
                "can_rm": {"pan": False, "mobile": True, "email": False, "bank_account_number": True},
            },
        )

    async with client_for(test_settings) as ops_client:
        assert (await login(ops_client, ops.email)).status_code == 200
        ops_sensitive_response = await ops_client.get(
            f"/api/v1/members/{member['id']}?include_sensitive=true",
            headers={"x-request-id": "req-sensitive-ops"},
        )

    async with client_for(test_settings) as rm_client:
        assert (await login(rm_client, rm.email)).status_code == 200
        rm_sensitive_response = await rm_client.get(
            f"/api/v1/members/{member['id']}?include_sensitive=true",
            headers={"x-request-id": "req-sensitive-rm"},
        )

    async with client_for(test_settings) as management_client:
        assert (await login(management_client, management.email)).status_code == 200
        management_response = await management_client.get(f"/api/v1/members/{member['id']}?include_sensitive=true")

    default_body = default_response.json()
    sensitive_body = sensitive_response.json()
    assert "pan" not in default_body
    assert sensitive_body["pan"] == "ABCDE1234F"
    assert sensitive_body["mobile"] == "9876543210"
    assert sensitive_body["email"] == "client.one@example.test"
    assert sensitive_body["primary_bank_account"]["account_number"] == "001122334455"
    assert settings_response.status_code == 200
    assert settings_response.json()["can_ops"] == {
        "pan": True,
        "mobile": True,
        "email": True,
        "bank_account_number": True,
    }
    assert settings_response.json()["can_rm"] == {
        "pan": False,
        "mobile": False,
        "email": False,
        "bank_account_number": False,
    }
    assert update_settings_response.status_code == 200
    assert ops_sensitive_response.status_code == 200
    assert ops_sensitive_response.json()["pan"] == "ABCDE1234F"
    assert ops_sensitive_response.json()["mobile"] == "9876543210"
    assert "email" not in ops_sensitive_response.json()
    assert "account_number" not in ops_sensitive_response.json()["primary_bank_account"]
    assert rm_sensitive_response.status_code == 200
    assert "pan" not in rm_sensitive_response.json()
    assert rm_sensitive_response.json()["mobile"] == "9876543210"
    assert rm_sensitive_response.json()["primary_bank_account"]["account_number"] == "001122334455"
    assert management_response.status_code == 403

    db_session.expire_all()
    sensitive_logs = list(
        db_session.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_id == UUID(member["id"]),
                AuditLog.action == AuditAction.SENSITIVE_READ,
            )
            .order_by(AuditLog.field_name)
        )
    )
    assert [log.field_name for log in sensitive_logs] == [
        "bank_account_number",
        "bank_account_number",
        "email",
        "mobile",
        "mobile",
        "mobile",
        "pan",
        "pan",
    ]
    assert {log.actor_user_id for log in sensitive_logs} == {admin.id, ops.id, rm.id}
    assert {log.request_id for log in sensitive_logs} == {"req-sensitive", "req-sensitive-ops", "req-sensitive-rm"}


@pytest.mark.asyncio
async def test_soft_deletes_exclude_family_and_member_records(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        family = await create_family(client, rm_id=rm.id, family_code="FAM-SOFT")
        member = await create_member(client, family_id=family["id"], can_number="CAN-SOFT")

        member_delete = await client.delete(
            f"/api/v1/members/{member['id']}",
            headers={"x-request-id": "req-delete-m"},
        )
        member_list = await client.get("/api/v1/members")
        member_detail = await client.get(f"/api/v1/members/{member['id']}")

        replacement_member = await create_member(client, family_id=family["id"], can_number="CAN-SOFT")
        family_delete = await client.delete(
            f"/api/v1/families/{family['id']}",
            headers={"x-request-id": "req-delete-f"},
        )
        family_list = await client.get("/api/v1/families")
        member_after_family_delete = await client.get(f"/api/v1/members/{replacement_member['id']}")

    assert member_delete.status_code == 204
    assert member_list.json()["total"] == 0
    assert member_detail.status_code == 404
    assert family_delete.status_code == 204
    assert family_list.json()["total"] == 0
    assert member_after_family_delete.status_code == 404

    db_session.expire_all()
    deleted_family = db_session.get(Family, UUID(family["id"]))
    deleted_member = db_session.get(Member, UUID(replacement_member["id"]))
    assert deleted_family is not None and deleted_family.deleted_at is not None
    assert deleted_member is not None and deleted_member.deleted_at is not None
    delete_logs = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == AuditAction.DELETE,
                AuditLog.entity_type.in_([AuditEntityType.FAMILY, AuditEntityType.MEMBER]),
            )
        )
    )
    assert delete_logs


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("GET", "/api/v1/families", None),
        ("POST", "/api/v1/families", {"family_code": "FAM", "family_head_name": "Head", "primary_rm_id": str(uuid4())}),
        ("GET", f"/api/v1/families/{uuid4()}", None),
        ("PATCH", f"/api/v1/families/{uuid4()}", {"remarks": "No auth"}),
        ("DELETE", f"/api/v1/families/{uuid4()}", None),
        ("GET", f"/api/v1/families/{uuid4()}/members", None),
        ("POST", f"/api/v1/families/{uuid4()}/members", member_payload()),
        ("GET", "/api/v1/members", None),
        ("GET", f"/api/v1/members/{uuid4()}", None),
        ("PATCH", f"/api/v1/members/{uuid4()}", {"remarks": "No auth"}),
        ("DELETE", f"/api/v1/members/{uuid4()}", None),
    ],
)
async def test_family_member_endpoints_reject_anonymous_access(
    method: str,
    path: str,
    json_body: dict[str, object] | None,
    test_settings: Settings,
    db_engine,
) -> None:
    async with client_for(test_settings) as client:
        response = await client.request(method, path, json=json_body)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
