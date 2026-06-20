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

const STORAGE_KEY = 'mfu_client_crm_mock_v1';

type CrmStore = {
  transactions: CrmTransaction[];
  serviceRequests: ServiceRequest[];
  leads: Lead[];
  prospects: Prospect[];
  pipelineOpportunities: PipelineOpportunity[];
  meetings: Meeting[];
  notes: RelationshipNote[];
};

type CrmCollectionName = keyof CrmStore;
type CrmRecord = CrmStore[CrmCollectionName][number];

const today = () => new Date().toISOString().slice(0, 10);
const daysFromNow = (days: number) => {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
};
const daysAgo = (days: number) => daysFromNow(-days);
const timestamp = () => new Date().toISOString();
const uid = (prefix: string) => `${prefix}-${Math.random().toString(36).slice(2, 8)}`;

function base(owner = 'Priya Mehta', status = 'Open') {
  const now = timestamp();
  return { owner, status, notes: '', createdAt: now, updatedAt: now };
}

function seedStore(): CrmStore {
  return {
    transactions: [
      {
        id: 'TRX-1001',
        ...base('Priya Mehta', 'Completed'),
        clientName: 'Ramesh Gupta',
        folioNumber: '1102345/67',
        amc: 'HDFC MF',
        schemeName: 'HDFC Flexi Cap Fund',
        transactionType: 'Purchase',
        transactionDate: today(),
        amount: 50000,
        units: 245.32,
        mode: 'Online',
        actualDate: today(),
        familyId: 'demo-family-ramesh',
        notes: 'Lump sum reinvestment completed.',
      },
      {
        id: 'TRX-1002',
        ...base('Amit Verma', 'Pending'),
        clientName: 'Sunita Rao',
        folioNumber: '2204567/89',
        amc: 'SBI MF',
        schemeName: 'SBI Bluechip Fund',
        transactionType: 'Redemption',
        transactionDate: daysAgo(6),
        amount: 150000,
        units: 780.2,
        mode: 'MFU',
        expectedDate: daysAgo(3),
        notes: 'Client plans to reinvest in a debt fund.',
      },
      {
        id: 'TRX-1003',
        ...base('Sneha Joshi', 'Rejected'),
        clientName: 'Deepa Nair',
        folioNumber: '6605432/10',
        amc: 'Nippon India MF',
        schemeName: 'Nippon India Small Cap Fund',
        transactionType: 'Purchase',
        transactionDate: daysAgo(1),
        amount: 100000,
        units: 410.6,
        mode: 'Online',
        notes: 'Payment failed. Awaiting corrected instruction.',
      },
    ],
    serviceRequests: [
      {
        id: 'SR-1001',
        ...base('Priya Mehta', 'In Progress'),
        clientName: 'Ramesh Gupta',
        requestType: 'Bank Change',
        submittedDate: daysAgo(9),
        expectedCompletionDate: daysAgo(2),
        pendingWith: 'AMC - HDFC',
        notes: 'Updated bank proof submitted.',
      },
      {
        id: 'SR-1002',
        ...base('Amit Verma', 'Pending with Client'),
        clientName: 'Sunita Rao',
        requestType: 'KYC Update',
        submittedDate: daysAgo(17),
        expectedCompletionDate: daysAgo(7),
        pendingWith: 'Client',
        notes: 'Awaiting Aadhaar copy.',
      },
    ],
    leads: [
      {
        id: 'LEAD-1001',
        ...base('Rahul Sharma', 'Open'),
        name: 'Kavita Singh',
        source: 'Referral',
        stage: 'Discovery',
        estimatedAum: 2500000,
        nextActionDate: daysFromNow(2),
        notes: 'Interested in retirement planning.',
      },
      {
        id: 'LEAD-1002',
        ...base('Priya Mehta', 'Open'),
        name: 'Mehta Family Office',
        source: 'Existing network',
        stage: 'Proposal',
        estimatedAum: 12000000,
        nextActionDate: daysFromNow(4),
        notes: 'Proposal shared for review.',
      },
    ],
    prospects: [
      {
        id: 'PROS-1001',
        ...base('Amit Verma', 'Warm'),
        name: 'Vikram Shah',
        segment: 'HNI',
        interestArea: 'Equity + debt allocation',
        probability: 65,
        notes: 'Meeting completed; awaiting portfolio statement.',
      },
    ],
    pipelineOpportunities: [
      {
        id: 'PIPE-1001',
        ...base('Rahul Sharma', 'Negotiation'),
        prospectName: 'Mehta Family Office',
        product: 'Managed MF portfolio',
        stage: 'Negotiation',
        expectedValue: 5000000,
        expectedCloseDate: daysFromNow(14),
        notes: 'Pricing and service model under discussion.',
      },
    ],
    meetings: [
      {
        id: 'MEET-1001',
        ...base('Priya Mehta', 'Scheduled'),
        subject: 'Quarterly portfolio review',
        clientOrLeadName: 'Ramesh Gupta',
        meetingDate: daysFromNow(1),
        type: 'Review',
        outcome: '',
        notes: 'Prepare performance and tax summary.',
      },
    ],
    notes: [
      {
        id: 'NOTE-1001',
        ...base('Amit Verma', 'Open'),
        clientOrLeadName: 'Sunita Rao',
        noteType: 'Relationship',
        noteDate: today(),
        summary: 'Prefers low-volatility debt allocation for short-term goals.',
        notes: 'Follow up after redemption credit.',
      },
    ],
  };
}

