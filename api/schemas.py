"""Pydantic response models for the FastAPI endpoints."""

from pydantic import BaseModel


class ForecastRow(BaseModel):
    year: int
    quarter: int
    segment: str
    point_estimate: float
    ci80_lower: float
    ci80_upper: float
    ci95_lower: float
    ci95_upper: float
    is_forecast: bool


class ForecastResponse(BaseModel):
    data: list[ForecastRow]
    count: int
    data_vintage: str | None


class SegmentSummary(BaseModel):
    id: str
    display_name: str
    market_size_2024_usd_b: float | None
    cagr_2025_2030_pct: float | None
    overlap_note: str


class SegmentsResponse(BaseModel):
    segments: list[SegmentSummary]


class CompanyRow(BaseModel):
    company_name: str
    cik: str
    segment: str
    ai_revenue_usd_billions: float
    attribution_method: str
    value_chain_layer: str


class CompaniesResponse(BaseModel):
    data: list[CompanyRow]
    count: int


class DiagnosticRow(BaseModel):
    year: int
    segment: str
    model: str
    mape: float
    actual_usd: float
    predicted_usd: float
    regime_label: str | None


class DiagnosticsResponse(BaseModel):
    data: list[DiagnosticRow]
    count: int
    summary: dict


class SensitivityRow(BaseModel):
    segment: str
    year: int
    quarter: int
    base: float
    shifted: float
    delta_pct: float


class SensitivityResponse(BaseModel):
    anchor_shift: float
    data: list[SensitivityRow]


class DispersionRow(BaseModel):
    segment: str
    year: int
    iqr_usd_billions: float
    std_usd_billions: float
    min_usd_billions: float
    max_usd_billions: float
    n_sources: int
    dispersion_ratio: float


class DispersionResponse(BaseModel):
    data: list[DispersionRow]
    count: int


class ScenarioForecastRow(BaseModel):
    year: int
    quarter: int
    segment: str
    scenario: str
    point_estimate: float
    ci80_lower: float
    ci80_upper: float
    ci95_lower: float
    ci95_upper: float
    is_forecast: bool


class ScenarioResponse(BaseModel):
    data: list[ScenarioForecastRow]
    count: int
    data_vintage: str | None


class InsightItem(BaseModel):
    type: str
    text: str
    priority: int


class InsightsResponse(BaseModel):
    data: list[InsightItem]
    count: int
    segment: str


class ValidationRow(BaseModel):
    segment: str
    year: int
    bottom_up_sum: float
    top_down_estimate: float
    coverage_ratio: float
    gap_usd_billions: float
    n_companies: int
    top_contributors: list[str]


class ValidationResponse(BaseModel):
    data: list[ValidationRow]
    count: int
