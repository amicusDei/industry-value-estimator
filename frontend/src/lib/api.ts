function getApiBase(): string {
  // If explicitly set, use that (e.g. for local dev pointing at FastAPI)
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  // On Vercel (server-side), use the deployment URL
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  // Client-side or local dev: relative URL
  if (typeof window !== 'undefined') return '';
  // Fallback for local SSR
  return 'http://localhost:3000';
}

const API_BASE = getApiBase();

async function fetchJSON<T>(path: string): Promise<T> {
  const base = getApiBase();
  const res = await fetch(`${base}${path}`, { next: { revalidate: 60 } });
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
  point_estimate: number;
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

export interface MapeMatrixEntry {
  segment: string;
  [year: string]: string | number;
}

export interface CiCoverageEntry {
  segment: string;
  ci80_target: number;
  ci80_actual: number;
  ci95_target: number;
  ci95_actual: number;
}

export interface RegimeComparisonEntry {
  segment: string;
  pre_genai_mape: number | null;
  post_genai_mape: number | null;
}

export interface DataSourceEntry {
  source_name: string;
  segments_covered: string[];
  years_covered: string;
  n_entries: number;
}

export interface DiagnosticsResponse {
  data: DiagnosticRow[];
  count: number;
  summary: Record<string, { mean_mape: number; n_folds: number }>;
  mape_matrix: MapeMatrixEntry[];
  ci_coverage: CiCoverageEntry[];
  regime_comparison: RegimeComparisonEntry[];
  data_sources: DataSourceEntry[];
}

export interface SensitivityRow {
  segment: string;
  year: number;
  quarter: number;
  base: number;
  shifted: number;
  delta_pct: number;
}

export interface SensitivityResponse {
  anchor_shift: number;
  data: SensitivityRow[];
}

export const getSegments = (valuation = "nominal") =>
  fetchJSON<SegmentsResponse>(`/api/v1/segments?valuation=${valuation}`);

export const getForecasts = (segment?: string, valuation = "nominal") =>
  fetchJSON<ForecastResponse>(
    `/api/v1/forecasts?valuation=${valuation}${segment ? `&segment=${segment}` : ""}`
  );

export const getCompanies = () => fetchJSON<CompaniesResponse>("/api/v1/companies");
export const getDiagnostics = () => fetchJSON<DiagnosticsResponse>("/api/v1/diagnostics");

export const getSensitivity = (shift: number, segment?: string) =>
  fetchJSON<SensitivityResponse>(
    `/api/v1/sensitivity?anchor_shift=${shift}${segment ? `&segment=${segment}` : ""}`
  );

export const getTotalForecasts = (valuation = "nominal") =>
  fetchJSON<ForecastResponse>(`/api/v1/forecasts/total?valuation=${valuation}`);

export interface AnalystFirm {
  firm: string;
  scope_alignment: string;
  scope_coefficient: number;
  estimates: { year: number; value: number }[];
  scope_includes: string;
  scope_excludes: string;
}

export interface ConsensusResponse {
  firms: AnalystFirm[];
  our_median_2024: number | null;
}

export const getConsensus = () => fetchJSON<ConsensusResponse>("/api/v1/analyst-consensus");

export interface DataQualitySegment {
  real_data_points: number;
  interpolated_data_points: number;
  real_data_ratio: number;
  earliest_real_year: number | null;
  latest_real_year: number | null;
  n_analyst_firms: number;
  backtesting_mape: number | null;
  backtesting_model: string;
  ci80_coverage: number | null;
  ci95_coverage: number | null;
  cagr_source: string;
}

export interface DataQualityResponse {
  per_segment: Record<string, DataQualitySegment>;
  methodology_caveats: string[];
}

export const getDataQuality = () => fetchJSON<DataQualityResponse>("/api/v1/data-quality");

export interface DispersionRow {
  segment: string;
  year: number;
  iqr_usd_billions: number;
  std_usd_billions: number;
  min_usd_billions: number;
  max_usd_billions: number;
  n_sources: number;
  dispersion_ratio: number;
}

export interface DispersionResponse {
  data: DispersionRow[];
  count: number;
}

export const getDispersion = (segment?: string) =>
  fetchJSON<DispersionResponse>(
    `/api/v1/dispersion${segment ? `?segment=${segment}` : ""}`
  );

export const getExportUrl = (format: "csv" | "excel", segment?: string, scenario?: string) => {
  const base = process.env.NEXT_PUBLIC_API_URL || '';
  // In serverless mode (no explicit API_URL), only CSV is available
  const effectiveFormat = base ? format : "csv";
  return `${base}/api/v1/export/${effectiveFormat}?valuation=nominal${segment ? `&segment=${segment}` : ""}${scenario ? `&scenario=${scenario}` : ""}`;
};

export interface ScenarioForecastRow {
  year: number;
  quarter: number;
  segment: string;
  scenario: string;
  point_estimate: number;
  ci80_lower: number;
  ci80_upper: number;
  ci95_lower: number;
  ci95_upper: number;
  is_forecast: boolean;
}

export interface ScenarioResponse {
  data: ScenarioForecastRow[];
  count: number;
  data_vintage: string | null;
}

export const getScenarioForecasts = (segment?: string, scenario?: string) =>
  fetchJSON<ScenarioResponse>(
    `/api/v1/scenarios?${segment ? `segment=${segment}` : ""}${scenario ? `&scenario=${scenario}` : ""}`
  );

export interface InsightItem {
  type: string;
  text: string;
  priority: number;
}

export interface InsightsResponse {
  data: InsightItem[];
  count: number;
  segment: string;
}

export const getInsights = (segment: string) =>
  fetchJSON<InsightsResponse>(`/api/v1/insights?segment=${segment}`);

export interface ValidationRow {
  segment: string;
  year: number;
  bottom_up_sum: number;
  top_down_estimate: number;
  coverage_ratio: number;
  gap_usd_billions: number;
  n_companies: number;
  top_contributors: string[];
  company_capex_sum: number;
  capex_intensity: number;
  capex_implied_growth: number | null;
}

export interface ValidationResponse {
  data: ValidationRow[];
  count: number;
}

export const getValidation = (segment?: string) =>
  fetchJSON<ValidationResponse>(
    `/api/v1/validation${segment ? `?segment=${segment}` : ""}`
  );
