import Link from "next/link";
import { getCompanies } from "@/lib/api";
import { formatUsdB } from "@/lib/formatters";

export const dynamic = "force-dynamic";

const METHOD_COLORS: Record<string, string> = {
  direct_disclosure: "bg-[#22c55e20] text-positive",
  management_commentary: "bg-[#3b82f620] text-[#60a5fa]",
  analogue_ratio: "bg-[#eab30820] text-[#eab308]",
};

export default async function CompaniesPage() {
  let companies: Awaited<ReturnType<typeof getCompanies>>["data"] = [];
  try {
    const res = await getCompanies();
    companies = res.data.sort((a, b) => b.ai_revenue_usd_billions - a.ai_revenue_usd_billions);
  } catch { /* API offline */ }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Company AI Revenue Attribution</h1>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-muted text-xs uppercase border-b border-border">
              <th className="text-left py-2 px-3">Company</th>
              <th className="text-left py-2 px-3">Segment</th>
              <th className="text-left py-2 px-3">Value Chain</th>
              <th className="text-right py-2 px-3">AI Revenue</th>
              <th className="text-center py-2 px-3">Method</th>
            </tr>
          </thead>
          <tbody>
            {companies.map((c) => (
              <tr key={c.cik} className="border-b border-border/50 hover:bg-surface-hover transition-colors">
                <td className="py-2.5 px-3">
                  <Link href={`/companies/${c.cik}`} className="text-text hover:text-accent transition-colors">
                    {c.company_name}
                  </Link>
                </td>
                <td className="py-2.5 px-3 text-muted text-xs">{c.segment.replace("ai_", "").replace("_", " ")}</td>
                <td className="py-2.5 px-3 text-muted text-xs">{c.value_chain_layer}</td>
                <td className="py-2.5 px-3 font-mono text-right">{formatUsdB(c.ai_revenue_usd_billions)}</td>
                <td className="py-2.5 px-3 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded ${METHOD_COLORS[c.attribution_method] || "bg-[#ffffff10] text-muted"}`}>
                    {c.attribution_method.replace("_", " ")}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {companies.length > 0 && (
        <p className="text-xs text-muted mt-4">
          Total: {formatUsdB(companies.reduce((s, c) => s + c.ai_revenue_usd_billions, 0))} across {companies.length} companies (FY2024)
        </p>
      )}
    </div>
  );
}
