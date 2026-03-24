"""
Integration test scaffold for Phase 6 pipeline wiring.

Covers all 5 wiring points that Plan 06-02 will integrate:
  1. LSEG scalar loading and application to PCA composite
  2. Structural break detection returning detected year
  3. assess_stationarity called in run_pipeline per-segment
  4. fit_top_down_ols_with_upgrade called in run_pipeline per-segment
  5. Prophet changepoint year configurable (already wired in Plan 06-01)

Tests for classes 1, 2, 3, and 4 are marked xfail because the pipeline
helper functions (_load_lseg_scalar, _run_break_detection) and call-site
wiring do not exist until Plan 06-02 executes.

Tests for class 5 (TestProphetChangepoint) pass immediately — Plan 06-01
added changepoint_year to both fit_prophet_segment and run_prophet_cv.

Usage:
    uv run pytest tests/test_pipeline_wiring.py -v --tb=short
"""

import logging
import sys
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Suppress verbose prophet/cmdstanpy output in tests
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Ensure project root on sys.path (same pattern as run_statistical_pipeline.py)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helper: synthetic DataFrame for segment series
# ---------------------------------------------------------------------------

def _make_prophet_df(n_years: int = 15, start_year: int = 2010, segment: str = "ai_software") -> pd.DataFrame:
    """Minimal ds/y DataFrame for Prophet tests."""
    rng = np.random.default_rng(42)
    years = list(range(start_year, start_year + n_years))
    values = np.cumsum(rng.standard_normal(n_years)) + np.arange(n_years) * 0.8 + 50.0
    return pd.DataFrame({
        "year": years,
        "value_real_2020": values,
        "industry_segment": segment,
    })


def _make_combined_df(n_years: int = 15, start_year: int = 2010) -> pd.DataFrame:
    """
    Synthetic combined indicator DataFrame matching _SEGMENT_FEATURES columns.
    Used for testing _build_segment_series with lseg_scalar.
    """
    rng = np.random.default_rng(42)
    years = list(range(start_year, start_year + n_years))
    return pd.DataFrame({
        "year": years,
        "gdp_real_2020_usd": rng.uniform(10e12, 20e12, n_years),
        "hightech_exports_real_2020_usd": rng.uniform(1e12, 2e12, n_years),
        "ict_service_exports_real_2020_usd": rng.uniform(0.5e12, 1e12, n_years),
        "rd_pct_gdp": rng.uniform(2.0, 3.5, n_years),
        "patent_applications_residents": rng.uniform(1e6, 2e6, n_years),
        "researchers_per_million": rng.uniform(3000, 5000, n_years),
        "B": rng.uniform(0.5e12, 1e12, n_years),
        "B_ICTS": rng.uniform(0.1e12, 0.3e12, n_years),
        "G": rng.uniform(1e12, 2e12, n_years),
    })


def _make_step_series(flat_start: int = 2010, flat_end: int = 2021,
                      jump_end: int = 2024, base: float = 10.0,
                      jump: float = 50.0) -> pd.Series:
    """Step-function series: flat 2010-2021, jump at 2022-2024."""
    years = list(range(flat_start, jump_end + 1))
    values = []
    for y in years:
        if y <= flat_end:
            values.append(base)
        else:
            values.append(jump)
    return pd.Series(values, index=years)


def _make_smooth_linear_series(start_year: int = 2010, n: int = 15) -> pd.Series:
    """Smooth linear series with no structural break."""
    years = list(range(start_year, start_year + n))
    values = np.arange(n, dtype=float) * 2.0 + 10.0
    return pd.Series(values, index=years)


# ---------------------------------------------------------------------------
# Class 1: TestLsegScalar
# Tests for _load_lseg_scalar() — added to run_statistical_pipeline.py in Plan 06-02
# ---------------------------------------------------------------------------

