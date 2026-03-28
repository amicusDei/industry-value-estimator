"""Sensitivity analysis endpoint."""

from fastapi import APIRouter, Query

from api.data_loader import get_forecasts
from api.schemas import SensitivityResponse, SensitivityRow

router = APIRouter(prefix="/api/v1", tags=["sensitivity"])


@router.get("/sensitivity", response_model=SensitivityResponse)
def sensitivity_analysis(
    anchor_shift: float = Query(0.1, description="Proportional shift (-0.2 to +0.2)"),
    segment: str | None = Query(None, description="Filter by segment"),
):
    """What-if: shift all market anchor point estimates by anchor_shift proportion."""
    df = get_forecasts()
    if df.empty:
        return SensitivityResponse(anchor_shift=anchor_shift, data=[])

    if segment:
        df = df[df["segment"] == segment]

    # Filter to Q4 forecast rows for concise output
    df = df[(df["quarter"] == 4) & (df["is_forecast"] == True)]

    rows = []
    for _, r in df.iterrows():
        base = float(r["point_estimate_nominal"])
        shifted = base * (1 + anchor_shift)
        delta = anchor_shift * 100
        rows.append(SensitivityRow(
            segment=str(r["segment"]),
            year=int(r["year"]),
            quarter=int(r["quarter"]),
            base=round(base, 2),
            shifted=round(shifted, 2),
            delta_pct=round(delta, 1),
        ))

    return SensitivityResponse(anchor_shift=anchor_shift, data=rows)
