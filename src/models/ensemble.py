"""
Ensemble combiner for blending statistical baseline and LightGBM correction.

Uses per-segment inverse-RMSE weighting to combine forecasts. The LightGBM
output is a residual correction (additive), not an independent full forecast.

Exports:
- compute_ensemble_weights: inverse-RMSE weights summing to 1.0
- blend_forecasts: additive blend (stat_pred + lgbm_weight * correction)
"""
import numpy as np


def compute_ensemble_weights(
    stat_cv_rmse: float,
    lgbm_cv_rmse: float,
) -> tuple[float, float]:
    """
    Compute inverse-RMSE ensemble weights for statistical and LightGBM models.

    Uses inverse-RMSE weighting: models with lower error get higher weight.
    A small epsilon (1e-10) prevents division by zero when RMSE = 0.

    Parameters
    ----------
    stat_cv_rmse : float
        Cross-validated RMSE for the statistical baseline model.
    lgbm_cv_rmse : float
        Cross-validated RMSE for the LightGBM correction model.

    Returns
    -------
    tuple[float, float]
        (stat_weight, lgbm_weight) — both positive, summing to 1.0.
    """
    inv_stat = 1.0 / (stat_cv_rmse + 1e-10)
    inv_lgbm = 1.0 / (lgbm_cv_rmse + 1e-10)
    total = inv_stat + inv_lgbm
    return float(inv_stat / total), float(inv_lgbm / total)


def blend_forecasts(
    stat_pred: "np.ndarray | float",
    lgbm_correction: "np.ndarray | float",
    stat_weight: float,
    lgbm_weight: float,
) -> "np.ndarray | float":
    """
    Additively blend statistical forecast with LightGBM residual correction.

    This is an ADDITIVE blend, not a convex combination. LightGBM produces
    a residual correction term, not an independent full forecast. The stat_pred
    provides the baseline level; lgbm_correction adjusts it.

    Formula: stat_pred + lgbm_weight * lgbm_correction
    (stat_weight is accepted for API symmetry but is not used in the blend)

    Parameters
    ----------
    stat_pred : np.ndarray or float
        Statistical model forecast (full level, e.g. in trillions USD).
    lgbm_correction : np.ndarray or float
        LightGBM predicted residual correction.
    stat_weight : float
        Weight for statistical model (accepted for API symmetry, not used).
    lgbm_weight : float
        Weight for LightGBM correction term.

    Returns
    -------
    np.ndarray or float
        Blended forecast: stat_pred + lgbm_weight * lgbm_correction.
    """
    return stat_pred + lgbm_weight * lgbm_correction
