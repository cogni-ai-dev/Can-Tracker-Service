export type ModuleCode = 'can_compliance' | 'client_crm';

export type UserRole = 'admin' | 'ops' | 'rm' | 'management';

export type ModuleRole =
  | 'can_admin'
  | 'can_ops'
  | 'can_rm'
  | 'can_management'
  | 'crm_admin'
  | 'crm_ops'
  | 'crm_relationship_manager'
  | 'crm_viewer';

export type UserMembership = {
  module_code: ModuleCode;
  role: ModuleRole;
  is_active: boolean;
};

export type CanSensitiveAccess = {
  pan: boolean;
  mobile: boolean;
  email: boolean;
  bank_account_number: boolean;
};

export type CanSensitiveAccessSettings = {
  can_ops: CanSensitiveAccess;
  can_rm: CanSensitiveAccess;
};

export type CurrentUser = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  memberships: UserMembership[];
  module_codes: ModuleCode[];
  can_sensitive_access?: CanSensitiveAccess;
  is_platform_admin: boolean;
  is_active: boolean;
  last_login_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type UserRecord = CurrentUser & {
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
};

export type UserSummary = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
};

export type CountPercentage = {
  count: number;
  percentage: number;
};

export type CanStatus = 'Pending' | 'Available';
export type KycStatus = 'Not Started' | 'Pending Re-KYC' | 'Verified';
export type VerificationStatus = 'Pending Verification' | 'Verified';
export type PayeezzStatus = 'Not Started' | 'Pending Approval' | 'Approved';
export type TaskType = 'kyc' | 'payeezz' | 'mobile' | 'email' | 'nominee';
export type TaskPriority = 'high' | 'medium' | 'low';
export type ReportType =
  | 'kyc_pending'
  | 'payeezz_pending'
  | 'contact_pending'
  | 'family_compliance'
  | 'rm_tasks'
  | 'full';
export type ReportExportFormat = 'csv' | 'xlsx' | 'pdf';

export type ImportBatchStatus = 'uploaded' | 'validated' | 'committed' | 'failed';
export type ImportRowStatus = 'valid' | 'error' | 'conflict' | 'committed' | 'skipped';

export type ImportBatch = {
  id: string;
  file_name: string;
  file_sha256: string;
  uploaded_by_user_id: string;
  status: ImportBatchStatus;
  row_count: number;
  valid_row_count: number;
  error_row_count: number;
  conflict_row_count: number;
  committed_row_count: number;
  warnings: string[];
  errors: string[];
  created_at: string;
  committed_at: string | null;
};

export type ImportBatchListResponse = {
  items: ImportBatch[];
  total: number;
  limit: number;
  offset: number;
};

export type ImportRow = {
  id: string;
  import_batch_id: string;
  row_number: number;
  raw_data: Record<string, unknown>;
  normalized_data: Record<string, unknown>;
  status: ImportRowStatus;
  errors: string[];
  family_id: string | null;
  member_id: string | null;
  created_at: string;
};

export type ImportRowListResponse = {
  items: ImportRow[];
  total: number;
  limit: number;
  offset: number;
};

export type DashboardSummary = {
  total_clients: number;
  total_families: number;
  kyc_verified: number;
  kyc_pending_rekyc: number;
  kyc_not_started: number;
  kyc_pending: number;
  kyc_verified_pct: number;
  kyc_pending_pct: number;
  payeezz_approved: number;
  payeezz_pending_approval: number;
  payeezz_not_started: number;
  payeezz_pending: number;
  payeezz_approved_pct: number;
  payeezz_pending_pct: number;
  mobile_verified: number;
  mobile_pending_verification: number;
  email_verified: number;
  email_pending_verification: number;
  nominee_verified: number;
  nominee_pending_verification: number;
  updated_at: string | null;
};

export type Family = {
  id: string;
  family_code: string;
  family_head_name: string;
  primary_rm: UserSummary | null;
  total_members: number;
  total_cans: number;
  last_updated_at: string;
  remarks: string | null;
  kyc_completion: CountPercentage;
  payeezz_completion: CountPercentage;
  mobile_verification: CountPercentage;
  email_verification: CountPercentage;
  nominee_verification: CountPercentage;
  kyc_completion_pct: number;
  payeezz_completion_pct: number;
  mobile_verification_pct: number;
  email_verification_pct: number;
  nominee_verification_pct: number;
  created_at: string;
  updated_at: string;
};

export type MemberBankAccount = {
  id: string;
  bank_name: string;
  account_number_masked: string;
  account_number?: string | null;
  ifsc_code: string | null;
  is_primary: boolean;
  payeezz_mandate_status: PayeezzStatus;
  payeezz_amount: string | number | null;
  payeezz_start_date: string | null;
  created_at: string;
  updated_at: string;
};

