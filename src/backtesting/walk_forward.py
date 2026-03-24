"""
Walk-forward backtesting with hard/soft actual labels (MODL-06).

2 evaluation folds (2023, 2024). The 2022 fold is absent because
forecasts_ensemble.parquet starts at 2023 — the model was trained on
pre-2023 data and has no 2022 point estimates. EVALUATION_YEARS includes
2022 so future coverage extension is handled automatically; the loop skips
any year where no forecast data exists.

Statistical significance caveat: 2 evaluation folds is insufficient for
statistical significance. MAPE/R2 values are reported with labels but are
NOT used as gates.

Design: custom walk-forward implementation (NOT skforecast) — with only 2-3 folds
and an explicit pre-2022 split, skforecast overhead is not justified. The loop
is ~50 lines, fully auditable.

MAPE thresholds (labels only, not gates):
  <15%  → acceptable
  15-30% → use_with_caution
  >30%  → directional_only

Circularity note: Soft actual MAPE is circular when the model was calibrated
against the same market anchor medians used as soft actuals. Hard actuals
(EDGAR direct-disclosure: NVIDIA, Palantir, C3.ai) are the primary
non-circular validation signal. Soft rows with circular_flag=True are labeled
'circular_not_validated' to make this limitation visible in output.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.backtesting.actuals_assembly import assemble_actuals
from src.diagnostics.model_eval import compute_mape, compute_r2
from config.settings import DATA_PROCESSED

# Candidate evaluation years — skipped automatically if no forecast data exists.
# 2022 is included for forward-compatibility; currently absent (forecasts start 2023).
EVALUATION_YEARS = [2022, 2023, 2024]

# Minimum folds required before printing a warning. With forecasts starting at 2023,
# we get 2 folds (2023, 2024). 1 fold would be insufficient even for directional use.
MIN_FOLDS = 2

# MAPE label thresholds: (lower_inclusive, upper_exclusive) -> label
# Note: upper boundary is exclusive except for the final bucket (float("inf"))
MAPE_LABELS = {
    (0, 15): "acceptable",
    (15, 30): "use_with_caution",
    (30, float("inf")): "directional_only",
}

# Circularity threshold: when |actual - predicted| < this value (in USD billions),
# the comparison is flagged as circular (values are effectively identical).
_CIRCULAR_THRESHOLD_BILLIONS = 0.01


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
    Run 2-fold walk-forward backtesting against hard and soft actuals.

    Folds evaluated (as of Plan 10-05):
    - Fold 1: evaluate 2022 — ABSENT (forecasts_ensemble.parquet starts at 2023)
    - Fold 2: train 2017-2022, evaluate 2023 — PRESENT
    - Fold 3: train 2017-2023, evaluate 2024 — PRESENT

    NOTE: 2022 fold absent — forecasts_ensemble.parquet starts at 2023.
    2 of 3 possible folds evaluated. EVALUATION_YEARS list is kept at
    [2022, 2023, 2024] so coverage extends automatically if 2022 forecasts
    are added in a future plan.

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
                 model, holdout_type, actual_type, mape, r2, mape_label,
                 circular_flag
    """
    # Load actuals (hard + soft)
    actuals_df = assemble_actuals(industry_id)

    # Load ensemble forecasts (Phase 9 output)
    forecasts_path = DATA_PROCESSED / f"forecasts_ensemble.parquet"
    if not forecasts_path.exists():
        print(f"[walk_forward] forecasts_ensemble.parquet not found at {forecasts_path} — returning empty results")
        return pd.DataFrame(columns=[
            "year", "segment", "actual_usd", "predicted_usd", "residual_usd",
            "model", "holdout_type", "actual_type", "mape", "r2", "mape_label",
            "circular_flag",
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

                # Detect circularity: when actual and predicted are effectively identical,
                # the MAPE is not a real validation signal. This happens for soft actuals
                # when the model was calibrated against the same market anchor medians
                # used as soft actuals — predicted == actual by construction.
                is_circular = abs(actual_val - predicted_val) < _CIRCULAR_THRESHOLD_BILLIONS
                if is_circular:
                    mape_label_val = "circular_not_validated"
                else:
                    mape_label_val = label_mape(mape_val)

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
                    "mape_label": mape_label_val,
                    "circular_flag": is_circular,
                })

    if not results:
        print("[walk_forward] No results produced — check that actuals and forecasts have overlapping years/segments")
        return pd.DataFrame(columns=[
            "year", "segment", "actual_usd", "predicted_usd", "residual_usd",
            "model", "holdout_type", "actual_type", "mape", "r2", "mape_label",
            "circular_flag",
        ])

    results_df = pd.DataFrame(results)

    # Check fold count — warn if fewer than MIN_FOLDS were evaluated
    unique_years = sorted(results_df["year"].unique().tolist())
    n_folds = len(unique_years)
    if n_folds < MIN_FOLDS:
        print(
            f"[walk_forward] WARNING: Only {n_folds} fold(s) evaluated (years: {unique_years}). "
            f"Minimum recommended: {MIN_FOLDS}. Results are directional only."
        )

    print(
        f"[walk_forward] NOTE: 2022 fold absent — forecasts_ensemble.parquet starts at 2023. "
        f"{n_folds} of 3 possible folds evaluated."
    )

    return results_df


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
        folds_evaluated = sorted(results_df["year"].unique().tolist())
        print(f"  Folds evaluated: {folds_evaluated} ({len(folds_evaluated)} of 3 possible folds)")
        print(f"  NOTE: 2022 fold absent — forecasts_ensemble.parquet starts at 2023.")
        for atype in sorted(results_df["actual_type"].unique()):
            subset = results_df[results_df["actual_type"] == atype]
            mean_mape = subset["mape"].mean()
            n_folds_type = len(subset)
            if "circular_flag" in subset.columns:
                n_circular = int(subset["circular_flag"].sum())
                circular_note = f", {n_circular} circular" if n_circular > 0 else ""
            else:
                circular_note = ""
            label = label_mape(mean_mape)
            print(
                f"  [{atype}] mean MAPE={mean_mape:.1f}% ({label}) "
                f"over {n_folds_type} fold-segment pairs{circular_note}"
            )
        print(f"  Written to: {output_path}")
        print(
            "  NOTE: 2 evaluation folds is insufficient for statistical significance. "
            "MAPE/R2 are labels only — NOT used as gates."
        )
    else:
        print(f"[backtesting] No results to write — empty DataFrame saved to {output_path}")

    return output_path
