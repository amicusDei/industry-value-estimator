import { NextResponse } from 'next/server';
import rawData from '@/data/scenarios.json';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const segment = searchParams.get('segment');
  const scenario = searchParams.get('scenario');
  const valuation = searchParams.get('valuation') || 'nominal';

  let data = rawData as any[];

  if (segment) {
    data = data.filter((d) => d.segment === segment);
  }
  if (scenario) {
    data = data.filter((d) => d.scenario === scenario);
  }

  const vintage = data.length > 0 && data[0].data_vintage ? String(data[0].data_vintage) : null;

  const ptCol = valuation === 'real_2020' ? 'point_estimate_real_2020' : 'point_estimate_nominal';
  const ci80lCol = valuation === 'real_2020' ? 'ci80_lower' : 'ci80_lower_nominal';
  const ci80uCol = valuation === 'real_2020' ? 'ci80_upper' : 'ci80_upper_nominal';
  const ci95lCol = valuation === 'real_2020' ? 'ci95_lower' : 'ci95_lower_nominal';
  const ci95uCol = valuation === 'real_2020' ? 'ci95_upper' : 'ci95_upper_nominal';

  const rows = data.map((r: any) => ({
    year: r.year,
    quarter: r.quarter,
    segment: r.segment,
    scenario: r.scenario,
    point_estimate: r[ptCol] ?? r.point_estimate_nominal,
    ci80_lower: r[ci80lCol] ?? r.ci80_lower,
    ci80_upper: r[ci80uCol] ?? r.ci80_upper,
    ci95_lower: r[ci95lCol] ?? r.ci95_lower,
    ci95_upper: r[ci95uCol] ?? r.ci95_upper,
    is_forecast: r.is_forecast,
  }));

  return NextResponse.json({ data: rows, count: rows.length, data_vintage: vintage });
}
