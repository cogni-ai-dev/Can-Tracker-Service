import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react';

import { Badge, Card, EmptyState, PageHeader } from '../../components/ui';
import { usersApi } from '../../lib/api';
import { canAdministerUserModule, canManageUsers, canRoleToUserRole, effectiveMemberships } from '../../lib/access';
import type { CurrentUser, ModuleCode, ModuleRole, UserMembership, UserPayload, UserRecord, UserRole } from '../../types';

const userRoleLabels: Record<UserRole, string> = {
  admin: 'Platform Admin',
  ops: 'CAN Ops',
  rm: 'Relationship Manager',
  management: 'Management',
};

const moduleRoleLabels: Record<ModuleRole, string> = {
  can_admin: 'CAN Admin',
  can_ops: 'CAN Ops',
  can_rm: 'CAN RM',
  can_management: 'CAN Management',
  crm_admin: 'CRM Admin',
  crm_ops: 'CRM Ops',
  crm_relationship_manager: 'CRM Relationship Manager',
  crm_viewer: 'CRM Viewer',
};

const canRoles: ModuleRole[] = ['can_admin', 'can_ops', 'can_rm', 'can_management'];
const crmRoles: ModuleRole[] = ['crm_admin', 'crm_ops', 'crm_relationship_manager', 'crm_viewer'];

type UserModalState = { mode: 'create'; user?: undefined } | { mode: 'edit'; user: UserRecord } | null;

