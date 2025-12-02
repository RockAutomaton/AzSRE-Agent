'use client';

import useSWR from 'swr';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';
import { format, parseISO, startOfHour, subHours } from 'date-fns';
import { Activity, PieChart as PieIcon, BarChart3, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#EF4444'];

export default function AnalyticsPage() {
  const { data: alerts, error } = useSWR('http://localhost:8000/api/history', fetcher);

  if (error) return <div className="p-8 text-red-500 dark:text-red-400">Failed to load data.</div>;
  if (!alerts) return <div className="p-8 text-slate-500 dark:text-slate-400">Calculating metrics...</div>;

  // --- Data Transformation Logic ---

  // 1. Severity Distribution
  const severityCounts = alerts.reduce((acc: any, curr: any) => {
    acc[curr.Severity] = (acc[curr.Severity] || 0) + 1;
    return acc;
  }, {});
  
  const severityData = Object.keys(severityCounts).map((key) => ({
    name: key,
    value: severityCounts[key],
  }));

  // 2. Classification Distribution
  const typeCounts = alerts.reduce((acc: any, curr: any) => {
    acc[curr.PartitionKey] = (acc[curr.PartitionKey] || 0) + 1;
    return acc;
  }, {});

  const typeData = Object.keys(typeCounts).map((key) => ({
    name: key,
    value: typeCounts[key],
  }));

  // 3. Timeline (Alerts per Hour)
  // Group by hour
  const timelineMap = new Map();
  alerts.forEach((alert: any) => {
    const date = parseISO(alert.CreatedAt);
    const hourKey = format(startOfHour(date), 'HH:mm');
    timelineMap.set(hourKey, (timelineMap.get(hourKey) || 0) + 1);
  });
  
  // Convert to array and reverse to show oldest -> newest
  const timelineData = Array.from(timelineMap, ([time, count]) => ({ time, count })).reverse();

  return (
    <div className="min-h-screen p-8 bg-slate-50 dark:bg-slate-900">
      <div className="max-w-6xl mx-auto space-y-8 pb-10">
        {/* Back Button */}
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors mb-4">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Dashboard
        </Link>
        
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-3">
            <BarChart3 className="text-blue-600 dark:text-blue-400" /> SRE Analytics
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Trends and patterns from the last {alerts.length} incidents.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Timeline Chart */}
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm lg:col-span-2">
            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-200 mb-6 flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-400 dark:text-slate-500" /> Alert Volume (Timeline)
            </h3>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={timelineData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Severity Pie Chart */}
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-200 mb-6 flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-slate-400 dark:text-slate-500" /> Severity Breakdown
            </h3>
            <div className="h-[300px] w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    fill="#8884d8"
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {severityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36}/>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Classification Bar Chart */}
          <div className="bg-white dark:bg-slate-800 p-6 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-200 mb-6 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-slate-400 dark:text-slate-500" /> Incident Classifications
            </h3>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={typeData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                  <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={12} width={80} />
                  <Tooltip 
                    cursor={{fill: 'transparent'}}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Bar dataKey="value" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={30} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

