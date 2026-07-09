import { HashRouter } from 'react-router-dom';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { App } from './App';
import type { CurrentUser, DashboardSummary, Family, Member, TaskItem, TaskSummary, UserRecord } from './types';

const rm: UserRecord = {
  id: 'rm-1',
  name: 'Ria Manager',
  email: 'ria@example.test',
  role: 'rm',
  memberships: [{ module_code: 'can_compliance', role: 'can_rm', is_active: true }],
  module_codes: ['can_compliance'],
  is_platform_admin: false,
  is_active: true,
  last_login_at: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const canUser: CurrentUser = {
  ...rm,
  id: 'user-can',
  name: 'CAN Admin',
  email: 'can.admin@example.test',
  role: 'admin',
  memberships: [{ module_code: 'can_compliance', role: 'can_admin', is_active: true }],
  module_codes: ['can_compliance'],
  is_platform_admin: false,
};

const canOpsUser: CurrentUser = {
  ...rm,
  id: 'user-can-ops',
  name: 'CAN Ops',
  email: 'can.ops@example.test',
  role: 'ops',
  memberships: [{ module_code: 'can_compliance', role: 'can_ops', is_active: true }],
  module_codes: ['can_compliance'],
  is_platform_admin: false,
};

const crmUser: CurrentUser = {
  ...rm,
  id: 'user-crm',
  name: 'CRM User',
  email: 'crm@example.test',
  role: 'management',
  memberships: [{ module_code: 'client_crm', role: 'crm_viewer', is_active: true }],
  module_codes: ['client_crm'],
};

const summary: DashboardSummary = {
  total_clients: 1,
  total_families: 1,
  kyc_verified: 0,
  kyc_pending_rekyc: 1,
  kyc_not_started: 0,
  kyc_pending: 1,
  kyc_verified_pct: 0,
  kyc_pending_pct: 100,
  payeezz_approved: 0,
  payeezz_pending_approval: 1,
  payeezz_not_started: 0,
  payeezz_pending: 1,
  payeezz_approved_pct: 0,
  payeezz_pending_pct: 100,
  mobile_verified: 0,
  mobile_pending_verification: 1,
  email_verified: 0,
  email_pending_verification: 1,
  nominee_verified: 0,
  nominee_pending_verification: 1,
  updated_at: '2026-01-01T00:00:00Z',
};

const family: Family = {
  id: 'family-1',
  family_code: 'FAM-001',
  family_head_name: 'Shah Family',
  primary_rm: rm,
  total_members: 1,
  total_cans: 1,
  last_updated_at: '2026-01-02T00:00:00Z',
  remarks: null,
  kyc_completion: { count: 0, percentage: 0 },
  payeezz_completion: { count: 0, percentage: 0 },
  mobile_verification: { count: 0, percentage: 0 },
  email_verification: { count: 0, percentage: 0 },
  nominee_verification: { count: 0, percentage: 0 },
  kyc_completion_pct: 0,
  payeezz_completion_pct: 0,
  mobile_verification_pct: 0,
  email_verification_pct: 0,
  nominee_verification_pct: 0,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
};

const unassignedFamily: Family = {
  ...family,
  id: 'family-unassigned',
  family_code: 'FAM-UNASSIGNED',
  family_head_name: 'Unassigned Family',
  primary_rm: null,
};

const member: Member = {
  id: 'member-1',
  family_id: family.id,
  name: 'Nisha Shah',
  can_number: 'CAN001',
  can_status: 'Available',
  pan_masked: 'ABCDE****F',
  date_of_birth: null,
  kyc_status: 'Pending Re-KYC',
  mobile_masked: '******3210',
  mobile_verification_status: 'Pending Verification',
  email_masked: 'n***@example.test',
  email_verification_status: 'Pending Verification',
  nominee_verification_status: 'Pending Verification',
  bank_name: 'HDFC',
  bank_account_number_masked: '****1234',
  ifsc_code: 'HDFC0000001',
  payeezz_mandate_status: 'Pending Approval',
  payeezz_amount: 10000,
  payeezz_start_date: '2026-01-01',
  remarks: null,
  family_code: family.family_code,
  family_head_name: family.family_head_name,
  primary_rm: rm,
  updated_at: '2026-01-03T00:00:00Z',
  updated_by: rm,
  created_at: '2026-01-01T00:00:00Z',
};

const unassignedMember: Member = {
  ...member,
  id: 'member-unassigned',
  family_id: unassignedFamily.id,
  family_code: unassignedFamily.family_code,
  family_head_name: unassignedFamily.family_head_name,
  primary_rm: null,
};

const taskSummary: TaskSummary = { total_tasks: 1, kyc: 1, payeezz: 0, mobile: 0, email: 0, nominee: 0 };

const task: TaskItem = {
  type: 'kyc',
  priority: 'high',
  member_id: member.id,
  member_name: member.name,
  family_id: family.id,
  family_head_name: family.family_head_name,
  family_code: family.family_code,
  rm_id: rm.id,
  rm_name: rm.name,
  can_number_masked: 'CAN***',
  description: 'KYC pending for Nisha Shah',
  label: 'KYC Pending',
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function installFetch(user: CurrentUser) {
  const calls: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), window.location.origin);
    const method = init?.method || 'GET';
    calls.push(`${method} ${url.pathname}${url.search}`);

    if (url.pathname === '/api/v1/auth/me') return json(user);
    if (url.pathname === '/api/v1/rms') return json([rm]);
    if (url.pathname === '/api/v1/dashboard/summary') return json(summary);
    if (url.pathname === '/api/v1/tasks/summary') return json(taskSummary);
    if (url.pathname === '/api/v1/tasks') return json({ items: [task], total: 1, limit: 500, offset: 0 });
    if (url.pathname === '/api/v1/families') return json({ items: [family], total: 1, limit: 500, offset: 0 });
    if (url.pathname === '/api/v1/members') return json({ items: [member], total: 1, limit: 500, offset: 0 });
    if (url.pathname === '/api/v1/users') return json([canUser, crmUser]);
    if (url.pathname === `/api/v1/dashboard/families/${family.id}`) {
      return json({ ...family, number_of_members: 1, members: [member] });
    }
    if (url.pathname === `/api/v1/dashboard/families/${unassignedFamily.id}`) {
      return json({ ...unassignedFamily, number_of_members: 1, members: [unassignedMember] });
    }
    if (method === 'DELETE' && (
      url.pathname === `/api/v1/families/${family.id}`
      || url.pathname === `/api/v1/members/${member.id}`
      || url.pathname === `/api/v1/users/${crmUser.id}`
    )) {
      return new Response(null, { status: 204 });
    }

    return json({ error: { message: `Unexpected ${url.pathname}` } }, 500);
  }));
  return calls;
}

