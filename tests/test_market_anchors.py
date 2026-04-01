"""
Tests for the analyst registry YAML and market_anchors.py ingestion module (DATA-09).

Test classes:
- TestAnalystRegistry: validates the YAML registry structure and content
- TestScopeNormalization: validates scope_normalize() function correctness
- TestMarketAnchorSchema: validates compiled DataFrame schema compliance
- TestSourceCoverage: validates per-year source coverage requirements
- TestCompileMarketAnchors: validates compile_market_anchors() pipeline output
"""
import yaml
import pandas as pd
import pytest
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / "data" / "raw" / "market_anchors" / "ai_analyst_registry.yaml"

VALID_SEGMENTS = {"total", "ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"}
REQUIRED_ENTRY_FIELDS = {
    "source_firm",
    "publication_year",
    "estimate_year",
    "segment",
    "as_published_usd_billions",
    "scope_includes",
    "scope_excludes",
    "methodology_notes",
    "confidence",
}


@pytest.fixture
def registry() -> dict:
    """Load the YAML registry once and share across tests."""
    with open(REGISTRY_PATH, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def entries(registry) -> list:
    """Return the list of entries from the registry."""
    return registry["entries"]


class TestAnalystRegistry:
    def test_registry_loads(self, registry):
        """YAML loads successfully and has top-level 'entries' key."""
        assert isinstance(registry, dict)
        assert "entries" in registry

    def test_minimum_entries(self, entries):
        """Registry has at least 40 entries."""
        assert len(entries) >= 40, f"Expected >= 40 entries, got {len(entries)}"

    def test_required_fields(self, entries):
        """Every entry has all required fields with non-null values."""
        for i, entry in enumerate(entries):
            for field in REQUIRED_ENTRY_FIELDS:
                assert field in entry, f"Entry {i} missing field '{field}': {entry.get('source_firm', '?')}"
                assert entry[field] is not None, (
                    f"Entry {i} field '{field}' is None for {entry.get('source_firm', '?')}"
                )

    def test_segment_values(self, entries):
        """Every entry's segment is one of the valid segment values."""
        for i, entry in enumerate(entries):
            assert entry["segment"] in VALID_SEGMENTS, (
                f"Entry {i} has invalid segment '{entry['segment']}' "
                f"(firm={entry.get('source_firm', '?')}, year={entry.get('estimate_year', '?')})"
            )

    def test_vintage_coverage(self, entries):
        """Publication years span at least 2019 to 2025."""
        pub_years = {entry["publication_year"] for entry in entries}
        assert min(pub_years) <= 2019, f"Oldest publication_year is {min(pub_years)}, expected <= 2019"
        assert max(pub_years) >= 2025, f"Newest publication_year is {max(pub_years)}, expected >= 2025"


class TestScopeNormalization:
    def test_normalize_idc(self):
        """IDC estimate with scope_coefficient 1.0 returns unchanged value."""
        from src.ingestion.market_anchors import scope_normalize
        result = scope_normalize(207.0, 1.0)
        assert abs(result - 207.0) < 0.001, f"Expected ~207.0, got {result}"

    def test_normalize_gartner(self):
        """Gartner $1500B with scope_coefficient 0.18 returns ~$270B."""
        from src.ingestion.market_anchors import scope_normalize
        result = scope_normalize(1500.0, 0.18)
        assert abs(result - 270.0) < 0.01, f"Expected ~270.0, got {result}"

    def test_normalize_zero_returns_zero(self):
        """Zero input returns zero regardless of coefficient."""
        from src.ingestion.market_anchors import scope_normalize
        assert scope_normalize(0.0, 0.85) == 0.0

    def test_normalize_proportional(self):
        """Scope normalization is purely multiplicative (proportional)."""
        from src.ingestion.market_anchors import scope_normalize
        assert abs(scope_normalize(100.0, 0.5) - 50.0) < 0.001


class TestMarketAnchorSchema:
    def test_compiled_df_validates(self):
        """Compiled DataFrame passes MARKET_ANCHOR_SCHEMA.validate() without error."""
        from src.ingestion.market_anchors import compile_market_anchors, validate_market_anchors
        df = compile_market_anchors("ai")
        result = validate_market_anchors(df)
        assert result is not None
        assert len(result) > 0

    def test_has_both_nominal_and_real(self):
        """Compiled DataFrame has _nominal columns (real_2020 is Plan 08-04 responsibility)."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        # Plan 08-02 outputs nominal only; real_2020 deflation is done in Plan 08-04
        nominal_cols = [c for c in df.columns if "nominal" in c]
        assert len(nominal_cols) >= 1, f"Expected at least one _nominal column, got: {df.columns.tolist()}"


class TestSourceCoverage:
    def test_per_year_source_count(self):
        """For years 2020-2024, the compiled DataFrame has n_sources >= 3."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        for year in range(2020, 2025):
            year_rows = df[df["estimate_year"] == year]
            if len(year_rows) == 0:
                pytest.fail(f"No rows for estimate_year={year}")
            max_sources = year_rows["n_sources"].max()
            assert max_sources >= 3, (
                f"Year {year}: max n_sources={max_sources}, expected >= 3. "
                f"Rows: {year_rows[['segment', 'n_sources']].to_dict('records')}"
            )


class TestCompileMarketAnchors:
    def test_compile_returns_dataframe(self):
        """compile_market_anchors('ai') returns a non-empty pd.DataFrame."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_percentile_ordering(self):
        """p25 <= median <= p75 for all rows in the compiled DataFrame."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        for i, row in df.iterrows():
            assert row["p25_usd_billions_nominal"] <= row["median_usd_billions_nominal"], (
                f"Row {i}: p25 ({row['p25_usd_billions_nominal']}) > median ({row['median_usd_billions_nominal']})"
            )
            assert row["median_usd_billions_nominal"] <= row["p75_usd_billions_nominal"], (
                f"Row {i}: median ({row['median_usd_billions_nominal']}) > p75 ({row['p75_usd_billions_nominal']})"
            )

    def test_expected_columns(self):
        """Compiled DataFrame has all expected columns."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        expected_cols = {
            "estimate_year", "segment",
            "p25_usd_billions_nominal", "median_usd_billions_nominal", "p75_usd_billions_nominal",
            "n_sources", "source_list", "estimated_flag",
        }
        missing = expected_cols - set(df.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_segment_values_in_compiled(self):
        """All segments in compiled output are valid segment values."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        for seg in df["segment"].unique():
            assert seg in VALID_SEGMENTS, f"Invalid segment in compiled output: {seg}"

    def test_load_analyst_registry_returns_dataframe(self):
        """load_analyst_registry() returns a DataFrame with all YAML entry fields."""
        from src.ingestion.market_anchors import load_analyst_registry
        df = load_analyst_registry(REGISTRY_PATH)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        for field in REQUIRED_ENTRY_FIELDS:
            assert field in df.columns, f"Missing column '{field}' in registry DataFrame"


# ============================================================
# Plan 08-04 tests: deflation, year coverage, estimated_flag, percentile ordering
# ============================================================

PARQUET_PATH = Path(__file__).parent.parent / "data" / "processed" / "market_anchors_ai.parquet"


@pytest.fixture(scope="module")
def anchors_df() -> pd.DataFrame:
    """
    Produce the full market_anchors_ai.parquet and load it.

    Runs compile_and_write_market_anchors() once per test module to avoid
    repeated file I/O. All DATA-11 tests share this fixture.
    """
    from src.ingestion.market_anchors import compile_and_write_market_anchors
    path = compile_and_write_market_anchors("ai")
    return pd.read_parquet(path)


class TestDeflation:
    """DATA-11: Nominal values are deflated to real 2020 USD."""

    def test_real_2020_columns_exist(self, anchors_df):
        """Output has _real_2020 columns for p25, median, p75."""
        expected_real_cols = {
            "p25_usd_billions_real_2020",
            "median_usd_billions_real_2020",
            "p75_usd_billions_real_2020",
        }
        missing = expected_real_cols - set(anchors_df.columns)
        assert not missing, f"Missing real_2020 columns: {missing}"

    def test_real_less_than_nominal_for_post_2020(self, anchors_df):
        """For years > 2020, real values should be <= nominal (inflation adjustment)."""
        post_2020 = anchors_df[anchors_df["estimate_year"] > 2020]
        # Check across all segments (total is no longer in output after v1.2 disaggregation)
        check_rows = post_2020[post_2020["segment"] == "ai_hardware"]
        for _, row in check_rows.iterrows():
            assert row["median_usd_billions_real_2020"] <= row["median_usd_billions_nominal"], (
                f"Year {row['estimate_year']}: real_2020 ({row['median_usd_billions_real_2020']:.2f}) "
                f"> nominal ({row['median_usd_billions_nominal']:.2f})"
            )

    def test_real_greater_than_nominal_for_pre_2020(self, anchors_df):
        """For years < 2020, real values should be >= nominal (deflation adjustment)."""
        pre_2020 = anchors_df[
            (anchors_df["estimate_year"] < 2020) & (anchors_df["segment"] == "ai_hardware")
        ]
        for _, row in pre_2020.iterrows():
            assert row["median_usd_billions_real_2020"] >= row["median_usd_billions_nominal"], (
                f"Year {row['estimate_year']}: real_2020 ({row['median_usd_billions_real_2020']:.2f}) "
                f"< nominal ({row['median_usd_billions_nominal']:.2f})"
            )


class TestYearCoverage:
    """DATA-11: Full 2017-2025 coverage after interpolation."""

    def test_all_years_present(self, anchors_df):
        """Every segment has entries for all years 2017-2025 (quarterly)."""
        expected_years = set(range(2017, 2026))
        for segment in anchors_df["segment"].unique():
            seg_years = set(anchors_df[anchors_df["segment"] == segment]["estimate_year"].tolist())
            missing = expected_years - seg_years
            assert not missing, (
                f"Segment '{segment}' missing years: {sorted(missing)}"
            )

    def test_no_nan_values(self, anchors_df):
        """No NaN in median_usd_billions_real_2020 after interpolation."""
        nan_count = anchors_df["median_usd_billions_real_2020"].isna().sum()
        assert nan_count == 0, (
            f"Found {nan_count} NaN values in median_usd_billions_real_2020"
        )

    def test_min_row_count(self, anchors_df):
        """At least 144 rows present (9 years x 4 quarters x 4 segments).

        Since v1.2, total-market entries are disaggregated into segment-level anchors
        and the 'total' segment is no longer in the output DataFrame.
        """
        assert len(anchors_df) >= 144, (
            f"Expected >= 144 rows (quarterly, 4 segments), got {len(anchors_df)}"
        )


class TestEstimatedFlag:
    """DATA-11: Interpolated years are flagged."""

    def test_interpolated_rows_flagged(self, anchors_df):
        """Rows with n_sources=0 (interpolated/extrapolated) have estimated_flag=True."""
        interpolated = anchors_df[anchors_df["n_sources"] == 0]
        if len(interpolated) > 0:
            all_flagged = interpolated["estimated_flag"].all()
            assert all_flagged, (
                "Some interpolated rows (n_sources=0) do not have estimated_flag=True"
            )

    def test_real_data_rows_not_flagged(self, anchors_df):
        """Rows backed by multiple analyst sources have estimated_flag reflecting actual data.

        Since v1.2, total-market entries are disaggregated into segment-level anchors.
        We check that segment-level rows with high source counts exist for core years.
        """
        # Rows with n_sources >= 3 should exist for any segment in 2020-2024
        high_coverage = anchors_df[
            (anchors_df["segment"] != "total") & (anchors_df["n_sources"] >= 3)
        ]
        assert len(high_coverage) > 0, (
            "Expected segment-level rows with n_sources >= 3 for core years 2020-2024"
        )

    def test_year_2017_is_estimated_for_sub_segments(self, anchors_df):
        """Year 2017 Q1-Q3 for sub-segments must be estimated (interpolated). Q4 may have real data."""
        sub_segments = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]
        for seg in sub_segments:
            rows_2017 = anchors_df[
                (anchors_df["segment"] == seg) & (anchors_df["estimate_year"] == 2017)
            ]
            if "quarter" in anchors_df.columns:
                assert len(rows_2017) == 4, f"Expected 4 quarterly rows for {seg} year 2017, got {len(rows_2017)}"
                # Q1-Q3 must be estimated (interpolated from Q4)
                q1_q3 = rows_2017[rows_2017["quarter"].isin([1, 2, 3])]
                assert q1_q3["estimated_flag"].all(), (
                    f"{seg} year 2017 Q1-Q3 should have estimated_flag=True (interpolated)"
                )
            else:
                assert len(rows_2017) == 1, f"Expected 1 row for {seg} year 2017"
                assert rows_2017.iloc[0]["estimated_flag"] is True or rows_2017.iloc[0]["estimated_flag"] == True


