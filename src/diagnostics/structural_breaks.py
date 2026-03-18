"""Structural break detection: CUSUM, Chow test, Markov switching with fallback."""

import warnings

import numpy as np
import pandas as pd
import scipy.stats as stats
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.diagnostic import breaks_cusumolsresid
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression


def run_cusum(series: pd.Series) -> dict:
    """
    CUSUM test for structural breaks via OLS residuals.

    Fits constant-only OLS (y = a), then applies the CUSUM test to the
    residuals. Using constant-only removes the mean but preserves level-shift
    signals; a linear trend detrending absorbs the shift and loses power.

    Parameters
    ----------
    series : pd.Series
        Annual time series indexed by year (int).

    Returns
    -------
    dict
        {"stat": float, "p_value": float, "critical_values": array}
    """
    y = series.values.astype(float)
    X = np.ones((len(y), 1))
    resid = OLS(y, X).fit().resid
    test_stat, p_value, crit = breaks_cusumolsresid(resid, ddof=1)
    return {
        "stat": float(test_stat),
        "p_value": float(p_value),
        "critical_values": crit,
    }


def run_chow(series: pd.Series, break_idx: int) -> dict:
    """
    Chow test for a known structural break at break_idx.

    Computes the F-statistic by comparing the SSR of the full model against
    the sum of SSRs of the two sub-period models. Uses scipy F-distribution
    for the p-value.

    Parameters
    ----------
    series : pd.Series
        Annual time series indexed by year (int).
    break_idx : int
        Integer position of the breakpoint (e.g., index of year 2022).

    Returns
    -------
    dict
        {"F_stat": float, "p_value": float, "break_year": int}
    """
    y = series.values.astype(float)
    n = len(y)
    X = np.column_stack([np.ones(n), np.arange(n)])
    k = X.shape[1]

    ssr_full = OLS(y, X).fit().ssr
    ssr_pre = OLS(y[:break_idx], X[:break_idx]).fit().ssr
    ssr_post = OLS(y[break_idx:], X[break_idx:]).fit().ssr

    F = ((ssr_full - (ssr_pre + ssr_post)) / k) / (
        (ssr_pre + ssr_post) / (n - 2 * k)
    )
    p_value = 1.0 - stats.f.cdf(F, dfn=k, dfd=n - 2 * k)

    return {
        "F_stat": float(F),
        "p_value": float(p_value),
        "break_year": series.index[break_idx],
    }


def fit_markov_switching(series: pd.Series) -> dict:
    """
    Two-regime Markov switching regression with convergence fallback.

    Attempts to fit a MarkovRegression(k_regimes=2) model. On convergence
    failure or any exception — or when the series is too short (< 20
    observations) — falls back to a dummy-variable OLS where the break point
    is identified as the year of the maximum absolute first-difference.

    Parameters
    ----------
    series : pd.Series
        Annual time series indexed by year (int).

    Returns
    -------
    dict
        {
            "model_type": str  ("markov_switching" | "fallback_dummy_ols"),
            "results": fitted model object or OLSResults,
            "regimes": smoothed probabilities array or None,
            "transition_matrix": 2D array or None,
        }
    """
    y = series.values.astype(float)
    n = len(y)

    # Require at least 20 observations for Markov switching to be stable
    if n < 20:
        return _fallback_dummy_ols(series, reason="too_short")

    trend = np.arange(n)

    with warnings.catch_warnings():
        warnings.filterwarnings("error", category=Warning)
        try:
            model = MarkovRegression(
                endog=y,
                k_regimes=2,
                exog=trend.reshape(-1, 1),
                switching_variance=False,
                switching_exog=False,
            )
            results = model.fit(disp=False)
            return {
                "model_type": "markov_switching",
                "results": results,
                "regimes": results.smoothed_marginal_probabilities.values,
                "transition_matrix": results.regime_transition,
            }
        except Exception:
            return _fallback_dummy_ols(series, reason="convergence_failure")


def _fallback_dummy_ols(series: pd.Series, reason: str) -> dict:
    """Dummy-variable OLS fallback for Markov switching non-convergence."""
    y = series.values.astype(float)
    n = len(y)

    # Detect break year as the year with the maximum absolute first-difference
    if n > 1:
        diffs = np.abs(np.diff(y))
        break_pos = int(np.argmax(diffs)) + 1  # position after the jump
    else:
        break_pos = n // 2

    break_year = series.index[break_pos] if break_pos < n else series.index[-1]

    post_break = np.array(
        [1 if idx >= break_year else 0 for idx in series.index], dtype=float
    )
    X = np.column_stack([np.ones(n), np.arange(n), post_break])
    results = OLS(y, X).fit()

    return {
        "model_type": f"fallback_dummy_ols ({reason})",
        "results": results,
        "regimes": None,
        "transition_matrix": None,
    }


def summarize_breaks(segment_results: dict) -> dict:
    """
    Summarize structural break analysis across segments.

    Parameters
    ----------
    segment_results : dict
        Mapping of segment names to their individual break analysis results,
        each containing "cusum", "chow", and "markov" sub-dicts.

    Returns
    -------
    dict
        One entry per segment plus "aggregate" if present. Each entry:
        {"break_detected": bool, "break_year": int or None, "method_used": str}
    """
    summary = {}

    for segment, results in segment_results.items():
        cusum = results.get("cusum", {})
        chow = results.get("chow", {})
        markov = results.get("markov", {})

        # Break is detected if CUSUM or Chow p-value is significant
        cusum_p = cusum.get("p_value", 1.0)
        chow_p = chow.get("p_value", 1.0)
        break_detected = (cusum_p < 0.05) or (chow_p < 0.05)

        # Prefer Chow break_year (explicit breakpoint); fallback to None
        break_year = chow.get("break_year", None)

        # Determine method used
        model_type = markov.get("model_type", "unknown")
        if "fallback" in str(model_type).lower():
            method_used = "fallback_dummy_ols"
        elif model_type == "markov_switching":
            method_used = "markov_switching"
        else:
            method_used = "cusum_chow_only"

        summary[segment] = {
            "break_detected": break_detected,
            "break_year": int(break_year) if break_year is not None else None,
            "method_used": method_used,
        }

    return summary
