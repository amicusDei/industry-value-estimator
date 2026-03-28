import Link from "next/link";
import { getSegments } from "@/lib/api";
import { formatUsdB, formatPct } from "@/lib/formatters";

export const dynamic = "force-dynamic";

export default async function SegmentsPage() {
  let segments: Awaited<ReturnType<typeof getSegments>>["segments"] = [];
  try {
    segments = (await getSegments()).segments;
  } catch { /* API offline */ }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Segment Analysis</h1>
      <div className="grid gap-4">
        {segments.map((seg) => {
          const pct = formatPct(seg.cagr_2025_2030_pct);
          return (
            <Link
              key={seg.id}
              href={`/segments/${seg.id}`}
              className="bg-surface border border-border rounded-lg p-5 flex justify-between items-center hover:border-accent transition-colors"
            >
              <div>
                <p className="font-semibold">{seg.display_name}</p>
                <p className="text-xs text-muted mt-1">{seg.overlap_note}</p>
              </div>
              <div className="text-right">
                <p className="font-mono text-xl">{formatUsdB(seg.market_size_2024_usd_b)}</p>
                <p className={`font-mono text-sm ${pct.colorClass}`}>{pct.text} CAGR</p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
