"""Backtesting diagnostics endpoints."""

from fastapi import APIRouter, Query

from api.data_loader import get_backtesting, get_market_anchors
from api.schemas import DiagnosticsResponse, DiagnosticRow

router = APIRouter(prefix="/api/v1", tags=["diagnostics"])

SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]

# Only show non-circular models — no soft actuals
VALID_MODELS = {"prophet_loo", "ensemble", "ensemble_loo", "naive", "random_walk", "consensus"}


def _build_mape_matrix(non_soft):
    """Segment x Year MAPE values for prophet_loo model."""
    prophet = non_soft[non_soft["model"] == "prophet_loo"]
    matrix = []
    for seg in SEGMENTS:
        seg_rows = prophet[prophet["segment"] == seg]
        entry = {"segment": seg}
        for _, r in seg_rows.iterrows():
            entry[str(int(r["year"]))] = round(float(r["mape"]), 1)
        matrix.append(entry)
    return matrix


def _build_ci_coverage(non_soft):
    """CI80 and CI95 actual coverage vs targets per segment."""
    prophet = non_soft[non_soft["model"] == "prophet_loo"]
    coverage = []
    for seg in SEGMENTS:
        seg_rows = prophet[prophet["segment"] == seg]
        if seg_rows.empty:
            continue
        n = len(seg_rows)
        ci80_actual = float(seg_rows["ci80_covered"].sum()) / n if n > 0 else 0.0
        ci95_actual = float(seg_rows["ci95_covered"].sum()) / n if n > 0 else 0.0
        coverage.append({
            "segment": seg,
            "ci80_target": 0.80,
            "ci80_actual": round(ci80_actual, 2),
            "ci95_target": 0.95,
            "ci95_actual": round(ci95_actual, 2),
        })
    return coverage


def _build_regime_comparison(non_soft):
    """Pre-GenAI (2017-2021) vs Post-GenAI (2022+) MAPE per segment."""
    prophet = non_soft[non_soft["model"] == "prophet_loo"]
    comparison = []
    for seg in SEGMENTS:
        seg_rows = prophet[prophet["segment"] == seg]
        pre = seg_rows[seg_rows["year"] <= 2021]
        post = seg_rows[seg_rows["year"] >= 2022]
        comparison.append({
            "segment": seg,
            "pre_genai_mape": round(float(pre["mape"].mean()), 1) if not pre.empty else None,
            "post_genai_mape": round(float(post["mape"].mean()), 1) if not post.empty else None,
        })
    return comparison


def _build_data_sources(anchors):
    """Data source summary from market anchors."""
    if anchors.empty or "source_list" not in anchors.columns:
        return []

    # Only Q4 rows with actual sources
    q4 = anchors[(anchors["quarter"] == 4) & (anchors["n_sources"] > 0)]

    source_info: dict[str, dict] = {}
    for _, r in q4.iterrows():
        sources = [s.strip() for s in str(r["source_list"]).split(",") if s.strip()]
        for src in sources:
            if src not in source_info:
                source_info[src] = {"segments": set(), "years": set(), "n_entries": 0}
            source_info[src]["segments"].add(str(r["segment"]))
            source_info[src]["years"].add(int(r["estimate_year"]))
            source_info[src]["n_entries"] += 1

    result = []
    for name, info in sorted(source_info.items()):
        years = sorted(info["years"])
        result.append({
            "source_name": name,
            "segments_covered": sorted(info["segments"]),
            "years_covered": f"{years[0]}-{years[-1]}" if len(years) > 1 else str(years[0]),
            "n_entries": info["n_entries"],
        })
    return result


@router.get("/diagnostics", response_model=DiagnosticsResponse)
def list_diagnostics(
    model: str | None = Query(None, description="Filter by model"),
    segment: str | None = Query(None, description="Filter by segment"),
):
    all_bt = get_backtesting()
    if all_bt.empty:
        return DiagnosticsResponse(
            data=[], count=0, summary={},
            mape_matrix=[], ci_coverage=[], regime_comparison=[], data_sources=[],
        )

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

    # New fields for enhanced diagnostics page
    mape_matrix = _build_mape_matrix(non_soft)
    ci_coverage = _build_ci_coverage(non_soft)
    regime_comparison = _build_regime_comparison(non_soft)
    data_sources = _build_data_sources(anchors)

    return DiagnosticsResponse(
        data=rows,
        count=len(rows),
        summary=summary,
        mape_matrix=mape_matrix,
        ci_coverage=ci_coverage,
        regime_comparison=regime_comparison,
        data_sources=data_sources,
    )
