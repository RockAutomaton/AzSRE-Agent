'use client';

import { use } from 'react';
import useSWR from 'swr';
import { ArrowLeft, CheckCircle, AlertTriangle, Terminal, Shield, Activity } from 'lucide-react';
import Link from 'next/link';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: alert, error } = useSWR(`http://localhost:8000/api/alerts/${id}`, fetcher);

  if (error) return <div className="p-8 text-red-500 dark:text-red-400">Error loading incident.</div>;
  if (!alert) return <div className="p-8 text-slate-500 dark:text-slate-400">Loading details...</div>;

  // Parse the ReportJson if it's a string
  let report: any = {};
  try {
    report = typeof alert.ReportJson === 'string' ? JSON.parse(alert.ReportJson) : alert.ReportJson;
  } catch (e) {
    report = { summary: alert.ReportSummary };
  }

  return (
    <div className="min-h-screen p-8 bg-slate-50 dark:bg-slate-900">
      <div className="max-w-5xl mx-auto space-y-6 pb-20">
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors mb-4">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Dashboard
        </Link>

      {/* Header Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{alert.RuleName}</h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-slate-500 dark:text-slate-400">
              <span className="font-mono bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded text-slate-900 dark:text-slate-100">{alert.RowKey}</span>
              <span>•</span>
              <span>{new Date(alert.FiredTime).toLocaleString()}</span>
            </div>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-bold ${
            alert.Severity === 'Sev0' || alert.Severity === 'Sev1' 
              ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' 
              : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
          }`}>
            {alert.Severity}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Main Analysis Column */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Executive Summary */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-slate-800 dark:text-slate-100">
              <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" /> Executive Summary
            </h2>
            <div className="prose text-slate-700 dark:text-slate-300 prose-invert">
              <p>{report.summary || alert.ReportSummary}</p>
            </div>
            
            {report.root_cause && (
              <div className="mt-4 p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-100 dark:border-orange-900/50 rounded-lg">
                <span className="font-bold text-orange-800 dark:text-orange-300">Root Cause:</span>
                <span className="ml-2 text-orange-900 dark:text-orange-200">{report.root_cause}</span>
              </div>
            )}
          </div>

          {/* Evidence Checklist */}
          {report.evidence && report.evidence.length > 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-slate-800 dark:text-slate-100">
                <Activity className="w-5 h-5 text-purple-600 dark:text-purple-400" /> Technical Evidence
              </h2>
              <ul className="space-y-3">
                {report.evidence.map((item: any, idx: number) => (
                  <li key={idx} className="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-700 rounded-lg border border-slate-100 dark:border-slate-600">
                    <CheckCircle className="w-5 h-5 text-green-500 dark:text-green-400 mt-0.5 shrink-0" />
                    <div>
                      <div className="font-medium text-slate-900 dark:text-slate-100">{item.source}</div>
                      <div className="text-sm text-slate-600 dark:text-slate-400">{item.finding}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {report.recommendations && report.recommendations.length > 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-4 text-slate-800 dark:text-slate-100">Recommendations</h2>
              <div className="space-y-2">
                {report.recommendations.map((rec: string, idx: number) => (
                  <div key={idx} className="flex gap-3">
                    <div className="w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center text-xs font-bold shrink-0">
                      {idx + 1}
                    </div>
                    <p className="text-slate-700 dark:text-slate-300">{rec}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar Metadata */}
        <div className="space-y-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-4">Metadata</h3>
            <div className="space-y-3 text-sm">
              <div>
                <span className="block text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider">Classification</span>
                <span className="font-medium text-slate-900 dark:text-slate-100">{alert.PartitionKey}</span>
              </div>
              <div>
                <span className="block text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider">Target Resource</span>
                {/* Try to parse resource name from AlertId or raw data if available */}
                <span className="font-medium truncate block text-slate-900 dark:text-slate-100">{alert.AlertId.split('/components/')[1] || 'Unknown'}</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 dark:bg-slate-950 rounded-xl border border-slate-800 dark:border-slate-700 p-4 shadow-sm overflow-hidden">
            <h3 className="font-semibold text-slate-300 dark:text-slate-400 mb-2 flex items-center gap-2">
              <Terminal className="w-4 h-4" /> Raw JSON
            </h3>
            <pre className="text-xs text-slate-400 dark:text-slate-500 overflow-x-auto p-2">
              {JSON.stringify(report, null, 2)}
            </pre>
          </div>
        </div>

      </div>
    </div>
    </div>
  );
}