class TestLsegScalar:
    """Tests for _load_lseg_scalar() pipeline helper (Plan 06-02 wires this)."""

    def test_load_lseg_scalar_returns_dict(self):
        """_load_lseg_scalar() returns dict with 'ai_software' key and float value in [0, 1]."""
        from scripts.run_statistical_pipeline import _load_lseg_scalar

        fake_lseg = pd.DataFrame({
            "year": [2026] * 10,
            "industry_segment": ["ai_software"] * 10,
            "Revenue": [47_300_000_000] * 10,
        })

        with patch("scripts.run_statistical_pipeline.pd.read_parquet", return_value=fake_lseg):
            with patch("scripts.run_statistical_pipeline.DATA_PROCESSED") as mock_path:
                mock_lseg_path = MagicMock()
                mock_lseg_path.exists.return_value = True
                mock_path.__truediv__ = MagicMock(return_value=mock_lseg_path)
                result = _load_lseg_scalar()

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "ai_software" in result, f"Expected 'ai_software' key, got keys: {list(result.keys())}"
        val = result["ai_software"]
        assert isinstance(val, float), f"Expected float value, got {type(val)}"
        assert 0.0 <= val <= 1.0, f"Expected value in [0, 1], got {val}"

    def test_load_lseg_scalar_missing_file(self):
        """_load_lseg_scalar() returns empty dict when parquet file does not exist."""
        from scripts.run_statistical_pipeline import _load_lseg_scalar

        with patch("scripts.run_statistical_pipeline.DATA_PROCESSED") as mock_path:
            mock_lseg_path = MagicMock()
            mock_lseg_path.exists.return_value = False
            mock_path.__truediv__ = MagicMock(return_value=mock_lseg_path)
            result = _load_lseg_scalar()

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert len(result) == 0, f"Expected empty dict for missing file, got {result}"

    def test_lseg_scalar_applied_to_pca(self):
        """_build_segment_series with lseg_scalar returns different scores than without."""
        from scripts.run_statistical_pipeline import _build_segment_series

        combined = _make_combined_df(n_years=15)

        # Call without scalar
        result_no_scalar = _build_segment_series(combined, "ai_software")

        # Call with lseg_scalar
        result_with_scalar = _build_segment_series(
            combined, "ai_software", lseg_scalar={"ai_software": 0.5}
        )

        scores_no_scalar = result_no_scalar["value_real_2020"].values
        scores_with_scalar = result_with_scalar["value_real_2020"].values

        # Scalar should amplify scores — results must differ
        assert not np.allclose(scores_no_scalar, scores_with_scalar), (
            "Expected scores to differ when lseg_scalar=0.5 applied, but they are identical"
        )


# ---------------------------------------------------------------------------
# Class 2: TestBreakDetection
# Tests for _run_break_detection() — added to run_statistical_pipeline.py in Plan 06-02
# ---------------------------------------------------------------------------

class TestBreakDetection:
    """Tests for _run_break_detection() pipeline helper (Plan 06-02 wires this)."""

    def test_run_break_detection_returns_int(self):
        """_run_break_detection() returns an int."""
        from scripts.run_statistical_pipeline import _run_break_detection

        series = _make_step_series()
        result = _run_break_detection(series)

        assert isinstance(result, int), f"Expected int, got {type(result)}"

    def test_run_break_detection_finds_2022(self):
        """_run_break_detection() finds break year == 2022 on step-function series."""
        from scripts.run_statistical_pipeline import _run_break_detection

        series = _make_step_series(flat_start=2010, flat_end=2021, jump_end=2024)
        result = _run_break_detection(series)

        assert result == 2022, f"Expected detected break_year=2022, got {result}"

    def test_run_break_detection_fallback(self):
        """_run_break_detection() returns 2022 (fallback) on smooth linear series with no break."""
        from scripts.run_statistical_pipeline import _run_break_detection

        series = _make_smooth_linear_series()
        result = _run_break_detection(series)

        assert result == 2022, (
            f"Expected fallback break_year=2022 for smooth series, got {result}"
        )


