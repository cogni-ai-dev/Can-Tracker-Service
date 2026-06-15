import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.domain.enums import AuditAction, AuditEntityType, UserRole
from app.main import create_app
from app.models.audit import AuditLog
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
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


@pytest.mark.asyncio
async def test_admin_can_query_audit_logs_for_user_writes(
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        create_response = await client.post(
            "/api/v1/users",
            json={"name": "Ops User", "email": "ops@example.test", "password": PASSWORD, "role": "ops"},
            headers={"x-request-id": "req-create"},
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        patch_response = await client.patch(
            f"/api/v1/users/{user_id}",
            json={"name": "Ops Renamed", "email": "ops.renamed@example.test"},
            headers={"x-request-id": "req-update"},
        )
        assert patch_response.status_code == 200

        response = await client.get(f"/api/v1/audit?entity_type=user&entity_id={user_id}&limit=20")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert {(item["action"], item["field_name"]) for item in body["items"]} == {
        ("create", None),
        ("update", "name"),
        ("update", "email"),
    }
    email_update = next(item for item in body["items"] if item["field_name"] == "email")
    assert email_update["old_value"] == "o**@e******.test"
    assert email_update["new_value"] == "o**********@e******.test"
    assert "ops@example.test" not in str(body)
    assert {item["actor_user_id"] for item in body["items"]} == {str(admin.id)}
    assert {item["request_id"] for item in body["items"]} == {"req-create", "req-update"}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.OPS, UserRole.RM, UserRole.MANAGEMENT])
async def test_non_admin_roles_cannot_query_audit_logs(
    role: UserRole,
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    user = create_test_user(db_session, email=f"{role.value}@example.test", role=role)

    async with client_for(test_settings) as client:
        assert (await login(client, user.email)).status_code == 200
        response = await client.get("/api/v1/audit")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_audit_query_is_rejected(test_settings: Settings, db_engine) -> None:
    async with client_for(test_settings) as client:
        response = await client.get("/api/v1/audit")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_user_update(
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Settings,
    db_engine,
    db_session: Session,
) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    target = create_test_user(db_session, email="ops@example.test", role=UserRole.OPS, name="Ops User")

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit insert failed")

    monkeypatch.setattr("app.api.v1.users.record_update", fail_audit)

    async with client_for(test_settings) as client:
        assert (await login(client, admin.email)).status_code == 200
        with pytest.raises(RuntimeError, match="audit insert failed"):
            await client.patch(f"/api/v1/users/{target.id}", json={"name": "Should Roll Back"})

    db_session.expire_all()
    persisted = db_session.get(User, target.id)
    assert persisted is not None
    assert persisted.name == "Ops User"
    assert db_session.scalar(select(AuditLog).where(AuditLog.entity_id == target.id)) is None


def test_user_update_audit_stores_password_changes_as_redacted_values(db_engine, db_session: Session) -> None:
    admin = create_test_user(db_session, email="admin@example.test", role=UserRole.ADMIN)
    target = create_test_user(db_session, email="ops@example.test", role=UserRole.OPS)

    from app.services.audit import record_update

    record_update(
        db_session,
        entity_type=AuditEntityType.USER,
        entity_id=target.id,
        old_values={"password": "configured"},
        new_values={"password": "changed"},
        actor_user_id=admin.id,
        sensitive_fields={"password"},
    )
    db_session.commit()

    log = db_session.scalar(select(AuditLog).where(AuditLog.action == AuditAction.UPDATE))
    assert log is not None
    assert log.old_value == "[REDACTED]"
    assert log.new_value == "[REDACTED]"
