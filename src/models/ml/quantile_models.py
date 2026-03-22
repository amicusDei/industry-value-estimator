"""
LightGBM quantile regression models for confidence interval bounds.

Trains four quantile regressors on the same feature matrix as the point
estimator to produce 80% and 95% prediction interval bounds.

Exports:
- QUANTILE_ALPHAS: dict mapping CI bound names to alpha values
- fit_lgbm_quantile: train one LGBMRegressor with quantile objective
- fit_all_quantile_models: train all four bound models and return as dict
"""
import numpy as np
import lightgbm as lgb

# Quantile alpha levels for each CI bound
# 80% CI: [0.10, 0.90]  — 80% coverage
# 95% CI: [0.025, 0.975] — 95% coverage
QUANTILE_ALPHAS: dict[str, float] = {
    "ci80_lower": 0.10,
    "ci80_upper": 0.90,
    "ci95_lower": 0.025,
    "ci95_upper": 0.975,
}


def fit_lgbm_quantile(
    X: np.ndarray,
    y: np.ndarray,
    alpha: float,
) -> lgb.LGBMRegressor:
    """
    Train a LightGBM quantile regression model.

    Uses the same hyperparameters as the point estimator but with
    objective="quantile" and the specified alpha quantile level.

    Parameters
    ----------
    X : np.ndarray, shape (n_samples, n_features)
        Feature matrix (same columns as used for the point estimator).
    y : np.ndarray, shape (n_samples,)
        Target residuals.
    alpha : float
        Quantile level, in (0, 1). For example 0.10 for the lower 80% bound.

    Returns
    -------
    lgb.LGBMRegressor
        Fitted quantile model with a predict() method.
    """
    model = lgb.LGBMRegressor(
        objective="quantile",
        alpha=alpha,
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        num_leaves=7,
        min_child_samples=3,
        subsample=0.8,
        random_state=42,
        verbose=-1,
    )
    model.fit(X, y)
    return model


def fit_all_quantile_models(
    X: np.ndarray,
    y: np.ndarray,
) -> dict[str, lgb.LGBMRegressor]:
    """
    Train all four quantile models for 80% and 95% CI bounds.

    Parameters
    ----------
    X : np.ndarray, shape (n_samples, n_features)
        Feature matrix.
    y : np.ndarray, shape (n_samples,)
        Target residuals.

    Returns
    -------
    dict[str, lgb.LGBMRegressor]
        Keys: ci80_lower, ci80_upper, ci95_lower, ci95_upper.
        Each value is a fitted LGBMRegressor with quantile objective.
    """
    return {
        name: fit_lgbm_quantile(X, y, alpha=alpha)
        for name, alpha in QUANTILE_ALPHAS.items()
    }
