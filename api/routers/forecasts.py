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
    valuation: str = Query("nominal", description="'nominal' or 'real_2020'"),
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

    # Select columns based on valuation mode
    if valuation == "real_2020":
        pt_col, ci80l, ci80u, ci95l, ci95u = (
            "point_estimate_real_2020", "ci80_lower", "ci80_upper", "ci95_lower", "ci95_upper",
        )
    else:
        pt_col = "point_estimate_nominal"
        ci80l = "ci80_lower_nominal" if "ci80_lower_nominal" in df.columns else "ci80_lower"
        ci80u = "ci80_upper_nominal" if "ci80_upper_nominal" in df.columns else "ci80_upper"
        ci95l = "ci95_lower_nominal" if "ci95_lower_nominal" in df.columns else "ci95_lower"
        ci95u = "ci95_upper_nominal" if "ci95_upper_nominal" in df.columns else "ci95_upper"

    rows = [
        ForecastRow(
            year=int(r["year"]),
            quarter=int(r["quarter"]),
            segment=str(r["segment"]),
            point_estimate=float(r[pt_col]),
            ci80_lower=float(r[ci80l]),
            ci80_upper=float(r[ci80u]),
            ci95_lower=float(r[ci95l]),
            ci95_upper=float(r[ci95u]),
            is_forecast=bool(r["is_forecast"]),
        )
        for _, r in df.iterrows()
    ]

    return ForecastResponse(data=rows, count=len(rows), data_vintage=vintage)
