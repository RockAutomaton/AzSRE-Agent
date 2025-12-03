'use client';

import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  mounted: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  // Always start with 'light' to match server render
  const [theme, setTheme] = useState<Theme>('light');
  const [mounted, setMounted] = useState(false);
  const themeRef = useRef<Theme>('light');

  // Initialize theme on mount
  useEffect(() => {
    // Read the actual theme from localStorage or DOM on mount
    const savedTheme = localStorage.getItem('theme') as Theme | null;
    const hasDarkClass = document.documentElement.classList.contains('dark');
    
    // Determine the actual current theme
    let actualTheme: Theme = 'light';
    if (savedTheme === 'dark' || savedTheme === 'light') {
      actualTheme = savedTheme;
    } else if (hasDarkClass) {
      actualTheme = 'dark';
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      actualTheme = prefersDark ? 'dark' : 'light';
    }
    
    // Sync state and ref to match what's in localStorage/DOM
    setTheme(actualTheme);
    themeRef.current = actualTheme;
    setMounted(true);
  }, []); // Only run once on mount

  // Sync DOM with theme state changes (backup in case toggleTheme DOM update doesn't work)
  useEffect(() => {
    if (!mounted) return; // Don't apply until after initial mount
    
    // Apply the theme class to the DOM
    const htmlEl = document.documentElement;
    if (theme === 'dark') {
      htmlEl.classList.add('dark');
    } else {
      htmlEl.classList.remove('dark');
    }
  }, [theme, mounted]);

  const toggleTheme = useCallback(() => {
    // Get current theme from ref (always up-to-date)
    const currentTheme = themeRef.current;
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    // Update ref immediately
    themeRef.current = newTheme;
    
    // Update localStorage
    localStorage.setItem('theme', newTheme);
    
    // Update DOM immediately and synchronously
    const htmlEl = document.documentElement;
    if (newTheme === 'dark') {
      htmlEl.classList.add('dark');
    } else {
      htmlEl.classList.remove('dark');
    }
    
    // Update React state (this will trigger re-renders)
    setTheme(newTheme);
  }, []);

  // Always provide the context, even before mounting
  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, mounted }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

