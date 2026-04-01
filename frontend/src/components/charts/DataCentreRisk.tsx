"use client";

import { useState } from "react";
import type { DCRiskResponse } from "@/lib/api";

interface Props {
  data: DCRiskResponse;
}

/* ─── Colour constants (Bloomberg-style) ─── */
const BONDS = "#3b82f6";
const PRIVATE_CREDIT = "#f97316";
const OFF_BS = "#ef4444";
const GRID = "#ffffff08";
const LABEL = "#64748b";
const TEXT = "#e2e8f0";
const MUTED = "#94a3b8";

/* ─── Build Rate Panel ─── */
function BuildRatePanel({
  data,
}: {
  data: DCRiskResponse["build_rate"];
}) {
  if (!data.length) return null;

  // Aggregate to annual: sum new_capacity_mw per year, take last half's yoy_growth_pct
  const byYear = new Map<
    number,
    { mw: number; yoy: number; cumulative: number }
  >();
  for (const d of data) {
    const prev = byYear.get(d.year);
    if (prev) {
      byYear.set(d.year, {
        mw: prev.mw + d.new_capacity_mw,
        yoy: d.yoy_growth_pct,
        cumulative: d.cumulative_mw,
      });
    } else {
      byYear.set(d.year, {
        mw: d.new_capacity_mw,
        yoy: d.yoy_growth_pct,
        cumulative: d.cumulative_mw,
      });
    }
  }

  const years = Array.from(byYear.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([year, v]) => ({ year, ...v }));

  const maxMW = Math.max(...years.map((y) => y.mw));
  const maxYoY = Math.max(...years.map((y) => y.yoy));

  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex flex-col">
      <h4 className="text-sm font-semibold text-text mb-1">Build Rate</h4>
      <p className="text-[10px] text-muted mb-3">
        MW/year capacity additions with YoY growth
      </p>
      <div className="flex-1 flex items-end gap-1.5">
        {years.map((y) => {
          const barH = Math.max(4, (y.mw / maxMW) * 100);
          return (
            <div
              key={y.year}
              className="flex-1 flex flex-col items-center gap-1"
            >
              {/* YoY label */}
              <span className="text-[9px] font-mono text-accent">
                +{y.yoy}%
              </span>
              {/* Capacity bar (area-like stacked look via gradient) */}
              <div className="w-full flex flex-col items-center">
                <div
                  className="w-full rounded-t-sm"
                  style={{
                    height: `${barH}px`,
                    background: `linear-gradient(to top, #f9731640, #f97316)`,
                    minHeight: "4px",
                  }}
                />
              </div>
              {/* MW label */}
              <span className="text-[8px] font-mono text-muted leading-none">
                {y.mw >= 10000
                  ? `${(y.mw / 1000).toFixed(0)}k`
                  : `${(y.mw / 1000).toFixed(1)}k`}
              </span>
              {/* Year */}
              <span className="text-[8px] font-mono text-muted leading-none">
                {String(y.year).slice(-2)}
              </span>
            </div>
          );
        })}
      </div>
      <p className="text-[9px] text-muted mt-2 text-right">MW/year</p>
    </div>
  );
}

