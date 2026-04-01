"""Bottom-up validation endpoint (v2-AP6)."""

import pandas as pd
from fastapi import APIRouter, Query

from api.data_loader import get_bottom_up_validation
from api.schemas import ValidationResponse, ValidationRow

router = APIRouter(prefix="/api/v1", tags=["validation"])


@router.get("/validation", response_model=ValidationResponse)
def validation(
    segment: str | None = Query(None, description="Filter by segment, e.g. ai_hardware"),
):
    """Return bottom-up vs top-down validation data per segment and year."""
    df = get_bottom_up_validation()
    if df.empty:
        return ValidationResponse(data=[], count=0)

    if segment:
        df = df[df["segment"] == segment]

    df = df.sort_values(["segment", "year"])

    rows = [
        ValidationRow(
            segment=str(r["segment"]),
            year=int(r["year"]),
            bottom_up_sum=round(float(r["bottom_up_sum"]), 2),
            top_down_estimate=round(float(r["top_down_estimate"]), 2),
            coverage_ratio=round(float(r["coverage_ratio"]), 4),
            gap_usd_billions=round(float(r["gap_usd_billions"]), 2),
            n_companies=int(r["n_companies"]),
            top_contributors=list(r["top_contributors"]) if r["top_contributors"] is not None else [],
            company_capex_sum=round(float(r.get("company_capex_sum", 0)), 2),
            capex_intensity=round(float(r.get("capex_intensity", 0)), 4),
            capex_implied_growth=round(float(r["capex_implied_growth"]), 4)
            if pd.notna(r.get("capex_implied_growth")) else None,
        )
        for _, r in df.iterrows()
    ]

    return ValidationResponse(data=rows, count=len(rows))
