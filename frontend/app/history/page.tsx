'use client';

import { useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import { 
  AlertCircle, 
  Search, 
  Activity, 
  Clock, 
  Server, 
  Database, 
  Shield,
  ArrowLeft
} from 'lucide-react';

// Fetcher function for SWR
const fetcher = (url: string) => fetch(url).then((res) => res.json());

interface AlertEntity {
  RowKey: string;
  PartitionKey: string; // Classification
  RuleName: string;
  Severity: string;
  ReportSummary: string;
  CreatedAt: string;
}

export default function HistoryPage() {
  const [searchTerm, setSearchTerm] = useState('');
  
  // Poll API every 5 seconds for real-time feel
  const { data: alerts, error, isLoading } = useSWR<AlertEntity[]>(
    'http://localhost:8000/api/history', 
    fetcher, 
    { refreshInterval: 5000 }
  );

  // Filter logic
  const filteredAlerts = alerts?.filter(alert => 
    alert.RuleName.toLowerCase().includes(searchTerm.toLowerCase()) ||
    alert.ReportSummary.toLowerCase().includes(searchTerm.toLowerCase()) ||
    alert.PartitionKey.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  // Metrics
  const totalAlerts = alerts?.length || 0;
  const criticalCount = alerts?.filter(a => a.Severity === 'Sev0' || a.Severity === 'Sev1').length || 0;
  const infraCount = alerts?.filter(a => a.PartitionKey === 'INFRA').length || 0;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] text-red-500">
        <AlertCircle className="w-12 h-12 mb-2 opacity-50" />
        <p className="font-semibold">Failed to connect to Agent API.</p>
        <p className="text-sm opacity-75">Is the backend running on port 8000?</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8 bg-slate-50 dark:bg-slate-900">
      <div className="max-w-6xl mx-auto space-y-8">
      
      {/* Back Button */}
      <Link href="/" className="inline-flex items-center text-sm text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors mb-4">
        <ArrowLeft className="w-4 h-4 mr-1" /> Back to Dashboard
      </Link>
      
      {/* Header & Metrics */}
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 dark:text-slate-100">Alert History</h1>
          <p className="text-slate-500 dark:text-slate-400">Real-time feed of automated investigations.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard 
            label="Total Incidents" 
            value={totalAlerts} 
            icon={<Activity className="text-blue-600" />} 
          />
          <MetricCard 
            label="Critical (Sev0/1)" 
            value={criticalCount} 
            icon={<AlertCircle className="text-red-600" />} 
            color="red"
          />
          <MetricCard 
            label="Infra Issues" 
            value={infraCount} 
            icon={<Server className="text-orange-600" />} 
            color="orange"
          />
        </div>
      </div>

      {/* Main Table Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        
        {/* Toolbar */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 flex justify-between items-center">
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
            <input 
              type="text" 
              placeholder="Search alerts..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-400"
            />
          </div>
          <div className="text-xs text-slate-400 dark:text-slate-500 font-mono">
            {isLoading ? 'Syncing...' : `Updated ${new Date().toLocaleTimeString()}`}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
              <tr>
                <th className="px-6 py-4 font-semibold w-[100px]">Severity</th>
                <th className="px-6 py-4 font-semibold w-[120px]">Type</th>
                <th className="px-6 py-4 font-semibold">Rule Name</th>
                <th className="px-6 py-4 font-semibold">Investigation Summary</th>
                <th className="px-6 py-4 font-semibold text-right">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
              {filteredAlerts.length === 0 && !isLoading && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400 dark:text-slate-500">
                    <div className="flex flex-col items-center gap-2">
                      <Shield className="w-8 h-8 opacity-20" />
                      <p>No alerts found matching your criteria.</p>
                    </div>
                  </td>
                </tr>
              )}

              {filteredAlerts.map((alert) => (
                <tr key={alert.RowKey} className="group hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      ['Sev0', 'Sev1'].includes(alert.Severity) 
                        ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400' 
                        : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                    }`}>
                      {alert.Severity}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300 font-medium">
                      {getIconForType(alert.PartitionKey)}
                      {alert.PartitionKey}
                    </div>
                  </td>
                  <td className="px-6 py-4 font-medium text-slate-900 dark:text-slate-100">
                    <Link href={`/incidents/${alert.RowKey}`} className="hover:text-blue-600 dark:hover:text-blue-400 hover:underline">
                      {alert.RuleName}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-slate-600 dark:text-slate-400 max-w-md truncate">
                    {alert.ReportSummary}
                  </td>
                  <td className="px-6 py-4 text-right text-slate-400 dark:text-slate-500 whitespace-nowrap">
                    {new Date(alert.CreatedAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    </div>
  );
}

// --- Helper Components ---

function MetricCard({ label, value, icon, color = 'blue' }: any) {
  const bgColorClass = color === 'red' ? 'bg-red-50 dark:bg-red-900/20' : color === 'orange' ? 'bg-orange-50 dark:bg-orange-900/20' : 'bg-blue-50 dark:bg-blue-900/20';
  
  return (
    <div className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1">{value}</p>
      </div>
      <div className={`p-3 rounded-full ${bgColorClass}`}>
        {icon}
      </div>
    </div>
  );
}

function getIconForType(type: string) {
  switch (type) {
    case 'INFRA': return <Server className="w-4 h-4 text-orange-500 dark:text-orange-400" />;
    case 'DATABASE': return <Database className="w-4 h-4 text-blue-500 dark:text-blue-400" />;
    case 'APP': return <Activity className="w-4 h-4 text-purple-500 dark:text-purple-400" />;
    default: return <Shield className="w-4 h-4 text-slate-400 dark:text-slate-500" />;
  }
}

