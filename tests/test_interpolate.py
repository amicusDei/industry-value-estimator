"""
Tests for src/processing/interpolate.py

Test coverage:
- Linear interpolation fills gap between two known values
- estimated_flag=True on interpolated values, False on original values
- Original non-null values are never flagged as estimated
- Spline (index-based) interpolation for large gaps
- apply_interpolation adds estimated_flag column
"""
import pytest
import pandas as pd
import numpy as np

from src.processing.interpolate import interpolate_series, apply_interpolation


# ================================================================
# interpolate_series tests
# ================================================================


class TestInterpolateSeries:
    """Tests for the core interpolation function."""

    def test_interpolation_linear_fills_gap(self):
        """Linear interpolation fills a gap between two known values.

        Gap of 1 NaN between 100 and 200 => filled with 150.
        """
        series = pd.Series([100.0, np.nan, 200.0], index=[2018, 2019, 2020])
        filled, flags = interpolate_series(series, max_linear_gap=2)

        assert filled.loc[2019] == pytest.approx(150.0, rel=1e-9)
        assert not filled.isna().any()

    def test_estimated_flag_true_on_interpolated(self):
        """Interpolated values have estimated_flag=True."""
        series = pd.Series([100.0, np.nan, 200.0], index=[2018, 2019, 2020])
        filled, flags = interpolate_series(series, max_linear_gap=2)

        assert flags.loc[2019] is True or flags.loc[2019] == True  # noqa: E712

    def test_estimated_flag_false_on_original(self):
        """Original non-null values have estimated_flag=False."""
        series = pd.Series([100.0, np.nan, 200.0], index=[2018, 2019, 2020])
        filled, flags = interpolate_series(series, max_linear_gap=2)

        assert flags.loc[2018] == False  # noqa: E712
        assert flags.loc[2020] == False  # noqa: E712

    def test_no_flag_on_non_null_values(self):
        """Original non-null values are never flagged as estimated."""
        series = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0], index=[2010, 2011, 2012, 2013, 2014])
        filled, flags = interpolate_series(series)

        # Only 2012 was NaN
        assert flags.loc[2012] == True  # noqa: E712
        # All others should be False
        for year in [2010, 2011, 2013, 2014]:
            assert flags.loc[year] == False  # noqa: E712

    def test_series_with_no_gaps_returns_all_false_flags(self):
        """If series has no NaN, all estimated_flags are False."""
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=range(2018, 2023))
        filled, flags = interpolate_series(series)

        assert filled.equals(series)
        assert not flags.any()

    def test_large_gap_uses_index_interpolation(self):
        """Large gap (>2 consecutive NaNs) triggers index-based interpolation."""
        series = pd.Series(
            [100.0, np.nan, np.nan, np.nan, 200.0],
            index=[2010, 2011, 2012, 2013, 2014]
        )
        filled, flags = interpolate_series(series, max_linear_gap=2)

        # All three NaN positions should now be filled
        assert not filled.isna().any()
        # All three were estimated
        assert flags.loc[2011] == True  # noqa: E712
        assert flags.loc[2012] == True  # noqa: E712
        assert flags.loc[2013] == True  # noqa: E712

    def test_returns_two_series(self):
        """interpolate_series returns a tuple of (filled, flags)."""
        series = pd.Series([1.0, np.nan, 3.0], index=[2018, 2019, 2020])
        result = interpolate_series(series)

        assert isinstance(result, tuple)
        assert len(result) == 2
        filled, flags = result
        assert isinstance(filled, pd.Series)
        assert isinstance(flags, pd.Series)


# ================================================================
# apply_interpolation tests
# ================================================================


class TestApplyInterpolation:
    """Tests for the DataFrame-level interpolation function."""

    def _make_test_df(self):
        return pd.DataFrame({
            "year": [2018, 2019, 2020, 2021, 2022],
            "economy": ["USA"] * 5,
            "rd_pct_gdp": [2.5, np.nan, 2.7, np.nan, 2.9],
        })

    def test_apply_interpolation_adds_estimated_flag_column(self):
        """apply_interpolation adds estimated_flag column if not present."""
        df = self._make_test_df()
        result = apply_interpolation(df, value_columns=["rd_pct_gdp"])

        assert "estimated_flag" in result.columns

    def test_apply_interpolation_fills_nan_values(self):
        """apply_interpolation fills NaN values in specified columns."""
        df = self._make_test_df()
        result = apply_interpolation(df, value_columns=["rd_pct_gdp"])

        assert not result["rd_pct_gdp"].isna().any()

    def test_apply_interpolation_flags_interpolated_rows(self):
        """Rows with interpolated values have estimated_flag=True."""
        df = self._make_test_df()
        result = apply_interpolation(df, value_columns=["rd_pct_gdp"])

        # Rows with original NaN (years 2019, 2021) should be flagged
        flagged_years = result[result["estimated_flag"]]["year"].tolist()
        assert 2019 in flagged_years
        assert 2021 in flagged_years

    def test_apply_interpolation_does_not_flag_original_values(self):
        """Rows with original non-null values have estimated_flag=False."""
        df = self._make_test_df()
        result = apply_interpolation(df, value_columns=["rd_pct_gdp"])

        # Years 2018, 2020, 2022 had original values
        for year in [2018, 2020, 2022]:
            row = result[result["year"] == year]
            assert row["estimated_flag"].values[0] == False  # noqa: E712

    def test_apply_interpolation_preserves_existing_estimated_flag(self):
        """If estimated_flag already exists, it is OR-ed with new flags."""
        df = pd.DataFrame({
            "year": [2018, 2019, 2020],
            "economy": ["USA"] * 3,
            "rd_pct_gdp": [2.5, np.nan, 2.7],
            "estimated_flag": [True, False, False],  # pre-existing flag on 2018
        })
        result = apply_interpolation(df, value_columns=["rd_pct_gdp"])

        # 2018 was already flagged — should stay flagged
        assert result[result["year"] == 2018]["estimated_flag"].values[0] == True  # noqa: E712
        # 2019 was NaN — should now be flagged
        assert result[result["year"] == 2019]["estimated_flag"].values[0] == True  # noqa: E712

    def test_apply_interpolation_auto_detects_float_columns(self):
        """If value_columns is None, auto-detects all float columns."""
        df = pd.DataFrame({
            "year": [2018, 2019, 2020],
            "economy": ["USA"] * 3,
            "col_a": [1.0, np.nan, 3.0],
            "col_b": [10.0, np.nan, 30.0],
        })
        result = apply_interpolation(df)  # No value_columns specified

        assert not result["col_a"].isna().any()
        assert not result["col_b"].isna().any()
