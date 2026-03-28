"""
Ensemble combiner for blending statistical baseline and LightGBM correction.

Uses per-segment inverse-RMSE weighting to combine forecasts. The LightGBM
output is a residual correction (additive), not an independent full forecast.

Additive blend vs. convex combination: Most ensemble methods use a convex combination
(w1 * model1 + w2 * model2 = total, w1 + w2 = 1). Here we use an additive blend
because LightGBM is trained on residuals — it does not produce a full forecast level,
only a correction to the statistical baseline. Formula: stat_pred + lgbm_weight * correction.
The stat_pred is always used at 100% (no separate stat_weight needed).

Inverse-RMSE weighting: models with lower out-of-sample CV error receive higher weight.
The epsilon guard (1e-10) prevents division by zero for a model with RMSE ≈ 0 (a
near-perfect fit on synthetic data): in that case the near-zero-RMSE model receives
weight ≈ 1.0 and the other model weight ≈ 0.0, which is the correct behaviour.

See docs/ASSUMPTIONS.md section Modeling Assumptions for ensemble weighting strategy
and the additive vs. parallel blend decision.

Exports:
- compute_ensemble_weights: inverse-RMSE weights summing to 1.0
- blend_forecasts: additive blend (stat_pred + lgbm_weight * correction)
- compute_source_disagreement_columns: add anchor p25/p75 disagreement band to forecast DF
"""
import numpy as np
import pandas as pd


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
    lgbm_weight: float,
) -> "np.ndarray | float":
    """
    Additively blend statistical forecast with LightGBM residual correction.

    This is an ADDITIVE blend, not a convex combination. LightGBM produces
    a residual correction term, not an independent full forecast. The stat_pred
    provides the baseline level (always used at 100%); lgbm_correction adjusts it
    scaled by lgbm_weight.

    Formula: stat_pred + lgbm_weight * lgbm_correction

    Parameters
    ----------
    stat_pred : np.ndarray or float
        Statistical model forecast (full level, e.g. in USD billions).
    lgbm_correction : np.ndarray or float
        LightGBM predicted residual correction.
    lgbm_weight : float
        Weight for LightGBM correction term.

    Returns
    -------
    np.ndarray or float
        Blended forecast: stat_pred + lgbm_weight * lgbm_correction.
    """
    return stat_pred + lgbm_weight * lgbm_correction


def compute_source_disagreement_columns(
    forecast_df: pd.DataFrame,
    anchors_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add source disagreement band columns from market anchors to a forecast DataFrame.

    Layer 1 uncertainty: analyst source disagreement (p25/p75 spread) — distinct from
    model prediction intervals (Layer 2). These columns are populated for historical
    years where anchor data exists; NaN for forecast years without anchor data.

    Parameters
    ----------
    forecast_df : pd.DataFrame
        Forecast DataFrame with at minimum columns: year (int), segment (str).
    anchors_df : pd.DataFrame
        Market anchors DataFrame (from market_anchors_ai.parquet) with columns:
        estimate_year (int), segment (str), p25_usd_billions_real_2020 (float),
        p75_usd_billions_real_2020 (float).

    Returns
    -------
    pd.DataFrame
        Copy of forecast_df with two additional columns:
        - anchor_p25_real_2020: p25 source disagreement lower bound (NaN for forecast years)
        - anchor_p75_real_2020: p75 source disagreement upper bound (NaN for forecast years)
    """
    # Build lookup key depending on whether data is quarterly
    if "quarter" in anchors_df.columns:
        anchor_lookup = anchors_df.set_index(["estimate_year", "quarter", "segment"])[
            ["p25_usd_billions_real_2020", "p75_usd_billions_real_2020"]
        ]
    else:
        anchor_lookup = anchors_df.set_index(["estimate_year", "segment"])[
            ["p25_usd_billions_real_2020", "p75_usd_billions_real_2020"]
        ]
    df = forecast_df.copy()

    p25_values = []
    p75_values = []
    for _, row in df.iterrows():
        if "quarter" in anchors_df.columns and "quarter" in df.columns:
            key = (row["year"], int(row["quarter"]), row["segment"])
        else:
            key = (row["year"], row["segment"])
        if key in anchor_lookup.index:
            p25_values.append(anchor_lookup.loc[key, "p25_usd_billions_real_2020"])
            p75_values.append(anchor_lookup.loc[key, "p75_usd_billions_real_2020"])
        else:
            p25_values.append(float("nan"))
            p75_values.append(float("nan"))

    df["anchor_p25_real_2020"] = p25_values
    df["anchor_p75_real_2020"] = p75_values
    return df
