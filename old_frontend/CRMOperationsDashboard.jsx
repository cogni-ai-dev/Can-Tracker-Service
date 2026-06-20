import React, { useState, useMemo, useEffect } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import {
  LayoutDashboard, Receipt, RefreshCw, Repeat, ClipboardList, Bell, Plus, X,
  AlertTriangle, CheckCircle2, Clock, ChevronRight, Search, Link2,
  ArrowDownCircle, ArrowUpCircle, Users2, Building2, FileWarning, FolderClock,
} from 'lucide-react';

/* ============================== CONSTANTS ============================== */

const TRANSACTION_TYPES = [
  'Purchase', 'Redemption', 'Switch In', 'Switch Out',
  'SIP Registration', 'SIP Cancellation',
  'STP Registration', 'STP Cancellation',
  'SWP Registration', 'SWP Cancellation',
  'Any Other Service Request',
];

const STATUS_OPTIONS = ['Submitted', 'In Process', 'Completed', 'Rejected'];

const MODES = ['Physical', 'Online', 'MFU', 'BSE Star', 'NSE NMF', 'AMC Portal', 'Other'];

const EMPLOYEES = ['Priya Mehta', 'Amit Verma', 'Sneha Joshi', 'Rahul Sharma', 'Rohit Kulkarni'];

const AMCS = [
  'HDFC MF', 'ICICI Prudential MF', 'SBI MF', 'Axis MF', 'Kotak MF',
  'Nippon India MF', 'Aditya Birla SL MF', 'UTI MF', 'Franklin Templeton MF',
  'Mirae Asset MF', 'Other',
];

const SR_TYPES = [
  'Bank Change', 'Nominee Addition/Modification', 'Address Change',
  'Mobile Number Change', 'Email Change', 'FATCA Update', 'KYC Update',
  'Transmission', 'CAN Creation', 'CAN Modification', 'Folio Consolidation',
  'SIP Modification', 'SWP Modification', 'STP Modification',
  'NPS Related Requests', 'Insurance Service Requests', 'Other Custom Requests',
];

const SR_STATUS_OPTIONS = ['Open', 'In Progress', 'Pending with Client', 'Pending with AMC', 'Completed', 'Closed'];

const SIP_STATUS_OPTIONS = ['Submitted', 'Awaiting Registration', 'Active', 'Rejected', 'Mandate Pending', 'Under Follow-up'];

const REINVEST_STATUS_OPTIONS = ['Pending', 'Reinvested', 'Not Required'];

const SR_SLA = {
  'Bank Change': 7,
  'Nominee Addition/Modification': 10,
  'Address Change': 7,
  'Mobile Number Change': 3,
  'Email Change': 3,
  'FATCA Update': 7,
  'KYC Update': 10,
  'Transmission': 30,
  'CAN Creation': 10,
  'CAN Modification': 10,
  'Folio Consolidation': 15,
  'SIP Modification': 7,
  'SWP Modification': 7,
  'STP Modification': 7,
  'NPS Related Requests': 15,
  'Insurance Service Requests': 10,
  'Other Custom Requests': 7,
};

const TABS = [
  { key: 'overview', label: 'Control Centre', icon: LayoutDashboard },
  { key: 'transactions', label: 'Transactions', icon: Receipt },
  { key: 'redemptions', label: 'Redemption Follow-ups', icon: RefreshCw },
  { key: 'sip', label: 'SIP Monitoring', icon: Repeat },
  { key: 'service', label: 'Service Requests', icon: ClipboardList },
  { key: 'notifications', label: 'Alerts', icon: Bell },
];

/* ============================== HELPERS ============================== */

const pad = (n) => String(n).padStart(2, '0');
const isoDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const todayStr = () => isoDate(new Date());
const daysAgo = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return isoDate(d); };
const daysFromNow = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return isoDate(d); };

const daysBetween = (dateStr, refStr) => {
  if (!dateStr) return 0;
  const a = new Date(dateStr + 'T00:00:00');
  const b = new Date((refStr || todayStr()) + 'T00:00:00');
  return Math.round((b - a) / 86400000);
};

const fmtDate = (dateStr) => {
  if (!dateStr) return '—';
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

const fmtShortDate = (dateStr) => {
  if (!dateStr) return '—';
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
};

const fmtINR = (n) => {
  if (n === null || n === undefined || n === '' || Number.isNaN(Number(n))) return '—';
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(n));
};

