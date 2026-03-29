import Link from "next/link";
import { getSegments } from "@/lib/api";
import { formatUsdB, formatPct } from "@/lib/formatters";
import ExportButton from "@/components/ExportButton";
import TotalChart from "@/components/TotalChart";

export const dynamic = "force-dynamic";

export default async function Home() {
  let segments: { id: string; display_name: string; market_size_2024_usd_b: number | null; cagr_2025_2030_pct: number | null }[] = [];
  let totalMarket = 0;

  try {
    const res = await getSegments("nominal");
    segments = res.segments;
    totalMarket = segments.reduce((s, seg) => s + (seg.market_size_2024_usd_b || 0), 0);
  } catch {
    // API offline
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold mb-1">Global AI Market Overview</h1>
          <p className="text-muted text-sm">
            <span className="font-mono text-text">{formatUsdB(totalMarket)}</span>{" "}
            total market (2025, nominal USD)
          </p>
        </div>
        <ExportButton label="Export All Data" />
      </div>

      {segments.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {segments.map((seg) => {
            const pct = formatPct(seg.cagr_2025_2030_pct);
            return (
              <Link
                key={seg.id}
                href={`/segments/${seg.id}`}
                className="bg-surface border border-border rounded-lg p-5 hover:border-accent transition-colors block"
              >
                <p className="text-muted text-xs uppercase tracking-wider mb-3">{seg.display_name}</p>
                <p className="font-mono text-3xl font-semibold text-text mb-2">
                  {formatUsdB(seg.market_size_2024_usd_b)}
                </p>
                <div className="flex items-center gap-2">
                  <span className="text-muted text-xs">CAGR 26-30</span>
                  <span className={`font-mono text-sm font-medium ${pct.colorClass}`}>{pct.text}</span>
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-lg p-8 text-center">
          <p className="text-muted">API offline.</p>
          <code className="font-mono text-accent text-sm mt-2 block">
            uv run uvicorn api.main:app --port 8000
          </code>
        </div>
      )}

      {/* Total Market Chart */}
      {segments.length > 0 && (
        <div className="mt-8">
          <TotalChart />
        </div>
      )}

      <div className="mt-12 border-t border-border pt-6">
        <p className="text-xs text-muted leading-relaxed max-w-3xl">
          Forecasts produced by an ARIMA + Prophet + LightGBM ensemble trained on
          scope-normalized analyst consensus from 8 firms. Quarterly granularity,
          bootstrapped confidence intervals. Values in nominal USD unless toggled.
        </p>
      </div>
    </div>
  );
}
