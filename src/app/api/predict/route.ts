import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const image = formData.get('image');
    
    if (!image) {
      return NextResponse.json(
        { error: 'No image provided' },
        { status: 400 }
      );
    }

    // Placeholder for ML model integration
    // For now, return a mock value
    const mockGlucoseLevel = Math.floor(Math.random() * (180 - 70) + 70);

    return NextResponse.json({
      glucoseLevel: mockGlucoseLevel
    });
  } catch (err) {
    console.error('Error processing image:', err);
    return NextResponse.json(
      { error: 'Failed to process image' },
      { status: 500 }
    );
  }
} 