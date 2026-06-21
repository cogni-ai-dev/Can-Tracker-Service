import { FormEvent, useEffect, useState } from 'react';
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  ClipboardList,
  Eye,
  EyeOff,
  FileText,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Settings,
  ShieldCheck,
  Users2,
} from 'lucide-react';

import { Badge } from './components/ui';
import { authApi } from './lib/api';
import { canAccessModule, canManageUsers } from './lib/access';
import { AdminModule } from './modules/admin/AdminModule';
import { ComplianceModule } from './modules/compliance/ComplianceModule';
import { ClientCrmModule } from './modules/crm/ClientCrmModule';
import { ReportsModule } from './modules/reports/ReportsModule';
import type { CurrentUser } from './types';

type AuthState = {
  user: CurrentUser | null;
  loading: boolean;
  error: string;
};

const complianceLinks = [
  ['Dashboard', '/compliance/dashboard', LayoutDashboard],
  ['Families', '/compliance/families', Users2],
  ['KYC', '/compliance/kyc', ShieldCheck],
  ['PayEezz', '/compliance/payeezz', ClipboardList],
  ['Contact Verification', '/compliance/contact', ClipboardList],
  ['Pending Tasks', '/compliance/tasks', ClipboardList],
] as const;

const crmLinks = [
  ['Control Centre', '/crm/control-centre', BarChart3],
  ['Transactions', '/crm/transactions', ClipboardList],
  ['Redemption Follow-ups', '/crm/redemptions', ClipboardList],
  ['SIP Monitoring', '/crm/sip', ClipboardList],
  ['Service Requests', '/crm/service-requests', ClipboardList],
  ['Alerts', '/crm/alerts', ClipboardList],
  ['Leads', '/crm/leads', Users2],
  ['Prospects', '/crm/prospects', Users2],
  ['Pipeline', '/crm/pipeline', BarChart3],
  ['Meetings', '/crm/meetings', ClipboardList],
  ['Relationship Notes', '/crm/notes', ClipboardList],
] as const;

