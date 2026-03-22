"""
Unit tests for LightGBM point estimator, feature engineering, CV, and quantile models.

Uses synthetic fixtures — no live parquet files required.
"""
import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]
YEARS = list(range(2010, 2025))  # 15 years


@pytest.fixture
def synthetic_residuals_df():
    """4 segments x 15 years = 60 rows. Matches residuals_statistical.parquet schema."""
    rng = np.random.default_rng(42)
    rows = []
    for seg in SEGMENTS:
        for year in YEARS:
            rows.append({
                "year": year,
                "segment": seg,
                "residual": float(rng.normal(0, 1)),
                "model_type": "arima",
            })
    return pd.DataFrame(rows)


@pytest.fixture
def feature_df(synthetic_residuals_df):
    from src.models.ml.gradient_boost import build_residual_features
    return build_residual_features(synthetic_residuals_df)


@pytest.fixture
def xy(feature_df):
    from src.models.ml.gradient_boost import FEATURE_COLS
    X = feature_df[FEATURE_COLS].values
    y = feature_df["residual"].values
    return X, y


# ---------------------------------------------------------------------------
# Task 1: Feature Engineering
# ---------------------------------------------------------------------------

class TestFeatureEngineering:

    def test_build_residual_features_shape(self, synthetic_residuals_df):
        """4 segments x 15 years, 2 lags dropped per segment => 4 * 13 = 52 rows."""
        from src.models.ml.gradient_boost import build_residual_features
        result = build_residual_features(synthetic_residuals_df)
        assert len(result) == 4 * 13  # 52 rows
        assert "residual_lag1" in result.columns
        assert "residual_lag2" in result.columns
        assert "year_norm" in result.columns
        assert result.shape[1] >= 3 + 1  # at least residual_lag1, residual_lag2, year_norm + residual

    def test_lag_values_correct(self, synthetic_residuals_df):
        """residual_lag1 for year=2012 segment X equals residual for year=2011 segment X."""
        from src.models.ml.gradient_boost import build_residual_features
        result = build_residual_features(synthetic_residuals_df)
        for seg in SEGMENTS:
            row_2012 = result[(result["segment"] == seg) & (result["year"] == 2012)]
            row_2011 = synthetic_residuals_df[
                (synthetic_residuals_df["segment"] == seg) & (synthetic_residuals_df["year"] == 2011)
            ]
            assert len(row_2012) == 1
            assert len(row_2011) == 1
            expected = float(row_2011["residual"].iloc[0])
            actual = float(row_2012["residual_lag1"].iloc[0])
            assert abs(actual - expected) < 1e-9

    def test_no_nan_in_output(self, feature_df):
        """After dropna on lags, no NaN values remain."""
        assert feature_df.isnull().sum().sum() == 0


# ---------------------------------------------------------------------------
# Task 1: LightGBM Point Model
# ---------------------------------------------------------------------------

class TestLGBMPointModel:

    def test_fit_lgbm_point_returns_model(self, xy):
        """fit_lgbm_point returns an LGBMRegressor with a predict method."""
        from src.models.ml.gradient_boost import fit_lgbm_point
        import lightgbm as lgb
        X, y = xy
        model = fit_lgbm_point(X, y)
        assert isinstance(model, lgb.LGBMRegressor)
        assert hasattr(model, "predict")

    def test_fit_lgbm_point_predictions_shape(self, xy):
        """model.predict(X) returns array of shape (n_samples,)."""
        from src.models.ml.gradient_boost import fit_lgbm_point
        X, y = xy
        model = fit_lgbm_point(X, y)
        preds = model.predict(X)
        assert preds.shape == (len(X),)

    def test_lgbm_cv_returns_metrics(self, synthetic_residuals_df):
        """lgbm_cv_for_segment returns list of dicts each containing 'rmse' key > 0."""
        from src.models.ml.gradient_boost import (
            build_residual_features,
            lgbm_cv_for_segment,
            FEATURE_COLS,
        )
        seg_df = synthetic_residuals_df[
            synthetic_residuals_df["segment"] == "ai_hardware"
        ].copy()
        # Build feature matrix for this single segment
        feat = build_residual_features(synthetic_residuals_df)
        seg_feat = feat[feat["segment"] == "ai_hardware"].sort_values("year")
        X = seg_feat[FEATURE_COLS].values
        y = seg_feat["residual"].values
        results = lgbm_cv_for_segment(y, X, n_splits=3)
        assert isinstance(results, list)
        assert len(results) == 3
        for fold in results:
            assert "rmse" in fold
            assert isinstance(fold["rmse"], float)
            assert fold["rmse"] >= 0


# ---------------------------------------------------------------------------
# Task 2: Quantile Models (RED tests - will fail until Task 2 is implemented)
# ---------------------------------------------------------------------------

class TestQuantileModels:

    @pytest.fixture
    def xy_quantile(self, xy):
        return xy

    def test_fit_lgbm_quantile_returns_model(self, xy_quantile):
        """fit_lgbm_quantile(X, y, alpha=0.10) returns LGBMRegressor."""
        from src.models.ml.quantile_models import fit_lgbm_quantile
        import lightgbm as lgb
        X, y = xy_quantile
        model = fit_lgbm_quantile(X, y, alpha=0.10)
        assert isinstance(model, lgb.LGBMRegressor)

    def test_quantile_objective_set(self, xy_quantile):
        """Model trained with alpha=0.10 has objective='quantile' in get_params()."""
        from src.models.ml.quantile_models import fit_lgbm_quantile
        X, y = xy_quantile
        model = fit_lgbm_quantile(X, y, alpha=0.10)
        params = model.get_params()
        assert params["objective"] == "quantile"

    def test_fit_all_quantile_models_returns_four(self, xy_quantile):
        """fit_all_quantile_models(X, y) returns dict with 4 keys."""
        from src.models.ml.quantile_models import fit_all_quantile_models
        X, y = xy_quantile
        result = fit_all_quantile_models(X, y)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"ci80_lower", "ci80_upper", "ci95_lower", "ci95_upper"}

    def test_all_models_predict(self, xy_quantile):
        """All 4 models produce predictions of shape (n_samples,)."""
        from src.models.ml.quantile_models import fit_all_quantile_models
        X, y = xy_quantile
        models = fit_all_quantile_models(X, y)
        for key, model in models.items():
            preds = model.predict(X)
            assert preds.shape == (len(X),), f"{key} predictions wrong shape"

    def test_quantile_alphas_dict(self):
        """QUANTILE_ALPHAS maps ci80_lower->0.10, ci80_upper->0.90, ci95_lower->0.025, ci95_upper->0.975."""
        from src.models.ml.quantile_models import QUANTILE_ALPHAS
        assert QUANTILE_ALPHAS["ci80_lower"] == 0.10
        assert QUANTILE_ALPHAS["ci80_upper"] == 0.90
        assert QUANTILE_ALPHAS["ci95_lower"] == 0.025
        assert QUANTILE_ALPHAS["ci95_upper"] == 0.975
