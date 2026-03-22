"""
Ensemble ML pipeline runner.

Trains LightGBM point and quantile models on statistical residuals, builds
the ensemble, forecasts to 2030, computes SHAP, serializes models, and saves
forecasts to:

    data/processed/forecasts_ensemble.parquet

This file is the Phase 4 dashboard's primary data source. Run it with:

    uv run python scripts/run_ensemble_pipeline.py

Prerequisites
-------------
- Run `uv run python scripts/run_statistical_pipeline.py` first to produce
  data/processed/residuals_statistical.parquet.

Design notes
------------
- Synthetic data from residuals_statistical.parquet (Phase 2 output)
- Feature engineering via build_residual_features (lag1, lag2, year_norm)
- LightGBM CV for per-segment RMSE evaluation
- Statistical baseline RMSE derived as std(residuals) — the statistical model's
  forecast of its own residuals is zero, so residual std is the baseline RMSE
- Inverse-RMSE ensemble weighting (stat_weight, lgbm_weight)
- Forecast horizon: 2025-2030 with constant forward projection of lag features
- Models serialized with joblib to models/ai_industry/
- SHAP beeswarm summary plot saved to models/ai_industry/shap_summary.png
"""

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so src/config imports work when this
# script is run directly (e.g. `python scripts/run_ensemble_pipeline.py`)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np
import pandas as pd
import joblib

from src.models.ml.gradient_boost import (
    FEATURE_COLS,
    build_residual_features,
    fit_lgbm_point,
    lgbm_cv_for_segment,
)
from src.models.ml.quantile_models import fit_all_quantile_models
from src.models.ensemble import compute_ensemble_weights, blend_forecasts
from src.inference.forecast import build_forecast_dataframe, get_data_vintage
from src.inference.shap_analysis import compute_shap_values, save_shap_summary_plot
from config.settings import DATA_PROCESSED, MODELS_DIR

# ---------------------------------------------------------------------------
# Segment definitions
# ---------------------------------------------------------------------------
SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]

# Forecast horizon
FORECAST_YEARS = list(range(2025, 2031))
HISTORICAL_END = 2024


# ---------------------------------------------------------------------------
# Feature builder for forecast horizon
# ---------------------------------------------------------------------------

def _build_forecast_features(
    seg_features: pd.DataFrame,
    forecast_years: list[int],
) -> np.ndarray:
    """
    Build feature rows for forecast years 2025-2030.

    Strategy: constant forward projection — the last two known residuals are
    used as residual_lag1 and residual_lag2 for every forecast step.
    This is a valid no-information extrapolation when residuals are
    mean-reverting (which is the assumption of the statistical baseline).

    Parameters
    ----------
    seg_features : pd.DataFrame
        Feature DataFrame for the segment (output of build_residual_features
        filtered to that segment). Must have residual column.
    forecast_years : list[int]
        Years to forecast (e.g. [2025, ..., 2030]).

    Returns
    -------
    np.ndarray, shape (len(forecast_years), len(FEATURE_COLS))
        Feature matrix for the forecast horizon.
    """
    # Get last two residuals from the segment feature DataFrame
    sorted_feats = seg_features.sort_values("year")
    last_residuals = sorted_feats["residual"].values

    # Last known lag values
    lag1 = float(last_residuals[-1])   # most recent residual
    lag2 = float(last_residuals[-2]) if len(last_residuals) >= 2 else 0.0

    rows = []
    for year in forecast_years:
        year_norm = (year - 2010) / 14.0
        rows.append([lag1, lag2, year_norm])

    return np.array(rows, dtype=np.float64)


# ---------------------------------------------------------------------------
# Historical values builder (2010-2024 actuals for the segment)
# ---------------------------------------------------------------------------

