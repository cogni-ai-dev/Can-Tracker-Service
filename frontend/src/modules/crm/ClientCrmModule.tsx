import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  BarChart3,
  Bell,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Handshake,
  MessageSquareText,
  Plus,
  RefreshCw,
  Repeat,
  Users2,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Badge, Card, EmptyState, PageHeader, formatINR } from '../../components/ui';
import type {
  CrmAlert,
  CrmTransaction,
  Lead,
  Meeting,
  PipelineOpportunity,
  Prospect,
  RelationshipNote,
  ServiceRequest,
} from '../../types';
import { crmApi } from './crmMockApi';

type CrmPage =
  | 'control-centre'
  | 'transactions'
  | 'redemptions'
  | 'sip'
  | 'service-requests'
  | 'alerts'
  | 'leads'
  | 'prospects'
  | 'pipeline'
  | 'meetings'
  | 'notes';

type CrmSnapshot = {
  transactions: CrmTransaction[];
  serviceRequests: ServiceRequest[];
  leads: Lead[];
  prospects: Prospect[];
  pipelineOpportunities: PipelineOpportunity[];
  meetings: Meeting[];
  notes: RelationshipNote[];
  alerts: CrmAlert[];
  summary: ReturnType<typeof crmApi.summary>;
};

const crmTabs: Array<{ key: CrmPage; label: string }> = [
  { key: 'control-centre', label: 'Control Centre' },
  { key: 'transactions', label: 'Transactions' },
  { key: 'redemptions', label: 'Redemption Follow-ups' },
  { key: 'sip', label: 'SIP Monitoring' },
  { key: 'service-requests', label: 'Service Requests' },
  { key: 'alerts', label: 'Alerts' },
  { key: 'leads', label: 'Leads' },
  { key: 'prospects', label: 'Prospects' },
  { key: 'pipeline', label: 'Pipeline' },
  { key: 'meetings', label: 'Meetings' },
  { key: 'notes', label: 'Relationship Notes' },
];

const pieColors = ['#2563eb', '#10b981', '#f59e0b', '#f43f5e', '#64748b'];

function snapshot(): CrmSnapshot {
  return {
    transactions: crmApi.listTransactions(),
    serviceRequests: crmApi.listServiceRequests(),
    leads: crmApi.listLeads(),
    prospects: crmApi.listProspects(),
    pipelineOpportunities: crmApi.listPipelineOpportunities(),
    meetings: crmApi.listMeetings(),
    notes: crmApi.listNotes(),
    alerts: crmApi.alerts(),
    summary: crmApi.summary(),
  };
}

