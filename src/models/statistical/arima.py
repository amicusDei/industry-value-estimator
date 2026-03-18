"""
ARIMA per-segment fitting, automated order selection (AICc), forecasting, and temporal CV.

Provides:
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
"""

import numpy as np
import pandas as pd
import pmdarima as pm
from statsmodels.tsa.arima.model import ARIMA

from src.models.statistical.regression import temporal_cv_generic


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


def fit_arima_segment(series: pd.Series, order: tuple[int, int, int]) -> object:
    """
    Fit ARIMA(p, d, q) on a pandas Series using statsmodels.

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
    model = ARIMA(series, order=order)
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
) -> list[dict]:
    """
    Expanding-window temporal cross-validation for ARIMA.

    Reuses temporal_cv_generic from regression.py to keep CV methodology
    consistent across ARIMA and Prophet (see RESEARCH.md Pattern 7).

    Parameters
    ----------
    series : pd.Series
        Annual time series in chronological order.
    order : tuple[int, int, int]
        (p, d, q) order — typically from select_arima_order().
    n_splits : int
        Number of expanding-window folds. Default 3.
        With ~20 annual observations, 3–4 folds is typical.

    Returns
    -------
    list[dict]
        One dict per fold with keys: fold, train_end, test_end, rmse, mape.
    """
    values = series.values

    def fit_fn(train: np.ndarray):
        return ARIMA(train, order=order).fit()

    def forecast_fn(fitted, steps: int) -> np.ndarray:
        pm = fitted.get_forecast(steps=steps).predicted_mean
        # predicted_mean may be pd.Series or np.ndarray depending on whether the
        # training data was a Series or ndarray — normalise to ndarray.
        return np.asarray(pm)

    return temporal_cv_generic(values, fit_fn, forecast_fn, n_splits=n_splits)
