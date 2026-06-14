from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import user_can_update_family, user_can_view_family
from app.core.config import Settings
from app.core.security import hash_password
from app.domain.enums import UserRole
from app.main import create_app
from app.models.user import User, UserSession

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
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


@pytest.mark.asyncio
async def test_login_succeeds_for_active_user_and_me_returns_safe_user(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)

    async with client_for(test_settings) as client:
        response = await login(client, "ADMIN@EXAMPLE.TEST")
        assert response.status_code == 200
        body = response.json()
        assert body["user"]["email"] == "admin@example.test"
        assert body["user"]["role"] == "admin"
        assert "password_hash" not in body["user"]
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "samesite=lax" in response.headers["set-cookie"].lower()

        me_response = await client.get("/api/v1/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "admin@example.test"
    assert "password_hash" not in me_response.json()


@pytest.mark.asyncio
async def test_login_fails_with_wrong_password(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)

    async with client_for(test_settings) as client:
        response = await login(client, "admin@example.test", "wrong-password")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_login_fails_for_inactive_user(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    create_test_user(db_session, email="inactive@example.test", role=UserRole.ADMIN, is_active=False)

    async with client_for(test_settings) as client:
        response = await login(client, "inactive@example.test")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookie(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)

    async with client_for(test_settings) as client:
        assert (await login(client, "admin@example.test")).status_code == 200
        assert (await client.get("/api/v1/auth/me")).status_code == 200

        logout_response = await client.post("/api/v1/auth/logout")
        me_response = await client.get("/api/v1/auth/me")

    assert logout_response.status_code == 204
    assert "max-age=0" in logout_response.headers["set-cookie"].lower()
    assert me_response.status_code == 401
    assert db_session.scalar(select(UserSession)).revoked_at is not None


@pytest.mark.asyncio
async def test_password_change_revokes_existing_user_sessions(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    ops = create_test_user(db_session, email="ops@example.test", role=UserRole.OPS)

    async with client_for(test_settings) as ops_client, client_for(test_settings) as admin_client:
        assert (await login(ops_client, ops.email)).status_code == 200
        assert (await ops_client.get("/api/v1/auth/me")).status_code == 200
        assert (await login(admin_client, admin.email)).status_code == 200

        patch_response = await admin_client.patch(
            f"/api/v1/users/{ops.id}",
            json={"password": "new-password123"},
        )
        stale_session_response = await ops_client.get("/api/v1/auth/me")

    assert patch_response.status_code == 200
    assert stale_session_response.status_code == 401
    assert db_session.scalar(select(UserSession).where(UserSession.user_id == ops.id)).revoked_at is not None


@pytest.mark.asyncio
async def test_deactivation_revokes_existing_sessions_even_if_user_is_reactivated(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    ops = create_test_user(db_session, email="ops@example.test", role=UserRole.OPS)

    async with client_for(test_settings) as ops_client, client_for(test_settings) as admin_client:
        assert (await login(ops_client, ops.email)).status_code == 200
        assert (await login(admin_client, admin.email)).status_code == 200

        deactivate_response = await admin_client.delete(f"/api/v1/users/{ops.id}")
        deactivated_session_response = await ops_client.get("/api/v1/auth/me")
        reactivate_response = await admin_client.patch(f"/api/v1/users/{ops.id}", json={"is_active": True})
        reactivated_stale_session_response = await ops_client.get("/api/v1/auth/me")

    assert deactivate_response.status_code == 204
    assert deactivated_session_response.status_code == 401
    assert reactivate_response.status_code == 200
    assert reactivated_stale_session_response.status_code == 401
    assert db_session.scalar(select(UserSession).where(UserSession.user_id == ops.id)).revoked_at is not None


@pytest.mark.asyncio
async def test_inactive_user_cannot_continue_using_existing_session(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    user = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)

    async with client_for(test_settings) as client:
        assert (await login(client, "admin@example.test")).status_code == 200
        user.is_active = False
        db_session.commit()

        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "inactive_user"


@pytest.mark.asyncio
async def test_admin_can_create_update_list_and_deactivate_users(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)

    async with client_for(test_settings) as client:
        assert (await login(client, "admin@example.test")).status_code == 200

        create_response = await client.post(
            "/api/v1/users",
            json={
                "name": "Ops User",
                "email": "OPS@EXAMPLE.TEST",
                "password": PASSWORD,
                "role": "ops",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["email"] == "ops@example.test"
        assert "password_hash" not in created

        list_response = await client.get("/api/v1/users")
        assert list_response.status_code == 200
        assert {user["email"] for user in list_response.json()} == {"admin@example.test", "ops@example.test"}

        patch_response = await client.patch(
            f"/api/v1/users/{created['id']}",
            json={"name": "Renamed Ops", "role": "management"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["name"] == "Renamed Ops"
        assert patch_response.json()["role"] == "management"

        delete_response = await client.delete(f"/api/v1/users/{created['id']}")
        get_response = await client.get(f"/api/v1/users/{created['id']}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.OPS, UserRole.RM, UserRole.MANAGEMENT])
async def test_non_admin_roles_cannot_manage_users(
    role: UserRole,
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    create_test_user(db_session, email=f"{role.value}@example.test", role=role)
    target = create_test_user(db_session, email=f"target.{role.value}@example.test", role=UserRole.OPS)

    async with client_for(test_settings) as client:
        assert (await login(client, f"{role.value}@example.test")).status_code == 200
        responses = [
            await client.get("/api/v1/users"),
            await client.get(f"/api/v1/users/{target.id}"),
            await client.patch(f"/api/v1/users/{target.id}", json={"name": "Blocked Update"}),
            await client.delete(f"/api/v1/users/{target.id}"),
            await client.post(
                "/api/v1/users",
                json={
                    "name": "Blocked User",
                    "email": "blocked@example.test",
                    "password": PASSWORD,
                    "role": "ops",
                },
            ),
        ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403, 403]


@pytest.mark.asyncio
async def test_management_cannot_write_user_records(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    create_test_user(db_session, email="management@example.test", role=UserRole.MANAGEMENT)
    target = create_test_user(db_session, email="target@example.test", role=UserRole.OPS)

    async with client_for(test_settings) as client:
        assert (await login(client, "management@example.test")).status_code == 200
        patch_response = await client.patch(f"/api/v1/users/{target.id}", json={"name": "Blocked Update"})
        delete_response = await client.delete(f"/api/v1/users/{target.id}")
        create_response = await client.post(
            "/api/v1/users",
            json={
                "name": "Blocked User",
                "email": "blocked@example.test",
                "password": PASSWORD,
                "role": "ops",
            },
        )

    assert patch_response.status_code == 403
    assert delete_response.status_code == 403
    assert create_response.status_code == 403


@pytest.mark.asyncio
async def test_rms_lists_only_active_rm_users_for_allowed_roles(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    create_test_user(db_session, email="management@example.test", role=UserRole.MANAGEMENT)
    create_test_user(db_session, email="active.rm@example.test", role=UserRole.RM, name="Active RM")
    create_test_user(db_session, email="inactive.rm@example.test", role=UserRole.RM, is_active=False)
    create_test_user(db_session, email="ops@example.test", role=UserRole.OPS)

    async with client_for(test_settings) as client:
        assert (await login(client, "management@example.test")).status_code == 200
        response = await client.get("/api/v1/rms")

    assert response.status_code == 200
    assert [(user["name"], user["email"], user["role"]) for user in response.json()] == [
        ("Active RM", "active.rm@example.test", "rm")
    ]


@pytest.mark.asyncio
async def test_rm_cannot_access_rm_listing(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    create_test_user(db_session, email="rm@example.test", role=UserRole.RM)

    async with client_for(test_settings) as client:
        assert (await login(client, "rm@example.test")).status_code == 200
        response = await client.get("/api/v1/rms")

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("GET", "/api/v1/auth/me", None),
        ("GET", "/api/v1/users", None),
        ("POST", "/api/v1/users", {"name": "Anon", "email": "anon@example.test", "password": PASSWORD, "role": "ops"}),
        ("GET", f"/api/v1/users/{uuid4()}", None),
        ("PATCH", f"/api/v1/users/{uuid4()}", {"name": "Anon Update"}),
        ("DELETE", f"/api/v1/users/{uuid4()}", None),
        ("GET", "/api/v1/rms", None),
    ],
)
async def test_protected_endpoints_reject_anonymous_access(
    method: str,
    path: str,
    json_body: dict[str, str] | None,
    test_settings: Settings,
    db_engine,
) -> None:
    async with client_for(test_settings) as client:
        response = await client.request(method, path, json=json_body)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_rm_family_scope_helpers_limit_visibility_to_assigned_families(db_engine, db_session: Session) -> None:
    rm = create_test_user(db_session, email="rm@example.test", role=UserRole.RM)
    management = create_test_user(db_session, email="management@example.test", role=UserRole.MANAGEMENT)
    ops = create_test_user(db_session, email="ops@example.test", role=UserRole.OPS)

    assert user_can_view_family(rm, rm.id) is True
    assert user_can_view_family(rm, uuid4()) is False
    assert user_can_update_family(rm, rm.id) is True
    assert user_can_update_family(rm, uuid4()) is False
    assert user_can_view_family(management, uuid4()) is True
    assert user_can_update_family(management, uuid4()) is False
    assert user_can_update_family(ops, uuid4()) is True
