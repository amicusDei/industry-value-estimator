"""Tests for the diagnostics subsystem: structural breaks and model evaluation."""

import numpy as np
import pandas as pd
import pytest


class TestStructuralBreaks:
    """Tests for src/diagnostics/structural_breaks.py."""

    def test_cusum_output_shape(self):
        """run_cusum returns dict with stat, p_value, critical_values keys."""
        from src.diagnostics.structural_breaks import run_cusum

        series = pd.Series(np.arange(20, dtype=float), index=range(2000, 2020))
        result = run_cusum(series)

        assert isinstance(result, dict)
        assert "stat" in result
        assert "p_value" in result
        assert "critical_values" in result
        assert isinstance(result["stat"], float)
        assert isinstance(result["p_value"], float)

    def test_cusum_detects_break(self):
        """run_cusum detects level shift at index 10 with p_value < 0.05."""
        from src.diagnostics.structural_breaks import run_cusum

        series = pd.Series(
            np.concatenate([np.ones(10), np.ones(10) * 5]),
            index=range(2000, 2020),
        )
        result = run_cusum(series)

        assert result["p_value"] < 0.05, (
            f"Expected p_value < 0.05 for level-shift series, got {result['p_value']}"
        )

    def test_chow_known_break(self):
        """run_chow on level-shift series with break_idx=10 returns p_value < 0.05."""
        from src.diagnostics.structural_breaks import run_chow

        series = pd.Series(
            np.concatenate([np.ones(10), np.ones(10) * 5]),
            index=range(2000, 2020),
        )
        result = run_chow(series, break_idx=10)

        assert isinstance(result, dict)
        assert "F_stat" in result
        assert "p_value" in result
        assert "break_year" in result
        assert result["p_value"] < 0.05, (
            f"Expected p_value < 0.05 for known break, got {result['p_value']}"
        )

    def test_chow_no_break(self):
        """run_chow on smooth linear series returns p_value > 0.05."""
        from src.diagnostics.structural_breaks import run_chow

        series = pd.Series(np.arange(20, dtype=float), index=range(2000, 2020))
        result = run_chow(series, break_idx=10)

        assert result["p_value"] > 0.05, (
            f"Expected p_value > 0.05 for linear series, got {result['p_value']}"
        )

    def test_markov_switching_fits(self):
        """fit_markov_switching returns dict with required keys on clear regime-change series."""
        from src.diagnostics.structural_breaks import fit_markov_switching

        rng = np.random.default_rng(42)
        series = pd.Series(
            np.concatenate([rng.normal(1.0, 0.1, 15), rng.normal(5.0, 0.1, 15)]),
            index=range(2000, 2030),
        )
        result = fit_markov_switching(series)

        assert isinstance(result, dict)
        assert "model_type" in result
        assert "results" in result
        assert "regimes" in result
        assert "transition_matrix" in result

    def test_markov_fallback(self):
        """fit_markov_switching with 5-element series returns dict with 'fallback' in model_type."""
        from src.diagnostics.structural_breaks import fit_markov_switching

        series = pd.Series([1.0, 2.0, 5.0, 6.0, 7.0], index=range(2000, 2005))
        result = fit_markov_switching(series)

        assert isinstance(result, dict)
        assert "model_type" in result
        assert "fallback" in result["model_type"].lower(), (
            f"Expected 'fallback' in model_type for too-short series, got '{result['model_type']}'"
        )

    def test_summarize_breaks(self):
        """summarize_breaks returns dict with 'aggregate' key and all segment names."""
        from src.diagnostics.structural_breaks import summarize_breaks

        segment_results = {
            "aggregate": {
                "cusum": {"stat": 2.0, "p_value": 0.01, "critical_values": []},
                "chow": {"F_stat": 5.0, "p_value": 0.02, "break_year": 2022},
                "markov": {"model_type": "markov_switching", "results": None, "regimes": None, "transition_matrix": None},
            },
            "ai_hardware": {
                "cusum": {"stat": 1.5, "p_value": 0.08, "critical_values": []},
                "chow": {"F_stat": 2.0, "p_value": 0.10, "break_year": 2021},
                "markov": {"model_type": "fallback_dummy_ols", "results": None, "regimes": None, "transition_matrix": None},
            },
        }
        result = summarize_breaks(segment_results)

        assert isinstance(result, dict)
        assert "aggregate" in result
        assert "ai_hardware" in result
        for key in ("aggregate", "ai_hardware"):
            assert "break_detected" in result[key]
            assert "break_year" in result[key]
            assert "method_used" in result[key]


