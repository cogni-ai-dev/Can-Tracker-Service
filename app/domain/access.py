from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from sqlalchemy.orm import Session

from app.domain.enums import ModuleCode, ModuleRole, UserRole
from app.models.user import Module, User, UserModuleMembership

MODULE_NAMES: dict[ModuleCode, str] = {
    ModuleCode.CAN_COMPLIANCE: "CAN Compliance",
    ModuleCode.CLIENT_CRM: "Client CRM",
}

MODULE_ROLES: dict[ModuleCode, set[ModuleRole]] = {
    ModuleCode.CAN_COMPLIANCE: {
        ModuleRole.CAN_ADMIN,
        ModuleRole.CAN_OPS,
        ModuleRole.CAN_RM,
        ModuleRole.CAN_MANAGEMENT,
    },
    ModuleCode.CLIENT_CRM: {
        ModuleRole.CRM_ADMIN,
        ModuleRole.CRM_OPS,
        ModuleRole.CRM_RELATIONSHIP_MANAGER,
        ModuleRole.CRM_VIEWER,
    },
}

LEGACY_CAN_ROLE_BY_USER_ROLE: dict[UserRole, ModuleRole] = {
    UserRole.ADMIN: ModuleRole.CAN_ADMIN,
    UserRole.OPS: ModuleRole.CAN_OPS,
    UserRole.RM: ModuleRole.CAN_RM,
    UserRole.MANAGEMENT: ModuleRole.CAN_MANAGEMENT,
}

CAN_USER_ROLE_BY_MODULE_ROLE: dict[ModuleRole, UserRole] = {
    ModuleRole.CAN_ADMIN: UserRole.ADMIN,
    ModuleRole.CAN_OPS: UserRole.OPS,
    ModuleRole.CAN_RM: UserRole.RM,
    ModuleRole.CAN_MANAGEMENT: UserRole.MANAGEMENT,
}

MODULE_ADMIN_ROLES: dict[ModuleCode, ModuleRole] = {
    ModuleCode.CAN_COMPLIANCE: ModuleRole.CAN_ADMIN,
    ModuleCode.CLIENT_CRM: ModuleRole.CRM_ADMIN,
}


class ModuleMembershipLike(Protocol):
    module_code: ModuleCode | str
    role: ModuleRole | str


def module_code_value(module_code: ModuleCode | str) -> str:
    return module_code.value if isinstance(module_code, ModuleCode) else str(module_code)


def module_role_value(role: ModuleRole | str) -> str:
    return role.value if isinstance(role, ModuleRole) else str(role)


def normalize_module_code(module_code: ModuleCode | str) -> ModuleCode:
    return module_code if isinstance(module_code, ModuleCode) else ModuleCode(str(module_code))


def normalize_module_role(role: ModuleRole | str) -> ModuleRole:
    return role if isinstance(role, ModuleRole) else ModuleRole(str(role))


def ensure_modules_seeded(db: Session) -> None:
    for code, name in MODULE_NAMES.items():
        if db.get(Module, code.value) is None:
            db.add(Module(code=code, name=name, is_active=True))
    db.flush()


def role_belongs_to_module(module_code: ModuleCode | str, role: ModuleRole | str) -> bool:
    normalized_module = normalize_module_code(module_code)
    normalized_role = normalize_module_role(role)
    return normalized_role in MODULE_ROLES[normalized_module]


def is_platform_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN or user.role == UserRole.ADMIN.value


def active_explicit_memberships(user: User) -> list[UserModuleMembership]:
    return [
        membership
        for membership in user.module_memberships
        if membership.deleted_at is None and membership.is_active
    ]


def has_any_explicit_membership(user: User) -> bool:
    return any(membership.deleted_at is None for membership in user.module_memberships)


def explicit_module_roles(user: User, module_code: ModuleCode | str) -> set[ModuleRole]:
    normalized_module = normalize_module_code(module_code)
    roles: set[ModuleRole] = set()
    for membership in active_explicit_memberships(user):
        if module_code_value(membership.module_code) == normalized_module.value:
            roles.add(normalize_module_role(membership.role))
    return roles