const fmtNum = (n, dp = 2) => {
  if (n === null || n === undefined || n === '' || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('en-IN', { maximumFractionDigits: dp });
};

let idCounter = 1000;
const uid = (prefix) => { idCounter += 1; return `${prefix}-${idCounter}`; };

/* ============================== STYLE MAPS ============================== */

const STATUS_STYLES = {
  Completed: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  Active: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  Reinvested: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  Closed: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  'Not Required': 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',

  'In Process': 'bg-amber-50 text-amber-700 ring-amber-600/20',
  'In Progress': 'bg-amber-50 text-amber-700 ring-amber-600/20',
  Submitted: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  'Awaiting Registration': 'bg-amber-50 text-amber-700 ring-amber-600/20',
  'Under Follow-up': 'bg-amber-50 text-amber-700 ring-amber-600/20',
  'Mandate Pending': 'bg-amber-50 text-amber-700 ring-amber-600/20',
  Pending: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  Open: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  'Pending with Client': 'bg-amber-50 text-amber-700 ring-amber-600/20',
  'Pending with AMC': 'bg-amber-50 text-amber-700 ring-amber-600/20',

  Rejected: 'bg-rose-50 text-rose-700 ring-rose-600/20',
};
const DEFAULT_STATUS_STYLE = 'bg-slate-100 text-slate-600 ring-slate-500/20';

const ACCENT_STYLES = {
  indigo: 'bg-indigo-50 text-indigo-600',
  emerald: 'bg-emerald-50 text-emerald-600',
  rose: 'bg-rose-50 text-rose-600',
  sky: 'bg-sky-50 text-sky-600',
  amber: 'bg-amber-50 text-amber-600',
  slate: 'bg-slate-100 text-slate-600',
};

const SEVERITY_STYLES = {
  red: { border: 'border-l-rose-500', chip: 'bg-rose-50 text-rose-700 ring-rose-600/20', dot: 'bg-rose-500' },
  yellow: { border: 'border-l-amber-500', chip: 'bg-amber-50 text-amber-700 ring-amber-600/20', dot: 'bg-amber-500' },
  green: { border: 'border-l-emerald-500', chip: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20', dot: 'bg-emerald-500' },
};

const PIE_COLORS = ['#10b981', '#f59e0b', '#6366f1', '#f43f5e', '#0ea5e9', '#94a3b8'];

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_STYLES[status] || DEFAULT_STATUS_STYLE}`}>
      {status}
    </span>
  );
}

function StatusSelect({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`rounded-full border-0 px-2 py-0.5 text-xs font-medium ring-1 ring-inset focus:outline-none focus:ring-2 focus:ring-indigo-500 ${STATUS_STYLES[value] || DEFAULT_STATUS_STYLE}`}
    >
      {options.map((o) => <option key={o} value={o}>{o}</option>)}
    </select>
  );
}

/* ============================== SEED DATA ============================== */

function buildSeedTransactions() {
  const reinvestPurchaseId = uid('TXN');
  return [
    {
      id: reinvestPurchaseId,
      clientName: 'Ramesh Gupta', folioNumber: '1102345/67', amc: 'HDFC MF', schemeName: 'HDFC Flexi Cap Fund',
      transactionType: 'Purchase', transactionDate: daysAgo(0), amount: 50000, units: 245.32,
      status: 'Completed', mode: 'Online', employee: 'Priya Mehta',
      remarks: 'Lump sum reinvestment from recent ELSS redemption', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Ramesh Gupta', folioNumber: '1102345/67', amc: 'HDFC MF', schemeName: 'HDFC Top 100 Fund',
      transactionType: 'Redemption', transactionDate: daysAgo(10), amount: 200000, units: 1023.5,
      status: 'Completed', mode: 'BSE Star', employee: 'Priya Mehta',
      remarks: 'Redeemed to reinvest into Flexi Cap Fund', awaitingDocuments: false,
      isReinvestment: true, expectedCreditDate: daysAgo(7), actualCreditDate: daysAgo(7),
      reinvestmentScheme: 'HDFC Flexi Cap Fund', reinvestmentStatus: 'Reinvested', reinvestmentLinkedTxnId: reinvestPurchaseId,
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Sunita Rao', folioNumber: '2204567/89', amc: 'SBI MF', schemeName: 'SBI Bluechip Fund',
      transactionType: 'Redemption', transactionDate: daysAgo(6), amount: 150000, units: 780.2,
      status: 'Completed', mode: 'MFU', employee: 'Amit Verma',
      remarks: 'Client requested partial redemption; reinvest later in debt fund', awaitingDocuments: false,
      isReinvestment: true, expectedCreditDate: daysAgo(3), actualCreditDate: daysAgo(3),
      reinvestmentScheme: '', reinvestmentStatus: 'Pending', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Anil Kapoor', folioNumber: '3309876/54', amc: 'Axis MF', schemeName: 'Axis Long Term Equity Fund',
      transactionType: 'SIP Registration', transactionDate: daysAgo(40), amount: 5000, units: '',
      status: 'Submitted', mode: 'Physical', employee: 'Sneha Joshi',
      remarks: 'Physical SIP form submitted to AMC branch', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: daysAgo(40), expectedActivationDate: daysAgo(10), sipStatus: 'Submitted',
    },
    {
      id: uid('TXN'),
      clientName: 'Meena Iyer', folioNumber: '4401122/33', amc: 'ICICI Prudential MF', schemeName: 'ICICI Pru Bluechip Fund',
      transactionType: 'SIP Registration', transactionDate: daysAgo(9), amount: 10000, units: '',
      status: 'In Process', mode: 'Physical', employee: 'Rahul Sharma',
      remarks: 'Awaiting bank mandate confirmation', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: daysAgo(9), expectedActivationDate: daysFromNow(21), sipStatus: 'Mandate Pending',
    },
    {
      id: uid('TXN'),
      clientName: 'Vikram Shah', folioNumber: '5501239/87', amc: 'Kotak MF', schemeName: 'Kotak Standard Multicap Fund',
      transactionType: 'Switch Out', transactionDate: daysAgo(2), amount: 75000, units: 320.4,
      status: 'Completed', mode: 'AMC Portal', employee: 'Amit Verma',
      remarks: 'Switched into Kotak Emerging Equity Fund', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Deepa Nair', folioNumber: '6605432/10', amc: 'Nippon India MF', schemeName: 'Nippon India Small Cap Fund',
      transactionType: 'Purchase', transactionDate: daysAgo(1), amount: 100000, units: 410.6,
      status: 'Rejected', mode: 'Online', employee: 'Sneha Joshi',
      remarks: 'Payment failed - cheque bounced, client to resubmit', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Rohan Das', folioNumber: '7709871/22', amc: 'Aditya Birla SL MF', schemeName: 'ABSL Frontline Equity Fund',
      transactionType: 'Redemption', transactionDate: daysAgo(13), amount: 300000, units: 1500,
      status: 'Completed', mode: 'AMC Portal', employee: 'Rahul Sharma',
      remarks: 'Reinvest into debt fund as part of year-end tax planning', awaitingDocuments: false,
      isReinvestment: true, expectedCreditDate: daysAgo(10), actualCreditDate: daysAgo(10),
      reinvestmentScheme: 'ABSL Corporate Bond Fund', reinvestmentStatus: 'Pending', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Kavita Singh', folioNumber: '8807654/33', amc: 'HDFC MF', schemeName: 'HDFC Corporate Bond Fund',
      transactionType: 'STP Registration', transactionDate: daysAgo(5), amount: 20000, units: '',
      status: 'Completed', mode: 'Online', employee: 'Priya Mehta',
      remarks: 'Monthly STP set up from liquid fund into corporate bond fund', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Suresh Menon', folioNumber: '9901234/55', amc: 'SBI MF', schemeName: 'SBI Liquid Fund',
      transactionType: 'SWP Registration', transactionDate: daysAgo(7), amount: 15000, units: '',
      status: 'In Process', mode: 'BSE Star', employee: 'Amit Verma',
      remarks: 'Monthly SWP for retirement income - awaiting signed cancelled cheque', awaitingDocuments: true,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Pooja Bhatt', folioNumber: '1011223/44', amc: 'Axis MF', schemeName: 'Axis Bluechip Fund',
      transactionType: 'Purchase', transactionDate: daysAgo(0), amount: 25000, units: 98.7,
      status: 'Completed', mode: 'MFU', employee: 'Sneha Joshi',
      remarks: 'SIP top-up lump sum', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Arjun Mehta', folioNumber: '1223344/55', amc: 'Kotak MF', schemeName: 'Kotak Flexicap Fund',
      transactionType: 'Any Other Service Request', transactionDate: daysAgo(3), amount: '', units: '',
      status: 'In Process', mode: 'Physical', employee: 'Rahul Sharma',
      remarks: 'Address change form submitted along with address proof', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Ramesh Gupta', folioNumber: '1102345/67', amc: 'HDFC MF', schemeName: 'HDFC Flexi Cap Fund',
      transactionType: 'SIP Registration', transactionDate: daysAgo(12), amount: 8000, units: '',
      status: 'In Process', mode: 'MFU', employee: 'Priya Mehta',
      remarks: 'New SIP registered via MFU portal', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: daysAgo(12), expectedActivationDate: daysFromNow(18), sipStatus: 'Awaiting Registration',
    },
    {
      id: uid('TXN'),
      clientName: 'Sunita Rao', folioNumber: '2204567/89', amc: 'SBI MF', schemeName: 'SBI Bluechip Fund',
      transactionType: 'Purchase', transactionDate: daysAgo(25), amount: 100000, units: 520,
      status: 'Completed', mode: 'Online', employee: 'Amit Verma',
      remarks: 'Initial lump sum investment', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: '', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
    {
      id: uid('TXN'),
      clientName: 'Deepa Nair', folioNumber: '6605432/10', amc: 'Nippon India MF', schemeName: 'Nippon India Growth Fund',
      transactionType: 'Redemption', transactionDate: daysAgo(1), amount: 50000, units: 200,
      status: 'Completed', mode: 'NSE NMF', employee: 'Sneha Joshi',
      remarks: 'Full redemption for personal use, no reinvestment planned', awaitingDocuments: false,
      isReinvestment: false, expectedCreditDate: '', actualCreditDate: '', reinvestmentScheme: '', reinvestmentStatus: 'Not Required', reinvestmentLinkedTxnId: '',
      submissionDate: '', expectedActivationDate: '', sipStatus: '',
    },
  ];
}

function buildSeedServiceRequests() {
  return [
    {
      id: uid('SR'), clientName: 'Ramesh Gupta', requestType: 'Bank Change', dateSubmitted: daysAgo(9),
      employeeAssigned: 'Priya Mehta', currentStatus: 'In Progress', expectedCompletionDate: daysAgo(2),
      actualCompletionDate: '', pendingWith: 'AMC - HDFC', followUpNotes: 'Updated bank proof submitted; awaiting AMC confirmation.',
    },
    {
      id: uid('SR'), clientName: 'Sunita Rao', requestType: 'KYC Update', dateSubmitted: daysAgo(17),
      employeeAssigned: 'Amit Verma', currentStatus: 'Pending with Client', expectedCompletionDate: daysAgo(7),
      actualCompletionDate: '', pendingWith: 'Client - documents', followUpNotes: 'Client yet to submit updated Aadhaar copy for KYC re-verification.',
    },
    {
      id: uid('SR'), clientName: 'Anil Kapoor', requestType: 'FATCA Update', dateSubmitted: daysAgo(4),
      employeeAssigned: 'Sneha Joshi', currentStatus: 'Open', expectedCompletionDate: daysFromNow(3),
      actualCompletionDate: '', pendingWith: 'Internal', followUpNotes: 'FATCA declaration form to be collected at next client visit.',
    },
    {
      id: uid('SR'), clientName: 'Vikram Shah', requestType: 'Nominee Addition/Modification', dateSubmitted: daysAgo(8),
      employeeAssigned: 'Rahul Sharma', currentStatus: 'Completed', expectedCompletionDate: daysAgo(1),
      actualCompletionDate: daysAgo(2), pendingWith: '', followUpNotes: 'Nominee updated successfully across all folios.',
    },
    {
      id: uid('SR'), clientName: 'Rohan Das', requestType: 'Transmission', dateSubmitted: daysAgo(35),
      employeeAssigned: 'Priya Mehta', currentStatus: 'In Progress', expectedCompletionDate: daysAgo(5),
      actualCompletionDate: '', pendingWith: 'AMC - Aditya Birla SL', followUpNotes: 'Legal heir documents and death certificate submitted; AMC processing transmission.',
    },
    {
      id: uid('SR'), clientName: 'Meena Iyer', requestType: 'CAN Creation', dateSubmitted: daysAgo(2),
      employeeAssigned: 'Amit Verma', currentStatus: 'Open', expectedCompletionDate: daysFromNow(8),
      actualCompletionDate: '', pendingWith: 'MFU', followUpNotes: 'New CAN application submitted via MFU portal.',
    },
  ];
}

/* ============================== MAIN COMPONENT ============================== */

export default function CRMOperationsDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [transactions, setTransactions] = useState(buildSeedTransactions);
  const [serviceRequests, setServiceRequests] = useState(buildSeedServiceRequests);
  const [showTxnModal, setShowTxnModal] = useState(false);
  const [showSRModal, setShowSRModal] = useState(false);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [showCompletedReinvest, setShowCompletedReinvest] = useState(false);
  const [now, setNow] = useState(new Date());

  const [filters, setFilters] = useState({
    client: '', employee: '', type: '', amc: '', status: '', dateFrom: '', dateTo: '',
  });

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  /* -------- mutation handlers -------- */

  const addTransaction = (form) => {
    const newTxn = {
      id: uid('TXN'),
      clientName: form.clientName,
      folioNumber: form.folioNumber,
      amc: form.amc,
      schemeName: form.schemeName,
      transactionType: form.transactionType,
      transactionDate: form.transactionDate,
      amount: form.amount === '' ? '' : Number(form.amount),
      units: form.units === '' ? '' : Number(form.units),
      status: form.status,
      mode: form.mode,
      employee: form.employee,
      remarks: form.remarks,
      awaitingDocuments: form.awaitingDocuments,
      isReinvestment: form.transactionType === 'Redemption' ? form.isReinvestment : false,
      expectedCreditDate: form.transactionType === 'Redemption' && form.isReinvestment ? form.expectedCreditDate : '',
      actualCreditDate: '',
      reinvestmentScheme: form.transactionType === 'Redemption' && form.isReinvestment ? form.reinvestmentScheme : '',
      reinvestmentStatus: form.transactionType === 'Redemption' && form.isReinvestment ? 'Pending' : '',
      reinvestmentLinkedTxnId: '',
      submissionDate: form.transactionType === 'SIP Registration' ? form.transactionDate : '',
      expectedActivationDate: form.transactionType === 'SIP Registration' ? form.expectedActivationDate : '',
      sipStatus: form.transactionType === 'SIP Registration' ? form.sipStatus : '',
    };

    setTransactions((prev) => {
      let updated = [newTxn, ...prev];
      if (form.transactionType === 'Purchase' && form.linkedRedemptionId) {
        updated = updated.map((t) => (t.id === form.linkedRedemptionId
          ? {
            ...t,
            reinvestmentStatus: 'Reinvested',
            reinvestmentLinkedTxnId: newTxn.id,
            reinvestmentScheme: t.reinvestmentScheme || newTxn.schemeName,
            actualCreditDate: t.actualCreditDate || newTxn.transactionDate,
          }
          : t));
      }
      return updated;
    });
    setShowTxnModal(false);
  };

  const updateTransaction = (id, patch) => {
    setTransactions((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));
  };

  const addServiceRequest = (form) => {
    const newSR = { id: uid('SR'), ...form };
    setServiceRequests((prev) => [newSR, ...prev]);
    setShowSRModal(false);
  };

  const updateServiceRequest = (id, patch) => {
    setServiceRequests((prev) => prev.map((sr) => (sr.id === id ? { ...sr, ...patch } : sr)));
  };

  /* -------- derived data -------- */

  const today = todayStr();

  const pendingReinvestments = useMemo(
    () => transactions.filter((t) => t.transactionType === 'Redemption' && t.isReinvestment && t.reinvestmentStatus === 'Pending'),
    [transactions],
  );

  const resolvedReinvestments = useMemo(
    () => transactions.filter((t) => t.transactionType === 'Redemption' && t.isReinvestment && t.reinvestmentStatus !== 'Pending'),
    [transactions],
  );

  const sipRegistrations = useMemo(
    () => transactions.filter((t) => t.transactionType === 'SIP Registration'),
    [transactions],
  );

  const overdueSIPs = useMemo(
    () => sipRegistrations.filter((t) => !['Active', 'Rejected'].includes(t.sipStatus) && daysBetween(t.submissionDate, today) > 30),
    [sipRegistrations, today],
  );

  const overdueServiceRequests = useMemo(
    () => serviceRequests.filter((sr) => !['Completed', 'Closed'].includes(sr.currentStatus)
      && daysBetween(sr.dateSubmitted, today) > (SR_SLA[sr.requestType] || 7)),
    [serviceRequests, today],
  );

  const rejectedTxns = useMemo(() => transactions.filter((t) => t.status === 'Rejected'), [transactions]);

  const awaitingDocsTxns = useMemo(() => transactions.filter((t) => t.awaitingDocuments), [transactions]);

  const kycFatcaCases = useMemo(
    () => serviceRequests.filter((sr) => (sr.requestType === 'KYC Update' || sr.requestType === 'FATCA Update')
      && !['Completed', 'Closed'].includes(sr.currentStatus)),
    [serviceRequests],
  );

  const existingClients = useMemo(
    () => Array.from(new Set(transactions.map((t) => t.clientName))).sort(),
    [transactions],
  );

  /* -------- notification center -------- */

  const notifications = useMemo(() => {
    const groups = [];

    groups.push({
      key: 'reinvest', title: 'Pending Redemptions Awaiting Reinvestment', icon: RefreshCw,
      items: pendingReinvestments.map((t) => {
        const days = daysBetween(t.actualCreditDate || t.expectedCreditDate || t.transactionDate, today);
        return {
          id: t.id, severity: days > 7 ? 'red' : 'yellow',
          title: `${t.clientName} — ${fmtINR(t.amount)} redeemed from ${t.schemeName}`,
          subtitle: `Credited ${fmtDate(t.actualCreditDate || t.expectedCreditDate)} · ${days} day(s) awaiting reinvestment · Owner: ${t.employee}`,
        };
      }),
    });

    groups.push({
      key: 'sip', title: 'SIP Registrations Pending Beyond 30 Days', icon: Repeat,
      items: overdueSIPs.map((t) => {
        const days = daysBetween(t.submissionDate, today);
        return {
          id: t.id, severity: 'red',
          title: `${t.clientName} — ${t.schemeName} (${t.amc})`,
          subtitle: `Submitted ${fmtDate(t.submissionDate)} · ${days} days elapsed · Status: ${t.sipStatus} · Owner: ${t.employee}`,
        };
      }),
    });

    groups.push({
      key: 'sr', title: 'Service Requests Pending Beyond SLA', icon: FolderClock,
      items: overdueServiceRequests.map((sr) => {
        const days = daysBetween(sr.dateSubmitted, today);
        const sla = SR_SLA[sr.requestType] || 7;
        return {
          id: sr.id, severity: 'red',
          title: `${sr.clientName} — ${sr.requestType}`,
          subtitle: `Submitted ${fmtDate(sr.dateSubmitted)} · ${days} days elapsed (SLA ${sla}d) · Pending with: ${sr.pendingWith || '—'} · Owner: ${sr.employeeAssigned}`,
        };
      }),
    });

    groups.push({
      key: 'rejected', title: 'Rejected Transactions', icon: AlertTriangle,
      items: rejectedTxns.map((t) => ({
        id: t.id, severity: 'red',
        title: `${t.clientName} — ${t.transactionType} of ${fmtINR(t.amount)} rejected`,
        subtitle: `${t.schemeName} (${t.amc}) · ${fmtDate(t.transactionDate)} · ${t.remarks || 'No remarks'} · Owner: ${t.employee}`,
      })),
    });

    groups.push({
      key: 'docs', title: 'Transactions Awaiting Client Documents', icon: FileWarning,
      items: awaitingDocsTxns.map((t) => ({
        id: t.id, severity: 'yellow',
        title: `${t.clientName} — ${t.transactionType} (${t.schemeName})`,
        subtitle: `${fmtDate(t.transactionDate)} · ${t.remarks || 'Documents pending from client'} · Owner: ${t.employee}`,
      })),
    });

    groups.push({
      key: 'kyc', title: 'Pending KYC / FATCA Cases', icon: ClipboardList,
      items: kycFatcaCases.map((sr) => {
        const days = daysBetween(sr.dateSubmitted, today);
        const overdue = days > (SR_SLA[sr.requestType] || 7);
        return {
          id: sr.id, severity: overdue ? 'red' : 'yellow',
          title: `${sr.clientName} — ${sr.requestType}`,
          subtitle: `Submitted ${fmtDate(sr.dateSubmitted)} · Status: ${sr.currentStatus} · Owner: ${sr.employeeAssigned}`,
        };
      }),
    });

    return groups;
  }, [pendingReinvestments, overdueSIPs, overdueServiceRequests, rejectedTxns, awaitingDocsTxns, kycFatcaCases, today]);

  const redCount = notifications.reduce((sum, g) => sum + g.items.filter((i) => i.severity === 'red').length, 0);
  const yellowCount = notifications.reduce((sum, g) => sum + g.items.filter((i) => i.severity === 'yellow').length, 0);
  const totalAlerts = redCount + yellowCount;

  /* -------- management dashboard metrics -------- */

  const transactionsToday = transactions.filter((t) => t.transactionDate === today).length;
  const purchasesToday = transactions.filter((t) => t.transactionDate === today && t.transactionType === 'Purchase').length;
  const redemptionsToday = transactions.filter((t) => t.transactionDate === today && t.transactionType === 'Redemption').length;
  const sipsRegisteredTotal = sipRegistrations.length;
  const serviceRequestsOpen = serviceRequests.filter((sr) => !['Completed', 'Closed'].includes(sr.currentStatus)).length;
  const serviceRequestsClosed = serviceRequests.filter((sr) => ['Completed', 'Closed'].includes(sr.currentStatus)).length;
  const overdueTasksCount = pendingReinvestments.length + overdueSIPs.length + overdueServiceRequests.length;

  const kpis = [
    { label: 'Transactions Today', value: transactionsToday, icon: Receipt, accent: 'indigo' },
    { label: 'Purchases Today', value: purchasesToday, icon: ArrowDownCircle, accent: 'emerald' },
    { label: 'Redemptions Today', value: redemptionsToday, icon: ArrowUpCircle, accent: 'rose' },
    { label: 'SIPs Registered (Total)', value: sipsRegisteredTotal, icon: Repeat, accent: 'sky' },
    { label: 'SIPs Pending Verification', value: overdueSIPs.length, icon: AlertTriangle, accent: 'amber' },
    { label: 'Service Requests Open', value: serviceRequestsOpen, icon: ClipboardList, accent: 'indigo' },
    { label: 'Service Requests Closed', value: serviceRequestsClosed, icon: CheckCircle2, accent: 'emerald' },
    { label: 'Overdue Tasks', value: overdueTasksCount, icon: Clock, accent: 'rose' },
  ];

  const amcBusiness = useMemo(() => {
    const map = {};
    transactions.forEach((t) => {
      if (t.amount !== '' && t.amount !== null && t.amount !== undefined) {
        map[t.amc] = (map[t.amc] || 0) + Number(t.amount);
      }
    });
    return Object.entries(map).map(([amc, total]) => ({ amc, total })).sort((a, b) => b.total - a.total);
  }, [transactions]);

  const employeeProductivity = useMemo(() => {
    const map = {};
    transactions.forEach((t) => { map[t.employee] = (map[t.employee] || 0) + 1; });
    return Object.entries(map).map(([employee, count]) => ({ employee, count })).sort((a, b) => b.count - a.count);
  }, [transactions]);

  const dailyTrend = useMemo(() => {
    const days = [];
    for (let i = 6; i >= 0; i -= 1) {
      const ds = daysAgo(i);
      const count = transactions.filter((t) => t.transactionDate === ds).length;
      days.push({ date: fmtShortDate(ds), count });
    }
    return days;
  }, [transactions]);

  const statusDistribution = useMemo(() => {
    const map = {};
    transactions.forEach((t) => { map[t.status] = (map[t.status] || 0) + 1; });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  }, [transactions]);

  /* -------- transactions table filtering -------- */

  const filteredTransactions = useMemo(() => transactions.filter((t) => {
    if (filters.client && !t.clientName.toLowerCase().includes(filters.client.toLowerCase())) return false;
    if (filters.employee && t.employee !== filters.employee) return false;
    if (filters.type && t.transactionType !== filters.type) return false;
    if (filters.amc && t.amc !== filters.amc) return false;
    if (filters.status && t.status !== filters.status) return false;
    if (filters.dateFrom && t.transactionDate < filters.dateFrom) return false;
    if (filters.dateTo && t.transactionDate > filters.dateTo) return false;
    return true;
  }), [transactions, filters]);

  const clearFilters = () => setFilters({ client: '', employee: '', type: '', amc: '', status: '', dateFrom: '', dateTo: '' });

  /* ============================== RENDER ============================== */

  return (
    <div className="flex h-[820px] w-full overflow-hidden rounded-xl border border-slate-200 bg-slate-50 font-sans text-slate-800">

      {/* ---------------- Sidebar ---------------- */}
      <aside className="flex w-60 flex-shrink-0 flex-col bg-slate-900 text-slate-200">
        <div className="border-b border-slate-700/60 px-5 py-5">
          <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400">Ops Console</p>
          <h1 className="mt-1 text-lg font-bold leading-tight text-white">Mutual Fund Distribution</h1>
          <p className="mt-1 text-xs text-slate-400">Transaction &amp; Service Tracker</p>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.key;
            const badge = tab.key === 'notifications' ? totalAlerts : 0;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  active ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <span className="flex items-center gap-2">
                  <Icon size={16} />
                  {tab.label}
                </span>
                {badge > 0 && (
                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${active ? 'bg-white/20 text-white' : 'bg-rose-500 text-white'}`}>
                    {badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
        <div className="border-t border-slate-700/60 px-5 py-4 text-xs text-slate-400">
          <p>{now.toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })}</p>
          <p className="mt-0.5 font-mono text-slate-300">{now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</p>
        </div>
      </aside>

      {/* ---------------- Main ---------------- */}
      <div className="flex flex-1 flex-col overflow-hidden">

        {/* Top bar */}
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">{TABS.find((t) => t.key === activeTab)?.label}</h2>
            <p className="text-xs text-slate-500">No transaction, SIP, redemption or service request falls through the cracks.</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setActiveTab('notifications')}
              className="relative flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
            >
              <Bell size={16} />
              Alerts
              {totalAlerts > 0 && (
                <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-500 px-1 text-xs font-bold text-white">
                  {totalAlerts}
                </span>
              )}
            </button>
            <button
              onClick={() => setShowTxnModal(true)}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              <Plus size={16} /> Add Transaction
            </button>
          </div>
        </header>

        {/* Urgent banner */}
        {redCount > 0 && !bannerDismissed && (
          <div className="flex items-center justify-between gap-3 border-b border-rose-200 bg-rose-50 px-6 py-2 text-sm text-rose-700">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-rose-500" />
              </span>
              <span className="font-medium">{redCount} item(s) need urgent attention — pending reinvestments, overdue SIPs, SLA breaches or rejections.</span>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={() => setActiveTab('notifications')} className="font-semibold underline">View all</button>
              <button onClick={() => setBannerDismissed(true)} className="text-rose-400 hover:text-rose-600"><X size={14} /></button>
            </div>
          </div>
        )}

        {/* Content */}
        <main className="flex-1 overflow-y-auto px-6 py-5">
          {activeTab === 'overview' && (
            <OverviewTab
              kpis={kpis}
              amcBusiness={amcBusiness}
              employeeProductivity={employeeProductivity}
              dailyTrend={dailyTrend}
              statusDistribution={statusDistribution}
            />
          )}

          {activeTab === 'transactions' && (
            <TransactionsTab
              filters={filters}
              setFilters={setFilters}
              clearFilters={clearFilters}
              filteredTransactions={filteredTransactions}
              updateTransaction={updateTransaction}
            />
          )}

          {activeTab === 'redemptions' && (
            <RedemptionTab
              pendingReinvestments={pendingReinvestments}
              resolvedReinvestments={resolvedReinvestments}
              showCompleted={showCompletedReinvest}
              setShowCompleted={setShowCompletedReinvest}
              updateTransaction={updateTransaction}
              today={today}
            />
          )}

          {activeTab === 'sip' && (
            <SIPTab
              sipRegistrations={sipRegistrations}
              overdueSIPs={overdueSIPs}
              updateTransaction={updateTransaction}
              today={today}
            />
          )}

          {activeTab === 'service' && (
            <ServiceRequestsTab
              serviceRequests={serviceRequests}
              updateServiceRequest={updateServiceRequest}
              setShowSRModal={setShowSRModal}
              today={today}
            />
          )}

          {activeTab === 'notifications' && (
            <NotificationsTab notifications={notifications} />
          )}
        </main>
      </div>

      {/* ---------------- Modals ---------------- */}
      {showTxnModal && (
        <TransactionModal
          onClose={() => setShowTxnModal(false)}
          onSubmit={addTransaction}
          pendingReinvestments={pendingReinvestments}
          existingClients={existingClients}
        />
      )}

      {showSRModal && (
        <ServiceRequestModal
          onClose={() => setShowSRModal(false)}
          onSubmit={addServiceRequest}
          existingClients={existingClients}
        />
      )}
    </div>
  );
}

