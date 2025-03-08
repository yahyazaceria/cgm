'use client';

import { useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface Reading {
  timestamp: string;
  value: number;
}

export default function Home() {
  const [readings, setReadings] = useState<Reading[]>([]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files?.[0]) return;

    const file = event.target.files[0];
    const formData = new FormData();
    formData.append('image', file);

    try {
      const response = await fetch('/api/predict', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      
      setReadings([...readings, {
        timestamp: new Date().toLocaleTimeString(),
        value: data.glucoseLevel
      }]);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const chartData = {
    labels: readings.map(r => r.timestamp),
    datasets: [{
      label: 'Glucose Levels',
      data: readings.map(r => r.value),
      borderColor: 'rgb(75, 192, 192)',
      tension: 0.1
    }]
  };

  return (
    <main className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Glucose Level Tracker</h1>
      
      <div className="mb-4">
        <input
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-full file:border-0
            file:text-sm file:font-semibold
            file:bg-violet-50 file:text-violet-700
            hover:file:bg-violet-100"
        />
      </div>

      <div className="h-[400px] mb-4">
        <Line 
          data={chartData}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                beginAtZero: true,
                title: {
                  display: true,
                  text: 'Glucose Level (mg/dL)'
                }
              }
            }
          }}
        />
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full table-auto">
          <thead>
            <tr>
              <th className="px-4 py-2">Time</th>
              <th className="px-4 py-2">Glucose Level (mg/dL)</th>
            </tr>
          </thead>
          <tbody>
            {readings.map((reading, index) => (
              <tr key={index}>
                <td className="border px-4 py-2">{reading.timestamp}</td>
                <td className="border px-4 py-2">{reading.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
} 