import { getDiagnostics } from "@/lib/api";
import { formatMape } from "@/lib/formatters";

export const dynamic = "force-dynamic";

const PRIMARY_MODELS = ["prophet_loo", "ensemble_loo", "ensemble"];
const BENCHMARK_MODELS = ["naive", "random_walk", "consensus"];
const SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"];

export default async function DiagnosticsPage() {
  let diag: Awaited<ReturnType<typeof getDiagnostics>> | null = null;
  try {
    diag = await getDiagnostics();
  } catch { /* API offline */ }

  if (!diag) return <div className="text-muted">API offline.</div>;

  const dataQuality = (diag.summary as Record<string, unknown>)["_data_quality"] as Record<string, { real_points: number; interpolated_points: number; total_points: number; real_ratio: number }> | undefined;
  const modelCoverage = (diag.summary as Record<string, unknown>)["_model_coverage"] as Record<string, { models: string[]; has_ensemble: boolean; ensemble_note: string }> | undefined;

  // Filter summary to exclude internal keys
  const modelSummary = Object.entries(diag.summary)
    .filter(([k]) => !k.startsWith("_"))
    .map(([k, v]) => [k, v as { mean_mape: number; n_folds: number; per_segment?: Record<string, number> }] as const);

  // Separate primary vs benchmark
  const primaryModels = modelSummary.filter(([k]) => PRIMARY_MODELS.includes(k));
  const benchmarkModels = modelSummary.filter(([k]) => BENCHMARK_MODELS.includes(k));

  // Prophet LOO MAPE for comparison
  const prophetMape = (diag.summary["prophet_loo"] as { mean_mape: number })?.mean_mape;

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-2">Model Diagnostics</h1>
      <p className="text-muted text-sm mb-6">All metrics from leave-one-out cross-validation. No circular (training = test) comparisons.</p>

      {/* Primary model cards */}
      <h2 className="text-lg font-semibold mb-3">Primary Models</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {primaryModels.map(([model, stats]) => {
          const m = formatMape(stats.mean_mape);
          return (
            <div key={model} className="bg-surface border border-border rounded-lg p-4">
              <p className="text-muted text-xs uppercase mb-1">{model.replace(/_/g, " ")}</p>
              <p className={`font-mono text-2xl ${m.colorClass}`}>{m.text}</p>
              <p className="text-muted text-xs">{stats.n_folds} evaluations (LOO)</p>
            </div>
          );
        })}
      </div>

      {/* Benchmark comparison */}
      <h2 className="text-lg font-semibold mb-3">Benchmark Comparison</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {benchmarkModels.map(([model, stats]) => {
          const m = formatMape(stats.mean_mape);
          const betterThanProphet = prophetMape != null && stats.mean_mape > prophetMape;
          return (
            <div key={model} className="bg-surface border border-border rounded-lg p-4">
              <p className="text-muted text-xs uppercase mb-1">{model.replace(/_/g, " ")}</p>
              <p className={`font-mono text-xl ${m.colorClass}`}>{m.text}</p>
              <p className="text-muted text-xs">{stats.n_folds} evaluations</p>
              {betterThanProphet && (
                <p className="text-positive text-xs mt-1">Prophet LOO outperforms by {(stats.mean_mape - prophetMape!).toFixed(0)}pp</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Per-segment MAPE matrix */}
      <h2 className="text-lg font-semibold mb-3">MAPE by Model x Segment</h2>
      <div className="overflow-x-auto mb-8">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-muted text-xs uppercase border-b border-border">
              <th className="text-left py-2 px-3">Model</th>
              {SEGMENTS.map((s) => (
                <th key={s} className="text-right py-2 px-3">{s.replace("ai_", "")}</th>
              ))}
              <th className="text-right py-2 px-3">Overall</th>
            </tr>
          </thead>
          <tbody>
            {[...primaryModels, ...benchmarkModels].map(([model, stats]) => {
              const perSeg = (stats as { per_segment?: Record<string, number> }).per_segment || {};
              const overall = formatMape(stats.mean_mape);
              return (
                <tr key={model} className="border-b border-border/50">
                  <td className="py-2 px-3 text-muted">{model.replace(/_/g, " ")}</td>
                  {SEGMENTS.map((seg) => {
                    const val = perSeg[seg];
                    const fm = val != null ? formatMape(val) : { text: "--", colorClass: "text-muted" };
                    return (
                      <td key={seg} className={`py-2 px-3 font-mono text-right ${fm.colorClass}`}>{fm.text}</td>
                    );
                  })}
                  <td className={`py-2 px-3 font-mono text-right font-semibold ${overall.colorClass}`}>{overall.text}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Data Quality */}
      {dataQuality && (
        <>
          <h2 className="text-lg font-semibold mb-3">Training Data Composition</h2>
          <div className="overflow-x-auto mb-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted text-xs uppercase border-b border-border">
                  <th className="text-left py-2 px-3">Segment</th>
                  <th className="text-right py-2 px-3">Real Points</th>
                  <th className="text-right py-2 px-3">Interpolated</th>
                  <th className="text-right py-2 px-3">Total</th>
                  <th className="text-right py-2 px-3">Real %</th>
                </tr>
              </thead>
              <tbody>
                {SEGMENTS.map((seg) => {
                  const dq = dataQuality[seg];
                  if (!dq) return null;
                  const pct = Math.round(dq.real_ratio * 100);
                  const color = pct >= 50 ? "text-positive" : pct >= 25 ? "text-[#eab308]" : "text-negative";
                  return (
                    <tr key={seg} className="border-b border-border/50">
                      <td className="py-2 px-3">{seg.replace("ai_", "")}</td>
                      <td className="py-2 px-3 font-mono text-right text-positive">{dq.real_points}</td>
                      <td className="py-2 px-3 font-mono text-right text-muted">{dq.interpolated_points}</td>
                      <td className="py-2 px-3 font-mono text-right">{dq.total_points}</td>
                      <td className={`py-2 px-3 font-mono text-right ${color}`}>{pct}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="bg-[#eab30810] border border-[#eab30830] rounded-lg p-4 text-sm text-[#eab308] mb-8">
            <p className="font-semibold mb-1">Data Quality Caveat</p>
            <p className="text-[#eab308]/80">
              Models are trained on 75-80% interpolated data (quarterly values derived from annual analyst estimates).
              Only Q4 values with n_sources {">"} 0 represent genuine analyst data points.
              CI coverage targets and MAPE values should be interpreted with this context.
            </p>
          </div>
        </>
      )}

      {/* Model coverage */}
      {modelCoverage && (
        <>
          <h2 className="text-lg font-semibold mb-3">Model Coverage</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            {SEGMENTS.map((seg) => {
              const cov = modelCoverage[seg];
              if (!cov) return null;
              return (
                <div key={seg} className="bg-surface border border-border rounded-lg p-4">
                  <p className="font-semibold text-sm mb-2">{seg.replace("ai_", "AI ")}</p>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {cov.models.map((m) => (
                      <span key={m} className="text-xs px-2 py-0.5 rounded bg-[#ffffff10] text-muted">{m.replace(/_/g, " ")}</span>
                    ))}
                  </div>
                  {cov.has_ensemble ? (
                    <p className="text-xs text-positive">LOO ensemble validated</p>
                  ) : (
                    <p className="text-xs text-[#eab308]">{cov.ensemble_note}</p>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
