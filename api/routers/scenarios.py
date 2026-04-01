"""Scenario forecast endpoints."""

from fastapi import APIRouter, Query

from api.data_loader import get_scenario_forecasts
from api.schemas import ScenarioForecastRow, ScenarioResponse

router = APIRouter(prefix="/api/v1", tags=["scenarios"])


@router.get("/scenarios", response_model=ScenarioResponse)
def list_scenarios(
    segment: str | None = Query(None, description="Filter by segment"),
    scenario: str | None = Query(None, description="Filter by scenario (conservative, base, aggressive)"),
    valuation: str = Query("nominal", description="'nominal' or 'real_2020'"),
):
    df = get_scenario_forecasts()
    if df.empty:
        return ScenarioResponse(data=[], count=0, data_vintage=None)

    if segment:
        df = df[df["segment"] == segment]
    if scenario:
        df = df[df["scenario"] == scenario]

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
        ScenarioForecastRow(
            year=int(r["year"]),
            quarter=int(r["quarter"]),
            segment=str(r["segment"]),
            scenario=str(r["scenario"]),
            point_estimate=float(r[pt_col]),
            ci80_lower=float(r[ci80l]),
            ci80_upper=float(r[ci80u]),
            ci95_lower=float(r[ci95l]),
            ci95_upper=float(r[ci95u]),
            is_forecast=bool(r["is_forecast"]),
        )
        for _, r in df.iterrows()
    ]

    return ScenarioResponse(data=rows, count=len(rows), data_vintage=vintage)
