from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import clear_session_cookie, get_app_settings, get_db, require_active_user, utc_now
from app.api.errors import raise_api_error
from app.core.config import Settings
from app.core.security import hash_session_token, new_session_token, verify_password
from app.models.user import User, UserSession
from app.schemas.users import LoginRequest, LoginResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _require_secret(settings: Settings):
    if settings.app_secret_key is None:
        raise RuntimeError("APP_SECRET_KEY is required for session handling.")
    return settings.app_secret_key


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, User]:
    user = db.scalar(select(User).where(User.email == payload.email, User.deleted_at.is_(None)))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise_api_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_credentials",
            "Invalid email or password.",
        )

    now = utc_now()
    token = new_session_token()
    session = UserSession(
        user_id=user.id,
        session_token_hash=hash_session_token(token, _require_secret(settings)),
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
    )
    user.last_login_at = now
    db.add(session)
    db.commit()
    db.refresh(user)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"user": user}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token and settings.app_secret_key is not None:
        session_token_hash = hash_session_token(token, settings.app_secret_key)
        session = db.scalar(
            select(UserSession).where(
                UserSession.session_token_hash == session_token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.deleted_at.is_(None),
            )
        )
        if session is not None:
            session.revoked_at = utc_now()
            db.commit()

    clear_session_cookie(response, settings)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(require_active_user)) -> User:
    return current_user
