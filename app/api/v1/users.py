from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_id, require_active_user, require_module_roles, utc_now
from app.api.errors import raise_api_error
from app.core.security import hash_password
from app.domain.access import (
    LEGACY_CAN_ROLE_BY_USER_ROLE,
    MODULE_ADMIN_ROLES,
    administered_module_codes,
    effective_membership_dicts,
    effective_module_roles,
    effective_module_codes,
    ensure_modules_seeded,
    is_platform_admin,
    module_code_value,
    normalize_module_code,
    normalize_module_role,
    user_has_module_role,
)
from app.domain.enums import AuditEntityType, ChangeSource, ModuleCode, ModuleRole, UserRole
from app.models.user import User, UserModuleMembership, UserSession
from app.models.user import CanSensitiveAccessSetting
from app.schemas.users import (
    CanSensitiveAccessSettingsRead,
    CanSensitiveAccessSettingsUpdate,
    CanSensitiveField,
    UserCreate,
    UserModuleMembershipInput,
    UserRead,
    UserUpdate,
)
from app.services.audit import record_create, record_delete, record_update

router = APIRouter(tags=["users"])

require_rm_listing = require_module_roles(
    ModuleCode.CAN_COMPLIANCE,
    ModuleRole.CAN_ADMIN,
    ModuleRole.CAN_OPS,
    ModuleRole.CAN_MANAGEMENT,
)
USER_AUDIT_SENSITIVE_FIELDS = {"email", "password"}
CAN_SENSITIVE_FIELDS: tuple[CanSensitiveField, ...] = ("pan", "mobile", "email", "bank_account_number")
CAN_SENSITIVE_CONFIGURABLE_ROLES: tuple[ModuleRole, ...] = (ModuleRole.CAN_OPS, ModuleRole.CAN_RM)


def require_user_admin(current_user: User = Depends(require_active_user)) -> User:
    if not administered_module_codes(current_user):
        raise_api_error(
            status.HTTP_403_FORBIDDEN,
            "forbidden",
            "User role is not permitted for this action.",
        )
    return current_user


def require_can_admin(current_user: User = Depends(require_active_user)) -> User:
    if not user_has_module_role(current_user, ModuleCode.CAN_COMPLIANCE, ModuleRole.CAN_ADMIN):
        raise_api_error(
            status.HTTP_403_FORBIDDEN,
            "forbidden",
            "Only CAN admins can manage sensitive access settings.",
        )
    return current_user


def _request_id(request: Request) -> str | None:
    return get_request_id(request)


def _user_audit_values(user: User) -> dict[str, object]:
    return {
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }


def _setting_key(role: ModuleRole | str, field_name: str) -> tuple[str, str]:
    return (role.value if isinstance(role, ModuleRole) else str(role), field_name)


def ensure_can_sensitive_access_seeded(db: Session) -> None:
    existing = {
        _setting_key(setting.role, setting.field_name)
        for setting in db.scalars(
            select(CanSensitiveAccessSetting).where(CanSensitiveAccessSetting.deleted_at.is_(None))
        )
    }
    for role in CAN_SENSITIVE_CONFIGURABLE_ROLES:
        for field_name in CAN_SENSITIVE_FIELDS:
            if (role.value, field_name) in existing:
                continue
            db.add(
                CanSensitiveAccessSetting(
                    role=role,
                    field_name=field_name,
                    is_enabled=role == ModuleRole.CAN_OPS,
                )
            )
    db.flush()


def can_sensitive_access_settings_to_read(db: Session) -> dict[str, dict[str, bool]]:
    result = {
        role.value: {field_name: role == ModuleRole.CAN_OPS for field_name in CAN_SENSITIVE_FIELDS}
        for role in CAN_SENSITIVE_CONFIGURABLE_ROLES
    }
    settings = db.scalars(
        select(CanSensitiveAccessSetting).where(CanSensitiveAccessSetting.deleted_at.is_(None))
    )
    for setting in settings:
        role = str(setting.role)
        if role in result and setting.field_name in result[role]:
            result[role][setting.field_name] = setting.is_enabled
    return result


def can_sensitive_access_for_user(user: User, db: Session | None = None) -> dict[str, bool]:
    if user_has_module_role(user, ModuleCode.CAN_COMPLIANCE, ModuleRole.CAN_ADMIN):
        return {field_name: True for field_name in CAN_SENSITIVE_FIELDS}
    if user_has_module_role(user, ModuleCode.CAN_COMPLIANCE, ModuleRole.CAN_MANAGEMENT, platform_admin_bypass=False):
        return {field_name: False for field_name in CAN_SENSITIVE_FIELDS}

    roles = effective_module_roles(user, ModuleCode.CAN_COMPLIANCE)
    configurable_roles = roles & set(CAN_SENSITIVE_CONFIGURABLE_ROLES)
    if not configurable_roles:
        return {field_name: False for field_name in CAN_SENSITIVE_FIELDS}
    if db is None:
        return {
            field_name: any(role == ModuleRole.CAN_OPS for role in configurable_roles)
            for field_name in CAN_SENSITIVE_FIELDS
        }

    settings = can_sensitive_access_settings_to_read(db)
    return {
        field_name: any(settings[role.value][field_name] for role in configurable_roles)
        for field_name in CAN_SENSITIVE_FIELDS
    }


