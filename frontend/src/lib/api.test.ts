import { describe, expect, it, vi } from 'vitest';

import { authApi, complianceApi, usersApi } from './api';

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('API adapters', () => {
  it('uses existing auth and compliance endpoints for writes and reads', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), init });
      return json({ id: 'ok', items: [], total: 0, limit: 10, offset: 0 });
    }));

    await authApi.changePassword('old-password', 'new-password');
    await complianceApi.createFamily({ family_code: 'FAM-001', family_head_name: 'Shah Family', primary_rm_id: 'rm-1' });
    await complianceApi.updateMember('member-1', { remarks: 'Called client.' });
    await complianceApi.deleteMember('member-1');
    await usersApi.update('user-1', { memberships: [{ module_code: 'client_crm', role: 'crm_viewer', is_active: true }] });

    expect(calls.map((call) => `${call.init?.method || 'GET'} ${new URL(call.url).pathname}`)).toEqual([
      'POST /api/v1/auth/change-password',
      'POST /api/v1/families',
      'PATCH /api/v1/members/member-1',
      'DELETE /api/v1/members/member-1',
      'PATCH /api/v1/users/user-1',
    ]);
    expect(calls.some((call) => call.url.includes('/api/v1/crm'))).toBe(false);
  });

  it('downloads report blobs through existing report export endpoints', async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    const createObjectURL = vi.fn(() => 'blob:report');
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', { value: createObjectURL, configurable: true });
    Object.defineProperty(URL, 'revokeObjectURL', { value: revokeObjectURL, configurable: true });
    const calls: string[] = [];

    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      calls.push(`${url.pathname}${url.search}`);
      return new Response(new Blob(['a,b\n1,2']), {
        status: 200,
        headers: { 'content-disposition': 'attachment; filename="kyc.csv"' },
      });
    }));

    await complianceApi.exportReport('kyc_pending', 'csv');

    expect(calls).toEqual(['/api/v1/reports/kyc_pending/export?format=csv']);
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:report');
  });
});
