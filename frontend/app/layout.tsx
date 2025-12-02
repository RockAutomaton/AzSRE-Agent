import type { Metadata } from 'next'
import './globals.css'
import { ClientWrapper } from './components/ClientWrapper'

export const metadata: Metadata = {
  title: 'Azure SRE Agent Dashboard',
  description: 'Intelligent incident response and alert management',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ClientWrapper>
          {children}
        </ClientWrapper>
      </body>
    </html>
  )
}