def user_to_read(user: User, db: Session | None = None) -> dict[str, object]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "memberships": effective_membership_dicts(user),
        "module_codes": effective_module_codes(user),
        "can_sensitive_access": can_sensitive_access_for_user(user, db),
        "is_platform_admin": is_platform_admin(user),
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@router.get("/admin/can-sensitive-access", response_model=CanSensitiveAccessSettingsRead)
def get_can_sensitive_access_settings(
    _admin: User = Depends(require_can_admin),
    db: Session = Depends(get_db),
) -> dict[str, dict[str, bool]]:
    return can_sensitive_access_settings_to_read(db)


@router.patch("/admin/can-sensitive-access", response_model=CanSensitiveAccessSettingsRead)
def update_can_sensitive_access_settings(
    payload: CanSensitiveAccessSettingsUpdate,
    _request: Request,
    _admin: User = Depends(require_can_admin),
    db: Session = Depends(get_db),
) -> dict[str, dict[str, bool]]:
    ensure_can_sensitive_access_seeded(db)
    existing = {
        _setting_key(setting.role, setting.field_name): setting
        for setting in db.scalars(
            select(CanSensitiveAccessSetting).where(CanSensitiveAccessSetting.deleted_at.is_(None))
        )
    }
    for role in CAN_SENSITIVE_CONFIGURABLE_ROLES:
        role_payload = getattr(payload, role.value)
        for field_name in CAN_SENSITIVE_FIELDS:
            existing[(role.value, field_name)].is_enabled = getattr(role_payload, field_name)
    db.commit()
    return can_sensitive_access_settings_to_read(db)


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


def _ensure_self_update_is_safe(user: User, admin: User, payload: UserUpdate) -> None:
    if user.id != admin.id:
        return
    if payload.is_active is False:
        raise_api_error(
            status.HTTP_400_BAD_REQUEST,
            "self_deactivation_not_allowed",
            "You cannot deactivate your own account.",
        )
    if payload.role is not None and payload.role != UserRole.ADMIN:
        raise_api_error(
            status.HTTP_400_BAD_REQUEST,
            "self_role_change_not_allowed",
            "You cannot remove your own admin role.",
        )
    if payload.memberships is not None and not is_platform_admin(admin):
        retained_admin_modules = set()
        for membership in payload.memberships:
            module_code = normalize_module_code(membership.module_code)
            admin_role = MODULE_ADMIN_ROLES.get(module_code)
            if membership.is_active and admin_role is not None and normalize_module_role(membership.role) == admin_role:
                retained_admin_modules.add(module_code)
        if not administered_module_codes(admin).issubset(retained_admin_modules):
            raise_api_error(
                status.HTTP_400_BAD_REQUEST,
                "self_module_admin_change_not_allowed",
                "You cannot remove your own module admin access.",
            )


def _membership_key(membership: UserModuleMembershipInput) -> ModuleCode:
    return normalize_module_code(membership.module_code)


def _ensure_no_duplicate_memberships(memberships: list[UserModuleMembershipInput]) -> None:
    module_codes = [_membership_key(membership) for membership in memberships]
    if len(module_codes) != len(set(module_codes)):
        raise_api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "duplicate_module_membership",
            "Only one membership per module is allowed.",
        )


def _legacy_membership(role: UserRole, is_active: bool = True) -> UserModuleMembershipInput:
    return UserModuleMembershipInput(
        module_code=ModuleCode.CAN_COMPLIANCE,
        role=LEGACY_CAN_ROLE_BY_USER_ROLE[role],
        is_active=is_active,
    )


def _requested_memberships_for_create(payload: UserCreate, admin: User) -> list[UserModuleMembershipInput]:
    if payload.memberships:
        memberships = payload.memberships
    elif is_platform_admin(admin):
        memberships = [_legacy_membership(payload.role, payload.is_active)]
    else:
        raise_api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "module_membership_required",
            "Module admins must provide at least one module membership.",
        )
    _ensure_no_duplicate_memberships(memberships)
    return memberships


def _ensure_memberships_administerable(admin: User, memberships: list[UserModuleMembershipInput]) -> None:
    if is_platform_admin(admin):
        return
    allowed_modules = administered_module_codes(admin)
    for membership in memberships:
        if normalize_module_code(membership.module_code) not in allowed_modules:
            raise_api_error(
                status.HTTP_403_FORBIDDEN,
                "forbidden",
                "You cannot manage memberships for this module.",
            )


def _ensure_user_visible_to_admin(admin: User, user: User) -> None:
    if is_platform_admin(admin):
        return
    allowed_modules = administered_module_codes(admin)
    if _has_any_administered_module(user, allowed_modules):
        return
    raise_api_error(
        status.HTTP_403_FORBIDDEN,
        "forbidden",
        "You cannot manage this user.",
    )