# ---------------------------------------------------------------------------
# Class 3: TestStationarityWiring
# Tests that assess_stationarity is called in run_pipeline — Plan 06-02 wires this
# ---------------------------------------------------------------------------

class TestStationarityWiring:
    """Tests that assess_stationarity is called in the pipeline (Plan 06-02 wires this)."""

    def test_assess_stationarity_called_in_pipeline(self):
        """assess_stationarity is called at least 4 times (once per segment) in run_pipeline."""
        from scripts.run_statistical_pipeline import run_pipeline

        with patch(
            "scripts.run_statistical_pipeline.assess_stationarity",
            wraps=None,
        ) as mock_stationarity:
            mock_stationarity.return_value = {
                "adf_stationary": True,
                "kpss_stationary": True,
                "adf_pval": 0.01,
                "kpss_pval": 0.10,
                "recommendation_d": 0,
            }
            run_pipeline(use_real_data=False)

        call_count = mock_stationarity.call_count
        assert call_count >= 4, (
            f"Expected assess_stationarity called >= 4 times (once per segment), "
            f"got {call_count} calls"
        )


# ---------------------------------------------------------------------------
# Class 4: TestOlsWiring
# Tests that fit_top_down_ols_with_upgrade is called in run_pipeline — Plan 06-02 wires this
# ---------------------------------------------------------------------------

class TestOlsWiring:
    """Tests that OLS is called in the pipeline (Plan 06-02 wires this)."""

    def test_ols_called_in_pipeline(self):
        """fit_top_down_ols_with_upgrade is called at least 4 times in run_pipeline."""
        from scripts.run_statistical_pipeline import run_pipeline

        dummy_ols_result = (None, "OLS", {"r2": 0.9, "r2_adj": 0.88,
                                          "bp_stat": 1.0, "bp_pval": 0.3,
                                          "lb_pval": 0.4})

        with patch(
            "scripts.run_statistical_pipeline.fit_top_down_ols_with_upgrade",
            return_value=dummy_ols_result,
        ) as mock_ols:
            run_pipeline(use_real_data=False)

        call_count = mock_ols.call_count
        assert call_count >= 4, (
            f"Expected fit_top_down_ols_with_upgrade called >= 4 times (once per segment), "
            f"got {call_count} calls"
        )


# ---------------------------------------------------------------------------
# Class 5: TestProphetChangepoint
# Tests for configurable changepoint_year — already wired by Plan 06-01
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Class 6: TestPrivateValuationsPipelineWiring
# Tests that compile_and_write_private_valuations is wired in pipeline.py Step 9
# ---------------------------------------------------------------------------

class TestPrivateValuationsPipelineWiring:
    """Tests that private valuations Step 9 is wired in run_full_pipeline."""

    def test_private_valuations_step_in_pipeline(self):
        """compile_and_write_private_valuations returns Path ending in private_valuations_ai.parquet."""
        from src.processing.private_valuations import compile_and_write_private_valuations
        result = compile_and_write_private_valuations("ai")
        assert isinstance(result, Path), f"Expected Path, got {type(result)}"
        assert str(result).endswith(".parquet"), (
            f"Expected path ending in .parquet, got {result}"
        )
        assert "private_valuations_ai" in str(result), (
            f"Expected 'private_valuations_ai' in path, got {result}"
        )

    def test_step_9_present_in_pipeline_source(self):
        """pipeline.py source contains Step 9 and compile_and_write_private_valuations import."""
        pipeline_source_path = (
            Path(__file__).parent.parent / "src" / "ingestion" / "pipeline.py"
        )
        source = pipeline_source_path.read_text()
        assert "Step 9" in source, "Expected 'Step 9' in pipeline.py source"
        assert "compile_and_write_private_valuations" in source, (
            "Expected 'compile_and_write_private_valuations' in pipeline.py source"
        )


