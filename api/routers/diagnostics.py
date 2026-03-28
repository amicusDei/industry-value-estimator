"""Backtesting diagnostics endpoints."""

from fastapi import APIRouter, Query

from api.data_loader import get_backtesting
from api.schemas import DiagnosticsResponse, DiagnosticRow

router = APIRouter(prefix="/api/v1", tags=["diagnostics"])


@router.get("/diagnostics", response_model=DiagnosticsResponse)
def list_diagnostics(
    model: str | None = Query(None, description="Filter by model"),
    segment: str | None = Query(None, description="Filter by segment"),
):
    df = get_backtesting()
    if df.empty:
        return DiagnosticsResponse(data=[], count=0, summary={})

    if model:
        df = df[df["model"] == model]
    if segment:
        df = df[df["segment"] == segment]

    rows = [
        DiagnosticRow(
            year=int(r["year"]),
            segment=str(r["segment"]),
            model=str(r["model"]),
            mape=float(r["mape"]),
            actual_usd=float(r["actual_usd"]),
            predicted_usd=float(r["predicted_usd"]),
            regime_label=str(r["regime_label"]) if "regime_label" in r and r.get("regime_label") else None,
        )
        for _, r in df.iterrows()
    ]

    # Summary statistics
    all_bt = get_backtesting()
    summary = {}
    for m in all_bt["model"].unique():
        m_df = all_bt[all_bt["model"] == m]
        summary[str(m)] = {"mean_mape": round(float(m_df["mape"].mean()), 1), "n_folds": len(m_df)}

    return DiagnosticsResponse(data=rows, count=len(rows), summary=summary)
