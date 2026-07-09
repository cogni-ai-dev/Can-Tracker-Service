import { HashRouter } from 'react-router-dom';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { App } from './App';
import type {
  CurrentUser,
  DashboardSummary,
  Family,
  ImportBatch,
  ImportRow,
  Member,
  TaskItem,
  TaskSummary,
  UserRecord,
} from './types';

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
  bank_accounts: [{
    id: 'bank-1',
    bank_name: 'HDFC',
    account_number_masked: 'bank account ending 1234',
    ifsc_code: 'HDFC0000001',
    is_primary: true,
    payeezz_mandate_status: 'Pending Approval',
    payeezz_amount: 10000,
    payeezz_start_date: '2026-01-01',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }],
  primary_bank_account: {
    id: 'bank-1',
    bank_name: 'HDFC',
    account_number_masked: 'bank account ending 1234',
    ifsc_code: 'HDFC0000001',
    is_primary: true,
    payeezz_mandate_status: 'Pending Approval',
    payeezz_amount: 10000,
    payeezz_start_date: '2026-01-01',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  effective_payeezz_mandate_status: 'Pending Approval',
  remarks: null,
  family_code: family.family_code,
  family_head_name: family.family_head_name,
  primary_rm: rm,
  updated_at: '2026-01-03T00:00:00Z',
  updated_by: rm,
  created_at: '2026-01-01T00:00:00Z',
};

