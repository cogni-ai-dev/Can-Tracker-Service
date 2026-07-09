import { useEffect, useState } from 'react';
import { Download, Eye } from 'lucide-react';

import { Card, EmptyState, PageHeader } from '../../components/ui';
import { complianceApi } from '../../lib/api';
import type { ReportExportFormat, ReportPreview, ReportType } from '../../types';

const reportDefinitions: Array<{ type: ReportType; name: string; description: string }> = [
  {
    type: 'kyc_pending',
    name: 'KYC Pending Report',
    description: 'Clients with Not Started or Re-KYC pending status.',
  },
  {
    type: 'payeezz_pending',
    name: 'PayEezz Pending Report',
    description: 'Clients without accepted PayEezz mandates.',
  },
  {
    type: 'contact_pending',
    name: 'Contact Pending Report',
    description: 'Mobile, email, and nominee verification gaps.',
  },
  {
    type: 'family_compliance',
    name: 'Family Compliance Report',
    description: 'Family-level completion across CAN compliance checks.',
  },
  {
    type: 'rm_tasks',
    name: 'RM-wise Pending Tasks Report',
    description: 'Pending tasks grouped by relationship manager.',
  },
  {
    type: 'full',
    name: 'Full CAN Database Export',
    description: 'Complete export of all client records and compliance statuses.',
  },
];

export function ReportsModule() {
  const [selected, setSelected] = useState<ReportType>('kyc_pending');
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    void loadPreview(selected);
  }, [selected]);

  async function loadPreview(type: ReportType) {
    setLoading(true);
    setMessage('');
    try {
      setPreview(await complianceApi.reportPreview(type, { limit: 10, offset: 0 }));
    } catch (error) {
      setPreview(null);
      setMessage(friendlyError(error));
    } finally {
      setLoading(false);
    }
  }

  async function exportReport(type: ReportType, format: ReportExportFormat) {
    setMessage('');
    try {
      await complianceApi.exportReport(type, format);
      setMessage(`${format.toUpperCase()} export started.`);
    } catch (error) {
      setMessage(friendlyError(error));
    }
  }

  return (
    <div>
      <PageHeader title="Reports" subtitle="Generate and download existing CAN compliance reports." />
      {message && <div className="mb-4 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">{message}</div>}
      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.4fr]">
        <div className="space-y-3">
          {reportDefinitions.map((report) => (
            <Card key={report.type} className={selected === report.type ? 'ring-2 ring-blue-500' : ''}>
              <div className="flex items-start justify-between gap-3">
                <button type="button" onClick={() => setSelected(report.type)} className="text-left">
                  <div className="font-semibold text-slate-900">{report.name}</div>
                  <p className="mt-1 text-sm text-slate-500">{report.description}</p>
                </button>
                <button type="button" onClick={() => setSelected(report.type)} className="rounded-md border border-slate-300 p-2 text-slate-600 hover:bg-slate-50" aria-label={`Preview ${report.name}`}>
                  <Eye size={16} />
                </button>
              </div>
              <div className="mt-3 flex gap-2">
                <button type="button" onClick={() => exportReport(report.type, 'csv')} className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">
                  <Download size={14} /> CSV
                </button>
                <button type="button" onClick={() => exportReport(report.type, 'xlsx')} className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700">
                  <Download size={14} /> Excel
                </button>
              </div>
            </Card>
          ))}
        </div>
        <Card>
          <div className="mb-3 flex items-center justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-slate-900">{preview?.title || 'Report Preview'}</div>
              {preview && <div className="mt-1 text-sm text-slate-500">Showing {preview.items.length} of {preview.total} rows</div>}
            </div>
            <button type="button" onClick={() => loadPreview(selected)} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
              Refresh Preview
            </button>
          </div>
          {loading && <div className="rounded-md bg-slate-50 p-8 text-center text-sm text-slate-500">Loading preview...</div>}
          {!loading && !preview && <EmptyState title="Preview unavailable" detail={message || 'Select a report to load its preview.'} />}
          {!loading && preview && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    {preview.columns.map((column) => <th key={column.key} className="px-3 py-2">{column.label}</th>)}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {preview.items.map((item, index) => (
                    <tr key={index}>
                      {preview.columns.map((column) => (
                        <td key={column.key} className="px-3 py-3">{formatCell(item[column.key])}</td>
                      ))}
                    </tr>
                  ))}
                  {!preview.items.length && (
                    <tr><td className="px-3 py-8 text-center text-slate-500" colSpan={preview.columns.length}>No rows in this preview.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function formatCell(value: unknown) {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'number') return value.toLocaleString('en-IN');
  return String(value);
}

function friendlyError(error: unknown) {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}
