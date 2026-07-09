import { describe, expect, it, vi } from 'vitest';

import { authApi, complianceApi, importsApi, usersApi } from './api';

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

  it('calls import endpoints and sends multipart uploads', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), init });
      if (init?.method === 'POST') {
        const body = init.body;
        if (body instanceof FormData) {
          const keys = [...body.keys()];
          expect(keys).toContain('file');
          return json({ id: 'import-1', file_name: 'upload.xlsx', file_sha256: 'hash', uploaded_by_user_id: 'user-1', status: 'uploaded', row_count: 0, valid_row_count: 0, error_row_count: 0, conflict_row_count: 0, committed_row_count: 0, warnings: [], errors: [], created_at: '2026-01-01T00:00:00Z', committed_at: null });
        }
        return json({});
      }
      return json({ items: [{ id: 'batch-1', file_name: 'batch.xlsx', file_sha256: 'hash', uploaded_by_user_id: 'user-1', status: 'validated', row_count: 0, valid_row_count: 0, error_row_count: 0, conflict_row_count: 0, committed_row_count: 0, warnings: [], errors: [], created_at: '2026-01-01T00:00:00Z', committed_at: null }], total: 1, limit: 100, offset: 0 });
    }));

    const file = new File(['sample'], 'sample.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

    await importsApi.listBatches({ status: 'validated', limit: 10, offset: 0 });
    await importsApi.getBatch('batch-1');
    await importsApi.listRows('batch-1', { status: 'valid', limit: 10, offset: 0 });
    await importsApi.commitBatch('batch-1');
    await importsApi.uploadTemplate(file);

    const methodsAndPaths = calls.map((call) => `${call.init?.method || 'GET'} ${new URL(call.url).pathname}${new URL(call.url).search}`);
    expect(methodsAndPaths).toEqual([
      'GET /api/v1/imports?status=validated&limit=10&offset=0',
      'GET /api/v1/imports/batch-1',
      'GET /api/v1/imports/batch-1/rows?status=valid&limit=10&offset=0',
      'POST /api/v1/imports/batch-1/commit',
      'POST /api/v1/imports/mfu-template/upload',
    ]);
    const uploadCall = calls[4];
    expect(uploadCall.init?.headers).toEqual({});
    expect(uploadCall.init?.body).toBeInstanceOf(FormData);
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
