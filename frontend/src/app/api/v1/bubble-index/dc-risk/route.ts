import { NextResponse } from 'next/server';
import rawData from '@/data/bubble_dc_risk.json';

export async function GET() {
  return NextResponse.json(rawData);
}
