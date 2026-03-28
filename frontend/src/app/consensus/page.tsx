import { getConsensus } from "@/lib/api";

export const dynamic = "force-dynamic";

const SCOPE_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  close: { bg: "bg-[#22c55e20]", text: "text-positive", label: "Close" },
  partial: { bg: "bg-[#eab30820]", text: "text-[#eab308]", label: "Partial" },
  broad: { bg: "bg-[#ef444420]", text: "text-negative", label: "Broad" },
};

export default async function ConsensusPage() {
  let firms: Awaited<ReturnType<typeof getConsensus>>["firms"] = [];
  let ourMedian: number | null = null;

  try {
    const res = await getConsensus();
    firms = res.firms;
    ourMedian = res.our_median_2024;
  } catch {
    return <div className="text-muted">API offline.</div>;
  }

  // Find global min/max for scale
  let globalMin = Infinity;
  let globalMax = 0;
  for (const firm of firms) {
    for (const est of firm.estimates) {
      globalMin = Math.min(globalMin, est.value);
      globalMax = Math.max(globalMax, est.value);
    }
  }
  // Use log scale breakpoints for the bar since range is $24B to $7900B
  const maxLog = Math.log10(globalMax);
  const minLog = Math.log10(Math.max(globalMin, 1));
  const logScale = (v: number) => ((Math.log10(Math.max(v, 1)) - minLog) / (maxLog - minLog)) * 100;

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-2">Analyst Consensus & Scope Comparison</h1>
      <p className="text-muted text-sm mb-8">
        Published AI market estimates vary by 40x ($90B to $5,900B) because analysts measure different things.
        The bars show each firm{"'"}s published range. Our scope-normalized median adjusts all estimates to a common definition.
      </p>

      <div className="space-y-3">
        {firms.map((firm) => {
          const scope = SCOPE_COLORS[firm.scope_alignment] || SCOPE_COLORS.partial;
          const values = firm.estimates.map((e) => e.value);
          const min = Math.min(...values);
          const max = Math.max(...values);
          const leftPct = logScale(min);
          const rightPct = logScale(max);
          const widthPct = Math.max(rightPct - leftPct, 1);

          return (
            <div key={firm.firm} className="bg-surface border border-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-sm">{firm.firm}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${scope.bg} ${scope.text}`}>
                    {scope.label} ({firm.scope_coefficient}x)
                  </span>
                </div>
                <span className="font-mono text-sm text-muted">
                  ${min.toFixed(0)}B - ${max.toFixed(0)}B
                </span>
              </div>

              {/* Bar */}
              <div className="relative h-6 bg-[#ffffff06] rounded overflow-hidden">
                <div
                  className={`absolute h-full rounded ${scope.bg.replace("20]", "40]")}`}
                  style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                />
                {/* Our estimate marker */}
                {ourMedian && (
                  <div
                    className="absolute top-0 h-full w-0.5 bg-accent"
                    style={{ left: `${logScale(ourMedian)}%` }}
                    title={`Our estimate: $${ourMedian}B`}
                  />
                )}
              </div>

              {/* Scope details */}
              <div className="mt-2 text-xs text-muted">
                <span className="text-text/60">Includes:</span> {firm.scope_includes.slice(0, 120)}
                {firm.scope_includes.length > 120 && "..."}
              </div>
            </div>
          );
        })}
      </div>

      {ourMedian && (
        <div className="mt-6 flex items-center gap-2 text-sm text-muted">
          <span className="w-4 h-0.5 bg-accent inline-block" />
          Our scope-normalized estimate: <span className="font-mono text-text">${ourMedian}B</span> (2024, nominal)
        </div>
      )}
    </div>
  );
}
