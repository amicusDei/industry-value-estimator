"""Forecast data endpoints."""

from fastapi import APIRouter, Query

from api.data_loader import get_forecasts
from api.schemas import ForecastResponse, ForecastRow

router = APIRouter(prefix="/api/v1", tags=["forecasts"])


@router.get("/forecasts", response_model=ForecastResponse)
def list_forecasts(
    segment: str | None = Query(None, description="Filter by segment"),
    year: int | None = Query(None, description="Filter by year"),
    forecast_only: bool = Query(False, description="Only forecast rows"),
):
    df = get_forecasts()
    if df.empty:
        return ForecastResponse(data=[], count=0, data_vintage=None)

    if segment:
        df = df[df["segment"] == segment]
    if year:
        df = df[df["year"] == year]
    if forecast_only:
        df = df[df["is_forecast"] == True]

    vintage = str(df["data_vintage"].iloc[0]) if "data_vintage" in df.columns and len(df) > 0 else None

    rows = [
        ForecastRow(
            year=int(r["year"]),
            quarter=int(r["quarter"]),
            segment=str(r["segment"]),
            point_estimate_real_2020=float(r["point_estimate_real_2020"]),
            point_estimate_nominal=float(r["point_estimate_nominal"]),
            ci80_lower=float(r["ci80_lower"]),
            ci80_upper=float(r["ci80_upper"]),
            ci95_lower=float(r["ci95_lower"]),
            ci95_upper=float(r["ci95_upper"]),
            is_forecast=bool(r["is_forecast"]),
        )
        for _, r in df.iterrows()
    ]

    return ForecastResponse(data=rows, count=len(rows), data_vintage=vintage)
