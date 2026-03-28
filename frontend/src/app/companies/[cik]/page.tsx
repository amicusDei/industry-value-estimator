import { getCompanies } from "@/lib/api";
import { formatUsdB } from "@/lib/formatters";
import Link from "next/link";

export const dynamic = "force-dynamic";

const METHOD_LABELS: Record<string, { label: string; color: string }> = {
  direct_disclosure: { label: "Direct Disclosure", color: "bg-[#22c55e20] text-positive" },
  management_commentary: { label: "Mgmt Commentary", color: "bg-[#3b82f620] text-[#60a5fa]" },
  analogue_ratio: { label: "Analogue Ratio", color: "bg-[#eab30820] text-[#eab308]" },
};

export default async function CompanyDetailPage({ params }: { params: Promise<{ cik: string }> }) {
  const { cik } = await params;
  let company: Awaited<ReturnType<typeof getCompanies>>["data"][0] | null = null;

  try {
    const res = await getCompanies();
    company = res.data.find((c) => c.cik === cik) || null;
  } catch { /* API offline */ }

  if (!company) {
    return (
      <div>
        <Link href="/companies" className="text-accent text-sm hover:underline">&larr; Back</Link>
        <p className="text-muted mt-4">Company not found (CIK: {cik}).</p>
      </div>
    );
  }

  const method = METHOD_LABELS[company.attribution_method] || { label: company.attribution_method, color: "bg-[#ffffff10] text-muted" };

  return (
    <div>
      <Link href="/companies" className="text-accent text-sm hover:underline">&larr; All Companies</Link>

      <h1 className="text-2xl font-semibold mt-4 mb-2">{company.company_name}</h1>
      <p className="text-muted text-sm mb-6">CIK: {company.cik}</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-surface border border-border rounded-lg p-4">
          <p className="text-muted text-xs uppercase mb-1">AI Revenue</p>
          <p className="font-mono text-2xl">{formatUsdB(company.ai_revenue_usd_billions)}</p>
        </div>
        <div className="bg-surface border border-border rounded-lg p-4">
          <p className="text-muted text-xs uppercase mb-1">Segment</p>
          <p className="text-lg">{company.segment.replace("ai_", "AI ").replace("_", " ")}</p>
        </div>
        <div className="bg-surface border border-border rounded-lg p-4">
          <p className="text-muted text-xs uppercase mb-1">Value Chain Layer</p>
          <p className="text-lg capitalize">{company.value_chain_layer}</p>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg p-4">
        <p className="text-muted text-xs uppercase mb-2">Attribution Method</p>
        <span className={`text-sm px-3 py-1 rounded ${method.color}`}>{method.label}</span>
      </div>
    </div>
  );
}
