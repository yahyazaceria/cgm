'use client'

import { useState, useEffect } from 'react'
import GlucoseChart from './GlucoseChart'

interface GlucoseReading {
  id: number
  value: number
  timestamp: string
  deviceId: string
}

export default function Dashboard() {
  const [readings, setReadings] = useState<GlucoseReading[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchReadings = async () => {
      try {
        const response = await fetch('/api/readings')
        const data = await response.json()
        setReadings(data)
      } catch (err) {
        console.error('Failed to fetch readings:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchReadings()
    // Refresh data every 30 seconds
    const interval = setInterval(fetchReadings, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-8">Glucose Monitor</h1>
      
      {loading ? (
        <div className="text-center">Loading...</div>
      ) : (
        <>
          <div className="mb-8">
            <GlucoseChart readings={readings} />
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full table-auto">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-4 py-2">Time</th>
                  <th className="px-4 py-2">Glucose Level (mg/dL)</th>
                  <th className="px-4 py-2">Device ID</th>
                </tr>
              </thead>
              <tbody>
                {readings.map((reading) => (
                  <tr key={reading.id} className="border-b">
                    <td className="px-4 py-2">
                      {new Date(reading.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-2">{reading.value}</td>
                    <td className="px-4 py-2">{reading.deviceId}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
} 