import { NextResponse } from 'next/server';
import rawData from '@/data/bubble_dotcom.json';

export async function GET() {
  return NextResponse.json(rawData);
}
