'use client';

import Link from 'next/link';
import { ThemeToggle } from './ThemeToggle';

export function Navbar() {
  return (
    <nav className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-8 py-4">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-xl font-bold text-slate-800 dark:text-slate-100">
            Azure SRE Agent
          </Link>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-6 text-sm text-slate-600 dark:text-slate-300">
              <Link href="/" className="hover:text-blue-600 dark:hover:text-blue-400">Dashboard</Link>
              <Link href="/history" className="hover:text-blue-600 dark:hover:text-blue-400">History</Link>
              <Link href="/analytics" className="hover:text-blue-600 dark:hover:text-blue-400">Analytics</Link>
              <Link href="/chat" className="hover:text-blue-600 dark:hover:text-blue-400">Investigator</Link>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </nav>
  );
}

