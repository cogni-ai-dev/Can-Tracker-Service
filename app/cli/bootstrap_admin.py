import os
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.core.pii import mask_email
from app.core.security import hash_password
from app.domain.enums import AuditEntityType, ChangeSource, UserRole
from app.models.user import User
from app.schemas.users import normalize_email
from app.services.audit import record_create


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def main() -> int:
    settings = get_settings()
    email = normalize_email(_required_env("BOOTSTRAP_ADMIN_EMAIL"))
    name = _required_env("BOOTSTRAP_ADMIN_NAME")
    password = _required_env("BOOTSTRAP_ADMIN_PASSWORD")
    if len(password) < 8:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD must be at least 8 characters.")

    session_local = get_sessionmaker(settings.database_url)
    with session_local() as db:
        existing = db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
        if existing is not None:
            print(f"Admin bootstrap skipped; user already exists: {mask_email(email)}")
            return 0

        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.flush()
        record_create(
            db,
            entity_type=AuditEntityType.USER,
            entity_id=admin.id,
            actor_user_id=None,
            source=ChangeSource.MANUAL,
        )
        db.commit()

    print(f"Admin bootstrap created: {mask_email(email)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Admin bootstrap failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
