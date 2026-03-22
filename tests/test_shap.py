"""
Tests for SHAP attribution analysis: TreeExplainer wrapper and summary plot saver.

Tests are written before implementation (TDD RED phase).
"""
import numpy as np
import pytest


@pytest.fixture
def trained_lgbm_model():
    """Train a small LGBMRegressor on synthetic data for testing."""
    import lightgbm as lgb
    from sklearn.datasets import make_regression

    np.random.seed(42)
    X, y = make_regression(n_samples=20, n_features=3, noise=0.1, random_state=42)

    model = lgb.LGBMRegressor(
        n_estimators=10,
        max_depth=3,
        num_leaves=7,
        min_child_samples=1,
        verbose=-1,
    )
    model.fit(X, y)
    return model, X


class TestSHAPValues:
    """Tests for compute_shap_values function."""

    def test_shap_values_shape(self, trained_lgbm_model):
        """compute_shap_values returns dict with 'shap_values' of shape (n_samples, n_features)."""
        from src.inference.shap_analysis import compute_shap_values

        model, X = trained_lgbm_model
        feature_names = ["f1", "f2", "f3"]

        result = compute_shap_values(model, X, feature_names)

        assert "shap_values" in result
        shap_vals = result["shap_values"]
        assert shap_vals.shape == X.shape, (
            f"Expected SHAP values shape {X.shape}, got {shap_vals.shape}"
        )

    def test_shap_expected_value_is_float(self, trained_lgbm_model):
        """compute_shap_values returns dict with 'expected_value' key that is a float."""
        from src.inference.shap_analysis import compute_shap_values

        model, X = trained_lgbm_model
        feature_names = ["f1", "f2", "f3"]

        result = compute_shap_values(model, X, feature_names)

        assert "expected_value" in result
        assert isinstance(result["expected_value"], float), (
            f"Expected float, got {type(result['expected_value'])}"
        )

    def test_shap_feature_names_present(self, trained_lgbm_model):
        """compute_shap_values returns dict with 'feature_names' key matching input."""
        from src.inference.shap_analysis import compute_shap_values

        model, X = trained_lgbm_model
        feature_names = ["residual_lag1", "residual_lag2", "year_norm"]

        result = compute_shap_values(model, X, feature_names)

        assert "feature_names" in result
        assert result["feature_names"] == feature_names

    def test_shap_values_are_numeric(self, trained_lgbm_model):
        """SHAP values should be numeric (not NaN, not None)."""
        from src.inference.shap_analysis import compute_shap_values

        model, X = trained_lgbm_model
        feature_names = ["f1", "f2", "f3"]

        result = compute_shap_values(model, X, feature_names)
        shap_vals = result["shap_values"]

        assert not np.any(np.isnan(shap_vals)), "SHAP values contain NaN"
        assert not np.any(np.isinf(shap_vals)), "SHAP values contain Inf"


class TestSHAPPlot:
    """Tests for save_shap_summary_plot function."""

    def test_summary_plot_saves(self, trained_lgbm_model, tmp_path):
        """save_shap_summary_plot creates a PNG file at the specified path (size > 0)."""
        from src.inference.shap_analysis import compute_shap_values, save_shap_summary_plot

        model, X = trained_lgbm_model
        feature_names = ["residual_lag1", "residual_lag2", "year_norm"]

        shap_dict = compute_shap_values(model, X, feature_names)

        output_path = tmp_path / "shap_summary.png"
        save_shap_summary_plot(shap_dict, X, output_path)

        assert output_path.exists(), "PNG file was not created"
        assert output_path.stat().st_size > 0, "PNG file is empty"

    def test_summary_plot_accepts_string_path(self, trained_lgbm_model, tmp_path):
        """save_shap_summary_plot accepts a string path as well as a Path object."""
        from src.inference.shap_analysis import compute_shap_values, save_shap_summary_plot

        model, X = trained_lgbm_model
        feature_names = ["f1", "f2", "f3"]

        shap_dict = compute_shap_values(model, X, feature_names)
        output_path = str(tmp_path / "shap_summary2.png")

        save_shap_summary_plot(shap_dict, X, output_path)

        import os
        assert os.path.exists(output_path), "PNG file was not created with string path"
        assert os.path.getsize(output_path) > 0, "PNG file is empty"
