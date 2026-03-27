"""
ARIMA per-segment fitting, automated order selection (AICc), forecasting, and temporal CV.

Provides:
- load_segment_y_series: Load USD billions Y series from market_anchors_ai.parquet
- load_source_disagreement_band: p25/p75 source disagreement band from market anchors
- assert_model_version: Gate ARIMA training to v1.1_real_data config
- select_arima_order: AICc-based ARIMA order selection via pmdarima auto_arima
- fit_arima_segment: Fit ARIMA(p,d,q) on a pandas Series using statsmodels
- forecast_arima: Out-of-sample forecast with prediction intervals
- get_arima_residuals: Year-aligned residual extraction (no positional index drift)
- run_arima_cv: Expanding-window temporal CV using temporal_cv_generic scaffold

Design notes:
- AICc is used (not AIC) for small N — see RESEARCH.md Pitfall 1
- max_p=2, max_q=2 enforces parsimony for N < 30 annual observations
- Residuals are aligned to original year index to prevent Phase 3 feature misalignment
  (RESEARCH.md Pitfall 5)
- CV reuses temporal_cv_generic from regression.py for consistent CV methodology
  across all model types (RESEARCH.md Pattern 7)
- Y variable is median_usd_billions_real_2020 from market_anchors_ai.parquet (v1.1)
- Training uses ALL data (real + interpolated). With only 2-3 real observations per
  segment, models require the full 9-year series including interpolated values to
  produce stable fits. Interpolated values are derived from analyst consensus estimates
  and provide reasonable signal.
"""

import logging
import warnings

import numpy as np
import pandas as pd
import pmdarima as pm
from statsmodels.tsa.arima.model import ARIMA

from src.models.statistical.regression import temporal_cv_generic

logger = logging.getLogger(__name__)

# Column name for the USD billions Y variable in market_anchors_ai.parquet
_MEDIAN_COL = "median_usd_billions_real_2020"
_P25_COL = "p25_usd_billions_real_2020"
_P75_COL = "p75_usd_billions_real_2020"


def assert_model_version() -> None:
    """Assert that ai.yaml model_version is v1.1_real_data.

    This is a hard gate preventing ARIMA from training on the wrong pipeline version.
    Must be called at the start of any v1.1 training entry point.

    Raises
    ------
    AssertionError
        If model_version is not 'v1.1_real_data'.
    """
    import yaml
    from pathlib import Path
    cfg_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "industries" / "ai.yaml"
    with open(cfg_path) as f:
        _cfg = yaml.safe_load(f)
    assert _cfg.get("model_version") == "v1.1_real_data", (
        f"model_version must be 'v1.1_real_data', got: {_cfg.get('model_version')}. "
        "Update config/industries/ai.yaml before running v1.1 ARIMA training."
    )


def load_segment_y_series(segment: str) -> pd.Series:
    """Load USD billions Y series for a segment from market_anchors_ai.parquet.

    Uses ALL data (real + interpolated) to give models enough training points.
    With only 2-3 real observations per segment, models require the full 9-year
    series including interpolated values to produce stable fits. Interpolated
    values are derived from analyst consensus estimates and provide reasonable
    signal.

    Parameters
    ----------
    segment : str
        Segment name, e.g. "ai_hardware", "ai_software".

    Returns
    -------
    pd.Series
        Series indexed by estimate_year (int), values in USD billions (median_usd_billions_real_2020).
        Includes both real (n_sources > 0) and interpolated (n_sources == 0) rows.

    Warns
    -----
    UserWarning
        If fewer than 5 observations are available.
    """
    from config.settings import DATA_PROCESSED
    anchors = pd.read_parquet(DATA_PROCESSED / "market_anchors_ai.parquet")
    # Use ALL data (real + interpolated) to give models enough training points.
    # The interpolated rows are derived from analyst estimates and provide reasonable
    # signal for 2017-2022. Filtering to n_sources > 0 only leaves 2 points per segment.
    seg_df = (
        anchors[anchors["segment"] == segment]
        .sort_values("estimate_year")
        .set_index("estimate_year")
    )
    seg = seg_df[_MEDIAN_COL]

    # Attach observation weights: real data (n_sources > 0) gets weight 1.0,
    # interpolated data (n_sources == 0) gets weight 0.3 to down-weight synthetic points.
    # Note: ARIMA and Prophet do not support sample_weight natively. Weighting is
    # implemented via observation duplication in fit_arima_segment and
    # prepare_prophet_from_anchors respectively. This attribute is kept for reference.
    if "n_sources" in seg_df.columns:
        seg.attrs["weights"] = pd.Series(
            [1.0 if ns > 0 else 0.3 for ns in seg_df["n_sources"]],
            index=seg_df.index,
            name="weight",
        )
        # Store n_sources for downstream duplication in fit_arima_segment
        seg.attrs["n_sources"] = seg_df["n_sources"]

    if len(seg) < 5:
        warnings.warn(
            f"load_segment_y_series: segment '{segment}' has only {len(seg)} observations. "
            f"Forecasts may be unreliable.",
            UserWarning,
            stacklevel=2,
        )
    return seg


