import { formatUsdB, formatPct } from "@/lib/formatters";

interface KpiCardProps {
  segmentName: string;
  marketSize: number | null;
  cagr: number | null;
}

export default function KpiCard({ segmentName, marketSize, cagr }: KpiCardProps) {
  const pct = formatPct(cagr);

  return (
    <div className="bg-surface border border-border rounded-lg p-5 hover:border-accent-muted transition-colors">
      <p className="text-muted text-xs uppercase tracking-wider mb-3">{segmentName}</p>
      <p className="font-mono text-3xl font-semibold text-text mb-2">
        {formatUsdB(marketSize)}
      </p>
      <div className="flex items-center gap-2">
        <span className="text-muted text-xs">CAGR 2025-30</span>
        <span className={`font-mono text-sm font-medium ${pct.colorClass}`}>
          {pct.text}
        </span>
      </div>
    </div>
  );
}
