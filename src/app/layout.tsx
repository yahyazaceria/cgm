import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Glucose Level Tracker',
  description: 'Track your glucose levels using image analysis',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
} 