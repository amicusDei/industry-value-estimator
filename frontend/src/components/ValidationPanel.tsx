"use client";

import React from "react";
import type { ValidationRow } from "@/lib/api";

interface ValidationPanelProps {
  data: ValidationRow[];
}

function coverageColor(ratio: number): string {
  if (ratio >= 0.7) return "#22c55e";
  if (ratio >= 0.4) return "#eab308";
  return "#ef4444";
}

function coverageLabel(ratio: number): string {
  if (ratio >= 0.7) return "High";
  if (ratio >= 0.4) return "Moderate";
  return "Low";
}

export default function ValidationPanel({ data }: ValidationPanelProps) {
  if (!data || data.length === 0) return null;

  // Use the latest year available for the primary display
  const latestYear = Math.max(...data.map((r) => r.year));
  const latest = data.find((r) => r.year === latestYear);
  if (!latest) return null;

  const pct = (latest.coverage_ratio * 100).toFixed(1);
  const color = coverageColor(latest.coverage_ratio);
  const barWidth = Math.min(latest.coverage_ratio * 100, 100);

  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold mb-1">Bottom-Up Validation</h2>
      <p className="text-muted text-xs mb-3">
        Cross-reference of top-down analyst consensus with company-level EDGAR
        filings. Shows what fraction of the market is explained by known public
        companies.
      </p>
      <div className="bg-surface border border-border rounded-lg p-4">
        {/* Coverage bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-muted">
              Coverage ({latestYear})
            </span>
            <span
              className="text-xs font-mono font-medium px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: color + "20",
                color: color,
              }}
            >
              {coverageLabel(latest.coverage_ratio)}
            </span>
          </div>
          <div className="relative h-6 bg-[#ffffff08] rounded overflow-hidden">
            {/* Bottom-up (solid fill) */}
            <div
              className="absolute inset-y-0 left-0 rounded"
              style={{
                width: `${barWidth}%`,
                backgroundColor: "#f97316",
                opacity: 0.85,
              }}
            />
            {/* Top-down outline (full bar) */}
            <div className="absolute inset-0 rounded border border-[#f9731640]" />
            {/* Labels inside bar */}
            <div className="absolute inset-0 flex items-center justify-between px-2">
              <span className="text-[10px] font-mono text-white/90 z-10">
                ${latest.bottom_up_sum.toFixed(1)}B
              </span>
              <span className="text-[10px] font-mono text-muted z-10">
                ${latest.top_down_estimate.toFixed(1)}B
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-[10px] text-muted">Bottom-up (companies)</span>
            <span className="text-[10px] text-muted">Top-down (consensus)</span>
          </div>
        </div>

        {/* Metrics row */}
        <div className="grid grid-cols-3 gap-3 mb-3">
          <div className="text-center">
            <div
              className="font-mono text-lg font-semibold"
              style={{ color }}
            >
              {pct}%
            </div>
            <div className="text-[10px] text-muted">Coverage Ratio</div>
          </div>
          <div className="text-center">
            <div className="font-mono text-lg font-semibold text-accent">
              ${latest.gap_usd_billions.toFixed(1)}B
            </div>
            <div className="text-[10px] text-muted">Unexplained Gap</div>
          </div>
          <div className="text-center">
            <div className="font-mono text-lg font-semibold text-text">
              {latest.n_companies}
            </div>
            <div className="text-[10px] text-muted">Companies</div>
          </div>
        </div>

        {/* Top contributors */}
        {latest.top_contributors.length > 0 && (
          <div className="border-t border-border pt-2">
            <span className="text-[10px] text-muted">Explained by: </span>
            <span className="text-xs text-text">
              {latest.top_contributors.join(", ")}
            </span>
          </div>
        )}

        {/* Gap narrative */}
        {latest.gap_usd_billions > 0 && (
          <div className="mt-2 text-xs text-muted">
            <span className="font-mono text-accent">${latest.gap_usd_billions.toFixed(1)}B</span>{" "}
            unexplained market opportunity — likely comprised of private companies, smaller public
            players, and emerging AI startups not yet in EDGAR filings.
          </div>
        )}
      </div>
    </div>
  );
}