class TestProphetChangepoint:
    """Tests for configurable changepoint_year in Prophet functions (wired in Plan 06-01)."""

    def test_fit_prophet_segment_custom_changepoint(self):
        """fit_prophet_segment with changepoint_year=2021 uses a 2021 date in changepoints."""
        from src.models.statistical.prophet_model import fit_prophet_segment

        df = _make_prophet_df(n_years=15, start_year=2010)
        model = fit_prophet_segment(df, "ai_software", changepoint_year=2021)

        # model.changepoints is a Series of Timestamps for the explicit changepoints
        # The date 2021-01-01 should appear in the model's changepoint list
        changepoint_dates = model.changepoints
        changepoint_years = set(pd.to_datetime(changepoint_dates).dt.year.tolist())

        assert 2021 in changepoint_years, (
            f"Expected changepoint year 2021, got years: {changepoint_years}"
        )
        assert 2022 not in changepoint_years, (
            f"Expected 2022 NOT in changepoints when changepoint_year=2021, "
            f"but found years: {changepoint_years}"
        )

    def test_run_prophet_cv_custom_changepoint(self):
        """run_prophet_cv threads changepoint_year=2021 into Prophet constructor."""
        from src.models.statistical.prophet_model import run_prophet_cv

        df = _make_prophet_df(n_years=15, start_year=2010)

        captured_changepoints = []

        original_prophet = __import__("prophet", fromlist=["Prophet"]).Prophet

        class CapturingProphet(original_prophet):
            def __init__(self, *args, **kwargs):
                captured_changepoints.append(kwargs.get("changepoints", []))
                super().__init__(*args, **kwargs)

        with patch("src.models.statistical.prophet_model.Prophet", CapturingProphet):
            run_prophet_cv(df, "ai_software", n_splits=3, changepoint_year=2021)

        # At least one fold should have passed "2021-01-01" as the changepoint
        # (folds where 2021 is in the training window; early folds may have no changepoint)
        all_changepoint_strings = [
            cp for cps in captured_changepoints for cp in cps
        ]

        assert any("2021" in str(cp) for cp in all_changepoint_strings), (
            f"Expected '2021' in at least one fold's changepoints, "
            f"got: {captured_changepoints}"
        )
        assert not any("2022" in str(cp) for cp in all_changepoint_strings), (
            f"Expected '2022' NOT in any fold's changepoints when changepoint_year=2021, "
            f"got: {captured_changepoints}"
        )


# ---------------------------------------------------------------------------
# Class 6: TestAttributionWiring
# Tests that Step 8 revenue attribution is wired into pipeline.py
# ---------------------------------------------------------------------------

class TestAttributionWiring:
    """Tests that Step 8 revenue attribution runs in the pipeline (Plan 10-02 wires this)."""

    def test_attribution_step_in_pipeline(self):
        """compile_and_write_attribution('ai') returns a Path ending in revenue_attribution_ai.parquet."""
        from src.processing.revenue_attribution import compile_and_write_attribution
        from pathlib import Path

        result = compile_and_write_attribution("ai")

        assert isinstance(result, Path), f"Expected Path, got {type(result)}"
        assert result.name == "revenue_attribution_ai.parquet", (
            f"Expected filename 'revenue_attribution_ai.parquet', got '{result.name}'"
        )
        assert result.exists(), f"Parquet file not found at {result}"

    def test_attribution_step_wired_in_pipeline_module(self):
        """pipeline.py Step 8 imports compile_and_write_attribution (source-level check)."""
        from pathlib import Path

        pipeline_path = Path(__file__).parent.parent / "src" / "ingestion" / "pipeline.py"
        source = pipeline_path.read_text()
        assert "compile_and_write_attribution" in source, (
            "compile_and_write_attribution not found in pipeline.py source"
        )
        assert "Step 8" in source, (
            "Step 8 comment not found in pipeline.py source"
        )