def legacy_can_role(user: User) -> ModuleRole | None:
    try:
        return LEGACY_CAN_ROLE_BY_USER_ROLE[UserRole(user.role)]
    except ValueError:
        return None


def effective_module_roles(user: User, module_code: ModuleCode | str) -> set[ModuleRole]:
    normalized_module = normalize_module_code(module_code)
    roles = explicit_module_roles(user, normalized_module)
    if roles:
        return roles

    if normalized_module == ModuleCode.CAN_COMPLIANCE and not has_any_explicit_membership(user):
        legacy_role = legacy_can_role(user)
        return {legacy_role} if legacy_role is not None else set()

    return set()


def user_has_module_role(
    user: User,
    module_code: ModuleCode | str,
    *roles: ModuleRole,
    platform_admin_bypass: bool = True,
) -> bool:
    if platform_admin_bypass and is_platform_admin(user):
        return True
    allowed = set(roles)
    return bool(effective_module_roles(user, module_code) & allowed)


def user_is_can_rm(user: User) -> bool:
    return user_has_module_role(
        user,
        ModuleCode.CAN_COMPLIANCE,
        ModuleRole.CAN_RM,
        platform_admin_bypass=False,
    )


def user_can_read_all_can(user: User) -> bool:
    return user_has_module_role(
        user,
        ModuleCode.CAN_COMPLIANCE,
        ModuleRole.CAN_ADMIN,
        ModuleRole.CAN_OPS,
        ModuleRole.CAN_MANAGEMENT,
    )


def user_can_write_all_can(user: User) -> bool:
    return user_has_module_role(
        user,
        ModuleCode.CAN_COMPLIANCE,
        ModuleRole.CAN_ADMIN,
        ModuleRole.CAN_OPS,
    )


def user_can_read_sensitive_can(user: User) -> bool:
    return user_has_module_role(user, ModuleCode.CAN_COMPLIANCE, ModuleRole.CAN_ADMIN)


def administered_module_codes(user: User) -> set[ModuleCode]:
    if is_platform_admin(user):
        return set(ModuleCode)
    codes: set[ModuleCode] = set()
    for module_code, admin_role in MODULE_ADMIN_ROLES.items():
        if user_has_module_role(user, module_code, admin_role, platform_admin_bypass=False):
            codes.add(module_code)
    return codes


def can_administer_module(user: User, module_code: ModuleCode | str) -> bool:
    return normalize_module_code(module_code) in administered_module_codes(user)


def effective_membership_dicts(user: User) -> list[dict[str, object]]:
    memberships: dict[ModuleCode, ModuleRole] = {}
    for membership in active_explicit_memberships(user):
        module_code = normalize_module_code(membership.module_code)
        memberships[module_code] = normalize_module_role(membership.role)

    if not memberships:
        can_role = legacy_can_role(user)
        if can_role is not None:
            memberships[ModuleCode.CAN_COMPLIANCE] = can_role

    if is_platform_admin(user):
        memberships.setdefault(ModuleCode.CAN_COMPLIANCE, ModuleRole.CAN_ADMIN)
        memberships.setdefault(ModuleCode.CLIENT_CRM, ModuleRole.CRM_ADMIN)

    return [
        {"module_code": module_code, "role": role, "is_active": True}
        for module_code, role in sorted(memberships.items(), key=lambda item: item[0].value)
    ]


def effective_module_codes(user: User) -> list[ModuleCode]:
    return [membership["module_code"] for membership in effective_membership_dicts(user)]


def validate_membership_roles(memberships: Iterable[ModuleMembershipLike]) -> None:
    for membership in memberships:
        module_code = membership.module_code
        role = membership.role
        if not role_belongs_to_module(module_code, role):
            raise ValueError(
                f"Role {module_role_value(role)} is not valid for module {module_code_value(module_code)}."
            )
