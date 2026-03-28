import { getForecasts, getSegments } from "@/lib/api";
import { formatUsdB } from "@/lib/formatters";
import TimeseriesChart from "@/components/charts/TimeseriesChart";
import ExportButton from "@/components/ExportButton";

export const dynamic = "force-dynamic";

function toTimeStr(year: number, quarter: number): string {
  const month = { 1: "01", 2: "04", 3: "07", 4: "10" }[quarter] || "01";
  return `${year}-${month}-01`;
}

export default async function SegmentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let segmentName = id;
  let forecasts: Awaited<ReturnType<typeof getForecasts>>["data"] = [];

  try {
    const [segRes, fcRes] = await Promise.all([getSegments(), getForecasts(id)]);
    const seg = segRes.segments.find((s) => s.id === id);
    if (seg) segmentName = seg.display_name;
    forecasts = fcRes.data;
  } catch {
    return <div className="text-muted">API offline or segment not found.</div>;
  }

  const historical = forecasts
    .filter((r) => !r.is_forecast)
    .map((r) => ({ time: toTimeStr(r.year, r.quarter), value: r.point_estimate }));

  const forecast = forecasts
    .filter((r) => r.is_forecast)
    .map((r) => ({ time: toTimeStr(r.year, r.quarter), value: r.point_estimate }));

  const ci80 = forecasts
    .filter((r) => r.is_forecast)
    .map((r) => ({ time: toTimeStr(r.year, r.quarter), lower: r.ci80_lower, upper: r.ci80_upper }));

  const ci95 = forecasts
    .filter((r) => r.is_forecast)
    .map((r) => ({ time: toTimeStr(r.year, r.quarter), lower: r.ci95_lower, upper: r.ci95_upper }));

  const latestVal = historical.length > 0 ? historical[historical.length - 1].value : null;

  // Q4-only rows for the data table
  const q4Rows = forecasts.filter((r) => r.quarter === 4);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">{segmentName}</h1>
          {latestVal && (
            <p className="text-muted text-sm mt-1">
              Current: <span className="font-mono text-text">{formatUsdB(latestVal)}</span> (nominal USD)
            </p>
          )}
        </div>
        <ExportButton segment={id} label="Export Segment" />
      </div>

      <div className="bg-surface border border-border rounded-lg p-4 mb-8">
        <TimeseriesChart historical={historical} forecast={forecast} ci80={ci80} ci95={ci95} />
        <div className="flex gap-6 mt-3 text-xs text-muted">
          <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-[#64748b] inline-block" /> Historical</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-accent inline-block" /> Forecast</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-2 bg-[#f9731620] inline-block rounded-sm" /> 80% CI</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-2 bg-[#f973160d] inline-block rounded-sm" /> 95% CI</span>
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-3">Annual Data (Q4 Snapshots)</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-muted text-xs uppercase border-b border-border">
              <th className="text-left py-2 px-3">Year</th>
              <th className="text-right py-2 px-3">Point Est.</th>
              <th className="text-right py-2 px-3">CI80 Low</th>
              <th className="text-right py-2 px-3">CI80 High</th>
              <th className="text-right py-2 px-3">CI95 Low</th>
              <th className="text-right py-2 px-3">CI95 High</th>
              <th className="text-center py-2 px-3">Type</th>
            </tr>
          </thead>
          <tbody>
            {q4Rows.map((r) => (
              <tr key={r.year} className="border-b border-border/50">
                <td className="py-2 px-3 font-mono">{r.year}</td>
                <td className="py-2 px-3 font-mono text-right">{formatUsdB(r.point_estimate)}</td>
                <td className="py-2 px-3 font-mono text-right text-muted">{formatUsdB(r.ci80_lower)}</td>
                <td className="py-2 px-3 font-mono text-right text-muted">{formatUsdB(r.ci80_upper)}</td>
                <td className="py-2 px-3 font-mono text-right text-muted">{formatUsdB(r.ci95_lower)}</td>
                <td className="py-2 px-3 font-mono text-right text-muted">{formatUsdB(r.ci95_upper)}</td>
                <td className="py-2 px-3 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded ${r.is_forecast ? "bg-accent/20 text-accent" : "bg-[#22c55e20] text-positive"}`}>
                    {r.is_forecast ? "Forecast" : "Actual"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
