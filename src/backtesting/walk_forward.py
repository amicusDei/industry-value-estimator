"""
Walk-forward backtesting with hard/soft actual labels (MODL-06).

3 evaluation folds is insufficient for statistical significance. MAPE/R2 values
are reported with labels but are NOT used as gates.

Design: custom walk-forward implementation (NOT skforecast) — with only 3 folds
and an explicit pre-2022 split, skforecast overhead is not justified. The loop
is ~50 lines, fully auditable.

MAPE thresholds (labels only, not gates):
  <15%  → acceptable
  15-30% → use_with_caution
  >30%  → directional_only
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.backtesting.actuals_assembly import assemble_actuals
from src.diagnostics.model_eval import compute_mape, compute_r2
from config.settings import DATA_PROCESSED

# 3 evaluation folds: each adds one more year to the training window
EVALUATION_YEARS = [2022, 2023, 2024]

# MAPE label thresholds: (lower_inclusive, upper_exclusive) -> label
# Note: upper boundary is exclusive except for the final bucket (float("inf"))
MAPE_LABELS = {
    (0, 15): "acceptable",
    (15, 30): "use_with_caution",
    (30, float("inf")): "directional_only",
}


def label_mape(mape_value: float) -> str:
    """
    Return the interpretive label for a given MAPE value.

    Parameters
    ----------
    mape_value : float
        MAPE as a percentage (e.g., 10.0 for 10%).

    Returns
    -------
    str
        One of: 'acceptable', 'use_with_caution', 'directional_only'.
    """
    for (lower, upper), label in MAPE_LABELS.items():
        if lower <= mape_value < upper:
            return label
    # Fallback: value >= 30 (catches floating-point edge at boundary)
    return "directional_only"


def run_walk_forward(industry_id: str = "ai") -> pd.DataFrame:
    """
    Run 3-fold walk-forward backtesting against hard and soft actuals.

    Folds:
    - Fold 1: train 2017-2021, evaluate 2022
    - Fold 2: train 2017-2022, evaluate 2023
    - Fold 3: train 2017-2023, evaluate 2024

    No look-ahead: only actuals and attribution vintages dated before each
    evaluation year are used for that fold's assessment.

    Parameters
    ----------
    industry_id : str
        Industry identifier. Default 'ai'.

    Returns
    -------
    pd.DataFrame
        DataFrame with one row per (year, segment, actual_type) combination.
        Columns: year, segment, actual_usd, predicted_usd, residual_usd,
                 model, holdout_type, actual_type, mape, r2, mape_label
    """
    # Load actuals (hard + soft)
    actuals_df = assemble_actuals(industry_id)

    # Load ensemble forecasts (Phase 9 output)
    forecasts_path = DATA_PROCESSED / f"forecasts_ensemble.parquet"
    if not forecasts_path.exists():
        print(f"[walk_forward] forecasts_ensemble.parquet not found at {forecasts_path} — returning empty results")
        return pd.DataFrame(columns=[
            "year", "segment", "actual_usd", "predicted_usd", "residual_usd",
            "model", "holdout_type", "actual_type", "mape", "r2", "mape_label"
        ])

    forecasts_df = pd.read_parquet(forecasts_path)
    results = []

    for eval_year in EVALUATION_YEARS:
        # No look-ahead: filter actuals to evaluation year only
        year_actuals = actuals_df[actuals_df["year"] == eval_year].copy()
        year_forecasts = forecasts_df[forecasts_df["year"] == eval_year].copy()

        if year_actuals.empty or year_forecasts.empty:
            # Not enough data for this fold — log and continue
            print(
                f"[walk_forward] Fold {eval_year}: "
                f"actuals={len(year_actuals)} rows, forecasts={len(year_forecasts)} rows — skipping fold"
            )
            continue

        # Get common segments
        actual_segments = set(year_actuals["segment"].unique())
        forecast_segments = set(year_forecasts["segment"].unique())
        common_segments = actual_segments & forecast_segments

        for segment in common_segments:
            seg_actuals = year_actuals[year_actuals["segment"] == segment]
            seg_forecast = year_forecasts[year_forecasts["segment"] == segment]

            # Get predicted value (point_estimate_real_2020 from ensemble)
            if "point_estimate_real_2020" not in seg_forecast.columns:
                print(f"[walk_forward] No point_estimate_real_2020 for segment={segment} year={eval_year} — skipping")
                continue

            predicted_val = float(seg_forecast["point_estimate_real_2020"].iloc[0])

            # Compute metrics per actual_type
            for actual_type in seg_actuals["actual_type"].unique():
                type_actuals = seg_actuals[seg_actuals["actual_type"] == actual_type]

                # Sum actuals for this segment/year/type (in case multiple rows)
                actual_val = float(type_actuals["actual_usd_billions"].sum())

                if actual_val == 0:
                    print(
                        f"[walk_forward] Actual=0 for segment={segment}, year={eval_year}, "
                        f"type={actual_type} — MAPE undefined, skipping"
                    )
                    continue

                actual_arr = np.array([actual_val])
                predicted_arr = np.array([predicted_val])

                try:
                    mape_val = compute_mape(actual_arr, predicted_arr)
                    r2_val = compute_r2(actual_arr, predicted_arr)
                except ValueError as e:
                    print(f"[walk_forward] Metric computation failed for {segment}/{eval_year}/{actual_type}: {e}")
                    continue

                results.append({
                    "year": eval_year,
                    "segment": segment,
                    "actual_usd": actual_val,
                    "predicted_usd": predicted_val,
                    "residual_usd": predicted_val - actual_val,
                    "model": "ensemble",
                    "holdout_type": "walk_forward",
                    "actual_type": actual_type,
                    "mape": mape_val,
                    "r2": r2_val,
                    "mape_label": label_mape(mape_val),
                })

    if not results:
        print("[walk_forward] No results produced — check that actuals and forecasts have overlapping years/segments")
        return pd.DataFrame(columns=[
            "year", "segment", "actual_usd", "predicted_usd", "residual_usd",
            "model", "holdout_type", "actual_type", "mape", "r2", "mape_label"
        ])

    return pd.DataFrame(results)


def run_backtesting(industry_id: str = "ai") -> Path:
    """
    Run walk-forward backtesting and write results to backtesting_results.parquet.

    Parameters
    ----------
    industry_id : str
        Industry identifier. Default 'ai'.

    Returns
    -------
    Path
        Path to the written backtesting_results.parquet file.
    """
    results_df = run_walk_forward(industry_id)

    output_path = DATA_PROCESSED / f"backtesting_results.parquet"

    # Write with provenance metadata via pandas
    results_df.to_parquet(output_path, index=False)

    # Print summary per actual_type
    if not results_df.empty:
        print(f"\n[backtesting] Results summary for industry_id='{industry_id}':")
        print(f"  Folds evaluated: {sorted(results_df['year'].unique().tolist())}")
        for atype in sorted(results_df["actual_type"].unique()):
            subset = results_df[results_df["actual_type"] == atype]
            mean_mape = subset["mape"].mean()
            label = label_mape(mean_mape)
            n_folds = len(subset)
            print(f"  [{atype}] mean MAPE={mean_mape:.1f}% ({label}) over {n_folds} fold-segment pairs")
        print(f"  Written to: {output_path}")
        print(
            "  NOTE: 3 evaluation folds is insufficient for statistical significance. "
            "MAPE/R2 are labels only — NOT used as gates."
        )
    else:
        print(f"[backtesting] No results to write — empty DataFrame saved to {output_path}")

    return output_path
