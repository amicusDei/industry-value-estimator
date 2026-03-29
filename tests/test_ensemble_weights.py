"""Ensemble weight contract tests."""

import pytest
from src.models.ensemble import compute_ensemble_weights


def test_weights_sum_to_one():
    w_s, w_l = compute_ensemble_weights(5.0, 3.0)
    assert abs(w_s + w_l - 1.0) < 1e-9


def test_lower_rmse_gets_higher_weight():
    w_s, w_l = compute_ensemble_weights(5.0, 3.0)
    assert w_l > w_s, "Lower RMSE model should get higher weight"


def test_equal_rmse_equal_weights():
    w_s, w_l = compute_ensemble_weights(5.0, 5.0)
    assert abs(w_s - 0.5) < 1e-6
    assert abs(w_l - 0.5) < 1e-6


def test_zero_rmse_handling():
    """Epsilon guard prevents division by zero."""
    w_s, w_l = compute_ensemble_weights(0.0, 5.0)
    assert w_s > 0.99, "Zero-RMSE model should get ~1.0 weight"
    assert w_l < 0.01
