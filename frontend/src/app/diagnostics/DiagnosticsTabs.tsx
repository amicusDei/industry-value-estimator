"use client";

import { useState } from "react";
import type {
  MapeMatrixEntry,
  CiCoverageEntry,
  RegimeComparisonEntry,
  DataSourceEntry,
} from "@/lib/api";

const TABS = [
  {
    id: "performance",
    label: "Model Performance",
    subtitle:
      "MAPE heatmap across segments and years from Prophet leave-one-out cross-validation.",
  },
  {
    id: "ci",
    label: "CI Coverage",
    subtitle:
      "Actual vs target confidence interval coverage at 80% and 95% levels per segment.",
  },
  {
    id: "regime",
    label: "Regime Analysis",
    subtitle:
      "Pre-GenAI (2017-2021) vs post-GenAI (2022+) forecast accuracy comparison.",
  },
  {
    id: "sources",
    label: "Data Sources",
    subtitle:
      "Analyst firms contributing to market anchor estimates with segment and year coverage.",
  },
] as const;

type TabId = (typeof TABS)[number]["id"];

const SEGMENT_LABELS: Record<string, string> = {
  ai_hardware: "Hardware",
  ai_infrastructure: "Infrastructure",
  ai_software: "Software",
  ai_adoption: "Adoption",
};

function mapeColor(mape: number): string {
  if (mape < 15) return "bg-emerald-500/80 text-white";
  if (mape < 30) return "bg-yellow-500/80 text-black";
  if (mape < 50) return "bg-orange-500/80 text-white";
  return "bg-red-500/80 text-white";
}

function mapeColorText(mape: number): string {
  if (mape < 15) return "text-emerald-400";
  if (mape < 30) return "text-yellow-400";
  if (mape < 50) return "text-orange-400";
  return "text-red-400";
}

interface Props {
  mapeMatrix: MapeMatrixEntry[];
  ciCoverage: CiCoverageEntry[];
  regimeComparison: RegimeComparisonEntry[];
  dataSources: DataSourceEntry[];
  summary: Record<string, unknown>;
}

