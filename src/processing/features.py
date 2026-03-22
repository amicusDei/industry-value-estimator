"""
Feature engineering for the AI industry statistical baseline.

Provides:
- build_indicator_matrix: pivot long-format processed data to wide indicator matrix
- build_pca_composite: first principal component composite index (train-only fitting, no leakage)
- build_manual_composite: weighted sum alternative for sensitivity comparison
- assess_stationarity: ADF + KPSS stationarity tests with differencing recommendation

All preprocessing is designed to be fit on training data only to prevent data leakage
in temporal cross-validation. See RESEARCH.md Pattern 6 and Pitfall 3.

PCA composite rationale: AI market activity has no single clean observable metric.
Six proxies capture different facets (R&D spend, patent filings, VC investment, public
company revenue, researcher density, high-tech exports). PCA reduces these to the first
principal component — the linear combination that maximises explained variance. This is
preferable to manual weighting because it is data-driven and reproducible across
different industry configs.

See docs/ASSUMPTIONS.md section Modeling Assumptions for the composite index approach,
explained variance thresholds, and sensitivity to number of principal components.
"""
import warnings

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import adfuller, kpss


def build_indicator_matrix(
    df: pd.DataFrame,
    indicators: list[str],
    segment: str | None = None,
) -> tuple[np.ndarray, pd.Index]:
    """
    Build a wide indicator matrix from long-format processed data.

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


def build_pca_composite(
    indicator_matrix: np.ndarray,
    train_end_idx: int,
) -> tuple[np.ndarray, float, Pipeline]:
    """
    Build PCA composite index (first principal component) fitted on training data only.

    The pipeline is fit ONLY on indicator_matrix[:train_end_idx] to prevent data leakage.
    The trained pipeline is then applied to the full matrix to produce scores for all years.

    Why train-only fitting matters: if PCA were fit on the full matrix (including test years),
    the scaler's mean and standard deviation would absorb future information. The PC loadings
    would subtly reflect the trend direction of the test period, making the composite index
    look like it has better predictive power than it actually does. This is the canonical
    temporal leakage pitfall in time-series feature engineering.

    The sklearn Pipeline ensures scaler and PCA are always fit together in the correct order.
    The fitted Pipeline is returned so callers can verify non-leakage by inspecting
    pipe.named_steps["scaler"].mean_ (should reflect only training period values).

    See docs/ASSUMPTIONS.md section Modeling Assumptions for PCA composite rationale.

    Parameters
    ----------
    indicator_matrix : np.ndarray, shape (n_years, n_indicators)
        Rows = years, columns = proxy indicators.
    train_end_idx : int
        Exclusive upper bound of training period rows. E.g. 7 means rows 0–6 are training.

    Returns
    -------
    scores : np.ndarray, shape (n_years,)
        First principal component scores for all years.
    explained : float
        Explained variance ratio of the first principal component.
    pipe : Pipeline
        Fitted sklearn Pipeline (scaler + PCA). Caller can inspect
        pipe.named_steps["scaler"].mean_ to verify no leakage.
    """
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=1)),
    ])
    pipe.fit(indicator_matrix[:train_end_idx])  # FIT ON TRAINING DATA ONLY
    scores = pipe.transform(indicator_matrix).flatten()
    explained = pipe.named_steps["pca"].explained_variance_ratio_[0]
    return scores, explained, pipe


def build_manual_composite(
    indicator_matrix: np.ndarray,
    weights: list[float],
    train_end_idx: int,
) -> np.ndarray:
    """
    Build a manual weighted composite index as a sensitivity alternative to PCA.

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
