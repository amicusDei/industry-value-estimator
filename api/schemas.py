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
