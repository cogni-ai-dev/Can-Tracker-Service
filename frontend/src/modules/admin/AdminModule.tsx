import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  FileUp,
  Pencil,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

import { Badge, Card, ConfirmActionDialog, EmptyState, PageHeader } from '../../components/ui';
import { importsApi, usersApi } from '../../lib/api';
import { canAdministerUserModule, canManageUsers, canRoleToUserRole, canUseImportPanel, effectiveMemberships } from '../../lib/access';
import type {
  CanSensitiveAccess,
  CanSensitiveAccessSettings,
  CurrentUser,
  ImportBatch,
  ImportBatchStatus,
  ImportRow,
  ImportRowStatus,
  ModuleCode,
  ModuleRole,
  UserMembership,
  UserPayload,
  UserRecord,
  UserRole,
} from '../../types';

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

const roleGuideItems: Array<{ title: string; detail: string }> = [
  {
    title: 'CAN Admin',
    detail: 'Full CAN access, user management, audit logs, imports, and sensitive values.',
  },
  {
    title: 'CAN Ops',
    detail: 'Create, edit, import, and report across CAN records. No delete, user management, or audit logs.',
  },
  {
    title: 'CAN RM',
    detail: 'Assigned families only, with remarks-only updates.',
  },
  {
    title: 'CAN Management',
    detail: 'Read-only CAN dashboards, records, tasks, and reports.',
  },
  {
    title: 'CRM Admin',
    detail: 'Can manage CRM users and CRM module access.',
  },
  {
    title: 'CRM Ops / Relationship / Viewer',
    detail: 'CRM operations work, relationship follow-up, and read-only access labels.',
  },
];

const userRoleHelpText: Record<UserRole, string> = {
  admin: 'Platform admin maps to CAN Admin and can administer the full platform.',
  ops: 'CAN Ops maps to operational CAN write access without delete, user, or audit administration.',
  rm: 'Relationship Manager maps to CAN RM and is limited to assigned-family remarks updates.',
  management: 'Management maps to read-only CAN access, or a CRM-only user when no CAN role is selected.',
};

const moduleRoleHelpText: Record<ModuleRole, string> = {
  can_admin: roleGuideItems[0].detail,
  can_ops: roleGuideItems[1].detail,
  can_rm: roleGuideItems[2].detail,
  can_management: roleGuideItems[3].detail,
  crm_admin: roleGuideItems[4].detail,
  crm_ops: 'CRM operations work access.',
  crm_relationship_manager: 'CRM relationship follow-up access.',
  crm_viewer: 'Read-only CRM access label.',
};

type UserModalState = { mode: 'create'; user?: undefined } | { mode: 'edit'; user: UserRecord } | null;

type ImportPanelFilters = {
  batchStatus: '' | ImportBatchStatus;
  rowStatus: '' | ImportRowStatus;
};

export function AdminModule({ user }: { user: CurrentUser }) {
  const { page = 'users' } = useParams<{ page?: string }>();
  if (page === 'imports') {
    if (!canUseImportPanel(user)) {
      return <EmptyState title="Admin access required" detail="You do not have permissions to access MFU import." />;
    }
    return <AdminImportPanel user={user} />;
  }

  if (!canManageUsers(user)) {
    return <EmptyState title="Admin access required" detail="You do not have permissions to manage users." />;
  }
  return <UserManagementPanel user={user} />;
}

