"""
LightGBM point estimator for residual correction.

Trains on Phase 2 statistical residuals to learn systematic biases that
the statistical models missed. Feature engineering produces lag and time
features per segment.

v1.1 update: feature matrix extended to include macro indicator columns
(rd_pct_gdp, ict_service_exports, patent_applications) alongside residual
lags. Macro features are optional — if the processed World Bank data does not
have >80% coverage in 2017-2025, the model falls back to residual-only features.

Exports:
- build_residual_features: construct feature matrix from residuals DataFrame
- fit_lgbm_point: train LGBMRegressor on feature matrix
- lgbm_cv_for_segment: expanding-window CV using temporal_cv_generic
- build_macro_features_for_lgbm: load World Bank macro indicators for LightGBM
- FEATURE_COLS: base residual lag feature column names
- MACRO_FEATURE_COLS: macro indicator feature column names (when available)
- ALL_FEATURE_COLS: combined feature column list (FEATURE_COLS + MACRO_FEATURE_COLS)
"""
import logging
import warnings

import numpy as np
import pandas as pd
import lightgbm as lgb

from src.models.statistical.regression import temporal_cv_generic

logger = logging.getLogger(__name__)

# Base feature columns: residual lags + time normalisation
FEATURE_COLS = ["residual_lag1", "residual_lag2", "year_norm"]

# Macro indicator columns added when available with >80% coverage in 2017-2025.
# With N=9 training observations, limit to 3 macro indicators max to avoid
# overfitting (following RESEARCH.md Pattern 5 guidance).
MACRO_FEATURE_COLS = [
    "rd_pct_gdp",           # World Bank GB.XPD.RSDV.GD.ZS — R&D spend % of GDP
    "ict_service_exports",  # World Bank BX.GSR.CCIS.CD — ICT service exports
    "patent_applications",  # World Bank IP.PAT.RESD — patent applications
]

# Combined feature list used when macro features are available
ALL_FEATURE_COLS = FEATURE_COLS + MACRO_FEATURE_COLS


def build_macro_features_for_lgbm(segment: str) -> pd.DataFrame | None:
    """
    Load macro indicators from processed World Bank data for LightGBM feature
    enrichment.

    Returns DataFrame indexed by year with macro indicator columns, restricted
    to the 2017-2025 window. Only includes indicators with >80% non-null
    coverage in that window. Returns None if coverage is insufficient for any
    indicator (falls back to residual-only features).

    Parameters
    ----------
    segment : str
        Segment ID (e.g. "ai_hardware"). Currently macro data is not segment-
        specific; argument reserved for future segment-level indicator filtering.

    Returns
    -------
    pd.DataFrame | None
        DataFrame indexed by integer year (2017-2025) with columns from
        MACRO_FEATURE_COLS that have sufficient coverage, or None if the
        processed World Bank parquet does not contain usable macro data.
    """
    try:
        from config.settings import DATA_PROCESSED
        from src.processing.features import build_indicator_matrix

        wb_path = DATA_PROCESSED / "world_bank_ai.parquet"
        if not wb_path.exists():
            logger.warning(
                "build_macro_features_for_lgbm: world_bank_ai.parquet not found — "
                "falling back to residual-only features"
            )
            return None

        df = pd.read_parquet(wb_path)

        # world_bank_ai.parquet uses flat columns (rd_pct_gdp, etc.) rather than
        # the long-format indicator/value_real_2020 schema that build_indicator_matrix
        # expects. Build macro DataFrame directly from the flat columns.
        year_col = "year" if "year" in df.columns else None
        if year_col is None:
            logger.warning(
                "build_macro_features_for_lgbm: no 'year' column in world_bank_ai.parquet — "
                "falling back to residual-only features"
            )
            return None

        # Aggregate across economies (if multiple rows per year)
        available_cols = [c for c in MACRO_FEATURE_COLS if c in df.columns]
        if not available_cols:
            logger.warning(
                "build_macro_features_for_lgbm: none of %s found in world_bank_ai.parquet "
                "— falling back to residual-only features",
                MACRO_FEATURE_COLS,
            )
            return None

        macro_df = (
            df.groupby("year")[available_cols]
            .mean()
            .sort_index()
        )

        # Filter to 2017-2025 window
        macro_df = macro_df[(macro_df.index >= 2017) & (macro_df.index <= 2025)]
        n_years = 9  # 2017-2025 inclusive

        # Coverage check: require >80% non-null in 2017-2025 window
        good_cols = []
        for col in available_cols:
            if col not in macro_df.columns:
                continue
            # Count non-null years including the full 2017-2025 range
            full_index = pd.RangeIndex(2017, 2026)
            aligned = macro_df[col].reindex(full_index)
            coverage = aligned.notna().mean()
            if coverage > 0.80:
                good_cols.append(col)
            else:
                logger.warning(
                    "build_macro_features_for_lgbm: indicator %s has %.0f%% coverage in "
                    "2017-2025 (< 80%%) — excluded from feature matrix",
                    col,
                    coverage * 100,
                )

        if not good_cols:
            logger.warning(
                "build_macro_features_for_lgbm: no macro indicators with >80%% coverage — "
                "falling back to residual-only features"
            )
            return None

        macro_df = macro_df[good_cols]

        # Reindex to full 2017-2025 range and fill gaps
        full_index = pd.RangeIndex(2017, 2026)
        macro_df = macro_df.reindex(full_index)
        macro_df = macro_df.ffill().bfill()

        logger.info(
            "build_macro_features_for_lgbm: using %d macro indicators: %s",
            len(good_cols),
            good_cols,
        )
        return macro_df

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "build_macro_features_for_lgbm: exception loading macro features (%s) — "
            "falling back to residual-only features",
            exc,
        )
        return None


