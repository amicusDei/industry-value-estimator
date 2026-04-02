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
    `AI revenue HHI at ${latest.ai_revenue_hhi.toFixed(2)} \u2014 NVIDIA holds ${latest.top_player_ai_share_pct.toFixed(0)}% of AI chip market, exceeding dotcom-era concentration levels.`
  );

  return findings;
}

function classifyScore(score: number): string {
  if (score < 30) return "Healthy Expansion";
  if (score < 50) return "Elevated Valuations";
  if (score < 70) return "Bubble Warning";
  return "Critical Overheating";
}

function ScoreTimeline({ rows }: { rows: BubbleIndexRow[] }) {
  // Chart dimensions
  const marginLeft = 32;
  const marginRight = 8;
  const marginTop = 4;
  const marginBottom = 24;
  const width = 600;
  const height = 140;
  const chartW = width - marginLeft - marginRight;
  const chartH = height - marginTop - marginBottom;

  const n = rows.length;
  if (n === 0) return null;

  // Scale helpers
  const xStep = chartW / Math.max(n - 1, 1);
  const x = (i: number) => marginLeft + i * xStep;
  const y = (score: number) => marginTop + chartH - (score / 100) * chartH;

  // Zone backgrounds (green 0-30, yellow 30-50, orange 50-70, red 70-100)
  const zones = [
    { min: 0, max: 30, color: "rgba(34,197,94,0.07)" },
    { min: 30, max: 50, color: "rgba(234,179,8,0.07)" },
    { min: 50, max: 70, color: "rgba(249,115,22,0.07)" },
    { min: 70, max: 100, color: "rgba(239,68,68,0.07)" },
  ];

  // Threshold lines
  const thresholds = [30, 50, 70];

  // Build line path
  const linePath = rows
    .map((row, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(row.composite_score).toFixed(1)}`)
    .join(" ");

  // Build area path (line + close along bottom)
  const areaPath =
    linePath +
    ` L ${x(n - 1).toFixed(1)} ${y(0).toFixed(1)} L ${x(0).toFixed(1)} ${y(0).toFixed(1)} Z`;

  // Y-axis labels
  const yLabels = [0, 30, 50, 70, 100];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height: "140px" }}>
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f97316" stopOpacity={0.25} />
          <stop offset="100%" stopColor="#f97316" stopOpacity={0.02} />
        </linearGradient>
      </defs>

      {/* Zone backgrounds */}
      {zones.map((z) => (
        <rect
          key={z.min}
          x={marginLeft}
          y={y(z.max)}
          width={chartW}
          height={y(z.min) - y(z.max)}
          fill={z.color}
        />
      ))}

      {/* Threshold dashed lines */}
      {thresholds.map((t) => (
        <line
          key={t}
          x1={marginLeft}
          y1={y(t)}
          x2={marginLeft + chartW}
          y2={y(t)}
          stroke="#475569"
          strokeWidth={1}
          strokeDasharray="4 3"
        />
      ))}

      {/* Y-axis labels */}
      {yLabels.map((v) => (
        <text
          key={v}
          x={marginLeft - 4}
          y={y(v)}
          textAnchor="end"
          dominantBaseline="middle"
          fill="#64748b"
          fontSize="9"
          fontFamily="JetBrains Mono, monospace"
        >
          {v}
        </text>
      ))}

      {/* Area fill */}
      <path d={areaPath} fill="url(#areaGrad)" />

      {/* Score line */}
      <path d={linePath} fill="none" stroke="#f97316" strokeWidth={2} strokeLinejoin="round" />

      {/* Data points + tooltips */}
      {rows.map((row, i) => (
        <g key={`${row.year}-${row.half}`}>
          {/* Invisible larger hit area for tooltip */}
          <circle cx={x(i)} cy={y(row.composite_score)} r={8} fill="transparent">
            <title>{`${row.year} H${row.half}: Score ${row.composite_score.toFixed(1)} \u2014 ${classifyScore(row.composite_score)}`}</title>
          </circle>
          {/* Visible dot */}
          <circle
            cx={x(i)}
            cy={y(row.composite_score)}
            r={3}
            fill="#f97316"
            stroke="#0f172a"
            strokeWidth={1.5}
          />
        </g>
      ))}

      {/* X-axis labels */}
      {rows.map((row, i) => (
        <text
          key={`label-${row.year}-${row.half}`}
          x={x(i)}
          y={height - 4}
          textAnchor="middle"
          fill="#64748b"
          fontSize="8"
          fontFamily="JetBrains Mono, monospace"
        >
          {String(row.year).slice(-2)}H{row.half}
        </text>
      ))}
    </svg>
  );
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

  // Latest row + previous half-year for YoY trend
  const latest = rows[rows.length - 1];
  const previousHalf = rows.length >= 2 ? rows[rows.length - 2] : undefined;
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
            previousData={previousHalf ? { composite_score: previousHalf.composite_score, year: previousHalf.year, half: previousHalf.half } : undefined}
          />
        </div>
      </div>

      {/* Timeline mini */}
      <div className="bg-surface border border-border rounded-lg p-4 mb-8">
        <h2 className="text-sm text-slate-400 mb-3">
          Score Timeline
        </h2>
        <ScoreTimeline rows={rows} />
      </div>

      {/* Subindicator bars */}
      <div className="bg-surface border border-border rounded-lg p-5 mb-8">
        <h2 className="text-lg font-semibold mb-4">Sub-Indicators</h2>
        <SubindicatorBars data={latest} previousData={previousHalf} />
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
