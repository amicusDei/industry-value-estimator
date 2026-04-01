"""Analyst dispersion endpoint."""

from fastapi import APIRouter, Query

from api.data_loader import get_dispersion
from api.schemas import DispersionResponse, DispersionRow

router = APIRouter(prefix="/api/v1", tags=["dispersion"])


@router.get("/dispersion", response_model=DispersionResponse)
def dispersion(
    segment: str | None = Query(None, description="Filter by segment"),
):
    """Return analyst estimate dispersion data (IQR, std, min/max, n_sources) per segment and year."""
    df = get_dispersion()
    if df.empty:
        return DispersionResponse(data=[], count=0)

    if segment:
        df = df[df["segment"] == segment]

    df = df.sort_values(["segment", "year"])

    rows = [
        DispersionRow(
            segment=str(r["segment"]),
            year=int(r["year"]),
            iqr_usd_billions=round(float(r["iqr_usd_billions"]), 3),
            std_usd_billions=round(float(r["std_usd_billions"]), 3),
            min_usd_billions=round(float(r["min_usd_billions"]), 3),
            max_usd_billions=round(float(r["max_usd_billions"]), 3),
            n_sources=int(r["n_sources"]),
            dispersion_ratio=round(float(r["dispersion_ratio"]), 4),
        )
        for _, r in df.iterrows()
    ]

    return DispersionResponse(data=rows, count=len(rows))
