"""
Serialization round-trip tests for Phase 3 ML pipeline.

Tests:
- test_save_and_load_lgbm_model: joblib round-trip for LGBMRegressor
- test_save_and_load_ensemble_weights: joblib round-trip for weights dict
- test_forecast_parquet_schema: parquet output has all 10 required columns
- test_forecast_parquet_no_nan: no NaN values in CI and point estimate columns
"""
import numpy as np
import pandas as pd
import joblib
import pytest

import lightgbm as lgb

from src.models.ml.gradient_boost import fit_lgbm_point, FEATURE_COLS
from src.inference.forecast import build_forecast_dataframe


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def small_xy():
    """Minimal X/y arrays suitable for a quick LightGBM fit."""
    rng = np.random.default_rng(0)
    X = rng.standard_normal((15, 3))
    y = rng.standard_normal(15)
    return X, y


@pytest.fixture()
def fitted_lgbm(small_xy):
    """A fitted LGBMRegressor for serialization tests."""
    X, y = small_xy
    return fit_lgbm_point(X, y)


@pytest.fixture()
def sample_forecast_df():
    """
    A minimal forecast DataFrame with all 10 required columns,
    built via build_forecast_dataframe so the schema matches production.
    """
    # Build quarterly year_quarters from 2010Q1 through 2030Q4
    year_quarters = [(y, q) for y in range(2010, 2031) for q in range(1, 5)]
    is_forecast = [False] * (15 * 4) + [True] * (6 * 4)
    rng = np.random.default_rng(1)
    n = len(year_quarters)

    segment_forecasts = {
        "ai_software": {
            "year_quarters": year_quarters,
            "point_estimates": rng.uniform(50, 200, n),
            "ci80_lower": rng.uniform(40, 180, n),
            "ci80_upper": rng.uniform(60, 220, n),
            "ci95_lower": rng.uniform(30, 160, n),
            "ci95_upper": rng.uniform(70, 240, n),
            "is_forecast": is_forecast,
        }
    }
    return build_forecast_dataframe(segment_forecasts, data_vintage="2024-Q4")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = [
    "year",
    "quarter",
    "segment",
    "point_estimate_real_2020",
    "point_estimate_nominal",
    "ci80_lower",
    "ci80_upper",
    "ci95_lower",
    "ci95_upper",
    "ci80_lower_nominal",
    "ci80_upper_nominal",
    "ci95_lower_nominal",
    "ci95_upper_nominal",
    "is_forecast",
    "data_vintage",
]

CI_POINT_COLS = [
    "point_estimate_real_2020",
    "point_estimate_nominal",
    "ci80_lower",
    "ci80_upper",
    "ci95_lower",
    "ci95_upper",
]


def test_save_and_load_lgbm_model(tmp_path, fitted_lgbm, small_xy):
    """joblib.dump / joblib.load round-trip: predictions must be identical."""
    X, _ = small_xy
    path = tmp_path / "test_lgbm.joblib"

    preds_before = fitted_lgbm.predict(X)
    joblib.dump(fitted_lgbm, path)

    loaded = joblib.load(path)
    preds_after = loaded.predict(X)

    assert isinstance(loaded, lgb.LGBMRegressor), "Loaded object must be LGBMRegressor"
    np.testing.assert_array_equal(
        preds_before,
        preds_after,
        err_msg="Predictions changed after joblib round-trip",
    )


def test_save_and_load_ensemble_weights(tmp_path):
    """joblib.dump / joblib.load round-trip for a weights dict."""
    weights = {
        "ai_hardware": {"stat_weight": 0.4, "lgbm_weight": 0.6},
        "ai_software": {"stat_weight": 0.35, "lgbm_weight": 0.65},
    }
    path = tmp_path / "ensemble_weights.joblib"

    joblib.dump(weights, path)
    loaded = joblib.load(path)

    assert loaded == weights, "Ensemble weights changed after joblib round-trip"


def test_forecast_parquet_schema(tmp_path, sample_forecast_df):
    """
    Forecast DataFrame saved to parquet and reloaded must have all 10 required columns.
    """
    parquet_path = tmp_path / "forecasts_ensemble.parquet"
    sample_forecast_df.to_parquet(parquet_path, index=False)

    loaded = pd.read_parquet(parquet_path)

    for col in REQUIRED_COLUMNS:
        assert col in loaded.columns, f"Missing column: {col}"

    assert set(loaded.columns) == set(REQUIRED_COLUMNS), (
        f"Unexpected columns: {set(loaded.columns) - set(REQUIRED_COLUMNS)}"
    )


def test_forecast_parquet_no_nan(tmp_path, sample_forecast_df):
    """
    Loaded parquet must have zero NaN values in CI and point estimate columns.
    """
    parquet_path = tmp_path / "forecasts_ensemble.parquet"
    sample_forecast_df.to_parquet(parquet_path, index=False)

    loaded = pd.read_parquet(parquet_path)

    for col in CI_POINT_COLS:
        n_nans = loaded[col].isna().sum()
        assert n_nans == 0, f"Column '{col}' has {n_nans} NaN values"