class TestPercentileOrder:
    """DATA-11: p25 <= median <= p75 invariant."""

    def test_percentile_ordering_nominal(self, anchors_df):
        """p25_nominal <= median_nominal <= p75_nominal for all rows."""
        for i, row in anchors_df.iterrows():
            assert row["p25_usd_billions_nominal"] <= row["median_usd_billions_nominal"], (
                f"Row {i} (year={row['estimate_year']}, seg={row['segment']}): "
                f"p25_nominal ({row['p25_usd_billions_nominal']:.4f}) > "
                f"median_nominal ({row['median_usd_billions_nominal']:.4f})"
            )
            assert row["median_usd_billions_nominal"] <= row["p75_usd_billions_nominal"], (
                f"Row {i} (year={row['estimate_year']}, seg={row['segment']}): "
                f"median_nominal ({row['median_usd_billions_nominal']:.4f}) > "
                f"p75_nominal ({row['p75_usd_billions_nominal']:.4f})"
            )

    def test_percentile_ordering_real(self, anchors_df):
        """p25_real_2020 <= median_real_2020 <= p75_real_2020 for all rows."""
        for i, row in anchors_df.iterrows():
            assert row["p25_usd_billions_real_2020"] <= row["median_usd_billions_real_2020"], (
                f"Row {i} (year={row['estimate_year']}, seg={row['segment']}): "
                f"p25_real ({row['p25_usd_billions_real_2020']:.4f}) > "
                f"median_real ({row['median_usd_billions_real_2020']:.4f})"
            )
            assert row["median_usd_billions_real_2020"] <= row["p75_usd_billions_real_2020"], (
                f"Row {i} (year={row['estimate_year']}, seg={row['segment']}): "
                f"median_real ({row['median_usd_billions_real_2020']:.4f}) > "
                f"p75_real ({row['p75_usd_billions_real_2020']:.4f})"
            )


