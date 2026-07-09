import { FormEvent, ReactNode, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Download, Eye, Pencil, Plus, RefreshCw, Search, Trash2 } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Badge, Card, ConfirmActionDialog, EmptyState, PageHeader, formatINR } from '../../components/ui';
import { complianceApi } from '../../lib/api';
import {
  canCreateFamily,
  canCreateMember,
  canDeleteFamily,
  canDeleteMember,
  canEditFamily,
  canEditMember,
  isCanRM,
} from '../../lib/access';
import type {
  CanStatus,
  CurrentUser,
  DashboardSummary,
  Family,
  FamilyDashboard,
  FamilyPayload,
  KycStatus,
  Member,
  MemberBankAccount,
  MemberBankAccountPayload,
  MemberPayload,
  PayeezzStatus,
  ReportExportFormat,
  ReportType,
  TaskItem,
  TaskSummary,
  TaskType,
  UserRecord,
  VerificationStatus,
} from '../../types';

const PAGE_LIMIT = 500;

const pageCopy: Record<string, { title: string; subtitle: string }> = {
  dashboard: {
    title: 'Compliance Dashboard',
    subtitle: 'CAN, KYC, PayEezz, contact verification, and pending compliance work.',
  },
  families: {
    title: 'Families',
    subtitle: 'Manage family master records, members, CANs, and compliance completion.',
  },
  'family-detail': {
    title: 'Family Detail',
    subtitle: 'Review family-level compliance, member records, and CAN status.',
  },
  kyc: {
    title: 'KYC Status',
    subtitle: 'Track verified, re-KYC pending, and not-started clients.',
  },
  payeezz: {
    title: 'PayEezz',
    subtitle: 'Track mandate approval, pending approval, and not-started clients.',
  },
  contact: {
    title: 'Contact Verification',
    subtitle: 'Review mobile, email, and nominee verification gaps.',
  },
  tasks: {
    title: 'Pending Tasks',
    subtitle: 'Computed compliance follow-ups grouped by task category.',
  },
};

const reportLabels: Record<ReportType, string> = {
  kyc_pending: 'KYC Pending Report',
  payeezz_pending: 'PayEezz Pending Report',
  contact_pending: 'Contact Pending Report',
  family_compliance: 'Family Compliance Report',
  rm_tasks: 'RM-wise Pending Tasks Report',
  full: 'Full CAN Database Export',
};

const kycStatuses: KycStatus[] = ['Verified', 'Pending Re-KYC', 'Not Started'];
const payeezzStatuses: PayeezzStatus[] = ['Approved', 'Pending Approval', 'Not Started'];
const verificationStatuses: VerificationStatus[] = ['Verified', 'Pending Verification'];

type ModalState =
  | { type: 'family'; mode: 'create'; family?: undefined }
  | { type: 'family'; mode: 'edit'; family: Family | FamilyDashboard }
  | { type: 'member'; mode: 'create'; familyId: string; member?: undefined }
  | { type: 'member'; mode: 'edit'; familyId: string; member: Member }
  | { type: 'bank'; mode: 'create'; member: Member; bankAccount?: undefined }
  | { type: 'bank'; mode: 'edit'; member: Member; bankAccount: MemberBankAccount }
  | null;

type LoadState<T> = {
  loading: boolean;
  error: string;
  data: T | null;
};

