import { NextResponse } from 'next/server';
import rawData from '@/data/validation.json';

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
    bottom_up_sum: Math.round(r.bottom_up_sum * 100) / 100,
    top_down_estimate: Math.round(r.top_down_estimate * 100) / 100,
    coverage_ratio: Math.round(r.coverage_ratio * 10000) / 10000,
    gap_usd_billions: Math.round(r.gap_usd_billions * 100) / 100,
    n_companies: r.n_companies,
    top_contributors: r.top_contributors || [],
    company_capex_sum: Math.round((r.company_capex_sum || 0) * 100) / 100,
    capex_intensity: Math.round((r.capex_intensity || 0) * 10000) / 10000,
    capex_implied_growth: r.capex_implied_growth != null
      ? Math.round(r.capex_implied_growth * 10000) / 10000
      : null,
  }));

  return NextResponse.json({ data: rows, count: rows.length });
}
