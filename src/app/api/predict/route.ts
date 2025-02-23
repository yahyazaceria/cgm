import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function POST(request: Request) {
  try {
    const data = await request.formData();
    const image = data.get('image');
    
    // Handle image and call Python script
    const { stdout } = await execAsync(`python transfer_cnn.py ${image}`);
    const glucoseLevel = parseFloat(stdout);

    return NextResponse.json({ glucoseLevel });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
} 