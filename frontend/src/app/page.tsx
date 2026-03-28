import KpiCard from "@/components/KpiCard";
import { getSegments } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  let segments: { id: string; display_name: string; market_size_2024_usd_b: number | null; cagr_2025_2030_pct: number | null }[] = [];
  let vintage = "";
  let totalMarket: number | null = null;

  try {
    const res = await getSegments();
    segments = res.segments;
    totalMarket = segments.reduce((sum, s) => sum + (s.market_size_2024_usd_b || 0), 0);
    vintage = new Date().toISOString().slice(0, 10);
  } catch {
    // API offline — show placeholder
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold mb-1">
          Global AI Market Overview
        </h1>
        <p className="text-muted text-sm">
          {totalMarket != null && (
            <span className="font-mono text-text">
              ${totalMarket.toFixed(0)}B
            </span>
          )}{" "}
          total market (2024, constant 2020 USD)
          {vintage && (
            <span className="ml-3 text-xs text-muted">
              Vintage: {vintage}
            </span>
          )}
        </p>
      </div>

      {/* KPI Grid */}
      {segments.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {segments.map((seg) => (
            <KpiCard
              key={seg.id}
              segmentName={seg.display_name}
              marketSize={seg.market_size_2024_usd_b}
              cagr={seg.cagr_2025_2030_pct}
            />
          ))}
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-lg p-8 text-center">
          <p className="text-muted">
            API offline. Start the backend:
          </p>
          <code className="font-mono text-accent text-sm mt-2 block">
            uv run uvicorn api.main:app --port 8000
          </code>
        </div>
      )}

      {/* Methodology footer */}
      <div className="mt-12 border-t border-border pt-6">
        <p className="text-xs text-muted leading-relaxed max-w-3xl">
          Forecasts produced by an ARIMA + Prophet + LightGBM ensemble trained on
          scope-normalized analyst consensus estimates from 8 firms (IDC, Gartner,
          Grand View Research, Statista, Goldman Sachs, Bloomberg Intelligence,
          McKinsey, CB Insights). Quarterly granularity, bootstrapped confidence
          intervals. All monetary values in 2020 constant USD.
        </p>
      </div>
    </div>
  );
}
