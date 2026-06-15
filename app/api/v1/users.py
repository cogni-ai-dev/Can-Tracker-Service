from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_id, require_roles, utc_now
from app.api.errors import raise_api_error
from app.core.security import hash_password
from app.domain.enums import AuditEntityType, ChangeSource, UserRole
from app.models.user import User, UserSession
from app.schemas.users import UserCreate, UserRead, UserUpdate
from app.services.audit import record_create, record_delete, record_update

router = APIRouter(tags=["users"])

require_admin = require_roles(UserRole.ADMIN)
require_rm_listing = require_roles(UserRole.ADMIN, UserRole.OPS, UserRole.MANAGEMENT)
USER_AUDIT_SENSITIVE_FIELDS = {"email", "password"}


def _request_id(request: Request) -> str | None:
    return get_request_id(request)


def _user_audit_values(user: User) -> dict[str, object]:
    return {
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }


def _get_user_or_404(user_id: UUID, db: Session) -> User:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise_api_error(
            status.HTTP_404_NOT_FOUND,
            "user_not_found",
            "User was not found.",
        )
    return user


def _ensure_email_available(email: str, db: Session, existing_user_id: UUID | None = None) -> None:
    user = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    if user is not None and user.id != existing_user_id:
        raise_api_error(
            status.HTTP_409_CONFLICT,
            "email_already_exists",
            "A user with this email already exists.",
        )


def _revoke_user_sessions(user_id: UUID, db: Session) -> None:
    now = utc_now()
    sessions = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.deleted_at.is_(None),
        )
    )
    for session in sessions:
        session.revoked_at = now


@router.get("/users", response_model=list[UserRead])
def list_users(
    include_inactive: bool = True,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    filters = [User.deleted_at.is_(None)]
    if not include_inactive:
        filters.append(User.is_active.is_(True))
    return list(db.scalars(select(User).where(*filters).order_by(User.name, User.email)).all())


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    _ensure_email_available(payload.email, db)
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()
    record_create(
        db,
        entity_type=AuditEntityType.USER,
        entity_id=user.id,
        actor_user_id=admin.id,
        source=ChangeSource.MANUAL,
        request_id=_request_id(request),
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    return _get_user_or_404(user_id, db)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    user = _get_user_or_404(user_id, db)
    old_values = _user_audit_values(user)
    if payload.password is not None:
        old_values["password"] = "configured"

    if payload.email is not None:
        _ensure_email_available(payload.email, db, existing_user_id=user.id)
        user.email = payload.email
    if payload.name is not None:
        user.name = payload.name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        _revoke_user_sessions(user.id, db)
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        if user.is_active and not payload.is_active:
            _revoke_user_sessions(user.id, db)
        user.is_active = payload.is_active

    new_values = _user_audit_values(user)
    if payload.password is not None:
        new_values["password"] = "changed"
    record_update(
        db,
        entity_type=AuditEntityType.USER,
        entity_id=user.id,
        old_values=old_values,
        new_values=new_values,
        actor_user_id=admin.id,
        source=ChangeSource.MANUAL,
        sensitive_fields=USER_AUDIT_SENSITIVE_FIELDS,
        request_id=_request_id(request),
    )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: UUID,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    user = _get_user_or_404(user_id, db)
    if user.is_active:
        _revoke_user_sessions(user.id, db)
    user.is_active = False
    record_delete(
        db,
        entity_type=AuditEntityType.USER,
        entity_id=user.id,
        actor_user_id=admin.id,
        source=ChangeSource.MANUAL,
        request_id=_request_id(request),
    )
    db.commit()


@router.get("/rms", response_model=list[UserRead], tags=["rms"])
def list_rms(
    _current_user: User = Depends(require_rm_listing),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(
                User.role == UserRole.RM,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
            .order_by(User.name, User.email)
        ).all()
    )
