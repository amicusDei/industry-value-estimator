"""Total market aggregate endpoint."""

import math
from fastapi import APIRouter, Query

from api.data_loader import get_forecasts
from api.schemas import ForecastResponse, ForecastRow

router = APIRouter(prefix="/api/v1", tags=["total"])

# Overlap discount: sum of segments double-counts ~15% due to
# hardware→infra, software→adoption, and infra→software overlaps
# (documented in ai.yaml market_boundary.overlap_zones)
OVERLAP_DISCOUNT = 0.85


@router.get("/forecasts/total", response_model=ForecastResponse)
def total_forecasts(
    valuation: str = Query("nominal", description="'nominal' or 'real_2020'"),
):
    df = get_forecasts()
    if df.empty:
        return ForecastResponse(data=[], count=0, data_vintage=None)

    # Select columns based on valuation
    if valuation == "real_2020":
        pt, ci80l, ci80u, ci95l, ci95u = (
            "point_estimate_real_2020", "ci80_lower", "ci80_upper",
            "ci95_lower", "ci95_upper",
        )
    else:
        pt = "point_estimate_nominal"
        ci80l = "ci80_lower_nominal" if "ci80_lower_nominal" in df.columns else "ci80_lower"
        ci80u = "ci80_upper_nominal" if "ci80_upper_nominal" in df.columns else "ci80_upper"
        ci95l = "ci95_lower_nominal" if "ci95_lower_nominal" in df.columns else "ci95_lower"
        ci95u = "ci95_upper_nominal" if "ci95_upper_nominal" in df.columns else "ci95_upper"

    vintage = str(df["data_vintage"].iloc[0]) if "data_vintage" in df.columns else None

    # Exclude "total" segment if present, aggregate the 4 sub-segments
    sub = df[~df["segment"].isin(["total"])]

    # Group by (year, quarter) and aggregate
    grouped = sub.groupby(["year", "quarter"]).agg(
        point=( pt, "sum"),
        c80l=(ci80l, "sum"),
        c80u=(ci80u, "sum"),
        c95l=(ci95l, "sum"),
        c95u=(ci95u, "sum"),
        is_forecast=("is_forecast", "first"),
    ).reset_index()

    rows = []
    for _, r in grouped.iterrows():
        point = float(r["point"]) * OVERLAP_DISCOUNT
        rows.append(ForecastRow(
            year=int(r["year"]),
            quarter=int(r["quarter"]),
            segment="total",
            point_estimate=round(point, 2),
            ci80_lower=round(float(r["c80l"]) * OVERLAP_DISCOUNT, 2),
            ci80_upper=round(float(r["c80u"]) * OVERLAP_DISCOUNT, 2),
            ci95_lower=round(float(r["c95l"]) * OVERLAP_DISCOUNT, 2),
            ci95_upper=round(float(r["c95u"]) * OVERLAP_DISCOUNT, 2),
            is_forecast=bool(r["is_forecast"]),
        ))

    rows.sort(key=lambda r: (r.year, r.quarter))
    return ForecastResponse(data=rows, count=len(rows), data_vintage=vintage)
