import { NextResponse } from 'next/server';
import rawData from '@/data/dispersion.json';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const segment = searchParams.get('segment');

  let data = rawData as any[];

  if (segment) {
    data = data.filter((d: any) => d.segment === segment);
  }

  data.sort((a: any, b: any) => a.segment.localeCompare(b.segment) || a.year - b.year);

  const rows = data.map((r: any) => ({
    segment: r.segment,
    year: r.year,
    iqr_usd_billions: Math.round(r.iqr_usd_billions * 1000) / 1000,
    std_usd_billions: Math.round(r.std_usd_billions * 1000) / 1000,
    min_usd_billions: Math.round(r.min_usd_billions * 1000) / 1000,
    max_usd_billions: Math.round(r.max_usd_billions * 1000) / 1000,
    n_sources: r.n_sources,
    dispersion_ratio: Math.round(r.dispersion_ratio * 10000) / 10000,
  }));

  return NextResponse.json({ data: rows, count: rows.length });
}
