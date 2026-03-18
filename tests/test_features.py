"""
Tests for src/processing/features.py and src/models/statistical/regression.py.

Task 1: Feature engineering — indicator matrix, PCA composite, manual weights, stationarity
Task 2: OLS diagnostic-driven upgrade chain, temporal cross-validation helper
"""
import numpy as np
import pandas as pd
import pytest


# ============================================================
# Task 1: Feature Engineering
# ============================================================


class TestBuildIndicatorMatrix:
    def _make_long_df(self, n_years=10, indicators=None):
        """Synthetic long-format DataFrame with 3 indicators x n_years years."""
        if indicators is None:
            indicators = ["ind_a", "ind_b", "ind_c"]
        rng = np.random.default_rng(42)
        rows = []
        for year in range(2010, 2010 + n_years):
            for ind in indicators:
                rows.append(
                    {
                        "year": year,
                        "economy": "USA",
                        "indicator": ind,
                        "value_real_2020": rng.normal(10, 1),
                        "industry_segment": "ai_hardware",
                    }
                )
        return pd.DataFrame(rows)

    def test_build_indicator_matrix_shape(self):
        from src.processing.features import build_indicator_matrix

        df = self._make_long_df(n_years=10, indicators=["ind_a", "ind_b", "ind_c"])
        matrix, year_idx = build_indicator_matrix(df, ["ind_a", "ind_b", "ind_c"])
        assert matrix.shape == (10, 3)
        assert len(year_idx) == 10

    def test_build_indicator_matrix_handles_missing(self):
        from src.processing.features import build_indicator_matrix

        df = self._make_long_df(n_years=10, indicators=["ind_a", "ind_b", "ind_c"])
        # Introduce a NaN for ind_b in year 2010
        mask = (df["year"] == 2010) & (df["indicator"] == "ind_b")
        df.loc[mask, "value_real_2020"] = np.nan
        matrix, _ = build_indicator_matrix(df, ["ind_a", "ind_b", "ind_c"])
        # After forward-fill (+ bfill), no NaN should remain
        assert not np.isnan(matrix).any()


class TestPcaComposite:
    def _make_matrix(self, n_rows=10, n_cols=3, seed=42):
        rng = np.random.default_rng(seed)
        return rng.normal(0, 1, size=(n_rows, n_cols))

    def test_pca_composite_shape(self):
        from src.processing.features import build_pca_composite

        matrix = self._make_matrix(n_rows=10, n_cols=3)
        scores, explained, pipe = build_pca_composite(matrix, train_end_idx=7)
        assert scores.shape == (10,)
        assert isinstance(explained, float)
        assert 0 < explained <= 1.0

    def test_pca_no_leakage(self):
        from src.processing.features import build_pca_composite

        matrix = self._make_matrix(n_rows=10, n_cols=3)
        scores, explained, pipe = build_pca_composite(matrix, train_end_idx=7)
        # Scaler mean_ must match mean of training portion only (first 7 rows)
        expected_mean = matrix[:7].mean(axis=0)
        np.testing.assert_allclose(
            pipe.named_steps["scaler"].mean_,
            expected_mean,
            rtol=1e-10,
            err_msg="Scaler mean_ does not match training-only mean — PCA leakage detected",
        )


class TestManualComposite:
    def test_manual_composite_shape_and_value(self):
        from src.processing.features import build_manual_composite

        rng = np.random.default_rng(42)
        matrix = rng.normal(0, 1, size=(10, 3))
        weights = [0.4, 0.3, 0.3]
        result = build_manual_composite(matrix, weights, train_end_idx=7)
        assert result.shape == (10,)

        # Verify: standardize using train mean/std, then dot with weights
        mean = matrix[:7].mean(axis=0)
        std = matrix[:7].std(axis=0)
        standardized = (matrix - mean) / (std + 1e-10)
        expected = np.dot(standardized, np.array(weights))
        np.testing.assert_allclose(result, expected, rtol=1e-10)


