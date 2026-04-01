"use client";

import type { DispersionRow } from "@/lib/api";
import { formatUsdB } from "@/lib/formatters";

interface Props {
  data: DispersionRow[];
}

export default function DispersionChart({ data }: Props) {
  if (data.length === 0) {
    return <p className="text-muted text-sm">No dispersion data available.</p>;
  }

  const sorted = [...data].sort((a, b) => a.year - b.year);

  // Compute max value for Y-axis scaling
  const maxVal = Math.max(...sorted.map((d) => d.max_usd_billions));
  const yMax = maxVal * 1.15; // 15% headroom

  // Y-axis ticks (4-5 ticks)
  const tickCount = 5;
  const rawStep = yMax / tickCount;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const step = Math.ceil(rawStep / magnitude) * magnitude;
  const ticks: number[] = [];
  for (let v = 0; v <= yMax; v += step) {
    ticks.push(v);
  }

  const chartHeight = 280;
  const yAxisWidth = 60;
  const xAxisHeight = 28;
  const plotHeight = chartHeight - xAxisHeight;

  function yPos(val: number): number {
    return plotHeight - (val / yMax) * plotHeight;
  }

  return (
    <div className="w-full overflow-x-auto">
      <div
        className="relative"
        style={{ minWidth: sorted.length * 64 + yAxisWidth, height: chartHeight }}
      >
        {/* Y-axis labels */}
        {ticks.map((tick) => (
          <div
            key={tick}
            className="absolute text-[10px] font-mono text-muted text-right"
            style={{
              left: 0,
              top: yPos(tick) - 7,
              width: yAxisWidth - 8,
            }}
          >
            {formatUsdB(tick)}
          </div>
        ))}

        {/* Grid lines */}
        {ticks.map((tick) => (
          <div
            key={`grid-${tick}`}
            className="absolute border-t border-[#ffffff08]"
            style={{
              left: yAxisWidth,
              top: yPos(tick),
              right: 0,
            }}
          />
        ))}

        {/* Bars */}
        <div
          className="absolute flex items-end justify-around"
          style={{
            left: yAxisWidth,
            top: 0,
            right: 0,
            height: plotHeight,
          }}
        >
          {sorted.map((d) => {
            const minY = yPos(d.min_usd_billions);
            const maxY = yPos(d.max_usd_billions);
            const whiskerHeight = minY - maxY;

            // IQR bar: from median-iqr/2 to median+iqr/2
            // Since we have min/max and iqr, we approximate Q1 and Q3
            const median = (d.min_usd_billions + d.max_usd_billions) / 2;
            const q1 = Math.max(d.min_usd_billions, median - d.iqr_usd_billions / 2);
            const q3 = Math.min(d.max_usd_billions, median + d.iqr_usd_billions / 2);
            const iqrTopY = yPos(q3);
            const iqrBottomY = yPos(q1);
            const iqrHeight = iqrBottomY - iqrTopY;

            return (
              <div
                key={d.year}
                className="relative flex flex-col items-center"
                style={{ flex: "1 1 0", maxWidth: 64 }}
              >
                {/* n_sources label */}
                <div
                  className="absolute text-[9px] font-mono text-muted"
                  style={{ top: maxY - 18 }}
                >
                  n={d.n_sources}
                </div>

                {/* Whisker line (min to max) */}
                <div
                  className="absolute w-px bg-[#f9731660]"
                  style={{
                    top: maxY,
                    height: Math.max(whiskerHeight, 1),
                  }}
                />

                {/* Min whisker cap */}
                <div
                  className="absolute h-px w-3 bg-[#f9731660]"
                  style={{ top: minY, transform: "translateX(0)" }}
                />

                {/* Max whisker cap */}
                <div
                  className="absolute h-px w-3 bg-[#f9731660]"
                  style={{ top: maxY, transform: "translateX(0)" }}
                />

                {/* IQR bar (solid orange) */}
                {iqrHeight > 0 && (
                  <div
                    className="absolute rounded-sm bg-[#f97316] opacity-80"
                    style={{
                      top: iqrTopY,
                      height: Math.max(iqrHeight, 2),
                      width: 16,
                    }}
                  />
                )}

                {/* Median tick */}
                <div
                  className="absolute h-px w-5 bg-white/70"
                  style={{ top: yPos(median) }}
                />

                {/* Year label */}
                <div
                  className="absolute text-[10px] font-mono text-muted"
                  style={{ top: plotHeight + 6 }}
                >
                  {d.year}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-6 mt-3 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 bg-[#f97316] opacity-80 rounded-sm inline-block" /> IQR
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-px bg-[#f9731660] inline-block" /> Min/Max Range
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-px bg-white/70 inline-block" /> Median
        </span>
      </div>

      {/* Dispersion ratio trend */}
      {sorted.some((d) => d.dispersion_ratio > 0) && (
        <div className="mt-4">
          <p className="text-[10px] text-muted uppercase tracking-wider mb-2">
            Dispersion Ratio (IQR / Median)
          </p>
          <div className="flex items-end gap-1" style={{ height: 40 }}>
            {sorted.map((d) => {
              const maxRatio = Math.max(...sorted.map((r) => r.dispersion_ratio), 0.01);
              const barH = (d.dispersion_ratio / maxRatio) * 36;
              return (
                <div
                  key={d.year}
                  className="flex flex-col items-center"
                  style={{ flex: "1 1 0", maxWidth: 64 }}
                >
                  <div
                    className="w-3 rounded-t-sm"
                    style={{
                      height: Math.max(barH, 1),
                      backgroundColor:
                        d.dispersion_ratio > 0.5
                          ? "#ef4444"
                          : d.dispersion_ratio > 0.3
                            ? "#eab308"
                            : "#22c55e",
                      opacity: 0.7,
                    }}
                  />
                  <span className="text-[9px] font-mono text-muted mt-0.5">
                    {d.dispersion_ratio.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