export function ComplianceModule({ user }: { user: CurrentUser }) {
  const { page = 'dashboard', familyId } = useParams();
  const navigate = useNavigate();
  const currentPage = familyId ? 'family-detail' : page;
  const config = pageCopy[currentPage] || pageCopy.dashboard;
  const [rms, setRms] = useState<UserRecord[]>([]);
  const [rmId, setRmId] = useState('');
  const [rmLoadError, setRmLoadError] = useState('');
  const [modal, setModal] = useState<ModalState>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    complianceApi.rms()
      .then((items) => {
        if (!cancelled) {
          setRms(items);
          setRmLoadError('');
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setRms(isCanRM(user) ? [user as UserRecord] : []);
          setRmLoadError(friendlyError(error));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  const rmParams = rmId ? { rm_id: rmId } : {};

  function refresh() {
    setRefreshToken((value) => value + 1);
  }

  async function openMemberEditorById(familyId: string, memberId: string) {
    const member = await complianceApi.member(memberId);
    setModal({ type: 'member', mode: 'edit', familyId, member });
  }

  function closeModal(refreshAfterClose = false) {
    setModal(null);
    if (refreshAfterClose) refresh();
  }

  return (
    <div>
      <PageHeader
        title={config.title}
        subtitle={config.subtitle}
        action={(
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={rmId}
              onChange={(event) => setRmId(event.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Relationship manager filter"
            >
              <option value="">All RMs</option>
              {rms.map((rm) => <option key={rm.id} value={rm.id}>{rm.name}</option>)}
            </select>
            <button
              type="button"
              onClick={refresh}
              className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw size={16} /> Refresh
            </button>
          </div>
        )}
      />
      {rmLoadError && <div className="mb-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">{rmLoadError}</div>}
      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        {Object.entries(pageCopy).map(([key, item]) => (
          key !== 'family-detail' && (
            <Link
              key={key}
              to={`/compliance/${key}`}
              className={`rounded-md px-3 py-1.5 font-medium ${key === page && !familyId ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'}`}
            >
              {item.title}
            </Link>
          )
        ))}
      </div>
      <CanSearch onOpenFamily={(id) => navigate(`/compliance/families/${id}`)} />
      {currentPage === 'dashboard' && <DashboardPage rmParams={rmParams} onOpenFamily={(id) => navigate(`/compliance/families/${id}`)} refreshToken={refreshToken} />}
      {currentPage === 'families' && (
        <FamiliesPage
          user={user}
          rmParams={rmParams}
          rms={rms}
          refreshToken={refreshToken}
          onOpenFamily={(id) => navigate(`/compliance/families/${id}`)}
          onEditFamily={(family) => setModal({ type: 'family', mode: 'edit', family })}
          onCreateFamily={() => setModal({ type: 'family', mode: 'create' })}
          onAddMember={(id) => setModal({ type: 'member', mode: 'create', familyId: id })}
        />
      )}
      {currentPage === 'family-detail' && familyId && (
        <FamilyDetailPage
          familyId={familyId}
          user={user}
          refreshToken={refreshToken}
          onBack={() => navigate('/compliance/families')}
          onEditFamily={(family) => setModal({ type: 'family', mode: 'edit', family })}
          onAddMember={(id) => setModal({ type: 'member', mode: 'create', familyId: id })}
          onEditMember={(id, member) => setModal({ type: 'member', mode: 'edit', familyId: id, member })}
          onAddBankAccount={(member) => setModal({ type: 'bank', mode: 'create', member })}
          onEditBankAccount={(member, bankAccount) => setModal({ type: 'bank', mode: 'edit', member, bankAccount })}
          onDeleted={() => {
            refresh();
            navigate('/compliance/families');
          }}
          onChanged={refresh}
        />
      )}
      {currentPage === 'kyc' && (
        <KycPage
          user={user}
          rmParams={rmParams}
          refreshToken={refreshToken}
          onOpenFamily={(id) => navigate(`/compliance/families/${id}`)}
          onEditMember={(id, member) => setModal({ type: 'member', mode: 'edit', familyId: id, member })}
        />
      )}
      {currentPage === 'payeezz' && (
        <PayeezzPage
          user={user}
          rmParams={rmParams}
          refreshToken={refreshToken}
          onOpenFamily={(id) => navigate(`/compliance/families/${id}`)}
          onEditMember={(id, member) => setModal({ type: 'member', mode: 'edit', familyId: id, member })}
        />
      )}
      {currentPage === 'contact' && (
        <ContactPage
          user={user}
          rmParams={rmParams}
          refreshToken={refreshToken}
          onOpenFamily={(id) => navigate(`/compliance/families/${id}`)}
          onEditMember={(id, member) => setModal({ type: 'member', mode: 'edit', familyId: id, member })}
        />
      )}
      {currentPage === 'tasks' && (
        <TasksPage
          user={user}
          rmParams={rmParams}
          refreshToken={refreshToken}
          onOpenFamily={(id) => navigate(`/compliance/families/${id}`)}
          onFixMember={openMemberEditorById}
        />
      )}
      {modal?.type === 'family' && (
        <FamilyModal
          user={user}
          rms={rms}
          modal={modal}
          onClose={() => closeModal()}
          onSaved={(family) => {
            closeModal(true);
            if (modal.mode === 'create') navigate(`/compliance/families/${family.id}`);
          }}
        />
      )}
      {modal?.type === 'member' && (
        <MemberModal
          user={user}
          modal={modal}
          onClose={() => closeModal()}
          onSaved={() => closeModal(true)}
        />
      )}
      {modal?.type === 'bank' && (
        <BankAccountModal
          modal={modal}
          onClose={() => closeModal()}
          onSaved={() => closeModal(true)}
        />
      )}
    </div>
  );
}

function DashboardPage({
  rmParams,
  refreshToken,
  onOpenFamily,
}: {
  rmParams: { rm_id?: string };
  refreshToken: number;
  onOpenFamily: (familyId: string) => void;
}) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [taskSummary, setTaskSummary] = useState<TaskSummary | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setError('');
    Promise.all([
      complianceApi.dashboardSummary(rmParams),
      complianceApi.tasks({ ...rmParams, limit: 8 }),
      complianceApi.tasksSummary(rmParams),
    ])
      .then(([nextSummary, nextTasks, nextTaskSummary]) => {
        if (!cancelled) {
          setSummary(nextSummary);
          setTasks(nextTasks.items);
          setTaskSummary(nextTaskSummary);
        }
      })
      .catch((error) => {
        if (!cancelled) setError(friendlyError(error));
      });
    return () => {
      cancelled = true;
    };
  }, [refreshToken, rmParams.rm_id]);

  if (error) return <EmptyState title="Compliance dashboard unavailable" detail={error} />;
  if (!summary || !taskSummary) return <LoadingBlock label="Loading dashboard..." />;

  const chartData = [
    { name: 'KYC Verified', value: summary.kyc_verified },
    { name: 'KYC Pending', value: summary.kyc_pending },
    { name: 'PayEezz Approved', value: summary.payeezz_approved },
    { name: 'PayEezz Pending', value: summary.payeezz_pending },
    { name: 'Mobile Pending', value: summary.mobile_pending_verification },
    { name: 'Email Pending', value: summary.email_pending_verification },
    { name: 'Nominee Pending', value: summary.nominee_pending_verification },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total Clients" value={summary.total_clients} tone="blue" />
        <MetricCard label="Total Families" value={summary.total_families} tone="slate" />
        <MetricCard label="KYC Pending" value={summary.kyc_pending} tone={summary.kyc_pending ? 'red' : 'green'} detail={`${summary.kyc_pending_pct}% pending`} />
        <MetricCard label="PayEezz Pending" value={summary.payeezz_pending} tone={summary.payeezz_pending ? 'red' : 'green'} detail={`${summary.payeezz_pending_pct}% pending`} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <Card>
          <div className="mb-3 text-sm font-semibold text-slate-900">Compliance Summary</div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-18} textAnchor="end" height={70} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <div className="text-sm font-semibold text-slate-900">Status Completion</div>
          <div className="mt-4 space-y-4">
            <ProgressRow label="KYC Verified" value={summary.kyc_verified_pct} tone="green" />
            <ProgressRow label="PayEezz Approved" value={summary.payeezz_approved_pct} tone="green" />
            <ProgressRow label="Mobile Verified" value={percent(summary.mobile_verified, summary.total_clients)} tone="blue" />
            <ProgressRow label="Email Verified" value={percent(summary.email_verified, summary.total_clients)} tone="blue" />
            <ProgressRow label="Nominee Verified" value={percent(summary.nominee_verified, summary.total_clients)} tone="blue" />
          </div>
        </Card>
      </div>
      <div className="grid gap-4 xl:grid-cols-[1fr_1.35fr]">
        <Card>
          <div className="text-sm font-semibold text-slate-900">Pending Task Mix</div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <MiniStat label="Total" value={taskSummary.total_tasks} />
            <MiniStat label="KYC" value={taskSummary.kyc} />
            <MiniStat label="PayEezz" value={taskSummary.payeezz} />
            <MiniStat label="Mobile" value={taskSummary.mobile} />
            <MiniStat label="Email" value={taskSummary.email} />
            <MiniStat label="Nominee" value={taskSummary.nominee} />
          </div>
        </Card>
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-900">Top Pending Tasks</div>
            <Link className="text-sm font-semibold text-blue-600" to="/compliance/tasks">View all</Link>
          </div>
          <TaskList tasks={tasks} onOpenFamily={onOpenFamily} />
        </Card>
      </div>
    </div>
  );
}

function FamiliesPage({
  user,
  rms,
  rmParams,
  refreshToken,
  onOpenFamily,
  onEditFamily,
  onCreateFamily,
  onAddMember,
}: {
  user: CurrentUser;
  rms: UserRecord[];
  rmParams: { rm_id?: string };
  refreshToken: number;
  onOpenFamily: (familyId: string) => void;
  onEditFamily: (family: Family) => void;
  onCreateFamily: () => void;
  onAddMember: (familyId: string) => void;
}) {
  const [families, setFamilies] = useState<Family[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    complianceApi.families({
      ...rmParams,
      q: query,
      status_filter: filter,
      limit: PAGE_LIMIT,
      sort: 'family_head_name',
    })
      .then((response) => {
        if (!cancelled) {
          setFamilies(response.items);
          setTotal(response.total);
        }
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
  }, [filter, query, refreshToken, rmParams.rm_id]);

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          {[
            ['all', 'All Families'],
            ['kyc_pending', 'KYC Pending'],
            ['payeezz_pending', 'PayEezz Pending'],
            ['contact_pending', 'Contact Pending'],
            ['nominee_pending', 'Nominee Pending'],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setFilter(value)}
              className={`rounded-full px-3 py-1.5 text-sm font-semibold ${filter === value ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              {label}
            </button>
          ))}
          <div className="ml-auto flex min-w-64 items-center gap-2">
            <Search size={16} className="text-slate-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search families"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {canCreateFamily(user) && (
            <button
              type="button"
              onClick={onCreateFamily}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              <Plus size={16} /> Add Family
            </button>
          )}
        </div>
      </Card>
      {loading && <LoadingBlock label="Loading families..." />}
      {error && <EmptyState title="Families unavailable" detail={error} />}
      {!loading && !error && (
        <>
          <div className="text-sm text-slate-500">Showing {families.length} of {total} families</div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {families.map((family) => (
              <FamilyCard
                key={family.id}
                family={family}
                rmName={displayRm(family.primary_rm, rms)}
                canEdit={canEditFamily(user)}
                canAddMember={canCreateMember(user)}
                onOpen={() => onOpenFamily(family.id)}
                onEdit={() => onEditFamily(family)}
                onAddMember={() => onAddMember(family.id)}
              />
            ))}
          </div>
          {!families.length && <EmptyState title="No families found" detail="Adjust filters or search text to find a family." />}
        </>
      )}
    </div>
  );
}

function FamilyDetailPage({
  familyId,
  user,
  refreshToken,
  onBack,
  onEditFamily,
  onAddMember,
  onEditMember,
  onAddBankAccount,
  onEditBankAccount,
  onDeleted,
  onChanged,
}: {
  familyId: string;
  user: CurrentUser;
  refreshToken: number;
  onBack: () => void;
  onEditFamily: (family: FamilyDashboard) => void;
  onAddMember: (familyId: string) => void;
  onEditMember: (familyId: string, member: Member) => void;
  onAddBankAccount: (member: Member) => void;
  onEditBankAccount: (member: Member, bankAccount: MemberBankAccount) => void;
  onDeleted: () => void;
  onChanged: () => void;
}) {
  const [state, setState] = useState<LoadState<FamilyDashboard>>({ loading: true, error: '', data: null });
  const [message, setMessage] = useState('');
  const [confirmAction, setConfirmAction] = useState<
    { type: 'family' } | { type: 'member'; member: Member } | { type: 'bank'; member: Member; bankAccount: MemberBankAccount } | null
  >(null);
  const [detailMember, setDetailMember] = useState<Member | null>(null);
  const [detailError, setDetailError] = useState('');
  const [revealBusy, setRevealBusy] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true, error: '', data: null });
    complianceApi.familyDashboard(familyId)
      .then((data) => {
        if (!cancelled) setState({ loading: false, error: '', data });
      })
      .catch((error) => {
        if (!cancelled) setState({ loading: false, error: friendlyError(error), data: null });
      });
    return () => {
      cancelled = true;
    };
  }, [familyId, refreshToken]);

  async function exportFamily() {
    try {
      await complianceApi.exportReport('full', 'csv', { family_id: familyId });
      setMessage('Family CSV export started.');
    } catch (error) {
      setMessage(friendlyError(error));
    }
  }

  async function confirmDelete() {
    if (!confirmAction) return;
    if (confirmAction.type === 'bank') {
      if (!canCreateMember(user)) return;
      setDeleteBusy(true);
      try {
        await complianceApi.deleteBankAccount(confirmAction.member.id, confirmAction.bankAccount.id);
        setMessage('Bank account deleted.');
        setConfirmAction(null);
        onChanged();
      } catch (error) {
        setMessage(friendlyError(error));
      } finally {
        setDeleteBusy(false);
      }
      return;
    }
    if (confirmAction.type === 'member') {
      if (!canDeleteMember(user)) return;
      setDeleteBusy(true);
      try {
        await complianceApi.deleteMember(confirmAction.member.id);
        setMessage('Member deleted.');
        setConfirmAction(null);
        onChanged();
      } catch (error) {
        setMessage(friendlyError(error));
      } finally {
        setDeleteBusy(false);
      }
      return;
    }
    if (!canDeleteFamily(user) || !state.data) return;
    setDeleteBusy(true);
    try {
      await complianceApi.deleteFamily(state.data.id);
      setMessage('Family deleted.');
      setConfirmAction(null);
      onDeleted();
    } catch (error) {
      setMessage(friendlyError(error));
    } finally {
      setDeleteBusy(false);
    }
  }

  async function revealSensitiveMemberData() {
    if (!detailMember || !canRevealSensitiveData(user)) return;
    setRevealBusy(true);
    setDetailError('');
    try {
      const revealed = await complianceApi.memberSensitive(detailMember.id);
      setDetailMember(revealed);
    } catch (error) {
      setDetailError(friendlyError(error));
    } finally {
      setRevealBusy(false);
    }
  }

  if (state.loading) return <LoadingBlock label="Loading family details..." />;
  if (state.error || !state.data) return <EmptyState title="Family unavailable" detail={state.error || 'Family was not found.'} />;

  const family = state.data;
  const memberCount = family.number_of_members || family.members.length;
  const confirmTitle = confirmAction?.type === 'member' ? 'Delete Member' : confirmAction?.type === 'bank' ? 'Delete Bank Account' : 'Delete Family';
  const confirmMessage = confirmAction?.type === 'member'
    ? `Delete member ${confirmAction.member.name}? This action cannot be undone.`
    : confirmAction?.type === 'bank'
      ? `Delete ${confirmAction.bankAccount.bank_name} ${confirmAction.bankAccount.account_number_masked}? This action cannot be undone.`
      : `Delete family ${family.family_head_name}? This will also delete its members. This action cannot be undone.`;
  const confirmLabel = confirmAction?.type === 'member' ? 'Delete Member' : confirmAction?.type === 'bank' ? 'Delete Bank Account' : 'Delete Family';

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={onBack} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
          Back to Families
        </button>
        {canEditFamily(user) && (
          <button type="button" onClick={() => onEditFamily(family)} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            <Pencil size={16} /> Edit Family
          </button>
        )}
        {canCreateMember(user) && (
          <button type="button" onClick={() => onAddMember(family.id)} className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            <Plus size={16} /> Add Member
          </button>
        )}
        <button type="button" onClick={exportFamily} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
          <Download size={16} /> Export CSV
        </button>
        {canDeleteFamily(user) && (
          <button type="button" onClick={() => setConfirmAction({ type: 'family' })} className="inline-flex items-center gap-2 rounded-md border border-rose-200 bg-white px-3 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50">
            <Trash2 size={16} /> Delete Family
          </button>
        )}
      </div>
      {message && <div className="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{message}</div>}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xl font-bold text-slate-950">{family.family_head_name}</div>
            <div className="mt-1 text-sm text-slate-500">{family.family_code} | RM: {displayRm(family.primary_rm)}</div>
          </div>
          <Badge tone="blue">{memberCount} members</Badge>
        </div>
        {family.remarks && <p className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">{family.remarks}</p>}
      </Card>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Members" value={memberCount} tone="slate" />
        <MetricCard label="Total CANs" value={family.total_cans} tone="blue" />
        <MetricCard label="KYC" value={`${family.kyc_completion_pct}%`} tone={family.kyc_completion_pct === 100 ? 'green' : 'red'} />
        <MetricCard label="PayEezz" value={`${family.payeezz_completion_pct}%`} tone={family.payeezz_completion_pct === 100 ? 'green' : 'red'} />
        <MetricCard label="Contact" value={`${Math.round((family.mobile_verification_pct + family.email_verification_pct + family.nominee_verification_pct) / 3)}%`} tone="yellow" />
      </div>
      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="text-sm font-semibold text-slate-900">Members</div>
          {canCreateMember(user) && (
            <button type="button" onClick={() => onAddMember(family.id)} className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700">
              <Plus size={14} /> Add Member
            </button>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">CAN</th>
                <th className="px-3 py-2">PAN</th>
                <th className="px-3 py-2">KYC</th>
                <th className="px-3 py-2">Mobile</th>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Nominee</th>
                <th className="px-3 py-2">Nominee Name</th>
                <th className="px-3 py-2">PayEezz</th>
                <th className="px-3 py-2">Bank</th>
                <th className="px-3 py-2">Updated</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {family.members.map((member) => (
                <tr key={member.id} className="align-top">
                  <td className="px-3 py-3 font-semibold text-slate-900">{member.name}</td>
                  <td className="px-3 py-3">{displayCan(member)}</td>
                  <td className="px-3 py-3">{member.pan_masked || '-'}</td>
                  <td className="px-3 py-3"><StatusBadge value={member.kyc_status} /></td>
                  <td className="px-3 py-3"><StatusBadge value={member.mobile_verification_status} /></td>
                  <td className="px-3 py-3"><StatusBadge value={member.email_verification_status} /></td>
                  <td className="px-3 py-3"><StatusBadge value={member.nominee_verification_status} /></td>
                  <td className="px-3 py-3">{member.nominee_name || '-'}</td>
                  <td className="px-3 py-3"><StatusBadge value={member.effective_payeezz_mandate_status} /></td>
                  <td className="px-3 py-3">
                    <BankAccountList
                      member={member}
                      canManage={canCreateMember(user)}
                      onAdd={() => onAddBankAccount(member)}
                      onEdit={(bankAccount) => onEditBankAccount(member, bankAccount)}
                      onDelete={(bankAccount) => setConfirmAction({ type: 'bank', member, bankAccount })}
                    />
                  </td>
                  <td className="px-3 py-3">{formatDate(member.updated_at)}</td>
                  <td className="px-3 py-3">
                    <div className="flex gap-2">
                      {canEditMember(user) && (
                        <button type="button" onClick={() => onEditMember(family.id, member)} className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                          Edit
                        </button>
                      )}
                      <button type="button" onClick={() => { setDetailMember(member); setDetailError(''); }} className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                        <Eye size={13} /> View Details
                      </button>
                      {canCreateMember(user) && (
                        <button type="button" onClick={() => onAddBankAccount(member)} className="rounded-md border border-blue-200 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50">
                          Add Bank
                        </button>
                      )}
                      {canDeleteMember(user) && (
                        <button type="button" onClick={() => setConfirmAction({ type: 'member', member })} className="rounded-md border border-rose-200 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {!family.members.length && (
                <tr><td className="px-3 py-8 text-center text-slate-500" colSpan={12}>No members yet. Add a member to get started.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
      {confirmAction && (
        <ConfirmActionDialog
          title={confirmTitle}
          message={confirmMessage}
          confirmLabel={confirmLabel}
          busy={deleteBusy}
          onCancel={() => setConfirmAction(null)}
          onConfirm={confirmDelete}
        />
      )}
      {detailMember && (
        <MemberDetailDialog
          member={detailMember}
          canReveal={canRevealSensitiveData(user)}
          revealBusy={revealBusy}
          error={detailError}
          onReveal={revealSensitiveMemberData}
          onClose={() => setDetailMember(null)}
        />
      )}
    </div>
  );
}

function canRevealSensitiveData(user: CurrentUser) {
  if (canDeleteFamily(user)) return true;
  if (user.can_sensitive_access) return Object.values(user.can_sensitive_access).some(Boolean);
  return canCreateMember(user);
}

function displaySensitive(masked: string | null | undefined, revealed: string | null | undefined) {
  return revealed || masked || '-';
}

function MemberDetailDialog({
  member,
  canReveal,
  revealBusy,
  error,
  onReveal,
  onClose,
}: {
  member: Member;
  canReveal: boolean;
  revealBusy: boolean;
  error: string;
  onReveal: () => void;
  onClose: () => void;
}) {
  const hasRevealed = Boolean(member.pan || member.mobile || member.email || member.bank_accounts.some((account) => account.account_number));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
      <div role="dialog" aria-modal="true" aria-label="Member Details" className="max-h-full w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-950 px-5 py-4 text-white">
          <div>
            <div className="font-semibold">Member Details</div>
            <div className="text-sm text-slate-300">{member.name} | {member.family_head_name}</div>
          </div>
          <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-sm text-slate-300 hover:bg-white/10 hover:text-white">Close</button>
        </div>
        <div className="max-h-[78vh] space-y-4 overflow-y-auto p-5">
          {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm text-slate-500">Sensitive values are masked until revealed.</div>
            {canReveal && (
              <button type="button" disabled={revealBusy || hasRevealed} onClick={onReveal} className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50">
                <Eye size={16} /> {hasRevealed ? 'Sensitive Data Revealed' : revealBusy ? 'Revealing...' : 'Reveal Sensitive Data'}
              </button>
            )}
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <DetailItem label="CAN" value={displayCan(member)} />
            <DetailItem label="PAN" value={displaySensitive(member.pan_masked, member.pan)} />
            <DetailItem label="Date of Birth" value={formatDate(member.date_of_birth)} />
            <DetailItem label="Nominee Name" value={member.nominee_name || '-'} />
            <DetailItem label="Mobile" value={displaySensitive(member.mobile_masked, member.mobile)} />
            <DetailItem label="Email" value={displaySensitive(member.email_masked, member.email)} />
            <DetailItem label="RM" value={displayRm(member.primary_rm)} />
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <StatusItem label="KYC" value={member.kyc_status} />
            <StatusItem label="Mobile" value={member.mobile_verification_status} />
            <StatusItem label="Email" value={member.email_verification_status} />
            <StatusItem label="Nominee" value={member.nominee_verification_status} />
          </div>
          {member.remarks && <div className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">{member.remarks}</div>}
          <div>
            <div className="mb-2 text-sm font-semibold text-slate-900">Bank Accounts</div>
            <div className="overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Bank</th>
                    <th className="px-3 py-2">Account</th>
                    <th className="px-3 py-2">IFSC</th>
                    <th className="px-3 py-2">PayEezz</th>
                    <th className="px-3 py-2">Amount</th>
                    <th className="px-3 py-2">Start</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {member.bank_accounts.map((account) => (
                    <tr key={account.id}>
                      <td className="px-3 py-3 font-semibold text-slate-900">{account.bank_name}{account.is_primary && <span className="ml-2 rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">Primary</span>}</td>
                      <td className="px-3 py-3">{account.account_number || account.account_number_masked}</td>
                      <td className="px-3 py-3">{account.ifsc_code || '-'}</td>
                      <td className="px-3 py-3"><StatusBadge value={account.payeezz_mandate_status} /></td>
                      <td className="px-3 py-3">{account.payeezz_amount ? formatINR(Number(account.payeezz_amount)) : '-'}</td>
                      <td className="px-3 py-3">{formatDate(account.payeezz_start_date)}</td>
                    </tr>
                  ))}
                  {!member.bank_accounts.length && <tr><td className="px-3 py-8 text-center text-slate-500" colSpan={6}>No bank accounts.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold uppercase text-slate-500">{label}</div>
      <div className="mt-1 break-words text-sm font-semibold text-slate-900">{value}</div>
    </div>
  );
}

function StatusItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="mb-1 text-xs font-semibold uppercase text-slate-500">{label}</div>
      <StatusBadge value={value} />
    </div>
  );
}

function BankAccountList({
  member,
  canManage,
  onAdd,
  onEdit,
  onDelete,
}: {
  member: Member;
  canManage: boolean;
  onAdd: () => void;
  onEdit: (bankAccount: MemberBankAccount) => void;
  onDelete: (bankAccount: MemberBankAccount) => void;
}) {
  if (!member.bank_accounts.length) {
    return (
      <div className="space-y-2">
        <span className="text-slate-500">No bank accounts</span>
        {canManage && (
          <button type="button" onClick={onAdd} className="block rounded-md border border-blue-200 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50">
            Add Bank
          </button>
        )}
      </div>
    );
  }
  return (
    <div className="min-w-72 space-y-2">
      {member.bank_accounts.map((bankAccount) => (
        <div key={bankAccount.id} className="rounded-md border border-slate-200 p-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-900">{bankAccount.bank_name}</span>
            {bankAccount.is_primary && <Badge tone="blue">Primary</Badge>}
            <StatusBadge value={bankAccount.payeezz_mandate_status} />
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {bankAccount.account_number_masked}
            {bankAccount.ifsc_code ? ` | ${bankAccount.ifsc_code}` : ''}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {bankAccount.payeezz_amount ? formatINR(Number(bankAccount.payeezz_amount)) : '-'} | {formatDate(bankAccount.payeezz_start_date)}
          </div>
          {canManage && (
            <div className="mt-2 flex flex-wrap gap-2">
              <button type="button" onClick={() => onEdit(bankAccount)} className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                Edit Bank
              </button>
              {!bankAccount.is_primary && (
                <button type="button" onClick={() => onEdit({ ...bankAccount, is_primary: true })} className="rounded-md border border-blue-200 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50">
                  Set Primary
                </button>
              )}
              <button type="button" onClick={() => onDelete(bankAccount)} className="rounded-md border border-rose-200 px-2 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50">
                Delete Bank
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function KycPage({ user, rmParams, refreshToken, onOpenFamily, onEditMember }: StatusPageProps) {
  const tabs: Array<{ key: string; label: string; params: Record<string, string> }> = [
    { key: 'all', label: 'All Clients', params: {} },
    { key: 'verified', label: 'Verified', params: { kyc_status: 'Verified' } },
    { key: 'pending_rekyc', label: 'Re-KYC Pending', params: { kyc_status: 'Pending Re-KYC' } },
    { key: 'not_started', label: 'Not Started', params: { kyc_status: 'Not Started' } },
  ];
  return (
    <MemberStatusPage
      kind="kyc"
      tabs={tabs}
      rmParams={rmParams}
      refreshToken={refreshToken}
      onOpenFamily={onOpenFamily}
      user={user}
      onEditMember={onEditMember}
      exportType="kyc_pending"
      columns={['family', 'can', 'pan', 'kyc', 'rm', 'updated']}
    />
  );
}

function PayeezzPage({ user, rmParams, refreshToken, onOpenFamily, onEditMember }: StatusPageProps) {
  const tabs: Array<{ key: string; label: string; params: Record<string, string> }> = [
    { key: 'all', label: 'All Clients', params: {} },
    { key: 'approved', label: 'Approved', params: { payeezz_mandate_status: 'Approved' } },
    { key: 'pending_approval', label: 'Pending Approval', params: { payeezz_mandate_status: 'Pending Approval' } },
    { key: 'not_started', label: 'Not Started', params: { payeezz_mandate_status: 'Not Started' } },
  ];
  return (
    <MemberStatusPage
      kind="payeezz"
      tabs={tabs}
      rmParams={rmParams}
      refreshToken={refreshToken}
      onOpenFamily={onOpenFamily}
      user={user}
      onEditMember={onEditMember}
      exportType="payeezz_pending"
      columns={['family', 'can', 'bank', 'payeezz', 'amount', 'start', 'rm']}
    />
  );
}

function ContactPage({ user, rmParams, refreshToken, onOpenFamily, onEditMember }: StatusPageProps) {
  const tabs: Array<{ key: string; label: string; params: Record<string, string> }> = [
    { key: 'all', label: 'All Clients', params: {} },
    { key: 'mobile', label: 'Mobile Pending', params: { mobile_verification_status: 'Pending Verification' } },
    { key: 'email', label: 'Email Pending', params: { email_verification_status: 'Pending Verification' } },
    { key: 'nominee', label: 'Nominee Pending', params: { nominee_verification_status: 'Pending Verification' } },
  ];
  return (
    <MemberStatusPage
      kind="contact"
      tabs={tabs}
      rmParams={rmParams}
      refreshToken={refreshToken}
      onOpenFamily={onOpenFamily}
      user={user}
      onEditMember={onEditMember}
      exportType="contact_pending"
      columns={['family', 'can', 'mobile', 'email', 'nominee', 'rm', 'updated']}
    />
  );
}

type StatusPageProps = {
  user: CurrentUser;
  rmParams: { rm_id?: string };
  refreshToken: number;
  onOpenFamily: (familyId: string) => void;
  onEditMember: (familyId: string, member: Member) => void;
};

type MemberStatusPageProps = StatusPageProps & {
  kind: 'kyc' | 'payeezz' | 'contact';
  tabs: Array<{ key: string; label: string; params: Record<string, string> }>;
  exportType: ReportType;
  columns: string[];
};

function MemberStatusPage({
  kind,
  tabs,
  rmParams,
  refreshToken,
  onOpenFamily,
  user,
  onEditMember,
  exportType,
  columns,
}: MemberStatusPageProps) {
  const [active, setActive] = useState(tabs[0].key);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [total, setTotal] = useState(0);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const activeTab = tabs.find((tab) => tab.key === active) || tabs[0];

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    Promise.all([
      complianceApi.dashboardSummary(rmParams),
      complianceApi.members({ ...rmParams, ...activeTab.params, limit: PAGE_LIMIT }),
    ])
      .then(([nextSummary, response]) => {
        if (!cancelled) {
          setSummary(nextSummary);
          setMembers(response.items);
          setTotal(response.total);
        }
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
  }, [active, refreshToken, rmParams.rm_id]);

  async function exportReport() {
    try {
      await complianceApi.exportReport(exportType, 'csv', rmParams);
      setMessage(`${reportLabels[exportType]} export started.`);
    } catch (error) {
      setMessage(friendlyError(error));
    }
  }

  return (
    <div className="space-y-4">
      {summary && <StatusKpis kind={kind} summary={summary} />}
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <TabButtons tabs={tabs} active={active} onChange={setActive} />
          <button type="button" onClick={exportReport} className="ml-auto inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            <Download size={16} /> Export
          </button>
        </div>
        {message && <div className="mt-3 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{message}</div>}
      </Card>
      {loading && <LoadingBlock label="Loading member records..." />}
      {error && <EmptyState title="Member records unavailable" detail={error} />}
      {!loading && !error && (
        <Card>
          <div className="mb-3 text-sm text-slate-500">Showing {members.length} of {total} clients</div>
          <MembersTable
            members={members}
            columns={columns}
            onOpenFamily={onOpenFamily}
            canEdit={canEditMember(user)}
            onEditMember={onEditMember}
          />
        </Card>
      )}
    </div>
  );
}

function TasksPage({
  user,
  rmParams,
  refreshToken,
  onOpenFamily,
  onFixMember,
}: {
  user: CurrentUser;
  rmParams: { rm_id?: string };
  refreshToken: number;
  onOpenFamily: (familyId: string) => void;
  onFixMember: (familyId: string, memberId: string) => Promise<void>;
}) {
  const tabs: Array<{ key: TaskType | 'all'; label: string }> = [
    { key: 'all', label: 'All Pending' },
    { key: 'kyc', label: 'KYC' },
    { key: 'payeezz', label: 'PayEezz' },
    { key: 'mobile', label: 'Mobile' },
    { key: 'email', label: 'Email' },
    { key: 'nominee', label: 'Nominee' },
  ];
  const [active, setActive] = useState<TaskType | 'all'>('all');
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [summary, setSummary] = useState<TaskSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    Promise.all([
      complianceApi.tasksSummary(rmParams),
      complianceApi.tasks({ ...rmParams, type: active, limit: PAGE_LIMIT }),
    ])
      .then(([nextSummary, response]) => {
        if (!cancelled) {
          setSummary(nextSummary);
          setTasks(response.items);
        }
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
  }, [active, refreshToken, rmParams.rm_id]);

  return (
    <div className="space-y-4">
      {summary && (
        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          <MetricCard label="Total Pending" value={summary.total_tasks} tone="blue" />
          <MetricCard label="KYC" value={summary.kyc} tone="red" />
          <MetricCard label="PayEezz" value={summary.payeezz} tone="yellow" />
          <MetricCard label="Mobile" value={summary.mobile} tone="slate" />
          <MetricCard label="Email" value={summary.email} tone="slate" />
          <MetricCard label="Nominee" value={summary.nominee} tone="slate" />
        </div>
      )}
      <Card>
        <TabButtons tabs={tabs} active={active} onChange={(value) => setActive(value as TaskType | 'all')} />
      </Card>
      {loading && <LoadingBlock label="Loading tasks..." />}
      {error && <EmptyState title="Tasks unavailable" detail={error} />}
      {!loading && !error && (
        <Card>
          <TaskList
            tasks={tasks}
            onOpenFamily={onOpenFamily}
            canFix={canEditMember(user)}
            onFixMember={onFixMember}
          />
        </Card>
      )}
    </div>
  );
}

function FamilyModal({
  user,
  rms,
  modal,
  onClose,
  onSaved,
}: {
  user: CurrentUser;
  rms: UserRecord[];
  modal: Extract<ModalState, { type: 'family' }>;
  onClose: () => void;
  onSaved: (family: Family) => void;
}) {
  const editing = modal.mode === 'edit';
  const family = editing ? modal.family : null;
  const remarksOnly = editing && isCanRM(user) && !canCreateFamily(user);
  const [form, setForm] = useState<FamilyPayload>({
    family_code: family?.family_code || '',
    family_head_name: family?.family_head_name || '',
    primary_rm_id: family?.primary_rm?.id || '',
    remarks: family?.remarks || '',
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  function update<K extends keyof FamilyPayload>(key: K, value: FamilyPayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      if (editing) {
        const payload = remarksOnly
          ? { remarks: form.remarks || null }
          : {
              family_head_name: form.family_head_name,
              primary_rm_id: form.primary_rm_id || null,
              remarks: form.remarks || null,
            };
        const saved = await complianceApi.updateFamily(family!.id, payload);
        onSaved(saved);
      } else {
        if (!form.family_head_name.trim()) {
          setError('Family head is required.');
          return;
        }
        const saved = await complianceApi.createFamily({
          family_head_name: form.family_head_name,
          primary_rm_id: form.primary_rm_id || null,
          remarks: form.remarks || null,
        });
        onSaved(saved);
      }
    } catch (error) {
      setError(friendlyError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={editing ? 'Edit Family' : 'Add Family'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
        <div className="grid gap-4 md:grid-cols-2">
          {editing && (
            <Field label="Family Code">
              <input value={form.family_code || ''} disabled className={inputClass} />
            </Field>
          )}
          <Field label="Family Head">
            <input value={form.family_head_name} disabled={remarksOnly} onChange={(event) => update('family_head_name', event.target.value)} className={inputClass} required />
          </Field>
          <Field label="Primary RM">
            <select value={form.primary_rm_id || ''} disabled={remarksOnly} onChange={(event) => update('primary_rm_id', event.target.value || null)} className={inputClass}>
              <option value="">Unassigned</option>
              {rms.map((rm) => <option key={rm.id} value={rm.id}>{rm.name}</option>)}
            </select>
          </Field>
          <Field label="Remarks">
            <textarea value={form.remarks || ''} onChange={(event) => update('remarks', event.target.value)} className={`${inputClass} min-h-24`} />
          </Field>
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className={secondaryButtonClass}>Cancel</button>
          <button disabled={busy} className={primaryButtonClass}>{busy ? 'Saving...' : 'Save Family'}</button>
        </div>
      </form>
    </Modal>
  );
}

function MemberModal({
  user,
  modal,
  onClose,
  onSaved,
}: {
  user: CurrentUser;
  modal: Extract<ModalState, { type: 'member' }>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const member = modal.mode === 'edit' ? modal.member : null;
  const remarksOnly = modal.mode === 'edit' && isCanRM(user) && !canCreateMember(user);
  const [clearPan, setClearPan] = useState(false);
  const [form, setForm] = useState<MemberPayload>({
    name: member?.name || '',
    can_number: member?.can_number || '',
    can_status: member?.can_status || 'Pending',
    pan: '',
    date_of_birth: member?.date_of_birth || null,
    kyc_status: member?.kyc_status || 'Not Started',
    mobile: '',
    mobile_verification_status: member?.mobile_verification_status || 'Pending Verification',
    email: '',
    email_verification_status: member?.email_verification_status || 'Pending Verification',
    nominee_name: member?.nominee_name || '',
    nominee_verification_status: member?.nominee_verification_status || 'Pending Verification',
    remarks: member?.remarks || '',
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  function update<K extends keyof MemberPayload>(key: K, value: MemberPayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function buildPayload(): Partial<MemberPayload> {
    if (remarksOnly) return { remarks: form.remarks || null };
    const canNumber = form.can_number?.trim() || null;
    const payload: Partial<MemberPayload> = {
      name: form.name.trim(),
      can_number: canNumber,
      can_status: (canNumber ? 'Available' : 'Pending') as CanStatus,
      date_of_birth: form.date_of_birth || null,
      kyc_status: form.kyc_status,
      nominee_name: form.nominee_name?.trim() || null,
      mobile_verification_status: form.mobile_verification_status,
      email_verification_status: form.email_verification_status,
      nominee_verification_status: form.nominee_verification_status,
      remarks: form.remarks?.trim() || null,
    };
    if (modal.mode === 'create' || form.pan || clearPan) payload.pan = clearPan ? null : form.pan?.trim() || null;
    if (modal.mode === 'create' || form.mobile) payload.mobile = form.mobile?.trim() || null;
    if (modal.mode === 'create' || form.email) payload.email = form.email?.trim() || null;
    return payload;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!remarksOnly && !form.name.trim()) {
      setError('Name is required.');
      return;
    }
    setBusy(true);
    try {
      if (modal.mode === 'edit') {
        await complianceApi.updateMember(modal.member.id, buildPayload());
      } else {
        await complianceApi.createMember(modal.familyId, buildPayload() as MemberPayload);
      }
      onSaved();
    } catch (error) {
      setError(friendlyError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={modal.mode === 'edit' ? `Edit Member - ${member?.name}` : 'Add Family Member'} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
        {remarksOnly && <div className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">RM access can update remarks only.</div>}
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Name">
            <input value={form.name} disabled={remarksOnly} onChange={(event) => update('name', event.target.value)} className={inputClass} required={!remarksOnly} />
          </Field>
          <Field label="CAN Number">
            <input value={form.can_number || ''} disabled={remarksOnly} onChange={(event) => update('can_number', event.target.value)} className={inputClass} placeholder="Leave blank until CAN is available" />
          </Field>
          <Field label="PAN">
            <input value={form.pan || ''} disabled={remarksOnly || clearPan} onChange={(event) => update('pan', event.target.value)} placeholder={member?.pan_masked ? `Stored: ${member.pan_masked}` : 'ABCDE1234F'} className={inputClass} />
            {modal.mode === 'edit' && member?.pan_masked && !remarksOnly && <Checkbox label="Clear stored PAN" checked={clearPan} onChange={setClearPan} />}
          </Field>
          <Field label="Date of Birth">
            <input type="date" value={form.date_of_birth || ''} disabled={remarksOnly} onChange={(event) => update('date_of_birth', event.target.value || null)} className={inputClass} />
          </Field>
          <Field label="KYC Status">
            <select value={form.kyc_status} disabled={remarksOnly} onChange={(event) => update('kyc_status', event.target.value as KycStatus)} className={inputClass}>
              {kycStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </Field>
          <Field label="Mobile">
            <input value={form.mobile || ''} disabled={remarksOnly} onChange={(event) => update('mobile', event.target.value)} placeholder={member?.mobile_masked ? `Stored: ${member.mobile_masked}` : 'Mobile number'} className={inputClass} />
          </Field>
          <Field label="Mobile Status">
            <select value={form.mobile_verification_status} disabled={remarksOnly} onChange={(event) => update('mobile_verification_status', event.target.value as VerificationStatus)} className={inputClass}>
              {verificationStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </Field>
          <Field label="Nominee Name">
            <input value={form.nominee_name || ''} onChange={(event) => update('nominee_name', event.target.value)} className={inputClass} />
          </Field>
          <Field label="Email">
            <input value={form.email || ''} disabled={remarksOnly} onChange={(event) => update('email', event.target.value)} placeholder={member?.email_masked ? `Stored: ${member.email_masked}` : 'client@example.com'} className={inputClass} />
          </Field>
          <Field label="Email Status">
            <select value={form.email_verification_status} disabled={remarksOnly} onChange={(event) => update('email_verification_status', event.target.value as VerificationStatus)} className={inputClass}>
              {verificationStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </Field>
          <Field label="Nominee Status">
            <select value={form.nominee_verification_status} disabled={remarksOnly} onChange={(event) => update('nominee_verification_status', event.target.value as VerificationStatus)} className={inputClass}>
              {verificationStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </Field>
          <Field label="Remarks">
            <textarea value={form.remarks || ''} onChange={(event) => update('remarks', event.target.value)} className={`${inputClass} min-h-24`} />
          </Field>
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className={secondaryButtonClass}>Cancel</button>
          <button disabled={busy} className={primaryButtonClass}>{busy ? 'Saving...' : 'Save Member'}</button>
        </div>
      </form>
    </Modal>
  );
}

function BankAccountModal({
  modal,
  onClose,
  onSaved,
}: {
  modal: Extract<ModalState, { type: 'bank' }>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const editing = modal.mode === 'edit';
  const bankAccount = editing ? modal.bankAccount : null;
  const [form, setForm] = useState<MemberBankAccountPayload>({
    bank_name: bankAccount?.bank_name || '',
    account_number: '',
    ifsc_code: bankAccount?.ifsc_code || '',
    is_primary: bankAccount?.is_primary || modal.member.bank_accounts.length === 0,
    payeezz_mandate_status: bankAccount?.payeezz_mandate_status || 'Not Started',
    payeezz_amount: bankAccount?.payeezz_amount === null || bankAccount?.payeezz_amount === undefined ? null : Number(bankAccount.payeezz_amount),
    payeezz_start_date: bankAccount?.payeezz_start_date || null,
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  function update<K extends keyof MemberBankAccountPayload>(key: K, value: MemberBankAccountPayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function buildPayload(): Partial<MemberBankAccountPayload> {
    const payload: Partial<MemberBankAccountPayload> = {
      bank_name: form.bank_name.trim(),
      ifsc_code: form.ifsc_code?.trim() || null,
      is_primary: Boolean(form.is_primary),
      payeezz_mandate_status: form.payeezz_mandate_status,
      payeezz_amount: form.payeezz_amount === undefined ? null : form.payeezz_amount,
      payeezz_start_date: form.payeezz_start_date || null,
    };
    if (!editing || form.account_number) payload.account_number = form.account_number?.trim() || null;
    return payload;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!form.bank_name.trim()) {
      setError('Bank name is required.');
      return;
    }
    if (!editing && !form.account_number?.trim()) {
      setError('Bank account number is required.');
      return;
    }
    setBusy(true);
    try {
      if (editing) {
        await complianceApi.updateBankAccount(modal.member.id, modal.bankAccount.id, buildPayload());
      } else {
        await complianceApi.createBankAccount(modal.member.id, buildPayload() as MemberBankAccountPayload);
      }
      onSaved();
    } catch (error) {
      setError(friendlyError(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={editing ? `Edit Bank - ${bankAccount?.bank_name}` : `Add Bank - ${modal.member.name}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Bank Name">
            <input value={form.bank_name} onChange={(event) => update('bank_name', event.target.value)} className={inputClass} required />
          </Field>
          <Field label="Bank Account">
            <input value={form.account_number || ''} onChange={(event) => update('account_number', event.target.value)} placeholder={bankAccount?.account_number_masked ? `Stored: ${bankAccount.account_number_masked}` : 'Bank account number'} className={inputClass} required={!editing} />
          </Field>
          <Field label="IFSC">
            <input value={form.ifsc_code || ''} onChange={(event) => update('ifsc_code', event.target.value)} className={inputClass} />
          </Field>
          <Field label="PayEezz Status">
            <select value={form.payeezz_mandate_status} onChange={(event) => update('payeezz_mandate_status', event.target.value as PayeezzStatus)} className={inputClass}>
              {payeezzStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </Field>
          <Field label="PayEezz Amount">
            <input type="number" min="0" value={form.payeezz_amount ?? ''} onChange={(event) => update('payeezz_amount', event.target.value === '' ? null : Number(event.target.value))} className={inputClass} />
          </Field>
          <Field label="PayEezz Start Date">
            <input type="date" value={form.payeezz_start_date || ''} onChange={(event) => update('payeezz_start_date', event.target.value || null)} className={inputClass} />
          </Field>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <input type="checkbox" checked={Boolean(form.is_primary)} onChange={(event) => update('is_primary', event.target.checked)} />
            Primary bank account
          </label>
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className={secondaryButtonClass}>Cancel</button>
          <button disabled={busy} className={primaryButtonClass}>{busy ? 'Saving...' : 'Save Bank'}</button>
        </div>
      </form>
    </Modal>
  );
}

function CanSearch({ onOpenFamily }: { onOpenFamily: (familyId: string) => void }) {
  const [query, setQuery] = useState('');
  const [families, setFamilies] = useState<Family[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const term = query.trim();
    if (!term) {
      setFamilies([]);
      setMembers([]);
      setMessage('');
      return;
    }
    setLoading(true);
    setMessage('');
    try {
      const [familyResults, memberResults] = await Promise.all([
        complianceApi.families({ q: term, limit: 5 }),
        complianceApi.members({ q: term, limit: 5 }),
      ]);
      setFamilies(familyResults.items);
      setMembers(memberResults.items);
      if (familyResults.total === 1 && memberResults.total === 0) onOpenFamily(familyResults.items[0].id);
      if (memberResults.total === 1) onOpenFamily(memberResults.items[0].family_id);
      if (!familyResults.total && !memberResults.total) setMessage('No matching family or member found.');
    } catch (error) {
      setMessage(friendlyError(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="mb-4">
      <form onSubmit={submit} className="flex flex-wrap items-center gap-2">
        <Search size={17} className="text-slate-400" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search families, members, CAN, PAN, mobile, or email"
          className="min-w-72 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button className={secondaryButtonClass}>{loading ? 'Searching...' : 'Search'}</button>
      </form>
      {(message || families.length > 1 || members.length > 1) && (
        <div className="mt-3 rounded-md bg-slate-50 p-3 text-sm">
          {message && <div className="text-slate-600">{message}</div>}
          <div className="grid gap-2 md:grid-cols-2">
            {families.length > 1 && (
              <SearchResults title="Families" items={families.map((family) => ({
                id: family.id,
                title: family.family_head_name,
                detail: `${family.family_code} | ${displayRm(family.primary_rm)}`,
                familyId: family.id,
              }))} onOpenFamily={onOpenFamily} />
            )}
            {members.length > 1 && (
              <SearchResults title="Members" items={members.map((member) => ({
                id: member.id,
                title: member.name,
                detail: `${member.family_head_name} | ${displayCan(member)}`,
                familyId: member.family_id,
              }))} onOpenFamily={onOpenFamily} />
            )}
          </div>
        </div>
      )}
    </Card>
  );
}

function SearchResults({
  title,
  items,
  onOpenFamily,
}: {
  title: string;
  items: Array<{ id: string; title: string; detail: string; familyId: string }>;
  onOpenFamily: (familyId: string) => void;
}) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase text-slate-500">{title}</div>
      <div className="space-y-1">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onOpenFamily(item.familyId)}
            className="block w-full rounded-md bg-white px-3 py-2 text-left hover:bg-blue-50"
          >
            <div className="font-semibold text-slate-900">{item.title}</div>
            <div className="text-xs text-slate-500">{item.detail}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function FamilyCard({
  family,
  rmName,
  canEdit,
  canAddMember,
  onOpen,
  onEdit,
  onAddMember,
}: {
  family: Family;
  rmName: string;
  canEdit: boolean;
  canAddMember: boolean;
  onOpen: () => void;
  onEdit: () => void;
  onAddMember: () => void;
}) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <button type="button" onClick={onOpen} className="text-left">
          <div className="font-semibold text-slate-950 hover:text-blue-700">{family.family_head_name}</div>
          <div className="mt-1 text-sm text-slate-500">{family.family_code} | RM: {rmName}</div>
        </button>
        {canEdit && (
          <button type="button" onClick={onEdit} className="rounded-md border border-slate-300 p-2 text-slate-600 hover:bg-slate-50" aria-label="Edit family">
            <Pencil size={15} />
          </button>
        )}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        <MiniStat label="Members" value={family.total_members} />
        <MiniStat label="CANs" value={family.total_cans} />
        <MiniStat label="Updated" value={formatDate(family.last_updated_at)} small />
      </div>
      <div className="mt-4 space-y-2">
        <ProgressRow label="KYC" value={family.kyc_completion_pct} tone={family.kyc_completion_pct === 100 ? 'green' : 'red'} compact />
        <ProgressRow label="PayEezz" value={family.payeezz_completion_pct} tone={family.payeezz_completion_pct === 100 ? 'green' : 'red'} compact />
        <ProgressRow label="Contact" value={Math.round((family.mobile_verification_pct + family.email_verification_pct + family.nominee_verification_pct) / 3)} tone="blue" compact />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={onOpen} className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
          Open Family
        </button>
        {canAddMember && (
          <button type="button" onClick={onAddMember} className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700">
            <Plus size={14} /> Add Member
          </button>
        )}
      </div>
    </Card>
  );
}

function MembersTable({
  members,
  columns,
  onOpenFamily,
  canEdit = false,
  onEditMember,
}: {
  members: Member[];
  columns: string[];
  onOpenFamily: (familyId: string) => void;
  canEdit?: boolean;
  onEditMember?: (familyId: string, member: Member) => void;
}) {
  if (!members.length) return <EmptyState title="No clients found" detail="No records match the selected status." />;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-2">Name</th>
            <th className="px-3 py-2">Nominee Name</th>
            {columns.includes('family') && <th className="px-3 py-2">Family</th>}
            {columns.includes('can') && <th className="px-3 py-2">CAN</th>}
            {columns.includes('pan') && <th className="px-3 py-2">PAN</th>}
            {columns.includes('bank') && <th className="px-3 py-2">Bank</th>}
            {columns.includes('kyc') && <th className="px-3 py-2">KYC</th>}
            {columns.includes('payeezz') && <th className="px-3 py-2">PayEezz</th>}
            {columns.includes('amount') && <th className="px-3 py-2">Amount</th>}
            {columns.includes('start') && <th className="px-3 py-2">Start Date</th>}
            {columns.includes('mobile') && <th className="px-3 py-2">Mobile</th>}
            {columns.includes('email') && <th className="px-3 py-2">Email</th>}
            {columns.includes('nominee') && <th className="px-3 py-2">Nominee</th>}
            {columns.includes('rm') && <th className="px-3 py-2">RM</th>}
            {columns.includes('updated') && <th className="px-3 py-2">Updated</th>}
            <th className="px-3 py-2">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {members.map((member) => (
            <tr key={member.id}>
              <td className="px-3 py-3 font-semibold text-slate-900">{member.name}</td>
              <td className="px-3 py-3">{member.nominee_name || '-'}</td>
              {columns.includes('family') && <td className="px-3 py-3">{member.family_head_name}</td>}
              {columns.includes('can') && <td className="px-3 py-3">{displayCan(member)}</td>}
              {columns.includes('pan') && <td className="px-3 py-3">{member.pan_masked || '-'}</td>}
              {columns.includes('bank') && <td className="px-3 py-3">{member.primary_bank_account?.bank_name || '-'}</td>}
              {columns.includes('kyc') && <td className="px-3 py-3"><StatusBadge value={member.kyc_status} /></td>}
              {columns.includes('payeezz') && <td className="px-3 py-3"><StatusBadge value={member.effective_payeezz_mandate_status} /></td>}
              {columns.includes('amount') && <td className="px-3 py-3">{member.primary_bank_account?.payeezz_amount ? formatINR(Number(member.primary_bank_account.payeezz_amount)) : '-'}</td>}
              {columns.includes('start') && <td className="px-3 py-3">{formatDate(member.primary_bank_account?.payeezz_start_date)}</td>}
              {columns.includes('mobile') && <td className="px-3 py-3"><StatusBadge value={member.mobile_verification_status} /></td>}
              {columns.includes('email') && <td className="px-3 py-3"><StatusBadge value={member.email_verification_status} /></td>}
              {columns.includes('nominee') && <td className="px-3 py-3"><StatusBadge value={member.nominee_verification_status} /></td>}
              {columns.includes('rm') && <td className="px-3 py-3">{displayRm(member.primary_rm)}</td>}
              {columns.includes('updated') && <td className="px-3 py-3">{formatDate(member.updated_at)}</td>}
              <td className="px-3 py-3">
                <div className="flex flex-wrap gap-2">
                  {canEdit && onEditMember && (
                    <button type="button" onClick={() => onEditMember(member.family_id, member)} className="rounded-md border border-blue-200 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50">
                      Update
                    </button>
                  )}
                  <button type="button" onClick={() => onOpenFamily(member.family_id)} className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                    Open Family
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusKpis({ kind, summary }: { kind: 'kyc' | 'payeezz' | 'contact'; summary: DashboardSummary }) {
  if (kind === 'kyc') {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="KYC Verified" value={summary.kyc_verified} tone="green" detail={`${percent(summary.kyc_verified, summary.total_clients)}%`} />
        <MetricCard label="Re-KYC Pending" value={summary.kyc_pending_rekyc} tone="yellow" detail={`${percent(summary.kyc_pending_rekyc, summary.total_clients)}%`} />
        <MetricCard label="Not Started" value={summary.kyc_not_started} tone="red" detail={`${percent(summary.kyc_not_started, summary.total_clients)}%`} />
      </div>
    );
  }
  if (kind === 'payeezz') {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Approved" value={summary.payeezz_approved} tone="green" detail={`${summary.payeezz_approved_pct}%`} />
        <MetricCard label="Pending Approval" value={summary.payeezz_pending_approval} tone="yellow" detail={`${percent(summary.payeezz_pending_approval, summary.total_clients)}%`} />
        <MetricCard label="Not Started" value={summary.payeezz_not_started} tone="red" detail={`${percent(summary.payeezz_not_started, summary.total_clients)}%`} />
      </div>
    );
  }
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <MetricCard label="Mobile Pending" value={summary.mobile_pending_verification} tone="red" detail={`${percent(summary.mobile_pending_verification, summary.total_clients)}%`} />
      <MetricCard label="Email Pending" value={summary.email_pending_verification} tone="red" detail={`${percent(summary.email_pending_verification, summary.total_clients)}%`} />
      <MetricCard label="Nominee Pending" value={summary.nominee_pending_verification} tone="red" detail={`${percent(summary.nominee_pending_verification, summary.total_clients)}%`} />
    </div>
  );
}

function TaskList({
  tasks,
  onOpenFamily,
  canFix = false,
  onFixMember,
}: {
  tasks: TaskItem[];
  onOpenFamily: (familyId: string) => void;
  canFix?: boolean;
  onFixMember?: (familyId: string, memberId: string) => Promise<void>;
}) {
  const [fixingId, setFixingId] = useState('');
  const [error, setError] = useState('');

  async function fixTask(task: TaskItem) {
    if (!onFixMember) return;
    setError('');
    setFixingId(task.member_id);
    try {
      await onFixMember(task.family_id, task.member_id);
    } catch (error) {
      setError(friendlyError(error));
    } finally {
      setFixingId('');
    }
  }

  if (!tasks.length) return <EmptyState title="All clear" detail="No pending tasks in this category." />;
  return (
    <div className="space-y-2">
      {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
      {tasks.map((task) => (
        <div
          key={`${task.type}-${task.member_id}-${task.label}`}
          className="flex w-full items-start justify-between gap-3 rounded-md border border-slate-200 bg-white px-3 py-3 text-left hover:bg-slate-50"
        >
          <button type="button" onClick={() => onOpenFamily(task.family_id)} className="min-w-0 flex-1 text-left">
            <div className="font-semibold text-slate-900">{task.member_name}</div>
            <div className="mt-1 text-sm text-slate-500">{task.description}</div>
            <div className="mt-1 text-xs text-slate-400">{task.family_head_name} | {task.can_number_masked} | {task.rm_name}</div>
          </button>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <StatusBadge value={task.type.toUpperCase()} />
            <Badge tone={task.priority === 'high' ? 'red' : task.priority === 'medium' ? 'yellow' : 'slate'}>{task.priority}</Badge>
            {canFix && onFixMember && (
              <button
                type="button"
                onClick={() => fixTask(task)}
                disabled={fixingId === task.member_id}
                className="mt-1 rounded-md border border-blue-200 px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {fixingId === task.member_id ? 'Loading...' : 'Fix'}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function MetricCard({
  label,
  value,
  tone,
  detail,
}: {
  label: string;
  value: ReactNode;
  tone: 'green' | 'yellow' | 'red' | 'blue' | 'slate';
  detail?: string;
}) {
  const toneClasses = {
    green: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    yellow: 'border-amber-200 bg-amber-50 text-amber-700',
    red: 'border-rose-200 bg-rose-50 text-rose-700',
    blue: 'border-blue-200 bg-blue-50 text-blue-700',
    slate: 'border-slate-200 bg-white text-slate-900',
  };
  return (
    <div className={`rounded-lg border p-4 shadow-sm ${toneClasses[tone]}`}>
      <div className="text-xs font-semibold uppercase opacity-75">{label}</div>
      <div className="mt-2 text-3xl font-bold">{value}</div>
      {detail && <div className="mt-1 text-sm opacity-80">{detail}</div>}
    </div>
  );
}

function MiniStat({ label, value, small = false }: { label: string; value: ReactNode; small?: boolean }) {
  return (
    <div className="rounded-md bg-slate-50 px-3 py-2">
      <div className={`${small ? 'text-sm' : 'text-lg'} font-bold text-slate-900`}>{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

function ProgressRow({ label, value, tone, compact = false }: { label: string; value: number; tone: 'green' | 'yellow' | 'red' | 'blue'; compact?: boolean }) {
  const colors = {
    green: 'bg-emerald-500',
    yellow: 'bg-amber-500',
    red: 'bg-rose-500',
    blue: 'bg-blue-500',
  };
  return (
    <div>
      <div className={`mb-1 flex justify-between ${compact ? 'text-xs' : 'text-sm'}`}>
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-500">{value}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${colors[tone]}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
    </div>
  );
}

function StatusBadge({ value }: { value: string }) {
  const tone = value === 'Verified' || value === 'Approved' || value === 'Available'
    ? 'green'
    : value === 'Pending Re-KYC' || value === 'Pending Approval' || value === 'Pending'
      ? 'yellow'
      : value === 'Not Started' || value === 'Pending Verification'
        ? 'red'
        : 'slate';
  return <Badge tone={tone}>{value}</Badge>;
}

function TabButtons<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ key: T; label: string }>;
  active: T;
  onChange: (key: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          onClick={() => onChange(tab.key)}
          className={`rounded-full px-3 py-1.5 text-sm font-semibold ${active === tab.key ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function Modal({ title, children, onClose, wide = false }: { title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6">
      <div className={`max-h-full w-full ${wide ? 'max-w-5xl' : 'max-w-2xl'} overflow-hidden rounded-lg bg-white shadow-xl`}>
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-950 px-5 py-4 text-white">
          <div className="font-semibold">{title}</div>
          <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-sm text-slate-300 hover:bg-white/10 hover:text-white">Close</button>
        </div>
        <div className="max-h-[78vh] overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <div className="mt-1">{children}</div>
    </label>
  );
}

function Checkbox({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="mt-2 flex items-center gap-2 text-xs font-normal text-slate-600">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

function LoadingBlock({ label }: { label: string }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">{label}</div>;
}

function formatDate(value: string | null | undefined) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function displayCan(member: Pick<Member, 'can_number' | 'can_status'>) {
  return member.can_number || member.can_status;
}

function displayRm(rm: Member['primary_rm'] | Family['primary_rm'], rms: UserRecord[] = []) {
  if (!rm) return 'Unassigned';
  return rms.find((candidate) => candidate.id === rm.id)?.name || rm.name;
}

function percent(value: number, total: number) {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

function friendlyError(error: unknown) {
  if (error && typeof error === 'object' && 'status' in error) {
    const status = (error as { status?: number }).status;
    if (status === 401) return 'Please sign in to continue.';
    if (status === 403) return 'Your role is not allowed to perform this action.';
  }
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}

const inputClass = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-500';
const secondaryButtonClass = 'inline-flex items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50';
const primaryButtonClass = 'inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50';
