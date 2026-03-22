"""
Tests for forecast output DataFrame schema, vintage, CI ordering, dual units, is_forecast flag.

Tests are written before implementation (TDD RED phase).
"""
import pytest
import numpy as np
import pandas as pd


def _make_segment_forecasts():
    """
    Build synthetic segment_forecasts dict for testing.

    Returns a dict with one segment ('ai_software') covering years 2020-2030.
    Historical years 2020-2024 have is_forecast=False; 2025-2030 have is_forecast=True.
    """
    years = list(range(2020, 2031))  # 11 years
    n = len(years)

    # Simple increasing trend for point estimates
    point_estimates = np.array([1.0 + i * 0.1 for i in range(n)])

    # CI bounds set so ordering is maintained
    ci80_lower = point_estimates - 0.05
    ci80_upper = point_estimates + 0.05
    ci95_lower = point_estimates - 0.10
    ci95_upper = point_estimates + 0.10

    is_forecast = [y >= 2025 for y in years]

    return {
        "ai_software": {
            "years": years,
            "point_estimates": point_estimates,
            "ci80_lower": ci80_lower,
            "ci80_upper": ci80_upper,
            "ci95_lower": ci95_lower,
            "ci95_upper": ci95_upper,
            "is_forecast": is_forecast,
        }
    }


class TestForecastOutputSchema:
    """Tests for build_forecast_dataframe output contract."""

    def test_vintage_column(self):
        """DataFrame must have 'data_vintage' column of type str, not None."""
        from src.inference.forecast import build_forecast_dataframe

        seg_fcasts = _make_segment_forecasts()
        df = build_forecast_dataframe(seg_fcasts, data_vintage="2024-Q4")
        assert "data_vintage" in df.columns
        assert df["data_vintage"].notna().all()
        # Must be str dtype (not None or object holding None)
        assert all(isinstance(v, str) for v in df["data_vintage"])

    def test_output_units(self):
        """DataFrame must have both real 2020 USD and nominal USD point estimate columns."""
        from src.inference.forecast import build_forecast_dataframe

        seg_fcasts = _make_segment_forecasts()
        df = build_forecast_dataframe(seg_fcasts, data_vintage="2024-Q4")
        assert "point_estimate_real_2020" in df.columns
        assert "point_estimate_nominal" in df.columns

    def test_no_bare_point_forecasts(self):
        """Every row must have ci80_lower, ci80_upper, ci95_lower, ci95_upper — no NaN."""
        from src.inference.forecast import build_forecast_dataframe

        seg_fcasts = _make_segment_forecasts()
        df = build_forecast_dataframe(seg_fcasts, data_vintage="2024-Q4")
        ci_cols = ["ci80_lower", "ci80_upper", "ci95_lower", "ci95_upper"]
        for col in ci_cols:
            assert col in df.columns, f"Missing CI column: {col}"
            assert df[col].notna().all(), f"NaN values in CI column: {col}"

    def test_ci_ordering(self):
        """For every row: ci95_lower <= ci80_lower <= point_estimate_real_2020 <= ci80_upper <= ci95_upper."""
        from src.inference.forecast import build_forecast_dataframe

        seg_fcasts = _make_segment_forecasts()
        df = build_forecast_dataframe(seg_fcasts, data_vintage="2024-Q4")
        assert (df["ci95_lower"] <= df["ci80_lower"]).all(), "ci95_lower > ci80_lower"
        assert (df["ci80_lower"] <= df["point_estimate_real_2020"]).all(), "ci80_lower > point"
        assert (df["point_estimate_real_2020"] <= df["ci80_upper"]).all(), "point > ci80_upper"
        assert (df["ci80_upper"] <= df["ci95_upper"]).all(), "ci80_upper > ci95_upper"

    def test_is_forecast_flag(self):
        """Rows with year <= 2024 have is_forecast=False; rows with year >= 2025 have is_forecast=True."""
        from src.inference.forecast import build_forecast_dataframe

        seg_fcasts = _make_segment_forecasts()
        df = build_forecast_dataframe(seg_fcasts, data_vintage="2024-Q4")
        historical = df[df["year"] <= 2024]
        forecast = df[df["year"] >= 2025]
        assert (historical["is_forecast"] == False).all()  # noqa: E712
        assert (forecast["is_forecast"] == True).all()  # noqa: E712

    def test_output_columns_complete(self):
        """DataFrame must have all 10 required columns."""
        from src.inference.forecast import build_forecast_dataframe

        seg_fcasts = _make_segment_forecasts()
        df = build_forecast_dataframe(seg_fcasts, data_vintage="2024-Q4")
        required_cols = [
            "year",
            "segment",
            "point_estimate_real_2020",
            "point_estimate_nominal",
            "ci80_lower",
            "ci80_upper",
            "ci95_lower",
            "ci95_upper",
            "is_forecast",
            "data_vintage",
        ]
        for col in required_cols:
            assert col in df.columns, f"Missing required column: {col}"

    def test_sorted_by_segment_then_year(self):
        """Output DataFrame must be sorted by (segment, year)."""
        from src.inference.forecast import build_forecast_dataframe

        # Two segments to test sorting
        seg1 = _make_segment_forecasts()
        # Add second segment
        years = list(range(2020, 2031))
        n = len(years)
        seg1["ai_hardware"] = {
            "years": years,
            "point_estimates": np.array([2.0 + i * 0.2 for i in range(n)]),
            "ci80_lower": np.array([2.0 + i * 0.2 - 0.05 for i in range(n)]),
            "ci80_upper": np.array([2.0 + i * 0.2 + 0.05 for i in range(n)]),
            "ci95_lower": np.array([2.0 + i * 0.2 - 0.10 for i in range(n)]),
            "ci95_upper": np.array([2.0 + i * 0.2 + 0.10 for i in range(n)]),
            "is_forecast": [y >= 2025 for y in years],
        }
        df = build_forecast_dataframe(seg1, data_vintage="2024-Q4")
        # Segments should be alphabetical: ai_hardware before ai_software
        assert df.iloc[0]["segment"] == "ai_hardware"
        # Within each segment, years should be ascending
        hw_df = df[df["segment"] == "ai_hardware"]
        assert list(hw_df["year"]) == sorted(hw_df["year"].tolist())

    def test_nominal_greater_than_real_for_future_years(self):
        """Nominal values for years after base year (2020) should be >= real values (inflation)."""
        from src.inference.forecast import build_forecast_dataframe

        seg_fcasts = _make_segment_forecasts()
        df = build_forecast_dataframe(seg_fcasts, data_vintage="2024-Q4")
        # For years > 2020, nominal should be > real (inflation factor > 1)
        post_base = df[df["year"] > 2020]
        assert (post_base["point_estimate_nominal"] >= post_base["point_estimate_real_2020"]).all()