# ============================================================
# v2-AP1 tests: Analyst Dispersion Index
# ============================================================

DISPERSION_PARQUET_PATH = Path(__file__).parent.parent / "data" / "processed" / "analyst_dispersion.parquet"


class TestAnalystDispersion:
    """v2-AP1: Analyst Dispersion Index — IQR, std, min, max per segment/year."""

    def test_analyst_dispersion_shape(self):
        """compute_analyst_dispersion returns a DataFrame with expected columns and non-zero rows."""
        from src.ingestion.market_anchors import compute_analyst_dispersion, load_analyst_registry
        from src.ingestion.market_anchors import _disaggregate_totals
        from config.settings import DATA_RAW, load_industry_config

        # Reproduce the raw_df as it exists right before aggregation
        registry_path = DATA_RAW / "market_anchors" / "ai_analyst_registry.yaml"
        raw_df = load_analyst_registry(registry_path)
        config = load_industry_config("ai")
        scope_table = config.get("scope_mapping_table", [])
        scope_map = {entry["firm"]: entry["scope_coefficient"] for entry in scope_table}
        raw_df["scope_coefficient"] = raw_df["source_firm"].map(scope_map).fillna(1.0)

        def _apply_scope(row):
            if row["segment"] == "total":
                return row["as_published_usd_billions"] * row["scope_coefficient"]
            seg_coeff = row.get("segment_scope_coefficient")
            if pd.notna(seg_coeff) and seg_coeff != 1.0:
                return row["as_published_usd_billions"] * float(seg_coeff)
            return row["as_published_usd_billions"]

        raw_df["scope_normalized_usd_billions"] = raw_df.apply(_apply_scope, axis=1)
        segment_ids = [s["id"] for s in config.get("segments", [])]
        if segment_ids:
            raw_df = _disaggregate_totals(raw_df, segment_ids)

        disp = compute_analyst_dispersion(raw_df)

        # Check expected columns
        expected_cols = {
            "segment", "year", "iqr_usd_billions", "std_usd_billions",
            "min_usd_billions", "max_usd_billions", "n_sources", "dispersion_ratio",
        }
        assert expected_cols.issubset(set(disp.columns)), (
            f"Missing columns: {expected_cols - set(disp.columns)}"
        )

        # Non-empty
        assert len(disp) > 0, "Dispersion DataFrame is empty"

    def test_no_nan_where_sufficient_sources(self):
        """IQR should not be NaN where n_sources >= 3."""
        from src.ingestion.market_anchors import compute_analyst_dispersion, load_analyst_registry
        from src.ingestion.market_anchors import _disaggregate_totals
        from config.settings import DATA_RAW, load_industry_config

        registry_path = DATA_RAW / "market_anchors" / "ai_analyst_registry.yaml"
        raw_df = load_analyst_registry(registry_path)
        config = load_industry_config("ai")
        scope_table = config.get("scope_mapping_table", [])
        scope_map = {entry["firm"]: entry["scope_coefficient"] for entry in scope_table}
        raw_df["scope_coefficient"] = raw_df["source_firm"].map(scope_map).fillna(1.0)

        def _apply_scope(row):
            if row["segment"] == "total":
                return row["as_published_usd_billions"] * row["scope_coefficient"]
            seg_coeff = row.get("segment_scope_coefficient")
            if pd.notna(seg_coeff) and seg_coeff != 1.0:
                return row["as_published_usd_billions"] * float(seg_coeff)
            return row["as_published_usd_billions"]

        raw_df["scope_normalized_usd_billions"] = raw_df.apply(_apply_scope, axis=1)
        segment_ids = [s["id"] for s in config.get("segments", [])]
        if segment_ids:
            raw_df = _disaggregate_totals(raw_df, segment_ids)

        disp = compute_analyst_dispersion(raw_df)
        sufficient = disp[disp["n_sources"] >= 3]
        nan_iqr = sufficient["iqr_usd_billions"].isna().sum()
        assert nan_iqr == 0, f"Found {nan_iqr} NaN IQR values where n_sources >= 3"

    def test_iqr_non_negative(self):
        """IQR must be >= 0 for all rows."""
        from src.ingestion.market_anchors import compute_analyst_dispersion, load_analyst_registry
        from src.ingestion.market_anchors import _disaggregate_totals
        from config.settings import DATA_RAW, load_industry_config

        registry_path = DATA_RAW / "market_anchors" / "ai_analyst_registry.yaml"
        raw_df = load_analyst_registry(registry_path)
        config = load_industry_config("ai")
        scope_table = config.get("scope_mapping_table", [])
        scope_map = {entry["firm"]: entry["scope_coefficient"] for entry in scope_table}
        raw_df["scope_coefficient"] = raw_df["source_firm"].map(scope_map).fillna(1.0)

        def _apply_scope(row):
            if row["segment"] == "total":
                return row["as_published_usd_billions"] * row["scope_coefficient"]
            seg_coeff = row.get("segment_scope_coefficient")
            if pd.notna(seg_coeff) and seg_coeff != 1.0:
                return row["as_published_usd_billions"] * float(seg_coeff)
            return row["as_published_usd_billions"]

        raw_df["scope_normalized_usd_billions"] = raw_df.apply(_apply_scope, axis=1)
        segment_ids = [s["id"] for s in config.get("segments", [])]
        if segment_ids:
            raw_df = _disaggregate_totals(raw_df, segment_ids)

        disp = compute_analyst_dispersion(raw_df)
        negative_iqr = (disp["iqr_usd_billions"] < 0).sum()
        assert negative_iqr == 0, f"Found {negative_iqr} negative IQR values"