export default function DiagnosticsTabs({
  mapeMatrix,
  ciCoverage,
  regimeComparison,
  dataSources,
}: Props) {
  const [activeTab, setActiveTab] = useState<TabId>("performance");
  const currentTab = TABS.find((t) => t.id === activeTab)!;

  // Extract years from mape matrix
  const years =
    mapeMatrix.length > 0
      ? Object.keys(mapeMatrix[0])
          .filter((k) => k !== "segment")
          .sort()
      : [];

  return (
    <div>
      {/* Tab Pills */}
      <div className="flex flex-col md:flex-row flex-wrap gap-2 mb-6">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-150 ${
                isActive
                  ? "bg-accent text-[#0a0a0f]"
                  : "bg-transparent border border-[#ffffff20] text-muted hover:border-accent/50 hover:text-text"
              }`}
            >
              <span className="font-mono text-xs tracking-wide uppercase">
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Subtitle */}
      <p className="text-muted text-sm mb-6">{currentTab.subtitle}</p>

      {/* Tab Content */}
      {activeTab === "performance" && (
        <MapeHeatmap matrix={mapeMatrix} years={years} />
      )}
      {activeTab === "ci" && <CiCoverageChart coverage={ciCoverage} />}
      {activeTab === "regime" && (
        <RegimeChart comparison={regimeComparison} />
      )}
      {activeTab === "sources" && <DataSourcesTable sources={dataSources} />}
    </div>
  );
}

/* ---------- Tab 1: MAPE Heatmap ---------- */

function MapeHeatmap({
  matrix,
  years,
}: {
  matrix: MapeMatrixEntry[];
  years: string[];
}) {
  if (matrix.length === 0) {
    return <div className="text-muted">No MAPE data available.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[600px]">
        {/* Header row */}
        <div
          className="grid gap-1 mb-1"
          style={{
            gridTemplateColumns: `140px repeat(${years.length}, 1fr)`,
          }}
        >
          <div className="text-xs text-muted uppercase px-2 py-2">Segment</div>
          {years.map((y) => (
            <div key={y} className="text-xs text-muted text-center py-2">
              {y}
            </div>
          ))}
        </div>
        {/* Data rows */}
        {matrix.map((row) => (
          <div
            key={row.segment}
            className="grid gap-1 mb-1"
            style={{
              gridTemplateColumns: `140px repeat(${years.length}, 1fr)`,
            }}
          >
            <div className="text-sm px-2 py-3 flex items-center">
              {SEGMENT_LABELS[row.segment] || row.segment}
            </div>
            {years.map((y) => {
              const val = row[y];
              if (val == null || typeof val !== "number") {
                return (
                  <div
                    key={y}
                    className="rounded bg-[#ffffff08] text-center py-3 text-xs text-muted"
                  >
                    --
                  </div>
                );
              }
              return (
                <div
                  key={y}
                  className={`rounded text-center py-3 text-sm font-mono font-semibold ${mapeColor(val)}`}
                >
                  {val.toFixed(1)}%
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-4 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-emerald-500/80" /> &lt;15%
          Excellent
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-yellow-500/80" /> 15-30% Good
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-orange-500/80" /> 30-50% Moderate
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-red-500/80" /> &gt;50% Poor
        </span>
      </div>
    </div>
  );
}

/* ---------- Tab 2: CI Coverage ---------- */

function CiCoverageChart({ coverage }: { coverage: CiCoverageEntry[] }) {
  if (coverage.length === 0) {
    return <div className="text-muted">No CI coverage data available.</div>;
  }

  return (
    <div className="space-y-6">
      {coverage.map((c) => {
        const ci80Pct = Math.min(c.ci80_actual, 1) * 100;
        const ci95Pct = Math.min(c.ci95_actual, 1) * 100;
        const ci80TargetPct = c.ci80_target * 100;
        const ci95TargetPct = c.ci95_target * 100;

        return (
          <div
            key={c.segment}
            className="bg-surface border border-border rounded-lg p-4"
          >
            <p className="text-sm font-semibold mb-3">
              {SEGMENT_LABELS[c.segment] || c.segment}
            </p>

            {/* CI80 */}
            <div className="mb-3">
              <div className="flex justify-between text-xs text-muted mb-1">
                <span>CI80 Coverage</span>
                <span>
                  <span
                    className={
                      c.ci80_actual >= c.ci80_target
                        ? "text-emerald-400"
                        : "text-red-400"
                    }
                  >
                    {(c.ci80_actual * 100).toFixed(0)}%
                  </span>
                  {" / "}
                  {(c.ci80_target * 100).toFixed(0)}% target
                </span>
              </div>
              <div className="relative h-6 bg-[#ffffff08] rounded overflow-hidden">
                <div
                  className={`absolute inset-y-0 left-0 rounded ${
                    c.ci80_actual >= c.ci80_target
                      ? "bg-emerald-500/70"
                      : "bg-red-500/70"
                  }`}
                  style={{ width: `${ci80Pct}%` }}
                />
                <div
                  className="absolute inset-y-0 w-0.5 bg-white/60"
                  style={{ left: `${ci80TargetPct}%` }}
                />
              </div>
            </div>

            {/* CI95 */}
            <div>
              <div className="flex justify-between text-xs text-muted mb-1">
                <span>CI95 Coverage</span>
                <span>
                  <span
                    className={
                      c.ci95_actual >= c.ci95_target
                        ? "text-emerald-400"
                        : "text-red-400"
                    }
                  >
                    {(c.ci95_actual * 100).toFixed(0)}%
                  </span>
                  {" / "}
                  {(c.ci95_target * 100).toFixed(0)}% target
                </span>
              </div>
              <div className="relative h-6 bg-[#ffffff08] rounded overflow-hidden">
                <div
                  className={`absolute inset-y-0 left-0 rounded ${
                    c.ci95_actual >= c.ci95_target
                      ? "bg-emerald-500/70"
                      : "bg-red-500/70"
                  }`}
                  style={{ width: `${ci95Pct}%` }}
                />
                <div
                  className="absolute inset-y-0 w-0.5 bg-white/60"
                  style={{ left: `${ci95TargetPct}%` }}
                />
              </div>
            </div>
          </div>
        );
      })}

      <div className="text-xs text-muted flex items-center gap-2 mt-2">
        <span className="w-4 h-0.5 bg-white/60 inline-block" /> Target
        threshold
      </div>
    </div>
  );
}

/* ---------- Tab 3: Regime Analysis ---------- */

function RegimeChart({
  comparison,
}: {
  comparison: RegimeComparisonEntry[];
}) {
  if (comparison.length === 0) {
    return <div className="text-muted">No regime data available.</div>;
  }

  // Find max for scaling
  const allVals = comparison.flatMap((c) =>
    [c.pre_genai_mape, c.post_genai_mape].filter(
      (v): v is number => v != null
    )
  );
  const maxMape = Math.max(...allVals, 10);

  return (
    <div className="space-y-4">
      {comparison.map((c) => {
        const preWidth =
          c.pre_genai_mape != null ? (c.pre_genai_mape / maxMape) * 100 : 0;
        const postWidth =
          c.post_genai_mape != null
            ? (c.post_genai_mape / maxMape) * 100
            : 0;

        return (
          <div
            key={c.segment}
            className="bg-surface border border-border rounded-lg p-4"
          >
            <p className="text-sm font-semibold mb-3">
              {SEGMENT_LABELS[c.segment] || c.segment}
            </p>

            {/* Pre-GenAI bar */}
            <div className="mb-2">
              <div className="flex justify-between text-xs text-muted mb-1">
                <span>Pre-GenAI (2017-2021)</span>
                <span
                  className={
                    c.pre_genai_mape != null
                      ? mapeColorText(c.pre_genai_mape)
                      : "text-muted"
                  }
                >
                  {c.pre_genai_mape != null
                    ? `${c.pre_genai_mape.toFixed(1)}%`
                    : "N/A"}
                </span>
              </div>
              <div className="h-5 bg-[#ffffff08] rounded overflow-hidden">
                <div
                  className="h-full rounded bg-slate-400/60"
                  style={{ width: `${preWidth}%` }}
                />
              </div>
            </div>

            {/* Post-GenAI bar */}
            <div>
              <div className="flex justify-between text-xs text-muted mb-1">
                <span>Post-GenAI (2022+)</span>
                <span
                  className={
                    c.post_genai_mape != null
                      ? mapeColorText(c.post_genai_mape)
                      : "text-muted"
                  }
                >
                  {c.post_genai_mape != null
                    ? `${c.post_genai_mape.toFixed(1)}%`
                    : "N/A"}
                </span>
              </div>
              <div className="h-5 bg-[#ffffff08] rounded overflow-hidden">
                <div
                  className="h-full rounded bg-accent/70"
                  style={{ width: `${postWidth}%` }}
                />
              </div>
            </div>

            {/* Delta indicator */}
            {c.pre_genai_mape != null && c.post_genai_mape != null && (
              <p className="text-xs mt-2">
                {c.post_genai_mape < c.pre_genai_mape ? (
                  <span className="text-emerald-400">
                    Improved by{" "}
                    {(c.pre_genai_mape - c.post_genai_mape).toFixed(1)}pp
                  </span>
                ) : (
                  <span className="text-red-400">
                    Worse by{" "}
                    {(c.post_genai_mape - c.pre_genai_mape).toFixed(1)}pp
                  </span>
                )}
              </p>
            )}
          </div>
        );
      })}

      <div className="flex flex-wrap gap-4 mt-2 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-slate-400/60" /> Pre-GenAI
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-accent/70" /> Post-GenAI
        </span>
      </div>
    </div>
  );
}

/* ---------- Tab 4: Data Sources ---------- */

function DataSourcesTable({ sources }: { sources: DataSourceEntry[] }) {
  if (sources.length === 0) {
    return (
      <div className="text-muted">No data source information available.</div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-muted text-xs uppercase border-b border-border">
            <th className="text-left py-2 px-3">Source</th>
            <th className="text-left py-2 px-3">Segments Covered</th>
            <th className="text-left py-2 px-3">Years</th>
            <th className="text-right py-2 px-3">Entries</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((s) => (
            <tr key={s.source_name} className="border-b border-border/50">
              <td className="py-2 px-3 font-medium">{s.source_name}</td>
              <td className="py-2 px-3">
                <div className="flex flex-wrap gap-1">
                  {s.segments_covered.map((seg) => (
                    <span
                      key={seg}
                      className="text-xs px-1.5 py-0.5 rounded bg-[#ffffff10] text-muted"
                    >
                      {SEGMENT_LABELS[seg] || seg}
                    </span>
                  ))}
                </div>
              </td>
              <td className="py-2 px-3 font-mono text-xs text-muted">
                {s.years_covered}
              </td>
              <td className="py-2 px-3 font-mono text-right">{s.n_entries}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="text-xs text-muted mt-4">
        {sources.length} analyst firms contributing to market anchor estimates.
        Entry count reflects segment-year combinations with data from each
        source.
      </p>
    </div>
  );
}