class TestAssessStationarity:
    def test_stationarity_stationary(self):
        from src.processing.features import assess_stationarity

        # seed=1 produces white noise with ADF p~0.000 (rejects unit root) and
        # KPSS p=0.10 (fails to reject stationarity) → d=0 recommendation is reliable
        rng = np.random.default_rng(1)
        series = rng.standard_normal(50)
        result = assess_stationarity(series)
        assert "adf_stationary" in result
        assert "kpss_stationary" in result
        assert "adf_pval" in result
        assert "kpss_pval" in result
        assert "recommendation_d" in result
        # Pure white noise is stationary
        assert result["recommendation_d"] == 0

    def test_stationarity_trending(self):
        from src.processing.features import assess_stationarity

        rng = np.random.default_rng(7)
        series = np.cumsum(rng.standard_normal(50))
        result = assess_stationarity(series)
        # A random walk is non-stationary — should recommend differencing
        assert result["recommendation_d"] == 1


# ============================================================
# Task 2: Regression — OLS Upgrade Chain
# ============================================================


class TestRegression:
    def _make_simple_ols_data(self, n=20, seed=42):
        rng = np.random.default_rng(seed)
        x = rng.uniform(1, 10, size=n)
        y = 2 * x + rng.normal(0, 0.5, size=n)
        import statsmodels.api as sm

        X = sm.add_constant(x)
        return y, X

    def test_ols_fits_basic(self):
        from src.models.statistical.regression import fit_top_down_ols_with_upgrade

        y, X = self._make_simple_ols_data()
        result = fit_top_down_ols_with_upgrade(y, X)
        assert len(result) == 3
        model, model_type, diagnostics = result
        assert hasattr(model, "params")
        assert isinstance(model_type, str)
        assert isinstance(diagnostics, dict)

    def test_ols_diagnostics_keys(self):
        from src.models.statistical.regression import fit_top_down_ols_with_upgrade

        y, X = self._make_simple_ols_data()
        _, _, diagnostics = fit_top_down_ols_with_upgrade(y, X)
        assert "bp_stat" in diagnostics
        assert "bp_pval" in diagnostics
        assert "lb_pval" in diagnostics

    def test_ols_upgrade_to_wls_on_heteroscedastic_data(self):
        from src.models.statistical.regression import fit_top_down_ols_with_upgrade

        rng = np.random.default_rng(99)
        n = 20
        x = np.arange(1, n + 1, dtype=float)
        # Variance grows with x — classic heteroscedasticity
        y = 3.0 * x + rng.normal(0, 1, size=n) * x
        import statsmodels.api as sm

        X = sm.add_constant(x)
        _, model_type, _ = fit_top_down_ols_with_upgrade(y, X)
        assert "WLS" in model_type, (
            f"Expected WLS upgrade on heteroscedastic data, got: {model_type}"
        )


# ============================================================
# Task 2: Temporal Cross-Validation
# ============================================================


class TestTemporalCV:
    def _make_linear_fit_fn(self):
        """Simple linear extrapolation as fit_fn / forecast_fn for CV scaffold testing."""

        def fit_fn(train: np.ndarray):
            x = np.arange(len(train), dtype=float)
            coeffs = np.polyfit(x, train, 1)
            return coeffs  # (slope, intercept)

        def forecast_fn(fitted, steps: int) -> np.ndarray:
            slope, intercept = fitted
            return np.array(
                [slope * i + intercept for i in range(len(fitted) if False else steps)]
            )

        return fit_fn, forecast_fn

    def test_temporal_cv_folds(self):
        from src.models.statistical.regression import temporal_cv_generic

        series = np.arange(1, 21, dtype=float)
        fit_fn, forecast_fn = self._make_linear_fit_fn()
        results = temporal_cv_generic(series, fit_fn, forecast_fn, n_splits=3)
        assert len(results) == 3
        for fold_result in results:
            for key in ("fold", "train_end", "test_end", "rmse", "mape"):
                assert key in fold_result, f"Missing key '{key}' in fold result"

    def test_temporal_cv_no_overlap(self):
        from src.models.statistical.regression import temporal_cv_generic

        series = np.arange(1, 21, dtype=float)
        fit_fn, forecast_fn = self._make_linear_fit_fn()
        results = temporal_cv_generic(series, fit_fn, forecast_fn, n_splits=3)
        for fold_result in results:
            # Train end must be strictly before test end
            assert fold_result["train_end"] < fold_result["test_end"], (
                f"Fold {fold_result['fold']}: train_end={fold_result['train_end']} "
                f">= test_end={fold_result['test_end']} — overlap detected"
            )