def load_source_disagreement_band(segment: str) -> tuple[pd.Series, pd.Series]:
    """Layer 1 uncertainty: p25/p75 source disagreement band from market anchors.

    Returns the interquartile spread of analyst estimates as the source disagreement
    band — this is distinct from model prediction intervals (Layer 2).

    Parameters
    ----------
    segment : str
        Segment name, e.g. "ai_hardware", "ai_software".

    Returns
    -------
    tuple[pd.Series, pd.Series]
        (p25_series, p75_series) indexed by estimate_year (int), in USD billions.
        Filtered to real observations only (n_sources > 0).
    """
    from config.settings import DATA_PROCESSED
    anchors = pd.read_parquet(DATA_PROCESSED / "market_anchors_ai.parquet")
    real = anchors[anchors["n_sources"] > 0].copy()
    seg = (
        real[real["segment"] == segment]
        .sort_values("estimate_year")
        .set_index("estimate_year")
    )
    return seg[_P25_COL], seg[_P75_COL]


def select_arima_order(series: pd.Series) -> tuple[int, int, int]:
    """
    Select ARIMA(p, d, q) order via AICc on a pandas Series.

    Uses pmdarima auto_arima with stepwise Hyndman-Khandakar search,
    constrained to max_p=2, max_q=2 for parsimony on short annual panels
    (N < 30). Differencing order d is detected automatically via ADF.

    Parameters
    ----------
    series : pd.Series
        Annual time series (any year-indexed or integer-indexed Series).

    Returns
    -------
    tuple[int, int, int]
        (p, d, q) order selected by AICc.
    """
    model = pm.auto_arima(
        series,
        information_criterion="aicc",   # corrected AIC — required for small N
        stepwise=True,
        max_p=2, max_q=2,               # parsimony constraint for N < 30
        d=None,                          # auto-detect differencing order via ADF
        seasonal=False,                  # annual data — no intra-year seasonality
        error_action="ignore",
        suppress_warnings=True,
    )
    return model.order


def _duplicate_for_weighting(series: pd.Series) -> pd.Series:
    """Duplicate real observations 3x for effective weighting in ARIMA.

    Since statsmodels ARIMA does not support sample_weight, we duplicate
    real observations (n_sources > 0) 3x in the training series while
    keeping interpolated observations (n_sources == 0) at 1x. This
    effectively gives real data 3x weight during model fitting.

    If n_sources metadata is not available, returns the series unchanged.
    """
    n_sources = getattr(series, 'attrs', {}).get('n_sources')
    if n_sources is None:
        return series
    values = []
    for year_idx, val in series.items():
        ns = n_sources.get(year_idx, 0) if hasattr(n_sources, 'get') else 0
        n_copies = 3 if ns > 0 else 1
        values.extend([val] * n_copies)
    return pd.Series(values, name=series.name)


