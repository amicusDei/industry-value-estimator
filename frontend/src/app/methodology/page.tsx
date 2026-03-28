export default function MethodologyPage() {
  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-6">Methodology</h1>

      <Section title="Market Boundary">
        <p>
          The AI market is defined as: AI software platforms, AI infrastructure (cloud compute
          dedicated to AI workloads, AI-specific hardware including GPUs, TPUs, and AI accelerators),
          and AI services/consulting. This scope was locked on 2026-03-23 before any data collection,
          preventing anchor estimate shopping.
        </p>
        <p className="mt-2">
          Closest analyst match: IDC Worldwide AI Spending Guide (enterprise narrow scope, coefficient 1.0).
          Gartner{"'"}s broader $1.5T+ definition receives a 0.18x scope coefficient.
        </p>
      </Section>

      <Section title="Data Sources">
        <ul className="list-disc ml-5 space-y-1">
          <li><strong>Analyst Consensus:</strong> 8 firms (IDC, Gartner, Grand View Research, Statista, Goldman Sachs, Bloomberg Intelligence, McKinsey, CB Insights)</li>
          <li><strong>EDGAR Filings:</strong> 10-K/10-Q from 14 public companies for revenue attribution</li>
          <li><strong>World Bank:</strong> GDP deflators, R&D expenditure, ICT exports, patent data</li>
          <li><strong>OECD MSTI:</strong> Business R&D by sector</li>
          <li><strong>Private Companies:</strong> 18 private AI companies valued via comparable EV/Revenue multiples</li>
        </ul>
      </Section>

      <Section title="Scope Normalization">
        <p>
          Each analyst firm{"'"}s published estimate is multiplied by a scope coefficient from the
          scope_mapping_table in ai.yaml. Per (estimate_year, segment) group, the scope-normalized
          estimates are aggregated: median = point estimate, 25th/75th percentiles = uncertainty band.
          All values deflated to 2020 constant USD using World Bank GDP deflator, then reflated to
          nominal for display.
        </p>
      </Section>

      <Section title="Statistical Models">
        <p>
          <strong>ARIMA:</strong> Auto-selected order via AICc (pmdarima). Max p=2, q=2 for parsimony.
          Fitted on quarterly market anchor series (36 observations per segment).
        </p>
        <p className="mt-2">
          <strong>Prophet:</strong> Explicit 2022 changepoint for GenAI surge. changepoint_prior_scale=0.1.
          Quarterly frequency. Real observations weighted 3x vs interpolated.
        </p>
      </Section>

      <Section title="Ensemble">
        <p>
          LightGBM is trained on statistical model residuals (not raw targets). The additive blend
          formula is: <code className="font-mono text-accent">stat_pred + lgbm_weight * correction</code>.
          Weights computed via inverse-RMSE from expanding-window CV.
        </p>
      </Section>

      <Section title="Confidence Intervals">
        <p>
          Bootstrap-based: 1000 resamples of Prophet in-sample residuals added to point forecasts.
          Empirical 10th/90th percentiles for 80% CI, 2.5th/97.5th for 95% CI.
          Minimum floor widths: 25% (CI80) and 40% (CI95) of point estimate.
        </p>
        <p className="mt-2">
          Backtesting coverage: CI80 = 90% (target 80%), CI95 = 100% (target 95%).
        </p>
      </Section>

      <Section title="Limitations">
        <ul className="list-disc ml-5 space-y-1">
          <li>Market anchors rely on analyst consensus which may lag real market shifts</li>
          <li>Private company ARR estimates have HIGH/MEDIUM/LOW confidence tiers</li>
          <li>Quarterly interpolation between annual data points introduces synthetic observations</li>
          <li>CAGR calibration floors may override model-generated growth when model underperforms</li>
          <li>Geographic coverage: ~85% of global AI activity (19 economies)</li>
        </ul>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold mb-3 text-accent">{title}</h2>
      <div className="text-sm text-text/80 leading-relaxed">{children}</div>
    </section>
  );
}
