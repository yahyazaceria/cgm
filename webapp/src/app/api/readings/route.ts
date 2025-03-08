import { NextResponse } from 'next/server'
import { prisma } from '@/lib/db'

export async function GET() {
  try {
    const readings = await prisma.glucoseReading.findMany({
      orderBy: {
        timestamp: 'desc'
      }
    })
    return NextResponse.json(readings)
  } catch (err) {
    console.error('Failed to fetch readings:', err)
    return NextResponse.json(
      { error: 'Failed to fetch readings' },
      { status: 500 }
    )
  }
}

export async function POST(request: Request) {
  try {
    const data = await request.json()
    const reading = await prisma.glucoseReading.create({
      data: {
        value: data.value,
        deviceId: data.deviceId,
        timestamp: new Date()
      }
    })
    return NextResponse.json(reading)
  } catch (err) {
    console.error('Failed to create reading:', err)
    return NextResponse.json(
      { error: 'Failed to create reading' },
      { status: 500 }
    )
  }
} 