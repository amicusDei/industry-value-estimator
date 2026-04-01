import { NextResponse } from 'next/server';
import segmentsMeta from '@/data/segments.json';
import forecasts from '@/data/forecasts.json';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const valuation = searchParams.get('valuation') || 'nominal';

  const ptCol = valuation === 'real_2020' ? 'point_estimate_real_2020' : 'point_estimate_nominal';

  const summaries = segmentsMeta.map((seg: any) => {
    const segFc = (forecasts as any[]).filter(
      (d: any) => d.segment === seg.id && d.quarter === 4
    );

    let marketSize: number | null = null;
    const q4_2025 = segFc.filter((d: any) => d.year === 2025);
    if (q4_2025.length > 0) {
      marketSize = Math.round(q4_2025[0][ptCol] * 10) / 10;
    }

    let cagr: number | null = null;
    const q4_2025_c = segFc.filter((d: any) => d.year === 2025);
    const q4_2030 = segFc.filter((d: any) => d.year === 2030);
    if (q4_2025_c.length > 0 && q4_2030.length > 0) {
      const vStart = q4_2025_c[0][ptCol];
      const vEnd = q4_2030[0][ptCol];
      if (vStart > 0) {
        cagr = Math.round((Math.pow(vEnd / vStart, 1 / 5) - 1) * 1000) / 10;
      }
    }

    return {
      id: seg.id,
      display_name: seg.display_name,
      market_size_2024_usd_b: marketSize,
      cagr_2025_2030_pct: cagr,
      overlap_note: seg.overlap_note || '',
    };
  });

  return NextResponse.json({ segments: summaries });
}
