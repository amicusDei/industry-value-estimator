import { NextResponse } from 'next/server';
import dataQuality from '@/data/data_quality.json';

export async function GET() {
  return NextResponse.json(dataQuality);
}
