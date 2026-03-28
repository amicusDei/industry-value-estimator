/**
 * Format a USD billions value for display.
 * e.g., 142.3 → "$142.3B", 0.31 → "$310M"
 */
export function formatUsdB(value: number | null | undefined): string {
  if (value == null) return "N/A";
  if (Math.abs(value) < 1) {
    return `$${(value * 1000).toFixed(0)}M`;
  }
  return `$${value.toFixed(1)}B`;
}

/**
 * Format a percentage with +/- sign and color class.
 * e.g., 24.5 → { text: "+24.5%", colorClass: "text-positive" }
 */
export function formatPct(
  value: number | null | undefined
): { text: string; colorClass: string } {
  if (value == null) return { text: "N/A", colorClass: "text-muted" };
  const sign = value >= 0 ? "+" : "";
  const colorClass = value >= 0 ? "text-positive" : "text-negative";
  return { text: `${sign}${value.toFixed(1)}%`, colorClass };
}

/**
 * Format a MAPE value with traffic-light color.
 */
export function formatMape(mape: number): { text: string; colorClass: string } {
  const text = `${mape.toFixed(1)}%`;
  if (mape < 15) return { text, colorClass: "text-positive" };
  if (mape < 30) return { text, colorClass: "text-accent" };
  return { text, colorClass: "text-negative" };
}