def _has_any_administered_module(user: User, allowed_modules: set[ModuleCode]) -> bool:
    user_module_codes = {
        module_code_value(membership["module_code"])
        for membership in effective_membership_dicts(user)
    }
    return any(module_code.value in user_module_codes for module_code in allowed_modules)


def _set_user_memberships(
    db: Session,
    user: User,
    memberships: list[UserModuleMembershipInput],
    admin: User,
    module_scope: set[ModuleCode] | None = None,
) -> None:
    _ensure_no_duplicate_memberships(memberships)
    _ensure_memberships_administerable(admin, memberships)
    ensure_modules_seeded(db)

    allowed_modules = (
        module_scope
        if module_scope is not None
        else set(ModuleCode) if is_platform_admin(admin) else administered_module_codes(admin)
    )
    existing = {
        normalize_module_code(membership.module_code): membership
        for membership in user.module_memberships
        if membership.deleted_at is None
    }
    requested = {_membership_key(membership): membership for membership in memberships}

    for module_code, payload in requested.items():
        if module_code not in allowed_modules:
            continue
        existing_membership = existing.get(module_code)
        if existing_membership is None:
            user.module_memberships.append(
                UserModuleMembership(
                    module_code=payload.module_code,
                    role=payload.role,
                    is_active=payload.is_active,
                )
            )
        else:
            existing_membership.role = payload.role
            existing_membership.is_active = payload.is_active

    for module_code, existing_membership in existing.items():
        if module_code in allowed_modules and module_code not in requested:
            existing_membership.is_active = False


def _sync_legacy_can_membership(db: Session, user: User, admin: User) -> None:
    try:
        role = UserRole(user.role)
    except ValueError:
        return
    _set_user_memberships(
        db,
        user,
        [_legacy_membership(role, user.is_active)],
        admin,
        module_scope={ModuleCode.CAN_COMPLIANCE},
    )


@router.get("/users", response_model=list[UserRead])
def list_users(
    include_inactive: bool = True,
    admin: User = Depends(require_user_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    filters = [User.deleted_at.is_(None)]
    if not include_inactive:
        filters.append(User.is_active.is_(True))
    users = list(db.scalars(select(User).where(*filters).order_by(User.name, User.email)).all())
    if not is_platform_admin(admin):
        allowed_modules = administered_module_codes(admin)
        users = [user for user in users if _has_any_administered_module(user, allowed_modules)]
    return [user_to_read(user) for user in users]


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    admin: User = Depends(require_user_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if not is_platform_admin(admin) and payload.role == UserRole.ADMIN:
        raise_api_error(
            status.HTTP_403_FORBIDDEN,
            "forbidden",
            "Module admins cannot create platform admin users.",
        )
    memberships = _requested_memberships_for_create(payload, admin)
    _ensure_memberships_administerable(admin, memberships)
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
    _set_user_memberships(db, user, memberships, admin)
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
    return user_to_read(user)


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    admin: User = Depends(require_user_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    user = _get_user_or_404(user_id, db)
    _ensure_user_visible_to_admin(admin, user)
    return user_to_read(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    request: Request,
    admin: User = Depends(require_user_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    user = _get_user_or_404(user_id, db)
    _ensure_user_visible_to_admin(admin, user)
    _ensure_self_update_is_safe(user, admin, payload)
    if not is_platform_admin(admin):
        disallowed_global_fields = payload.model_fields_set - {"memberships"}
        if disallowed_global_fields:
            raise_api_error(
                status.HTTP_403_FORBIDDEN,
                "forbidden",
                "Module admins can only update memberships for modules they administer.",
            )
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
    if payload.memberships is not None:
        _set_user_memberships(db, user, payload.memberships, admin)
    elif payload.role is not None or payload.is_active is not None:
        _sync_legacy_can_membership(db, user, admin)

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
    return user_to_read(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: UUID,
    request: Request,
    admin: User = Depends(require_user_admin),
    db: Session = Depends(get_db),
) -> None:
    if not is_platform_admin(admin):
        raise_api_error(
            status.HTTP_403_FORBIDDEN,
            "forbidden",
            "Only platform admins can deactivate user identities.",
        )
    user = _get_user_or_404(user_id, db)
    if user.id == admin.id:
        raise_api_error(
            status.HTTP_400_BAD_REQUEST,
            "self_deactivation_not_allowed",
            "You cannot deactivate your own account.",
        )
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
) -> list[dict[str, object]]:
    users = list(
        db.scalars(
            select(User)
            .where(
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
            .order_by(User.name, User.email)
        ).all()
    )
    rms = [
        user
        for user in users
        if user_has_module_role(
            user,
            ModuleCode.CAN_COMPLIANCE,
            ModuleRole.CAN_RM,
            platform_admin_bypass=False,
        )
    ]
    return [user_to_read(user) for user in rms]
