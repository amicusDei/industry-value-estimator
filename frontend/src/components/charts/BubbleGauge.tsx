"use client";

import { useEffect, useState } from "react";

interface PreviousData {
  composite_score: number;
  year: number;
  half: number;
}

interface Props {
  score: number;
  classification: string;
  previousData?: PreviousData;
}

function scoreColor(score: number): string {
  if (score < 30) return "#22c55e";
  if (score < 50) return "#eab308";
  if (score < 70) return "#f97316";
  return "#ef4444";
}

export default function BubbleGauge({ score, classification, previousData }: Props) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const duration = 1200;
    const startTime = performance.now();

    function animate(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = eased * score;
      setAnimatedScore(current);
      if (progress < 1) requestAnimationFrame(animate);
    }

    requestAnimationFrame(animate);
  }, [score]);

  // SVG gauge dimensions
  const cx = 200;
  const cy = 180;
  const r = 140;
  const strokeWidth = 28;

  // Half-circle: from 180deg (left) to 0deg (right) = PI to 0
  // In SVG arc terms, we go from left to right along the top half
  function polarToCart(angleDeg: number, radius: number) {
    const rad = (angleDeg * Math.PI) / 180;
    return {
      x: cx + radius * Math.cos(rad),
      y: cy - radius * Math.sin(rad),
    };
  }

  // Zone arcs: angles go from 180 (left, score=0) to 0 (right, score=100)
  const zones = [
    { min: 0, max: 30, color: "#22c55e" },
    { min: 30, max: 50, color: "#eab308" },
    { min: 50, max: 70, color: "#f97316" },
    { min: 70, max: 100, color: "#ef4444" },
  ];

  function scoreToAngle(s: number): number {
    return 180 - (s / 100) * 180;
  }

  function arcPath(startScore: number, endScore: number, radius: number): string {
    const startAngle = scoreToAngle(startScore);
    const endAngle = scoreToAngle(endScore);
    const start = polarToCart(startAngle, radius);
    const end = polarToCart(endAngle, radius);
    const largeArc = Math.abs(startAngle - endAngle) > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
  }

  // Needle — tip ends at r - 4 = 136, center of the 28px arc
  const needleAngle = scoreToAngle(animatedScore);
  const needleTip = polarToCart(needleAngle, r - 4);

  // Needle as a line from center to tip, 3px wide, rounded
  const needleBaseOffset = 5;
  const baseX1 = cx + needleBaseOffset * Math.cos(((needleAngle + 90) * Math.PI) / 180);
  const baseY1 = cy - needleBaseOffset * Math.sin(((needleAngle + 90) * Math.PI) / 180);
  const baseX2 = cx + needleBaseOffset * Math.cos(((needleAngle - 90) * Math.PI) / 180);
  const baseY2 = cy - needleBaseOffset * Math.sin(((needleAngle - 90) * Math.PI) / 180);

  // Tick marks
  const ticks = [0, 25, 50, 75, 100];

  // YoY trend
  let trendText = "";
  let trendColor = "#64748b";
  if (previousData) {
    const diff = score - previousData.composite_score;
    const sign = diff >= 0 ? "+" : "";
    const arrow = diff >= 0 ? "\u25B2" : "\u25BC";
    trendText = `${arrow} ${sign}${diff.toFixed(1)} vs H${previousData.half} ${previousData.year}`;
    // Rising = more risk = red, falling = green
    trendColor = diff >= 0 ? "#ef4444" : "#22c55e";
  }

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 400 270" className="w-full max-w-md">
        {/* Background track */}
        <path
          d={arcPath(0, 100, r)}
          fill="none"
          stroke="#1e293b"
          strokeWidth={strokeWidth + 4}
          strokeLinecap="round"
        />

        {/* Color zones */}
        {zones.map((zone) => (
          <path
            key={zone.min}
            d={arcPath(zone.min, zone.max, r)}
            fill="none"
            stroke={zone.color}
            strokeWidth={strokeWidth}
            strokeLinecap="butt"
            opacity={0.7}
          />
        ))}

        {/* Tick marks and labels */}
        {ticks.map((t) => {
          const angle = scoreToAngle(t);
          const outer = polarToCart(angle, r + strokeWidth / 2 + 4);
          const inner = polarToCart(angle, r + strokeWidth / 2 - 2);
          const labelPos = polarToCart(angle, r + strokeWidth / 2 + 18);
          return (
            <g key={t}>
              <line
                x1={inner.x}
                y1={inner.y}
                x2={outer.x}
                y2={outer.y}
                stroke="#64748b"
                strokeWidth={1.5}
              />
              <text
                x={labelPos.x}
                y={labelPos.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#64748b"
                fontSize="11"
                fontFamily="JetBrains Mono, monospace"
              >
                {t}
              </text>
            </g>
          );
        })}

        {/* Needle — 3px, rounded tip, slate-700 */}
        <line
          x1={cx}
          y1={cy}
          x2={needleTip.x}
          y2={needleTip.y}
          stroke="#334155"
          strokeWidth={3}
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={7} fill="#334155" />
        <circle cx={cx} cy={cy} r={3} fill="#0a0a0f" />

        {/* Score number — below the needle hub */}
        <text
          x={cx}
          y={cy + 30}
          textAnchor="middle"
          fill={scoreColor(score)}
          fontSize="48"
          fontWeight="700"
          fontFamily="JetBrains Mono, monospace"
        >
          {Math.round(animatedScore)}
        </text>

        {/* YoY trend text */}
        {trendText && (
          <text
            x={cx}
            y={cy + 52}
            textAnchor="middle"
            fill={trendColor}
            fontSize="12"
            fontWeight="500"
            fontFamily="JetBrains Mono, monospace"
          >
            {trendText}
          </text>
        )}

        {/* Label */}
        <text
          x={cx}
          y={cy + 72}
          textAnchor="middle"
          fill="#e2e8f0"
          fontSize="13"
          fontWeight="600"
          fontFamily="Inter, system-ui, sans-serif"
        >
          AI BUBBLE INDEX
        </text>
      </svg>

      {/* Classification badge */}
      <div
        className="mt-2 px-4 py-1.5 rounded-full text-sm font-semibold tracking-wide uppercase"
        style={{
          backgroundColor: `${scoreColor(score)}20`,
          color: scoreColor(score),
          border: `1px solid ${scoreColor(score)}40`,
        }}
      >
        {classification}
      </div>
    </div>
  );
}