export function App() {
  const [auth, setAuth] = useState<AuthState>({ user: null, loading: true, error: '' });

  useEffect(() => {
    let cancelled = false;
    authApi.me()
      .then((user) => {
        if (!cancelled) setAuth({ user, loading: false, error: '' });
      })
      .catch(() => {
        if (!cancelled) setAuth({ user: null, loading: false, error: '' });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (auth.loading) {
    return <div className="grid h-full place-items-center text-sm text-slate-500">Loading MFU Operations Portal...</div>;
  }

  if (!auth.user) {
    return <LoginScreen onLogin={(user) => setAuth({ user, loading: false, error: '' })} />;
  }

  return <Shell user={auth.user} onLogout={() => setAuth({ user: null, loading: false, error: '' })} />;
}

function LoginScreen({ onLogin }: { onLogin: (user: CurrentUser) => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await authApi.login(email, password);
      onLogin(result.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-full place-items-center bg-slate-100 px-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="text-xs font-semibold uppercase tracking-widest text-blue-600">MFU Platform</div>
        <h1 className="mt-1 text-xl font-bold text-slate-950">MFU Operations Portal</h1>
        <p className="mt-1 text-sm text-slate-500">Sign in with your internal operations account.</p>
        {error && <div className="mt-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
        <label className="mt-5 block text-sm font-medium text-slate-700">
          Email
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            type="email"
            autoComplete="email"
            required
          />
        </label>
        <label className="mt-4 block text-sm font-medium text-slate-700">
          Password
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        <button
          disabled={busy}
          className="mt-5 w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
    </div>
  );
}

function Shell({ user, onLogout }: { user: CurrentUser; onLogout: () => void }) {
  const location = useLocation();
  const [passwordOpen, setPasswordOpen] = useState(false);

  async function logout() {
    await authApi.logout().catch(() => undefined);
    onLogout();
  }

  const defaultRoute = canAccessModule(user, 'can_compliance')
    ? '/compliance/dashboard'
    : canAccessModule(user, 'client_crm')
      ? '/crm/control-centre'
      : '/reports';

  return (
    <div className="flex h-full min-h-screen bg-slate-100">
      <aside className="flex w-72 shrink-0 flex-col bg-slate-950 text-slate-200">
        <div className="border-b border-slate-800 px-5 py-5">
          <div className="text-xs font-semibold uppercase tracking-widest text-blue-400">MFU Platform</div>
          <div className="mt-1 text-lg font-bold text-white">MFU Operations Portal</div>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {canAccessModule(user, 'can_compliance') && (
            <NavSection title="Compliance" links={complianceLinks} currentPath={location.pathname} />
          )}
          {canAccessModule(user, 'client_crm') && (
            <NavSection title="Client CRM" links={crmLinks} currentPath={location.pathname} />
          )}
          <NavSection
            title="Reports"
            links={[['Reports', '/reports', FileText]]}
            currentPath={location.pathname}
          />
          {canManageUsers(user) && (
            <NavSection
              title="Admin"
              links={[['Users & Access', '/admin/users', Settings]]}
              currentPath={location.pathname}
            />
          )}
        </nav>
        <div className="border-t border-slate-800 p-4">
          <div className="mb-3">
            <div className="text-sm font-semibold text-white">{user.name}</div>
            <div className="mt-1 text-xs text-slate-400">{user.email}</div>
            <div className="mt-2 flex flex-wrap gap-1">
              {user.memberships.map((membership) => (
                <Badge key={`${membership.module_code}-${membership.role}`} tone="blue">{membership.role}</Badge>
              ))}
            </div>
          </div>
          <button onClick={logout} className="flex w-full items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800">
            <LogOut size={16} /> Sign out
          </button>
          <button onClick={() => setPasswordOpen(true)} className="mt-2 flex w-full items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800">
            <KeyRound size={16} /> Change password
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto px-6 py-5">
        <Routes>
          <Route path="/" element={<Navigate to={defaultRoute} replace />} />
          <Route
            path="/compliance/families/:familyId"
            element={canAccessModule(user, 'can_compliance') ? <ComplianceModule user={user} /> : <Navigate to={defaultRoute} replace />}
          />
          <Route
            path="/compliance/:page"
            element={canAccessModule(user, 'can_compliance') ? <ComplianceModule user={user} /> : <Navigate to={defaultRoute} replace />}
          />
          <Route
            path="/crm/:page"
            element={canAccessModule(user, 'client_crm') ? <ClientCrmModule /> : <Navigate to={defaultRoute} replace />}
          />
          <Route path="/reports" element={<ReportsModule />} />
          <Route
            path="/admin/:page"
            element={canManageUsers(user) ? <AdminModule user={user} /> : <Navigate to={defaultRoute} replace />}
          />
          <Route path="*" element={<Navigate to={defaultRoute} replace />} />
        </Routes>
      </main>
      {passwordOpen && <PasswordModal onClose={() => setPasswordOpen(false)} />}
    </div>
  );
}

function NavSection({
  title,
  links,
  currentPath,
}: {
  title: string;
  links: ReadonlyArray<readonly [string, string, LucideIcon]>;
  currentPath: string;
}) {
  return (
    <div className="mb-5">
      <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{title}</div>
      <div className="space-y-1">
        {links.map(([label, href, Icon]) => {
          const active = currentPath === href;
          return (
            <Link
              key={href}
              to={href}
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium ${active ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-900 hover:text-white'}`}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function PasswordModal({ onClose }: { onClose: () => void }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError('Please fill in all password fields.');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }
    setBusy(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Password change failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-950 px-5 py-4 text-white">
          <div className="font-semibold">Change Password</div>
          <button type="button" onClick={onClose} className="rounded-md px-2 py-1 text-sm text-slate-300 hover:bg-white/10 hover:text-white">Close</button>
        </div>
        <div className="space-y-4 p-5">
          {error && <div className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
          <label className="block text-sm font-medium text-slate-700">
            Current password
            <RevealPasswordInput
              value={currentPassword}
              onChange={setCurrentPassword}
              autoComplete="current-password"
              revealLabel="current password"
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            New password
            <RevealPasswordInput
              value={newPassword}
              onChange={setNewPassword}
              autoComplete="new-password"
              revealLabel="new password"
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Confirm new password
            <RevealPasswordInput
              value={confirmPassword}
              onChange={setConfirmPassword}
              autoComplete="new-password"
              revealLabel="confirm new password"
            />
          </label>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Cancel</button>
            <button disabled={busy} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">{busy ? 'Saving...' : 'Save Password'}</button>
          </div>
        </div>
      </form>
    </div>
  );
}

function RevealPasswordInput({
  value,
  onChange,
  autoComplete,
  revealLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  revealLabel: string;
}) {
  const [visible, setVisible] = useState(false);
  const label = `${visible ? 'Hide' : 'Show'} ${revealLabel}`;
  const Icon = visible ? EyeOff : Eye;

  return (
    <div className="relative mt-1">
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        type={visible ? 'text' : 'password'}
        autoComplete={autoComplete}
        className="w-full rounded-md border border-slate-300 px-3 py-2 pr-10 text-sm outline-none focus:ring-2 focus:ring-blue-500"
      />
      <button
        type="button"
        aria-label={label}
        title={label}
        onClick={() => setVisible((current) => !current)}
        className="absolute right-2 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <Icon size={16} />
      </button>
    </div>
  );
}
