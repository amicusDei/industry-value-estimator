"""Backtesting diagnostics endpoints."""

from fastapi import APIRouter, Query

from api.data_loader import get_backtesting, get_market_anchors
from api.schemas import DiagnosticsResponse, DiagnosticRow

router = APIRouter(prefix="/api/v1", tags=["diagnostics"])

SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]

# Only show non-circular models — no soft actuals
VALID_MODELS = {"prophet_loo", "ensemble", "ensemble_loo", "naive", "random_walk", "consensus"}


@router.get("/diagnostics", response_model=DiagnosticsResponse)
def list_diagnostics(
    model: str | None = Query(None, description="Filter by model"),
    segment: str | None = Query(None, description="Filter by segment"),
):
    all_bt = get_backtesting()
    if all_bt.empty:
        return DiagnosticsResponse(data=[], count=0, summary={})

    # Filter out circular soft actuals globally
    df = all_bt[all_bt["actual_type"] != "soft"].copy()

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

    # Summary: per-model stats (excluding soft actuals)
    non_soft = all_bt[all_bt["actual_type"] != "soft"]
    summary: dict = {}
    for m in sorted(non_soft["model"].unique()):
        m_df = non_soft[non_soft["model"] == m]
        # Per-segment breakdown
        seg_mape = {}
        for seg in SEGMENTS:
            seg_rows = m_df[m_df["segment"] == seg]
            if not seg_rows.empty:
                seg_mape[seg] = round(float(seg_rows["mape"].mean()), 1)
        summary[str(m)] = {
            "mean_mape": round(float(m_df["mape"].mean()), 1),
            "n_folds": len(m_df),
            "per_segment": seg_mape,
        }

    # Data quality: real vs interpolated per segment (using n_sources > 0 as "real")
    anchors = get_market_anchors()
    data_quality = {}
    if not anchors.empty:
        for seg in SEGMENTS:
            seg_df = anchors[anchors["segment"] == seg]
            q4 = seg_df[seg_df["quarter"] == 4] if "quarter" in seg_df.columns else seg_df
            real_q4 = q4[q4["n_sources"] > 0] if "n_sources" in q4.columns else q4[q4["estimated_flag"] == False]
            total_q4 = len(q4)
            real_count = len(real_q4)
            data_quality[seg] = {
                "real_points": real_count,
                "interpolated_points": total_q4 - real_count,
                "total_points": total_q4,
                "real_ratio": round(real_count / total_q4, 2) if total_q4 > 0 else 0,
            }

    # Model coverage per segment
    model_coverage = {}
    for seg in SEGMENTS:
        seg_models = sorted(non_soft[non_soft["segment"] == seg]["model"].unique().tolist())
        has_loo_ensemble = any("ensemble" in m for m in seg_models)
        model_coverage[seg] = {
            "models": seg_models,
            "has_ensemble": has_loo_ensemble,
            "ensemble_note": "" if has_loo_ensemble else "Ensemble LOO not available for this segment",
        }

    summary["_data_quality"] = data_quality
    summary["_model_coverage"] = model_coverage

    return DiagnosticsResponse(data=rows, count=len(rows), summary=summary)
