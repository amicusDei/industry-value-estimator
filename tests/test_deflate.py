"""
Tests for src/processing/deflate.py

Test coverage:
- Deflation identity: base year value is unchanged
- Deflation arithmetic: known nominal + known deflator => expected real
- Missing deflator base year raises ValueError
- Column renaming: _nominal_ -> _real_2020
- No nominal columns survive apply_deflation
"""
import pytest
import pandas as pd
import numpy as np

from src.processing.deflate import deflate_to_base_year, apply_deflation
from src.processing.validate import check_no_nominal_columns


# ================================================================
# deflate_to_base_year tests
# ================================================================


class TestDeflateToBaseYear:
    """Tests for the core deflation formula."""

    def test_deflation_base_year_identity(self):
        """Deflating a value at base year 2020 returns the same value.

        Formula: real = nominal * (deflator[2020] / deflator[year])
        At base year: deflator[2020] / deflator[2020] = 1.0
        """
        deflator = pd.Series({2018: 95.0, 2019: 97.5, 2020: 100.0, 2021: 103.0, 2022: 108.0})
        nominal = pd.Series({2018: 800.0, 2019: 900.0, 2020: 1000.0, 2021: 1100.0, 2022: 1200.0})

        real = deflate_to_base_year(nominal, deflator, base_year=2020)

        # Identity: value at 2020 should be unchanged
        assert real.loc[2020] == pytest.approx(1000.0, rel=1e-9)

    def test_deflation_arithmetic(self):
        """Known nominal value + known deflator produces expected real value.

        Example: $1000 nominal at year where deflator=110, base deflator=100
        real = 1000 * (100 / 110) = $909.09...
        """
        deflator = pd.Series({2019: 100.0, 2020: 110.0})
        nominal = pd.Series({2019: 1000.0, 2020: 500.0})

        real = deflate_to_base_year(nominal, deflator, base_year=2019)

        expected_2019 = 1000.0 * (100.0 / 100.0)  # 1000.0 identity
        expected_2020 = 500.0 * (100.0 / 110.0)   # 454.54...

        assert real.loc[2019] == pytest.approx(expected_2019, rel=1e-6)
        assert real.loc[2020] == pytest.approx(expected_2020, rel=1e-6)

    def test_deflation_classic_example(self):
        """Classic deflation example: deflator 110 at non-base year.

        $1000 nominal with deflator 110, base deflator 100 => $909.09 real
        """
        deflator = pd.Series({2015: 100.0, 2020: 100.0, 2023: 110.0})
        nominal = pd.Series({2015: 1000.0, 2020: 1000.0, 2023: 1000.0})

        real = deflate_to_base_year(nominal, deflator, base_year=2020)

        assert real.loc[2020] == pytest.approx(1000.0, rel=1e-9)
        assert real.loc[2023] == pytest.approx(1000.0 * 100.0 / 110.0, rel=1e-6)

    def test_missing_base_year_raises_value_error(self):
        """If deflator does not contain base year, raises ValueError."""
        deflator = pd.Series({2018: 95.0, 2019: 97.5, 2021: 103.0})  # missing 2020
        nominal = pd.Series({2018: 800.0, 2019: 900.0, 2021: 1100.0})

        with pytest.raises(ValueError, match="Deflator missing for base year 2020"):
            deflate_to_base_year(nominal, deflator, base_year=2020)

    def test_nan_base_year_deflator_raises_value_error(self):
        """If deflator is NaN at base year, raises ValueError."""
        deflator = pd.Series({2018: 95.0, 2019: 97.5, 2020: float("nan"), 2021: 103.0})
        nominal = pd.Series({2018: 800.0, 2019: 900.0, 2020: 1000.0, 2021: 1100.0})

        with pytest.raises(ValueError, match="Deflator is NaN for base year 2020"):
            deflate_to_base_year(nominal, deflator, base_year=2020)

    def test_deflation_series_length(self):
        """Output series has same length as input."""
        deflator = pd.Series({y: 100.0 + y - 2020 for y in range(2010, 2025)})
        nominal = pd.Series({y: float(y * 100) for y in range(2010, 2025)})

        real = deflate_to_base_year(nominal, deflator, base_year=2020)

        assert len(real) == len(nominal)


# ================================================================
# apply_deflation tests
# ================================================================


class TestApplyDeflation:
    """Tests for the DataFrame-level deflation function."""

    def _make_test_df(self):
        """Create a simple DataFrame with nominal columns for testing."""
        return pd.DataFrame({
            "year": [2018, 2019, 2020, 2021, 2022],
            "economy": ["USA"] * 5,
            "gdp_nominal_usd": [800.0, 900.0, 1000.0, 1100.0, 1200.0],
            "rd_pct_gdp": [2.5, 2.6, 2.7, 2.8, 2.9],  # non-monetary, no suffix
            "gdp_deflator_index": [95.0, 97.5, 100.0, 103.0, 108.0],
        })

    def test_column_renaming_nominal_to_real(self):
        """apply_deflation renames _nominal_ columns to _real_2020."""
        df = self._make_test_df()
        result = apply_deflation(df, deflator_col="gdp_deflator_index", base_year=2020)

        assert "gdp_nominal_usd" not in result.columns
        # Should have a real column
        real_cols = [c for c in result.columns if "_real_" in c.lower()]
        assert len(real_cols) >= 1

    def test_no_nominal_after_deflation(self):
        """After apply_deflation, check_no_nominal_columns returns True."""
        df = self._make_test_df()
        result = apply_deflation(df, deflator_col="gdp_deflator_index", base_year=2020)

        # Should not raise — no nominal columns
        assert check_no_nominal_columns(result) is True

    def test_non_monetary_columns_unchanged(self):
        """Non-monetary columns (no _nominal_ suffix) pass through unchanged."""
        df = self._make_test_df()
        result = apply_deflation(df, deflator_col="gdp_deflator_index", base_year=2020)

        # rd_pct_gdp should be exactly the same
        pd.testing.assert_series_equal(result["rd_pct_gdp"], df["rd_pct_gdp"])

    def test_missing_deflator_column_raises(self):
        """RuntimeError if deflator column is absent from DataFrame."""
        df = pd.DataFrame({
            "year": [2020],
            "economy": ["USA"],
            "gdp_nominal_usd": [1000.0],
        })

        with pytest.raises(RuntimeError, match="GDP deflator column"):
            apply_deflation(df, deflator_col="gdp_deflator_index", base_year=2020)

    def test_deflation_base_year_identity_in_dataframe(self):
        """Row at base year 2020 has same real value as original nominal."""
        df = self._make_test_df()
        result = apply_deflation(df, deflator_col="gdp_deflator_index", base_year=2020)

        real_cols = [c for c in result.columns if "_real_" in c.lower()]
        assert real_cols, "No real columns found after deflation"
        real_col = real_cols[0]

        row_2020 = result[result["year"] == 2020]
        original_2020 = df[df["year"] == 2020]["gdp_nominal_usd"].values[0]
        deflated_2020 = row_2020[real_col].values[0]

        assert deflated_2020 == pytest.approx(original_2020, rel=1e-9)

    def test_no_nominal_columns_when_none_present(self):
        """If DataFrame has no nominal columns, returns unchanged (minus deflation)."""
        df = pd.DataFrame({
            "year": [2020],
            "economy": ["USA"],
            "rd_pct_gdp": [2.7],
            "gdp_deflator_index": [100.0],
        })
        result = apply_deflation(df, deflator_col="gdp_deflator_index", base_year=2020)

        # Should not raise, structure preserved
        assert "rd_pct_gdp" in result.columns
        assert check_no_nominal_columns(result) is True