class TestForecastHelpers:
    """Tests for individual helper functions."""

    def test_reflate_to_nominal(self):
        """reflate_to_nominal(100.0, year=2024, base_year=2020) returns > 100.0."""
        from src.inference.forecast import reflate_to_nominal

        result = reflate_to_nominal(100.0, year=2024, base_year=2020)
        assert result > 100.0, f"Expected nominal > 100.0 but got {result}"

    def test_reflate_base_year_returns_same(self):
        """reflate_to_nominal at base year returns same value (factor = 1.0)."""
        from src.inference.forecast import reflate_to_nominal

        result = reflate_to_nominal(100.0, year=2020, base_year=2020)
        assert abs(result - 100.0) < 1e-10

    def test_clip_ci_bounds_no_crossing(self):
        """clip_ci_bounds enforces monotonic ordering."""
        from src.inference.forecast import clip_ci_bounds

        # Deliberately crossed bounds
        row = {
            "point_estimate_real_2020": 10.0,
            "ci80_lower": 11.0,   # crossed: above point
            "ci80_upper": 9.0,    # crossed: below point
            "ci95_lower": 12.0,   # crossed: above ci80_lower
            "ci95_upper": 8.0,    # crossed: below ci80_upper
        }
        clipped = clip_ci_bounds(row)
        assert clipped["ci95_lower"] <= clipped["ci80_lower"]
        assert clipped["ci80_lower"] <= clipped["point_estimate_real_2020"]
        assert clipped["point_estimate_real_2020"] <= clipped["ci80_upper"]
        assert clipped["ci80_upper"] <= clipped["ci95_upper"]

    def test_get_data_vintage(self):
        """get_data_vintage returns 'YYYY-Q4' string from residuals DataFrame max year."""
        from src.inference.forecast import get_data_vintage

        residuals_df = pd.DataFrame({
            "year": [2020, 2021, 2022, 2023, 2024],
            "segment": ["seg1"] * 5,
            "residual": [0.1, 0.2, -0.1, 0.0, 0.3],
        })
        vintage = get_data_vintage(residuals_df)
        assert vintage == "2024-Q4"
        assert isinstance(vintage, str)
