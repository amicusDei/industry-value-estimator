"""
Statistical baseline pipeline runner.

Generates representative synthetic AI-segment data, fits ARIMA and Prophet
per segment using expanding-window CV, selects the winning model by RMSE,
extracts residuals, and persists them to:

    data/processed/residuals_statistical.parquet

Schema: year (int), segment (str), residual (float), model_type (str)

This file is the Phase 3 ML training input. Run it with:

    uv run python scripts/run_statistical_pipeline.py

Design notes
------------
- Synthetic data covers 2010-2024 (15 years) per segment with:
    * Realistic upward trend (segment-specific growth rates)
    * Structural break at 2022 simulating the GenAI surge
    * Reproducible noise via numpy seed=42
- ARIMA order selected via AICc (parsimony for N<30)
- Prophet uses explicit changepoint at 2022-01-01
- Winner determined by mean CV RMSE across 3 expanding-window folds
- Residuals are year-indexed (int) — required for Phase 3 feature joins
"""

import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so src/config imports work when this
# script is run directly (e.g. `python scripts/run_statistical_pipeline.py`)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Suppress verbose Stan / Prophet output before any prophet import
# ---------------------------------------------------------------------------
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
from src.models.statistical.arima import (
    select_arima_order,
    fit_arima_segment,
    get_arima_residuals,
    run_arima_cv,
)
from src.models.statistical.prophet_model import (
    fit_prophet_segment,
    get_prophet_residuals,
    run_prophet_cv,
    save_all_residuals,
)
from src.diagnostics.model_eval import compare_models
from config.settings import DATA_PROCESSED

# ---------------------------------------------------------------------------
# Segment definitions
# ---------------------------------------------------------------------------
SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]

# Growth rates (units per year) and break-amplitudes at 2022 per segment
# Chosen to give each segment a distinct trend profile while remaining plausible
_SEGMENT_PARAMS = {
    "ai_hardware":        {"growth": 3.5, "break_amp": 8.0,  "base": 60.0},
    "ai_infrastructure":  {"growth": 4.0, "break_amp": 12.0, "base": 45.0},
    "ai_software":        {"growth": 5.0, "break_amp": 20.0, "base": 30.0},
    "ai_adoption":        {"growth": 2.5, "break_amp": 6.0,  "base": 20.0},
}


# ---------------------------------------------------------------------------
# Synthetic data generator
# ---------------------------------------------------------------------------

def _generate_synthetic_data(seed: int = 42) -> pd.DataFrame:
    """
    Generate 15 years (2010-2024) of synthetic AI-segment data in
    PROCESSED_SCHEMA long format: year, value_real_2020, industry_segment.

    Each segment has:
    - A linear upward trend (segment-specific growth rate)
    - A step increase in growth starting at 2022 (structural break)
    - Gaussian noise (seed=42 for reproducibility)
    """
    rng = np.random.default_rng(seed)
    years = list(range(2010, 2025))  # 15 years: 2010-2024
    frames = []

    for seg, params in _SEGMENT_PARAMS.items():
        n = len(years)
        # Linear base trend
        values = params["base"] + params["growth"] * np.arange(n)
        # Structural break at 2022 — step increase in growth
        break_idx = years.index(2022)
        extra_growth = params["break_amp"] * np.arange(n)
        extra_growth[:break_idx] = 0.0
        # Shift extra_growth so it starts at 0 at the break
        extra_growth[break_idx:] = params["break_amp"] * np.arange(n - break_idx)
        values = values + extra_growth
        # Add noise
        noise = rng.normal(0, params["growth"] * 0.3, size=n)
        values = values + noise

        frame = pd.DataFrame({
            "year": years,
            "value_real_2020": values,
            "industry_segment": seg,
        })
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(n_splits: int = 3) -> None:
    """
    End-to-end statistical pipeline:
    1. Generate synthetic data for all 4 AI segments.
    2. Per segment: run ARIMA and Prophet CV, compare, extract winner residuals.
    3. Persist residuals to data/processed/residuals_statistical.parquet.
    4. Print summary table.
    """
    # Ensure output directory exists
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    output_path = str(DATA_PROCESSED / "residuals_statistical.parquet")

    print("Generating synthetic AI-segment data (2010-2024, seed=42)...")
    df = _generate_synthetic_data(seed=42)
    print(f"  Total rows: {len(df)}, segments: {sorted(df['industry_segment'].unique())}\n")

    segment_residuals: dict[str, tuple[pd.Series, str]] = {}
    summary_rows = []

    for seg in SEGMENTS:
        print(f"Processing segment: {seg}")

        # --- Extract segment series ---
        series = (
            df[df["industry_segment"] == seg]
            .groupby("year")["value_real_2020"]
            .sum()
            .sort_index()
        )
        series.index = pd.Index(series.index.astype(int), name="year")

        # --- ARIMA: order selection + CV ---
        print(f"  ARIMA: selecting order via AICc...")
        order = select_arima_order(series)
        print(f"  ARIMA: order = {order}")
        arima_cv = run_arima_cv(series, order, n_splits=n_splits)

        # --- Prophet: CV ---
        print(f"  Prophet: running CV...")
        prophet_cv = run_prophet_cv(df, seg, n_splits=n_splits)

        # --- Compare models ---
        comparison = compare_models(arima_cv, prophet_cv, seg)
        winner = comparison["winner"]
        arima_rmse = comparison["arima_mean_cv_rmse"]
        prophet_rmse = comparison["prophet_mean_cv_rmse"]
        print(f"  Winner: {winner} (ARIMA RMSE={arima_rmse:.4f}, Prophet RMSE={prophet_rmse:.4f})")

        # --- Extract residuals from winning model ---
        if winner == "ARIMA":
            arima_results = fit_arima_segment(series, order)
            residuals = get_arima_residuals(arima_results, series.index)
            model_type = "ARIMA"
        else:
            prophet_model = fit_prophet_segment(df, seg)
            # Prepare ds/y format DataFrame for get_prophet_residuals
            df_segment = (
                df[df["industry_segment"] == seg]
                .groupby("year")["value_real_2020"]
                .sum()
                .reset_index()
                .rename(columns={"year": "ds", "value_real_2020": "y"})
                .sort_values("ds")
                .reset_index(drop=True)
            )
            df_segment["ds"] = pd.to_datetime(df_segment["ds"].astype(str) + "-01-01")
            residuals = get_prophet_residuals(prophet_model, df_segment)
            model_type = "Prophet"

        segment_residuals[seg] = (residuals, model_type)
        summary_rows.append({
            "segment": seg,
            "arima_cv_rmse": arima_rmse,
            "prophet_cv_rmse": prophet_rmse,
            "winner": winner,
            "residual_count": len(residuals),
        })
        print(f"  Residuals extracted: {len(residuals)} rows\n")

    # --- Save all residuals ---
    print(f"Saving residuals to: {output_path}")
    save_all_residuals(segment_residuals, output_path)
    print("Done.\n")

    # --- Print summary table ---
    print("=" * 72)
    print(f"{'Segment':<22} {'ARIMA RMSE':>12} {'Prophet RMSE':>13} {'Winner':>8} {'Residuals':>10}")
    print("-" * 72)
    for row in summary_rows:
        print(
            f"{row['segment']:<22} "
            f"{row['arima_cv_rmse']:>12.4f} "
            f"{row['prophet_cv_rmse']:>13.4f} "
            f"{row['winner']:>8} "
            f"{row['residual_count']:>10}"
        )
    print("=" * 72)
    print(f"\nOutput: {output_path}")


if __name__ == "__main__":
    run_pipeline()
