import Link from "next/link";
import {
  getSegments,
  getForecasts,
  getScenarioForecasts,
  getDispersion,
  getBubbleIndex,
} from "@/lib/api";
import type {
  SegmentSummary,
  ForecastRow,
  ScenarioForecastRow,
  DispersionRow,
  BubbleIndexRow,
} from "@/lib/api";
import { formatUsdB, formatPct } from "@/lib/formatters";
import SegmentSparkline from "./SegmentSparkline";

export const dynamic = "force-dynamic";

/* ── risk-context templates (template-based, no LLM) ── */

function getRiskContext(
  segmentId: string,
  bubble: BubbleIndexRow | null
): string {
  if (!bubble) return "Risk data unavailable";

  switch (segmentId) {
    case "ai_hardware": {
      const ratio = bubble.capex_intensity_ratio?.toFixed(1) ?? "?";
      const comparison =
        bubble.capex_intensity_ratio > 2.5 ? "exceeds" : "comparable";
      return `Capex intensity at ${ratio}× — ${comparison} to dotcom peak`;
    }
    case "ai_infrastructure": {
      const yoy = bubble.dc_yoy_growth_pct?.toFixed(0) ?? "?";
      const credit = bubble.credit_total_usd_b?.toFixed(0) ?? "?";
      return `DC build rate +${yoy}% YoY, $${credit}B credit exposure`;
    }
    case "ai_software": {
      const roiPct = bubble.roi_from_headcount_pct?.toFixed(0) ?? "?";
      return `Enterprise adoption, but ${roiPct}% report zero ROI`;
    }
    case "ai_adoption": {
      const capexGrowth = bubble.ai_capex_growth_yoy_pct ?? 0;
      const prodGrowth = bubble.us_productivity_growth_pct ?? 1;
      const ratio =
        prodGrowth > 0 ? (capexGrowth / prodGrowth).toFixed(0) : "?";
      return `Productivity gap: ${ratio}× — AI capex growing faster than productivity`;
    }
    default:
      return "Risk data unavailable";
  }
}

/* ── dispersion trend ── */

function getDispersionTrend(
  segmentId: string,
  dispersionData: DispersionRow[]
): { label: string; color: string } {
  const rows = dispersionData
    .filter((r) => r.segment === segmentId)
    .sort((a, b) => a.year - b.year);

  if (rows.length < 2) return { label: "N/A", color: "text-muted" };

  const last = rows[rows.length - 1];
  const prev = rows[rows.length - 2];
  const rising = last.iqr_usd_billions > prev.iqr_usd_billions;

  return rising
    ? { label: "Diverging ▲", color: "text-accent" }
    : { label: "Converging ▼", color: "text-positive" };
}

/* ── scenario range for 2030 ── */

function getScenarioRange(
  segmentId: string,
  scenarioData: ScenarioForecastRow[]
): { conservative: string; aggressive: string } | null {
  const rows2030 = scenarioData.filter(
    (r) => r.segment === segmentId && r.year === 2030 && r.quarter === 4
  );

  const conservative = rows2030.find(
    (r) => r.scenario === "bear" || r.scenario === "conservative"
  );
  const aggressive = rows2030.find(
    (r) => r.scenario === "bull" || r.scenario === "aggressive"
  );

  if (!conservative && !aggressive) return null;

  return {
    conservative: conservative
      ? formatUsdB(conservative.point_estimate)
      : "N/A",
    aggressive: aggressive ? formatUsdB(aggressive.point_estimate) : "N/A",
  };
}

/* ── sparkline data ── */

interface SparkPoint {
  year: number;
  value: number;
  isForecast: boolean;
}

function getSparklineData(
  segmentId: string,
  forecastData: ForecastRow[]
): SparkPoint[] {
  // Only use Q4 data for annual sparkline
  return forecastData
    .filter((r) => r.segment === segmentId && r.quarter === 4)
    .sort((a, b) => a.year - b.year)
    .map((r) => ({
      year: r.year,
      value: r.point_estimate,
      isForecast: r.is_forecast,
    }));
}

export default async function SegmentsPage() {
  /* ── parallel data fetch with graceful degradation ── */
  const [segmentsResult, forecastsResult, scenariosResult, dispersionResult, bubbleResult] =
    await Promise.all([
      getSegments().catch(() => null),
      getForecasts().catch(() => null),
      getScenarioForecasts().catch(() => null),
      getDispersion().catch(() => null),
      getBubbleIndex().catch(() => null),
    ]);

  const segments: SegmentSummary[] = segmentsResult?.segments ?? [];
  const forecastData: ForecastRow[] = forecastsResult?.data ?? [];
  const scenarioData: ScenarioForecastRow[] = scenariosResult?.data ?? [];
  const dispersionData: DispersionRow[] = dispersionResult?.data ?? [];

  // Get latest bubble index row
  const bubbleRows: BubbleIndexRow[] = Array.isArray(bubbleResult)
    ? bubbleResult
    : [];
  const latestBubble =
    bubbleRows.length > 0
      ? bubbleRows.sort(
          (a, b) => b.year - a.year || b.half - a.half
        )[0]
      : null;

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Segment Intelligence</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {segments.map((seg) => {
          const pct = formatPct(seg.cagr_2025_2030_pct);
          const trend = getDispersionTrend(seg.id, dispersionData);
          const range = getScenarioRange(seg.id, scenarioData);
          const riskCtx = getRiskContext(seg.id, latestBubble);
          const sparkData = getSparklineData(seg.id, forecastData);

          return (
            <Link
              key={seg.id}
              href={`/segments/${seg.id}`}
              className="bg-surface border border-slate-800 rounded-lg p-5 hover:border-accent transition-colors block"
            >
              <div className="flex justify-between items-start">
                {/* Left: content */}
                <div className="flex-1 min-w-0">
                  {/* Header */}
                  <div className="flex items-baseline gap-3 mb-3">
                    <h2 className="font-semibold text-base truncate">
                      {seg.display_name}
                    </h2>
                    <span className="font-mono text-lg text-slate-100 whitespace-nowrap">
                      {formatUsdB(seg.market_size_2024_usd_b)}
                    </span>
                  </div>

                  {/* Row 1 — Growth */}
                  <div className="flex items-center gap-3 mb-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-medium ${pct.colorClass} bg-slate-800`}
                    >
                      {pct.text} CAGR
                    </span>
                    {range && (
                      <span className="text-xs text-muted truncate">
                        Conservative: {range.conservative} — Aggressive:{" "}
                        {range.aggressive}{" "}
                        <span className="text-slate-600">(2030)</span>
                      </span>
                    )}
                  </div>

                  {/* Row 2 — Confidence */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-muted">Analyst consensus:</span>
                    <span className={`text-xs font-medium ${trend.color}`}>
                      {trend.label}
                    </span>
                  </div>

                  {/* Row 3 — Risk Context */}
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {riskCtx}
                  </p>
                </div>

                {/* Right: Sparkline */}
                {sparkData.length > 0 && (
                  <div className="ml-4 flex-shrink-0">
                    <SegmentSparkline data={sparkData} />
                  </div>
                )}
              </div>
            </Link>
          );
        })}
      </div>

      {segments.length === 0 && (
        <p className="text-muted text-sm mt-8">
          No segment data available. Check API connectivity.
        </p>
      )}
    </div>
  );
}
