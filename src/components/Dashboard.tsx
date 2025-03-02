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
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [readings, setReadings] = useState<GlucoseReading[]>([])
  const [loading, setLoading] = useState(true)

  // Filter readings for selected date
  const selectedDateStr = selectedDate.toISOString().split('T')[0]
  const filteredReadings = readings.filter(reading => {
    const readingDate = new Date(reading.timestamp).toISOString().split('T')[0]
    return readingDate === selectedDateStr
  })

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
    <div className="max-w-7xl mx-auto px-4">
      <h1 className="text-2xl md:text-3xl font-bold mb-6">Glucose Monitor</h1>
      
      {loading ? (
        <div className="text-center">Loading...</div>
      ) : (
        <div className="space-y-6">
          <GlucoseChart 
            readings={readings}
            selectedDate={selectedDate}
            onDateChange={setSelectedDate}
          />
          
          <div className="overflow-x-auto bg-white rounded-lg shadow-sm">
            <table className="min-w-full table-auto">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Time</th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Glucose Level (mg/dL)</th>
                  <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Device ID</th>
                </tr>
              </thead>
              <tbody>
                {filteredReadings.map((reading) => (
                  <tr key={reading.id} className="border-t">
                    <td className="px-4 py-2 text-sm">{new Date(reading.timestamp).toLocaleTimeString()}</td>
                    <td className="px-4 py-2 text-sm">{reading.value.toFixed(1)}</td>
                    <td className="px-4 py-2 text-sm">{reading.deviceId}</td>
                  </tr>
                ))}
                {filteredReadings.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-sm text-gray-500">
                      No readings for this date
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
} 