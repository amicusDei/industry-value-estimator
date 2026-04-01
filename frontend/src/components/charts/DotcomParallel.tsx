"use client";

import type { DotcomParallelPoint } from "@/lib/api";

interface Props {
  ai: DotcomParallelPoint[];
  dotcom: DotcomParallelPoint[];
}

export default function DotcomParallel({ ai, dotcom }: Props) {
  // Chart dimensions
  const w = 700;
  const h = 320;
  const pad = { top: 30, right: 30, bottom: 40, left: 50 };
  const chartW = w - pad.left - pad.right;
  const chartH = h - pad.top - pad.bottom;

  // Determine axis ranges
  const maxYears = Math.max(
    ...ai.map((d) => d.years_into_cycle),
    ...dotcom.map((d) => d.years_into_cycle)
  );
  const xMax = Math.ceil(maxYears) + 0.5;
  const yMax = 100;

  function scaleX(v: number): number {
    return pad.left + (v / xMax) * chartW;
  }
  function scaleY(v: number): number {
    return pad.top + chartH - (v / yMax) * chartH;
  }

  function polyline(points: DotcomParallelPoint[]): string {
    return points
      .map((p) => `${scaleX(p.years_into_cycle)},${scaleY(p.composite_score)}`)
      .join(" ");
  }

  // Y-axis ticks
  const yTicks = [0, 25, 50, 75, 100];
  // X-axis ticks
  const xTicks = Array.from({ length: Math.ceil(xMax) + 1 }, (_, i) => i);

  // Find the "today" point (latest AI data)
  const today = ai[ai.length - 1];
  // Find dotcom peak
  const dotcomPeak = dotcom.reduce((a, b) =>
    b.composite_score > a.composite_score ? b : a
  );

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-text mb-1">
        AI vs Dotcom Cycle Comparison
      </h3>
      <p className="text-xs text-muted mb-4">
        Composite bubble score mapped to years-into-cycle. AI cycle starts 2020;
        Dotcom starts 1996.
      </p>
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${w} ${h}`}
          className="w-full max-w-3xl"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Grid lines */}
          {yTicks.map((t) => (
            <line
              key={`yg-${t}`}
              x1={pad.left}
              y1={scaleY(t)}
              x2={w - pad.right}
              y2={scaleY(t)}
              stroke="#ffffff08"
              strokeWidth={1}
            />
          ))}

          {/* Classification zones (horizontal bands) */}
          <rect
            x={pad.left}
            y={scaleY(30)}
            width={chartW}
            height={scaleY(0) - scaleY(30)}
            fill="#22c55e"
            opacity={0.04}
          />
          <rect
            x={pad.left}
            y={scaleY(50)}
            width={chartW}
            height={scaleY(30) - scaleY(50)}
            fill="#eab308"
            opacity={0.04}
          />
          <rect
            x={pad.left}
            y={scaleY(70)}
            width={chartW}
            height={scaleY(50) - scaleY(70)}
            fill="#f97316"
            opacity={0.04}
          />
          <rect
            x={pad.left}
            y={scaleY(100)}
            width={chartW}
            height={scaleY(70) - scaleY(100)}
            fill="#ef4444"
            opacity={0.04}
          />

          {/* Y-axis labels */}
          {yTicks.map((t) => (
            <text
              key={`yl-${t}`}
              x={pad.left - 8}
              y={scaleY(t)}
              textAnchor="end"
              dominantBaseline="middle"
              fill="#64748b"
              fontSize="11"
              fontFamily="JetBrains Mono, monospace"
            >
              {t}
            </text>
          ))}

          {/* X-axis labels */}
          {xTicks.map((t) => (
            <text
              key={`xl-${t}`}
              x={scaleX(t)}
              y={h - pad.bottom + 20}
              textAnchor="middle"
              fill="#64748b"
              fontSize="11"
              fontFamily="JetBrains Mono, monospace"
            >
              {t}
            </text>
          ))}

          {/* X-axis title */}
          <text
            x={pad.left + chartW / 2}
            y={h - 4}
            textAnchor="middle"
            fill="#64748b"
            fontSize="11"
            fontFamily="Inter, system-ui, sans-serif"
          >
            Years into cycle
          </text>

          {/* Dotcom line (gray dashed) */}
          <polyline
            points={polyline(dotcom)}
            fill="none"
            stroke="#64748b"
            strokeWidth={2}
            strokeDasharray="6,4"
          />
          {/* Dotcom dots */}
          {dotcom.map((p, i) => (
            <circle
              key={`dc-${i}`}
              cx={scaleX(p.years_into_cycle)}
              cy={scaleY(p.composite_score)}
              r={3}
              fill="#64748b"
            />
          ))}

          {/* AI line (orange solid) */}
          <polyline
            points={polyline(ai)}
            fill="none"
            stroke="#f97316"
            strokeWidth={2.5}
          />
          {/* AI dots */}
          {ai.map((p, i) => (
            <circle
              key={`ai-${i}`}
              cx={scaleX(p.years_into_cycle)}
              cy={scaleY(p.composite_score)}
              r={3}
              fill="#f97316"
            />
          ))}

          {/* "Today" marker on AI line */}
          {today && (
            <>
              <circle
                cx={scaleX(today.years_into_cycle)}
                cy={scaleY(today.composite_score)}
                r={6}
                fill="none"
                stroke="#f97316"
                strokeWidth={2}
              />
              <text
                x={scaleX(today.years_into_cycle)}
                y={scaleY(today.composite_score) - 14}
                textAnchor="middle"
                fill="#f97316"
                fontSize="10"
                fontWeight="600"
                fontFamily="Inter, system-ui, sans-serif"
              >
                TODAY ({today.composite_score})
              </text>
            </>
          )}

          {/* Dotcom peak marker */}
          {dotcomPeak && (
            <>
              <circle
                cx={scaleX(dotcomPeak.years_into_cycle)}
                cy={scaleY(dotcomPeak.composite_score)}
                r={6}
                fill="none"
                stroke="#64748b"
                strokeWidth={2}
              />
              <text
                x={scaleX(dotcomPeak.years_into_cycle)}
                y={scaleY(dotcomPeak.composite_score) - 14}
                textAnchor="middle"
                fill="#64748b"
                fontSize="10"
                fontWeight="600"
                fontFamily="Inter, system-ui, sans-serif"
              >
                DOTCOM PEAK ({dotcomPeak.composite_score})
              </text>
            </>
          )}

          {/* Legend */}
          <line x1={w - pad.right - 180} y1={16} x2={w - pad.right - 155} y2={16} stroke="#f97316" strokeWidth={2.5} />
          <text x={w - pad.right - 150} y={16} dominantBaseline="middle" fill="#e2e8f0" fontSize="11" fontFamily="Inter, system-ui, sans-serif">
            AI Cycle (2020-)
          </text>
          <line x1={w - pad.right - 180} y1={32} x2={w - pad.right - 155} y2={32} stroke="#64748b" strokeWidth={2} strokeDasharray="6,4" />
          <text x={w - pad.right - 150} y={32} dominantBaseline="middle" fill="#e2e8f0" fontSize="11" fontFamily="Inter, system-ui, sans-serif">
            Dotcom (1996-2002)
          </text>
        </svg>
      </div>
    </div>
  );
}