function renderApp(hash: string, user: CurrentUser) {
  window.location.hash = hash;
  const calls = installFetch(user);
  render(
    <HashRouter>
      <App />
    </HashRouter>,
  );
  return calls;
}

describe('MFU Operations Portal shell', () => {
  it('shows CAN Compliance navigation and real dashboard content for CAN users', async () => {
    renderApp('#/compliance/dashboard', canUser);

    expect(await screen.findByRole('heading', { name: 'Compliance Dashboard' })).toBeInTheDocument();
    expect(screen.getAllByText('Families').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Pending Tasks').length).toBeGreaterThan(0);
    expect(screen.getByText('Total Clients')).toBeInTheDocument();
    expect(screen.queryByText('Control Centre')).not.toBeInTheDocument();
    expect(screen.queryByText('Backend Contract')).not.toBeInTheDocument();
  });

  it('shows Client CRM and does not call unimplemented CRM backend endpoints for CRM-only users', async () => {
    const calls = renderApp('#/crm/control-centre', crmUser);

    expect(await screen.findByRole('heading', { name: 'Client CRM' })).toBeInTheDocument();
    expect(screen.getAllByText('Control Centre').length).toBeGreaterThan(0);
    expect(screen.queryByText('Compliance')).not.toBeInTheDocument();
    expect(calls.some((call) => call.includes('/api/v1/crm'))).toBe(false);
  });

  it('renders real CAN status and task pages without placeholder endpoint cards', async () => {
    renderApp('#/compliance/kyc', canUser);

    expect(await screen.findByRole('heading', { name: 'KYC Status' })).toBeInTheDocument();
    expect(screen.getByText('KYC Verified')).toBeInTheDocument();
    expect(screen.getByText('Nisha Shah')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Update' })).toBeInTheDocument();
    expect(screen.queryByText('Summary Fields Loaded')).not.toBeInTheDocument();
    expect(screen.queryByText('Task Summary')).not.toBeInTheDocument();
  });

  it('exposes member create actions from family detail', async () => {
    renderApp('#/compliance/families/family-1', canUser);

    expect(await screen.findByRole('heading', { name: 'Family Detail' })).toBeInTheDocument();
    expect(await screen.findByText('Shah Family')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Add Member' }).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete Family' })).toBeInTheDocument();
  });

  it('requires typed confirmation before deleting a family', async () => {
    const user = userEvent.setup();
    const calls = renderApp('#/compliance/families/family-1', canUser);

    expect(await screen.findByText('Shah Family')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete Family' }));

    const dialog = screen.getByRole('dialog', { name: 'Delete Family' });
    expect(within(dialog).getByText(/also delete its members/i)).toBeInTheDocument();
    const confirmButton = within(dialog).getByRole('button', { name: 'Delete Family' });
    expect(confirmButton).toBeDisabled();

    await user.type(within(dialog).getByLabelText('Type CONFIRM to continue'), 'CONFIRM');
    expect(confirmButton).toBeEnabled();
    await user.click(confirmButton);

    await waitFor(() => expect(calls).toContain('DELETE /api/v1/families/family-1'));
  });

  it('requires typed confirmation before deleting a member', async () => {
    const user = userEvent.setup();
    const calls = renderApp('#/compliance/families/family-1', canUser);

    expect(await screen.findByText('Shah Family')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete' }));

    const dialog = screen.getByRole('dialog', { name: 'Delete Member' });
    expect(within(dialog).getByText(/Delete member Nisha Shah/i)).toBeInTheDocument();
    const confirmButton = within(dialog).getByRole('button', { name: 'Delete Member' });
    expect(confirmButton).toBeDisabled();

    await user.type(within(dialog).getByLabelText('Type CONFIRM to continue'), 'CONFIRM');
    expect(confirmButton).toBeEnabled();
    await user.click(confirmButton);

    await waitFor(() => expect(calls).toContain('DELETE /api/v1/members/member-1'));
  });

  it('hides delete actions for CAN Ops users', async () => {
    renderApp('#/compliance/families/family-1', canOpsUser);

    expect(await screen.findByRole('heading', { name: 'Family Detail' })).toBeInTheDocument();
    expect(await screen.findByText('Shah Family')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Add Member' }).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete Family' })).not.toBeInTheDocument();
  });

  it('renders unassigned family details without an RM', async () => {
    renderApp('#/compliance/families/family-unassigned', canUser);

    expect(await screen.findByText('Unassigned Family')).toBeInTheDocument();
    expect(screen.getByText('FAM-UNASSIGNED | RM: Unassigned')).toBeInTheDocument();
    expect(screen.getByText('Nisha Shah')).toBeInTheDocument();
  });

  it('shows role access guidance in admin user management', async () => {
    renderApp('#/admin/users', canUser);

    expect(await screen.findByRole('heading', { name: 'Users & Access' })).toBeInTheDocument();
    expect(screen.getByText('Role Access')).toBeInTheDocument();
    expect(screen.getByText('Full CAN access, user management, audit logs, imports, and sensitive values.')).toBeInTheDocument();
    expect(screen.getByText('Create, edit, import, and report across CAN records. No delete, user management, or audit logs.')).toBeInTheDocument();
    expect(screen.getByText('Can manage CRM users and CRM module access.')).toBeInTheDocument();
  });

  it('requires typed confirmation before deactivating a user', async () => {
    const user = userEvent.setup();
    const calls = renderApp('#/admin/users', canUser);

    expect(await screen.findByRole('heading', { name: 'Users & Access' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Deactivate' }));

    const dialog = screen.getByRole('dialog', { name: 'Deactivate User' });
    expect(within(dialog).getByText(/lose access until an admin reactivates/i)).toBeInTheDocument();
    const confirmButton = within(dialog).getByRole('button', { name: 'Deactivate User' });
    expect(confirmButton).toBeDisabled();

    await user.type(within(dialog).getByLabelText('Type CONFIRM to continue'), 'CONFIRM');
    expect(confirmButton).toBeEnabled();
    await user.click(confirmButton);

    await waitFor(() => expect(calls).toContain('DELETE /api/v1/users/user-crm'));
  });
});
