"""Data quality transparency endpoint for institutional audiences."""

from fastapi import APIRouter

from api.data_loader import get_forecasts, get_market_anchors, get_backtesting

router = APIRouter(prefix="/api/v1", tags=["data_quality"])

SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]
CAGR_FLOORS = {"ai_hardware": 0.15, "ai_infrastructure": 0.25, "ai_software": 0.20, "ai_adoption": 0.15}


@router.get("/data-quality")
def data_quality():
    anchors = get_market_anchors()
    bt = get_backtesting()
    fc = get_forecasts()

    per_segment = {}
    for seg in SEGMENTS:
        # Data quality from anchors
        seg_anch = anchors[anchors["segment"] == seg] if not anchors.empty else anchors
        real = seg_anch[seg_anch["estimated_flag"] == False] if not seg_anch.empty else seg_anch
        real_q4 = real[real["quarter"] == 4] if "quarter" in real.columns and not real.empty else real

        real_points = len(real)
        total_points = len(seg_anch)
        real_ratio = real_points / total_points if total_points > 0 else 0

        earliest_real = int(real_q4["estimate_year"].min()) if not real_q4.empty else None
        latest_real = int(real_q4["estimate_year"].max()) if not real_q4.empty else None
        n_firms = int(real_q4["n_sources"].max()) if not real_q4.empty and "n_sources" in real_q4.columns else 0

        # Backtesting metrics
        seg_bt_loo = bt[(bt["segment"] == seg) & (bt["model"] == "prophet_loo")] if not bt.empty else bt
        bt_mape = round(float(seg_bt_loo["mape"].mean()), 1) if not seg_bt_loo.empty else None
        ci80_cov = round(float(seg_bt_loo["ci80_covered"].mean()), 2) if not seg_bt_loo.empty else None
        ci95_cov = round(float(seg_bt_loo["ci95_covered"].mean()), 2) if not seg_bt_loo.empty else None

        # CAGR source
        cagr_source = "calibration_floor"  # All segments currently floor-constrained
        if not fc.empty and "quarter" in fc.columns:
            q4_25 = fc[(fc["segment"] == seg) & (fc["year"] == 2025) & (fc["quarter"] == 4)]
            q4_30 = fc[(fc["segment"] == seg) & (fc["year"] == 2030) & (fc["quarter"] == 4)]
            if not q4_25.empty and not q4_30.empty:
                v_s = float(q4_25["point_estimate_real_2020"].iloc[0])
                v_e = float(q4_30["point_estimate_real_2020"].iloc[0])
                if v_s > 0:
                    cagr = (v_e / v_s) ** 0.2 - 1
                    floor = CAGR_FLOORS.get(seg, 0.15)
                    if cagr > floor + 0.01:
                        cagr_source = "model"

        per_segment[seg] = {
            "real_data_points": real_points,
            "interpolated_data_points": total_points - real_points,
            "real_data_ratio": round(real_ratio, 2),
            "earliest_real_year": earliest_real,
            "latest_real_year": latest_real,
            "n_analyst_firms": n_firms,
            "backtesting_mape": bt_mape,
            "backtesting_model": "prophet_loo",
            "ci80_coverage": ci80_cov,
            "ci95_coverage": ci95_cov,
            "cagr_source": cagr_source,
        }

    return {
        "per_segment": per_segment,
        "methodology_caveats": [
            "75-85% of training data is interpolated from annual analyst estimates",
            "CI coverage validated via leave-one-out cross-validation (CI80: 90%, CI95: 100%)",
            "CAGR floors from analyst consensus override model when model underperforms",
            "Ensemble weights based on Prophet residual RMSE (not in-sample std)",
            "ai_software 2024 growth spike (+111%) due to scope-mixing between CB Insights and Precedence Research",
        ],
    }
