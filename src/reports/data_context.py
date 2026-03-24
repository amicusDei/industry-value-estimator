"""
Report data context loader.

Loads forecast artifacts and computes all metrics needed for PDF report rendering.
The returned dict is passed directly to Jinja2 templates.

Functions
---------
load_report_context : Load forecast data and compute context values for report rendering.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.settings import DATA_PROCESSED


def load_report_context(mode: str = "normal") -> dict:
    """
    Load forecast data and compute report context values.

    Reads forecasts_ensemble.parquet and residuals_statistical.parquet from
    DATA_PROCESSED. Loads config/industries/ai.yaml for segment metadata and
    source attribution. Computes USD headline metrics using the same value chain
    multiplier logic as src/dashboard/app.py.

    Parameters
    ----------
    mode : str
        "normal" — standard report context (default).
        "expert" — includes additional diagnostic fields: RMSE per segment,
        model types, residual statistics.

    Returns
    -------
    dict
        Context dict with keys:
        - segments : list[str] — segment IDs
        - segment_display : dict[str, str] — segment_id -> display name
        - forecasts_df : pd.DataFrame — full forecasts with USD columns attached
        - residuals_df : pd.DataFrame — statistical residuals
        - source_attribution : dict[str, str] — data source strings
        - fan_chart_uris : dict[str, str] — segment -> data URI
        - backtest_chart_uris : dict[str, str] — segment -> data URI (expert only)
        - shap_uri : str — SHAP image data URI
        - headline_metrics : dict — global totals (2024 and 2030 USD billions, CAGR)
        - per_segment_metrics : dict[str, dict] — per-segment metrics
        - vintage : str — data vintage year string
        - generation_date : str — ISO 8601 generation date
        Additional keys when mode="expert":
        - segment_rmse : dict[str, float] — RMSE per segment
        - segment_model_types : dict[str, str] — model type per segment
        - residual_statistics : dict[str, dict] — mean, std, min, max per segment
    """
    # --- Load data ---
    forecasts_df = pd.read_parquet(DATA_PROCESSED / "forecasts_ensemble.parquet")
    residuals_df = pd.read_parquet(DATA_PROCESSED / "residuals_statistical.parquet")

    # --- Load AI config ---
    config_path = _PROJECT_ROOT / "config" / "industries" / "ai.yaml"
    with open(config_path) as f:
        ai_config = yaml.safe_load(f)

    source_attribution: dict[str, str] = ai_config["source_attribution"]
    segments: list[str] = [seg["id"] for seg in ai_config["segments"]]
    segment_display: dict[str, str] = {
        seg["id"]: seg["display_name"] for seg in ai_config["segments"]
    }

    # --- Minimal pass-through — point_estimate_real_2020 IS USD billions in v1.1 ---
    # These alias columns prevent downstream template crashes until Phase 11.
    forecasts_df = forecasts_df.copy()
    forecasts_df["usd_point"] = forecasts_df["point_estimate_real_2020"]
    forecasts_df["usd_ci80_lower"] = forecasts_df["ci80_lower"]
    forecasts_df["usd_ci80_upper"] = forecasts_df["ci80_upper"]
    forecasts_df["usd_ci95_lower"] = forecasts_df["ci95_lower"]
    forecasts_df["usd_ci95_upper"] = forecasts_df["ci95_upper"]

    # --- Per-segment metrics ---
    per_segment_metrics: dict[str, dict] = {}
    for seg in segments:
        seg_df = forecasts_df[forecasts_df["segment"] == seg].sort_values("year")

        # 2024 — most recent historical year with data
        row_2024 = seg_df[seg_df["year"] == 2024]
        val_2024 = float(row_2024["usd_point"].iloc[0]) if len(row_2024) > 0 else 0.0

        # 2030 forecast
        row_2030 = seg_df[seg_df["year"] == 2030]
        val_2030 = float(row_2030["usd_point"].iloc[0]) if len(row_2030) > 0 else 0.0
        ci80_lower_2030 = float(row_2030["usd_ci80_lower"].iloc[0]) if len(row_2030) > 0 else 0.0
        ci80_upper_2030 = float(row_2030["usd_ci80_upper"].iloc[0]) if len(row_2030) > 0 else 0.0
        ci95_lower_2030 = float(row_2030["usd_ci95_lower"].iloc[0]) if len(row_2030) > 0 else 0.0
        ci95_upper_2030 = float(row_2030["usd_ci95_upper"].iloc[0]) if len(row_2030) > 0 else 0.0

        # CAGR 2024-2030
        cagr = (
            ((val_2030 / val_2024) ** (1 / 6) - 1) * 100
            if val_2024 > 0 and val_2030 > 0
            else 0.0
        )

        per_segment_metrics[seg] = {
            "display_name": segment_display[seg],
            "val_2024": val_2024,
            "val_2030": val_2030,
            "cagr_pct": cagr,
            "ci80_lower_2030": ci80_lower_2030,
            "ci80_upper_2030": ci80_upper_2030,
            "ci95_lower_2030": ci95_lower_2030,
            "ci95_upper_2030": ci95_upper_2030,
        }

    # --- Headline metrics (global totals) ---
    total_2024 = sum(m["val_2024"] for m in per_segment_metrics.values())
    total_2030 = sum(m["val_2030"] for m in per_segment_metrics.values())
    global_cagr = (
        ((total_2030 / total_2024) ** (1 / 6) - 1) * 100
        if total_2024 > 0 and total_2030 > 0
        else 0.0
    )

    # Global 2030 CI totals
    total_ci80_lower = sum(m["ci80_lower_2030"] for m in per_segment_metrics.values())
    total_ci80_upper = sum(m["ci80_upper_2030"] for m in per_segment_metrics.values())
    total_ci95_lower = sum(m["ci95_lower_2030"] for m in per_segment_metrics.values())
    total_ci95_upper = sum(m["ci95_upper_2030"] for m in per_segment_metrics.values())

    headline_metrics = {
        "total_2024": total_2024,
        "total_2030": total_2030,
        "global_cagr_pct": global_cagr,
        "ci80_lower_2030": total_ci80_lower,
        "ci80_upper_2030": total_ci80_upper,
        "ci95_lower_2030": total_ci95_lower,
        "ci95_upper_2030": total_ci95_upper,
    }

    # --- Chart exports ---
    from src.reports.chart_export import export_fan_charts, export_shap_image

    fan_chart_uris = export_fan_charts(forecasts_df, segments, usd_mode=True)
    shap_uri = export_shap_image()

    # --- Vintage / generation date ---
    hist_years = forecasts_df[forecasts_df["is_forecast"] == False]["year"]  # noqa: E712
    vintage = str(int(hist_years.max())) if len(hist_years) > 0 else "2024"
    generation_date = date.today().isoformat()

    context = {
        "segments": segments,
        "segment_display": segment_display,
        "forecasts_df": forecasts_df,
        "residuals_df": residuals_df,
        "source_attribution": source_attribution,
        "fan_chart_uris": fan_chart_uris,
        "fan_chart_all": fan_chart_uris.get("all", ""),
        "backtest_chart_uris": {},  # populated in expert mode below
        "shap_uri": shap_uri,
        "headline_metrics": headline_metrics,
        "per_segment_metrics": per_segment_metrics,
        "vintage": vintage,
        "generation_date": generation_date,
    }

    # --- Expert mode extras ---
    if mode == "expert":
        from src.reports.chart_export import export_backtest_charts

        backtest_chart_uris = export_backtest_charts(residuals_df, segments)
        context["backtest_chart_uris"] = backtest_chart_uris

        # RMSE per segment
        segment_rmse: dict[str, float] = {}
        residual_statistics: dict[str, dict] = {}
        segment_model_types: dict[str, str] = {}

        for seg in segments:
            seg_res = residuals_df[residuals_df["segment"] == seg]["residual"].to_numpy()
            if len(seg_res) > 0:
                segment_rmse[seg] = float(np.sqrt(np.mean(seg_res**2)))
                residual_statistics[seg] = {
                    "mean": float(np.mean(seg_res)),
                    "std": float(np.std(seg_res)),
                    "min": float(np.min(seg_res)),
                    "max": float(np.max(seg_res)),
                    "n": len(seg_res),
                }
            else:
                segment_rmse[seg] = 0.0
                residual_statistics[seg] = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "n": 0}

            # Extract model type from residuals if column exists
            if "model_type" in residuals_df.columns:
                seg_types = residuals_df[residuals_df["segment"] == seg]["model_type"].unique()
                segment_model_types[seg] = seg_types[0] if len(seg_types) > 0 else "unknown"
            else:
                segment_model_types[seg] = "unknown"

        context["segment_rmse"] = segment_rmse
        context["segment_model_types"] = segment_model_types
        context["residual_statistics"] = residual_statistics

    return context
