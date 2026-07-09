import type {
  CurrentUser,
  DashboardSummary,
  Family,
  FamilyDashboard,
  FamilyPayload,
  ListResponse,
  Member,
  MemberPayload,
  ReportExportFormat,
  ReportPreview,
  ReportType,
  TaskItem,
  TaskSummary,
  TaskType,
  UserPayload,
  UserRecord,
} from '../types';

const API_BASE = '/api/v1';

type RequestOptions = {
  params?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  signal?: AbortSignal;
};

function buildUrl(path: string, params: RequestOptions['params'] = {}) {
  const url = new URL(API_BASE + path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });
  return url;
}

export class ApiError extends Error {
  status?: number;
  payload?: unknown;

  constructor(message: string, status?: number, payload?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(buildUrl(path, options.params), {
    method,
    credentials: 'include',
    headers: options.body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json().catch(() => ({}))
    : await response.text();
  if (!response.ok) {
    const message = typeof payload === 'object' && payload !== null
      ? (payload as { error?: { message?: string }; detail?: string }).error?.message
        || (payload as { detail?: string }).detail
        || response.statusText
        || 'Request failed'
      : response.statusText || 'Request failed';
    throw new ApiError(message, response.status, payload);
  }
  return payload as T;
}

async function download(path: string, params: RequestOptions['params'] = {}) {
  const response = await fetch(buildUrl(path, params), { credentials: 'include' });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message = payload?.error?.message || payload?.detail || response.statusText || 'Download failed';
    throw new ApiError(message, response.status, payload);
  }
  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') || '';
  const filename = disposition.match(/filename="?([^"]+)"?/i)?.[1] || 'report-download';
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  get: <T>(path: string, params?: RequestOptions['params'], options: Pick<RequestOptions, 'signal'> = {}) => request<T>('GET', path, { params, ...options }),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, { body }),
  delete: <T>(path: string) => request<T>('DELETE', path),
  download,
};

export const authApi = {
  me: () => api.get<CurrentUser>('/auth/me'),
  login: (email: string, password: string) =>
    api.post<{ user: CurrentUser }>('/auth/login', { email: email.trim().toLowerCase(), password }),
  logout: () => api.post<void>('/auth/logout'),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post<void>('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),
};

export const complianceApi = {
  dashboardSummary: (params?: { rm_id?: string }) => api.get<DashboardSummary>('/dashboard/summary', params),
  familyDashboard: (familyId: string) => api.get<FamilyDashboard>(`/dashboard/families/${familyId}`),
  families: (params?: {
    q?: string;
    rm_id?: string;
    status_filter?: string;
    can_status?: string;
    kyc_status?: string;
    payeezz_mandate_status?: string;
    mobile_verification_status?: string;
    email_verification_status?: string;
    nominee_verification_status?: string;
    limit?: number;
    offset?: number;
    sort?: string;
  }) => api.get<ListResponse<Family>>('/families', params),
  createFamily: (payload: FamilyPayload) => api.post<Family>('/families', payload),
  updateFamily: (familyId: string, payload: Partial<FamilyPayload>) => api.patch<Family>(`/families/${familyId}`, payload),
  deleteFamily: (familyId: string) => api.delete<void>(`/families/${familyId}`),
  members: (params?: {
    q?: string;
    family_id?: string;
    rm_id?: string;
    can_status?: string;
    kyc_status?: string;
    payeezz_mandate_status?: string;
    mobile_verification_status?: string;
    email_verification_status?: string;
    nominee_verification_status?: string;
    limit?: number;
    offset?: number;
  }) => api.get<ListResponse<Member>>('/members', params),
  member: (memberId: string) => api.get<Member>(`/members/${memberId}`),
  createMember: (familyId: string, payload: MemberPayload) => api.post<Member>(`/families/${familyId}/members`, payload),
  updateMember: (memberId: string, payload: Partial<MemberPayload>) => api.patch<Member>(`/members/${memberId}`, payload),
  deleteMember: (memberId: string) => api.delete<void>(`/members/${memberId}`),
  tasks: (params?: { type?: TaskType | 'all'; rm_id?: string; family_id?: string; q?: string; priority?: string; limit?: number; offset?: number }) => {
    const normalized = { ...params };
    if (normalized.type === 'all') delete normalized.type;
    return api.get<ListResponse<TaskItem>>('/tasks', normalized);
  },
  tasksSummary: (params?: { rm_id?: string; limit?: number }) => api.get<TaskSummary>('/tasks/summary', params),
  reportPreview: (type: ReportType, params?: { rm_id?: string; family_id?: string; limit?: number; offset?: number }) =>
    api.get<ReportPreview>(`/reports/${type}/preview`, params),
  exportReport: (type: ReportType, format: ReportExportFormat, params?: { rm_id?: string; family_id?: string }) =>
    api.download(`/reports/${type}/export`, { ...params, format }),
  rms: () => api.get<UserRecord[]>('/rms'),
};

export const usersApi = {
  list: (params?: { include_inactive?: boolean }) => api.get<UserRecord[]>('/users', params),
  create: (payload: UserPayload) => api.post<UserRecord>('/users', payload),
  update: (userId: string, payload: UserPayload) => api.patch<UserRecord>(`/users/${userId}`, payload),
  deactivate: (userId: string) => api.delete<void>(`/users/${userId}`),
};
