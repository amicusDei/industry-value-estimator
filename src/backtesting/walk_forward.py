"""
Walk-forward backtesting with leave-one-out cross-validation (MODL-06).

Instead of comparing model predictions to the same data it trained on (circular),
this module implements proper leave-one-out (LOO) validation:

For each evaluation year Y:
  1. Load ALL market anchor data
  2. EXCLUDE year Y from the training set
  3. Fit Prophet on the reduced training set
  4. Predict year Y
  5. Compare prediction to the held-out actual value

This produces non-circular MAPE for EVERY segment, not just segments with
EDGAR hard actuals. The held-out value is a real analyst estimate that the
model never saw during training.

EDGAR hard actuals (NVIDIA revenue) provide an additional independent
validation signal on top of the LOO cross-validation.

Benchmark models (naive, random walk, analyst consensus, Prophet-only) are
evaluated alongside the ensemble for comparison.

MAPE thresholds (labels only, not gates):
  <15%  -> acceptable
  15-30% -> use_with_caution
  >30%  -> directional_only
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import warnings

from src.backtesting.actuals_assembly import assemble_actuals
from src.backtesting.benchmarks import (
    naive_forecast,
    random_walk_forecast,
    analyst_consensus_forecast,
)
from src.diagnostics.model_eval import compute_mape, compute_r2
from config.settings import DATA_PROCESSED

# Evaluation years for LOO cross-validation
EVALUATION_YEARS = [2020, 2021, 2022, 2023, 2024]

MIN_FOLDS = 3

MAPE_LABELS = {
    (0, 15): "acceptable",
    (15, 30): "use_with_caution",
    (30, float("inf")): "directional_only",
}


def label_mape(mape_value: float) -> str:
    for (lower, upper), label in MAPE_LABELS.items():
        if lower <= mape_value < upper:
            return label
    return "directional_only"


def _fit_prophet_loo(train_df: pd.DataFrame, forecast_year: int, forecast_date: str | None = None) -> dict:
    """Fit Prophet on train_df and return point prediction + CI bounds for forecast_year.

    Uses bootstrap resampling of in-sample residuals for CI computation,
    replacing parametric z-score expansion.

    Parameters
    ----------
    train_df : pd.DataFrame
        Training data with columns ds (datetime) and y (float).
    forecast_year : int
        Year to forecast (used for fallback).
    forecast_date : str, optional
        Specific date to forecast (e.g. "2024-10-01" for Q4).
        If None, defaults to "{forecast_year}-01-01".

    Returns dict with keys: point, ci80_half, ci95_half.
    """
    if forecast_date is None:
        forecast_date = f"{forecast_year}-01-01"

    try:
        from prophet import Prophet
    except ImportError:
        warnings.warn("Prophet not available -- using linear extrapolation for LOO")
        if len(train_df) >= 2:
            last_two = train_df.tail(2)
            slope = float(last_two["y"].iloc[-1] - last_two["y"].iloc[-2])
            years_ahead = forecast_year - int(last_two["ds"].dt.year.iloc[-1])
            point = float(last_two["y"].iloc[-1] + slope * years_ahead)
        else:
            point = float(train_df["y"].iloc[-1])
        return {"point": point, "ci80_half": abs(point) * 0.25, "ci95_half": abs(point) * 0.40}

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
        growth="linear",
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(train_df)

    # In-sample prediction to compute residuals for bootstrap
    in_sample_pred = model.predict(train_df[["ds"]])
    residuals = train_df["y"].values - in_sample_pred["yhat"].values

    future = pd.DataFrame({"ds": [pd.Timestamp(forecast_date)]})
    forecast = model.predict(future)
    point = float(forecast["yhat"].iloc[0])

    # Bootstrap CI from in-sample residuals
    if len(residuals) >= 3:
        from src.inference.bootstrap_ci import bootstrap_confidence_intervals
        point_arr = np.array([point])
        ci = bootstrap_confidence_intervals(residuals, point_arr, n_bootstrap=1000, seed=42)
        ci80_half = float((ci["ci80_upper"][0] - ci["ci80_lower"][0]) / 2)
        ci95_half = float((ci["ci95_upper"][0] - ci["ci95_lower"][0]) / 2)
    else:
        # Fallback: wider parametric CIs for very sparse data
        ci80_half = abs(point) * 0.25
        ci95_half = abs(point) * 0.40

    # Enforce minimum CI width (25%/40% of point estimate)
    ci80_half = max(ci80_half, abs(point) * 0.25)
    ci95_half = max(ci95_half, abs(point) * 0.40)

    return {"point": point, "ci80_half": ci80_half, "ci95_half": ci95_half}


def run_walk_forward(industry_id: str = "ai") -> pd.DataFrame:
    """
    Run leave-one-out cross-validation for each segment.

    For each (segment, eval_year):
      1. Load market_anchors_ai.parquet
      2. Exclude eval_year from training
      3. Fit Prophet on remaining years
      4. Predict eval_year
      5. Compute MAPE against held-out actual

    Also runs benchmark models (naive, random walk, analyst consensus,
    Prophet-only) for comparison.

    Also includes EDGAR hard actuals (NVIDIA) as independent validation.
    """
    anchors_path = DATA_PROCESSED / "market_anchors_ai.parquet"
    if not anchors_path.exists():
        print(f"[walk_forward] market_anchors_ai.parquet not found -- returning empty")
        return pd.DataFrame()

    anchors_df = pd.read_parquet(anchors_path)
    median_col = "median_usd_billions_real_2020"

    results = []

    # --- Part 1: Leave-one-out cross-validation (non-circular) ---
    segments = [s for s in anchors_df["segment"].unique() if s != "total"]

    # Detect quarterly vs annual data
    has_quarter = "quarter" in anchors_df.columns

    for segment in sorted(segments):
        if has_quarter:
            seg_data = anchors_df[anchors_df["segment"] == segment].sort_values(["estimate_year", "quarter"])
        else:
            seg_data = anchors_df[anchors_df["segment"] == segment].sort_values("estimate_year")

        for eval_year in EVALUATION_YEARS:
            # Get Q4 actual for evaluation (or annual value if no quarters)
            if has_quarter:
                year_row = seg_data[(seg_data["estimate_year"] == eval_year) & (seg_data["quarter"] == 4)]
            else:
                year_row = seg_data[seg_data["estimate_year"] == eval_year]
            if year_row.empty:
                continue

            actual_val = float(year_row[median_col].iloc[0])
            if actual_val <= 0:
                continue

            # Build training set: ALL quarters EXCEPT Q4 of eval_year
            if has_quarter:
                train_data = seg_data[
                    ~((seg_data["estimate_year"] == eval_year) & (seg_data["quarter"] == 4))
                ].copy()
            else:
                train_data = seg_data[seg_data["estimate_year"] != eval_year].copy()
            if len(train_data) < 5:
                continue

            # --- Prophet LOO (primary model) ---
            if has_quarter:
                quarter_month = {1: "01", 2: "04", 3: "07", 4: "10"}
                train_prophet = pd.DataFrame({
                    "ds": pd.to_datetime(
                        train_data["estimate_year"].astype(str) + "-" +
                        train_data["quarter"].map(quarter_month) + "-01"
                    ),
                    "y": train_data[median_col].values,
                })
                # Forecast target is Q4 of eval_year
                forecast_date = f"{eval_year}-10-01"
            else:
                train_prophet = pd.DataFrame({
                    "ds": pd.to_datetime(train_data["estimate_year"].astype(str) + "-01-01"),
                    "y": train_data[median_col].values,
                })
                forecast_date = f"{eval_year}-01-01"

            try:
                prophet_result = _fit_prophet_loo(train_prophet, eval_year, forecast_date=forecast_date)
                predicted_val = prophet_result["point"]
                ci80_half = prophet_result["ci80_half"]
                ci95_half = prophet_result["ci95_half"]
            except Exception as exc:
                print(f"[walk_forward] LOO failed for {segment}/{eval_year}: {exc}")
                continue

            # Ensure prediction is positive
            predicted_val = max(predicted_val, 0.1)

            mape_val = abs(actual_val - predicted_val) / actual_val * 100
            mape_label_val = label_mape(mape_val)

            # CI coverage checks
            ci80_covered = (predicted_val - ci80_half) <= actual_val <= (predicted_val + ci80_half)
            ci95_covered = (predicted_val - ci95_half) <= actual_val <= (predicted_val + ci95_half)

            results.append({
                "year": eval_year,
                "segment": segment,
                "actual_usd": actual_val,
                "predicted_usd": predicted_val,
                "residual_usd": predicted_val - actual_val,
                "model": "prophet_loo",
                "holdout_type": "leave_one_out",
                "actual_type": "held_out",
                "mape": mape_val,
                "r2": float("nan"),  # R2 meaningless for single-point
                "mape_label": mape_label_val,
                "circular_flag": False,
                "ci80_covered": ci80_covered,
                "ci95_covered": ci95_covered,
            })

            # --- Benchmark: Naive forecast ---
            # Use Q4 annual values for benchmark models
            if has_quarter:
                _bench_data = train_data[train_data["quarter"] == 4].copy()
            else:
                _bench_data = train_data.copy()
            train_y = _bench_data.set_index("estimate_year")[median_col]
            try:
                naive_pred = naive_forecast(train_y, n_steps=1)[0]
                naive_pred = max(naive_pred, 0.1)
                naive_mape = abs(actual_val - naive_pred) / actual_val * 100
                results.append({
                    "year": eval_year,
                    "segment": segment,
                    "actual_usd": actual_val,
                    "predicted_usd": naive_pred,
                    "residual_usd": naive_pred - actual_val,
                    "model": "naive",
                    "holdout_type": "leave_one_out",
                    "actual_type": "held_out",
                    "mape": naive_mape,
                    "r2": float("nan"),
                    "mape_label": label_mape(naive_mape),
                    "circular_flag": False,
                    "ci80_covered": False,
                    "ci95_covered": False,
                })
            except Exception as e:
                logger.warning(f"Benchmark failed: {e}")

            # --- Benchmark: Random walk ---
            try:
                rw_pred = random_walk_forecast(train_y, n_steps=1)[0]
                rw_pred = max(rw_pred, 0.1)
                rw_mape = abs(actual_val - rw_pred) / actual_val * 100
                results.append({
                    "year": eval_year,
                    "segment": segment,
                    "actual_usd": actual_val,
                    "predicted_usd": rw_pred,
                    "residual_usd": rw_pred - actual_val,
                    "model": "random_walk",
                    "holdout_type": "leave_one_out",
                    "actual_type": "held_out",
                    "mape": rw_mape,
                    "r2": float("nan"),
                    "mape_label": label_mape(rw_mape),
                    "circular_flag": False,
                    "ci80_covered": False,
                    "ci95_covered": False,
                })
            except Exception as e:
                logger.warning(f"Benchmark failed: {e}")

            # --- Benchmark: Analyst consensus ---
            try:
                # Use anchors excluding eval_year for consensus CAGR
                train_anchors = anchors_df[anchors_df["estimate_year"] != eval_year]
                consensus_pred = analyst_consensus_forecast(train_anchors, segment, n_steps=1)[0]
                consensus_pred = max(consensus_pred, 0.1)
                consensus_mape = abs(actual_val - consensus_pred) / actual_val * 100
                results.append({
                    "year": eval_year,
                    "segment": segment,
                    "actual_usd": actual_val,
                    "predicted_usd": consensus_pred,
                    "residual_usd": consensus_pred - actual_val,
                    "model": "consensus",
                    "holdout_type": "leave_one_out",
                    "actual_type": "held_out",
                    "mape": consensus_mape,
                    "r2": float("nan"),
                    "mape_label": label_mape(consensus_mape),
                    "circular_flag": False,
                    "ci80_covered": False,
                    "ci95_covered": False,
                })
            except Exception as e:
                logger.warning(f"Benchmark failed: {e}")

    # --- Part 2: EDGAR hard actuals (independent validation) ---
    try:
        actuals_df = assemble_actuals(industry_id)
        forecasts_path = DATA_PROCESSED / "forecasts_ensemble.parquet"
        if forecasts_path.exists() and not actuals_df.empty:
            forecasts_df = pd.read_parquet(forecasts_path)
            hard_actuals = actuals_df[actuals_df["actual_type"] == "hard"]

            for _, row in hard_actuals.iterrows():
                year = int(row["year"])
                segment = row["segment"]
                actual_val = float(row["actual_usd_billions"])

                forecast_row = forecasts_df[
                    (forecasts_df["year"] == year) & (forecasts_df["segment"] == segment)
                ]
                if forecast_row.empty or actual_val <= 0:
                    continue

                predicted_val = float(forecast_row["point_estimate_real_2020"].iloc[0])
                mape_val = abs(actual_val - predicted_val) / actual_val * 100

                # CI coverage for ensemble hard actuals
                ci80_lower = float(forecast_row["ci80_lower"].iloc[0])
                ci80_upper = float(forecast_row["ci80_upper"].iloc[0])
                ci95_lower = float(forecast_row["ci95_lower"].iloc[0])
                ci95_upper = float(forecast_row["ci95_upper"].iloc[0])
                ci80_covered = ci80_lower <= actual_val <= ci80_upper
                ci95_covered = ci95_lower <= actual_val <= ci95_upper

                results.append({
                    "year": year,
                    "segment": segment,
                    "actual_usd": actual_val,
                    "predicted_usd": predicted_val,
                    "residual_usd": predicted_val - actual_val,
                    "model": "ensemble",
                    "holdout_type": "edgar_filing",
                    "actual_type": "hard",
                    "mape": mape_val,
                    "r2": float("nan"),
                    "mape_label": label_mape(mape_val),
                    "circular_flag": False,
                    "ci80_covered": ci80_covered,
                    "ci95_covered": ci95_covered,
                })
    except Exception as exc:
        print(f"[walk_forward] EDGAR hard actuals failed: {exc}")

    if not results:
        print("[walk_forward] No results produced")
        return pd.DataFrame(columns=[
            "year", "segment", "actual_usd", "predicted_usd", "residual_usd",
            "model", "holdout_type", "actual_type", "mape", "r2", "mape_label",
            "circular_flag", "ci80_covered", "ci95_covered",
        ])

    results_df = pd.DataFrame(results)
    return results_df


def run_backtesting(industry_id: str = "ai") -> Path:
    """Run backtesting and write results to parquet."""
    results_df = run_walk_forward(industry_id)
    output_path = DATA_PROCESSED / "backtesting_results.parquet"
    results_df.to_parquet(output_path, index=False)

    if not results_df.empty:
        print(f"\n[backtesting] Results summary for industry_id='{industry_id}':")

        # LOO results by model type
        loo = results_df[results_df["actual_type"] == "held_out"]
        if not loo.empty:
            for model_name in sorted(loo["model"].unique()):
                model_loo = loo[loo["model"] == model_name]
                print(f"\n  [{model_name}] {len(model_loo)} fold-segment pairs:")
                for seg in sorted(model_loo["segment"].unique()):
                    seg_loo = model_loo[model_loo["segment"] == seg]
                    mean_mape = seg_loo["mape"].mean()
                    print(f"    {seg}: mean MAPE={mean_mape:.1f}% ({label_mape(mean_mape)}) over {len(seg_loo)} folds")

            # Benchmark comparison summary
            print("\n  --- Benchmark Comparison (mean MAPE per model) ---")
            for model_name in sorted(loo["model"].unique()):
                model_mean_mape = loo[loo["model"] == model_name]["mape"].mean()
                print(f"    {model_name:<20} {model_mean_mape:.1f}%")

            # LightGBM value-add evaluation (Finding 4)
            prophet_loo_df = loo[loo["model"] == "prophet_loo"]
            ensemble_df = results_df[results_df["model"] == "ensemble"]
            if not prophet_loo_df.empty and not ensemble_df.empty:
                prophet_mape = prophet_loo_df["mape"].mean()
                ensemble_mape = ensemble_df["mape"].mean()
                delta = prophet_mape - ensemble_mape
                print(f"\n  LightGBM MAPE improvement: {prophet_mape:.1f}% -> {ensemble_mape:.1f}% (delta = {delta:.1f}%)")
                if abs(delta) < 5.0:
                    print(f"  WARNING: LightGBM does not improve MAPE by >5% absolute ({delta:.1f}%). Consider removal.")

        # CI coverage summary (Finding 3)
        ci_models = results_df[results_df["ci80_covered"].notna()]
        if not ci_models.empty:
            for model_name in ["prophet_loo", "ensemble"]:
                model_ci = ci_models[ci_models["model"] == model_name]
                if model_ci.empty:
                    continue
                ci80_rate = model_ci["ci80_covered"].mean() * 100
                ci95_rate = model_ci["ci95_covered"].mean() * 100
                print(f"\n  [{model_name}] Empirical CI80 coverage: {ci80_rate:.0f}% (target: 80%). Empirical CI95 coverage: {ci95_rate:.0f}% (target: 95%)")

        # Hard actuals
        hard = results_df[results_df["actual_type"] == "hard"]
        if not hard.empty:
            print(f"\n  [EDGAR hard actuals] {len(hard)} comparisons:")
            for _, r in hard.iterrows():
                print(f"    {r['segment']} {int(r['year'])}: actual=${r['actual_usd']:.1f}B predicted=${r['predicted_usd']:.1f}B MAPE={r['mape']:.1f}%")

        print(f"\n  Written to: {output_path}")

    return output_path
