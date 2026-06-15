from collections.abc import Callable, Generator
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Request, Response, status
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import raise_api_error
from app.core.config import Settings
from app.core.database import get_sessionmaker
from app.core.security import hash_session_token
from app.domain.enums import UserRole
from app.models.user import User, UserSession


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or request.headers.get("x-request-id")


def get_db(request: Request) -> Generator[Session, None, None]:
    settings = get_app_settings(request)
    session_local = get_sessionmaker(settings.database_url)
    with session_local() as session:
        yield session


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _configured_secret(settings: Settings) -> SecretStr:
    if settings.app_secret_key is None:
        raise RuntimeError("APP_SECRET_KEY is required for session handling.")
    return settings.app_secret_key


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> UserSession:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise_api_error(
            status.HTTP_401_UNAUTHORIZED,
            "authentication_required",
            "Authentication is required.",
        )

    token_hash = hash_session_token(token, _configured_secret(settings))
    session_record = db.scalar(
        select(UserSession)
        .join(UserSession.user)
        .where(
            UserSession.session_token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.deleted_at.is_(None),
            UserSession.expires_at > utc_now(),
            User.deleted_at.is_(None),
        )
    )
    if session_record is None:
        raise_api_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_session",
            "Session is invalid or expired.",
        )
    return session_record


def get_authenticated_user(current_session: UserSession = Depends(get_current_session)) -> User:
    return current_session.user


def require_active_user(current_user: User = Depends(get_authenticated_user)) -> User:
    if not current_user.is_active:
        raise_api_error(
            status.HTTP_403_FORBIDDEN,
            "inactive_user",
            "User account is inactive.",
        )
    return current_user


def require_user(current_user: User = Depends(require_active_user)) -> User:
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    role_set = set(allowed_roles)

    def dependency(current_user: User = Depends(require_active_user)) -> User:
        if current_user.role not in role_set:
            raise_api_error(
                status.HTTP_403_FORBIDDEN,
                "forbidden",
                "User role is not permitted for this action.",
            )
        return current_user

    return dependency


def user_can_view_family(user: User, primary_rm_id: UUID | str | None) -> bool:
    if user.role in {UserRole.ADMIN, UserRole.OPS, UserRole.MANAGEMENT}:
        return True
    if user.role == UserRole.RM:
        return primary_rm_id is not None and str(primary_rm_id) == str(user.id)
    return False


def user_can_update_family(user: User, primary_rm_id: UUID | str | None) -> bool:
    if user.role in {UserRole.ADMIN, UserRole.OPS}:
        return True
    if user.role == UserRole.RM:
        return primary_rm_id is not None and str(primary_rm_id) == str(user.id)
    return False


FamilyScopeGuard = Callable[[UUID | str | None], None]


def require_family_view_scope(current_user: User = Depends(require_active_user)) -> FamilyScopeGuard:
    def guard(primary_rm_id: UUID | str | None) -> None:
        if not user_can_view_family(current_user, primary_rm_id):
            raise_api_error(
                status.HTTP_403_FORBIDDEN,
                "forbidden",
                "User cannot view this family.",
            )

    return guard


def require_family_update_scope(current_user: User = Depends(require_active_user)) -> FamilyScopeGuard:
    def guard(primary_rm_id: UUID | str | None) -> None:
        if not user_can_update_family(current_user, primary_rm_id):
            raise_api_error(
                status.HTTP_403_FORBIDDEN,
                "forbidden",
                "User cannot update this family.",
            )

    return guard
