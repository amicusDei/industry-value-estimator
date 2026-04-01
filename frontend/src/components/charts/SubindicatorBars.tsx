"use client";

import type { BubbleIndexRow } from "@/lib/api";

interface Props {
  data: BubbleIndexRow;
}

function barColor(score: number): string {
  if (score < 30) return "#22c55e";
  if (score < 50) return "#eab308";
  if (score < 70) return "#f97316";
  return "#ef4444";
}

interface BarDef {
  key: keyof BubbleIndexRow;
  label: string;
  detail?: string;
}

const SECTIONS: { title: string; bars: BarDef[] }[] = [
  {
    title: "Investment Intensity",
    bars: [
      {
        key: "capex_intensity_score",
        label: "Capex Intensity",
        detail: "Hyperscaler AI capex-to-revenue ratio",
      },
      {
        key: "concentration_score",
        label: "Market Concentration",
        detail: "Top-5 share of S&P 500",
      },
      {
        key: "dc_build_score",
        label: "DC Build Momentum",
        detail: "Data centre capacity YoY growth",
      },
      {
        key: "credit_score",
        label: "Credit Exposure",
        detail: "Bonds + private credit + off-balance-sheet",
      },
      {
        key: "shadow_score",
        label: "Shadow Leverage",
        detail: "BIS qualitative risk rating",
      },
    ],
  },
  {
    title: "Productivity & ROI",
    bars: [
      {
        key: "enterprise_roi_score",
        label: "Enterprise ROI",
        detail: "Lower ROI realization = higher bubble risk",
      },
      {
        key: "productivity_gap_score",
        label: "Productivity Gap",
        detail: "Capex growth vs. productivity growth (Solow index)",
      },
    ],
  },
  {
    title: "Historical Parallel",
    bars: [
      {
        key: "dotcom_parallel_score",
        label: "Dotcom Parallel Score",
        detail: "Composite distance to dotcom cycle equivalent",
      },
    ],
  },
];

export default function SubindicatorBars({ data }: Props) {
  return (
    <div className="space-y-6">
      {SECTIONS.map((section) => (
        <div key={section.title}>
          <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
            {section.title}
          </h3>
          <div className="space-y-2.5">
            {section.bars.map((bar) => {
              const score = Number(data[bar.key]) || 0;
              const color = barColor(score);
              return (
                <div key={String(bar.key)} className="group">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-text">{bar.label}</span>
                    <span
                      className="font-mono text-sm font-semibold"
                      style={{ color }}
                    >
                      {Math.round(score)}
                    </span>
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
                  {bar.detail && (
                    <p className="text-[10px] text-muted mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      {bar.detail}
                    </p>
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