/* ─── Credit Stack Panel ─── */
function CreditStackPanel({
  data,
}: {
  data: DCRiskResponse["credit_stack"];
}) {
  if (!data.length) return null;

  // Aggregate to annual (use H2 values if available, otherwise H1, since credit is cumulative)
  const byYear = new Map<
    number,
    { bonds: number; private_credit: number; off_bs: number; total: number }
  >();
  for (const d of data) {
    byYear.set(d.year, {
      bonds: d.bonds_usd_b,
      private_credit: d.private_credit_usd_b,
      off_bs: d.off_balance_sheet_usd_b,
      total: d.total_usd_b,
    });
  }

  const years = Array.from(byYear.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([year, v]) => ({ year, ...v }));

  const maxTotal = Math.max(...years.map((y) => y.total));

  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex flex-col">
      <h4 className="text-sm font-semibold text-text mb-1">Credit Stack</h4>
      <p className="text-[10px] text-muted mb-3">
        AI-related credit exposure by type ($B)
      </p>
      <div className="flex-1 flex items-end gap-1.5">
        {years.map((y) => {
          const totalH = Math.max(8, (y.total / maxTotal) * 100);
          const bondsH = (y.bonds / y.total) * totalH;
          const pcH = (y.private_credit / y.total) * totalH;
          const obsH = (y.off_bs / y.total) * totalH;
          return (
            <div
              key={y.year}
              className="flex-1 flex flex-col items-center gap-1"
            >
              {/* Total label */}
              <span className="text-[9px] font-mono text-text">
                ${y.total}
              </span>
              {/* Stacked bar */}
              <div
                className="w-full flex flex-col-reverse rounded-t-sm overflow-hidden"
                style={{ height: `${totalH}px` }}
              >
                <div
                  style={{
                    height: `${bondsH}px`,
                    backgroundColor: BONDS,
                  }}
                />
                <div
                  style={{
                    height: `${pcH}px`,
                    backgroundColor: PRIVATE_CREDIT,
                  }}
                />
                <div
                  style={{
                    height: `${obsH}px`,
                    backgroundColor: OFF_BS,
                  }}
                />
              </div>
              {/* Year */}
              <span className="text-[8px] font-mono text-muted leading-none">
                {String(y.year).slice(-2)}
              </span>
            </div>
          );
        })}
      </div>
      {/* Legend */}
      <div className="flex gap-3 mt-3 flex-wrap">
        <span className="flex items-center gap-1 text-[9px] text-muted">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: BONDS }}
          />
          Bonds
        </span>
        <span className="flex items-center gap-1 text-[9px] text-muted">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: PRIVATE_CREDIT }}
          />
          Private Credit
        </span>
        <span className="flex items-center gap-1 text-[9px] text-muted">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: OFF_BS }}
          />
          Off-Balance Sheet
        </span>
      </div>
    </div>
  );
}

/* ─── Refinancing Wall Panel ─── */
function RefinancingWallPanel({
  data,
}: {
  data: DCRiskResponse["refinancing_calendar"];
}) {
  if (!data.length) return null;

  const maxDebt = Math.max(
    ...data.map(
      (d) => d.maturing_bonds_usd_b + d.maturing_private_credit_usd_b
    )
  );

  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex flex-col">
      <h4 className="text-sm font-semibold text-text mb-1">
        Refinancing Wall
      </h4>
      <p className="text-[10px] text-muted mb-3">
        Maturing AI-linked debt per year ($B, est.)
      </p>
      <div className="flex-1 flex items-end gap-2">
        {data.map((d) => {
          const total =
            d.maturing_bonds_usd_b + d.maturing_private_credit_usd_b;
          const barH = Math.max(8, (total / maxDebt) * 100);
          const bondsH = (d.maturing_bonds_usd_b / total) * barH;
          const pcH = (d.maturing_private_credit_usd_b / total) * barH;
          return (
            <div
              key={d.year}
              className="flex-1 flex flex-col items-center gap-1"
            >
              {/* Total label */}
              <span className="text-[9px] font-mono text-text">
                ${total}B
              </span>
              <span className="text-[8px] text-muted italic">(est.)</span>
              {/* Stacked bar */}
              <div
                className="w-full flex flex-col-reverse rounded-t-sm overflow-hidden"
                style={{ height: `${barH}px` }}
              >
                <div
                  style={{
                    height: `${bondsH}px`,
                    backgroundColor: BONDS,
                    opacity: 0.8,
                  }}
                />
                <div
                  style={{
                    height: `${pcH}px`,
                    backgroundColor: PRIVATE_CREDIT,
                    opacity: 0.8,
                  }}
                />
              </div>
              {/* Year */}
              <span className="text-[8px] font-mono text-muted leading-none">
                {d.year}
              </span>
            </div>
          );
        })}
      </div>
      {/* Legend */}
      <div className="flex gap-3 mt-3 flex-wrap">
        <span className="flex items-center gap-1 text-[9px] text-muted">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: BONDS, opacity: 0.8 }}
          />
          Bonds
        </span>
        <span className="flex items-center gap-1 text-[9px] text-muted">
          <span
            className="inline-block w-2.5 h-2.5 rounded-sm"
            style={{ backgroundColor: PRIVATE_CREDIT, opacity: 0.8 }}
          />
          Private Credit
        </span>
      </div>
    </div>
  );
}