export type Member = {
  id: string;
  family_id: string;
  name: string;
  can_number: string | null;
  can_status: CanStatus;
  pan_masked: string | null;
  pan?: string | null;
  date_of_birth: string | null;
  kyc_status: KycStatus;
  mobile_masked: string | null;
  mobile?: string | null;
  mobile_verification_status: VerificationStatus;
  email_masked: string | null;
  email?: string | null;
  email_verification_status: VerificationStatus;
  nominee_name?: string | null;
  nominee_verification_status: VerificationStatus;
  bank_accounts: MemberBankAccount[];
  primary_bank_account: MemberBankAccount | null;
  effective_payeezz_mandate_status: PayeezzStatus;
  remarks: string | null;
  family_code: string;
  family_head_name: string;
  primary_rm: UserSummary | null;
  updated_at: string;
  updated_by: UserSummary | null;
  created_at: string;
};

export type FamilyDashboard = {
  id: string;
  family_code: string;
  family_head_name: string;
  primary_rm: UserSummary | null;
  remarks: string | null;
  last_updated_at: string;
  number_of_members: number;
  total_cans: number;
  kyc_completion_pct: number;
  mobile_verification_pct: number;
  email_verification_pct: number;
  nominee_verification_pct: number;
  payeezz_completion_pct: number;
  members: Member[];
};

export type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type TaskItem = {
  type: TaskType;
  priority: TaskPriority;
  member_id: string;
  member_name: string;
  family_id: string;
  family_head_name: string;
  family_code: string;
  rm_id: string | null;
  rm_name: string;
  can_number_masked: string;
  description: string;
  label: string;
};

export type TaskSummary = {
  total_tasks: number;
  kyc: number;
  payeezz: number;
  mobile: number;
  email: number;
  nominee: number;
};

export type ReportPreview = {
  report_type: ReportType;
  title: string;
  columns: Array<{ key: string; label: string }>;
  items: Array<Record<string, unknown>>;
  total: number;
  limit: number;
  offset: number;
  filters: Record<string, unknown>;
};

export type FamilyPayload = {
  family_code?: string | null;
  family_head_name: string;
  primary_rm_id?: string | null;
  remarks?: string | null;
};

export type MemberPayload = {
  name: string;
  can_number?: string | null;
  can_status?: CanStatus | null;
  pan?: string | null;
  date_of_birth?: string | null;
  kyc_status: KycStatus;
  mobile?: string | null;
  mobile_verification_status: VerificationStatus;
  email?: string | null;
  email_verification_status: VerificationStatus;
  nominee_name?: string | null;
  nominee_verification_status: VerificationStatus;
  remarks?: string | null;
};

export type MemberBankAccountPayload = {
  bank_name: string;
  account_number?: string | null;
  ifsc_code?: string | null;
  is_primary?: boolean;
  payeezz_mandate_status: PayeezzStatus;
  payeezz_amount?: number | null;
  payeezz_start_date?: string | null;
};

export type UserPayload = {
  name?: string;
  email?: string;
  password?: string;
  role?: UserRole;
  memberships?: UserMembership[];
  is_active?: boolean;
};

export type CrmStatus = 'Open' | 'In Progress' | 'Pending' | 'Completed' | 'Closed' | 'Rejected';

export type CrmBase = {
  id: string;
  owner: string;
  status: string;
  notes: string;
  createdAt: string;
  updatedAt: string;
  familyId?: string;
  memberId?: string;
  clientId?: string;
};

export type CrmTransaction = CrmBase & {
  clientName: string;
  folioNumber: string;
  amc: string;
  schemeName: string;
  transactionType: string;
  transactionDate: string;
  amount: number;
  units?: number;
  mode: string;
  expectedDate?: string;
  actualDate?: string;
};

export type ServiceRequest = CrmBase & {
  clientName: string;
  requestType: string;
  submittedDate: string;
  expectedCompletionDate: string;
  actualCompletionDate?: string;
  pendingWith: string;
};

export type Lead = CrmBase & {
  name: string;
  source: string;
  stage: string;
  estimatedAum: number;
  nextActionDate: string;
  convertedFamilyId?: string;
};

export type Prospect = CrmBase & {
  name: string;
  segment: string;
  interestArea: string;
  probability: number;
  convertedFamilyId?: string;
};

export type PipelineOpportunity = CrmBase & {
  prospectName: string;
  product: string;
  stage: string;
  expectedValue: number;
  expectedCloseDate: string;
};

export type Meeting = CrmBase & {
  subject: string;
  clientOrLeadName: string;
  meetingDate: string;
  type: string;
  outcome: string;
};

export type RelationshipNote = CrmBase & {
  clientOrLeadName: string;
  noteType: string;
  noteDate: string;
  summary: string;
};

export type CrmAlert = {
  id: string;
  severity: 'urgent' | 'follow_up';
  category: string;
  title: string;
  detail: string;
  owner: string;
};
