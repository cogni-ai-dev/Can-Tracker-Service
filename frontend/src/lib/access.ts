import type { CurrentUser, ModuleCode, ModuleRole, UserRecord, UserRole } from '../types';

export function canAccessModule(user: CurrentUser | null, moduleCode: ModuleCode) {
  if (!user) return false;
  if (user.is_platform_admin) return true;
  return user.memberships.some((membership) => (
    membership.is_active
    && membership.module_code === moduleCode
  ));
}

export function hasModuleRole(user: CurrentUser | null, moduleCode: ModuleCode, roles: ModuleRole[]) {
  if (!user) return false;
  if (user.is_platform_admin) return true;
  return user.memberships.some((membership) => (
    membership.is_active
    && membership.module_code === moduleCode
    && roles.includes(membership.role)
  ));
}

export function canManageUsers(user: CurrentUser | null) {
  return hasModuleRole(user, 'can_compliance', ['can_admin'])
    || hasModuleRole(user, 'client_crm', ['crm_admin']);
}

export function canUseImportPanel(user: CurrentUser | null) {
  return hasModuleRole(user, 'can_compliance', ['can_admin', 'can_ops']);
}

export function canAdministerUserModule(user: CurrentUser | null, moduleCode: ModuleCode) {
  if (!user) return false;
  if (user.is_platform_admin) return true;
  if (moduleCode === 'can_compliance') return hasModuleRole(user, 'can_compliance', ['can_admin']);
  if (moduleCode === 'client_crm') return hasModuleRole(user, 'client_crm', ['crm_admin']);
  return false;
}

export function isCanRM(user: CurrentUser | null) {
  return hasModuleRole(user, 'can_compliance', ['can_rm']) && !user?.is_platform_admin;
}

export function canEditFamily(user: CurrentUser | null) {
  return hasModuleRole(user, 'can_compliance', ['can_admin', 'can_ops']) || isCanRM(user);
}

export function canCreateFamily(user: CurrentUser | null) {
  return hasModuleRole(user, 'can_compliance', ['can_admin', 'can_ops']);
}

export function canCreateMember(user: CurrentUser | null) {
  return hasModuleRole(user, 'can_compliance', ['can_admin', 'can_ops']);
}

export function canEditMember(user: CurrentUser | null) {
  return hasModuleRole(user, 'can_compliance', ['can_admin', 'can_ops']) || isCanRM(user);
}

export function canDeleteMember(user: CurrentUser | null) {
  return hasModuleRole(user, 'can_compliance', ['can_admin']);
}

export function canDeleteFamily(user: CurrentUser | null) {
  return hasModuleRole(user, 'can_compliance', ['can_admin']);
}

const legacyUserRoleToCanRole: Record<UserRole, ModuleRole> = {
  admin: 'can_admin',
  ops: 'can_ops',
  rm: 'can_rm',
  management: 'can_management',
};

export function effectiveMemberships(user: Pick<UserRecord, 'role' | 'memberships'>) {
  const active = user.memberships.filter((membership) => membership.is_active);
  if (active.length) return active;
  return [{ module_code: 'can_compliance' as ModuleCode, role: legacyUserRoleToCanRole[user.role], is_active: true }];
}

export const canRoleToUserRole: Partial<Record<ModuleRole, UserRole>> = {
  can_admin: 'admin',
  can_ops: 'ops',
  can_rm: 'rm',
  can_management: 'management',
};
