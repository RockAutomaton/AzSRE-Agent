'use client';

import Link from 'next/link';
import { MessageSquare, AlertTriangle, History, Clock, Server, Database, Activity, Shield } from 'lucide-react';
import useSWR from 'swr';
import { API_URL } from './lib/config';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

interface AlertEntity {
  RowKey: string;
  PartitionKey: string;
  RuleName: string;
  Severity: string;
  ReportSummary: string;
  CreatedAt: string;
}

function getIconForType(type: string) {
  switch (type) {
    case 'INFRA': return <Server className="w-4 h-4 text-orange-500 dark:text-orange-400" />;
    case 'DATABASE': return <Database className="w-4 h-4 text-blue-500 dark:text-blue-400" />;
    case 'APP': return <Activity className="w-4 h-4 text-purple-500 dark:text-purple-400" />;
    default: return <Shield className="w-4 h-4 text-slate-400 dark:text-slate-500" />;
  }
}

export default function Home() {
  const { data: alerts } = useSWR<AlertEntity[]>(`${API_URL}/api/history`, fetcher);
  const recentAlerts = alerts?.slice(0, 5) || [];

  return (
    <main className="min-h-screen p-8 bg-slate-50 dark:bg-slate-900 flex items-start justify-center pt-20">
      <div className="max-w-7xl mx-auto w-full">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4 text-slate-800 dark:text-slate-100">Azure SRE Agent Dashboard</h1>
          <p className="text-lg text-gray-600 dark:text-slate-400">
            Intelligent incident response and alert management for Azure Monitor.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-12">
          <Link 
            href="/history"
            className="p-6 bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow text-center"
          >
            <div className="flex justify-center mb-3">
              <AlertTriangle className="h-8 w-8 text-orange-600 dark:text-orange-400" />
            </div>
            <h2 className="text-xl font-semibold mb-2 text-slate-800 dark:text-slate-100">Alert History</h2>
            <p className="text-gray-600 dark:text-slate-400 text-sm">
              View and analyze past incidents and investigations.
            </p>
          </Link>
          
          <Link 
            href="/analytics"
            className="p-6 bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow text-center"
          >
            <div className="flex justify-center mb-3">
              <History className="h-8 w-8 text-green-600 dark:text-green-400" />
            </div>
            <h2 className="text-xl font-semibold mb-2 text-slate-800 dark:text-slate-100">Analytics</h2>
            <p className="text-gray-600 dark:text-slate-400 text-sm">
              Insights and trends from your alert data.
            </p>
          </Link>
          
          <Link 
            href="/chat"
            className="p-6 bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow text-center"
          >
            <div className="flex justify-center mb-3">
              <MessageSquare className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            </div>
            <h2 className="text-xl font-semibold mb-2 text-slate-800 dark:text-slate-100">Investigator Chat</h2>
            <p className="text-gray-600 dark:text-slate-400 text-sm">
              Ask questions about alerts, KQL syntax, or Azure troubleshooting.
            </p>
          </Link>
        </div>

        {/* Recent Alerts Section */}
        <div className="max-w-5xl mx-auto">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-200 dark:border-slate-700">
              <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-100">Recent Alerts</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Latest 5 incidents</p>
            </div>
            
            {recentAlerts.length === 0 ? (
              <div className="p-8 text-center text-slate-400 dark:text-slate-500">
                <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No alerts found. Alerts will appear here once they are processed.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-700">
                {recentAlerts.map((alert) => (
                  <Link
                    key={alert.RowKey}
                    href={`/incidents/${alert.RowKey}`}
                    className="block p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        <div className="flex items-center gap-2 shrink-0">
                          {getIconForType(alert.PartitionKey)}
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            ['Sev0', 'Sev1'].includes(alert.Severity) 
                              ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' 
                              : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                          }`}>
                            {alert.Severity}
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-slate-900 dark:text-slate-100 truncate">
                            {alert.RuleName}
                          </h3>
                          <p className="text-sm text-slate-600 dark:text-slate-400 truncate mt-1">
                            {alert.ReportSummary}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 shrink-0 ml-4">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(alert.CreatedAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
            
            {recentAlerts.length > 0 && (
              <div className="p-4 border-t border-slate-200 dark:border-slate-700 text-center">
                <Link 
                  href="/history"
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                >
                  View all alerts →
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  )
}
