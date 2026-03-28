const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json();
}

export interface SegmentSummary {
  id: string;
  display_name: string;
  market_size_2024_usd_b: number | null;
  cagr_2025_2030_pct: number | null;
  overlap_note: string;
}

export interface SegmentsResponse {
  segments: SegmentSummary[];
}

export interface ForecastRow {
  year: number;
  quarter: number;
  segment: string;
  point_estimate_real_2020: number;
  point_estimate_nominal: number;
  ci80_lower: number;
  ci80_upper: number;
  ci95_lower: number;
  ci95_upper: number;
  is_forecast: boolean;
}

export interface ForecastResponse {
  data: ForecastRow[];
  count: number;
  data_vintage: string | null;
}

export interface CompanyRow {
  company_name: string;
  cik: string;
  segment: string;
  ai_revenue_usd_billions: number;
  attribution_method: string;
  value_chain_layer: string;
}

export interface CompaniesResponse {
  data: CompanyRow[];
  count: number;
}

export interface DiagnosticRow {
  year: number;
  segment: string;
  model: string;
  mape: number;
  actual_usd: number;
  predicted_usd: number;
  regime_label: string | null;
}

export interface DiagnosticsResponse {
  data: DiagnosticRow[];
  count: number;
  summary: Record<string, { mean_mape: number; n_folds: number }>;
}

export const getSegments = () => fetchJSON<SegmentsResponse>("/api/v1/segments");
export const getForecasts = (segment?: string) =>
  fetchJSON<ForecastResponse>(
    `/api/v1/forecasts${segment ? `?segment=${segment}` : ""}`
  );
export const getCompanies = () => fetchJSON<CompaniesResponse>("/api/v1/companies");
export const getDiagnostics = () => fetchJSON<DiagnosticsResponse>("/api/v1/diagnostics");