def fit_arima_segment(series: pd.Series, order: tuple[int, int, int]) -> object:
    """
    Fit ARIMA(p, d, q) on a pandas Series using statsmodels.

    Applies observation weighting via duplication: real observations
    (n_sources > 0) are duplicated 3x, interpolated ones kept at 1x.

    Parameters
    ----------
    series : pd.Series
        Annual time series. Year index is preserved through residual extraction.
    order : tuple[int, int, int]
        (p, d, q) — typically from select_arima_order().

    Returns
    -------
    ARIMAResults
        Fitted statsmodels ARIMAResults object. Has .resid, .fittedvalues,
        .aic, .bic attributes and .get_forecast() method.
    """
    train_series = _duplicate_for_weighting(series)
    model = ARIMA(train_series, order=order)
    return model.fit()


def forecast_arima(
    results,
    steps: int,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """
    Generate out-of-sample forecasts with prediction intervals.

    Parameters
    ----------
    results : ARIMAResults
        Fitted ARIMA results object from fit_arima_segment().
    steps : int
        Number of out-of-sample steps to forecast.
    alpha : float
        Significance level for prediction intervals (default 0.05 → 95% CI).

    Returns
    -------
    pd.DataFrame
        summary_frame with columns including "mean", "mean_ci_lower",
        "mean_ci_upper". Length equals steps.
    """
    return results.get_forecast(steps=steps).summary_frame(alpha=alpha)


def get_arima_residuals(
    results,
    original_index: pd.Index,
) -> pd.Series:
    """
    Extract in-sample residuals aligned to the original year index.

    ARIMA residuals from statsmodels may use a positional index after
    differencing. This function re-aligns them to the original series index
    so that Phase 3 ML can join residuals to the feature matrix by year.

    See RESEARCH.md Pitfall 5: Residuals Index Misalignment.

    Parameters
    ----------
    results : ARIMAResults
        Fitted ARIMA results object.
    original_index : pd.Index
        Year index of the original series (e.g. Int64Index([2010, 2011, ...])).

    Returns
    -------
    pd.Series
        Residuals indexed by original_index[:len(resid)]. Name = "residual".
    """
    resid = results.resid.copy()
    resid.index = original_index[: len(resid)]  # year-align, NOT positional
    resid.name = "residual"
    return resid


def run_arima_cv(
    series: pd.Series,
    order: tuple[int, int, int],
    n_splits: int = 3,
    y_series: "pd.Series | None" = None,
) -> list[dict]:
    """
    Expanding-window temporal cross-validation for ARIMA.

    Reuses temporal_cv_generic from regression.py to keep CV methodology
    consistent across ARIMA and Prophet (see RESEARCH.md Pattern 7).

    Parameters
    ----------
    series : pd.Series
        Annual time series in chronological order. Used if y_series is None.
    order : tuple[int, int, int]
        (p, d, q) order — typically from select_arima_order().
    n_splits : int
        Number of expanding-window folds. Default 3.
        With ~20 annual observations, 3–4 folds is typical.
    y_series : pd.Series, optional
        If provided, this USD series is used instead of `series`. Allows callers
        to pass a pre-loaded USD billions series from market_anchors_ai.parquet
        (v1.1 training path) while preserving backward compatibility for callers
        that pass `series` directly.

    Returns
    -------
    list[dict]
        One dict per fold with keys: fold, train_end, test_end, rmse, mape.
    """
    # v1.1 path: use y_series if provided (USD billions from market_anchors)
    active_series = y_series if y_series is not None else series
    values = active_series.values

    def fit_fn(train: np.ndarray):
        """Fit ARIMA on the training slice. Signature required by temporal_cv_generic."""
        return ARIMA(train, order=order).fit()

    def forecast_fn(fitted, steps: int) -> np.ndarray:
        """Produce steps-ahead point forecasts. Signature required by temporal_cv_generic."""
        pm = fitted.get_forecast(steps=steps).predicted_mean
        # predicted_mean may be pd.Series or np.ndarray depending on whether the
        # training data was a Series or ndarray — normalise to ndarray.
        return np.asarray(pm)

    return temporal_cv_generic(values, fit_fn, forecast_fn, n_splits=n_splits)