class TestModelEval:
    """Tests for src/diagnostics/model_eval.py."""

    def test_compute_rmse(self):
        """compute_rmse returns float close to 0.1732 for known inputs."""
        from src.diagnostics.model_eval import compute_rmse

        actual = np.array([1.0, 2.0, 3.0])
        predicted = np.array([1.1, 2.2, 2.8])
        result = compute_rmse(actual, predicted)

        assert isinstance(result, float)
        assert abs(result - 0.1732) < 0.001, f"Expected ~0.1732, got {result}"

    def test_compute_mape(self):
        """compute_mape returns float close to 6.11 for known inputs."""
        from src.diagnostics.model_eval import compute_mape

        actual = np.array([100.0, 200.0, 300.0])
        predicted = np.array([110.0, 190.0, 310.0])
        result = compute_mape(actual, predicted)

        assert isinstance(result, float)
        # mean of [10%, 5%, 3.33%] = 6.11%
        assert abs(result - 6.11) < 0.1, f"Expected ~6.11, got {result}"

    def test_compute_r2(self):
        """compute_r2 returns float > 0.95 for near-perfect fit."""
        from src.diagnostics.model_eval import compute_r2

        actual = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        predicted = np.array([1.1, 1.9, 3.2, 3.8, 5.1])
        result = compute_r2(actual, predicted)

        assert isinstance(result, float)
        assert result > 0.95, f"Expected R2 > 0.95 for near-perfect fit, got {result}"

    def test_compute_aic_bic(self):
        """compute_aic_bic returns dict with aic, bic, aicc where aicc > aic for small N."""
        from src.diagnostics.model_eval import compute_aic_bic

        residuals = np.array([0.1, -0.2, 0.15, -0.1, 0.05])
        result = compute_aic_bic(residuals, n_params=2)

        assert isinstance(result, dict)
        assert "aic" in result
        assert "bic" in result
        assert "aicc" in result
        assert result["aicc"] > result["aic"], (
            f"Expected aicc > aic (small-N penalty), got aic={result['aic']}, aicc={result['aicc']}"
        )

    def test_ljung_box(self):
        """ljung_box_test returns dict with statistic and p_value as float."""
        from src.diagnostics.model_eval import ljung_box_test

        rng = np.random.default_rng(42)
        residuals = rng.standard_normal(50)
        result = ljung_box_test(residuals, lags=5)

        assert isinstance(result, dict)
        assert "statistic" in result
        assert "p_value" in result
        assert isinstance(result["p_value"], float)

    def test_compare_models(self):
        """compare_models returns dict with winner='ARIMA' when ARIMA RMSE is lower."""
        from src.diagnostics.model_eval import compare_models

        arima_cv = [{"rmse": 1.0, "mape": 5.0}]
        prophet_cv = [{"rmse": 1.5, "mape": 7.0}]
        result = compare_models(arima_cv, prophet_cv, segment="ai_hardware")

        assert isinstance(result, dict)
        assert result["winner"] == "ARIMA", f"Expected winner='ARIMA', got '{result['winner']}'"
        assert "segment" in result
        assert result["segment"] == "ai_hardware"
        assert "arima_mean_cv_rmse" in result
        assert "prophet_mean_cv_rmse" in result
        assert "margin_pct" in result
