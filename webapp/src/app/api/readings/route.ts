import { prisma } from '@/lib/prisma'
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    const readings = await prisma.glucoseReading.findMany({
      orderBy: {
        timestamp: 'desc'
      }
    })
    return NextResponse.json(readings)
  } catch (error) {
    console.error('Database Error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch readings' },
      { status: 500 }
    )
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const reading = await prisma.glucoseReading.create({
      data: {
        value: body.value,
        deviceId: body.deviceId
      }
    })
    return NextResponse.json(reading)
  } catch (error) {
    console.error('Database Error:', error)
    return NextResponse.json(
      { error: 'Failed to create reading' },
      { status: 500 }
    )
  }
} 