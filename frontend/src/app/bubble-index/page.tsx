import { getBubbleIndex, getDotcomParallel, getDCRisk } from "@/lib/api";
import type { BubbleIndexRow, DotcomParallelResponse, DCRiskResponse } from "@/lib/api";
import BubbleGauge from "@/components/charts/BubbleGauge";
import SubindicatorBars from "@/components/charts/SubindicatorBars";
import DotcomParallel from "@/components/charts/DotcomParallel";
import DataCentreRisk from "@/components/charts/DataCentreRisk";

export const dynamic = "force-dynamic";

function generateFindings(latest: BubbleIndexRow): string[] {
  const findings: string[] = [];

  // Capex intensity
  findings.push(
    `AI capex intensity ratio stands at ${latest.capex_intensity_ratio.toFixed(1)}\u00d7 \u2014 hyperscalers are spending $${Math.round(latest.capex_intensity_ratio * 100)}B on AI infrastructure for every $100B in AI revenue.`
  );

  // Credit exposure
  findings.push(
    `Total AI-related credit exposure has reached $${latest.credit_total_usd_b.toFixed(0)}B, spanning hyperscaler bonds, private credit, and off-balance-sheet vehicles (BIS QR March 2026).`
  );

  // Productivity gap
  const gap = latest.ai_capex_growth_yoy_pct / Math.max(0.1, latest.us_productivity_growth_pct);
  findings.push(
    `Productivity gap: AI capex growing ${latest.ai_capex_growth_yoy_pct.toFixed(0)}% YoY while US productivity grows ${latest.us_productivity_growth_pct.toFixed(1)}% \u2014 a ${gap.toFixed(0)}\u00d7 divergence (Goldman Sachs March 2026: "no meaningful economy-wide relationship").`
  );

  // Enterprise ROI
  findings.push(
    `Only ${latest.revenue_and_cost_impact_pct.toFixed(0)}% of enterprises report both revenue growth and cost reduction from AI (PwC Global CEO Survey 2026).`
  );

  // Market concentration
  findings.push(
    `Top-5 tech companies now represent ${latest.top5_pct_sp500.toFixed(0)}% of S&P 500 market cap \u2014 exceeding the dotcom-era peak concentration of ~18%.`
  );

  return findings;
}

const SOURCES = [
  "BIS Quarterly Review (March 2026)",
  "BIS Bulletin 120",
  "MUFG Global Markets Research",
  "Goldman Sachs Productivity Study (March 2026)",
  "PwC Global CEO Survey 2026",
  "Dell'Oro Group",
  "MIT/Sloan Management Review",
  "St. Louis Fed AI GDP Tracker",
  "Deloitte AI State of Enterprise 2026",
  "NBER CEO Study (Feb 2026)",
];

export default async function BubbleIndexPage() {
  let rows: BubbleIndexRow[] = [];
  let dotcomData: DotcomParallelResponse = { ai: [], dotcom: [] };
  let dcRiskData: DCRiskResponse | null = null;

  try {
    const [biData, dcData, dcRisk] = await Promise.all([
      getBubbleIndex(),
      getDotcomParallel(),
      getDCRisk(),
    ]);
    rows = biData;
    dotcomData = dcData;
    dcRiskData = dcRisk;
  } catch {
    return (
      <div className="text-muted">
        API offline or bubble index data not available.
      </div>
    );
  }

  if (rows.length === 0) {
    return <div className="text-muted">No bubble index data available.</div>;
  }

  // Latest row
  const latest = rows[rows.length - 1];
  const findings = generateFindings(latest);

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold">AI Bubble Index</h1>
        <p className="text-muted text-sm mt-1">
          Composite risk score tracking AI market overheating across investment
          intensity, productivity realization, and historical parallels.{" "}
          <span className="font-mono text-text">
            {latest.year} H{latest.half}
          </span>
        </p>
      </div>

      {/* Gauge - centered hero */}
      <div className="flex justify-center mb-10">
        <div className="w-full max-w-md">
          <BubbleGauge
            score={latest.composite_score}
            classification={latest.classification}
          />
        </div>
      </div>

      {/* Timeline mini */}
      <div className="bg-surface border border-border rounded-lg p-4 mb-8">
        <h2 className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
          Score Timeline
        </h2>
        <div className="flex gap-1 items-end h-16">
          {rows.map((r, i) => {
            const heightPct = Math.max(4, r.composite_score);
            const color =
              r.composite_score < 30
                ? "#22c55e"
                : r.composite_score < 50
                  ? "#eab308"
                  : r.composite_score < 70
                    ? "#f97316"
                    : "#ef4444";
            const isLast = i === rows.length - 1;
            return (
              <div
                key={`${r.year}-${r.half}`}
                className="flex-1 flex flex-col items-center gap-1"
              >
                <div
                  className="w-full rounded-t-sm transition-all"
                  style={{
                    height: `${heightPct}%`,
                    backgroundColor: color,
                    opacity: isLast ? 1 : 0.6,
                  }}
                />
                <span className="text-[8px] text-muted font-mono leading-none">
                  {String(r.year).slice(-2)}
                  H{r.half}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Subindicator bars */}
      <div className="bg-surface border border-border rounded-lg p-5 mb-8">
        <h2 className="text-lg font-semibold mb-4">Sub-Indicators</h2>
        <SubindicatorBars data={latest} />
      </div>

      {/* Dotcom Parallel Chart */}
      <div className="mb-8">
        <DotcomParallel ai={dotcomData.ai} dotcom={dotcomData.dotcom} />
      </div>

      {/* Data Centre Risk Deep-Dive */}
      {dcRiskData && (
        <div className="mb-8">
          <DataCentreRisk data={dcRiskData} />
        </div>
      )}

      {/* Key Findings */}
      <div className="bg-surface border border-border rounded-lg p-5 mb-8">
        <h2 className="text-lg font-semibold mb-3">Key Findings</h2>
        <ul className="space-y-2">
          {findings.map((f, i) => (
            <li key={i} className="flex gap-2 text-sm text-text">
              <span className="text-accent font-mono shrink-0">{i + 1}.</span>
              <span>{f}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Sources */}
      <div className="border-t border-border pt-4">
        <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
          Sources
        </h3>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {SOURCES.map((s) => (
            <span key={s} className="text-[10px] text-muted">
              {s}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
