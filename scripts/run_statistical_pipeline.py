"""
Statistical baseline pipeline runner.

Loads real processed Parquet data (World Bank, OECD MSTI), builds a PCA
composite indicator per AI segment, fits ARIMA and Prophet per segment
using expanding-window CV, selects the winning model by RMSE, extracts
residuals, and persists them to:

    data/processed/residuals_statistical.parquet

Schema: year (int), segment (str), residual (float), model_type (str)

This file is the Phase 3 ML training input. Run it with:

    uv run python scripts/run_statistical_pipeline.py

Prerequisites
-----------
- Run ingestion pipeline first to produce:
    * data/processed/world_bank_ai.parquet
    * data/processed/oecd_msti_ai.parquet
    * data/processed/lseg_ai.parquet

Design notes
------------
- Real data: World Bank global indicators + OECD MSTI R&D expenditure
- LSEG scalar: lseg_ai.parquet is a single-year company snapshot; loaded
  as a per-segment revenue-share weight applied to PCA composite scores
- PCA composite: 3 indicators per segment, fitted on training window only
  (70% of observations) to prevent leakage
- Structural break: CUSUM + Chow tests detect the break year from data;
  detected break_year is passed to Prophet changepoint (default 2022)
- Stationarity: assess_stationarity (ADF+KPSS) called per-segment before
  ARIMA order selection; results logged for ASSUMPTIONS.md traceability
- OLS complementary model: fit_top_down_ols_with_upgrade runs per-segment
  as a GDP-share regression diagnostic; logged but not written to Parquet
- ARIMA order selected via AICc (parsimony for N<30)
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
from src.processing.features import assess_stationarity
# build_pca_composite removed in Phase 9 (v1.1) — use run_ensemble_pipeline.py for USD forecasts
from src.diagnostics.structural_breaks import run_cusum, run_chow
from src.models.statistical.regression import fit_top_down_ols_with_upgrade
import statsmodels.api as sm
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
# Per-segment feature subsets for PCA composite construction.
# Each segment captures a different facet of AI industry activity.
# ai_hardware: compute/silicon intensity → high-tech exports + patents + ICT R&D
# ai_infrastructure: cloud/platform scale → GDP + ICT services + total BERD
# ai_software: software/platform R&D → ICT services + R&D intensity + GERD
# ai_adoption: enterprise deployment → R&D intensity + human capital + GDP
# ---------------------------------------------------------------------------
_SEGMENT_FEATURES = {
    "ai_hardware":       ["hightech_exports_real_2020_usd", "patent_applications_residents", "B_ICTS"],
    "ai_infrastructure": ["gdp_real_2020_usd", "ict_service_exports_real_2020_usd", "B"],
    "ai_software":       ["ict_service_exports_real_2020_usd", "rd_pct_gdp", "G"],
    "ai_adoption":       ["rd_pct_gdp", "researchers_per_million", "gdp_real_2020_usd"],
}


# ---------------------------------------------------------------------------
# Real data loader — reads and merges World Bank + OECD MSTI processed Parquets
# ---------------------------------------------------------------------------

def _load_real_data() -> pd.DataFrame:
    """
    Load and merge real processed indicator data from World Bank and OECD MSTI.

    Builds a global composite indicator matrix with one row per year (2010-2024)
    and columns for each proxy indicator used in segment PCA construction.

    World Bank data is globally aggregated (sum for monetary, mean for ratios).
    OECD MSTI data is aggregated across all economies per year for R&D indicators.

    Returns
    -------
    pd.DataFrame
        Wide DataFrame indexed by year with columns:
        gdp_real_2020_usd, hightech_exports_real_2020_usd,
        ict_service_exports_real_2020_usd, rd_pct_gdp,
        patent_applications_residents, researchers_per_million,
        B (BERD), B_ICTS (ICT BERD), G (GERD)
    """
    wb_path = DATA_PROCESSED / "world_bank_ai.parquet"
    msti_path = DATA_PROCESSED / "oecd_msti_ai.parquet"

    if not wb_path.exists() or not msti_path.exists():
        raise FileNotFoundError(
            "Real processed data not found. Run the ingestion pipeline first:\n"
            "  uv run python -c \"from src.ingestion.pipeline import run_full_pipeline; "
            "run_full_pipeline('ai', include_lseg=True)\""
        )

    wb = pd.read_parquet(wb_path)
    msti = pd.read_parquet(msti_path)

    # World Bank: aggregate globally per year
    wb_global = wb.groupby("year").agg({
        "gdp_real_2020_usd": "sum",
        "hightech_exports_real_2020_usd": "sum",
        "ict_service_exports_real_2020_usd": "sum",
        "rd_pct_gdp": "mean",
        "patent_applications_residents": "sum",
        "researchers_per_million": "mean",
    }).reset_index().sort_values("year")

    # OECD MSTI: B_ICTS, B (total BERD), G (GERD) per year aggregated globally
    msti_pivot = (
        msti[msti["MEASURE"].isin(["B_ICTS", "B", "G"])]
        .groupby(["year", "MEASURE"])["value"]
        .sum()
        .unstack("MEASURE")
        .reset_index()
        .sort_values("year")
    )
    msti_pivot.columns.name = None

    # Merge on year and filter to 2010-2024
    combined = (
        wb_global.merge(msti_pivot, on="year", how="outer")
        .sort_values("year")
        .query("year >= 2010 and year <= 2024")
        .ffill()
        .bfill()
        .reset_index(drop=True)
    )

    return combined


def _load_lseg_scalar() -> dict:
    """
    Load lseg_ai.parquet and derive a revenue-share scalar per AI segment.

    lseg_ai.parquet is a single-year company-universe snapshot (year=2026).
    It cannot be added as a time-series column to the 2010-2024 indicator
    matrix; instead, it contributes a per-segment scalar weight representing
    relative company-universe revenue size.

    Returns
    -------
    dict[str, float]
        Mapping of segment name to revenue share in [0, 1]. Returns empty
        dict if the parquet file is missing (pipeline runs without LSEG).
    """
    lseg_path = DATA_PROCESSED / "lseg_ai.parquet"
    if not lseg_path.exists():
        print("  LSEG: lseg_ai.parquet not found — running without LSEG scalar")
        return {}

    lseg = pd.read_parquet(lseg_path)

    # Aggregate total revenue per segment (convert raw units to billions USD)
    rev_by_seg = (
        lseg.groupby("industry_segment")["Revenue"]
        .sum()
        .astype(float)
        / 1e9
    )

    total = rev_by_seg.sum()
    if total <= 0:
        print("  LSEG: total revenue is zero — returning empty scalar dict")
        return {}

    scalar_dict = (rev_by_seg / total).to_dict()
    for seg, val in scalar_dict.items():
        print(f"  LSEG scalar: {seg} = {val:.4f} (revenue share of total)")
    return scalar_dict


def _run_break_detection(combined_series: pd.Series) -> int:
    """
    Detect the structural break year from CUSUM and Chow tests.

    Runs CUSUM test (non-parametric, detects shift anywhere in series) and
    Chow test at year 2022 (parametric, tests sharp level change). Returns
    the detected break year as an int for use as Prophet changepoint.

    Falls back to 2022 if:
    - Chow test is not significant (p >= 0.05)
    - CUSUM test is not significant (p >= 0.05)
    - break_idx guard fails (too close to series endpoints)

    Parameters
    ----------
    combined_series : pd.Series
        Annual time series indexed by integer year.

    Returns
    -------
    int
        Detected break year (e.g., 2022). Always returns 2022 as default.
    """
    cusum = run_cusum(combined_series)

    years = combined_series.index.tolist()
    break_candidate = 2022
    if break_candidate in years:
        break_idx = years.index(break_candidate)
    else:
        break_idx = len(years) // 2  # fallback to midpoint

    # Guard: Chow requires at least 3 obs in each sub-period (Pitfall 3)
    if break_idx < 3 or break_idx > len(years) - 3:
        print(f"  Break detection: break_idx={break_idx} too close to endpoints — "
              f"skipping Chow, using default 2022")
        return 2022

    chow = run_chow(combined_series, break_idx=break_idx)
    print(f"  CUSUM: p={cusum['p_value']:.4f}, "
          f"Chow: F={chow['F_stat']:.3f} p={chow['p_value']:.4f}")

    if chow["p_value"] < 0.05:
        detected = int(chow["break_year"])
        print(f"  Break detected at {detected} (Chow p<0.05)")
    elif cusum["p_value"] < 0.05:
        detected = 2022
        print(f"  Break confirmed by CUSUM (p={cusum['p_value']:.4f}), using 2022")
    else:
        detected = 2022
        print(f"  No significant break detected; using default changepoint 2022")

    return detected


def _build_segment_series(
    combined: pd.DataFrame,
    segment: str,
    lseg_scalar: dict | None = None,
) -> pd.DataFrame:
    """
    Build a year-indexed composite indicator series for a single AI segment.

    Uses PCA (first principal component) on the segment's indicator subset to
    produce a single normalized value per year. The PCA is fitted on the first
    70% of observations to prevent data leakage.

    If lseg_scalar is provided and contains the segment key, applies the LSEG
    revenue-share weight as a gentle amplification factor on the PCA scores:
    scores *= (1.0 + lseg_scalar[segment]). This is a post-PCA scalar — it
    does not modify the PCA fitting or the training/test split.

    Parameters
    ----------
    combined : pd.DataFrame
        Output of _load_real_data() — global indicator matrix.
    segment : str
        AI segment ID, one of: ai_hardware, ai_infrastructure, ai_software, ai_adoption.
    lseg_scalar : dict[str, float] or None
        Optional LSEG revenue-share scalar per segment. Pass None (default)
        to skip LSEG adjustment (backward-compatible).

    Returns
    -------
    pd.DataFrame
        Long-format DataFrame with columns: year, value_real_2020, industry_segment.
        value_real_2020 contains the PCA composite score (LSEG-scaled if applicable).
    """
    feature_cols = [c for c in _SEGMENT_FEATURES[segment] if c in combined.columns]
    matrix = combined[feature_cols].values.astype(float)
    train_end = max(3, int(len(matrix) * 0.7))  # minimum 3 training obs
    # PCA composite removed in Phase 9 (v1.1) — model now uses USD market anchors directly
    # See run_ensemble_pipeline.py for the v1.1 forecasting pipeline
    print(f"    [SKIP] PCA composite removed in v1.1 — {len(feature_cols)} features available as exogenous regressors")

    # Apply LSEG revenue weight if available for this segment
    if lseg_scalar is not None and segment in lseg_scalar:
        weight = lseg_scalar[segment]
        scores = scores * (1.0 + weight)  # gentle amplification, not replacement
        print(f"    LSEG scalar for {segment}: {weight:.4f} (revenue weight applied)")

    return pd.DataFrame({
        "year": combined["year"].values,
        "value_real_2020": scores,
        "industry_segment": segment,
    })


# ---------------------------------------------------------------------------
# Synthetic data generator — PRESERVED FOR UNIT TESTING ONLY
# Do NOT use in production runs. Use _load_real_data() instead.
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

def run_pipeline(n_splits: int = 3, use_real_data: bool = True) -> None:
    """
    End-to-end statistical pipeline:
    1. Load real processed indicator data (or synthetic for testing).
    2. Load LSEG scalar (real data mode only) — per-segment revenue-share weight.
    3. Run structural break detection (real data mode only) — derives break_year.
    4. Per segment: build PCA composite series (with optional LSEG scaling).
    5. Per segment: assess stationarity (ADF+KPSS) before ARIMA order selection.
    6. Per segment: run ARIMA and Prophet CV (Prophet uses detected break_year).
    7. Per segment: compare models, extract winner residuals.
    8. Per segment: run OLS complementary model (GDP-share), log diagnostics.
    9. Persist residuals to data/processed/residuals_statistical.parquet.
    10. Print summary table.

    Parameters
    ----------
    n_splits : int
        Number of expanding-window CV folds (default 3).
    use_real_data : bool
        If True (default), loads real processed Parquet data.
        If False, uses synthetic data (for unit testing only).
    """
    # Ensure output directory exists
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    output_path = str(DATA_PROCESSED / "residuals_statistical.parquet")

    if use_real_data:
        print("Loading real processed indicator data from data/processed/...")
        combined = _load_real_data()
        print(f"  Combined shape: {combined.shape}, years: {combined['year'].min()}-{combined['year'].max()}\n")

        # --- LSEG scalar loading (real data only) ---
        print("Loading LSEG revenue scalar...")
        lseg_scalar = _load_lseg_scalar()
        print(f"  LSEG segments covered: {list(lseg_scalar.keys())}\n")

        # --- Build per-segment composite series from real data (with LSEG scaling) ---
        frames = []
        for seg in SEGMENTS:
            seg_df = _build_segment_series(combined, seg, lseg_scalar=lseg_scalar)
            frames.append(seg_df)
        df = pd.concat(frames, ignore_index=True)
        print(f"  Total rows: {len(df)}, segments: {sorted(df['industry_segment'].unique())}\n")

        # --- Structural break detection on ai_software series (richest LSEG coverage) ---
        print("Running structural break detection on ai_software series...")
        agg_series = (
            df[df["industry_segment"] == "ai_software"]
            .groupby("year")["value_real_2020"]
            .sum()
            .sort_index()
        )
        agg_series.index = pd.Index(agg_series.index.astype(int), name="year")
        break_year = _run_break_detection(agg_series)
        print(f"  Using break_year={break_year} as Prophet changepoint\n")

    else:
        print("Generating synthetic AI-segment data (2010-2024, seed=42) [TEST MODE]...")
        df = _generate_synthetic_data(seed=42)
        print(f"  Total rows: {len(df)}, segments: {sorted(df['industry_segment'].unique())}\n")
        # Synthetic mode: use defaults (no LSEG, no break detection)
        lseg_scalar = None
        break_year = 2022
        combined = None  # not available in synthetic mode

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

        # --- Stationarity assessment (both real and synthetic paths) ---
        if len(series) < 20:
            print(f"  Stationarity note: N={len(series)} < 20, results may be unreliable")
        stationarity = assess_stationarity(series.values)
        print(f"  Stationarity: ADF p={stationarity['adf_pval']:.4f}, "
              f"KPSS p={stationarity['kpss_pval']:.4f}, "
              f"recommended d={stationarity['recommendation_d']}")

        # --- ARIMA: order selection + CV ---
        print(f"  ARIMA: selecting order via AICc...")
        order = select_arima_order(series)
        print(f"  ARIMA: order = {order}")
        arima_cv = run_arima_cv(series, order, n_splits=n_splits)

        # --- Prophet: CV (using detected break_year) ---
        print(f"  Prophet: running CV (changepoint_year={break_year})...")
        prophet_cv = run_prophet_cv(df, seg, n_splits=n_splits, changepoint_year=break_year)

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
            prophet_model = fit_prophet_segment(df, seg, changepoint_year=break_year)
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

        # --- OLS complementary model (both real and synthetic paths) ---
        # Serves as a GDP-share regression diagnostic for ASSUMPTIONS.md traceability.
        # Diagnostics are logged only — OLS residuals are NOT written to the Parquet output.
        try:
            if use_real_data and combined is not None and "gdp_real_2020_usd" in combined.columns:
                # Real data mode: use GDP as X, aligned to segment series index
                gdp_series = pd.Series(
                    combined["gdp_real_2020_usd"].values,
                    index=combined["year"].astype(int).values,
                )
                common_idx = series.index.intersection(gdp_series.index)
                y_ols = series.loc[common_idx].values
                x_ols = gdp_series.loc[common_idx].values
            else:
                # Synthetic mode: use time trend as X proxy
                y_ols = series.values
                x_ols = np.arange(len(series), dtype=float)
            X_ols = sm.add_constant(x_ols)
            _, ols_model_type, ols_diagnostics = fit_top_down_ols_with_upgrade(y_ols, X_ols)
            print(f"  OLS complementary: {ols_model_type}, "
                  f"R²={ols_diagnostics['r2']:.4f}, R²_adj={ols_diagnostics['r2_adj']:.4f}")
        except Exception as e:
            print(f"  OLS complementary: skipped ({type(e).__name__}: {e})")

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
