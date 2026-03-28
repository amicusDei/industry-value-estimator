"""Backtesting diagnostics endpoints."""

from fastapi import APIRouter, Query

from api.data_loader import get_backtesting, get_market_anchors
from api.schemas import DiagnosticsResponse, DiagnosticRow

router = APIRouter(prefix="/api/v1", tags=["diagnostics"])

SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]


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

    # Summary: per-model stats
    all_bt = get_backtesting()
    summary: dict = {}
    for m in all_bt["model"].unique():
        m_df = all_bt[all_bt["model"] == m]
        summary[str(m)] = {"mean_mape": round(float(m_df["mape"].mean()), 1), "n_folds": len(m_df)}

    # Data quality: real vs interpolated per segment
    anchors = get_market_anchors()
    data_quality = {}
    if not anchors.empty:
        for seg in SEGMENTS:
            seg_df = anchors[anchors["segment"] == seg]
            real = int((seg_df["estimated_flag"] == False).sum())
            total = len(seg_df)
            data_quality[seg] = {"real_points": real, "interpolated_points": total - real, "total_points": total}

    # Model coverage: which models have results per segment
    model_coverage = {}
    for seg in SEGMENTS:
        seg_models = sorted(all_bt[all_bt["segment"] == seg]["model"].unique().tolist())
        has_ensemble = "ensemble" in seg_models
        model_coverage[seg] = {
            "models": seg_models,
            "has_ensemble": has_ensemble,
            "ensemble_note": "" if has_ensemble else "No EDGAR hard actuals for this segment — ensemble comparison requires independent validation data",
        }

    summary["_data_quality"] = data_quality
    summary["_model_coverage"] = model_coverage

    return DiagnosticsResponse(data=rows, count=len(rows), summary=summary)
