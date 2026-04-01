import { NextResponse } from 'next/server';
import rawData from '@/data/companies.json';

export async function GET() {
  const data = rawData as any[];

  const rows = data.map((r: any) => ({
    company_name: r.company_name,
    cik: String(r.cik),
    segment: r.segment,
    ai_revenue_usd_billions: r.ai_revenue_usd_billions,
    attribution_method: r.attribution_method,
    value_chain_layer: r.value_chain_layer,
  }));

  return NextResponse.json({ data: rows, count: rows.length });
}
