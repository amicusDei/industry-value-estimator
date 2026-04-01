import { NextResponse } from 'next/server';
import rawData from '@/data/forecasts.json';

const OVERLAP_DISCOUNT = 0.85;

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const valuation = searchParams.get('valuation') || 'nominal';

  const data = rawData as any[];
  const vintage = data.length > 0 && data[0].data_vintage ? String(data[0].data_vintage) : null;

  const ptCol = valuation === 'real_2020' ? 'point_estimate_real_2020' : 'point_estimate_nominal';
  const ci80lCol = valuation === 'real_2020' ? 'ci80_lower' : 'ci80_lower_nominal';
  const ci80uCol = valuation === 'real_2020' ? 'ci80_upper' : 'ci80_upper_nominal';
  const ci95lCol = valuation === 'real_2020' ? 'ci95_lower' : 'ci95_lower_nominal';
  const ci95uCol = valuation === 'real_2020' ? 'ci95_upper' : 'ci95_upper_nominal';

  // Exclude "total" segment, aggregate the 4 sub-segments
  const sub = data.filter((d) => d.segment !== 'total');

  // Group by (year, quarter)
  const grouped: Record<string, any> = {};
  for (const r of sub) {
    const key = `${r.year}-${r.quarter}`;
    if (!grouped[key]) {
      grouped[key] = {
        year: r.year,
        quarter: r.quarter,
        point: 0,
        c80l: 0,
        c80u: 0,
        c95l: 0,
        c95u: 0,
        is_forecast: r.is_forecast,
      };
    }
    grouped[key].point += r[ptCol] ?? 0;
    grouped[key].c80l += r[ci80lCol] ?? r.ci80_lower ?? 0;
    grouped[key].c80u += r[ci80uCol] ?? r.ci80_upper ?? 0;
    grouped[key].c95l += r[ci95lCol] ?? r.ci95_lower ?? 0;
    grouped[key].c95u += r[ci95uCol] ?? r.ci95_upper ?? 0;
  }

  const rows = Object.values(grouped)
    .map((r: any) => ({
      year: r.year,
      quarter: r.quarter,
      segment: 'total',
      point_estimate: Math.round(r.point * OVERLAP_DISCOUNT * 100) / 100,
      ci80_lower: Math.round(r.c80l * OVERLAP_DISCOUNT * 100) / 100,
      ci80_upper: Math.round(r.c80u * OVERLAP_DISCOUNT * 100) / 100,
      ci95_lower: Math.round(r.c95l * OVERLAP_DISCOUNT * 100) / 100,
      ci95_upper: Math.round(r.c95u * OVERLAP_DISCOUNT * 100) / 100,
      is_forecast: r.is_forecast,
    }))
    .sort((a, b) => a.year - b.year || a.quarter - b.quarter);

  return NextResponse.json({ data: rows, count: rows.length, data_vintage: vintage });
}