function statusTone(status: string): 'green' | 'yellow' | 'red' | 'blue' | 'slate' {
  if (['Completed', 'Closed', 'Converted', 'Active'].includes(status)) return 'green';
  if (['Rejected', 'Lost'].includes(status)) return 'red';
  if (['In Progress', 'Proposal', 'Negotiation', 'Warm'].includes(status)) return 'blue';
  if (['Pending', 'Pending with Client', 'Open', 'Scheduled'].includes(status)) return 'yellow';
  return 'slate';
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function daysFromNow(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

export function ClientCrmModule() {
  const { page = 'control-centre' } = useParams();
  const activePage = crmTabs.some((tab) => tab.key === page) ? page as CrmPage : 'control-centre';
  const [data, setData] = useState<CrmSnapshot>(() => snapshot());

  const reload = () => setData(snapshot());

  const actions = useCrmActions(data, reload);

  return (
    <div>
      <PageHeader
        title="Client CRM"
        subtitle="Operations, service, relationship management, and future sales pipeline in one client lifecycle workspace."
        action={(
          <button onClick={actions.reset} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            Reset Mock Data
          </button>
        )}
      />
      <nav className="mb-5 flex flex-wrap gap-2">
        {crmTabs.map((tab) => (
          <Link
            key={tab.key}
            to={`/crm/${tab.key}`}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${activePage === tab.key ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'}`}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      {activePage === 'control-centre' && <ControlCentre data={data} actions={actions} />}
      {activePage === 'transactions' && <Transactions data={data.transactions} onAdd={actions.addTransaction} />}
      {activePage === 'redemptions' && <Redemptions data={data.transactions} />}
      {activePage === 'sip' && <SipMonitoring data={data.transactions} />}
      {activePage === 'service-requests' && <ServiceRequests data={data.serviceRequests} onAdd={actions.addServiceRequest} />}
      {activePage === 'alerts' && <Alerts data={data.alerts} />}
      {activePage === 'leads' && <Leads data={data.leads} onAdd={actions.addLead} onConvert={actions.convertLead} />}
      {activePage === 'prospects' && <Prospects data={data.prospects} />}
      {activePage === 'pipeline' && <Pipeline data={data.pipelineOpportunities} onAdd={actions.addPipeline} />}
      {activePage === 'meetings' && <Meetings data={data.meetings} onAdd={actions.addMeeting} />}
      {activePage === 'notes' && <Notes data={data.notes} onAdd={actions.addNote} />}
    </div>
  );
}

type QuickActions = Pick<
  ReturnType<typeof useCrmActions>,
  'addTransaction' | 'addServiceRequest' | 'addLead' | 'addPipeline' | 'addMeeting' | 'addNote'
>;

function useCrmActions(data: CrmSnapshot, reload: () => void) {
  return {
    addTransaction() {
      crmApi.createTransaction({
        owner: 'Priya Mehta',
        status: 'Pending',
        notes: 'Created from React CRM skeleton.',
        clientName: 'New Walk-in Client',
        folioNumber: 'NEW/FOLIO',
        amc: 'HDFC MF',
        schemeName: 'Balanced Advantage Fund',
        transactionType: 'Purchase',
        transactionDate: today(),
        amount: 75000,
        units: 0,
        mode: 'MFU',
      });
      reload();
    },
    addServiceRequest() {
      crmApi.createServiceRequest({
        owner: 'Amit Verma',
        status: 'Open',
        notes: 'Service request created from skeleton UI.',
        clientName: 'New Walk-in Client',
        requestType: 'CAN Modification',
        submittedDate: today(),
        expectedCompletionDate: daysFromNow(7),
        pendingWith: 'Internal',
      });
      reload();
    },
    addLead() {
      crmApi.createLead({
        owner: 'Rahul Sharma',
        status: 'Open',
        notes: 'New prospect captured from a referral.',
        name: `Lead ${data.leads.length + 1}`,
        source: 'Referral',
        stage: 'Discovery',
        estimatedAum: 1000000,
        nextActionDate: daysFromNow(3),
      });
      reload();
    },
    addPipeline() {
      crmApi.createPipelineOpportunity({
        owner: 'Priya Mehta',
        status: 'Proposal',
        notes: 'New pipeline item from skeleton UI.',
        prospectName: 'Pipeline Prospect',
        product: 'Mutual fund portfolio',
        stage: 'Proposal',
        expectedValue: 1500000,
        expectedCloseDate: daysFromNow(21),
      });
      reload();
    },
    addMeeting() {
      crmApi.createMeeting({
        owner: 'Amit Verma',
        status: 'Scheduled',
        notes: 'Meeting created from skeleton UI.',
        subject: 'Introductory discussion',
        clientOrLeadName: 'Pipeline Prospect',
        meetingDate: daysFromNow(2),
        type: 'Intro',
        outcome: '',
      });
      reload();
    },
    addNote() {
      crmApi.createNote({
        owner: 'Priya Mehta',
        status: 'Open',
        notes: 'Follow-up context added from skeleton UI.',
        clientOrLeadName: 'Ramesh Gupta',
        noteType: 'Relationship',
        noteDate: today(),
        summary: 'Prefers concise monthly updates and phone follow-ups.',
      });
      reload();
    },
    convertLead(id: string) {
      crmApi.convertLead(id);
      reload();
    },
    reset() {
      crmApi.reset();
      reload();
    },
  };
}

function ControlCentre({ data, actions }: { data: CrmSnapshot; actions: QuickActions }) {
  const statusMix = useMemo(() => {
    const map = new Map<string, number>();
    data.transactions.forEach((record) => map.set(record.status, (map.get(record.status) || 0) + 1));
    return Array.from(map, ([name, value]) => ({ name, value }));
  }, [data.transactions]);

  const employeeActivity = useMemo(() => {
    const map = new Map<string, number>();
    [...data.transactions, ...data.serviceRequests, ...data.leads].forEach((record) => {
      map.set(record.owner, (map.get(record.owner) || 0) + 1);
    });
    return Array.from(map, ([owner, count]) => ({ owner, count }));
  }, [data]);

  const kpis = [
    { label: 'Open Transactions', value: data.summary.openTransactions, icon: RefreshCw },
    { label: 'Rejected', value: data.summary.rejectedTransactions, icon: AlertTriangle },
    { label: 'Open Service Requests', value: data.summary.openServiceRequests, icon: ClipboardList },
    { label: 'Active Leads', value: data.summary.activeLeads, icon: Users2 },
    { label: 'Pipeline Value', value: formatINR(data.summary.pipelineValue), icon: BarChart3 },
    { label: 'Upcoming Meetings', value: data.summary.meetingsUpcoming, icon: CalendarDays },
  ];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {kpis.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.label}>
              <Icon className="mb-3 text-blue-600" size={22} />
              <div className="text-2xl font-bold text-slate-950">{item.value}</div>
              <div className="text-sm text-slate-500">{item.label}</div>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <div className="mb-3 text-sm font-semibold text-slate-900">Transaction Status Mix</div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={statusMix} dataKey="value" nameKey="name" outerRadius={82} label>
                {statusMix.map((entry, index) => <Cell key={entry.name} fill={pieColors[index % pieColors.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <div className="mb-3 text-sm font-semibold text-slate-900">Owner Activity</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={employeeActivity}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="owner" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card>
        <div className="mb-3 text-sm font-semibold text-slate-900">Quick Mock Actions</div>
        <div className="flex flex-wrap gap-2">
          <ActionButton onClick={actions.addTransaction}>Add Transaction</ActionButton>
          <ActionButton onClick={actions.addServiceRequest}>Add Service Request</ActionButton>
          <ActionButton onClick={actions.addLead}>Add Lead</ActionButton>
          <ActionButton onClick={actions.addPipeline}>Add Pipeline Item</ActionButton>
          <ActionButton onClick={actions.addMeeting}>Add Meeting</ActionButton>
          <ActionButton onClick={actions.addNote}>Add Note</ActionButton>
        </div>
      </Card>
    </div>
  );
}

function ActionButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button onClick={onClick} className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700">
      <Plus size={15} /> {children}
    </button>
  );
}

function Transactions({ data, onAdd }: { data: CrmTransaction[]; onAdd: () => void }) {
  return (
    <ListPage title="Transactions" subtitle="Mock transaction CRUD for future CRM transaction APIs." onAdd={onAdd}>
      <Table
        headers={['Client', 'Type', 'AMC', 'Scheme', 'Amount', 'Status', 'Owner', 'Link']}
        rows={data.map((record) => [
          record.clientName,
          record.transactionType,
          record.amc,
          record.schemeName,
          formatINR(record.amount),
          <Badge tone={statusTone(record.status)}>{record.status}</Badge>,
          record.owner,
          record.familyId || record.clientId || 'Unlinked',
        ])}
      />
    </ListPage>
  );
}

function Redemptions({ data }: { data: CrmTransaction[] }) {
  const redemptions = data.filter((record) => record.transactionType === 'Redemption');
  return (
    <ListPage title="Redemption Follow-ups" subtitle="Tracks redemption credit and reinvestment follow-up until completion.">
      <Table
        headers={['Client', 'Scheme', 'Amount', 'Expected Credit', 'Status', 'Owner', 'Notes']}
        rows={redemptions.map((record) => [
          record.clientName,
          record.schemeName,
          formatINR(record.amount),
          record.expectedDate || '-',
          <Badge tone={statusTone(record.status)}>{record.status}</Badge>,
          record.owner,
          record.notes,
        ])}
      />
    </ListPage>
  );
}

function SipMonitoring({ data }: { data: CrmTransaction[] }) {
  const sips = data.filter((record) => record.transactionType.includes('SIP'));
  return (
    <ListPage title="SIP Monitoring" subtitle="Monitors SIP registrations and cancellations, including activation follow-up.">
      {sips.length ? (
        <Table
          headers={['Client', 'Scheme', 'Amount', 'Date', 'Status', 'Owner']}
          rows={sips.map((record) => [
            record.clientName,
            record.schemeName,
            formatINR(record.amount),
            record.transactionDate,
            <Badge tone={statusTone(record.status)}>{record.status}</Badge>,
            record.owner,
          ])}
        />
      ) : (
        <EmptyState title="No SIP records" detail="Use Add Transaction with SIP Registration once the backend workflow is defined." />
      )}
    </ListPage>
  );
}

function ServiceRequests({ data, onAdd }: { data: ServiceRequest[]; onAdd: () => void }) {
  return (
    <ListPage title="Service Requests" subtitle="SLA-style tracking for client service requests." onAdd={onAdd}>
      <Table
        headers={['Client', 'Type', 'Submitted', 'Expected', 'Pending With', 'Status', 'Owner']}
        rows={data.map((record) => [
          record.clientName,
          record.requestType,
          record.submittedDate,
          record.expectedCompletionDate,
          record.pendingWith,
          <Badge tone={statusTone(record.status)}>{record.status}</Badge>,
          record.owner,
        ])}
      />
    </ListPage>
  );
}

function Alerts({ data }: { data: CrmAlert[] }) {
  return (
    <ListPage title="Alerts" subtitle="Aggregated CRM alerts from transactions, service requests, leads, and future reminders.">
      <div className="space-y-3">
        {data.map((alert) => (
          <Card key={alert.id} className={alert.severity === 'urgent' ? 'border-l-4 border-l-rose-500' : 'border-l-4 border-l-amber-500'}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-sm font-semibold text-slate-900">{alert.title}</div>
                <div className="mt-1 text-sm text-slate-500">{alert.detail}</div>
              </div>
              <Badge tone={alert.severity === 'urgent' ? 'red' : 'yellow'}>{alert.category}</Badge>
            </div>
          </Card>
        ))}
        {!data.length && <EmptyState title="No alerts" detail="No rejected transactions, overdue service requests, or due lead follow-ups." />}
      </div>
    </ListPage>
  );
}

function Leads({ data, onAdd, onConvert }: { data: Lead[]; onAdd: () => void; onConvert: (id: string) => void }) {
  return (
    <ListPage title="Leads" subtitle="Unconverted relationship leads; conversion can create/link a shared client family later." onAdd={onAdd}>
      <Table
        headers={['Lead', 'Source', 'Stage', 'Estimated AUM', 'Next Action', 'Status', 'Owner', 'Conversion']}
        rows={data.map((record) => [
          record.name,
          record.source,
          record.stage,
          formatINR(record.estimatedAum),
          record.nextActionDate,
          <Badge tone={statusTone(record.status)}>{record.status}</Badge>,
          record.owner,
          record.convertedFamilyId ? (
            <Badge tone="green">Linked: {record.convertedFamilyId}</Badge>
          ) : (
            <button onClick={() => onConvert(record.id)} className="text-sm font-semibold text-blue-600 hover:text-blue-700">
              Convert
            </button>
          ),
        ])}
      />
    </ListPage>
  );
}

function Prospects({ data }: { data: Prospect[] }) {
  return (
    <ListPage title="Prospects" subtitle="Qualified prospects before they become clients or compliance family records.">
      <Table
        headers={['Prospect', 'Segment', 'Interest Area', 'Probability', 'Status', 'Owner']}
        rows={data.map((record) => [
          record.name,
          record.segment,
          record.interestArea,
          `${record.probability}%`,
          <Badge tone={statusTone(record.status)}>{record.status}</Badge>,
          record.owner,
        ])}
      />
    </ListPage>
  );
}

function Pipeline({ data, onAdd }: { data: PipelineOpportunity[]; onAdd: () => void }) {
  return (
    <ListPage title="Pipeline" subtitle="Future sales and relationship opportunity tracking." onAdd={onAdd}>
      <Table
        headers={['Prospect', 'Product', 'Stage', 'Expected Value', 'Close Date', 'Owner']}
        rows={data.map((record) => [
          record.prospectName,
          record.product,
          <Badge tone={statusTone(record.stage)}>{record.stage}</Badge>,
          formatINR(record.expectedValue),
          record.expectedCloseDate,
          record.owner,
        ])}
      />
    </ListPage>
  );
}

function Meetings({ data, onAdd }: { data: Meeting[]; onAdd: () => void }) {
  return (
    <ListPage title="Meetings" subtitle="Client and prospect meeting planning, outcomes, and next actions." onAdd={onAdd}>
      <Table
        headers={['Subject', 'Client or Lead', 'Date', 'Type', 'Status', 'Owner', 'Outcome']}
        rows={data.map((record) => [
          record.subject,
          record.clientOrLeadName,
          record.meetingDate,
          record.type,
          <Badge tone={statusTone(record.status)}>{record.status}</Badge>,
          record.owner,
          record.outcome || '-',
        ])}
      />
    </ListPage>
  );
}

function Notes({ data, onAdd }: { data: RelationshipNote[]; onAdd: () => void }) {
  return (
    <ListPage title="Relationship Notes" subtitle="Structured notes for relationship context and future CRM history." onAdd={onAdd}>
      <Table
        headers={['Client or Lead', 'Type', 'Date', 'Summary', 'Owner']}
        rows={data.map((record) => [
          record.clientOrLeadName,
          record.noteType,
          record.noteDate,
          record.summary,
          record.owner,
        ])}
      />
    </ListPage>
  );
}

function ListPage({
  title,
  subtitle,
  children,
  onAdd,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  onAdd?: () => void;
}) {
  const iconMap: Record<string, ReactNode> = {
    Transactions: <RefreshCw size={18} />,
    'Redemption Follow-ups': <Handshake size={18} />,
    'SIP Monitoring': <Repeat size={18} />,
    'Service Requests': <ClipboardList size={18} />,
    Alerts: <Bell size={18} />,
    Leads: <Users2 size={18} />,
    Prospects: <Users2 size={18} />,
    Pipeline: <BarChart3 size={18} />,
    Meetings: <CalendarDays size={18} />,
    'Relationship Notes': <MessageSquareText size={18} />,
  };

  return (
    <div>
      <PageHeader
        title={title}
        subtitle={subtitle}
        action={onAdd ? <ActionButton onClick={onAdd}>Add</ActionButton> : undefined}
      />
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
        {iconMap[title] || <CheckCircle2 size={18} />}
        Mock/local mode
      </div>
      {children}
    </div>
  );
}

function Table({ headers, rows }: { headers: string[]; rows: Array<Array<ReactNode>> }) {
  if (!rows.length) return <EmptyState title="No records" detail="Mock data has no records for this view yet." />;
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            {headers.map((header) => <th key={header} className="whitespace-nowrap px-3 py-2 font-semibold">{header}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-slate-50">
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="whitespace-nowrap px-3 py-2 text-slate-700">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
