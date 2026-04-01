import { NextResponse } from 'next/server';
import forecastsData from '@/data/forecasts.json';
import scenariosData from '@/data/scenarios.json';

function filterForecasts(segment: string | null, scenario: string, valuation: string) {
  let data: any[];

  if (scenario === 'conservative' || scenario === 'aggressive') {
    data = (scenariosData as any[]).filter((r) => r.scenario === scenario);
  } else {
    data = forecastsData as any[];
  }

  if (segment) {
    data = data.filter((r) => r.segment === segment);
  }

  const ptCol = valuation === 'real_2020' ? 'point_estimate_real_2020' : 'point_estimate_nominal';
  const ci80lCol = valuation === 'real_2020' ? 'ci80_lower' : 'ci80_lower_nominal';
  const ci80uCol = valuation === 'real_2020' ? 'ci80_upper' : 'ci80_upper_nominal';
  const ci95lCol = valuation === 'real_2020' ? 'ci95_lower' : 'ci95_lower_nominal';
  const ci95uCol = valuation === 'real_2020' ? 'ci95_upper' : 'ci95_upper_nominal';

  return data.map((r) => ({
    Year: r.year,
    Quarter: r.quarter,
    Segment: r.segment,
    Type: r.is_forecast ? 'Forecast' : 'Historical',
    'Point Estimate ($B)': Math.round((r[ptCol] ?? r.point_estimate_nominal) * 10) / 10,
    'CI80 Low ($B)': Math.round((r[ci80lCol] ?? r.ci80_lower) * 10) / 10,
    'CI80 High ($B)': Math.round((r[ci80uCol] ?? r.ci80_upper) * 10) / 10,
    'CI95 Low ($B)': Math.round((r[ci95lCol] ?? r.ci95_lower) * 10) / 10,
    'CI95 High ($B)': Math.round((r[ci95uCol] ?? r.ci95_upper) * 10) / 10,
  }));
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const segment = searchParams.get('segment');
  const scenario = searchParams.get('scenario') || 'base';
  const valuation = searchParams.get('valuation') || 'nominal';

  const rows = filterForecasts(segment, scenario, valuation);

  if (rows.length === 0) {
    return new NextResponse('No data', { status: 404 });
  }

  const headers = Object.keys(rows[0]);
  const csvLines = [
    headers.join(','),
    ...rows.map((r: any) => headers.map((h) => JSON.stringify(r[h] ?? '')).join(',')),
  ];
  const csv = csvLines.join('\n');

  const segLabel = segment || 'all';
  const today = new Date().toISOString().split('T')[0];
  const filename = `ai_industry_${segLabel}_${scenario}_${today}.csv`;

  return new NextResponse(csv, {
    headers: {
      'Content-Type': 'text/csv',
      'Content-Disposition': `attachment; filename="${filename}"`,
    },
  });
}