export function AdminModule({ user }: { user: CurrentUser }) {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<UserModalState>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    usersApi.list({ include_inactive: true })
      .then((items) => {
        if (!cancelled) setUsers(items);
      })
      .catch((error) => {
        if (!cancelled) setError(friendlyError(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshToken]);

  const filteredUsers = useMemo(() => {
    const term = query.trim().toLowerCase();
    return users.filter((item) => {
      if (roleFilter && item.role !== roleFilter) return false;
      if (statusFilter === 'active' && !item.is_active) return false;
      if (statusFilter === 'inactive' && item.is_active) return false;
      if (!term) return true;
      const membershipText = effectiveMemberships(item).map((membership) => moduleRoleLabels[membership.role]).join(' ');
      return [item.name, item.email, item.role, membershipText].join(' ').toLowerCase().includes(term);
    });
  }, [users, roleFilter, statusFilter, query]);

  function refresh() {
    setRefreshToken((value) => value + 1);
  }

  async function deactivate(target: UserRecord) {
    if (target.id === user.id) {
      setMessage('You cannot deactivate your own account.');
      return;
    }
    if (!window.confirm(`Deactivate ${target.name}?`)) return;
    try {
      await usersApi.deactivate(target.id);
      setMessage('User deactivated.');
      refresh();
    } catch (error) {
      setMessage(friendlyError(error));
    }
  }

  async function reactivate(target: UserRecord) {
    try {
      await usersApi.update(target.id, { is_active: true });
      setMessage('User reactivated.');
      refresh();
    } catch (error) {
      setMessage(friendlyError(error));
    }
  }

  if (!canManageUsers(user)) {
    return <EmptyState title="Admin access required" detail="Your role is not allowed to manage users." />;
  }

  return (
    <div>
      <PageHeader
        title="Users & Access"
        subtitle="Manage shared identities and module memberships for Compliance and Client CRM."
        action={(
          <button type="button" onClick={() => setModal({ mode: 'create' })} className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            <Plus size={16} /> Add User
          </button>
        )}
      />
      {message && <div className="mb-4 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{message}</div>}
      <Card className="mb-4">
        <div className="flex flex-wrap gap-2">
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search users" className={inputClass} />
          <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} className={selectClass}>
            <option value="">All roles</option>
            {Object.entries(userRoleLabels).map(([role, label]) => <option key={role} value={role}>{label}</option>)}
          </select>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className={selectClass}>
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </Card>
      {loading && <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">Loading users...</div>}
      {error && <EmptyState title="Users unavailable" detail={error} />}
      {!loading && !error && (
        <Card>
          <div className="mb-3 text-sm text-slate-500">Showing {filteredUsers.length} of {users.length} users</div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2">Primary Role</th>
                  <th className="px-3 py-2">Module Access</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Last Login</th>
                  <th className="px-3 py-2">Updated</th>
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredUsers.map((item) => (
                  <tr key={item.id}>
                    <td className="px-3 py-3 font-semibold text-slate-900">{item.name}</td>
                    <td className="px-3 py-3">{item.email}</td>
                    <td className="px-3 py-3"><Badge tone={item.role === 'admin' ? 'red' : 'blue'}>{userRoleLabels[item.role]}</Badge></td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1">
                        {effectiveMemberships(item).map((membership) => (
                          <Badge key={`${membership.module_code}-${membership.role}`} tone={membership.module_code === 'client_crm' ? 'yellow' : 'blue'}>
                            {moduleRoleLabels[membership.role]}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-3"><Badge tone={item.is_active ? 'green' : 'red'}>{item.is_active ? 'Active' : 'Inactive'}</Badge></td>
                    <td className="px-3 py-3">{formatDate(item.last_login_at)}</td>
                    <td className="px-3 py-3">{formatDate(item.updated_at)}</td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button type="button" onClick={() => setModal({ mode: 'edit', user: item })} className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                          <Pencil size={13} /> Edit
                        </button>
                        {item.id !== user.id && item.is_active && (
                          <button type="button" onClick={() => deactivate(item)} className="inline-flex items-center gap-1 rounded-md border border-rose-200 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                            <Trash2 size={13} /> Deactivate
                          </button>
                        )}
                        {!item.is_active && (
                          <button type="button" onClick={() => reactivate(item)} className="inline-flex items-center gap-1 rounded-md border border-blue-200 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50">
                            <RotateCcw size={13} /> Reactivate
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {!filteredUsers.length && <tr><td className="px-3 py-8 text-center text-slate-500" colSpan={8}>No users match the current filters.</td></tr>}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {modal && (
        <UserModal
          currentUser={user}
          modal={modal}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            setMessage(modal.mode === 'edit' ? 'User updated.' : 'User created.');
            refresh();
          }}
        />
      )}
    </div>
  );
}

function UserModal({
  currentUser,
  modal,
  onClose,
  onSaved,
}: {
  currentUser: CurrentUser;
  modal: UserModalState;
  onClose: () => void;
  onSaved: () => void;
}) {
  const target = modal?.mode === 'edit' ? modal.user : null;
  const isEdit = Boolean(target);
  const isSelf = target?.id === currentUser.id;
  const globalFieldsDisabled = isEdit && (isSelf || !currentUser.is_platform_admin);
  const canManageCan = canAdministerUserModule(currentUser, 'can_compliance');
  const canManageCrm = canAdministerUserModule(currentUser, 'client_crm');
  const memberships = target ? effectiveMemberships(target) : [];
  const [name, setName] = useState(target?.name || '');
  const [email, setEmail] = useState(target?.email || '');
  const [role, setRole] = useState<UserRole>(target?.role || 'rm');
  const [isActive, setIsActive] = useState(target?.is_active ?? true);
  const [password, setPassword] = useState('');
  const [canRole, setCanRole] = useState<ModuleRole | ''>(moduleRoleFor(memberships, 'can_compliance') || (canManageCan ? 'can_rm' : ''));
  const [crmRole, setCrmRole] = useState<ModuleRole | ''>(moduleRoleFor(memberships, 'client_crm') || (canManageCrm && !canRole ? 'crm_viewer' : ''));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (canRole && canRoleToUserRole[canRole] && !globalFieldsDisabled) setRole(canRoleToUserRole[canRole]);
    if (!canRole && crmRole && role === 'rm' && !globalFieldsDisabled) setRole('management');
  }, [canRole, crmRole, globalFieldsDisabled, role]);

  function membershipPayload(): UserMembership[] {
    const payload: UserMembership[] = [];
    if (canManageCan && canRole) payload.push({ module_code: 'can_compliance', role: canRole, is_active: isActive });
    if (canManageCrm && crmRole) payload.push({ module_code: 'client_crm', role: crmRole, is_active: isActive });
    return payload;
  }

  function buildPayload(): UserPayload | null {
    const memberships = membershipPayload();
    if (isEdit && !currentUser.is_platform_admin) return { memberships };
    if (!name.trim() || !email.trim() || !role) {
      setError('Name, email, and primary role are required.');
      return null;
    }
    if (!isEdit && !password.trim()) {
      setError('Password is required for new users.');
      return null;
    }
    if (password && password.length < 8) {
      setError('Password must be at least 8 characters.');
      return null;
    }
    if ((canManageCan || canManageCrm) && !memberships.length) {
      setError('Select at least one module access role.');
      return null;
    }
    const payload: UserPayload = {
      name: name.trim(),
      email: email.trim(),
      role,
      is_active: isActive,
      memberships,
    };
    if (!isEdit || password) payload.password = password;
    return payload;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    const payload = buildPayload();
    if (!payload) return;
    setBusy(true);
    try {
      if (target) await usersApi.update(target.id, payload);
      else await usersApi.create(payload);
      onSaved();
    } catch (error) {
      setError(friendlyError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
      <form onSubmit={submit} className="max-h-full w-full max-w-3xl overflow-hidden rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-950 px-5 py-4 text-white">
          <div className="font-semibold">{target ? 'Edit User' : 'Add User'}</div>
          <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-sm text-slate-300 hover:bg-white/10 hover:text-white">Close</button>
        </div>
        <div className="max-h-[78vh] space-y-4 overflow-y-auto p-5">
          {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
          {isSelf && <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">You cannot remove your own admin access or deactivate your own account.</div>}
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Name">
              <input value={name} disabled={globalFieldsDisabled} onChange={(event) => setName(event.target.value)} className={inputClass} />
            </Field>
            <Field label="Email">
              <input value={email} disabled={globalFieldsDisabled} onChange={(event) => setEmail(event.target.value)} className={inputClass} />
            </Field>
            <Field label="Primary Role">
              <select value={role} disabled={globalFieldsDisabled} onChange={(event) => setRole(event.target.value as UserRole)} className={inputClass}>
                {Object.entries(userRoleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </Field>
            <Field label="Status">
              <select value={String(isActive)} disabled={globalFieldsDisabled} onChange={(event) => setIsActive(event.target.value === 'true')} className={inputClass}>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </Field>
            <Field label={isEdit ? 'Reset Password' : 'Password'}>
              <input value={password} disabled={isEdit && !currentUser.is_platform_admin} onChange={(event) => setPassword(event.target.value)} type="password" placeholder={isEdit ? 'Leave blank to keep current password' : 'Initial password'} className={inputClass} />
            </Field>
          </div>
          <div className="rounded-lg border border-slate-200 p-4">
            <div className="mb-3 text-sm font-semibold text-slate-900">Module Access</div>
            <div className="grid gap-4 md:grid-cols-2">
              {canManageCan && (
                <Field label="CAN Compliance">
                  <select value={canRole} disabled={isSelf} onChange={(event) => setCanRole(event.target.value as ModuleRole | '')} className={inputClass}>
                    <option value="">No CAN access</option>
                    {canRoles.map((item) => <option key={item} value={item}>{moduleRoleLabels[item]}</option>)}
                  </select>
                </Field>
              )}
              {canManageCrm && (
                <Field label="Client CRM">
                  <select value={crmRole} disabled={isSelf} onChange={(event) => setCrmRole(event.target.value as ModuleRole | '')} className={inputClass}>
                    <option value="">No CRM access</option>
                    {crmRoles.map((item) => <option key={item} value={item}>{moduleRoleLabels[item]}</option>)}
                  </select>
                </Field>
              )}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel</button>
            <button disabled={busy} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{busy ? 'Saving...' : 'Save User'}</button>
          </div>
        </div>
      </form>
    </div>
  );
}

function moduleRoleFor(memberships: UserMembership[], moduleCode: ModuleCode) {
  return memberships.find((membership) => membership.module_code === moduleCode)?.role || '';
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <div className="mt-1">{children}</div>
    </label>
  );
}

function formatDate(value: string | null | undefined) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function friendlyError(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}

const inputClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-500';
const selectClass = 'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500';
