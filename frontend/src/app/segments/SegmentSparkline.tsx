"use client";

interface SparkPoint {
  year: number;
  value: number;
  isForecast: boolean;
}

interface Props {
  data: SparkPoint[];
}

/**
 * Minimal SVG sparkline — no axes, no labels, just the line.
 * Historical in slate (#64748b), forecast in orange (#f97316).
 * 80x40px as specified.
 */
export default function SegmentSparkline({ data }: Props) {
  if (data.length < 2) return null;

  const W = 80;
  const H = 40;
  const PAD = 2;

  const values = data.map((d) => d.value);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = maxV - minV || 1;

  // Map data to SVG coordinates
  const points = data.map((d, i) => ({
    x: PAD + (i / (data.length - 1)) * (W - 2 * PAD),
    y: H - PAD - ((d.value - minV) / range) * (H - 2 * PAD),
    isForecast: d.isForecast,
  }));

  // Build separate paths for historical and forecast
  // Find the transition point
  const lastHistIdx = points.findLastIndex((p) => !p.isForecast);

  // Historical path
  const histPoints = points.filter((_, i) => i <= lastHistIdx);
  const histPath =
    histPoints.length > 1
      ? histPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ")
      : "";

  // Forecast path — starts from last historical point for continuity
  const forecastStart = lastHistIdx >= 0 ? lastHistIdx : 0;
  const fcPoints = points.filter(
    (_, i) => i >= forecastStart && (i > lastHistIdx || i === forecastStart)
  );
  // Only include if there are actual forecast points
  const hasForecast = points.some((p) => p.isForecast);
  const fcPath =
    hasForecast && fcPoints.length > 1
      ? fcPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ")
      : "";

  return (
    <svg
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      className="block"
      aria-hidden="true"
    >
      {histPath && (
        <path
          d={histPath}
          fill="none"
          stroke="#64748b"
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      {fcPath && (
        <path
          d={fcPath}
          fill="none"
          stroke="#f97316"
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}
