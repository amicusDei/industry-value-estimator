"""
Integration snapshot tests: verify schema and value ranges of pipeline outputs.

These tests load pinned pipeline outputs and verify structural invariants
(columns, types, value ranges) that downstream consumers depend on.
"""
import pytest
import pandas as pd
from pathlib import Path

from config.settings import DATA_PROCESSED


class TestMarketAnchorsSnapshot:
    """Verify market_anchors_ai.parquet schema and value ranges."""

    @pytest.fixture
    def anchors_df(self):
        path = DATA_PROCESSED / "market_anchors_ai.parquet"
        if not path.exists():
            pytest.skip("market_anchors_ai.parquet not found — run ingestion pipeline first")
        return pd.read_parquet(path)

    def test_expected_columns_present(self, anchors_df):
        """market_anchors_ai.parquet must have required columns."""
        required = {
            "estimate_year",
            "segment",
            "median_usd_billions_real_2020",
            "n_sources",
        }
        missing = required - set(anchors_df.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_column_types(self, anchors_df):
        """Key columns should have expected types."""
        assert pd.api.types.is_integer_dtype(anchors_df["estimate_year"]) or \
               pd.api.types.is_float_dtype(anchors_df["estimate_year"])
        assert pd.api.types.is_object_dtype(anchors_df["segment"]) or \
               pd.api.types.is_string_dtype(anchors_df["segment"])
        assert pd.api.types.is_float_dtype(anchors_df["median_usd_billions_real_2020"])

    def test_year_range(self, anchors_df):
        """Years should be in a reasonable range."""
        assert anchors_df["estimate_year"].min() >= 2010
        assert anchors_df["estimate_year"].max() <= 2035

    def test_segment_values(self, anchors_df):
        """Segments must be from the expected set."""
        expected_segments = {"ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"}
        actual_segments = set(anchors_df["segment"].unique())
        unexpected = actual_segments - expected_segments
        assert not unexpected, f"Unexpected segments: {unexpected}"

    def test_median_values_positive(self, anchors_df):
        """Median USD values should be non-negative."""
        assert (anchors_df["median_usd_billions_real_2020"] >= 0).all(), \
            "Found negative median values"

    def test_median_values_in_range(self, anchors_df):
        """Median USD values should be in a plausible range (0-5000B)."""
        max_val = anchors_df["median_usd_billions_real_2020"].max()
        assert max_val < 5000, f"Max median value {max_val}B seems too high"

    def test_n_sources_non_negative(self, anchors_df):
        """n_sources should be non-negative."""
        assert (anchors_df["n_sources"] >= 0).all(), "Found negative n_sources"


class TestForecastsEnsembleSnapshot:
    """Verify forecasts_ensemble.parquet schema and value ranges."""

    @pytest.fixture
    def forecasts_df(self):
        path = DATA_PROCESSED / "forecasts_ensemble.parquet"
        if not path.exists():
            pytest.skip("forecasts_ensemble.parquet not found — run ensemble pipeline first")
        return pd.read_parquet(path)

    def test_expected_columns_present(self, forecasts_df):
        """forecasts_ensemble.parquet must have required columns."""
        required = {
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
        }
        missing = required - set(forecasts_df.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_ci_ordering(self, forecasts_df):
        """CI bounds must be monotonically ordered for every row."""
        for _, row in forecasts_df.iterrows():
            assert row["ci95_lower"] <= row["ci80_lower"] + 1e-6, \
                f"ci95_lower > ci80_lower at year={row['year']}, segment={row['segment']}"
            assert row["ci80_lower"] <= row["point_estimate_real_2020"] + 1e-6, \
                f"ci80_lower > point at year={row['year']}, segment={row['segment']}"
            assert row["point_estimate_real_2020"] <= row["ci80_upper"] + 1e-6, \
                f"point > ci80_upper at year={row['year']}, segment={row['segment']}"
            assert row["ci80_upper"] <= row["ci95_upper"] + 1e-6, \
                f"ci80_upper > ci95_upper at year={row['year']}, segment={row['segment']}"

    def test_point_estimates_positive(self, forecasts_df):
        """Point estimates should be non-negative."""
        assert (forecasts_df["point_estimate_real_2020"] >= 0).all()

    def test_has_forecast_rows(self, forecasts_df):
        """Should contain both historical and forecast rows."""
        assert forecasts_df["is_forecast"].any(), "No forecast rows found"
        assert (~forecasts_df["is_forecast"]).any(), "No historical rows found"