function UserManagementPanel({ user }: { user: CurrentUser }) {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<UserModalState>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<UserRecord | null>(null);
  const [deactivateBusy, setDeactivateBusy] = useState(false);
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

  function requestDeactivate(target: UserRecord) {
    if (target.id === user.id) {
      setMessage('You cannot deactivate your own account.');
      return;
    }
    setDeactivateTarget(target);
  }

  async function deactivate() {
    if (!deactivateTarget) return;
    setDeactivateBusy(true);
    try {
      await usersApi.deactivate(deactivateTarget.id);
      setMessage('User deactivated.');
      setDeactivateTarget(null);
      refresh();
    } catch (error) {
      setMessage(friendlyError(error));
    } finally {
      setDeactivateBusy(false);
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
      <RoleAccessGuide />
      {canAdministerUserModule(user, 'can_compliance') && <SensitiveAccessSettingsCard />}
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
                          <button type="button" onClick={() => requestDeactivate(item)} className="inline-flex items-center gap-1 rounded-md border border-rose-200 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50">
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
      {deactivateTarget && (
        <ConfirmActionDialog
          title="Deactivate User"
          message={`Deactivate ${deactivateTarget.name}? This user will lose access until an admin reactivates the account.`}
          confirmLabel="Deactivate User"
          busy={deactivateBusy}
          onCancel={() => setDeactivateTarget(null)}
          onConfirm={deactivate}
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
              <HelpText>{userRoleHelpText[role]}</HelpText>
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
                  <HelpText>{canRole ? moduleRoleHelpText[canRole] : 'No CAN Compliance access will be assigned.'}</HelpText>
                </Field>
              )}
              {canManageCrm && (
                <Field label="Client CRM">
                  <select value={crmRole} disabled={isSelf} onChange={(event) => setCrmRole(event.target.value as ModuleRole | '')} className={inputClass}>
                    <option value="">No CRM access</option>
                    {crmRoles.map((item) => <option key={item} value={item}>{moduleRoleLabels[item]}</option>)}
                  </select>
                  <HelpText>{crmRole ? moduleRoleHelpText[crmRole] : 'No Client CRM access will be assigned.'}</HelpText>
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

function AdminImportPanel({ user }: { user: CurrentUser }) {
  const [batches, setBatches] = useState<ImportBatch[]>([]);
  const [batchLoading, setBatchLoading] = useState(true);
  const [batchError, setBatchError] = useState('');
  const [batchFilters, setBatchFilters] = useState<ImportPanelFilters>({ batchStatus: '', rowStatus: '' });
  const [selectedBatchId, setSelectedBatchId] = useState('');
  const [rows, setRows] = useState<ImportRow[]>([]);
  const [rowLoading, setRowLoading] = useState(false);
  const [rowError, setRowError] = useState('');
  const [uploadBusy, setUploadBusy] = useState(false);
  const [commitBusy, setCommitBusy] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState('');
  const [refreshToken, setRefreshToken] = useState(0);

  const canImport = canUseImportPanel(user);
  const selectedBatch = batches.find((batch) => batch.id === selectedBatchId) || batches[0] || null;

  useEffect(() => {
    if (!canImport) return;
    let cancelled = false;
    setBatchLoading(true);
    setBatchError('');
    const params = batchFilters.batchStatus ? { status: batchFilters.batchStatus } : {};
    importsApi.listBatches({ ...params, limit: 100, offset: 0 })
      .then((response) => {
        if (cancelled) return;
        setBatches(response.items);
        if (!response.items.length) {
          setSelectedBatchId('');
          return;
        }
        const stillExists = response.items.some((batch) => batch.id === selectedBatchId);
        if (!selectedBatchId || !stillExists) {
          setSelectedBatchId(response.items[0].id);
        }
      })
      .catch((error) => {
        if (!cancelled) setBatchError(friendlyError(error));
      })
      .finally(() => {
        if (!cancelled) setBatchLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [batchFilters.batchStatus, canImport, refreshToken, selectedBatchId]);

  useEffect(() => {
    if (!canImport) return;
    const batchId = selectedBatchId || (batches[0] && batches[0].id);
    if (!batchId) {
      setRows([]);
      return;
    }
    let cancelled = false;
    setRowLoading(true);
    setRowError('');
    const params = batchFilters.rowStatus ? { status: batchFilters.rowStatus, limit: 1000, offset: 0 } : { limit: 1000, offset: 0 };
    importsApi.listRows(batchId, params)
      .then((response) => {
        if (!cancelled) setRows(response.items);
      })
      .catch((error) => {
        if (!cancelled) setRowError(friendlyError(error));
      })
      .finally(() => {
        if (!cancelled) setRowLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedBatchId, batches, batchFilters.rowStatus, canImport, refreshToken]);

  function refresh(options: { clearMessage?: boolean } = {}) {
    setRefreshToken((value) => value + 1);
    if (options.clearMessage !== false) setMessage('');
    setRowError('');
  }

  async function uploadBatch() {
    if (!selectedFile) return;
    if (!canImport) return;
    setUploadBusy(true);
    setBatchError('');
    setMessage('');
    try {
      const uploaded = await importsApi.uploadTemplate(selectedFile);
      setSelectedBatchId(uploaded.id);
      setSelectedFile(null);
      setMessage('Upload complete. Review validated rows before committing.');
      refresh({ clearMessage: false });
    } catch (error) {
      setBatchError(friendlyError(error));
    } finally {
      setUploadBusy(false);
    }
  }

  async function commitBatch() {
    if (!selectedBatch || selectedBatch.status !== 'validated' || selectedBatch.valid_row_count <= 0 || selectedBatch.errors.length > 0 || commitBusy) return;
    setCommitBusy(true);
    try {
      const committed = await importsApi.commitBatch(selectedBatch.id);
      setMessage(`Batch ${committed.file_name} committed successfully.`);
      refresh({ clearMessage: false });
    } catch (error) {
      setMessage(friendlyError(error));
    } finally {
      setCommitBusy(false);
    }
  }

  if (!canImport) {
    return <EmptyState title="Import access required" detail="You do not have permissions to access MFU import." />;
  }

  return (
    <div>
      <PageHeader
        title="MFU Import"
        subtitle="Upload and validate MFU template files, review row status, then commit valid rows."
        action={(
          <button
            type="button"
            onClick={() => {
              setMessage('');
              refresh();
            }}
            className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw size={16} /> Refresh
          </button>
        )}
      />

      {message && <div className="mb-4 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{message}</div>}

      <Card className="mb-4">
        <div className="mb-3 font-semibold text-slate-900">Upload New Template</div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="grow text-sm font-medium text-slate-700">
            Select CSV / XLSX
            <input
              type="file"
              accept=".csv,.xlsx"
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
            />
          </label>
          <button
            type="button"
            disabled={!selectedFile || uploadBusy}
            onClick={uploadBatch}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <FileUp size={16} />
            {uploadBusy ? 'Uploading...' : 'Upload'}
          </button>
        </div>
        {selectedFile && <div className="mt-2 text-sm text-slate-500">Selected file: {selectedFile.name}</div>}
      </Card>

      <Card className="mb-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="font-semibold text-slate-900">Import Batches</div>
            <div className="text-sm text-slate-500">Select a batch to review row-level results.</div>
          </div>
          <select
            aria-label="Filter batches by status"
            value={batchFilters.batchStatus}
            onChange={(event) => setBatchFilters((current) => ({ ...current, batchStatus: event.target.value as ImportPanelFilters['batchStatus'] }))}
            className={selectClass}
          >
            <option value="">All statuses</option>
            <option value="uploaded">Uploaded</option>
            <option value="validated">Validated</option>
            <option value="committed">Committed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        {batchError && <div className="mb-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{batchError}</div>}
        {batchLoading && <div className="text-sm text-slate-500">Loading batches...</div>}
        {selectedBatch && (
          <div className="mb-4 rounded-md bg-slate-50 p-3 text-sm text-slate-700">
            <div className="font-medium text-slate-900">{selectedBatch.file_name}</div>
            <div className="mt-1">Status: {formatImportStatus(selectedBatch.status)} | Valid: {selectedBatch.valid_row_count} | Errors: {selectedBatch.error_row_count} | Conflicts: {selectedBatch.conflict_row_count} | Committed: {selectedBatch.committed_row_count}</div>
            <div className="mt-1">Created: {formatDate(selectedBatch.created_at)} | Committed: {selectedBatch.committed_at ? formatDate(selectedBatch.committed_at) : 'Not committed'}</div>
            {!!selectedBatch.warnings.length && <div className="mt-2 text-slate-600">Warnings: {selectedBatch.warnings.join(', ')}</div>}
            {!!selectedBatch.errors.length && <div className="mt-1 text-rose-700">Batch Errors: {selectedBatch.errors.join(' | ')}</div>}
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">File</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Rows</th>
                <th className="px-3 py-2">Created</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {batches.map((batch) => (
                <tr key={batch.id} className={batch.id === selectedBatchId ? 'bg-blue-50' : ''}>
                  <td className="px-3 py-2">{batch.file_name}</td>
                  <td className="px-3 py-2"><span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs">{batch.status}</span></td>
                  <td className="px-3 py-2">{batch.row_count}</td>
                  <td className="px-3 py-2">{formatDate(batch.created_at)}</td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => setSelectedBatchId(batch.id)}
                      className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      Open
                    </button>
                  </td>
                </tr>
              ))}
              {!batches.length && <tr><td className="px-3 py-8 text-center text-slate-500" colSpan={5}>No batches found.</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-semibold text-slate-900">Batch Rows</div>
            <div className="text-sm text-slate-500">{selectedBatch ? `Rows for ${selectedBatch.file_name}` : 'Upload/select a batch to view rows.'}</div>
          </div>
          <div className="flex items-center gap-2">
            <select
              aria-label="Filter rows by status"
              value={batchFilters.rowStatus}
              onChange={(event) => setBatchFilters((current) => ({ ...current, rowStatus: event.target.value as ImportPanelFilters['rowStatus'] }))}
              className={selectClass}
            >
              <option value="">All rows</option>
              <option value="valid">Valid</option>
              <option value="error">Error</option>
              <option value="conflict">Conflict</option>
              <option value="committed">Committed</option>
              <option value="skipped">Skipped</option>
            </select>
            <button
              type="button"
              disabled={
                !selectedBatch
                || selectedBatch.status !== 'validated'
                || selectedBatch.valid_row_count <= 0
                || selectedBatch.errors.length > 0
                || commitBusy
              }
              onClick={commitBatch}
              className="rounded-md bg-green-600 px-3 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
            >
              {commitBusy ? 'Committing...' : 'Commit Valid Rows'}
            </button>
          </div>
        </div>
        {rowError && <div className="mb-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{rowError}</div>}
        {rowLoading && <div className="text-sm text-slate-500">Loading rows...</div>}
        {!selectedBatch && <div className="text-sm text-slate-500">Upload and select a batch first.</div>}
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Row</th>
                <th className="px-3 py-2">Family Code</th>
                <th className="px-3 py-2">Family Head</th>
                <th className="px-3 py-2">Member</th>
                <th className="px-3 py-2">CAN</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Errors</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className="px-3 py-2">{row.row_number}</td>
                  <td className="px-3 py-2">{String(asString(row.normalized_data.family_code) || asString(row.normalized_data.FamilyCode) || '-')}</td>
                  <td className="px-3 py-2">{String(asString(row.normalized_data.family_head_name) || asString(row.normalized_data.FamilyHeadName) || '-')}</td>
                  <td className="px-3 py-2">{String(asString(row.normalized_data.member_name) || asString(row.normalized_data.MemberName) || '-')}</td>
                  <td className="px-3 py-2">{String(asString(row.normalized_data.can_number) || asString(row.normalized_data.CANNumber) || '-')}</td>
                  <td className="px-3 py-2"><span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs">{row.status}</span></td>
                  <td className="px-3 py-2 text-slate-500">{row.errors.join('; ') || '-'}</td>
                </tr>
              ))}
              {!rows.length && !rowLoading && (
                <tr>
                  <td className="px-3 py-6 text-center text-slate-500" colSpan={7}>{selectedBatch ? 'No rows match the current filter.' : 'Upload/select a batch first.'}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function asString(value: unknown) {
  return typeof value === 'string' ? value : null;
}

function formatImportStatus(status: ImportBatchStatus) {
  if (status === 'uploaded') return 'Uploaded';
  if (status === 'validated') return 'Validated';
  if (status === 'committed') return 'Committed';
  return 'Failed';
}

function RoleAccessGuide() {
  return (
    <Card className="mb-4">
      <div className="mb-3">
        <div className="text-sm font-semibold text-slate-900">Role Access</div>
        <div className="mt-1 text-sm text-slate-500">Use this reference before assigning primary roles or module access.</div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {roleGuideItems.map((item) => (
          <div key={item.title} className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <div className="text-sm font-semibold text-slate-900">{item.title}</div>
            <div className="mt-1 text-sm leading-5 text-slate-600">{item.detail}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

const sensitiveFieldLabels: Array<{ key: keyof CanSensitiveAccess; label: string }> = [
  { key: 'pan', label: 'PAN' },
  { key: 'mobile', label: 'Mobile' },
  { key: 'email', label: 'Email' },
  { key: 'bank_account_number', label: 'Bank Account' },
];

const sensitiveRoleLabels: Array<{ key: keyof CanSensitiveAccessSettings; label: string }> = [
  { key: 'can_ops', label: 'CAN Ops' },
  { key: 'can_rm', label: 'CAN RM' },
];

function SensitiveAccessSettingsCard() {
  const [settings, setSettings] = useState<CanSensitiveAccessSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    usersApi.sensitiveAccess()
      .then((data) => {
        if (!cancelled) setSettings(data);
      })
      .catch((error) => {
        if (!cancelled) setMessage(friendlyError(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function update(role: keyof CanSensitiveAccessSettings, field: keyof CanSensitiveAccess, checked: boolean) {
    setSettings((current) => current ? ({
      ...current,
      [role]: { ...current[role], [field]: checked },
    }) : current);
  }

  async function save() {
    if (!settings) return;
    setSaving(true);
    setMessage('');
    try {
      const saved = await usersApi.updateSensitiveAccess(settings);
      setSettings(saved);
      setMessage('Sensitive access settings saved.');
    } catch (error) {
      setMessage(friendlyError(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="mb-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="inline-flex items-center gap-2 text-sm font-semibold text-slate-900"><ShieldCheck size={16} /> Sensitive Member Detail Access</div>
          <div className="mt-1 text-sm text-slate-500">Full values stay masked until users reveal them from member details.</div>
        </div>
        <button type="button" disabled={!settings || saving} onClick={save} className="rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
          {saving ? 'Saving...' : 'Save Access'}
        </button>
      </div>
      {message && <div className="mb-3 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{message}</div>}
      {loading && <div className="text-sm text-slate-500">Loading sensitive access settings...</div>}
      {settings && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Role</th>
                {sensitiveFieldLabels.map((field) => <th key={field.key} className="px-3 py-2">{field.label}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sensitiveRoleLabels.map((role) => (
                <tr key={role.key}>
                  <td className="px-3 py-3 font-semibold text-slate-900">{role.label}</td>
                  {sensitiveFieldLabels.map((field) => (
                    <td key={field.key} className="px-3 py-3">
                      <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                        <input
                          type="checkbox"
                          checked={settings[role.key][field.key]}
                          onChange={(event) => update(role.key, field.key, event.target.checked)}
                          className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        />
                        Enabled
                      </label>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
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

function HelpText({ children }: { children: React.ReactNode }) {
  return <div className="mt-1 text-xs leading-5 text-slate-500">{children}</div>;
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
