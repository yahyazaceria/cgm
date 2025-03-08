import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Glucose Monitor',
  description: 'Non-invasive glucose monitoring system',
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
