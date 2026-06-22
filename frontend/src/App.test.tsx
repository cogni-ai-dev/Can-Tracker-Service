import { HashRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
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
  kyc_validated: 0,
  kyc_registered: 1,
  kyc_no_kyc: 0,
  kyc_pending: 1,
  kyc_validated_pct: 0,
  kyc_pending_pct: 100,
  payeezz_accepted: 0,
  payeezz_sent_for_approval: 1,
  payeezz_not_available: 0,
  payeezz_pending: 1,
  payeezz_accepted_pct: 0,
  payeezz_pending_pct: 100,
  mobile_verified: 0,
  mobile_not_verified: 1,
  email_verified: 0,
  email_not_verified: 1,
  nominee_verified: 0,
  nominee_not_verified: 1,
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

const member: Member = {
  id: 'member-1',
  family_id: family.id,
  name: 'Nisha Shah',
  can_number: 'CAN001',
  pan_masked: 'ABCDE****F',
  date_of_birth: null,
  kyc_status: 'Registered',
  mobile_masked: '******3210',
  mobile_status: 'Not Verified',
  email_masked: 'n***@example.test',
  email_status: 'Not Verified',
  nominee_status: 'Not Verified',
  bank_name: 'HDFC',
  bank_account_number_masked: '****1234',
  ifsc_code: 'HDFC0000001',
  payeezz_status: 'Sent for Approval',
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
    expect(screen.getByText('KYC Validated')).toBeInTheDocument();
    expect(screen.getByText('Nisha Shah')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Update' })).toBeInTheDocument();
    expect(screen.queryByText('Summary Fields Loaded')).not.toBeInTheDocument();
    expect(screen.queryByText('Task Summary')).not.toBeInTheDocument();
  });

  it('exposes member create actions from family detail', async () => {
    renderApp('#/compliance/families/family-1', canUser);

    expect(await screen.findByRole('heading', { name: 'Family Detail' })).toBeInTheDocument();
    expect(screen.getByText('Shah Family')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Add Member' }).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
  });

  it('shows role access guidance in admin user management', async () => {
    renderApp('#/admin/users', canUser);

    expect(await screen.findByRole('heading', { name: 'Users & Access' })).toBeInTheDocument();
    expect(screen.getByText('Role Access')).toBeInTheDocument();
    expect(screen.getByText('Full CAN access, user management, audit logs, imports, and sensitive values.')).toBeInTheDocument();
    expect(screen.getByText('Create, edit, delete, import, and report across CAN records. No user management or audit logs.')).toBeInTheDocument();
    expect(screen.getByText('Can manage CRM users and CRM module access.')).toBeInTheDocument();
  });
});
