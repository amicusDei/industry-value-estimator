"use client";

import type { BubbleIndexRow } from "@/lib/api";

interface Props {
  data: BubbleIndexRow;
  previousData?: BubbleIndexRow;
}

function barColor(score: number): string {
  if (score < 30) return "#22c55e";
  if (score < 50) return "#eab308";
  if (score < 70) return "#f97316";
  return "#ef4444";
}

/** Format a context line for each sub-indicator using raw data from the API */
function contextLine(key: string, d: BubbleIndexRow): string {
  switch (key) {
    case "capex_intensity_score":
      return `Ratio: ${d.capex_intensity_ratio.toFixed(1)}\u00d7 | $${Math.round(d.hyperscaler_ai_capex_usd_b)}B capex / $${Math.round(d.ai_revenue_usd_b)}B revenue`;
    case "concentration_score":
      return `AI Revenue HHI: ${d.ai_revenue_hhi.toFixed(2)} | NVIDIA ${d.top_player_ai_share_pct.toFixed(0)}% AI chip market share`;
    case "dc_build_score":
      return `${d.new_capacity_mw.toLocaleString()} MW new capacity | ${d.dc_yoy_growth_pct.toFixed(0)}% YoY growth`;
    case "credit_score": {
      const bonds = Math.round(d.hyperscaler_bonds_usd_b);
      const priv = Math.round(d.private_credit_ai_usd_b);
      const obs = Math.round(d.off_balance_sheet_est_usd_b);
      return `$${Math.round(d.credit_total_usd_b)}B total | $${bonds}B bonds + $${priv}B private + $${obs}B off-BS`;
    }
    case "shadow_score":
      return `Off-BS ratio: ${d.off_bs_ratio.toFixed(1)}\u00d7 | ${d.spv_jv_count} SPV/JVs | ${d.asset_life_mismatch_ratio.toFixed(0)}\u00d7 asset-life mismatch`;
    case "enterprise_roi_score": {
      const gap = Math.max(0, d.enterprise_ai_spend_growth_pct - d.revenue_and_cost_impact_pct);
      return `Spend +${d.enterprise_ai_spend_growth_pct.toFixed(0)}% vs ${d.revenue_and_cost_impact_pct.toFixed(0)}% impact (gap: ${gap.toFixed(0)}pp) | ${d.roi_from_headcount_pct.toFixed(0)}% ROI from headcount | ${d.margin_erosion_from_ai_infra_pct.toFixed(0)}% margin erosion`;
    }
    case "productivity_gap_score": {
      const gap = d.us_productivity_growth_pct > 0
        ? (d.ai_capex_growth_yoy_pct / d.us_productivity_growth_pct).toFixed(0)
        : "N/A";
      return `Capex +${d.ai_capex_growth_yoy_pct.toFixed(0)}% vs Productivity +${d.us_productivity_growth_pct.toFixed(1)}% | Solow Gap: ${gap}\u00d7`;
    }
    case "dotcom_parallel_score":
      return `AI cycle year ${d.ai_cycle_year} \u2248 Dotcom ${d.dotcom_equivalent_year}`;
    default:
      return "";
  }
}

/** Output indicators have inverted color logic: rising score = risk rising,
 *  but for these indicators, a falling score means improving conditions (green). */
const OUTPUT_INDICATORS = new Set([
  "enterprise_roi_score",
  "productivity_gap_score",
]);

interface TrendInfo {
  delta: number;
  triangle: string;
  colorClass: string;
}

function getTrend(
  key: string,
  current: number,
  previous: number | undefined
): TrendInfo | null {
  if (previous === undefined) return null;
  const delta = current - previous;
  if (Math.abs(delta) < 0.1) return null;

  const isRising = delta > 0;
  const triangle = isRising ? "\u25b2" : "\u25bc";

  // Input indicators: rising = red (more risk), falling = green (less risk)
  // Output indicators (Enterprise ROI, Productivity Gap): inverted color logic
  const isOutputIndicator = OUTPUT_INDICATORS.has(key);
  const isRed = isOutputIndicator ? !isRising : isRising;
  const colorClass = isRed ? "text-red-400" : "text-emerald-400";

  return { delta, triangle, colorClass };
}

interface BarDef {
  key: keyof BubbleIndexRow;
  label: string;
}

const SECTIONS: { title: string; bars: BarDef[] }[] = [
  {
    title: "Investment Intensity",
    bars: [
      { key: "capex_intensity_score", label: "Capex Intensity" },
      { key: "concentration_score", label: "Market Concentration" },
      { key: "dc_build_score", label: "DC Build Momentum" },
      { key: "credit_score", label: "Credit Exposure" },
      { key: "shadow_score", label: "Shadow Leverage" },
    ],
  },
  {
    title: "Productivity & ROI",
    bars: [
      { key: "enterprise_roi_score", label: "Enterprise ROI" },
      { key: "productivity_gap_score", label: "Productivity Gap" },
    ],
  },
  {
    title: "Historical Parallel",
    bars: [
      { key: "dotcom_parallel_score", label: "Dotcom Parallel Score" },
    ],
  },
];

export default function SubindicatorBars({ data, previousData }: Props) {
  return (
    <div className="space-y-6">
      {SECTIONS.map((section) => (
        <div key={section.title}>
          <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
            {section.title}
          </h3>
          <div className="space-y-3">
            {section.bars.map((bar) => {
              const score = Number(data[bar.key]) || 0;
              const prevScore = previousData
                ? Number(previousData[bar.key]) || 0
                : undefined;
              const color = barColor(score);
              const trend = getTrend(String(bar.key), score, prevScore);
              const context = contextLine(String(bar.key), data);

              return (
                <div key={String(bar.key)}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-text">{bar.label}</span>
                    <div className="flex items-center gap-2">
                      <span
                        className="font-mono text-sm font-semibold"
                        style={{ color }}
                      >
                        {Math.round(score)}
                      </span>
                      {trend && (
                        <span
                          className={`font-mono text-xs ${trend.colorClass}`}
                        >
                          {trend.triangle}{" "}
                          {trend.delta > 0 ? "+" : ""}
                          {trend.delta.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="h-2.5 bg-[#1e293b] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700 ease-out"
                      style={{
                        width: `${Math.min(100, Math.max(0, score))}%`,
                        backgroundColor: color,
                        opacity: 0.85,
                      }}
                    />
                  </div>
                  {context && (
                    <p className="text-xs text-slate-500 mt-1">{context}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