function readStore(): CrmStore {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    const seeded = seedStore();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(seeded));
    return seeded;
  }
  return JSON.parse(raw) as CrmStore;
}

function writeStore(store: CrmStore) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function list<TName extends CrmCollectionName>(name: TName): CrmStore[TName] {
  return readStore()[name];
}

function create<TName extends CrmCollectionName>(
  name: TName,
  prefix: string,
  payload: Omit<CrmStore[TName][number], 'id' | 'createdAt' | 'updatedAt'>,
) {
  const store = readStore();
  const now = timestamp();
  const record = { ...payload, id: uid(prefix), createdAt: now, updatedAt: now } as CrmStore[TName][number];
  (store[name] as CrmRecord[]).unshift(record as CrmRecord);
  writeStore(store);
  return record;
}

function update<TName extends CrmCollectionName>(
  name: TName,
  id: string,
  patch: Partial<CrmStore[TName][number]>,
) {
  const store = readStore();
  const collection = store[name] as CrmRecord[];
  const index = collection.findIndex((record) => record.id === id);
  if (index === -1) throw new Error('CRM record was not found.');
  const updated = { ...collection[index], ...patch, updatedAt: timestamp() };
  collection[index] = updated as CrmRecord;
  writeStore(store);
  return updated as CrmStore[TName][number];
}

function remove(name: CrmCollectionName, id: string) {
  const store = readStore();
  const collection = store[name] as CrmRecord[];
  store[name] = collection.filter((record) => record.id !== id) as never;
  writeStore(store);
}