/* ─── Asset-Life Mismatch Panel ─── */
function AssetLifeMismatchPanel({
  data,
}: {
  data: DCRiskResponse["asset_life_mismatch"];
}) {
  const dcYears = data.dc_assumed_life_years;
  const gpuMonths = data.gpu_upgrade_cycle_months;
  const mismatch = data.mismatch_factor;

  // Normalize to the same base for visual comparison
  // DC life = 20 years = 240 months. GPU = 18 months. Show as relative bars.
  const dcMonths = dcYears * 12;
  const maxMonths = dcMonths;

  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex flex-col">
      <h4 className="text-sm font-semibold text-text mb-1">
        Asset-Life Mismatch
      </h4>
      <p className="text-[10px] text-muted mb-4">
        Infrastructure depreciation vs GPU upgrade cycle
      </p>
      <div className="flex-1 flex flex-col justify-center gap-5">
        {/* Data Centre bar */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-text font-medium">
              Data Centre Assumed Life
            </span>
            <span className="font-mono text-sm font-semibold text-text">
              {dcYears} years
            </span>
          </div>
          <div className="h-6 bg-[#1e293b] rounded overflow-hidden">
            <div
              className="h-full rounded"
              style={{
                width: "100%",
                backgroundColor: BONDS,
                opacity: 0.7,
              }}
            />
          </div>
        </div>

        {/* GPU Cycle bar */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-text font-medium">
              GPU Upgrade Cycle
            </span>
            <span className="font-mono text-sm font-semibold text-accent">
              {gpuMonths} months
            </span>
          </div>
          <div className="h-6 bg-[#1e293b] rounded overflow-hidden">
            <div
              className="h-full rounded"
              style={{
                width: `${(gpuMonths / maxMonths) * 100}%`,
                backgroundColor: OFF_BS,
                opacity: 0.85,
              }}
            />
          </div>
        </div>

        {/* Mismatch callout */}
        <div className="flex items-center justify-center mt-2">
          <div className="bg-[#ef444418] border border-[#ef444440] rounded-lg px-5 py-3 text-center">
            <span className="font-mono text-2xl font-bold text-[#ef4444]">
              {mismatch}x
            </span>
            <p className="text-[10px] text-muted mt-1">mismatch factor</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Main DataCentreRisk (expandable wrapper) ─── */
export default function DataCentreRisk({ data }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-surface border border-border rounded-lg overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-[#1e293b30] transition-colors text-left"
      >
        <div>
          <h3 className="text-sm font-semibold text-text">
            Data Centre Risk Deep-Dive
          </h3>
          <p className="text-[10px] text-muted mt-0.5">
            Build rate, credit stack, refinancing wall, asset-life mismatch
          </p>
        </div>
        <span className="text-muted text-lg transition-transform duration-200"
          style={{ transform: expanded ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          &#9656;
        </span>
      </button>

      {/* Expandable content */}
      {expanded && (
        <div className="px-5 pb-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <BuildRatePanel data={data.build_rate} />
            <CreditStackPanel data={data.credit_stack} />
            <RefinancingWallPanel data={data.refinancing_calendar} />
            <AssetLifeMismatchPanel data={data.asset_life_mismatch} />
          </div>
        </div>
      )}
    </div>
  );
}