def _get_historical_values(residuals_df: pd.DataFrame, segment: str) -> dict:
    """
    Return actual historical values from the residuals file.

    For the historical period, point estimate equals the series value itself
    (residuals are added on top of statistical model output; for the training
    period we use residuals as the proxy — since statistical model residuals
    represent the unexplained component, and our LightGBM learns to correct
    them, the historical 'corrected' value approximates zero net residual).

    For simplicity and consistency with the forecast schema, historical
    point estimates use the raw residual series (centered around 0) to
    represent the correction signal — the dashboard will render historical
    actuals from the source data.
    """
    seg_df = residuals_df[residuals_df["segment"] == segment].sort_values("year")
    years = seg_df["year"].tolist()
    residuals = seg_df["residual"].values

    # Historical CI: symmetric ±1.28σ (80%) and ±1.96σ (95%) from residual std
    sigma = float(np.std(residuals)) if len(residuals) > 1 else 1.0
    ci80_half = 1.28 * sigma
    ci95_half = 1.96 * sigma

    n = len(years)
    return {
        "years": years,
        "point_estimates": residuals,
        "ci80_lower": residuals - ci80_half,
        "ci80_upper": residuals + ci80_half,
        "ci95_lower": residuals - ci95_half,
        "ci95_upper": residuals + ci95_half,
        "is_forecast": [False] * n,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> None:
    """
    End-to-end ensemble ML pipeline:
    1. Load residuals from Phase 2 statistical pipeline.
    2. Build lag features per segment.
    3. Per segment: LightGBM CV, ensemble weights, fit point + quantile models.
    4. Generate forecasts for 2025-2030.
    5. Compute SHAP attribution.
    6. Serialize all models (joblib) and ensemble weights.
    7. Save SHAP summary plot.
    8. Build and save forecasts_ensemble.parquet.
    9. Print summary table.
    """
    # Ensure output directories exist
    models_ai_dir = MODELS_DIR / "ai_industry"
    models_ai_dir.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # --- Load residuals ---
    residuals_path = DATA_PROCESSED / "residuals_statistical.parquet"
    if not residuals_path.exists():
        print(
            f"ERROR: {residuals_path} not found. "
            "Run `uv run python scripts/run_statistical_pipeline.py` first."
        )
        sys.exit(1)

    print(f"Loading residuals from: {residuals_path}")
    residuals_df = pd.read_parquet(residuals_path)
    print(
        f"  Rows: {len(residuals_df)}, "
        f"segments: {sorted(residuals_df['segment'].unique())}\n"
    )

    # --- Data vintage ---
    vintage = get_data_vintage(residuals_df)
    print(f"Data vintage: {vintage}\n")

    # --- Build feature matrix ---
    features_df = build_residual_features(residuals_df)
    print(f"Feature matrix shape: {features_df.shape}\n")

    # Accumulators
    all_segment_forecasts: dict = {}
    weights_dict: dict = {}
    summary_rows = []
    shap_dict_aggregate: dict | None = None

    for seg in SEGMENTS:
        print(f"Processing segment: {seg}")

        # Filter features for segment
        seg_feats = features_df[features_df["segment"] == seg].sort_values("year").copy()

        if len(seg_feats) < 5:
            print(f"  WARNING: insufficient rows for {seg} ({len(seg_feats)}), skipping.\n")
            continue

        X = seg_feats[FEATURE_COLS].values  # shape (n_samples, 3)
        y = seg_feats["residual"].values    # shape (n_samples,)

        # --- LightGBM CV ---
        print(f"  Running LightGBM CV ({len(y)} samples)...")
        cv_results = lgbm_cv_for_segment(y, X, n_splits=3)
        lgbm_cv_rmse = float(np.mean([fold["rmse"] for fold in cv_results]))

        # Statistical baseline RMSE: std(residuals) — stat model forecast = 0
        stat_rmse = float(np.std(y))

        # --- Ensemble weights ---
        stat_weight, lgbm_weight = compute_ensemble_weights(stat_rmse, lgbm_cv_rmse)
        weights_dict[seg] = {"stat_weight": stat_weight, "lgbm_weight": lgbm_weight}

        print(
            f"  stat_rmse={stat_rmse:.4f}, lgbm_cv_rmse={lgbm_cv_rmse:.4f}, "
            f"stat_weight={stat_weight:.3f}, lgbm_weight={lgbm_weight:.3f}"
        )

        # --- Fit point model ---
        print(f"  Fitting point model...")
        point_model = fit_lgbm_point(X, y)

        # --- Fit quantile models ---
        print(f"  Fitting quantile models...")
        quantile_models = fit_all_quantile_models(X, y)

        # --- Generate forecast features (2025-2030) ---
        X_future = _build_forecast_features(seg_feats, FORECAST_YEARS)

        # --- Predict ---
        point_pred_future = point_model.predict(X_future)
        q_preds_future = {name: qm.predict(X_future) for name, qm in quantile_models.items()}

        # --- Blend: stat_baseline=0.0 (residuals horizon, stat model projects 0) ---
        blended_point = blend_forecasts(
            stat_pred=0.0,
            lgbm_correction=point_pred_future,
            stat_weight=stat_weight,
            lgbm_weight=lgbm_weight,
        )

        blended_ci80_lower = blend_forecasts(
            stat_pred=0.0,
            lgbm_correction=q_preds_future["ci80_lower"],
            stat_weight=stat_weight,
            lgbm_weight=lgbm_weight,
        )
        blended_ci80_upper = blend_forecasts(
            stat_pred=0.0,
            lgbm_correction=q_preds_future["ci80_upper"],
            stat_weight=stat_weight,
            lgbm_weight=lgbm_weight,
        )
        blended_ci95_lower = blend_forecasts(
            stat_pred=0.0,
            lgbm_correction=q_preds_future["ci95_lower"],
            stat_weight=stat_weight,
            lgbm_weight=lgbm_weight,
        )
        blended_ci95_upper = blend_forecasts(
            stat_pred=0.0,
            lgbm_correction=q_preds_future["ci95_upper"],
            stat_weight=stat_weight,
            lgbm_weight=lgbm_weight,
        )

        # --- Build segment forecast dict ---
        # Combine historical (2010-2024) and forecast (2025-2030)
        hist_data = _get_historical_values(residuals_df, seg)

        all_years = hist_data["years"] + FORECAST_YEARS
        all_point = np.concatenate([
            hist_data["point_estimates"],
            np.array(blended_point).ravel(),
        ])
        all_ci80_lower = np.concatenate([
            hist_data["ci80_lower"],
            np.array(blended_ci80_lower).ravel(),
        ])
        all_ci80_upper = np.concatenate([
            hist_data["ci80_upper"],
            np.array(blended_ci80_upper).ravel(),
        ])
        all_ci95_lower = np.concatenate([
            hist_data["ci95_lower"],
            np.array(blended_ci95_lower).ravel(),
        ])
        all_ci95_upper = np.concatenate([
            hist_data["ci95_upper"],
            np.array(blended_ci95_upper).ravel(),
        ])
        all_is_forecast = hist_data["is_forecast"] + [True] * len(FORECAST_YEARS)

        all_segment_forecasts[seg] = {
            "years": all_years,
            "point_estimates": all_point,
            "ci80_lower": all_ci80_lower,
            "ci80_upper": all_ci80_upper,
            "ci95_lower": all_ci95_lower,
            "ci95_upper": all_ci95_upper,
            "is_forecast": all_is_forecast,
        }

        # --- SHAP ---
        print(f"  Computing SHAP values...")
        X_df = pd.DataFrame(X, columns=FEATURE_COLS)
        shap_dict = compute_shap_values(point_model, X_df, FEATURE_COLS)

        # Aggregate SHAP across segments (keep last — overwritten each loop)
        # For multi-segment SHAP, users can inspect per-segment .joblib models
        shap_dict_aggregate = shap_dict
        shap_X_aggregate = X_df

        # --- Serialize models ---
        model_prefix = models_ai_dir / f"{seg}_lgbm"
        print(f"  Serializing models to {models_ai_dir}/...")

        joblib.dump(point_model, models_ai_dir / f"{seg}_lgbm_point.joblib")
        for q_name, q_model in quantile_models.items():
            joblib.dump(q_model, models_ai_dir / f"{seg}_lgbm_{q_name}.joblib")

        summary_rows.append({
            "segment": seg,
            "stat_rmse": stat_rmse,
            "lgbm_cv_rmse": lgbm_cv_rmse,
            "stat_weight": stat_weight,
            "lgbm_weight": lgbm_weight,
        })
        print()

    # --- Serialize ensemble weights ---
    weights_path = models_ai_dir / "ensemble_weights.joblib"
    print(f"Saving ensemble weights to: {weights_path}")
    joblib.dump(weights_dict, weights_path)

    # --- Save SHAP summary plot ---
    if shap_dict_aggregate is not None:
        shap_plot_path = models_ai_dir / "shap_summary.png"
        print(f"Saving SHAP summary plot to: {shap_plot_path}")
        save_shap_summary_plot(shap_dict_aggregate, shap_X_aggregate, shap_plot_path)

    # --- Build and save forecast DataFrame ---
    forecast_path = DATA_PROCESSED / "forecasts_ensemble.parquet"
    print(f"\nBuilding forecast DataFrame for {len(all_segment_forecasts)} segments...")
    forecast_df = build_forecast_dataframe(all_segment_forecasts, vintage)
    print(f"  Shape: {forecast_df.shape}")
    print(f"  Columns: {forecast_df.columns.tolist()}")
    forecast_df.to_parquet(forecast_path, index=False)
    print(f"  Saved: {forecast_path}")

    # --- Print summary table ---
    print("\n" + "=" * 80)
    print(f"{'Segment':<22} {'Stat RMSE':>10} {'LGBM RMSE':>10} {'Stat W':>8} {'LGBM W':>8}")
    print("-" * 80)
    for row in summary_rows:
        print(
            f"{row['segment']:<22} "
            f"{row['stat_rmse']:>10.4f} "
            f"{row['lgbm_cv_rmse']:>10.4f} "
            f"{row['stat_weight']:>8.3f} "
            f"{row['lgbm_weight']:>8.3f}"
        )
    print("=" * 80)
    print(f"\nOutputs:")
    print(f"  Forecast parquet: {forecast_path}")
    print(f"  Models directory: {models_ai_dir}")
    print(f"  SHAP plot:        {models_ai_dir / 'shap_summary.png'}")
    print(f"  Ensemble weights: {weights_path}")


if __name__ == "__main__":
    run_pipeline()