def build_residual_features(
    residuals_df: pd.DataFrame,
    macro_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Build feature matrix from residuals DataFrame.

    For each segment, computes two residual lags and a normalised year index.
    Optionally merges macro indicator columns from macro_df (output of
    build_macro_features_for_lgbm). Falls back to residual-only features if
    macro_df is None or macro columns are missing.

    Rows where lag1 or lag2 is NaN (i.e., the first two years per segment)
    are dropped.

    Parameters
    ----------
    residuals_df : pd.DataFrame
        Schema: year (int), segment (str), residual (float), model_type (str).
        Typically ~60 rows (4 segments x 15 years).
    macro_df : pd.DataFrame | None
        Optional macro indicator DataFrame indexed by integer year (e.g. 2017-2025)
        with columns matching MACRO_FEATURE_COLS. Merged by year if provided.
        If None, macro features are omitted and only FEATURE_COLS are produced.

    Returns
    -------
    pd.DataFrame
        Columns: year, segment, residual, model_type, residual_lag1,
        residual_lag2, year_norm [+ macro cols if macro_df provided].
        Rows: (n_years - 2) * n_segments.
    """
    df = residuals_df.copy()
    df = df.sort_values(["segment", "year"]).reset_index(drop=True)

    # Lag features within each segment — shift by 1 and 2 positions
    df["residual_lag1"] = df.groupby("segment")["residual"].shift(1)
    df["residual_lag2"] = df.groupby("segment")["residual"].shift(2)

    # Year normalisation: maps 2010 -> 0.0, 2024 -> 1.0
    df["year_norm"] = (df["year"] - 2010) / 14.0

    # Merge macro features if provided
    if macro_df is not None:
        macro_cols = [c for c in macro_df.columns if c in MACRO_FEATURE_COLS]
        if macro_cols:
            macro_reset = macro_df[macro_cols].reset_index()
            if macro_reset.columns[0] != "year":
                macro_reset = macro_reset.rename(columns={macro_reset.columns[0]: "year"})

            # Check for columns with >20% missing before fill
            for col in macro_cols:
                missing_frac = macro_reset[col].isna().mean()
                if missing_frac > 0.20:
                    logger.warning(
                        "build_residual_features: macro column %s has %.0f%% missing before merge",
                        col,
                        missing_frac * 100,
                    )

            df = df.merge(macro_reset, on="year", how="left")

            # Fill any NaN in macro columns after merge
            for col in macro_cols:
                if col in df.columns:
                    df[col] = df[col].ffill().bfill()

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
        min_child_weight=1,      # Explicit (was implicit default)
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,           # L1 regularization to reduce overfitting
        reg_lambda=1.0,          # L2 regularization to reduce overfitting
        random_state=42,
        verbose=-1,
    )
    # Early stopping: use a validation set if enough samples, otherwise fit on all data.
    if len(X) >= 8:
        split_idx = int(len(X) * 0.75)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=10, verbose=False)],
        )
    else:
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