const revealedMember: Member = {
  ...member,
  pan: 'ABCDE1234F',
  mobile: '9876543210',
  email: 'nisha@example.test',
  bank_accounts: member.bank_accounts.map((account) => ({ ...account, account_number: '001122334455' })),
  primary_bank_account: member.primary_bank_account ? { ...member.primary_bank_account, account_number: '001122334455' } : null,
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

const importBatch: ImportBatch = {
  id: 'import-batch-1',
  file_name: 'Can sample data import-ready.xlsx',
  file_sha256: 'hash-1',
  uploaded_by_user_id: 'user-can',
  status: 'validated',
  row_count: 2,
  valid_row_count: 1,
  error_row_count: 1,
  conflict_row_count: 0,
  committed_row_count: 0,
  warnings: ['One row has a duplicate nominee'],
  errors: [],
  created_at: '2026-01-02T00:00:00Z',
  committed_at: null,
};

const importRows: ImportRow[] = [
  {
    id: 'row-1',
    import_batch_id: importBatch.id,
    row_number: 2,
    raw_data: { CANNumber: 'CAN001' },
    normalized_data: {
      FamilyCode: 'FAM-001',
      FamilyHeadName: 'Shah Family',
      MemberName: 'Nisha Shah',
      CANNumber: 'CAN001',
    },
    status: 'valid',
    errors: [],
    family_id: family.id,
    member_id: member.id,
    created_at: '2026-01-02T00:00:00Z',
  },
  {
    id: 'row-2',
    import_batch_id: importBatch.id,
    row_number: 4,
    raw_data: { CANNumber: 'CAN002' },
    normalized_data: {
      FamilyHeadName: 'Shah Family',
      MemberName: 'Karan Patel',
      FamilyCode: 'FAM-001',
    },
    status: 'error',
    errors: ['Invalid PayEezz status'],
    family_id: null,
    member_id: null,
    created_at: '2026-01-02T00:00:00Z',
  },
];

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function installFetch(user: CurrentUser) {
  const calls: string[] = [];
  let activeImportBatch = importBatch;
  let activeImportRows = importRows;

  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), window.location.origin);
    const method = init?.method || 'GET';
    calls.push(`${method} ${url.pathname}${url.search}`);
    const filterStatus = url.searchParams.get('status');

    if (url.pathname === '/api/v1/auth/me') return json(user);
    if (url.pathname === '/api/v1/rms') return json([rm]);
    if (url.pathname === '/api/v1/dashboard/summary') return json(summary);
    if (url.pathname === '/api/v1/tasks/summary') return json(taskSummary);
    if (url.pathname === '/api/v1/tasks') return json({ items: [task], total: 1, limit: 500, offset: 0 });
    if (url.pathname === '/api/v1/families') return json({ items: [family], total: 1, limit: 500, offset: 0 });
    if (url.pathname === '/api/v1/members') return json({ items: [member], total: 1, limit: 500, offset: 0 });
    if (url.pathname === '/api/v1/users') return json([canUser, crmUser]);
    if (url.pathname === '/api/v1/imports' && method === 'GET') {
      if (filterStatus && filterStatus !== activeImportBatch.status) {
        return json({ items: [], total: 0, limit: 100, offset: 0 });
      }
      return json({ items: [activeImportBatch], total: 1, limit: 100, offset: 0 });
    }
    if (url.pathname === `/api/v1/imports/${activeImportBatch.id}`) {
      if (method === 'GET') return json(activeImportBatch);
    }
    if (url.pathname === `/api/v1/imports/${activeImportBatch.id}/rows` && method === 'GET') {
      const rows = filterStatus ? activeImportRows.filter((row) => row.status === filterStatus) : activeImportRows;
      return json({ items: rows, total: rows.length, limit: 1000, offset: 0 });
    }
    if (url.pathname === `/api/v1/imports/${activeImportBatch.id}/commit` && method === 'POST') {
      activeImportBatch = {
        ...activeImportBatch,
        status: 'committed',
        committed_row_count: activeImportBatch.valid_row_count,
        committed_at: '2026-01-02T00:10:00Z',
      };
      return json(activeImportBatch);
    }
    if (url.pathname === '/api/v1/imports/mfu-template/upload' && method === 'POST') {
      activeImportBatch = {
        ...importBatch,
        id: 'upload-batch',
        file_name: 'sample-upload.xlsx',
        uploaded_by_user_id: user.id,
        status: 'validated',
      };
      return json(activeImportBatch, 201);
    }
    if (url.pathname === '/api/v1/admin/can-sensitive-access') {
      if (method === 'PATCH') {
        return json(JSON.parse(String(init?.body || '{}')));
      }
      return json({
        can_ops: { pan: true, mobile: true, email: true, bank_account_number: true },
        can_rm: { pan: false, mobile: false, email: false, bank_account_number: false },
      });
    }
    if (url.pathname === `/api/v1/members/${member.id}` && url.searchParams.get('include_sensitive') === 'true') {
      return json(revealedMember);
    }
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
    expect(screen.getByText('HDFC')).toBeInTheDocument();
    expect(screen.getByText('Primary')).toBeInTheDocument();
    expect(screen.getByText('bank account ending 1234 | HDFC0000001')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete Family' })).toBeInTheDocument();
  });

  it('opens member details masked first and reveals sensitive values on request', async () => {
    const user = userEvent.setup();
    const calls = renderApp('#/compliance/families/family-1', canUser);

    expect(await screen.findByText('Shah Family')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'View Details' }));

    const dialog = screen.getByRole('dialog', { name: 'Member Details' });
    expect(within(dialog).getByText('ABCDE****F')).toBeInTheDocument();
    expect(within(dialog).getByText('******3210')).toBeInTheDocument();
    expect(within(dialog).getByText('n***@example.test')).toBeInTheDocument();
    expect(within(dialog).getByText('bank account ending 1234')).toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: 'Reveal Sensitive Data' }));

    expect(await within(dialog).findByText('ABCDE1234F')).toBeInTheDocument();
    expect(within(dialog).getByText('9876543210')).toBeInTheDocument();
    expect(within(dialog).getByText('nisha@example.test')).toBeInTheDocument();
    expect(within(dialog).getByText('001122334455')).toBeInTheDocument();
    expect(calls).toContain('GET /api/v1/members/member-1?include_sensitive=true');
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

  it('renders MFU Import panel for import-capable users', async () => {
    renderApp('#/admin/imports', canOpsUser);

    expect(await screen.findByRole('heading', { name: 'MFU Import' })).toBeInTheDocument();
    expect(screen.getAllByText('Can sample data import-ready.xlsx').length).toBeGreaterThan(0);
    expect(screen.getByText('Upload New Template')).toBeInTheDocument();
    expect(screen.getByText(/Valid: 1/i)).toBeInTheDocument();
  });

  it('uploads import workbook, filters rows, and commits validated batch', async () => {
    const user = userEvent.setup();
    const calls = renderApp('#/admin/imports', canOpsUser);
    expect(await screen.findByRole('heading', { name: 'MFU Import' })).toBeInTheDocument();

    const fileInput = screen.getByLabelText('Select CSV / XLSX');
    const file = new File(['sample-data'], 'Can sample.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    await user.upload(fileInput, file);

    await user.click(screen.getByRole('button', { name: 'Upload' }));
    await waitFor(() => expect(calls).toContain('POST /api/v1/imports/mfu-template/upload'));
    expect(await screen.findByText('Upload complete. Review validated rows before committing.')).toBeInTheDocument();
    const rows = await screen.findAllByText('sample-upload.xlsx');
    expect(rows.length).toBeGreaterThan(0);

    await user.selectOptions(screen.getByLabelText('Filter rows by status'), 'error');
    expect(await screen.findByText('Invalid PayEezz status')).toBeInTheDocument();

    const commitButton = await screen.findByRole('button', { name: 'Commit Valid Rows' });
    expect(commitButton).toBeEnabled();
    await user.click(commitButton);
    await waitFor(() => expect(calls.some((call) => call.includes('/api/v1/imports/') && call.includes('/commit') && call.startsWith('POST '))).toBe(true));
    expect(await screen.findByText('Batch sample-upload.xlsx committed successfully.')).toBeInTheDocument();
  });

  it('keeps users without import role out of admin import route', async () => {
    renderApp('#/admin/imports', rm);

    expect(await screen.findByRole('heading', { name: 'Compliance Dashboard' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'MFU Import' })).not.toBeInTheDocument();
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
    expect(await screen.findByText('Sensitive Member Detail Access')).toBeInTheDocument();
  });

  it('lets CAN Admin update role-level sensitive access settings', async () => {
    const user = userEvent.setup();
    const calls = renderApp('#/admin/users', canUser);

    expect(await screen.findByText('Sensitive Member Detail Access')).toBeInTheDocument();
    const rmPan = screen.getAllByRole('checkbox')[4];
    await user.click(rmPan);
    await user.click(screen.getByRole('button', { name: 'Save Access' }));

    await waitFor(() => expect(calls).toContain('PATCH /api/v1/admin/can-sensitive-access'));
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
