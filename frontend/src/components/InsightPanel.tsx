"use client";

import React from "react";

interface Insight {
  type: string;
  text: string;
  priority: number;
}

interface InsightPanelProps {
  insights: Insight[];
}

const TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  cagr_insight: { label: "CAGR", color: "#f97316" },
  dispersion_insight: { label: "DISP", color: "#8b5cf6" },
  scenario_spread: { label: "SCEN", color: "#06b6d4" },
  top_growth: { label: "RANK", color: "#22c55e" },
  yoy_momentum: { label: "MOM", color: "#eab308" },
};

function highlightNumbers(text: string): React.ReactNode[] {
  // Match $XXB, $XXXM, XX.X%, and similar numeric patterns
  const parts = text.split(/(\$[\d,.]+[BMT]|\d+\.?\d*%)/g);
  return parts.map((part, i) => {
    if (/^\$[\d,.]+[BMT]$/.test(part) || /^\d+\.?\d*%$/.test(part)) {
      return (
        <span key={i} className="font-mono text-accent font-medium">
          {part}
        </span>
      );
    }
    return part;
  });
}

export default function InsightPanel({ insights }: InsightPanelProps) {
  if (!insights || insights.length === 0) return null;

  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold mb-1">Key Insights</h2>
      <p className="text-muted text-xs mb-3">
        Automated narrative analysis derived from forecast data, analyst dispersion, and scenario modeling.
      </p>
      <div className="grid gap-2">
        {insights.map((insight, idx) => {
          const cfg = TYPE_CONFIG[insight.type] || {
            label: "INFO",
            color: "#64748b",
          };
          return (
            <div
              key={idx}
              className="bg-surface border border-border rounded-lg p-3 flex items-start gap-3"
              style={{ borderLeftWidth: "3px", borderLeftColor: cfg.color }}
            >
              <span
                className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded shrink-0 mt-0.5"
                style={{
                  backgroundColor: cfg.color + "20",
                  color: cfg.color,
                }}
              >
                {cfg.label}
              </span>
              <p className="text-sm text-text leading-relaxed">
                {highlightNumbers(insight.text)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
