import { NextResponse } from 'next/server';
import allInsights from '@/data/insights.json';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const segment = searchParams.get('segment');

  if (!segment) {
    return NextResponse.json({ data: [], count: 0, segment: '' }, { status: 400 });
  }

  const insights = (allInsights as Record<string, any[]>)[segment] || [];

  const items = insights.map((r: any) => ({
    type: r.type,
    text: r.text,
    priority: r.priority,
  }));

  return NextResponse.json({ data: items, count: items.length, segment });
}
