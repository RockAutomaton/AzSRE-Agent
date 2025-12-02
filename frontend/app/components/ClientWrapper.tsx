'use client';

import { ThemeProvider } from './ThemeProvider';
import { Navbar } from './Navbar';

export function ClientWrapper({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <Navbar />
      {children}
    </ThemeProvider>
  );
}

