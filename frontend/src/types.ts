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

export type CurrentUser = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  memberships: UserMembership[];
  module_codes: ModuleCode[];
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

export type KycStatus = 'Validated' | 'Registered' | 'No KYC';
export type VerificationStatus = 'Verified' | 'Not Verified';
export type PayeezzStatus = 'Aggregator Accepted' | 'Sent for Approval' | 'Not Available';
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

export type DashboardSummary = {
  total_clients: number;
  total_families: number;
  kyc_validated: number;
  kyc_registered: number;
  kyc_no_kyc: number;
  kyc_pending: number;
  kyc_validated_pct: number;
  kyc_pending_pct: number;
  payeezz_accepted: number;
  payeezz_sent_for_approval: number;
  payeezz_not_available: number;
  payeezz_pending: number;
  payeezz_accepted_pct: number;
  payeezz_pending_pct: number;
  mobile_verified: number;
  mobile_not_verified: number;
  email_verified: number;
  email_not_verified: number;
  nominee_verified: number;
  nominee_not_verified: number;
  updated_at: string | null;
};

export type Family = {
  id: string;
  family_code: string;
  family_head_name: string;
  primary_rm: UserSummary;
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

export type Member = {
  id: string;
  family_id: string;
  name: string;
  can_number: string;
  pan_masked: string | null;
  pan?: string | null;
  date_of_birth: string | null;
  kyc_status: KycStatus;
  mobile_masked: string | null;
  mobile?: string | null;
  mobile_status: VerificationStatus;
  email_masked: string | null;
  email?: string | null;
  email_status: VerificationStatus;
  nominee_status: VerificationStatus;
  bank_name: string | null;
  bank_account_number_masked: string | null;
  bank_account_number?: string | null;
  ifsc_code: string | null;
  payeezz_status: PayeezzStatus;
  payeezz_amount: string | number | null;
  payeezz_start_date: string | null;
  remarks: string | null;
  family_code: string;
  family_head_name: string;
  primary_rm: UserSummary;
  updated_at: string;
  updated_by: UserSummary | null;
  created_at: string;
};

export type FamilyDashboard = {
  id: string;
  family_code: string;
  family_head_name: string;
  primary_rm: UserSummary;
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
  rm_id: string;
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
  family_code: string;
  family_head_name: string;
  primary_rm_id: string;
  remarks?: string | null;
};

export type MemberPayload = {
  name: string;
  can_number: string;
  pan?: string | null;
  date_of_birth?: string | null;
  kyc_status: KycStatus;
  mobile?: string | null;
  mobile_status: VerificationStatus;
  email?: string | null;
  email_status: VerificationStatus;
  nominee_status: VerificationStatus;
  bank_name?: string | null;
  bank_account_number?: string | null;
  ifsc_code?: string | null;
  payeezz_status: PayeezzStatus;
  payeezz_amount?: number | null;
  payeezz_start_date?: string | null;
  remarks?: string | null;
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
