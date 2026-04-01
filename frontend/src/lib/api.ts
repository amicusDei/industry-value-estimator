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

export interface DiagnosticsResponse {
  data: DiagnosticRow[];
  count: number;
  summary: Record<string, { mean_mape: number; n_folds: number }>;
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

export const getExportUrl = (format: "csv" | "excel", segment?: string) =>
  `${API_BASE}/api/v1/export/${format}?valuation=nominal${segment ? `&segment=${segment}` : ""}`;

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
}

export interface ValidationResponse {
  data: ValidationRow[];
  count: number;
}

export const getValidation = (segment?: string) =>
  fetchJSON<ValidationResponse>(
    `/api/v1/validation${segment ? `?segment=${segment}` : ""}`
  );
