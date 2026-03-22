"""
Tests for ensemble combiner: inverse-RMSE weights and additive blend.

Tests are written before implementation (TDD RED phase).
"""
import pytest
import numpy as np


class TestEnsembleWeights:
    """Tests for compute_ensemble_weights function."""

    def test_inverse_rmse_weights_sum_to_one(self):
        """Weights must sum to 1.0."""
        from src.models.ensemble import compute_ensemble_weights

        stat_w, lgbm_w = compute_ensemble_weights(0.3, 0.2)
        assert abs(stat_w + lgbm_w - 1.0) < 1e-10

    def test_lower_rmse_gets_higher_weight(self):
        """Model with lower RMSE should get higher weight."""
        from src.models.ensemble import compute_ensemble_weights

        stat_w, lgbm_w = compute_ensemble_weights(stat_cv_rmse=0.3, lgbm_cv_rmse=0.2)
        assert lgbm_w > stat_w

    def test_equal_rmse_gives_equal_weights(self):
        """When both models have same RMSE, weights should be equal."""
        from src.models.ensemble import compute_ensemble_weights

        stat_w, lgbm_w = compute_ensemble_weights(0.5, 0.5)
        assert abs(stat_w - 0.5) < 1e-10
        assert abs(lgbm_w - 0.5) < 1e-10

    def test_zero_rmse_no_division_error(self):
        """Zero RMSE should not cause division by zero."""
        from src.models.ensemble import compute_ensemble_weights

        # Should not raise
        stat_w, lgbm_w = compute_ensemble_weights(0.0, 0.5)
        assert abs(stat_w + lgbm_w - 1.0) < 1e-10

    def test_zero_rmse_gets_maximum_weight(self):
        """Model with zero RMSE should get very high weight (near 1.0)."""
        from src.models.ensemble import compute_ensemble_weights

        stat_w, lgbm_w = compute_ensemble_weights(0.0, 0.5)
        # stat_rmse=0.0 means stat gets near-infinite inverse weight
        assert stat_w > 0.99


class TestEnsembleCombiner:
    """Tests for blend_forecasts function."""

    def test_blend_additive(self):
        """blend_forecasts is additive: stat_pred + lgbm_weight * lgbm_correction."""
        from src.models.ensemble import blend_forecasts

        result = blend_forecasts(
            stat_pred=10.0,
            lgbm_correction=2.0,
            stat_weight=0.4,
            lgbm_weight=0.6,
        )
        expected = 10.0 + 0.6 * 2.0  # = 11.2
        assert abs(result - expected) < 1e-10

    def test_blend_zero_correction(self):
        """Zero correction leaves stat_pred unchanged."""
        from src.models.ensemble import blend_forecasts

        result = blend_forecasts(
            stat_pred=5.0,
            lgbm_correction=0.0,
            stat_weight=0.6,
            lgbm_weight=0.4,
        )
        assert abs(result - 5.0) < 1e-10

    def test_blend_works_with_arrays(self):
        """blend_forecasts should work with numpy arrays."""
        from src.models.ensemble import blend_forecasts

        stat_pred = np.array([10.0, 20.0, 30.0])
        correction = np.array([1.0, 2.0, 3.0])
        result = blend_forecasts(stat_pred, correction, 0.4, 0.6)
        expected = stat_pred + 0.6 * correction
        np.testing.assert_allclose(result, expected)

    def test_blend_negative_correction(self):
        """Negative correction should reduce the forecast."""
        from src.models.ensemble import blend_forecasts

        result = blend_forecasts(
            stat_pred=10.0,
            lgbm_correction=-2.0,
            stat_weight=0.5,
            lgbm_weight=0.5,
        )
        expected = 10.0 + 0.5 * (-2.0)  # = 9.0
        assert abs(result - expected) < 1e-10
