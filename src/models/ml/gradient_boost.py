"""
LightGBM point estimator for residual correction.

Trains on Phase 2 statistical residuals to learn systematic biases that
the statistical models missed. Feature engineering produces lag and time
features per segment.

Exports:
- build_residual_features: construct feature matrix from residuals DataFrame
- fit_lgbm_point: train LGBMRegressor on feature matrix
- lgbm_cv_for_segment: expanding-window CV using temporal_cv_generic
- FEATURE_COLS: module-level list of feature column names
"""
import numpy as np
import pandas as pd
import lightgbm as lgb

from src.models.statistical.regression import temporal_cv_generic

# Module-level constant: columns used as features for LightGBM
FEATURE_COLS = ["residual_lag1", "residual_lag2", "year_norm"]


def build_residual_features(residuals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature matrix from residuals DataFrame.

    For each segment, computes two residual lags and a normalised year index.
    Rows where lag1 or lag2 is NaN (i.e., the first two years per segment)
    are dropped.

    Parameters
    ----------
    residuals_df : pd.DataFrame
        Schema: year (int), segment (str), residual (float), model_type (str).
        Typically ~60 rows (4 segments x 15 years).

    Returns
    -------
    pd.DataFrame
        Columns: year, segment, residual, model_type, residual_lag1,
        residual_lag2, year_norm. Rows: (n_years - 2) * n_segments.
    """
    df = residuals_df.copy()
    df = df.sort_values(["segment", "year"]).reset_index(drop=True)

    # Lag features within each segment — shift by 1 and 2 positions
    df["residual_lag1"] = df.groupby("segment")["residual"].shift(1)
    df["residual_lag2"] = df.groupby("segment")["residual"].shift(2)

    # Year normalisation: maps 2010 -> 0.0, 2024 -> 1.0
    df["year_norm"] = (df["year"] - 2010) / 14.0

    # Drop rows where lag features are NaN (first two years per segment)
    df = df.dropna(subset=["residual_lag1", "residual_lag2"]).reset_index(drop=True)

    return df


def fit_lgbm_point(X: np.ndarray, y: np.ndarray) -> lgb.LGBMRegressor:
    """
    Train a LightGBM regression model on the residual feature matrix.

    Parameters
    ----------
    X : np.ndarray, shape (n_samples, n_features)
        Feature matrix (output of build_residual_features[FEATURE_COLS].values).
    y : np.ndarray, shape (n_samples,)
        Target residuals.

    Returns
    -------
    lgb.LGBMRegressor
        Fitted model with a predict() method.
    """
    model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        num_leaves=7,
        min_child_samples=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,
    )
    model.fit(X, y)
    return model


def lgbm_cv_for_segment(
    residual_series: np.ndarray,
    feature_matrix: np.ndarray,
    n_splits: int = 3,
) -> list[dict]:
    """
    Expanding-window cross-validation for the LightGBM point estimator.

    Reuses temporal_cv_generic from the statistical models layer. Because
    temporal_cv_generic passes only y-slices to fit_fn/forecast_fn, the
    feature matrix is aligned via a closure with a mutable training-size
    tracker.

    Parameters
    ----------
    residual_series : np.ndarray, shape (n_samples,)
        Residual values in chronological order (y target).
    feature_matrix : np.ndarray, shape (n_samples, n_features)
        Feature matrix aligned row-for-row with residual_series.
    n_splits : int
        Number of expanding CV folds (default 3).

    Returns
    -------
    list[dict]
        One dict per fold with keys: fold, train_end, test_end, rmse, mape.
    """
    # Mutable container so the closure can write back the training size
    _state = {"train_size": 0}

    def fit_fn(train_y: np.ndarray) -> lgb.LGBMRegressor:
        """Fit LightGBM on training slice; record training size for forecast_fn alignment."""
        n = len(train_y)
        _state["train_size"] = n
        X_train = feature_matrix[:n]
        return fit_lgbm_point(X_train, train_y)

    def forecast_fn(model: lgb.LGBMRegressor, steps: int) -> np.ndarray:
        """Predict test slice using feature rows aligned after the training window."""
        start = _state["train_size"]
        X_test = feature_matrix[start : start + steps]
        return model.predict(X_test)

    return temporal_cv_generic(
        series=residual_series,
        fit_fn=fit_fn,
        forecast_fn=forecast_fn,
        n_splits=n_splits,
    )
