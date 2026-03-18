"""Model evaluation metrics: RMSE, MAPE, R-squared, AIC/BIC/AICc, Ljung-Box, model comparison."""

import numpy as np
from statsmodels.stats.diagnostic import acorr_ljungbox


def compute_rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Root Mean Squared Error.

    Parameters
    ----------
    actual : np.ndarray
        Observed values.
    predicted : np.ndarray
        Model-predicted values.

    Returns
    -------
    float
        RMSE.
    """
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def compute_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Mean Absolute Percentage Error.

    Parameters
    ----------
    actual : np.ndarray
        Observed values. Must not contain zeros.
    predicted : np.ndarray
        Model-predicted values.

    Returns
    -------
    float
        MAPE as a percentage (e.g., 6.11 for 6.11%).

    Raises
    ------
    ValueError
        If any actual value is zero (division by zero).
    """
    actual = np.asarray(actual, dtype=float)
    if np.any(actual == 0):
        raise ValueError(
            "compute_mape: actual contains zero values; MAPE is undefined."
        )
    return float(np.mean(np.abs((actual - predicted) / actual)) * 100)


def compute_r2(actual: np.ndarray, predicted: np.ndarray) -> float:
    """
    Coefficient of Determination (R-squared).

    Parameters
    ----------
    actual : np.ndarray
        Observed values.
    predicted : np.ndarray
        Model-predicted values.

    Returns
    -------
    float
        R-squared (can be negative if model is worse than the mean).
    """
    actual = np.asarray(actual, dtype=float)
    ss_res = np.sum((actual - predicted) ** 2)
    ss_tot = np.sum((actual - np.mean(actual)) ** 2)
    return float(1.0 - ss_res / ss_tot)


def compute_aic_bic(residuals: np.ndarray, n_params: int) -> dict:
    """
    Compute AIC, BIC, and AICc from residuals.

    Uses the log-likelihood approximation for a Gaussian model:
        AIC  = n * log(SSE/n) + 2 * k
        BIC  = n * log(SSE/n) + k * log(n)
        AICc = AIC + 2k(k+1) / (n - k - 1)  [corrected for small N]

    Parameters
    ----------
    residuals : np.ndarray
        Model residuals (actual - predicted).
    n_params : int
        Number of estimated parameters (k).

    Returns
    -------
    dict
        {"aic": float, "bic": float, "aicc": float}
    """
    residuals = np.asarray(residuals, dtype=float)
    n = len(residuals)
    k = n_params
    sse = np.sum(residuals ** 2)

    aic = n * np.log(sse / n) + 2 * k
    bic = n * np.log(sse / n) + k * np.log(n)
    aicc = aic + (2 * k * (k + 1)) / (n - k - 1)

    return {"aic": float(aic), "bic": float(bic), "aicc": float(aicc)}


def ljung_box_test(residuals: np.ndarray, lags: int = 1) -> dict:
    """
    Ljung-Box test for residual autocorrelation.

    Parameters
    ----------
    residuals : np.ndarray
        Model residuals.
    lags : int
        Number of lags to test (default: 1).

    Returns
    -------
    dict
        {"statistic": float, "p_value": float}
        Values correspond to the last (highest) lag tested.
    """
    lb_result = acorr_ljungbox(residuals, lags=[lags], return_df=True)
    statistic = float(lb_result["lb_stat"].iloc[-1])
    p_value = float(lb_result["lb_pvalue"].iloc[-1])
    return {"statistic": statistic, "p_value": p_value}


def compare_models(
    arima_cv: list,
    prophet_cv: list,
    segment: str,
) -> dict:
    """
    Compare ARIMA and Prophet models based on cross-validation fold results.

    Parameters
    ----------
    arima_cv : list[dict]
        List of CV fold results for ARIMA. Each dict must have "rmse" and
        optionally "mape".
    prophet_cv : list[dict]
        List of CV fold results for Prophet. Same structure as arima_cv.
    segment : str
        Name of the AI segment being evaluated.

    Returns
    -------
    dict
        {
            "segment": str,
            "arima_mean_cv_rmse": float,
            "prophet_mean_cv_rmse": float,
            "arima_mean_cv_mape": float,
            "prophet_mean_cv_mape": float,
            "winner": str,       # "ARIMA" or "Prophet"
            "margin_pct": float, # percentage margin of winner vs. loser RMSE
        }
    """
    arima_mean_rmse = float(
        sum(r["rmse"] for r in arima_cv) / len(arima_cv)
    )
    prophet_mean_rmse = float(
        sum(r["rmse"] for r in prophet_cv) / len(prophet_cv)
    )

    arima_mapes = [r["mape"] for r in arima_cv if "mape" in r]
    prophet_mapes = [r["mape"] for r in prophet_cv if "mape" in r]
    arima_mean_mape = float(sum(arima_mapes) / len(arima_mapes)) if arima_mapes else float("nan")
    prophet_mean_mape = float(sum(prophet_mapes) / len(prophet_mapes)) if prophet_mapes else float("nan")

    winner = "ARIMA" if arima_mean_rmse <= prophet_mean_rmse else "Prophet"
    best_rmse = min(arima_mean_rmse, prophet_mean_rmse)
    worst_rmse = max(arima_mean_rmse, prophet_mean_rmse)
    margin_pct = float(abs(arima_mean_rmse - prophet_mean_rmse) / best_rmse * 100)

    return {
        "segment": segment,
        "arima_mean_cv_rmse": arima_mean_rmse,
        "prophet_mean_cv_rmse": prophet_mean_rmse,
        "arima_mean_cv_mape": arima_mean_mape,
        "prophet_mean_cv_mape": prophet_mean_mape,
        "winner": winner,
        "margin_pct": margin_pct,
    }
