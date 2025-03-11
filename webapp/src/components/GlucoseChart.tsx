'use client'

import { Line } from 'react-chartjs-2'
import Calendar from 'react-calendar'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import 'react-calendar/dist/Calendar.css'

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface GlucoseReading {
  id: number
  value: number
  timestamp: string
  deviceId: string
}

interface Props {
  readings: GlucoseReading[]
  selectedDate: Date
  onDateChange: (date: Date) => void
}

export default function GlucoseChart({ readings, selectedDate, onDateChange }: Props) {
  // Group readings by date
  const readingsByDate = readings.reduce((acc, reading) => {
    const date = new Date(reading.timestamp).toISOString().split('T')[0]
    if (!acc[date]) {
      acc[date] = []
    }
    acc[date].push(reading)
    return acc
  }, {} as Record<string, GlucoseReading[]>)

  // Get readings for selected date
  const dateStr = selectedDate.toISOString().split('T')[0]
  const selectedReadings = readingsByDate[dateStr] || []

  // Get dates with readings
  const datesWithReadings = new Set(Object.keys(readingsByDate))

  const data = {
    labels: selectedReadings.map(r => new Date(r.timestamp).toLocaleTimeString()),
    datasets: [
      {
        label: 'Glucose Level',
        data: selectedReadings.map(r => r.value),
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1
      }
    ]
  }

  return (
    <div className="flex flex-col md:flex-row gap-4">
      <div className="order-2 md:order-1 md:w-[400px] p-6 bg-white rounded-lg shadow-sm">
        <Calendar
          onChange={onDateChange}
          value={selectedDate}
          tileClassName={({ date }) => {
            const dateStr = date.toISOString().split('T')[0]
            return datesWithReadings.has(dateStr) ? 'has-readings' : ''
          }}
          className="mx-auto scale-125"
        />
      </div>
      
      <div className="order-1 md:order-2 flex-1 bg-white p-6 rounded-lg shadow-sm">
        <div className="w-full h-[400px]">
          <Line
            data={data}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                y: {
                  beginAtZero: false,
                  min: 0,
                  max: 350,
                  title: {
                    display: true,
                    text: 'Glucose Level (mg/dL)'
                  }
                }
              }
            }}
          />
        </div>
      </div>
    </div>
  )
} 