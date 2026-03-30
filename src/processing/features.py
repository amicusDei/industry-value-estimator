"""
Feature engineering for the AI industry statistical baseline.

Provides:
- build_indicator_matrix: flat macro indicator matrix for ARIMA exogenous regressors and LightGBM features
- build_manual_composite: weighted sum composite for sensitivity comparison
- assess_stationarity: ADF + KPSS stationarity tests with differencing recommendation

All preprocessing is designed to be fit on training data only to prevent data leakage
in temporal cross-validation. See RESEARCH.md Pattern 6 and Pitfall 3.

Flat feature builder rationale: Phase 9 retrains ARIMA, Prophet, and LightGBM directly on
real USD market sizes from market_anchors_ai.parquet. The macro indicators (R&D spend,
patents, ICT exports, GDP) feed into models as exogenous regressors. The full indicator
matrix is preserved without dimensionality reduction. Keeping the full indicator matrix preserves interpretability and allows
per-indicator feature importance analysis via SHAP in Phase 10.
"""
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss


def build_indicator_matrix(
    df: pd.DataFrame,
    indicators: list[str],
    segment: str | None = None,
) -> tuple[np.ndarray, pd.Index]:
    """
    Build flat macro indicator matrix from long-format processed data.

    Output: wide matrix (n_years x n_indicators) in value_real_2020 units.
    No dimensionality reduction applied.

    Parameters
    ----------
    df : pd.DataFrame
        Long-format DataFrame with columns: year, indicator, value_real_2020,
        and optionally industry_segment. Conforms to PROCESSED_SCHEMA.
    indicators : list[str]
        Ordered list of indicator IDs to include as columns.
    segment : str | None
        If provided, filter to rows where industry_segment == segment.

    Returns
    -------
    matrix : np.ndarray, shape (n_years, n_indicators)
        Wide indicator matrix with years as rows and indicators as columns.
    year_idx : pd.Index
        Integer year index corresponding to the rows.
    """
    if segment is not None:
        df = df[df["industry_segment"] == segment]

    wide = df.pivot_table(
        index="year",
        columns="indicator",
        values="value_real_2020",
        aggfunc="sum",
    )

    # Keep only the requested indicators in the specified order
    available = [ind for ind in indicators if ind in wide.columns]
    wide = wide[available]

    # Forward-fill then backfill within each column to handle leading/trailing NaNs
    wide = wide.ffill().bfill()

    return wide.values, wide.index



def build_manual_composite(
    indicator_matrix: np.ndarray,
    weights: list[float],
    train_end_idx: int,
) -> np.ndarray:
    """
    Build a manual weighted composite index as a sensitivity check.

    Standardizes using training-period statistics only (no leakage), then
    computes a weighted sum across indicators.

    Parameters
    ----------
    indicator_matrix : np.ndarray, shape (n_years, n_indicators)
        Rows = years, columns = proxy indicators.
    weights : list[float]
        Weight for each indicator column. len(weights) must equal n_indicators.
        Weights need not sum to 1 — they are applied as-is to standardized columns.
    train_end_idx : int
        Exclusive upper bound of training period rows. Standardization statistics
        are computed on indicator_matrix[:train_end_idx] only.

    Returns
    -------
    composite : np.ndarray, shape (n_years,)
        Weighted composite scores for all years.
    """
    mean = indicator_matrix[:train_end_idx].mean(axis=0)
    std = indicator_matrix[:train_end_idx].std(axis=0)
    standardized = (indicator_matrix - mean) / (std + 1e-10)
    return np.dot(standardized, np.array(weights))


def assess_stationarity(series: np.ndarray | pd.Series) -> dict:
    """
    Assess stationarity of a time series using ADF and KPSS tests.

    Available for diagnostic use; not part of the main v1.1 ensemble pipeline.
    The ensemble pipeline (run_ensemble_pipeline.py) uses pmdarima's internal
    stationarity handling. This function remains useful for ad-hoc analysis
    and notebook diagnostics.

    Uses both tests together (belt-and-suspenders approach):
    - ADF null hypothesis: unit root present (non-stationary)
    - KPSS null hypothesis: trend-stationary

    Interpretation:
    - ADF rejects AND KPSS fails to reject → stationary → d=0
    - ADF fails to reject OR KPSS rejects → non-stationary → d=1

    Parameters
    ----------
    series : np.ndarray or pd.Series
        Time series to test. Should have at least 20 observations for reliable results.

    Returns
    -------
    dict with keys:
        adf_stationary : bool — ADF rejects unit root at 5%
        kpss_stationary : bool — KPSS fails to reject stationarity at 5%
        adf_pval : float — ADF p-value
        kpss_pval : float — KPSS p-value
        recommendation_d : int — 0 if stationary, 1 if differencing recommended
    """
    # Suppress KPSS interpolation warnings for p-values at boundary of look-up table.
    # When the test statistic is outside the table range, statsmodels returns the nearest
    # boundary value — the actual p-value is more extreme than reported.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=Warning, message=".*p-value is smaller than.*")
        warnings.filterwarnings("ignore", category=Warning, message=".*p-value is greater than.*")
        warnings.filterwarnings("ignore", category=Warning, message=".*outside of the range.*")

        adf_stat, adf_p, _, _, adf_crit, _ = adfuller(series, autolag="AIC")
        kpss_stat, kpss_p, _, kpss_crit = kpss(series, regression="c", nlags="auto")

    adf_stationary = bool(adf_p < 0.05)
    kpss_stationary = bool(kpss_p > 0.05)
    recommendation_d = 0 if (adf_stationary and kpss_stationary) else 1

    return {
        "adf_stationary": adf_stationary,
        "kpss_stationary": kpss_stationary,
        "adf_pval": float(adf_p),
        "kpss_pval": float(kpss_p),
        "recommendation_d": recommendation_d,
    }
