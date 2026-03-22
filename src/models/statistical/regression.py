"""
Statistical regression models for the AI industry baseline.

Provides:
- fit_top_down_ols_with_upgrade: OLS with diagnostic-driven upgrade to WLS or GLSAR
- temporal_cv_generic: expanding-window temporal cross-validation scaffold

OLS-to-WLS-to-GLSAR upgrade chain rationale:
Starting with OLS and upgrading diagnostically is more defensible than pre-selecting
WLS or GLSAR because the upgrade decision is data-driven and documented. OLS provides
the diagnostic residuals needed to detect heteroscedasticity (Breusch-Pagan) and
autocorrelation (Ljung-Box). If OLS assumptions are met, OLS is retained — using a
more complex model without evidence wastes degrees of freedom.

The diagnostics dict always captures the OLS-layer statistics even when the final
model is WLS or GLSAR, preserving traceability: reviewers can see what the data
suggested and why the upgrade was triggered.

See RESEARCH.md Pattern 7 (Temporal CV) and Pattern 8 (OLS Diagnostic-Driven Upgrade).
See docs/ASSUMPTIONS.md section Modeling Assumptions for the regression upgrade criteria.
"""
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from statsmodels.regression.linear_model import GLSAR, OLS, WLS
from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan


def fit_top_down_ols_with_upgrade(
    y: np.ndarray,
    X: np.ndarray,
) -> tuple:
    """
    Fit OLS regression with diagnostic-driven upgrade to WLS or GLSAR.

    Upgrade chain:
    1. Fit OLS
    2. Breusch-Pagan test for heteroscedasticity (p < 0.05 → upgrade to WLS)
    3. Ljung-Box test on residuals for autocorrelation (p < 0.05 → upgrade to GLSAR)
    4. If neither diagnostic triggers, keep OLS

    Parameters
    ----------
    y : np.ndarray, shape (n,)
        Dependent variable (e.g., GDP share of AI market).
    X : np.ndarray, shape (n, k)
        Design matrix including constant column. Use statsmodels.api.add_constant(X)
        before calling this function.

    Returns
    -------
    final_res : RegressionResults
        Fitted model results. Has .params, .resid, .fittedvalues, .rsquared attributes.
    model_type : str
        Human-readable description of which model was fitted and why (for ASSUMPTIONS.md).
    diagnostics : dict
        Keys: bp_stat, bp_pval, lb_pval, r2, r2_adj
        OLS diagnostic values — always from the initial OLS fit regardless of upgrade.
    """
    # Step 1: OLS baseline
    ols_res = OLS(y, X).fit()

    # Step 2: Breusch-Pagan heteroscedasticity test
    bp_stat, bp_pval, _, _ = het_breuschpagan(ols_res.resid, X)

    # Step 3: Ljung-Box residual autocorrelation test (lag=1)
    lb_result = acorr_ljungbox(ols_res.resid, lags=[1], return_df=True)
    lb_pval = lb_result["lb_pvalue"].iloc[0]

    # Step 4: Diagnostic-driven upgrade
    if bp_pval < 0.05:
        weights = 1.0 / (ols_res.fittedvalues ** 2 + 1e-8)
        final_res = WLS(y, X, weights=weights).fit()
        model_type = f"WLS (heteroscedasticity detected, BP p={bp_pval:.3f})"
    elif lb_pval < 0.05:
        final_res = GLSAR(y, X, rho=1).iterative_fit(maxiter=10)
        model_type = f"GLSAR (autocorrelation detected, LB p={lb_pval:.3f})"
    else:
        final_res = ols_res
        model_type = "OLS (no heteroscedasticity or autocorrelation detected)"

    diagnostics = {
        "bp_stat": float(bp_stat),
        "bp_pval": float(bp_pval),
        "lb_pval": float(lb_pval),
        "r2": float(ols_res.rsquared),
        "r2_adj": float(ols_res.rsquared_adj),
    }
    return final_res, model_type, diagnostics


def temporal_cv_generic(
    series: np.ndarray,
    fit_fn: callable,
    forecast_fn: callable,
    n_splits: int = 3,
) -> list[dict]:
    """
    Expanding-window temporal cross-validation scaffold.

    Uses sklearn TimeSeriesSplit to generate non-overlapping expanding folds.
    For each fold:
    1. Fit model on training window (fit_fn receives training slice)
    2. Forecast test window (forecast_fn receives fitted model + steps)
    3. Compute RMSE and MAPE against actual test values

    No leakage guarantee: fit_fn is called exclusively on training indices.
    Each fold is chronologically ordered — no shuffling.

    Parameters
    ----------
    series : np.ndarray, shape (n,)
        Time series values in chronological order.
    fit_fn : callable
        Signature: fit_fn(train: np.ndarray) -> fitted_model
        Fits a model on the training slice and returns a fitted object.
    forecast_fn : callable
        Signature: forecast_fn(fitted_model, steps: int) -> np.ndarray
        Generates `steps` out-of-sample forecasts.
    n_splits : int
        Number of expanding-window CV folds. Default 3.
        With ~20 annual observations, 3–4 folds is typical.

    Returns
    -------
    list[dict]
        One dict per fold, each containing:
        - fold: int, zero-indexed fold number
        - train_end: int, last index of training set
        - test_end: int, last index of test set
        - rmse: float, root mean squared error on test fold
        - mape: float, mean absolute percentage error on test fold (%)
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    results = []
    for i, (train_idx, test_idx) in enumerate(tscv.split(series)):
        train = series[train_idx]
        test = series[test_idx]
        fitted = fit_fn(train)
        forecast = forecast_fn(fitted, steps=len(test))
        rmse = float(np.sqrt(np.mean((test - forecast) ** 2)))
        mape = float(np.mean(np.abs((test - forecast) / (test + 1e-10))) * 100)
        results.append({
            "fold": i,
            "train_end": int(train_idx[-1]),
            "test_end": int(test_idx[-1]),
            "rmse": rmse,
            "mape": mape,
        })
    return results
