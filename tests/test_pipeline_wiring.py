"""
Integration test scaffold for pipeline wiring.

Covers:
  - Prophet changepoint year configurable (Plan 06-01)
  - Private valuations pipeline wiring (Plan 10-02)
  - Revenue attribution pipeline wiring (Plan 10-02)
  - Walk-forward backtesting pipeline wiring (Plan 10-04)

Note: Tests for v1.0 statistical pipeline helpers (LSEG scalar, break
detection, stationarity wiring, OLS wiring) were removed in v1.1 cleanup
along with scripts/run_statistical_pipeline.py.

Usage:
    uv run pytest tests/test_pipeline_wiring.py -v --tb=short
"""

import logging
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# Suppress verbose prophet/cmdstanpy output in tests
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Ensure project root on sys.path
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


# ---------------------------------------------------------------------------
# TestProphetChangepoint
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


# ---------------------------------------------------------------------------
# Class 7: TestBacktestingWiring
# Tests that Step 10 walk-forward backtesting is wired into pipeline.py
# ---------------------------------------------------------------------------

class TestBacktestingWiring:
    """Tests that Step 10 walk-forward backtesting runs in the pipeline (Plan 10-04 wires this)."""

    def test_backtesting_step_in_pipeline(self):
        """run_backtesting('ai') returns a Path ending in backtesting_results.parquet."""
        from src.backtesting.walk_forward import run_backtesting

        result = run_backtesting("ai")
        assert isinstance(result, Path), f"Expected Path, got {type(result)}"
        assert str(result).endswith("backtesting_results.parquet"), (
            f"Expected path ending in 'backtesting_results.parquet', got '{result}'"
        )

    def test_step_10_present_in_pipeline_source(self):
        """pipeline.py source contains Step 10 and run_backtesting import."""
        pipeline_source_path = (
            Path(__file__).parent.parent / "src" / "ingestion" / "pipeline.py"
        )
        source = pipeline_source_path.read_text()
        assert "Step 10" in source, "Expected 'Step 10' in pipeline.py source"
        assert "run_backtesting" in source, (
            "Expected 'run_backtesting' in pipeline.py source"
        )