// Future microservice handoff:
// Replace these local methods with:
// GET/POST/PATCH/DELETE /api/v1/crm/transactions
// GET/POST/PATCH/DELETE /api/v1/crm/service-requests
// GET/POST/PATCH/DELETE /api/v1/crm/leads
// GET/POST/PATCH/DELETE /api/v1/crm/prospects
// GET/POST/PATCH/DELETE /api/v1/crm/pipeline-opportunities
// GET/POST/PATCH/DELETE /api/v1/crm/meetings
// GET/POST/PATCH/DELETE /api/v1/crm/notes
// GET /api/v1/crm/summary
// GET /api/v1/crm/alerts
export const crmApi = {
  listTransactions: () => list('transactions'),
  createTransaction: (payload: Omit<CrmTransaction, 'id' | 'createdAt' | 'updatedAt'>) =>
    create('transactions', 'TRX', payload),
  updateTransaction: (id: string, patch: Partial<CrmTransaction>) => update('transactions', id, patch),
  deleteTransaction: (id: string) => remove('transactions', id),

  listServiceRequests: () => list('serviceRequests'),
  createServiceRequest: (payload: Omit<ServiceRequest, 'id' | 'createdAt' | 'updatedAt'>) =>
    create('serviceRequests', 'SR', payload),
  updateServiceRequest: (id: string, patch: Partial<ServiceRequest>) => update('serviceRequests', id, patch),
  deleteServiceRequest: (id: string) => remove('serviceRequests', id),

  listLeads: () => list('leads'),
  createLead: (payload: Omit<Lead, 'id' | 'createdAt' | 'updatedAt'>) => create('leads', 'LEAD', payload),
  updateLead: (id: string, patch: Partial<Lead>) => update('leads', id, patch),
  deleteLead: (id: string) => remove('leads', id),

  listProspects: () => list('prospects'),
  createProspect: (payload: Omit<Prospect, 'id' | 'createdAt' | 'updatedAt'>) =>
    create('prospects', 'PROS', payload),
  updateProspect: (id: string, patch: Partial<Prospect>) => update('prospects', id, patch),
  deleteProspect: (id: string) => remove('prospects', id),

  listPipelineOpportunities: () => list('pipelineOpportunities'),
  createPipelineOpportunity: (payload: Omit<PipelineOpportunity, 'id' | 'createdAt' | 'updatedAt'>) =>
    create('pipelineOpportunities', 'PIPE', payload),
  updatePipelineOpportunity: (id: string, patch: Partial<PipelineOpportunity>) =>
    update('pipelineOpportunities', id, patch),
  deletePipelineOpportunity: (id: string) => remove('pipelineOpportunities', id),

  listMeetings: () => list('meetings'),
  createMeeting: (payload: Omit<Meeting, 'id' | 'createdAt' | 'updatedAt'>) => create('meetings', 'MEET', payload),
  updateMeeting: (id: string, patch: Partial<Meeting>) => update('meetings', id, patch),
  deleteMeeting: (id: string) => remove('meetings', id),

  listNotes: () => list('notes'),
  createNote: (payload: Omit<RelationshipNote, 'id' | 'createdAt' | 'updatedAt'>) => create('notes', 'NOTE', payload),
  updateNote: (id: string, patch: Partial<RelationshipNote>) => update('notes', id, patch),
  deleteNote: (id: string) => remove('notes', id),

  convertLead: (id: string, familyId = 'pending-family-link') =>
    update('leads', id, { status: 'Converted', stage: 'Converted', convertedFamilyId: familyId }),

  summary: () => {
    const store = readStore();
    return {
      openTransactions: store.transactions.filter((record) => !['Completed', 'Closed'].includes(record.status)).length,
      rejectedTransactions: store.transactions.filter((record) => record.status === 'Rejected').length,
      openServiceRequests: store.serviceRequests.filter((record) => !['Completed', 'Closed'].includes(record.status)).length,
      activeLeads: store.leads.filter((record) => record.status !== 'Converted').length,
      pipelineValue: store.pipelineOpportunities.reduce((sum, record) => sum + record.expectedValue, 0),
      meetingsUpcoming: store.meetings.filter((record) => record.meetingDate >= today()).length,
    };
  },

  alerts: (): CrmAlert[] => {
    const store = readStore();
    return [
      ...store.transactions
        .filter((record) => record.status === 'Rejected')
        .map((record) => ({
          id: `alert-${record.id}`,
          severity: 'urgent' as const,
          category: 'Transactions',
          title: `${record.clientName} transaction rejected`,
          detail: `${record.transactionType} in ${record.schemeName}: ${record.notes}`,
          owner: record.owner,
        })),
      ...store.serviceRequests
        .filter((record) => !['Completed', 'Closed'].includes(record.status) && record.expectedCompletionDate < today())
        .map((record) => ({
          id: `alert-${record.id}`,
          severity: 'urgent' as const,
          category: 'Service Requests',
          title: `${record.clientName} service request is over SLA`,
          detail: `${record.requestType} pending with ${record.pendingWith}`,
          owner: record.owner,
        })),
      ...store.leads
        .filter((record) => record.status !== 'Converted' && record.nextActionDate <= today())
        .map((record) => ({
          id: `alert-${record.id}`,
          severity: 'follow_up' as const,
          category: 'Leads',
          title: `${record.name} needs relationship follow-up`,
          detail: `${record.stage} lead from ${record.source}`,
          owner: record.owner,
        })),
    ];
  },

  reset: () => {
    const seeded = seedStore();
    writeStore(seeded);
    return seeded;
  },
};
