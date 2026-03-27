"""
Bootstrap confidence intervals for forecast uncertainty quantification.

Resamples historical residuals with replacement, adds them to point forecasts,
and extracts empirical percentiles for 80% and 95% confidence intervals.

This replaces the parametric z-score approach (1.28σ/1.96σ) which produced
15-33% coverage instead of the target 80-95% on backtesting data.
"""

import numpy as np


def bootstrap_confidence_intervals(
    residuals: np.ndarray,
    point_forecast: np.ndarray,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> dict[str, np.ndarray]:
    """
    Compute bootstrap confidence intervals for a forecast array.

    For each bootstrap iteration, resample residuals with replacement and add
    them to the point forecast. Extract empirical percentiles from the
    resulting distribution.

    Parameters
    ----------
    residuals : np.ndarray
        Historical residuals (e.g., Prophet in-sample residuals) in the same
        units as the forecast (USD billions). Shape: (n_residuals,).
    point_forecast : np.ndarray
        Point forecast values. Shape: (n_forecast_steps,).
    n_bootstrap : int
        Number of bootstrap resamples. Default 1000.
    seed : int
        Random seed for reproducibility. Default 42.

    Returns
    -------
    dict with keys:
        ci80_lower : np.ndarray — 10th percentile (80% CI lower bound)
        ci80_upper : np.ndarray — 90th percentile (80% CI upper bound)
        ci95_lower : np.ndarray — 2.5th percentile (95% CI lower bound)
        ci95_upper : np.ndarray — 97.5th percentile (95% CI upper bound)
    """
    rng = np.random.default_rng(seed)
    n_steps = len(point_forecast)
    residuals = np.asarray(residuals).ravel()

    # Bootstrap matrix: (n_bootstrap, n_steps)
    # Each row is a resampled residual vector added to the point forecast
    resampled = rng.choice(residuals, size=(n_bootstrap, n_steps), replace=True)
    simulated_paths = point_forecast[np.newaxis, :] + resampled

    return {
        "ci80_lower": np.percentile(simulated_paths, 10, axis=0),
        "ci80_upper": np.percentile(simulated_paths, 90, axis=0),
        "ci95_lower": np.percentile(simulated_paths, 2.5, axis=0),
        "ci95_upper": np.percentile(simulated_paths, 97.5, axis=0),
    }
