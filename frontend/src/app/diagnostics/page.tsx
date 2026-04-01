import { getDiagnostics } from "@/lib/api";
import DiagnosticsTabs from "./DiagnosticsTabs";

export const dynamic = "force-dynamic";

export default async function DiagnosticsPage() {
  let diag: Awaited<ReturnType<typeof getDiagnostics>> | null = null;
  try {
    diag = await getDiagnostics();
  } catch {
    /* API offline */
  }

  if (!diag)
    return (
      <div className="text-muted p-8">
        API offline. Start the backend on localhost:8000.
      </div>
    );

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Model Diagnostics</h1>
      <p className="text-muted text-sm mb-6">
        Leave-one-out cross-validation metrics, confidence interval coverage,
        and data provenance across all segments.
      </p>
      <DiagnosticsTabs
        mapeMatrix={diag.mape_matrix}
        ciCoverage={diag.ci_coverage}
        regimeComparison={diag.regime_comparison}
        dataSources={diag.data_sources}
        summary={diag.summary}
      />
    </div>
  );
}