/* ============================== OVERVIEW TAB ============================== */

function OverviewTab({ kpis, amcBusiness, employeeProductivity, dailyTrend, statusDistribution }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {kpis.map((k) => {
          const Icon = k.icon;
          return (
            <div key={k.label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className={`mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg ${ACCENT_STYLES[k.accent]}`}>
                <Icon size={18} />
              </div>
              <p className="text-2xl font-bold tabular-nums text-slate-900">{k.value}</p>
              <p className="mt-0.5 text-xs font-medium text-slate-500">{k.label}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-1 text-sm font-semibold text-slate-900">AMC-wise Business (Cumulative Value)</h3>
          <p className="mb-3 text-xs text-slate-500">Sum of transaction amounts logged per AMC</p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={amcBusiness} margin={{ left: 0, right: 10, top: 5, bottom: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="amc" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${(v / 100000).toFixed(0)}L`} />
              <Tooltip formatter={(v) => fmtINR(v)} />
              <Bar dataKey="total" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-1 text-sm font-semibold text-slate-900">Employee-wise Productivity</h3>
          <p className="mb-3 text-xs text-slate-500">Total transactions logged per employee</p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={employeeProductivity} margin={{ left: 0, right: 10, top: 5, bottom: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="employee" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-1 text-sm font-semibold text-slate-900">Daily Transaction Trend (Last 7 Days)</h3>
          <p className="mb-3 text-xs text-slate-500">Number of transactions logged per day</p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={dailyTrend} margin={{ left: 0, right: 10, top: 5, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-1 text-sm font-semibold text-slate-900">Transaction Status Mix</h3>
          <p className="mb-3 text-xs text-slate-500">Distribution of all logged transactions by current status</p>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={statusDistribution} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={75} label={(e) => `${e.name} (${e.value})`}>
                {statusDistribution.map((entry, idx) => (
                  <Cell key={entry.name} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

/* ============================== TRANSACTIONS TAB ============================== */

function TransactionsTab({ filters, setFilters, clearFilters, filteredTransactions, updateTransaction }) {
  const setF = (key, value) => setFilters((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col">
          <label className="mb-1 text-xs font-medium text-slate-500">Client</label>
          <div className="relative">
            <Search size={14} className="absolute left-2 top-2.5 text-slate-400" />
            <input value={filters.client} onChange={(e) => setF('client', e.target.value)} placeholder="Search client..."
              className="w-40 rounded-lg border border-slate-300 py-1.5 pl-7 pr-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
        </div>
        <FilterSelect label="Employee" value={filters.employee} onChange={(v) => setF('employee', v)} options={EMPLOYEES} />
        <FilterSelect label="Transaction Type" value={filters.type} onChange={(v) => setF('type', v)} options={TRANSACTION_TYPES} width="w-48" />
        <FilterSelect label="AMC" value={filters.amc} onChange={(v) => setF('amc', v)} options={AMCS} width="w-44" />
        <FilterSelect label="Status" value={filters.status} onChange={(v) => setF('status', v)} options={STATUS_OPTIONS} />
        <div className="flex flex-col">
          <label className="mb-1 text-xs font-medium text-slate-500">From</label>
          <input type="date" value={filters.dateFrom} onChange={(e) => setF('dateFrom', e.target.value)}
            className="rounded-lg border border-slate-300 py-1.5 px-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
        </div>
        <div className="flex flex-col">
          <label className="mb-1 text-xs font-medium text-slate-500">To</label>
          <input type="date" value={filters.dateTo} onChange={(e) => setF('dateTo', e.target.value)}
            className="rounded-lg border border-slate-300 py-1.5 px-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
        </div>
        <button onClick={clearFilters} className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50">
          Clear filters
        </button>
        <span className="ml-auto text-xs text-slate-500">{filteredTransactions.length} of total transactions shown</span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[1300px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              {['Date', 'Client', 'Folio No.', 'AMC', 'Scheme', 'Type', 'Amount', 'Units', 'Status', 'Mode', 'Employee', 'Remarks'].map((h) => (
                <th key={h} className="whitespace-nowrap px-3 py-2 font-semibold">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredTransactions.map((t) => (
              <tr key={t.id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-3 py-2 text-slate-500">{fmtDate(t.transactionDate)}</td>
                <td className="whitespace-nowrap px-3 py-2 font-medium text-slate-900">{t.clientName}</td>
                <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-slate-500">{t.folioNumber}</td>
                <td className="whitespace-nowrap px-3 py-2">{t.amc}</td>
                <td className="whitespace-nowrap px-3 py-2">{t.schemeName}</td>
                <td className="whitespace-nowrap px-3 py-2">
                  <span className="inline-flex items-center gap-1">
                    {t.transactionType}
                    {t.isReinvestment && (
                      <span title="Linked to a reinvestment follow-up" className="text-indigo-500"><Link2 size={12} /></span>
                    )}
                  </span>
                </td>
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">{fmtINR(t.amount)}</td>
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">{fmtNum(t.units)}</td>
                <td className="whitespace-nowrap px-3 py-2">
                  <StatusSelect value={t.status} onChange={(v) => updateTransaction(t.id, { status: v })} options={STATUS_OPTIONS} />
                </td>
                <td className="whitespace-nowrap px-3 py-2">{t.mode}</td>
                <td className="whitespace-nowrap px-3 py-2">{t.employee}</td>
                <td className="max-w-[220px] px-3 py-2 text-slate-500">
                  <span className="line-clamp-2">{t.remarks || '—'}</span>
                  {t.awaitingDocuments && (
                    <span className="mt-1 inline-flex w-fit items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20">
                      <FileWarning size={10} /> Docs pending
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {filteredTransactions.length === 0 && (
              <tr><td colSpan={12} className="px-3 py-8 text-center text-sm text-slate-400">No transactions match the selected filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FilterSelect({ label, value, onChange, options, width = 'w-36' }) {
  return (
    <div className="flex flex-col">
      <label className="mb-1 text-xs font-medium text-slate-500">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className={`${width} rounded-lg border border-slate-300 py-1.5 px-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500`}>
        <option value="">All</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}

/* ============================== REDEMPTION TAB ============================== */

function RedemptionTab({ pendingReinvestments, resolvedReinvestments, showCompleted, setShowCompleted, updateTransaction, today }) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-900">Redemption Follow-up Tracker</h3>
        <p className="mt-1 text-xs text-slate-500">
          Every redemption marked &quot;for reinvestment&quot; appears here until the matching purchase is recorded (via
          &quot;Link to pending reinvestment&quot; on a new Purchase transaction) or the status is manually closed below.
        </p>
      </div>

      <div className="space-y-3">
        {pendingReinvestments.length === 0 && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
            All reinvestments are accounted for — nothing pending right now.
          </div>
        )}
        {pendingReinvestments.map((t) => {
          const days = daysBetween(t.actualCreditDate || t.expectedCreditDate || t.transactionDate, today);
          const severity = days > 7 ? 'red' : 'yellow';
          return (
            <div key={t.id} className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm border-l-4 ${SEVERITY_STYLES[severity].border}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{t.clientName} <span className="font-mono text-xs text-slate-400">· {t.folioNumber}</span></p>
                  <p className="text-xs text-slate-500">Redeemed {fmtINR(t.amount)} ({fmtNum(t.units)} units) from {t.schemeName} ({t.amc}) on {fmtDate(t.transactionDate)}</p>
                </div>
                <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${SEVERITY_STYLES[severity].chip}`}>
                  <Clock size={12} /> {days} day(s) pending
                </span>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-5">
                <FieldBlock label="Expected Credit Date">
                  <input type="date" value={t.expectedCreditDate || ''} onChange={(e) => updateTransaction(t.id, { expectedCreditDate: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                </FieldBlock>
                <FieldBlock label="Actual Credit Date">
                  <input type="date" value={t.actualCreditDate || ''} onChange={(e) => updateTransaction(t.id, { actualCreditDate: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                </FieldBlock>
                <FieldBlock label="Reinvestment Scheme" wide>
                  <input type="text" value={t.reinvestmentScheme || ''} placeholder="e.g. ABSL Corporate Bond Fund"
                    onChange={(e) => updateTransaction(t.id, { reinvestmentScheme: e.target.value })}
                    className="w-full rounded-lg border border-slate-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                </FieldBlock>
                <FieldBlock label="Reinvestment Status">
                  <StatusSelect value={t.reinvestmentStatus} onChange={(v) => updateTransaction(t.id, { reinvestmentStatus: v })} options={REINVEST_STATUS_OPTIONS} />
                </FieldBlock>
                <FieldBlock label="Owner">
                  <p className="pt-1 text-sm font-medium text-slate-700">{t.employee}</p>
                </FieldBlock>
              </div>
            </div>
          );
        })}
      </div>

      <div>
        <button onClick={() => setShowCompleted((v) => !v)} className="flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700">
          <ChevronRight size={14} className={`transition-transform ${showCompleted ? 'rotate-90' : ''}`} />
          {showCompleted ? 'Hide' : 'Show'} resolved reinvestments ({resolvedReinvestments.length})
        </button>
        {showCompleted && (
          <div className="mt-3 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  {['Client', 'Scheme Redeemed', 'Amount', 'Redemption Date', 'Reinvestment Scheme', 'Reinvestment Status', 'Owner'].map((h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-2 font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {resolvedReinvestments.map((t) => (
                  <tr key={t.id}>
                    <td className="whitespace-nowrap px-3 py-2 font-medium text-slate-900">{t.clientName}</td>
                    <td className="whitespace-nowrap px-3 py-2">{t.schemeName}</td>
                    <td className="whitespace-nowrap px-3 py-2 tabular-nums">{fmtINR(t.amount)}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-slate-500">{fmtDate(t.transactionDate)}</td>
                    <td className="whitespace-nowrap px-3 py-2">{t.reinvestmentScheme || '—'}</td>
                    <td className="whitespace-nowrap px-3 py-2"><StatusBadge status={t.reinvestmentStatus} /></td>
                    <td className="whitespace-nowrap px-3 py-2">{t.employee}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function FieldBlock({ label, children, wide }) {
  return (
    <div className={wide ? 'col-span-2' : ''}>
      <label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      {children}
    </div>
  );
}

/* ============================== SIP MONITORING TAB ============================== */

function SIPTab({ sipRegistrations, overdueSIPs, updateTransaction, today }) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 shadow-sm">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-rose-800">
          <AlertTriangle size={16} /> Pending SIP Verification ({overdueSIPs.length})
        </h3>
        <p className="mt-1 text-xs text-rose-600">
          These SIP registrations have been pending for more than 30 days without being marked &quot;Active&quot;. Follow up with the AMC / RTA until resolved.
        </p>
        {overdueSIPs.length === 0 ? (
          <p className="mt-2 text-sm text-rose-700">Nothing overdue — all SIPs are within the 30-day activation window.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {overdueSIPs.map((t) => {
              const days = daysBetween(t.submissionDate, today);
              return (
                <div key={t.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white px-3 py-2 text-sm shadow-sm">
                  <div>
                    <span className="font-semibold text-slate-900">{t.clientName}</span>
                    <span className="text-slate-500"> — {t.schemeName} ({t.amc}) · {fmtINR(t.amount)}/month</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">{days} days elapsed</span>
                    <StatusSelect value={t.sipStatus} onChange={(v) => updateTransaction(t.id, { sipStatus: v })} options={SIP_STATUS_OPTIONS} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[1100px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              {['Client', 'Folio No.', 'AMC', 'Scheme', 'SIP Amount', 'Submission Date', 'Expected Activation', 'Days Elapsed', 'SIP Status', 'Owner'].map((h) => (
                <th key={h} className="whitespace-nowrap px-3 py-2 font-semibold">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sipRegistrations.map((t) => {
              const days = daysBetween(t.submissionDate, today);
              const overdue = !['Active', 'Rejected'].includes(t.sipStatus) && days > 30;
              return (
                <tr key={t.id} className={overdue ? 'bg-rose-50/60' : 'hover:bg-slate-50'}>
                  <td className="whitespace-nowrap px-3 py-2 font-medium text-slate-900">{t.clientName}</td>
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-slate-500">{t.folioNumber}</td>
                  <td className="whitespace-nowrap px-3 py-2">{t.amc}</td>
                  <td className="whitespace-nowrap px-3 py-2">{t.schemeName}</td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{fmtINR(t.amount)}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-500">{fmtDate(t.submissionDate)}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-500">{fmtDate(t.expectedActivationDate)}</td>
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{days}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <StatusSelect value={t.sipStatus} onChange={(v) => updateTransaction(t.id, { sipStatus: v })} options={SIP_STATUS_OPTIONS} />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">{t.employee}</td>
                </tr>
              );
            })}
            {sipRegistrations.length === 0 && (
              <tr><td colSpan={10} className="px-3 py-8 text-center text-sm text-slate-400">No SIP registrations logged yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================== SERVICE REQUESTS TAB ============================== */

function ServiceRequestsTab({ serviceRequests, updateServiceRequest, setShowSRModal, today }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">Track every client service request from submission through resolution, with SLA monitoring.</p>
        <button onClick={() => setShowSRModal(true)} className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700">
          <Plus size={16} /> Add Service Request
        </button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[1300px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              {['Client', 'Request Type', 'Submitted', 'Owner', 'Status', 'Expected Completion', 'Actual Completion', 'Pending With', 'SLA', 'Follow-up Notes'].map((h) => (
                <th key={h} className="whitespace-nowrap px-3 py-2 font-semibold">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {serviceRequests.map((sr) => {
              const sla = SR_SLA[sr.requestType] || 7;
              const days = daysBetween(sr.dateSubmitted, today);
              const closed = ['Completed', 'Closed'].includes(sr.currentStatus);
              const overdue = !closed && days > sla;
              return (
                <tr key={sr.id} className={overdue ? 'bg-rose-50/60' : 'hover:bg-slate-50'}>
                  <td className="whitespace-nowrap px-3 py-2 font-medium text-slate-900">{sr.clientName}</td>
                  <td className="whitespace-nowrap px-3 py-2">{sr.requestType}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-500">{fmtDate(sr.dateSubmitted)}</td>
                  <td className="whitespace-nowrap px-3 py-2">{sr.employeeAssigned}</td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <StatusSelect value={sr.currentStatus} onChange={(v) => updateServiceRequest(sr.id, { currentStatus: v })} options={SR_STATUS_OPTIONS} />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <input type="date" value={sr.expectedCompletionDate || ''} onChange={(e) => updateServiceRequest(sr.id, { expectedCompletionDate: e.target.value })}
                      className="rounded-lg border border-slate-300 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <input type="date" value={sr.actualCompletionDate || ''} onChange={(e) => updateServiceRequest(sr.id, { actualCompletionDate: e.target.value })}
                      className="rounded-lg border border-slate-300 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <input type="text" value={sr.pendingWith || ''} placeholder="—" onChange={(e) => updateServiceRequest(sr.id, { pendingWith: e.target.value })}
                      className="w-32 rounded-lg border border-slate-300 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    {closed ? (
                      <StatusBadge status="Completed" />
                    ) : overdue ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700 ring-1 ring-inset ring-rose-600/20">
                        {days - sla}d over SLA
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                        On track ({sla - days}d left)
                      </span>
                    )}
                  </td>
                  <td className="min-w-[220px] px-3 py-2">
                    <textarea rows={2} value={sr.followUpNotes || ''} onChange={(e) => updateServiceRequest(sr.id, { followUpNotes: e.target.value })}
                      className="w-full resize-none rounded-lg border border-slate-300 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </td>
                </tr>
              );
            })}
            {serviceRequests.length === 0 && (
              <tr><td colSpan={10} className="px-3 py-8 text-center text-sm text-slate-400">No service requests logged yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================== NOTIFICATIONS TAB ============================== */

function NotificationsTab({ notifications }) {
  return (
    <div className="space-y-5">
      {notifications.map((group) => {
        const Icon = group.icon;
        return (
          <div key={group.key} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <Icon size={16} className="text-slate-400" />
              {group.title}
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">{group.items.length}</span>
            </h3>
            {group.items.length === 0 ? (
              <p className="mt-2 flex items-center gap-1.5 text-sm text-emerald-600"><CheckCircle2 size={14} /> All clear — nothing in this category.</p>
            ) : (
              <div className="mt-3 space-y-2">
                {group.items.map((item) => (
                  <div key={item.id} className={`flex items-start justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 border-l-4 ${SEVERITY_STYLES[item.severity].border}`}>
                    <div>
                      <p className="text-sm font-medium text-slate-900">{item.title}</p>
                      <p className="mt-0.5 text-xs text-slate-500">{item.subtitle}</p>
                    </div>
                    <span className={`mt-0.5 inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${SEVERITY_STYLES[item.severity].chip}`}>
                      {item.severity === 'red' ? 'Urgent' : 'Follow-up'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ============================== ADD TRANSACTION MODAL ============================== */

function TransactionModal({ onClose, onSubmit, pendingReinvestments, existingClients }) {
  const [form, setForm] = useState({
    clientName: '', folioNumber: '', amc: AMCS[0], schemeName: '',
    transactionType: 'Purchase', transactionDate: todayStr(),
    amount: '', units: '', status: 'Submitted', mode: MODES[0],
    employee: EMPLOYEES[0], remarks: '', awaitingDocuments: false,
    isReinvestment: false, expectedCreditDate: '', reinvestmentScheme: '',
    expectedActivationDate: daysFromNow(30), sipStatus: 'Submitted',
    linkedRedemptionId: '',
  });

  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.clientName || !form.folioNumber || !form.schemeName) return;
    onSubmit(form);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h3 className="text-base font-semibold text-slate-900">Log a New Transaction</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
          <div className="grid grid-cols-2 gap-3">
            <ModalField label="Client Name" required>
              <input list="client-names" value={form.clientName} onChange={(e) => set('clientName', e.target.value)} required
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <datalist id="client-names">{existingClients.map((c) => <option key={c} value={c} />)}</datalist>
            </ModalField>
            <ModalField label="Folio Number" required>
              <input value={form.folioNumber} onChange={(e) => set('folioNumber', e.target.value)} required
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </ModalField>
            <ModalField label="AMC">
              <select value={form.amc} onChange={(e) => set('amc', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {AMCS.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </ModalField>
            <ModalField label="Scheme Name" required>
              <input value={form.schemeName} onChange={(e) => set('schemeName', e.target.value)} required
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </ModalField>
            <ModalField label="Transaction Type">
              <select value={form.transactionType} onChange={(e) => set('transactionType', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {TRANSACTION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </ModalField>
            <ModalField label="Transaction Date">
              <input type="date" value={form.transactionDate} onChange={(e) => set('transactionDate', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </ModalField>
            <ModalField label="Amount (₹)">
              <input type="number" min="0" step="0.01" value={form.amount} onChange={(e) => set('amount', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </ModalField>
            <ModalField label="Units">
              <input type="number" min="0" step="0.001" value={form.units} onChange={(e) => set('units', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </ModalField>
            <ModalField label="Status">
              <select value={form.status} onChange={(e) => set('status', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </ModalField>
            <ModalField label="Mode of Transaction">
              <select value={form.mode} onChange={(e) => set('mode', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {MODES.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </ModalField>
            <ModalField label="Employee Responsible">
              <select value={form.employee} onChange={(e) => set('employee', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {EMPLOYEES.map((emp) => <option key={emp} value={emp}>{emp}</option>)}
              </select>
            </ModalField>
            <ModalField label=" ">
              <label className="mt-2 flex items-center gap-2 text-sm text-slate-600">
                <input type="checkbox" checked={form.awaitingDocuments} onChange={(e) => set('awaitingDocuments', e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                Awaiting client documents
              </label>
            </ModalField>
          </div>

          <ModalField label="Remarks">
            <textarea rows={2} value={form.remarks} onChange={(e) => set('remarks', e.target.value)}
              className="w-full resize-none rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </ModalField>

          {/* Redemption reinvestment block */}
          {form.transactionType === 'Redemption' && (
            <div className="rounded-lg border border-indigo-100 bg-indigo-50/50 p-3">
              <p className="mb-2 text-sm font-medium text-indigo-900">Redemption for Reinvestment?</p>
              <div className="flex gap-4">
                <label className="flex items-center gap-1.5 text-sm">
                  <input type="radio" name="reinvest" checked={form.isReinvestment === true} onChange={() => set('isReinvestment', true)} /> Yes
                </label>
                <label className="flex items-center gap-1.5 text-sm">
                  <input type="radio" name="reinvest" checked={form.isReinvestment === false} onChange={() => set('isReinvestment', false)} /> No
                </label>
              </div>
              {form.isReinvestment && (
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <ModalField label="Expected Credit Date">
                    <input type="date" value={form.expectedCreditDate} onChange={(e) => set('expectedCreditDate', e.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </ModalField>
                  <ModalField label="Reinvestment Scheme (if known)">
                    <input value={form.reinvestmentScheme} onChange={(e) => set('reinvestmentScheme', e.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                  </ModalField>
                </div>
              )}
              <p className="mt-2 text-xs text-indigo-600">
                A pending follow-up task will be created and reminders shown until the matching purchase is recorded.
              </p>
            </div>
          )}

          {/* Purchase linking block */}
          {form.transactionType === 'Purchase' && pendingReinvestments.length > 0 && (
            <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-3">
              <ModalField label="Link to a pending reinvestment redemption (optional)">
                <select value={form.linkedRedemptionId} onChange={(e) => set('linkedRedemptionId', e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option value="">None</option>
                  {pendingReinvestments.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.clientName} — {fmtINR(t.amount)} redeemed from {t.schemeName} on {fmtDate(t.transactionDate)}
                    </option>
                  ))}
                </select>
              </ModalField>
              <p className="mt-2 text-xs text-emerald-700">
                Linking will mark that redemption&apos;s reinvestment as completed and close its follow-up task.
              </p>
            </div>
          )}

          {/* SIP registration block */}
          {form.transactionType === 'SIP Registration' && (
            <div className="rounded-lg border border-sky-100 bg-sky-50/50 p-3">
              <div className="grid grid-cols-2 gap-3">
                <ModalField label="Expected Activation Date">
                  <input type="date" value={form.expectedActivationDate} onChange={(e) => set('expectedActivationDate', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                </ModalField>
                <ModalField label="Initial SIP Status">
                  <select value={form.sipStatus} onChange={(e) => set('sipStatus', e.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    {SIP_STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </ModalField>
              </div>
              <p className="mt-2 text-xs text-sky-700">
                This SIP will appear on the SIP Monitoring Dashboard. If it&apos;s still not marked &quot;Active&quot; 30 days after
                the transaction date, it will surface as a Pending SIP Verification alert.
              </p>
            </div>
          )}

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-300 px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50">
              Cancel
            </button>
            <button type="submit" className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700">
              Save Transaction
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ============================== ADD SERVICE REQUEST MODAL ============================== */

function ServiceRequestModal({ onClose, onSubmit, existingClients }) {
  const [form, setForm] = useState({
    clientName: '', requestType: SR_TYPES[0], dateSubmitted: todayStr(),
    employeeAssigned: EMPLOYEES[0], currentStatus: 'Open',
    expectedCompletionDate: daysFromNow(SR_SLA[SR_TYPES[0]]),
    actualCompletionDate: '', pendingWith: '', followUpNotes: '',
  });

  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const handleTypeChange = (type) => {
    setForm((prev) => ({ ...prev, requestType: type, expectedCompletionDate: daysFromNow(SR_SLA[type] || 7) }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.clientName) return;
    onSubmit(form);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h3 className="text-base font-semibold text-slate-900">New Service Request</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-4">
          <div className="grid grid-cols-2 gap-3">
            <ModalField label="Client Name" required>
              <input list="sr-client-names" value={form.clientName} onChange={(e) => set('clientName', e.target.value)} required
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <datalist id="sr-client-names">{existingClients.map((c) => <option key={c} value={c} />)}</datalist>
            </ModalField>
            <ModalField label="Request Type">
              <select value={form.requestType} onChange={(e) => handleTypeChange(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {SR_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </ModalField>
            <ModalField label="Date Submitted">
              <input type="date" value={form.dateSubmitted} onChange={(e) => set('dateSubmitted', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </ModalField>
            <ModalField label="Employee Assigned">
              <select value={form.employeeAssigned} onChange={(e) => set('employeeAssigned', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {EMPLOYEES.map((emp) => <option key={emp} value={emp}>{emp}</option>)}
              </select>
            </ModalField>
            <ModalField label="Current Status">
              <select value={form.currentStatus} onChange={(e) => set('currentStatus', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {SR_STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </ModalField>
            <ModalField label="Expected Completion Date">
              <input type="date" value={form.expectedCompletionDate} onChange={(e) => set('expectedCompletionDate', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </ModalField>
            <ModalField label="Actual Completion Date">
              <input type="date" value={form.actualCompletionDate} onChange={(e) => set('actualCompletionDate', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </ModalField>
            <ModalField label="Pending With">
              <input value={form.pendingWith} placeholder="e.g. AMC - HDFC, Client, Internal" onChange={(e) => set('pendingWith', e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </ModalField>
          </div>
          <ModalField label="Follow-up Notes">
            <textarea rows={3} value={form.followUpNotes} onChange={(e) => set('followUpNotes', e.target.value)}
              className="w-full resize-none rounded-lg border border-slate-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </ModalField>
          <p className="text-xs text-slate-500">
            SLA for &quot;{form.requestType}&quot; is {SR_SLA[form.requestType] || 7} days. If not Completed/Closed within that window, this request will surface under &quot;Service Requests Pending Beyond SLA&quot;.
          </p>
          <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-300 px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50">
              Cancel
            </button>
            <button type="submit" className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700">
              Save Request
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ModalField({ label, children, required }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-500">
        {label}{required && <span className="text-rose-500"> *</span>}
      </label>
      {children}
    </div>
  );
}
